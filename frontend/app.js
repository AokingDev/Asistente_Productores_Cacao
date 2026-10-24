"use strict";

// El historial vive en el teléfono (localStorage): el productor puede releer sus
// consultas sin señal, y el servidor no guarda conversaciones.
const CLAVE_HISTORIAL = "cacao.historial.v1";
const MAX_HISTORIAL_ENVIADO = 10;
const ESPERA_MAXIMA_MS = 45000; // sin recibir nada en este tiempo se corta la espera
const ES_ESCRITORIO = window.matchMedia("(min-width: 960px)");

const NOMBRES_IA = { gemini: "Gemini", groq: "Groq", simulado: "Simulador de pruebas" };

const $ = (sel) => document.querySelector(sel);
const conversacion = $("#conversacion");
const bienvenida = $("#bienvenida");
const formulario = $("#formulario");
const campo = $("#mensaje");
const botonEnviar = $("#enviar");
const botonDetener = $("#detener");
const cajaError = $("#error");
const textoError = $("#error-texto");
const botonReintentar = $("#reintentar");
const botonNueva = $("#nueva");
const lateral = $("#lateral");
const velo = $("#velo");
const botonInfo = $("#abrir-info");
const mascota = $("#mascota");
const botonAvatar = $("#avatar");

let historial = cargarHistorial();
let enviando = false;
let ultimoTexto = "";
let detener = null; // función que corta la respuesta en curso

