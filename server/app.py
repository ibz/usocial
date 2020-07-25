from flask import Flask, redirect, url_for
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from config import BaseConfig

app = Flask(__name__)

app.config.from_object(BaseConfig)

CORS(app)
CSRFProtect(app)

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
jwt = JWTManager(app)
