from marshmallow import Schema, fields


class ClientSchema(Schema):
    name    = fields.Str(required=True)
    email   = fields.Email(required=True)
    phone   = fields.Str(load_default=None)
    address = fields.Str(load_default=None)
