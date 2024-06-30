from flask import Flask, render_template, request, redirect, url_for, session, jsonify, current_app, flash
from app import app
from app.models import Transacciones, CuentaPresupuesto, Cuentas, Categorias, Presupuestos, Monedas

@app.route('/')
def inicio():
    return render_template('index.html')