from datetime import datetime
from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models import Invoice
from ..schema.invoice import PaymentProofSchema

public_bp = Blueprint("public", __name__)


@public_bp.get("/invoices/<public_token>")
def get_public_invoice(public_token):
    invoice = Invoice.query.filter_by(public_token=public_token).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    data = invoice.to_dict()
    settings = invoice.tenant.settings
    data["bank_transfer_details"] = settings.payment_info if settings else None
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
    settings = invoice.tenant.settings
    data["bank_transfer_details"] = settings.payment_info if settings else None
    return jsonify({"data": data}), 200
