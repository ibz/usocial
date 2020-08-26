from functools import wraps

from flask import redirect, url_for
from flask_jwt_extended import verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError

from mureader import jwt
from mureader import models

@jwt.claims_verification_failed_loader
def no_jwt():
    return redirect(url_for('user.login'))

@jwt.expired_token_loader
def jwt_token_expired():
    return redirect(url_for('user.refresh_jwt'))

@jwt.user_loader_callback_loader
def load_user(email):
    return models.User.query.filter_by(email=email).first()

def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except NoAuthorizationError:
            return no_jwt()
        return fn(*args, **kwargs)
    return wrapper