// ---------------------------------------------------------------- almacenamiento
function cargarHistorial() {
  try {
    const datos = JSON.parse(localStorage.getItem(CLAVE_HISTORIAL) || "[]");
    return Array.isArray(datos)
      ? datos.filter((m) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
      : [];
  } catch {
    return [];
  }
}

function guardarHistorial() {
  try {
    localStorage.setItem(CLAVE_HISTORIAL, JSON.stringify(historial.slice(-40)));
  } catch {
    /* sin almacenamiento (modo privado): la conversación igual funciona */
  }
}

// Al servidor solo van rol y texto: el esquema rechaza campos extra (proveedor, modelo…).
function historialParaEnviar() {
  return historial.slice(-MAX_HISTORIAL_ENVIADO).map(({ role, content }) => ({ role, content }));
}

// ---------------------------------------------------------------- formato seguro
// La respuesta del modelo NUNCA se inserta como HTML crudo (OWASP LLM05): primero se
// escapa todo y luego se aplica un formato mínimo (negritas y listas).
function escapar(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function enLinea(texto) {
  return escapar(texto).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

function aHtml(texto) {
  const bloques = [];
  let lista = null;
  for (const linea of texto.split("\n")) {
    const vineta = linea.match(/^\s*[-*•]\s+(.*)$/);
    const numero = linea.match(/^\s*\d+[.)]\s+(.*)$/);
    const item = vineta || numero;
    if (item) {
      const tipo = vineta ? "ul" : "ol";
      if (!lista || lista.tipo !== tipo) {
        lista = { tipo, items: [] };
        bloques.push(lista);
      }
      lista.items.push(enLinea(item[1]));
    } else if (linea.trim()) {
      lista = null;
      bloques.push(`<p>${enLinea(linea.trim())}</p>`);
    } else {
      lista = null;
    }
  }
  return bloques
    .map((b) => (typeof b === "string" ? b : `<${b.tipo}>${b.items.map((i) => `<li>${i}</li>`).join("")}</${b.tipo}>`))
    .join("");
}

// ---------------------------------------------------------------- recordatorio del técnico
// El recordatorio «confirme con un técnico» se muestra SIEMPRE en la nube del avatar (lo
// pone el código, no depende del modelo). Por eso se quita de la última línea de cada
// respuesta, para no repetirlo en todas. Solo se quita si es una línea suelta al final
// (no una viñeta con contenido) y si queda texto después de quitarla.
const RECORDATORIO = /(orientaci[oó]n\s+(es\s+)?preliminar|conf[ií]rm\w*\s.*t[eé]cnic|consult\w*\s.*t[eé]cnic|visit\w*\s.*t[eé]cnic)/i;
const ES_ITEM = /^\s*([-*•]|\d+[.)])\s/;

function sinRecordatorio(texto) {
  const lineas = texto.replace(/\s+$/, "").split("\n");
  let quitado = false;
  while (lineas.length > 1) {
    const ultima = lineas[lineas.length - 1];
    if (!ultima.trim()) {
      lineas.pop();
      continue;
    }
    if (ultima.length < 240 && !ES_ITEM.test(ultima) && RECORDATORIO.test(ultima)) {
      lineas.pop();
      quitado = true;
      continue;
    }
    break;
  }
  return { texto: lineas.join("\n"), quitado };
}

// Deja espacio al final de la conversación para que el avatar (y su nube, si está
// abierta) nunca tape el último mensaje.
function reservarEspacio() {
  const alto = mascota.classList.contains("cerrada") ? botonAvatar.offsetHeight : mascota.offsetHeight;
  document.documentElement.style.setProperty("--espacio-mascota", `${alto + 24}px`);
}

function abrirNube(llamar = false) {
  mascota.classList.remove("cerrada");
  botonAvatar.setAttribute("aria-expanded", "true");
  reservarEspacio();
  if (llamar) {
    mascota.classList.remove("llama");
    void mascota.offsetWidth; // reinicia la animación
    mascota.classList.add("llama");
  }
}

function cerrarNube() {
  mascota.classList.add("cerrada");
  botonAvatar.setAttribute("aria-expanded", "false");
  reservarEspacio();
}

// ---------------------------------------------------------------- interfaz
function pintarRespuesta(div, texto) {
  div.innerHTML = aHtml(sinRecordatorio(texto).texto);
}

function pintarMeta(div, { proveedor, modelo, latencia_ms: ms }) {
  if (!proveedor) return;
  const meta = document.createElement("div");
  meta.className = "meta";
  const clase = ["gemini", "groq"].includes(proveedor) ? proveedor : "";
  let html = `Generado por <span class="marca-ia ${clase}">${escapar(NOMBRES_IA[proveedor] || proveedor)}</span>`;
  if (modelo) html += ` <span>${escapar(modelo)}</span>`;
  if (ms) html += ` <span>· ${(ms / 1000).toFixed(1).replace(".", ",")} s</span>`;
  meta.innerHTML = html;
  div.appendChild(meta);
}

function burbuja(mensaje) {
  const div = document.createElement("div");
  div.className = `burbuja ${mensaje.role === "user" ? "usuario" : "asistente"}`;
  if (mensaje.role === "user") {
    div.textContent = mensaje.content;
  } else if (mensaje.content) {
    pintarRespuesta(div, mensaje.content);
    pintarMeta(div, mensaje);
  }
  conversacion.appendChild(div);
  bienvenida.hidden = true;
  return div;
}

function indicadorEscribiendo(div) {
  div.innerHTML = '<span class="escribiendo" aria-label="El asistente está escribiendo"><span></span><span></span><span></span></span>';
}

function bajar() {
  conversacion.scrollTop = conversacion.scrollHeight;
}

function mostrarError(mensaje) {
  textoError.textContent = mensaje;
  cajaError.hidden = false;
}

function ocultarError() {
  cajaError.hidden = true;
}

function ocupado(si) {
  enviando = si;
  botonEnviar.disabled = si; // «Enviar» se deshabilita mientras espera…
  botonEnviar.textContent = si ? "Enviando…" : "Enviar";
  botonDetener.hidden = !si; // …y aparece «Detener respuesta»
  campo.disabled = si;
  document.querySelectorAll(".chip").forEach((c) => (c.disabled = si));
}

function ajustarAltura() {
  campo.style.height = "auto";
  campo.style.height = `${Math.min(campo.scrollHeight, 140)}px`;
}

function pintarHistorial() {
  conversacion.querySelectorAll(".burbuja").forEach((b) => b.remove());
  bienvenida.hidden = historial.length > 0;
  historial.forEach(burbuja);
  bajar();
}

// ---------------------------------------------------------------- errores comprensibles
async function mensajeDeError(respuesta) {
  let detalle = "";
  try {
    const cuerpo = await respuesta.json();
    detalle = typeof cuerpo.detail === "string" ? cuerpo.detail : "";
  } catch {
    /* el cuerpo no era JSON */
  }
  if (respuesta.status === 422) return "Su mensaje está vacío o es demasiado largo (máximo 1000 letras).";
  if (respuesta.status === 429) return "Hay muchas consultas en este momento. Espere un minuto e intente de nuevo.";
  if (respuesta.status === 503) return detalle || "El asistente no está disponible ahora. Intente en unos minutos.";
  return `Ocurrió un problema en el servidor (código ${respuesta.status}). Intente de nuevo.`;
}

// ---------------------------------------------------------------- envío con streaming
async function enviar(texto) {
  texto = texto.trim();
  if (!texto || enviando) return;
  ocultarError();
  ultimoTexto = texto;

  if (!navigator.onLine) {
    mostrarError("No tiene señal de internet. Su pregunta no se envió; intente cuando tenga conexión.");
    return;
  }

  ocupado(true);
  campo.value = "";
  ajustarAltura();
  if (!ES_ESCRITORIO.matches) cerrarNube(); // en el teléfono la nube no debe tapar la respuesta
  const divUsuario = burbuja({ role: "user", content: texto });
  const divAsistente = burbuja({ role: "assistant", content: "" });
  indicadorEscribiendo(divAsistente);
  bajar();

  const control = new AbortController();
  let motivo = "tiempo"; // por qué se abortó: "tiempo" o "usuario"
  let temporizador = setTimeout(() => control.abort(), ESPERA_MAXIMA_MS);
  const reiniciarTemporizador = () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => control.abort(), ESPERA_MAXIMA_MS);
  };
  detener = () => {
    motivo = "usuario";
    control.abort();
  };

  let acumulado = "";
  let fin = null;

  const deshacer = (mensaje) => {
    // Nada llegó: se quita el intento y se devuelve el texto al campo para reintentar.
    divUsuario.remove();
    divAsistente.remove();
    bienvenida.hidden = historial.length > 0;
    campo.value = texto;
    ajustarAltura();
    if (mensaje) mostrarError(mensaje);
  };

  try {
    const respuesta = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensaje: texto, historial: historialParaEnviar() }),
      signal: control.signal,
    });

    if (!respuesta.ok) {
      deshacer(await mensajeDeError(respuesta));
      return;
    }

    const lector = respuesta.body.getReader();
    const decodificador = new TextDecoder();
    let pendiente = "";

    for (;;) {
      const { value, done } = await lector.read();
      if (done) break;
      reiniciarTemporizador();
      pendiente += decodificador.decode(value, { stream: true });
      const lineas = pendiente.split("\n");
      pendiente = lineas.pop();
      for (const linea of lineas) {
        if (!linea.trim()) continue;
        const evento = JSON.parse(linea);
        if (evento.tipo === "texto") {
          acumulado += evento.texto;
          pintarRespuesta(divAsistente, acumulado);
          bajar();
        } else if (evento.tipo === "error") {
          divAsistente.classList.add("incompleta");
          mostrarError(evento.mensaje);
        } else if (evento.tipo === "fin") {
          fin = evento;
        }
      }
    }

    if (fin) {
      const mensaje = { role: "assistant", content: acumulado, proveedor: fin.proveedor, modelo: fin.modelo, latencia_ms: fin.latencia_ms };
      pintarMeta(divAsistente, mensaje);
      historial.push({ role: "user", content: texto }, mensaje);
      guardarHistorial();
      abrirNube(true); // el avatar recuerda confirmar con un técnico
      bajar();
    } else if (!acumulado) {
      deshacer("El asistente no respondió. Intente de nuevo.");
    } else if (cajaError.hidden) {
      divAsistente.classList.add("incompleta");
      mostrarError("La respuesta se cortó a la mitad. Vuelva a enviar su pregunta.");
    }
  } catch (error) {
    if (error.name === "AbortError" && motivo === "usuario") {
      // Detenida a propósito: sin mensaje de error. Lo recibido se queda en pantalla, pero no se
      // guarda en el historial (una respuesta a medias confundiría al modelo en la siguiente pregunta).
      if (acumulado) divAsistente.classList.add("detenida");
      else deshacer();
      return;
    }
    const mensaje = error.name === "AbortError"
      ? "El asistente tardó demasiado en responder. Revise su señal e intente de nuevo."
      : "No se pudo conectar con el asistente. Revise su conexión a internet e intente de nuevo.";
    if (acumulado) {
      divAsistente.classList.add("incompleta");
      mostrarError(mensaje);
    } else {
      deshacer(mensaje);
    }
  } finally {
    clearTimeout(temporizador);
    detener = null;
    ocupado(false);
    if (ES_ESCRITORIO.matches) campo.focus();
  }
}

