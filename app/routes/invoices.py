from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..models import Invoice
from ..schema.invoice import InvoiceSchema
from ..middleware.auth import require_auth, attach_tenant
from ..services.invoice_service import build_invoice, calculate_totals, get_bank_transfer_details, refresh_overdue_status
from ..services.quota import quota_status

invoices_bp = Blueprint("invoices", __name__)


@invoices_bp.get("/")
@require_auth
@attach_tenant
def list_invoices():
    status = request.args.get("status")
    query = Invoice.query.filter_by(tenant_id=g.tenant.id)
    if status:
        query = query.filter_by(status=status.upper())
    invoices = query.order_by(Invoice.created_at.desc()).all()
    invoices = refresh_overdue_status(invoices)
    return jsonify({
        "data": [inv.to_dict() for inv in invoices],
        "meta": {"total": len(invoices)}
    }), 200


@invoices_bp.get("/quota")
@require_auth
@attach_tenant
def get_quota():
    return jsonify({"data": quota_status(g.tenant)}), 200


@invoices_bp.post("/")
@require_auth
@attach_tenant
def create_invoice():
    status = quota_status(g.tenant)
    if status["remaining"] <= 0:
        return jsonify({
            "error": f"Weekly invoice limit reached ({status['limit']} this week). "
                     f"Upgrade your plan or contact support to raise it.",
            "quota": status,
        }), 403

    data = request.get_json()
    schema = InvoiceSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify(errors), 422

    loaded = schema.load(data)
    invoice = build_invoice(g.tenant.id, loaded)
    db.session.add(invoice)
    db.session.commit()
    return jsonify({"data": invoice.to_dict()}), 201


@invoices_bp.get("/<invoice_id>")
@require_auth
@attach_tenant
def get_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404
    invoice = refresh_overdue_status(invoice)
    return jsonify({"data": invoice.to_dict()}), 200


@invoices_bp.put("/<invoice_id>")
@require_auth
@attach_tenant
def update_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    if invoice.status.value != "DRAFT":
        return jsonify({
            "error": "Only draft invoices can be edited. This one has already been sent to the client."
        }), 400

    data = request.get_json()
    schema = InvoiceSchema(partial=True)
    errors = schema.validate(data)
    if errors:
        return jsonify(errors), 422
    loaded = schema.load(data)

    if "items" in loaded or "tax_rate" in loaded:
        items = loaded.get("items", invoice.items)
        tax_rate = loaded.get("tax_rate", float(invoice.tax_rate))
        subtotal, tax_amount, total = calculate_totals(items, tax_rate)
        invoice.items = items
        invoice.tax_rate = tax_rate
        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.total = total

    for key in ("client_name", "client_email", "client_address", "currency",
                "payment_terms", "due_date", "notes"):
        if key in loaded:
            setattr(invoice, key, loaded[key])

    db.session.commit()
    return jsonify({"data": invoice.to_dict()}), 200


@invoices_bp.post("/<invoice_id>/send")
@require_auth
@attach_tenant
def send_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    if not get_bank_transfer_details(g.tenant):
        return jsonify({
            "error": "Add your bank transfer details in Settings before sending an invoice."
        }), 422

    invoice.status = "SENT"
    db.session.commit()
    return jsonify({"data": invoice.to_dict()}), 200


@invoices_bp.delete("/<invoice_id>")
@require_auth
@attach_tenant
def delete_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    if invoice.status.value != "DRAFT":
        return jsonify({
            "error": "Only draft invoices can be deleted. This one has already been sent — "
                     "cancel it instead to keep the record."
        }), 400

    db.session.delete(invoice)
    db.session.commit()
    return "", 204


@invoices_bp.post("/<invoice_id>/cancel")
@require_auth
@attach_tenant
def cancel_invoice(invoice_id):
    """
    For invoices that have already been sent (or gone overdue) — voids it
    without erasing the record, unlike delete which only works on drafts.
    """
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    if invoice.status.value in ("PAID", "CANCELLED"):
        return jsonify({"error": f"Invoice is already {invoice.status.value.lower()}."}), 400

    invoice.status = "CANCELLED"
    db.session.commit()
    return jsonify({"data": invoice.to_dict()}), 200
