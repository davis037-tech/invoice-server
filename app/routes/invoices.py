from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..models import Invoice
from ..schema.invoice import InvoiceSchema
from ..middleware.auth import require_auth, attach_tenant
from ..services.invoice_service import build_invoice, calculate_totals, get_bank_transfer_details

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
    return jsonify({
        "data": [inv.to_dict() for inv in invoices],
        "meta": {"total": len(invoices)}
    }), 200


@invoices_bp.post("/")
@require_auth
@attach_tenant
def create_invoice():
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
    return jsonify({"data": invoice.to_dict()}), 200


@invoices_bp.put("/<invoice_id>")
@require_auth
@attach_tenant
def update_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

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
    db.session.delete(invoice)
    db.session.commit()
    return "", 204
