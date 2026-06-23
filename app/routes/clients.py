from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..models import Client
from ..schema.client import ClientSchema
from ..middleware.auth import require_auth, attach_tenant

clients_bp = Blueprint("clients", __name__)


@clients_bp.get("/")
@require_auth
@attach_tenant
def get_client():
    client = Client.query.filter_by(tenant_id=g.tenant.id).all()
    return jsonify({
        "data": [c.to_dict() for c in client],
        "meta": {"total": len(client)}
    }), 200


@clients_bp.post("/")
@require_auth
@attach_tenant
def add_client():
    data = request.get_json()
    schema = ClientSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify(errors), 422
    client = Client(tenant_id=g.tenant.id, **data)
    db.session.add(client)
    db.session.commit()
    return jsonify({
        "data": [client.to_dict()],
        "meta": {"total": 1}
    }), 201


@clients_bp.get("/<client_id>")
@require_auth
@attach_tenant
def get_client_by_id(client_id):
    client = Client.query.filter_by(id=client_id, tenant_id=g.tenant.id).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404
    return jsonify({"data": client.to_dict()}), 200


@clients_bp.put("/<client_id>")
@require_auth
@attach_tenant
def update_client(client_id):
    client = Client.query.filter_by(id=client_id, tenant_id=g.tenant.id).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404
    data = request.get_json()
    schema = ClientSchema(partial=True)
    errors = schema.validate(data)
    if errors:
        return jsonify(errors), 422
    for key, value in data.items():
        setattr(client, key, value)
    db.session.commit()
    return jsonify({"data": client.to_dict()}), 200


@clients_bp.delete("/<client_id>")
@require_auth
@attach_tenant
def delete_client(client_id):
    client = Client.query.filter_by(id=client_id, tenant_id=g.tenant.id).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404
    db.session.delete(client)
    db.session.commit()
    return "", 204
