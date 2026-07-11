from flask import Blueprint, jsonify
from ..models import Invoice

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
