from datetime import datetime
from flask import Blueprint, jsonify, g, current_app
from ..extensions import db
from ..models import Invoice
from ..middleware.auth import require_auth, attach_tenant
from ..services.email_service import payment_received_email, EmailError

billing_bp = Blueprint("billing", __name__)


@billing_bp.get("/invoices/awaiting-confirmation")
@require_auth
@attach_tenant
def list_awaiting_confirmation():
    """Invoices where a client has submitted payment proof that hasn't been reviewed yet."""
    invoices = Invoice.query.filter(
        Invoice.tenant_id == g.tenant.id,
        Invoice.payment_proof_submitted_at.isnot(None),
        Invoice.status.notin_(["PAID", "CANCELLED"]),
    ).order_by(Invoice.payment_proof_submitted_at.desc()).all()
    return jsonify({
        "data": [inv.to_dict() for inv in invoices],
        "meta": {"total": len(invoices)}
    }), 200


@billing_bp.post("/invoices/<invoice_id>/mark-paid")
@require_auth
@attach_tenant
def mark_invoice_paid(invoice_id):
    """
    Bank transfers have no payment gateway to call back and confirm the
    transaction, so the tenant confirms receipt themselves (e.g. after
    checking their bank account, possibly against a submitted payment
    proof) and marks the invoice paid manually.
    """
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    if invoice.status.value == "PAID":
        return jsonify({"data": invoice.to_dict()}), 200

    invoice.status = "PAID"
    invoice.paid_at = datetime.utcnow()
    db.session.commit()

    try:
        if current_app.config.get("RESEND_API_KEY"):
            payment_received_email(invoice)
    except EmailError as e:
        current_app.logger.error(f"payment_received_email failed: {e}")

    return jsonify({"data": invoice.to_dict()}), 200


@billing_bp.post("/invoices/<invoice_id>/reject-proof")
@require_auth
@attach_tenant
def reject_payment_proof(invoice_id):
    """
    Clears a submitted payment proof (e.g. it didn't match, was unreadable,
    or doesn't cover the full amount) so the client can submit a new one.
    Invoice status is left as-is — this only affects the proof.
    """
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=g.tenant.id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    invoice.payment_proof_note = None
    invoice.payment_proof_image = None
    invoice.payment_proof_submitted_at = None
    db.session.commit()
    return jsonify({"data": invoice.to_dict()}), 200


@billing_bp.get("/invoices/<invoice_id>/status")
def get_payment_status(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404
    return jsonify({"status": invoice.status.value}), 200
