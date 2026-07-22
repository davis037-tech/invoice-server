from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT

GOLD = colors.HexColor("#B08D57")
INK = colors.HexColor("#241F19")
MUTED = colors.HexColor("#8A8175")
LINE = colors.HexColor("#E7E1D6")
PANEL = colors.HexColor("#F6F1E7")
WHITE = colors.white


def _money(amount, currency):
    return f"{currency} {float(amount):,.2f}"


def _date(dt):
    return dt.strftime("%d %b %Y") if dt else "—"


def generate_invoice_pdf(invoice, supplier, public_url):
    """
    Renders an invoice to PDF bytes, matching the tan/gold design used on
    the public invoice page. `supplier` is a dict with business_name /
    business_address. Returns raw PDF bytes ready to send as a response.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=0, bottomMargin=26 * mm, leftMargin=0, rightMargin=0,
    )

    label_style = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=8,
                                  textColor=GOLD, leading=10, spaceAfter=2)
    value_style = ParagraphStyle("value", fontName="Helvetica", fontSize=10,
                                  textColor=INK, leading=13)
    muted_style = ParagraphStyle("muted", fontName="Helvetica", fontSize=9,
                                  textColor=MUTED, leading=13)
    right_label = ParagraphStyle("right_label", parent=label_style, alignment=TA_RIGHT)
    right_value = ParagraphStyle("right_value", parent=value_style, alignment=TA_RIGHT)
    right_muted = ParagraphStyle("right_muted", parent=muted_style, alignment=TA_RIGHT)
    party_name = ParagraphStyle("party_name", parent=value_style, fontName="Helvetica-Bold", alignment=TA_RIGHT)
    h1 = ParagraphStyle("h1", fontName="Times-Bold", fontSize=28, textColor=GOLD, leading=32)
    link_style = ParagraphStyle("link", fontName="Helvetica", fontSize=10, textColor=GOLD, leading=14)

    content_width = A4[0] - 28 * mm

    elements = []

    # Gold top bar
    bar = Table([[""]], colWidths=[A4[0]], rowHeights=[6])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GOLD)]))
    elements.append(bar)
    elements.append(Spacer(1, 22 * mm - 6))

    # Header: left meta, right supplier/client — built with a 2-col table for alignment
    left_col = [
        Paragraph("Invoice", h1),
        Spacer(1, 6),
        Paragraph("INVOICE", label_style), Paragraph(invoice.number, value_style),
        Spacer(1, 4),
        Paragraph("ISSUE DATE", label_style), Paragraph(_date(invoice.issue_date), value_style),
        Spacer(1, 4),
        Paragraph("DUE DATE", label_style), Paragraph(_date(invoice.due_date), value_style),
    ]

    right_col = [
        Paragraph("SUPPLIER", right_label),
        Paragraph(supplier.get("business_name") or "", party_name),
    ]
    if supplier.get("business_address"):
        right_col.append(Paragraph(supplier["business_address"], right_muted))
    right_col.append(Spacer(1, 12))
    right_col.append(Paragraph("CLIENT", right_label))
    right_col.append(Paragraph(invoice.client_name, party_name))
    right_col.append(Paragraph(invoice.client_email, right_muted))
    if invoice.client_address:
        right_col.append(Paragraph(invoice.client_address, right_muted))

    header_table = Table(
        [[left_col, right_col]],
        colWidths=[content_width * 0.5, content_width * 0.5],
    )
    header_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (0, 0), 14 * mm),
        ("RIGHTPADDING", (1, 0), (1, 0), 14 * mm),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 18))

    # Line items table
    item_header_style = ParagraphStyle("item_header", fontName="Helvetica-Bold", fontSize=8,
                                        textColor=GOLD, leading=10)
    item_header_r = ParagraphStyle("item_header_r", parent=item_header_style, alignment=TA_RIGHT)
    item_cell = ParagraphStyle("item_cell", fontName="Helvetica", fontSize=9.5, textColor=INK, leading=13)
    item_cell_r = ParagraphStyle("item_cell_r", parent=item_cell, alignment=TA_RIGHT)

    rows = [[
        Paragraph("DESCRIPTION", item_header_style),
        Paragraph("QTY", item_header_r),
        Paragraph("UNIT PRICE", item_header_r),
        Paragraph("TOTAL", item_header_r),
    ]]
    for item in invoice.items:
        line_total = float(item["quantity"]) * float(item["unit_price"])
        rows.append([
            Paragraph(item["description"], item_cell),
            Paragraph(str(item["quantity"]), item_cell_r),
            Paragraph(_money(item["unit_price"], invoice.currency), item_cell_r),
            Paragraph(_money(line_total, invoice.currency), item_cell_r),
        ])

    items_table = Table(
        rows,
        colWidths=[content_width * 0.44, content_width * 0.14, content_width * 0.21, content_width * 0.21],
        hAlign="CENTER",
    )
    items_table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, GOLD),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (0, -1), 14 * mm),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 14 * mm),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 14))

    # Totals
    totals_rows = [
        ["Subtotal", _money(invoice.subtotal, invoice.currency)],
        [f"Tax ({float(invoice.tax_rate) * 100:.2f}%)", _money(invoice.tax_amount, invoice.currency)],
        ["Total", _money(invoice.total, invoice.currency)],
    ]
    totals_table = Table(
        [[Paragraph(l, muted_style if i < 2 else ParagraphStyle("tb", parent=value_style, fontName="Helvetica-Bold")),
          Paragraph(v, right_muted if i < 2 else ParagraphStyle("tvb", parent=right_value, fontName="Helvetica-Bold"))]
         for i, (l, v) in enumerate(totals_rows)],
        colWidths=[content_width * 0.75, content_width * 0.25],
        hAlign="CENTER",
    )
    totals_table.setStyle(TableStyle([
        ("RIGHTPADDING", (-1, 0), (-1, -1), 14 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 12))

    # Highlighted due-date / amount-due bar
    amount_display = "Paid" if invoice.status.value == "PAID" else _money(invoice.total, invoice.currency)
    bar_left = [Paragraph("DUE DATE", label_style), Paragraph(_date(invoice.due_date),
                ParagraphStyle("big", fontName="Times-Bold", fontSize=15, textColor=INK))]
    bar_right = [Paragraph("AMOUNT DUE", right_label), Paragraph(amount_display,
                 ParagraphStyle("big_g", parent=right_value, fontName="Times-Bold", fontSize=15, textColor=GOLD))]
    highlight = Table([[bar_left, bar_right]], colWidths=[content_width * 0.5, content_width * 0.5], hAlign="CENTER")
    highlight.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.75, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (0, 0), 14 * mm),
        ("RIGHTPADDING", (-1, 0), (-1, 0), 14 * mm),
    ]))
    elements.append(highlight)
    elements.append(Spacer(1, 20))

    if invoice.notes:
        elements.append(Paragraph("NOTES", label_style))
        elements.append(Paragraph(invoice.notes, muted_style))
        elements.append(Spacer(1, 16))

    if public_url:
        elements.append(Paragraph(
            f'View this invoice online, pay by bank transfer, or confirm payment: '
            f'<link href="{public_url}" color="#B08D57">{public_url}</link>',
            link_style
        ))

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFillColor(PANEL)
        canvas.rect(0, 0, A4[0], 24 * mm, fill=1, stroke=0)
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica", 10)
        canvas.drawString(14 * mm, 14 * mm, "Thank you for your business.")
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(14 * mm, 8 * mm, f"Invoice {invoice.number}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
