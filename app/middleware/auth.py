from functools import wraps
from flask import jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from ..models import User


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 401
        g.current_user = user
        return fn(*args, **kwargs)
    return wrapper


def attach_tenant(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(g, "current_user", None):
            return jsonify({"error": "Authentication required"}), 401
        g.tenant = g.current_user.tenant
        return fn(*args, **kwargs)
    return wrapper


def require_superadmin(fn):
    """
    Gates platform-admin routes (viewing/managing all tenants). Must be
    stacked after @require_auth so g.current_user is already set.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = getattr(g, "current_user", None)
        if not user or not user.is_superadmin:
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper
