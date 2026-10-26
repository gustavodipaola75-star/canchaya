# =========================================================================
# api.py — API JSON de CanchaYa, en el mismo servidor bajo /api.
# Responsable: [LEA] Leandro Licata.
# -------------------------------------------------------------------------
# Es la que usa static/js/reservar.js:
#   GET  /api/complejos                                  lista de complejos
#   GET  /api/complejos/<id>/disponibilidad?fecha=...    turnos y libres
#   POST /api/reservas                                   crea una reserva
# Los errores siempre vuelven como {"error": "mensaje para el usuario"}.
# Todo lo que llega se valida acá aunque el formulario ya lo valide: el
# navegador se puede saltear, el servidor no.
# =========================================================================

import re
from datetime import date

from flask import Blueprint, jsonify, request, session

from modelos import (
    db, Complejo, Reserva, CONFIRMADA, EN_ESPERA,
    horarios_del_dia, horarios_libres, validar_fecha_reservable,
)
from seguridad import limiter   # [GUS] límite de intentos

api = Blueprint("api", __name__, url_prefix="/api")

# Más que suficiente para una persona y corta a quien intente llenar los
# turnos con un script. Al pasarlo, seguridad.py responde 429 en JSON.
LIMITE_RESERVAS = "10 per minute"

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_JUGADORES, MAX_JUGADORES = 2, 14


def error(mensaje, codigo):
    return jsonify({"error": mensaje}), codigo


def complejo_a_dict(complejo):
    return {
        "id": complejo.id,
        "nombre": complejo.nombre,
        "zona": complejo.zona,
        "cantidad_canchas": complejo.cantidad_canchas,
        "caracteristicas": complejo.caracteristicas,
        "precio_hora": complejo.precio_hora,
        "imagen": complejo.imagen,
    }


def reserva_a_dict(reserva):
    return {
        "id": reserva.id,
        "id_complejo": reserva.complejo_id,
        "complejo": reserva.complejo.nombre,
        "fecha": reserva.fecha.isoformat(),
        "hora": reserva.hora,
        "jugadores": reserva.jugadores,
        "estado": reserva.estado,
    }


def leer_fecha(texto):
    """Convierte "AAAA-MM-DD" en date. Devuelve None si el formato no es válido."""
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        return None


def es_entero(valor):
    # bool es subclase de int en Python: True no tiene que pasar por un número.
    return isinstance(valor, int) and not isinstance(valor, bool)


# -------------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------------

@api.get("/complejos")
def listar_complejos():
    complejos = Complejo.select().order_by(Complejo.id)
    return jsonify([complejo_a_dict(complejo) for complejo in complejos])


@api.get("/complejos/<int:id_complejo>/disponibilidad")
def ver_disponibilidad(id_complejo):
    complejo = Complejo.get_or_none(Complejo.id == id_complejo)
    if complejo is None:
        return error("Ese complejo no existe.", 404)

    fecha = leer_fecha(request.args.get("fecha"))
    if fecha is None:
        return error("La fecha tiene que tener el formato AAAA-MM-DD.", 400)
    problema = validar_fecha_reservable(fecha)
    if problema:
        return error(problema, 400)

    horarios = horarios_del_dia(complejo, fecha)
    return jsonify({
        "horarios": horarios,
        "libres": horarios_libres(complejo, fecha, horarios),
    })


@api.post("/reservas")
@limiter.limit(LIMITE_RESERVAS)
def crear_reserva():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return error("El pedido tiene que ser un JSON con los datos de la reserva.", 400)

    # 1) Campos de texto: se recortan los espacios y se controla el largo.
    nombre = str(datos.get("nombre_cliente", "")).strip()
    email = str(datos.get("email", "")).strip()
    telefono = str(datos.get("telefono", "")).strip()
    comentarios = str(datos.get("comentarios", "")).strip()

    if not 3 <= len(nombre) <= 80:
        return error("El nombre tiene que tener entre 3 y 80 caracteres.", 400)
    if len(email) > 120 or not PATRON_EMAIL.match(email):
        return error("El email no es válido.", 400)
    if not 6 <= len(telefono) <= 30:
        return error("El teléfono tiene que tener entre 6 y 30 caracteres.", 400)
    if len(comentarios) > 500:
        return error("Los comentarios no pueden superar los 500 caracteres.", 400)

    # 2) Números: tienen que llegar como números, no como texto.
    id_complejo = datos.get("id_complejo")
    jugadores = datos.get("jugadores")
    if not es_entero(id_complejo):
        return error("Elegí un complejo.", 400)
    if not es_entero(jugadores) or not MIN_JUGADORES <= jugadores <= MAX_JUGADORES:
        return error(f"La cantidad de jugadores va de {MIN_JUGADORES} a {MAX_JUGADORES}.", 400)

    complejo = Complejo.get_or_none(Complejo.id == id_complejo)
    if complejo is None:
        return error("Ese complejo no existe.", 404)

    # 3) Fecha y hora: la hora tiene que ser uno de los turnos que quedan ese día.
    fecha = leer_fecha(datos.get("fecha"))
    if fecha is None:
        return error("La fecha tiene que tener el formato AAAA-MM-DD.", 400)
    problema = validar_fecha_reservable(fecha)
    if problema:
        return error(problema, 400)

    hora = datos.get("hora")
    horarios = horarios_del_dia(complejo, fecha)
    if hora not in horarios:
        return error("Ese horario no está disponible para la fecha elegida.", 400)

    # 4) Se crea la reserva. La transacción evita que dos pedidos simultáneos
    #    se queden con la última cancha libre.
    aceptar_espera = datos.get("aceptar_espera") is True
    with db.atomic():
        libre = hora in horarios_libres(complejo, fecha, [hora])
        if not libre and not aceptar_espera:
            return error("Ese horario ya está ocupado. Podés anotarte en la lista de "
                         "espera y, si se libera, el turno pasa a tu nombre.", 409)

        reserva = Reserva.create(
            complejo=complejo,
            usuario=session.get("usuario_id"),  # None si no inició sesión
            nombre_cliente=nombre,
            email=email,
            telefono=telefono,
            fecha=fecha,
            hora=hora,
            jugadores=jugadores,
            comentarios=comentarios,
            estado=CONFIRMADA if libre else EN_ESPERA,
        )

    return jsonify(reserva_a_dict(reserva)), 201
