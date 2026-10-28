# CanchaYa

CanchaYa es una plataforma ficticia diseñada para facilitar la reserva de canchas de fútbol 5 en Mendoza.

Proyecto de **Zonda Bytes** para Práctica Profesionalizante I — Tecnicatura Superior en
Desarrollo de Software, Instituto Superior Manuel Belgrano, 2026.

## Descripción del Proyecto
Este proyecto fue desarrollado como parte de la práctica profesional para facilitar a los usuarios la búsqueda de complejos deportivos, la consulta de horarios disponibles y la reserva de turnos de manera ágil y sencilla.

En el primer parcial fue un prototipo estático (HTML, CSS y JS), que quedó guardado en el
tag [`parcial-1`](https://github.com/gustavodipaola75-star/canchaya/tree/parcial-1). En el segundo parcial el sitio pasa a ser servido
por un servidor web Flask con base de datos.

## Funcionalidades principales
- **Inicio:** Sección destacada con llamado a la acción.
- **Reservas:** Formulario interactivo para gestionar turnos.
- **Complejos:** Listado de complejos deportivos disponibles.
- **Nosotros:** Información sobre el equipo de desarrollo.
- **Diseño Responsive:** Adaptabilidad a dispositivos móviles con menú de navegación colapsable.
- **Seguridad:** Protección contra CSRF, XSS, clickjacking y fuerza bruta (ver la sección [Seguridad](#seguridad)).

## Equipo de Desarrollo
- Federico Cabrera (Frontend / HTML)
- Leandro Licata (Frontend / Formularios)
- Gonzalo Tapia (Contenido / UX)
- Gustavo Di Paola (Documentación / Git)

## Tecnologías Utilizadas
- HTML5 con plantillas Jinja
- CSS3 (con CSS Grid, Flexbox y Variables CSS)
- JavaScript (menú hamburguesa y conexión del formulario con la API)
- Python 3.10+ con Flask (servidor web)
- peewee (ORM), flask-wtf y flask-limiter (seguridad), listados en `requirements.txt`

## Estructura

```
app.py            # Servidor Flask: rutas de las páginas
modelos.py        # Base de datos (peewee + SQLite) y lógica de horarios
api.py            # API JSON bajo /api (complejos, disponibilidad, reservas)
seguridad.py      # Medidas de seguridad: CSRF, cabeceras, límite de intentos
templates/        # Plantillas Jinja (base.html + una por página)
static/css/       # Estilos
static/js/        # Lógica de cliente
static/assets/    # Imágenes
requirements.txt  # Dependencias de Python
```

## Cómo se ejecuta

Las dependencias se instalan en un entorno virtual dentro del proyecto (la carpeta `.venv`
está en el `.gitignore`). En PowerShell, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

El sitio queda en `http://localhost:5000`. La primera vez se crea sola la base `canchaya.db`
con los complejos de ejemplo; para empezar de cero, alcanza con borrarla. Ya no se abre con Live Server: las páginas son
plantillas Jinja y solo se ven bien servidas por Flask.

## Seguridad

Todas las medidas están en `seguridad.py`, que se activa con una sola llamada,
`iniciar_seguridad(app)`, desde `app.py` (después de definir la `SECRET_KEY`). Los objetos
`csrf` y `limiter` quedan disponibles para importar desde otros archivos
(`from seguridad import limiter`).

| Medida | Protege contra | Cómo está implementada |
|---|---|---|
| Tokens CSRF | Formularios o pedidos falsos enviados desde otro sitio | `flask-wtf` (`CSRFProtect`). Los formularios llevan el campo oculto `csrf_token` y `reservar.js` envía el token en la cabecera `X-CSRFToken` |
| Content-Security-Policy | XSS (ejecución de scripts inyectados) | Solo se permiten scripts y estilos del propio sitio, más Google Fonts para tipografías |
| `X-Frame-Options: DENY` y `frame-ancestors 'none'` | Clickjacking (el sitio dentro de un iframe ajeno) | Cabeceras agregadas a todas las respuestas |
| Otras cabeceras | Sniffing de contenido y filtrado de datos | `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Permissions-Policy` (solo se permite el micrófono, para la búsqueda por voz) |
| Límite de intentos | Fuerza bruta en login, registro y reservas | `flask-limiter`, con un límite por IP en cada ruta sensible |
| Cookie de sesión | Robo o uso indebido de la sesión | `HttpOnly`, `SameSite=Lax` y `Secure` (solo en Render, que usa https) |
| Escape de plantillas | XSS por datos del usuario | Jinja escapa automáticamente el texto que se muestra en las páginas |
| `SECRET_KEY` | Falsificación de sesiones y tokens | Se carga como variable de entorno en Render; en local se genera una al azar |

### Límites de intentos

Se aplican con `@limiter.limit(...)` debajo del decorador de cada ruta:

| Ruta | Límite |
|---|---|
| `POST /login` | 5 por minuto |
| `POST /registro` | 3 por minuto |
| `POST /api/reservas` | 10 por minuto |

Al superar el límite, las rutas de /api responden con un error 429 en JSON. En el resto de las páginas (/login y /registro) el sitio vuelve a la página anterior y muestra el mensaje “Demasiados intentos, esperá un minuto”. El límite se cuenta por IP y solo en los pedidos POST, así que mirar o recargar el formulario no gasta intentos.

### Errores de seguridad

- **Token CSRF inválido o ausente:** respuesta 400. En `/api` devuelve JSON con el motivo
  del error; en las demás páginas muestra un mensaje y vuelve a la página anterior.
- **Render:** como los pedidos llegan a través de un proxy, `ProxyFix` hace que el límite de
  intentos se aplique a la IP real de cada usuario y no a todos juntos.

### Pruebas realizadas

| Medida | Prueba | Resultado |
|---|---|---|
| Cabeceras | `curl.exe -I http://localhost:5000/` | Aparecen las cinco cabeceras de seguridad |
| CSP | Revisión de la consola (F12) en todas las páginas, con y sin sesión | Sin errores de Content Security Policy |
| Clickjacking | Un `.html` suelto con `<iframe src="http://localhost:5000">` | El navegador se niega a mostrar el sitio |
| CSRF | Cambiar el `csrf_token` del login y borrar el `<meta name="csrf-token">` en `/reservar` | Mensaje de error en ambos casos |
| Fuerza bruta | 6 logins fallidos seguidos en /login | Los primeros 5 muestran “Email o contraseña incorrectos” y el 6º muestra “Demasiados intentos, esperá un minuto” |
| Fuerza bruta | 4 registros inválidos seguidos en /registro | Los primeros 3 muestran “Las contraseñas no coinciden” y el 4º muestra el mensaje de bloqueo |
| XSS | Registrarse con el nombre `<script>alert(1)</script>` | Se muestra como texto, sin ejecutarse |
| Sesiones | Reservar y verla en Mis reservas; salir y entrar a `/mis-reservas` | Pide iniciar sesión |
| Búsqueda por voz | Usar el micrófono con la cabecera `Permissions-Policy` activa | Sigue funcionando |