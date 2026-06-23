"""
Thin wrapper around the Flutterwave v3 API.

Docs:
- Create payment:  https://developer.flutterwave.com/docs/flutterwave-standard-1
- Verify txn:       https://developer.flutterwave.com/v3.0/docs/transaction-verification
- Webhooks:         https://developer.flutterwave.com/docs/webhooks
"""
import requests
from flask import current_app

BASE_URL = "https://api.flutterwave.com/v3"


class FlutterwaveError(Exception):
    pass


def _headers():
    secret_key = current_app.config["FLW_SECRET_KEY"]
    return {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }


def create_payment_link(tx_ref, amount, currency, customer_email, customer_name, redirect_url):
    """
    Creates a hosted Flutterwave checkout link for an invoice.
    Returns the checkout URL (data.link), or raises FlutterwaveError.
    """
    payload = {
        "tx_ref": tx_ref,
        "amount": str(amount),
        "currency": currency,
        "redirect_url": redirect_url,
        "customer": {
            "email": customer_email,
            "name": customer_name,
        },
        "customizations": {
            "title": "Invoice Payment",
        },
    }
    try:
        resp = requests.post(f"{BASE_URL}/payments", json=payload, headers=_headers(), timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise FlutterwaveError(f"Failed to create payment link: {e}") from e

    body = resp.json()
    if body.get("status") != "success":
        raise FlutterwaveError(f"Flutterwave error: {body.get('message')}")
    return body["data"]["link"]


def verify_transaction(transaction_id):
    """
    Re-queries Flutterwave for the authoritative status of a transaction.
    Always call this before crediting an invoice from a webhook —
    never trust the webhook payload alone.
    Returns the 'data' dict from Flutterwave's response.
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/transactions/{transaction_id}/verify",
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise FlutterwaveError(f"Failed to verify transaction: {e}") from e

    body = resp.json()
    if body.get("status") != "success":
        raise FlutterwaveError(f"Flutterwave error: {body.get('message')}")
    return body["data"]
