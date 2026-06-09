/* =========================================================================
   menu.js — Interactividad del menú hamburguesa.
   Responsable: [FED] Federico Cabrera (Frontend / HTML).
   Decisión de UX detrás: [GON] Gonzalo Tapia (menú colapsable en móvil).
   ------------------------------------------------------------------------- */

// 1) Buscamos el botón hamburguesa y el menú dentro de la página.
const boton = document.querySelector(".hamburguesa");
const menu  = document.querySelector(".menu");

// 2) Al hacer clic en el botón, alternamos la clase "abierto" en el menú.
//    classList.toggle = si la clase está, la quita; si no está, la agrega.
//    El JS solo cambia el ESTADO (la clase); el CSS decide cómo se ve.
boton.addEventListener("click", () => {
  menu.classList.toggle("abierto");
});
