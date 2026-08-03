from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app, Response
from ..extensions import db
from ..models import Invoice, User, Tenant, DemoInvoiceLog
from ..schema.invoice import PaymentProofSchema
from ..services.invoice_service import refresh_overdue_status, get_bank_transfer_details, build_invoice
from ..services.email_service import payment_proof_submitted_email, EmailError
from ..services.pdf_service import generate_invoice_pdf

public_bp = Blueprint("public", __name__)

DEMO_TENANT_SLUG = "ledger-demo"
DEMO_RATE_LIMIT_PER_IP = 5  # per 24h — backstop against scripted abuse; the real "once" limit is client-side


def _get_client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr


def _get_demo_tenant():
    tenant = Tenant.query.filter_by(slug=DEMO_TENANT_SLUG).first()
    if not tenant:
        tenant = Tenant(name="Ledger Demo", slug=DEMO_TENANT_SLUG)
        db.session.add(tenant)
        db.session.commit()
    return tenant


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

    now = datetime.utcnow()
    if invoice.first_viewed_at is None:
        invoice.first_viewed_at = now
    invoice.last_viewed_at = now
    invoice.view_count = (invoice.view_count or 0) + 1
    db.session.commit()

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


@public_bp.post("/demo-invoice")
def create_demo_invoice():
    """
    Powers the no-signup "try it" demo on the landing page. Creates a
    real invoice (so the PDF and public link are genuine, not fake data)
    under a shared demo tenant, then returns the PDF with the shareable
    link in a response header. Rate-limited by IP as a backstop — the
    actual "once per visitor" limit is enforced client-side.
    """
    ip = _get_client_ip()
    since = datetime.utcnow() - timedelta(hours=24)
    recent_count = DemoInvoiceLog.query.filter(
        DemoInvoiceLog.ip_address == ip,
        DemoInvoiceLog.created_at >= since,
    ).count()
    if recent_count >= DEMO_RATE_LIMIT_PER_IP:
        return jsonify({"error": "Too many demo invoices from this connection. Please try again later, or create a free account."}), 429

    data = request.get_json() or {}
    business_name = (data.get("business_name") or "Your Business").strip()[:200]
    client_name = (data.get("client_name") or "").strip()[:200]
    client_email = (data.get("client_email") or "").strip()[:200]
    currency = (data.get("currency") or "USD").strip()[:3].upper() or "USD"
    tax_rate = data.get("tax_rate") or 0
    items = data.get("items") or []

    if not client_name or not client_email:
        return jsonify({"error": "Add a client name and email."}), 422
    if not items or not isinstance(items, list):
        return jsonify({"error": "Add at least one line item."}), 422
    if len(items) > 20:
        return jsonify({"error": "Too many line items for the demo."}), 422

    clean_items = []
    for item in items:
        try:
            clean_items.append({
                "description": str(item.get("description") or "Item")[:200],
                "quantity": max(0, float(item.get("quantity") or 0)),
                "unit_price": max(0, float(item.get("unit_price") or 0)),
            })
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid line item data."}), 422

    try:
        tax_rate = max(0.0, min(1.0, float(tax_rate)))
    except (TypeError, ValueError):
        tax_rate = 0.0

    demo_tenant = _get_demo_tenant()
    invoice = build_invoice(demo_tenant.id, {
        "client_name": client_name,
        "client_email": client_email,
        "items": clean_items,
        "tax_rate": tax_rate,
        "currency": currency,
        "payment_terms": 30,
    })
    invoice.status = "SENT"
    db.session.add(invoice)
    db.session.add(DemoInvoiceLog(ip_address=ip))
    db.session.commit()

    frontend_url = current_app.config.get("FRONTEND_URL", "").rstrip("/")
    public_url = f"{frontend_url}/i.html?token={invoice.public_token}"
    supplier = {"business_name": business_name, "business_address": None}
    pdf_bytes = generate_invoice_pdf(invoice, supplier, public_url)

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{invoice.number}.pdf"',
            "X-Invoice-Link": public_url,
            "Access-Control-Expose-Headers": "X-Invoice-Link",
        },
    )
