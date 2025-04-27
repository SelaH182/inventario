from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)


class Trazabilidad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # quién hizo la acción
    accion = db.Column(db.String(100), nullable=False)  # qué hizo ('Inicio de sesión', etc.)
    descripcion = db.Column(db.String(250))  # detalle
    fecha_hora = db.Column(db.DateTime, default=db.func.now())  # cuándo fue


class Equipo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_equipo = db.Column(db.String(50))
    nombre_equipo = db.Column(db.String(100))
    serie = db.Column(db.String(100))
    marca = db.Column(db.String(100))
    modelo = db.Column(db.String(100))
    ubicacion = db.Column(db.String(100))
    
    mantenimiento_preventivo = db.Column(db.Numeric(precision=12, scale=2))
    fecha_mantenimiento_preventivo = db.Column(db.String(50))
    responsable_mantenimiento_preventivo = db.Column(db.String(100))
    fecha_proximo_mantenimiento_preventivo = db.Column(db.String(50))
    
    mantenimiento_correctivo = db.Column(db.Numeric(precision=12, scale=2))
    fecha_mantenimiento_correctivo = db.Column(db.String(50))
    responsable_mantenimiento_correctivo = db.Column(db.String(100))
    fecha_nuevo_mantenimiento_correctivo = db.Column(db.String(50))
    
    registro_invima = db.Column(db.String(100))
    calibracion = db.Column(db.String(100))
    observaciones = db.Column(db.Text)
    hoja_vida = db.Column(db.String(200))
    manuales = db.Column(db.String(200))
    factura = db.Column(db.String(200))
    insumos = db.Column(db.Text)
    responsable_compra_insumos = db.Column(db.String(100))
    costo_insumo = db.Column(db.Numeric(precision=12, scale=2))
    fecha_compra_insumos = db.Column(db.String(50))

    @staticmethod
    def calcular_color(fecha_str):
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return 'Blanco'  # Fecha inválida o vacía
        
        hoy = datetime.today().date()
        if fecha < hoy:
            return 'Rojo'
        elif (fecha - hoy).days <= 15:
            return 'Amarillo'
        else:
            return 'Verde'

    @property
    def color_preventivo(self):
        return self.calcular_color(self.fecha_proximo_mantenimiento_preventivo)

    @property
    def color_correctivo(self):
        return self.calcular_color(self.fecha_nuevo_mantenimiento_correctivo)