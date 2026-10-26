/* =========================================================================
   buscador.js — Buscador y filtros de la página Complejos.
   Responsable: [GON] Gonzalo Tapia (Contenido / UX).
   -------------------------------------------------------------------------
   Lee los data-* de cada tarjeta (los arma complejos.html desde la base) y,
   cada vez que cambia un filtro, muestra solo las que cumplen y las ordena.
   Todo pasa en el navegador: no hace pedidos al servidor.
   ========================================================================= */

// 1) Buscamos en la página los elementos con los que vamos a trabajar.
const grilla      = document.querySelector(".grilla-complejos");
const formulario  = document.querySelector("#buscador");
const campoTexto  = document.querySelector("#filtro-texto");
const selectZona  = document.querySelector("#filtro-zona");
const rangoPrecio = document.querySelector("#filtro-precio");
const valorPrecio = document.querySelector("#valor-precio");
const selectOrden = document.querySelector("#filtro-orden");
const resumen     = document.querySelector("#resumen");
const avisoVacio  = document.querySelector("#sin-resultados");

// 2) Funciones de ayuda.

// Pasa a minúsculas y saca las tildes, para que "guaymallen" encuentre
// "Guaymallén" y "TECHADAS" encuentre "techadas".
// normalize("NFD") separa la letra de su tilde ("é" → "e" + "´") y el
// replace borra esas tildes sueltas.
const normalizar = (texto) =>
  texto.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();

// 20000 → "20.000" (formato argentino).
const formatearPrecio = (numero) => numero.toLocaleString("es-AR");

// 3) Leemos las tarjetas UNA sola vez y armamos una lista de objetos.
//    Así, al filtrar, comparamos datos y no tenemos que leer el HTML cada vez.
const complejos = [...grilla.querySelectorAll(".complejo")].map((elemento, posicion) => ({
  elemento,                                   // la tarjeta en sí, para mostrarla u ocultarla
  posicion,                                   // orden original, para "Sin orden"
  nombre: normalizar(elemento.dataset.nombre),
  zona: elemento.dataset.zona,
  caracteristicas: normalizar(elemento.dataset.caracteristicas),
  precio: Number(elemento.dataset.precio),    // los data-* llegan como texto
}));

// 4) Lee los filtros, decide qué tarjetas se ven y en qué orden.
function aplicarFiltros() {
  const texto = normalizar(campoTexto.value);
  const palabras = texto.split(/\s+/).filter(Boolean);  // "techadas heras" → ["techadas", "heras"]
  const zona = selectZona.value;               // "" significa "Todas"
  const precioMaximo = Number(rangoPrecio.value);
  const orden = selectOrden.value;

  valorPrecio.textContent = formatearPrecio(precioMaximo);

  // a) Filtrar: se queda con los que cumplen las TRES condiciones.
  const visibles = complejos.filter((c) => {
    // Cada palabra tiene que aparecer en el nombre, las características o la zona.
    const coincideTexto = palabras.every((p) =>
      c.nombre.includes(p) || c.caracteristicas.includes(p) || normalizar(c.zona).includes(p));
    const coincideZona = zona === "" || c.zona === zona;
    const entraEnPrecio = c.precio <= precioMaximo;
    return coincideTexto && coincideZona && entraEnPrecio;
  });

  // b) Ordenar. sort recibe una función que compara de a dos:
  //    si da negativo, "a" va antes que "b".
  if (orden === "menor") {
    visibles.sort((a, b) => a.precio - b.precio);
  } else if (orden === "mayor") {
    visibles.sort((a, b) => b.precio - a.precio);
  } else {
    visibles.sort((a, b) => a.posicion - b.posicion);
  }

  // c) Mostrar: ocultamos todas y después mostramos las que quedaron,
  //    en orden. append() con una tarjeta que ya está en la grilla la MUEVE
  //    al final, así que al recorrerlas en orden quedan ordenadas.
  for (const c of complejos) {
    c.elemento.hidden = true;
  }
  for (const c of visibles) {
    c.elemento.hidden = false;
    grilla.append(c.elemento);
  }

  // d) Resumen y aviso. Siempre textContent, nunca innerHTML (regla del grupo).
  const cantidad = visibles.length;
  resumen.textContent = cantidad === 1 ? "1 complejo" : cantidad + " complejos";
  avisoVacio.hidden = cantidad > 0;
}

// 5) Cada vez que el usuario toca un filtro, se vuelve a aplicar todo.
//    "input" salta en cada tecla o movimiento del rango; "change", al elegir
//    una opción del select.
campoTexto.addEventListener("input", aplicarFiltros);
rangoPrecio.addEventListener("input", aplicarFiltros);
selectZona.addEventListener("change", aplicarFiltros);
selectOrden.addEventListener("change", aplicarFiltros);

// Si apretan Enter en el buscador, que no recargue la página.
formulario.addEventListener("submit", (evento) => evento.preventDefault());

// Primera pasada al cargar, para que aparezca el resumen ("6 complejos").
aplicarFiltros();

