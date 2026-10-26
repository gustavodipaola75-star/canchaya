# =========================================================================
# app.py — Servidor web Flask de CanchaYa.
# Responsable: [LEA] Leandro Licata.
# -------------------------------------------------------------------------
# Crea la app, prepara la base de datos (modelos.py), registra la API
# (api.py, bajo /api) y sirve las páginas del sitio (plantillas Jinja en
# templates/) junto con los archivos estáticos (static/).
# Las demás partes se suman como blueprints, cada una en su archivo.
# =========================================================================

import os
import secrets

from flask import Flask, render_template

from api import api
from cuentas import cuentas   # [FED] registro, login y logout
from mis_reservas import mis_reservas   # [FED] Mis reservas
from modelos import db, iniciar_base, Complejo

from seguridad import iniciar_seguridad   # [GUS] CSRF, CSP, limiter...

app = Flask(__name__)

# La clave firma la cookie de sesión y los tokens CSRF. En Render se carga
# como variable de entorno SECRET_KEY. Si falta (en la PC de cada uno), se
# genera una al azar: funciona igual, pero las sesiones se pierden al reiniciar.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

iniciar_seguridad(app)

iniciar_base()
app.register_blueprint(api)
app.register_blueprint(cuentas)
app.register_blueprint(mis_reservas)


# Cada pedido abre la conexión a la base y la cierra al terminar.
@app.before_request
def abrir_conexion():
    db.connect(reuse_if_open=True)


@app.teardown_request
def cerrar_conexion(excepcion):
    if not db.is_closed():
        db.close()


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/complejos")
def complejos():
    # [GON] arma las tarjetas con esta lista en complejos.html.
    lista = Complejo.select().order_by(Complejo.id)
    return render_template("complejos.html", complejos=lista)


@app.route("/reservar")
def reservar():
    return render_template("reservar.html")


@app.route("/nosotros")
def nosotros():
    return render_template("nosotros.html")


if __name__ == "__main__":
    app.run(debug=True)
