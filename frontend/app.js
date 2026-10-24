"use strict";

// El historial vive en el teléfono (localStorage): el productor puede releer sus
// consultas sin señal, y el servidor no guarda conversaciones.
const CLAVE_HISTORIAL = "cacao.historial.v1";
const MAX_HISTORIAL_ENVIADO = 10;
const ESPERA_MAXIMA_MS = 45000; // sin recibir nada en este tiempo se corta la espera

const $ = (sel) => document.querySelector(sel);
const conversacion = $("#conversacion");
const bienvenida = $("#bienvenida");
const formulario = $("#formulario");
const campo = $("#mensaje");
const botonEnviar = $("#enviar");
const cajaError = $("#error");
const textoError = $("#error-texto");
const botonReintentar = $("#reintentar");
const botonNueva = $("#nueva");

let historial = cargarHistorial();
let enviando = false;
let ultimoTexto = "";

// ---------------------------------------------------------------- almacenamiento
function cargarHistorial() {
  try {
    const datos = JSON.parse(localStorage.getItem(CLAVE_HISTORIAL) || "[]");
    return Array.isArray(datos) ? datos.filter((m) => m && (m.role === "user" || m.role === "assistant")) : [];
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

// ---------------------------------------------------------------- formato seguro
// La respuesta del modelo NUNCA se inserta como HTML crudo (OWASP LLM05): primero se
// escapa todo y luego se aplica un formato mínimo (negritas y listas).
function escapar(texto) {
  return texto.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
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

// ---------------------------------------------------------------- interfaz
function burbuja(rol, texto = "") {
  const div = document.createElement("div");
  div.className = `burbuja ${rol === "user" ? "usuario" : "asistente"}`;
  if (rol === "user") div.textContent = texto;
  else div.innerHTML = aHtml(texto);
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
  botonEnviar.disabled = si;
  botonEnviar.textContent = si ? "Enviando…" : "Enviar";
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
  historial.forEach((m) => burbuja(m.role, m.content));
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
  const divUsuario = burbuja("user", texto);
  const divAsistente = burbuja("assistant");
  indicadorEscribiendo(divAsistente);
  bajar();

  const control = new AbortController();
  let temporizador = setTimeout(() => control.abort(), ESPERA_MAXIMA_MS);
  const reiniciarTemporizador = () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => control.abort(), ESPERA_MAXIMA_MS);
  };

  let acumulado = "";
  let terminado = false;

  const deshacer = (mensaje) => {
    // Nada llegó: se quita el intento y se devuelve el texto al campo para reintentar.
    divUsuario.remove();
    divAsistente.remove();
    bienvenida.hidden = historial.length > 0;
    campo.value = texto;
    ajustarAltura();
    mostrarError(mensaje);
  };

  try {
    const respuesta = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensaje: texto, historial: historial.slice(-MAX_HISTORIAL_ENVIADO) }),
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
          divAsistente.innerHTML = aHtml(acumulado);
          bajar();
        } else if (evento.tipo === "error") {
          divAsistente.classList.add("incompleta");
          mostrarError(evento.mensaje);
        } else if (evento.tipo === "fin") {
          terminado = true;
        }
      }
    }

    if (terminado) {
      historial.push({ role: "user", content: texto }, { role: "assistant", content: acumulado });
      guardarHistorial();
    } else if (!acumulado) {
      deshacer("El asistente no respondió. Intente de nuevo.");
    } else if (cajaError.hidden) {
      divAsistente.classList.add("incompleta");
      mostrarError("La respuesta se cortó a la mitad. Vuelva a enviar su pregunta.");
    }
  } catch (error) {
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
    ocupado(false);
    campo.focus();
  }
}

// ---------------------------------------------------------------- eventos
formulario.addEventListener("submit", (e) => {
  e.preventDefault();
  enviar(campo.value);
});

campo.addEventListener("input", ajustarAltura);
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

window.addEventListener("offline", () => mostrarError("Se perdió la señal de internet. Sus consultas anteriores siguen aquí."));
window.addEventListener("online", ocultarError);

pintarHistorial();
