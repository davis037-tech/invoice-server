from flask import Flask 
from .extensions import db, jwt, migrate, cors
from .db_bootstrap import ensure_invoice_columns
from .routes.auth import auth_bp 
from .routes.clients import clients_bp 
from .routes.invoices import invoices_bp 
from .routes.billing import billing_bp  
from .routes.public import public_bp
from .routes.settings import settings_bp

def create_app():
    app = Flask(__name__) 
    app.config.from_object("app.config.Config")
    
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/v1/*": {"origins": app.config["CORS_ORIGINS"]}})

    ensure_invoice_columns(app, db)
    
    app.register_blueprint(auth_bp,    url_prefix="/v1/auth")
    app.register_blueprint(clients_bp,    url_prefix="/v1/clients")
    app.register_blueprint(invoices_bp,    url_prefix="/v1/invoices")
    app.register_blueprint(public_bp,     url_prefix="/v1/public")
    app.register_blueprint(billing_bp,     url_prefix="/v1/billing")
    app.register_blueprint(settings_bp,    url_prefix="/v1/settings")
    
    return app
    






















