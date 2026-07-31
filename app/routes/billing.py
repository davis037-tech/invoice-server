from datetime import datetime
from flask import Blueprint, jsonify, g, current_app, request
from ..extensions import db
from ..models import Invoice, UpgradeRequest, User, PlatformSettings
from ..middleware.auth import require_auth, attach_tenant
from ..services.email_service import payment_received_email, upgrade_request_submitted_email, EmailError
from ..services.pdf_quota import DEFAULT_PDF_WEEKLY_LIMITS
from ..services.quota import DEFAULT_PLAN_WEEKLY_LIMITS

billing_bp = Blueprint("billing", __name__)


@billing_bp.get("/platform-bank-details")
@require_auth
@attach_tenant
def get_platform_bank_details():
    """Your own bank details, shown to tenants who want to upgrade by transfer."""
    settings = PlatformSettings.get()
    return jsonify({
        "data": {
            "bank_details": settings.formatted(),
            "plan_limits": {p: {"invoices": DEFAULT_PLAN_WEEKLY_LIMITS[p], "pdfs": DEFAULT_PDF_WEEKLY_LIMITS[p]} for p in DEFAULT_PLAN_WEEKLY_LIMITS},
        }
    }), 200


@billing_bp.post("/upgrade-request")
@require_auth
@attach_tenant
def submit_upgrade_request():
    data = request.get_json() or {}
    requested_plan = data.get("requested_plan")
    if requested_plan not in ("PRO", "TEAM"):
        return jsonify({"error": "requested_plan must be PRO or TEAM"}), 422

    note = (data.get("note") or "").strip() or None
    image_base64 = data.get("image_base64")
    if image_base64 and len(image_base64) > 3_500_000:
        return jsonify({"error": "That photo is too large."}), 422
    if not note and not image_base64:
        return jsonify({"error": "Add a reference note or a receipt photo."}), 422

    existing = UpgradeRequest.query.filter_by(tenant_id=g.tenant.id, status="PENDING").first()
    if existing:
        return jsonify({"error": "You already have a pending upgrade request awaiting review."}), 400

    req = UpgradeRequest(
        tenant_id=g.tenant.id,
        requested_plan=requested_plan,
        note=note,
        image_base64=image_base64,
    )
    db.session.add(req)
    db.session.commit()

    try:
        superadmin_email = current_app.config.get("SUPERADMIN_EMAIL")
        if superadmin_email and current_app.config.get("RESEND_API_KEY"):
            upgrade_request_submitted_email(superadmin_email, g.tenant, req)
    except EmailError as e:
        current_app.logger.error(f"upgrade_request_submitted_email failed: {e}")

    return jsonify({"data": req.to_dict()}), 201


@billing_bp.get("/upgrade-request")
@require_auth
@attach_tenant
def get_my_upgrade_request():
    """The tenant's own most recent upgrade request, if any — so the UI can show its status."""
    req = UpgradeRequest.query.filter_by(tenant_id=g.tenant.id).order_by(UpgradeRequest.created_at.desc()).first()
    return jsonify({"data": req.to_dict() if req else None}), 200


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
