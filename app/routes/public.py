from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from ..extensions import db
from ..models import Invoice, User
from ..schema.invoice import PaymentProofSchema
from ..services.invoice_service import refresh_overdue_status, get_bank_transfer_details
from ..services.email_service import payment_proof_submitted_email, EmailError

public_bp = Blueprint("public", __name__)


def _supplier_info(tenant):
    settings = tenant.settings
    return {
        "business_name": (settings.business_name if settings else None) or tenant.name,
        "business_address": settings.business_address if settings else None,
    }


@public_bp.get("/invoices/<public_token>")
def get_public_invoice(public_token):
    invoice = Invoice.query.filter_by(public_token=public_token).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404
    invoice = refresh_overdue_status(invoice)

    data = invoice.to_dict()
    data["bank_transfer_details"] = get_bank_transfer_details(invoice.tenant)
    data["supplier"] = _supplier_info(invoice.tenant)
    return jsonify({"data": data}), 200


@public_bp.post("/invoices/<public_token>/payment-proof")
def submit_payment_proof(public_token):
    invoice = Invoice.query.filter_by(public_token=public_token).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    if invoice.status.value == "PAID":
        return jsonify({"error": "This invoice has already been paid."}), 400

    data = request.get_json() or {}
    schema = PaymentProofSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify(errors), 422
    loaded = schema.load(data)

    if not loaded.get("note") and not loaded.get("image_base64"):
        return jsonify({"error": "Add a reference note or a receipt photo."}), 422

    invoice.payment_proof_note = loaded.get("note")
    invoice.payment_proof_image = loaded.get("image_base64")
    invoice.payment_proof_submitted_at = datetime.utcnow()
    db.session.commit()

    # Best-effort: notify the tenant owner so they know to review it. Never
    # let an email hiccup block the client's submission from succeeding.
    try:
        owner = User.query.filter_by(tenant_id=invoice.tenant_id).order_by(User.created_at.asc()).first()
        if owner and current_app.config.get("RESEND_API_KEY"):
            frontend_url = current_app.config.get("FRONTEND_URL", "").rstrip("/")
            review_url = f"{frontend_url}/invoice-detail.html?id={invoice.id}"
            payment_proof_submitted_email(owner.email, invoice, review_url)
    except EmailError as e:
        current_app.logger.error(f"payment_proof_submitted_email failed: {e}")

    data = invoice.to_dict()
    data["bank_transfer_details"] = get_bank_transfer_details(invoice.tenant)
    data["supplier"] = _supplier_info(invoice.tenant)
    return jsonify({"data": data}), 200
