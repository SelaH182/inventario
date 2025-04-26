# crear_base.py
from app.app import app
from app.models import db

with app.app_context():
    db.create_all()
    print("✅ Base de datos creada correctamente.")
