from datetime import datetime
from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models import Invoice
from ..schema.invoice import PaymentProofSchema
from ..services.invoice_service import refresh_overdue_status, get_bank_transfer_details

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

    data = invoice.to_dict()
    data["bank_transfer_details"] = get_bank_transfer_details(invoice.tenant)
    data["supplier"] = _supplier_info(invoice.tenant)
    return jsonify({"data": data}), 200
