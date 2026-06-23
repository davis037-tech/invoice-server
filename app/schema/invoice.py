from marshmallow import Schema, fields, validate


class LineItemSchema(Schema):
    description  = fields.Str(required=True)
    quantity     = fields.Float(required=True, validate=validate.Range(min=0))
    unit_price   = fields.Float(required=True, validate=validate.Range(min=0))


class InvoiceSchema(Schema):
    client_id      = fields.Str(load_default=None)
    client_name    = fields.Str(required=True)
    client_email   = fields.Email(required=True)
    client_address = fields.Str(load_default=None)
    items          = fields.List(fields.Nested(LineItemSchema), required=True)
    tax_rate       = fields.Float(load_default=0.0)
    currency       = fields.Str(load_default="USD")
    payment_terms  = fields.Int(load_default=30)
    due_date       = fields.DateTime(load_default=None)
    notes          = fields.Str(load_default=None)