// ---------------------------------------------------------------- panel lateral (teléfono)
function abrirPanel() {
  lateral.classList.add("abierto");
  velo.hidden = false;
  botonInfo.setAttribute("aria-expanded", "true");
  $("#cerrar-info").focus();
}

function cerrarPanel() {
  lateral.classList.remove("abierto");
  velo.hidden = true;
  botonInfo.setAttribute("aria-expanded", "false");
}

async function mostrarEstado() {
  const estado = $("#estado");
  const texto = $("#estado-texto");
  try {
    const r = await fetch("/health");
    const datos = await r.json();
    if (datos.llm) {
      const principal = NOMBRES_IA[datos.llm.principal] || datos.llm.principal;
      const respaldo = datos.llm.respaldo ? ` · respaldo ${NOMBRES_IA[datos.llm.respaldo] || datos.llm.respaldo}` : "";
      texto.textContent = `En línea · ${principal}${respaldo}`;
      estado.className = "estado ok";
    } else {
      texto.textContent = "Servicio sin configurar";
      estado.className = "estado mal";
    }
  } catch {
    texto.textContent = "Sin conexión con el servicio";
    estado.className = "estado mal";
  }
}

// ---------------------------------------------------------------- eventos
formulario.addEventListener("submit", (e) => {
  e.preventDefault();
  enviar(campo.value);
});

