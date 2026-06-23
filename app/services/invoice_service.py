import secrets
from uuid import uuid4
from datetime import datetime, timedelta

from ..models import Invoice, Client


def _next_invoice_number(tenant_id):
    """Generate the next sequential invoice number for a tenant, e.g. INV-0001."""
    count = Invoice.query.filter_by(tenant_id=tenant_id).count()
    return f"INV-{count + 1:04d}"


def calculate_totals(items, tax_rate):
    """items: list of dicts with quantity + unit_price. Returns (subtotal, tax_amount, total)."""
    subtotal = sum(item["quantity"] * item["unit_price"] for item in items)
    tax_amount = subtotal * tax_rate
    total = subtotal + tax_amount
    return round(subtotal, 2), round(tax_amount, 2), round(total, 2)


def build_invoice(tenant_id, data):
    """Build (but do not commit) an Invoice from validated schema data."""
    items = data["items"]
    tax_rate = data.get("tax_rate", 0.0)
    subtotal, tax_amount, total = calculate_totals(items, tax_rate)

    client_name = data.get("client_name")
    client_email = data.get("client_email")
    client_address = data.get("client_address")

    # If a client_id was given, snapshot its details onto the invoice
    # so the invoice stays accurate even if the client record changes later.
    client_id = data.get("client_id")
    if client_id:
        client = Client.query.filter_by(id=client_id, tenant_id=tenant_id).first()
        if client:
            client_name = client_name or client.name
            client_email = client_email or client.email
            client_address = client_address or client.address

    issue_date = datetime.utcnow()
    due_date = data.get("due_date")
    payment_terms = data.get("payment_terms", 30)
    if not due_date:
        due_date = issue_date + timedelta(days=payment_terms)

    # Generate the id up front (rather than relying on the model's default)
    # so we can also use it as a globally-unique Flutterwave tx_ref later.
    invoice_id = str(uuid4())

    invoice = Invoice(
        id=invoice_id,
        tenant_id=tenant_id,
        client_id=client_id,
        client_name=client_name,
        client_email=client_email,
        client_address=client_address,
        number=_next_invoice_number(tenant_id),
        items=items,
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total=total,
        currency=data.get("currency", "USD"),
        issue_date=issue_date,
        due_date=due_date,
        payment_terms=payment_terms,
        notes=data.get("notes"),
        public_token=secrets.token_urlsafe(24),
    )
    return invoice


def get_or_create_payment_link(invoice):
    """
    Returns the invoice's existing payment_url if already generated,
    otherwise requests a new one from Flutterwave and returns it.
    Caller is responsible for committing the session afterward.
    """
    from .flutterwave import create_payment_link
    from flask import current_app

    if invoice.payment_url:
        return invoice.payment_url

    link = create_payment_link(
        tx_ref=invoice.id,
        amount=float(invoice.total),
        currency=invoice.currency,
        customer_email=invoice.client_email,
        customer_name=invoice.client_name,
        redirect_url=f"{current_app.config['FRONTEND_URL']}/invoices/{invoice.public_token}",
    )
    invoice.payment_url = link
    return link
