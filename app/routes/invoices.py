from datetime import datetime
from flask import Blueprint, request, jsonify, g, Response, current_app
from ..extensions import db
from ..models import Invoice, PdfDownload
from ..schema.invoice import InvoiceSchema
from ..middleware.auth import require_auth, attach_tenant
from ..services.invoice_service import build_invoice, calculate_totals, get_bank_transfer_details, refresh_overdue_status, get_supplier_info
from ..services.quota import quota_status
from ..services.pdf_quota import pdf_quota_status
from ..services.pdf_service import generate_invoice_pdf
from ..services.email_service import overdue_reminder_email, EmailError

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

    if loaded.get("business_profile_id"):
        from ..models import BusinessProfile
        profile = BusinessProfile.query.filter_by(
            id=loaded["business_profile_id"], tenant_id=g.tenant.id
        ).first()
        if not profile:
            return jsonify({"error": "That business profile wasn't found."}), 422

    invoice = build_invoice(g.tenant.id, loaded)
    db.session.add(invoice)
    db.session.commit()
    return jsonify({"data": invoice.to_dict()}), 201


@invoices_bp.get("/pdf-quota")
@require_auth
@attach_tenant
def get_pdf_quota():
    return jsonify({"data": pdf_quota_status(g.tenant)}), 200


@invoices_bp.get("/<invoice_id>/pdf")
@require_auth
@attach_tenant
def download_invoice_pdf(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    status = pdf_quota_status(g.tenant)
    if status["remaining"] <= 0:
        return jsonify({
            "error": f"Weekly PDF download limit reached ({status['limit']} this week). "
                     f"Upgrade your plan or contact support to raise it.",
            "quota": status,
        }), 403

    supplier = get_supplier_info(invoice)
    frontend_url = current_app.config.get("FRONTEND_URL", "").rstrip("/")
    public_url = f"{frontend_url}/i.html?token={invoice.public_token}" if invoice.public_token else None

    pdf_bytes = generate_invoice_pdf(invoice, supplier, public_url)

    db.session.add(PdfDownload(tenant_id=g.tenant.id, invoice_id=invoice.id))
    if invoice.pdf_downloaded_at is None:
        invoice.pdf_downloaded_at = datetime.utcnow()
    db.session.commit()

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.number}.pdf"'},
    )


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

    if "business_profile_id" in loaded:
        if loaded["business_profile_id"]:
            from ..models import BusinessProfile
            profile = BusinessProfile.query.filter_by(
                id=loaded["business_profile_id"], tenant_id=g.tenant.id
            ).first()
            if not profile:
                return jsonify({"error": "That business profile wasn't found."}), 422
        invoice.business_profile_id = loaded["business_profile_id"]

    db.session.commit()
    return jsonify({"data": invoice.to_dict()}), 200


@invoices_bp.post("/<invoice_id>/send")
@require_auth
@attach_tenant
def send_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    if not get_bank_transfer_details(invoice):
        return jsonify({
            "error": "Add your bank transfer details in Settings (or on this invoice's business profile) before sending an invoice."
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


@invoices_bp.post("/<invoice_id>/send-reminder")
@require_auth
@attach_tenant
def send_manual_reminder(invoice_id):
    """
    On-demand version of the automatic overdue reminder — sends
    immediately, no cooldown, since a person explicitly asked for it.
    Only makes sense for SENT/OVERDUE invoices.
    """
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    invoice = refresh_overdue_status(invoice)

    if invoice.status.value not in ("SENT", "OVERDUE"):
        return jsonify({"error": f"Can't send a reminder for a {invoice.status.value.lower()} invoice."}), 400

    if not current_app.config.get("RESEND_API_KEY"):
        return jsonify({"error": "Email isn't configured yet — set RESEND_API_KEY to enable reminders."}), 503

    frontend_url = current_app.config.get("FRONTEND_URL", "").rstrip("/")
    public_url = f"{frontend_url}/i.html?token={invoice.public_token}"

    try:
        overdue_reminder_email(invoice, public_url)
    except EmailError as e:
        current_app.logger.error(f"Manual reminder failed for invoice {invoice.id}: {e}")
        return jsonify({"error": f"Couldn't send the reminder email: {e}"}), 502

    invoice.last_reminder_sent_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"data": invoice.to_dict()}), 200
