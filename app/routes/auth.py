from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models import Tenant, User, Settings, LoginEvent
from ..schema.auth import RegisterSchema, LoginSchema

auth_bp = Blueprint("auth", __name__)


def _log_login(user):
    user.last_login_at = datetime.utcnow()
    db.session.add(LoginEvent(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        tenant_name=user.tenant.name if user.tenant else None,
    ))
    db.session.commit()


def _sync_superadmin_flag(user):
    """
    Anyone logging in or registering with the email set in SUPERADMIN_EMAIL
    gets platform-admin access. Re-checked on every login/register so
    changing the env var takes effect without a manual DB edit.
    """
    superadmin_email = current_app.config.get("SUPERADMIN_EMAIL")
    should_be_admin = bool(superadmin_email) and user.email.lower() == superadmin_email.lower()
    if user.is_superadmin != should_be_admin:
        user.is_superadmin = should_be_admin
        db.session.commit()


@auth_bp.post("/register")
def register():
    data    = request.get_json()
    schema  = RegisterSchema()
    errors  = schema.validate(data)
    if errors:
        return jsonify(errors), 400
    if User.query.filter_by(email=data["email"]).first():
      return jsonify({"error": "Email already exists"}), 409
    try:
        tenant = Tenant(name=data["org_name"], slug=data["org_name"].lower().replace(" ", "-"))
        db.session.add(tenant)
        db.session.flush()

        settings = Settings(tenant_id=tenant.id)
        db.session.add(settings)

        user = User(email=data["email"], tenant_id=tenant.id)
        user.set_password(data["password"])
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "An organization with that name already exists"}), 409

    _sync_superadmin_flag(user)

    access   = create_access_token(identity=user.id)
    refresh  = create_refresh_token(identity=user.id)
    return jsonify({"user": user.to_dict(), "tokens": { "access": access, "refresh": refresh} }), 201
    
@auth_bp.post("/login")
def login():
    data    = request.get_json()
    schema  = LoginSchema()
    errors  = schema.validate(data)
    if errors:
        return jsonify(errors), 400
    user = User.query.filter_by(email=data["email"]).first()
    if not user:
      return jsonify({"error": "Email not found"}), 401
      
    if not user.check_password(data["password"]):
      return jsonify({"error": "Invalid password"}), 401
      
    _sync_superadmin_flag(user)
    _log_login(user)
    
    access = create_access_token(identity=user.id)
    refresh = create_refresh_token(identity=user.id)
    return jsonify({"user": user.to_dict(), "tokens": {"access": access, "refresh": refresh} }), 200


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access = create_access_token(identity=user_id)
    return jsonify({"access": access}),200
    























