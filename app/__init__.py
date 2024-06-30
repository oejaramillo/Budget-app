import os 
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)

# Base de datos
db = SQLAlchemy(app)
migrate = Migrate(app, db) # para cambios y migraciones

from app import routes