from flask import Flask 
from .extensions import db, jwt, migrate, cors
from .routes.auth import auth_bp 
from .routes.clients import clients_bp 
from .routes.invoices import invoices_bp 
from .routes.billing import billing_bp  
from .routes.public import public_bp

def create_app():
    app = Flask(__name__) 
    app.config.from_object("app.config.Config")
    
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/v1/*": {"origins": app.config["CORS_ORIGINS"]}})
    
    app.register_blueprint(auth_bp,    url_prefix="/v1/auth")
    app.register_blueprint(clients_bp,    url_prefix="/v1/clients")
    app.register_blueprint(invoices_bp,    url_prefix="/v1/invoices")
    app.register_blueprint(public_bp,     url_prefix="/v1/public")
    app.register_blueprint(billing_bp,     url_prefix="/v1/billing")

    with app.app_context():
        # Creates tables if they don't exist yet. Fine for a free-tier
        # test deploy with no real users; switch to proper Alembic
        # migrations (flask db init / migrate / upgrade) before this
        # ever holds real customer data, since create_all() can't
        # safely evolve an existing schema later.
        db.create_all()

    return app
    






















