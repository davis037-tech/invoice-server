from flask import Blueprint, jsonify, g
from ..extensions import db
from ..models import Invoice
from ..middleware.auth import require_auth, attach_tenant

billing_bp = Blueprint("billing", __name__)


@billing_bp.post("/invoices/<invoice_id>/mark-paid")
@require_auth
@attach_tenant
def mark_invoice_paid(invoice_id):
    """
    Bank transfers have no payment gateway to call back and confirm the
    transaction, so the tenant confirms receipt themselves (e.g. after
    checking their bank account) and marks the invoice paid manually.
    """
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    if invoice.status.value == "PAID":
        return jsonify({"data": invoice.to_dict()}), 200

    invoice.status = "PAID"
    db.session.commit()
    return jsonify({"data": invoice.to_dict()}), 200


@billing_bp.get("/invoices/<invoice_id>/status")
def get_payment_status(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404
    return jsonify({"status": invoice.status.value}), 200