botonDetener.addEventListener("click", () => detener?.());

campo.addEventListener("input", ajustarAltura);
campo.addEventListener("focus", () => {
  if (!ES_ESCRITORIO.matches) cerrarNube();
});
campo.addEventListener("keydown", (e) => {
  // En computador, Enter envía y Shift+Enter hace salto de línea. En el teléfono, Enter hace salto de línea.
  if (e.key === "Enter" && !e.shiftKey && window.matchMedia("(pointer: fine)").matches) {
    e.preventDefault();
    formulario.requestSubmit();
  }
});

document.querySelectorAll(".chip").forEach((chip) => chip.addEventListener("click", () => enviar(chip.textContent)));

botonReintentar.addEventListener("click", () => {
  conversacion.querySelectorAll(".incompleta").forEach((b) => {
    b.previousElementSibling?.remove(); // la pregunta que quedó sin respuesta completa
    b.remove();
  });
  enviar(ultimoTexto || campo.value);
});

let confirmarBorrado = null;
botonNueva.addEventListener("click", () => {
  if (!confirmarBorrado) {
    botonNueva.textContent = "¿Borrar todo?";
    confirmarBorrado = setTimeout(() => {
      botonNueva.textContent = "Nueva";
      confirmarBorrado = null;
    }, 3000);
    return;
  }
  clearTimeout(confirmarBorrado);
  confirmarBorrado = null;
  botonNueva.textContent = "Nueva";
  historial = [];
  guardarHistorial();
  ocultarError();
  pintarHistorial();
});

botonAvatar.addEventListener("click", () => (mascota.classList.contains("cerrada") ? abrirNube() : cerrarNube()));
$("#cerrar-nube").addEventListener("click", cerrarNube);

botonInfo.addEventListener("click", abrirPanel);
$("#cerrar-info").addEventListener("click", cerrarPanel);
velo.addEventListener("click", cerrarPanel);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (lateral.classList.contains("abierto")) cerrarPanel();
    else if (enviando) detener?.();
  }
});
ES_ESCRITORIO.addEventListener("change", cerrarPanel);

// El avatar se ubica justo encima de la barra de entrada, mida lo que mida
new ResizeObserver(() => {
  document.documentElement.style.setProperty("--alto-entrada", `${formulario.offsetHeight}px`);
}).observe(formulario);
new ResizeObserver(reservarEspacio).observe(mascota);

window.addEventListener("offline", () => mostrarError("Se perdió la señal de internet. Sus consultas anteriores siguen aquí."));
window.addEventListener("online", ocultarError);

pintarHistorial();
mostrarEstado();
