import hmac
from flask import Blueprint, request, jsonify, current_app
from ..extensions import db
from ..models import Invoice
from ..services.flutterwave import verify_transaction, FlutterwaveError

billing_bp = Blueprint("billing", __name__)


def _signature_is_valid():
    """
    Flutterwave signs webhooks with a secret hash you configure on your
    dashboard, sent back as a request header. Different doc generations
    show this header as either 'verif-hash' or 'flutterwave-signature';
    we accept either name and compare against FLW_WEBHOOK_SECRET.
    Uses hmac.compare_digest to avoid timing attacks on the comparison.
    """
    expected = current_app.config.get("FLW_WEBHOOK_SECRET") or ""
    received = request.headers.get("verif-hash") or request.headers.get("flutterwave-signature") or ""
    if not expected or not received:
        return False
    return hmac.compare_digest(received, expected)


@billing_bp.post("/webhook")
def flutterwave_webhook():
    if not _signature_is_valid():
        # Not a genuine Flutterwave request — discard.
        return jsonify({"error": "Invalid signature"}), 401

    payload = request.get_json(silent=True) or {}
    data = payload.get("data", {})
    transaction_id = data.get("id")

    if not transaction_id:
        # Acknowledge with 200 so Flutterwave doesn't retry a malformed
        # event forever, but there's nothing actionable here.
        return jsonify({"received": True}), 200

    # NEVER trust the webhook payload's amount/status directly — always
    # re-query Flutterwave's API for the authoritative transaction state
    # before changing anything in the database.
    try:
        verified = verify_transaction(transaction_id)
    except FlutterwaveError as e:
        current_app.logger.error(f"Flutterwave verification failed: {e}")
        # Return 200 anyway: Flutterwave will retry on non-2xx, and a
        # transient network error on our end shouldn't trigger endless
        # retries for an event we can just re-check later if needed.
        return jsonify({"received": True}), 200

    tx_ref = verified.get("tx_ref")  # this is the invoice.id we set as tx_ref
    status = verified.get("status")
    amount = verified.get("amount")
    currency = verified.get("currency")

    invoice = Invoice.query.get(tx_ref)
    if not invoice:
        return jsonify({"received": True}), 200

    # Idempotency: if we've already marked this invoice paid, don't
    # reprocess (Flutterwave may send the same event more than once).
    if invoice.status.value == "PAID":
        return jsonify({"received": True}), 200

    if (
        status == "successful"
        and float(amount) >= float(invoice.total)
        and currency == invoice.currency
    ):
        invoice.status = "PAID"
        db.session.commit()
    elif status == "failed":
        # Leave status as SENT — a failed attempt doesn't cancel the invoice,
        # the customer may retry payment.
        pass

    return jsonify({"received": True}), 200


@billing_bp.get("/invoices/<invoice_id>/status")
def get_payment_status(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404
    return jsonify({"status": invoice.status.value}), 200
