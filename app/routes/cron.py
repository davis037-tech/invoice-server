from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from ..extensions import db
from ..models import Invoice
from ..services.invoice_service import refresh_overdue_status
from ..services.email_service import overdue_reminder_email, EmailError

cron_bp = Blueprint("cron", __name__)

REMINDER_COOLDOWN_DAYS = 6  # don't re-remind the same invoice more than ~weekly


def _check_secret():
    expected = current_app.config.get("CRON_SECRET")
    received = request.headers.get("X-Cron-Secret")
    return bool(expected) and received == expected


@cron_bp.post("/send-overdue-reminders")
def send_overdue_reminders():
    if not _check_secret():
        return jsonify({"error": "Unauthorized"}), 401

    if not current_app.config.get("RESEND_API_KEY"):
        return jsonify({"error": "RESEND_API_KEY is not configured — reminders are disabled."}), 503

    # First, make sure status is accurate before deciding who's overdue.
    sent_invoices = Invoice.query.filter(Invoice.status == "SENT").all()
    refresh_overdue_status(sent_invoices)

    cutoff = datetime.utcnow() - timedelta(days=REMINDER_COOLDOWN_DAYS)
    candidates = Invoice.query.filter(
        Invoice.status == "OVERDUE",
        db.or_(Invoice.last_reminder_sent_at.is_(None), Invoice.last_reminder_sent_at < cutoff),
    ).all()

    sent, failed = [], []
    for invoice in candidates:
        frontend_url = current_app.config.get("FRONTEND_URL", "").rstrip("/")
        public_url = f"{frontend_url}/i.html?token={invoice.public_token}"
        try:
            overdue_reminder_email(invoice, public_url)
            invoice.last_reminder_sent_at = datetime.utcnow()
            sent.append(invoice.id)
        except EmailError as e:
            current_app.logger.error(f"Reminder failed for invoice {invoice.id}: {e}")
            failed.append(invoice.id)

    db.session.commit()
    return jsonify({
        "checked": len(candidates),
        "sent": len(sent),
        "failed": len(failed),
    }), 200
