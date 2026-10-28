# =========================================================================
# cuentas.py — Registro, inicio y cierre de sesión de CanchaYa.
# Responsable: [FED] Federico Cabrera.
# -------------------------------------------------------------------------
# Blueprint con las rutas /registro, /login y /logout. Usa el modelo Usuario
# de modelos.py ([LEA]) sin agregarle campos. Al iniciar sesión guarda el id
# en session["usuario_id"], que es la clave que lee api.py para asociar la
# reserva al usuario. Las claves se guardan con hash (werkzeug, viene con
# Flask), nunca en texto plano.
# Los formularios llevan token CSRF (flask-wtf) y se valida acá mismo, sin
# depender de que CSRFProtect global esté activo ([GUS] lo activa aparte).
# =========================================================================

import re
from urllib.parse import urlparse

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash, g,
)
from flask_wtf.csrf import generate_csrf, validate_csrf
from peewee import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import ValidationError

from modelos import Usuario
from seguridad import limiter

cuentas = Blueprint("cuentas", __name__)

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")  # el mismo criterio que api.py
LARGO_MINIMO_CLAVE = 8


@cuentas.app_context_processor
def datos_para_plantillas():
    """Deja disponibles en todas las plantillas el usuario logueado y
    csrf_token() (que base.html usa en <meta name="csrf-token">)."""
    return {"usuario_actual": g.get("usuario"), "csrf_token": generate_csrf}


@cuentas.before_app_request
def cargar_usuario():
    """Busca el usuario de la sesión una vez por pedido. Si el id ya no
    existe (por ejemplo, se borró canchaya.db), limpia la sesión."""
    g.usuario = None
    id_usuario = session.get("usuario_id")
    if id_usuario is not None:
        g.usuario = Usuario.get_or_none(Usuario.id == id_usuario)
        if g.usuario is None:
            session.pop("usuario_id", None)


def csrf_valido():
    try:
        validate_csrf(request.form.get("csrf_token"))
        return True
    except ValidationError:
        return False


def destino_seguro(destino):
    """Solo se permite volver a rutas internas (evita redirecciones abiertas)."""
    if destino and destino.startswith("/") and not urlparse(destino).netloc:
        return destino
    return url_for("inicio")


def iniciar_sesion(usuario):
    session.clear()                      # evita reutilizar una sesión anterior
    session["usuario_id"] = usuario.id   # clave acordada con [LEA] en api.py


@cuentas.route("/registro", methods=["GET", "POST"])
@limiter.limit("3 per minute", methods=["POST"])
def registro():
    if g.usuario:
        return redirect(url_for("inicio"))
    errores, datos = [], {"nombre": "", "email": ""}
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        clave = request.form.get("clave", "")
        clave2 = request.form.get("clave2", "")
        datos = {"nombre": nombre, "email": email}

        if not csrf_valido():
            errores.append("El formulario venció. Recargá la página e intentá de nuevo.")
        if len(nombre) < 3:
            errores.append("El nombre debe tener al menos 3 caracteres.")
        if not PATRON_EMAIL.match(email):
            errores.append("Ingresá un email válido.")
        if len(clave) < LARGO_MINIMO_CLAVE:
            errores.append(f"La contraseña debe tener al menos {LARGO_MINIMO_CLAVE} caracteres.")
        if clave != clave2:
            errores.append("Las contraseñas no coinciden.")

        if not errores:
            try:
                usuario = Usuario.create(nombre=nombre, email=email,
                                         clave_hash=generate_password_hash(clave))
            except IntegrityError:       # email es unique en el modelo
                errores.append("Ya existe una cuenta con ese email.")
            else:
                iniciar_sesion(usuario)
                flash(f"¡Bienvenido, {usuario.nombre}! Tu cuenta quedó creada.", "exito")
                return redirect(url_for("inicio"))
    return render_template("registro.html", errores=errores, datos=datos)


@cuentas.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if g.usuario:
        return redirect(url_for("inicio"))
    errores, email = [], ""
    siguiente = request.values.get("siguiente", "")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        clave = request.form.get("clave", "")
        if not csrf_valido():
            errores.append("El formulario venció. Recargá la página e intentá de nuevo.")
        else:
            usuario = Usuario.get_or_none(Usuario.email == email)
            # Mismo mensaje en los dos casos: no revela qué emails existen.
            if usuario is None or not check_password_hash(usuario.clave_hash, clave):
                errores.append("Email o contraseña incorrectos.")
            else:
                iniciar_sesion(usuario)
                flash(f"Hola, {usuario.nombre}. Iniciaste sesión.", "exito")
                return redirect(destino_seguro(siguiente))
    return render_template("login.html", errores=errores, email=email, siguiente=siguiente)


@cuentas.route("/logout", methods=["POST"])
def logout():
    # Por POST (con CSRF) para que un link externo no pueda cerrar la sesión.
    if csrf_valido():
        session.clear()
        flash("Cerraste sesión.", "exito")
    return redirect(url_for("inicio"))
