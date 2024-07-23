from app import db
from datetime import datetime

class Transacciones(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=db.func.current_timestamp())
    monto = db.Column(db.Float, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    cuenta_id = db.Column(db.Integer, db.ForeignKey('cuentas.id'), nullable=False)
    presupuesto_id = db.Column(db.Integer, db.ForeignKey('presupuestos.id'))
    descripcion = db.Column(db.String)
    moneda_id = db.Column(db.String, db.ForeignKey('monedas.id'), nullable=False)

    categoria = db.relationship('Categorias', backref=db.backref('transacciones', lazy=True))
    cuenta = db.relationship('Cuentas', backref=db.backref('transacciones', lazy=True))
    presupuesto = db.relationship('Presupuestos', backref=db.backref('transacciones', lazy=True))
    moneda = db.relationship('Monedas', backref=db.backref('transacciones', lazy=True))

class CuentaPresupuesto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    presupuesto_id = db.Column(db.Integer, db.ForeignKey('presupuestos.id'), nullable=False)
    cuenta_id = db.Column(db.Integer, db.ForeignKey('cuentas.id'), nullable=False)

    presupuesto = db.relationship('Presupuestos', backref=db.backref('cuenta_presupuestos', lazy=True))
    cuenta = db.relationship('Cuentas', backref=db.backref('cuenta_presupuestos', lazy=True))

class Cuentas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=db.func.current_timestamp())
    saldo = db.Column(db.Float, nullable=False)
    moneda_id = db.Column(db.Integer, db.ForeignKey('monedas.id'), nullable=False)
    institucion = db.Column(db.String)
    numero_oficial = db.Column(db.String)
    fecha_finalizacion = db.Column(db.DateTime)

    moneda = db.relationship('Monedas', backref=db.backref('cuentas', lazy=True))

class Categorias(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    descripcion = db.Column(db.String)
    presupuesto_id = db.Column(db.Integer, db.ForeignKey('presupuestos.id'))

    presupuesto = db.relationship('Presupuestos', backref=db.backref('categorias', lazy=True))

class Presupuestos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    monto_max = db.Column(db.Float, nullable=False)
    monto_min = db.Column(db.Float, nullable=False)
    moneda_id = db.Column(db.Integer, db.ForeignKey('monedas.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    fecha_finalizacion = db.Column(db.DateTime)

    moneda = db.relationship('Monedas', backref=db.backref('presupuestos', lazy=True))

class Monedas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    codigo = db.Column(db.String, nullable=False)
    tipo_cambio = db.Column(db.Float, nullable=False)
    principal = db.Column(db.Boolean, nullable=False)