// =========================================================================
// 6) CARACTERÍSTICA INTELIGENTE: búsqueda por voz.
//    El navegador pasa la voz a texto (Web Speech API) y interpretar()
//    entiende la frase y la convierte en filtros: zona, precio, orden y texto.
// =========================================================================

// Palabras que no aportan a la búsqueda y se descartan ("quiero una cancha en...").
const PALABRAS_DE_RELLENO = [
  "quiero", "busco", "buscame", "mostrame", "dame", "necesito",
  "un", "una", "unos", "unas", "el", "la", "los", "las", "de", "del",
  "en", "con", "que", "sea", "sean", "y", "a", "por", "para",
  "cancha", "canchas", "complejo", "complejos", "futbol",
  "hasta", "menos", "mas", "maximo", "pesos", "hora", "precio", "mil",
  "barata", "baratas", "barato", "baratos", "economica", "economicas",
  "cara", "caras", "caro", "caros",
  "favor", "porfa", "algo", "alguna", "alguno", "me", "gustaria",
];

function interpretar(frase) {
  let resto = normalizar(frase);

  // a) ZONA: si la frase nombra alguna de las zonas del select, la elegimos.
  selectZona.value = "";
  for (const opcion of selectZona.options) {
    const zona = normalizar(opcion.value);
    if (zona && resto.includes(zona)) {
      selectZona.value = opcion.value;
      resto = resto.replace(zona, " ");   // ya la usamos: la sacamos de la frase
    }
  }

  // b) PRECIO: "hasta 18 mil", "menos de 18000", "18.000".
  //    Primero juntamos los miles ("18.000", "18,000" o "18 000" → "18000") y sacamos el $.
  resto = resto.replace(/(\d)[.,\s](\d{3})\b/g, "$1$2");  // 17.000 / 17,000 / 17 000 → 17000
  resto = resto.replace(/[^a-z0-9ñ\s]/g, " ");           // saca $, signos y puntuación
  const precio = resto.match(/\b(\d+)\s*(mil)?\b/);
  let numero = precio ? Number(precio[1]) * (precio[2] ? 1000 : 1) : 0;
  if (numero >= 1000) {
    rangoPrecio.value = numero;           // el rango solo lo ajusta entre su mín y máx
    resto = resto.replace(precio[0], " ");
  } else {
    rangoPrecio.value = rangoPrecio.max;  // un "5" suelto (ej. "Estadio 5") no es un precio
  }

  // c) ORDEN: "la más barata" → menor precio; "la más cara" → mayor precio.
  if (/\b(barat|economic)/.test(resto)) {
    selectOrden.value = "menor";
  } else if (/\bcar(a|o)s?\b/.test(resto)) {
    selectOrden.value = "mayor";
  } else {
    selectOrden.value = "";
  }

  // d) TEXTO: lo que sobra, sin relleno ni números, va al buscador.
  const palabras = resto
    .split(/\s+/)
    .filter((p) => p && !PALABRAS_DE_RELLENO.includes(p) && !/^\d+$/.test(p));
  campoTexto.value = palabras.join(" ");

  // e) Aplicamos y mostramos qué se escuchó, para que el usuario lo vea.
  aplicarFiltros();
  resumen.textContent = "Escuché: \"" + frase + "\" · " + resumen.textContent;
}

// El reconocimiento de voz existe en Chrome y Edge (con prefijo webkit).
// Si el navegador no lo tiene (ej. Firefox), el botón queda oculto y listo.
const botonVoz = document.querySelector("#boton-voz");
const Reconocimiento = window.SpeechRecognition || window.webkitSpeechRecognition;

if (Reconocimiento) {
  const reconocedor = new Reconocimiento();
  reconocedor.lang = "es-AR";          // español de Argentina
  reconocedor.interimResults = false;  // solo el resultado final, no el parcial
  reconocedor.maxAlternatives = 1;

  botonVoz.hidden = false;

  // Un clic empieza a escuchar; otro clic mientras escucha, corta.
  botonVoz.addEventListener("click", () => {
    if (botonVoz.classList.contains("escuchando")) {
      reconocedor.stop();
    } else {
      reconocedor.start();
    }
  });

  reconocedor.addEventListener("start", () => {
    botonVoz.classList.add("escuchando");   // el CSS lo pinta de rojo
    resumen.textContent = "Escuchando…";
  });

  reconocedor.addEventListener("result", (evento) => {
    interpretar(evento.results[0][0].transcript);
  });

  reconocedor.addEventListener("error", (evento) => {
    resumen.textContent = evento.error === "not-allowed"
      ? "Para buscar por voz, permití el uso del micrófono."
      : "No te escuché bien. Probá de nuevo.";
  });

  reconocedor.addEventListener("end", () => {
    botonVoz.classList.remove("escuchando");
    // Si terminó sin escuchar nada, volvemos al resumen normal.
    if (resumen.textContent === "Escuchando…") aplicarFiltros();
  });
}