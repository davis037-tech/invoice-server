import requests
from flask import current_app


class EmailError(Exception):
    pass


def send_email(to, subject, html):
    """
    Sends an email via Resend's REST API. Requires RESEND_API_KEY to be
    set — if it isn't, this raises rather than silently doing nothing,
    so a misconfiguration surfaces immediately instead of just quietly
    never sending reminders.
    """
    api_key = current_app.config.get("RESEND_API_KEY")
    if not api_key:
        raise EmailError("RESEND_API_KEY is not configured.")

    from_email = current_app.config.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"from": from_email, "to": [to], "subject": subject, "html": html},
        timeout=10,
    )
    if resp.status_code >= 400:
        raise EmailError(f"Resend API error ({resp.status_code}): {resp.text}")
    return resp.json()


def overdue_reminder_email(invoice, public_url):
    subject = f"Reminder: Invoice {invoice.number} is overdue"
    html = f"""
      <p>Hi {invoice.client_name},</p>
      <p>This is a friendly reminder that invoice <strong>{invoice.number}</strong>
      for <strong>{invoice.total} {invoice.currency}</strong> was due on
      {invoice.due_date.strftime('%d %b %Y') if invoice.due_date else 'the agreed date'}
      and is still outstanding.</p>
      <p><a href="{public_url}">View invoice and payment details</a></p>
      <p>If you've already paid, please disregard this note — or submit your
      payment confirmation at the link above so we can mark it received.</p>
    """
    return send_email(invoice.client_email, subject, html)
