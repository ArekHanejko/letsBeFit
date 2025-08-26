from flask import Flask
from flask_session import Session
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
import paypalrestsdk
import os
from itsdangerous import URLSafeTimedSerializer


def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"
    Session(app)
    csrf = CSRFProtect(app)


    # Inicjalizacja klienta PayPal API
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")  
    PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")  
    paypal_mode = os.getenv("PAYPAL_MODE", "sandbox")  
    paypalrestsdk.configure({
        "mode": paypal_mode,
        "client_id": PAYPAL_CLIENT_ID,
        "client_secret": PAYPAL_CLIENT_SECRET
    })

    app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
    app.config['MAIL_PORT'] = os.getenv("MAIL_PORT") 
    app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS")
    app.config['MAIL_USE_SSL'] = os.getenv("MAIL_USE_SSL")
    app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
    app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
    mail = Mail(app) 

    PER_PAGE = 9
    # Inicjalizacja serializera do tworzenia tokenów resetowania hasła
    serializer = URLSafeTimedSerializer(app.secret_key) #x
    
    from .routes.auth import auth_bp
    from .routes.payments import payments_bp
    from .routes.profile import profile_bp
    from .routes.workouts import workouts_bp
    from .routes.admin import admin_bp
    from .routes.reception import reception_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(workouts_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reception_bp)
    
    return app