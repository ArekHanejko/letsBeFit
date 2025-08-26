from .auth import auth_bp
from .payments import payments_bp
from .profile import profile_bp
from .workouts import workouts_bp
from .admin import admin_bp
from .reception import reception_bp

__all__ = [
    'auth_bp',
    'payments_bp', 
    'profile_bp',
    'workouts_bp',
    'admin_bp',
    'reception_bp'
]