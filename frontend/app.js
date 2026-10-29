"use strict";

// El historial vive en el teléfono (localStorage): el productor puede releer sus
// consultas sin señal, y el servidor no guarda conversaciones.
const CLAVE_HISTORIAL = "cacao.historial.v1";
const CLAVE_FILTRO = "cacao.filtro.v1";
const MAX_HISTORIAL_ENVIADO = 10;
const ESPERA_MAXIMA_MS = 60000; // sin recibir nada en este tiempo se corta la espera
const ES_ESCRITORIO = window.matchMedia("(min-width: 960px)");

const NOMBRES_IA = { gemini: "Gemini", groq: "Groq", simulado: "Simulador de pruebas" };
const CONFIANZA = { alta: "Coincide bien", media: "Coincide en parte", baja: "Coincide poco" };

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
const selectorTema = $("#filtro-tema");
const filtroActivo = $("#filtro-activo");

let historial = cargarHistorial();
let enviando = false;
let ultimoTexto = "";
let detener = null; // función que corta la respuesta en curso
let temas = {};      // id → etiqueta (de GET /fuentes)
let tema = leer(CLAVE_FILTRO, "");

// ---------------------------------------------------------------- almacenamiento
function leer(clave, porDefecto) {
  try {
    return JSON.parse(localStorage.getItem(clave)) ?? porDefecto;
  } catch {
    return porDefecto;
  }
}

function escribir(clave, valor) {
  try {
    localStorage.setItem(clave, JSON.stringify(valor));
  } catch {
    /* sin almacenamiento (modo privado): la conversación igual funciona */
  }
}

function cargarHistorial() {
  const datos = leer(CLAVE_HISTORIAL, []);
  return Array.isArray(datos)
    ? datos.filter((m) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
    : [];
}

function guardarHistorial() {
  escribir(CLAVE_HISTORIAL, historial.slice(-40));
}

// Al servidor solo van rol y texto: el esquema rechaza campos extra (fuentes, herramientas…).
function historialParaEnviar() {
  return historial.slice(-MAX_HISTORIAL_ENVIADO).map(({ role, content }) => ({ role, content }));
}

// ---------------------------------------------------------------- formato seguro
// La respuesta del modelo NUNCA se inserta como HTML crudo (OWASP LLM05): primero se
// escapa todo y luego se aplica un formato mínimo (negritas, listas y citas [n]).
function escapar(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function enLinea(texto) {
  return escapar(texto)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\[(\d+(?:\s*[,;]\s*\d+)*)\]/g, (_, grupo) =>
      grupo.split(/\s*[,;]\s*/).map((n) => `<button type="button" class="cita" data-n="${n}" aria-label="Ver fuente ${n}">${n}</button>`).join(""));
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

function el(etiqueta, clase, html) {
  const e = document.createElement(etiqueta);
  if (clase) e.className = clase;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

// ---------------------------------------------------------------- recordatorio del técnico
// El recordatorio «confirme con un técnico» se muestra SIEMPRE en la nube del avatar (lo
// pone el código, no depende del modelo). Si el modelo lo repite al final, se quita.
const RECORDATORIO = /(orientaci[oó]n\s+(es\s+)?preliminar|conf[ií]rm\w*\s.*t[eé]cnic|consult\w*\s.*t[eé]cnic|visit\w*\s.*t[eé]cnic)/i;
const ES_ITEM = /^\s*([-*•]|\d+[.)])\s/;

function sinRecordatorio(texto) {
  const lineas = texto.replace(/\s+$/, "").split("\n");
  while (lineas.length > 1) {
    const ultima = lineas[lineas.length - 1];
    if (!ultima.trim()) {
      lineas.pop();
      continue;
    }
    if (ultima.length < 240 && !ES_ITEM.test(ultima) && !/\[\d/.test(ultima) && RECORDATORIO.test(ultima)) {
      lineas.pop();
      continue;
    }
    break;
  }
  return lineas.join("\n");
}

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

// ---------------------------------------------------------------- piezas de la respuesta
// Cada respuesta del asistente es un objeto que se guarda en el historial y se vuelve a pintar igual:
// { role, content, fuentes, citadas, herramientas, confirmaciones, alerta, aviso, abstencion, proveedor, modelo, latencia_ms }

function pintarFuentes(caja, msg) {
  caja.innerHTML = "";
  const fuentes = msg.fuentes || [];
  if (msg.cuarentena) {
    caja.append(el("p", "nota-cuarentena", `🛡️ Se descartó ${msg.cuarentena === 1 ? "1 fragmento" : `${msg.cuarentena} fragmentos`} ` +
      "que contenía instrucciones sospechosas en lugar de información técnica."));
  }
  if (!fuentes.length) return;
  const citadas = new Set(msg.citadas || []);
  const principales = fuentes.filter((f) => citadas.has(f.n));
  const otras = fuentes.filter((f) => !citadas.has(f.n));
  const tarjeta = (f) => {
    const pags = f.paginas.length === 1 ? `pág. ${f.paginas[0]}` : `págs. ${f.paginas[0]}–${f.paginas[f.paginas.length - 1]}`;
    const enlace = f.url ? `<a href="${escapar(f.url)}" target="_blank" rel="noopener noreferrer">Abrir ${pags}</a>` : pags;
    return `<li class="fuente" data-n="${f.n}">
      <span class="fuente-n">${f.n}</span>
      <div><strong>${escapar(f.seccion)}</strong>
        <span class="fuente-doc">${escapar(f.documento)} · ${escapar(f.institucion)} (${escapar(f.anio)})</span>
        <span class="fuente-pie">${enlace} · tema: ${escapar(temas[f.tema] || f.tema)}</span></div></li>`;
  };
  if (principales.length) {
    caja.append(el("p", "fuentes-titulo", `📖 Fuentes citadas (${principales.length})`));
    caja.append(el("ul", "fuentes-lista", principales.map(tarjeta).join("")));
  }
  if (otras.length) {
    const det = el("details", "fuentes-otras");
    det.innerHTML = `<summary>${principales.length ? "Otros fragmentos consultados" : "Fragmentos consultados (sin cita en la respuesta)"} (${otras.length})</summary>
      <ul class="fuentes-lista">${otras.map(tarjeta).join("")}</ul>`;
    caja.append(det);
  }
}

function fuentesMini(lista) {
  return (lista || []).map((f) => f.url
    ? `<a href="${escapar(f.url)}" target="_blank" rel="noopener noreferrer">${escapar(f.documento.split(" (")[0])}, p. ${f.pagina}</a>`
    : `${escapar(f.documento)}, p. ${f.pagina}`).join(" · ");
}

function tarjetaDiagnostico(r) {
  const t = el("section", "tarjeta diagnostico");
  if (r.sin_coincidencias) {
    t.innerHTML = `<h4>🔎 Diagnóstico preliminar</h4><p>No encontré una enfermedad o plaga que coincida con lo que describe. Cuénteme qué parte de la planta está afectada y cómo se ve.</p>`;
    return t;
  }
  const alts = r.alternativas.map((a, i) => `
    <li class="alt ${a.confianza}">
      <div class="alt-cabecera"><strong>${i === 0 ? "" : "o "}${escapar(a.nombre)}</strong>
        <span class="insignia ${a.confianza}">${CONFIANZA[a.confianza]}</span></div>
      <p class="alt-signos">Coincide con: ${a.signos_coincidentes.map(escapar).join("; ")}</p>
      <p><strong>Para confirmar:</strong> ${escapar(a.para_confirmar)}</p>
      <p><strong>Mientras tanto:</strong> ${escapar(a.manejo_cultural)}</p>
      <p class="alt-fuentes">Fuente: ${fuentesMini(a.fuentes)}</p>
    </li>`).join("");
  t.innerHTML = `<h4>🔎 Diagnóstico preliminar${r.hay_varias ? ` · ${r.alternativas.length} posibles causas` : ""}</h4>
    <ol class="alternativas">${alts}</ol><p class="tarjeta-nota">${escapar(r.advertencia)}</p>`;
  return t;
}

function tarjetaCalendario(r) {
  const t = el("section", "tarjeta calendario");
  const esteMes = r.labores.filter((l) => l.este_mes);
  const filas = r.labores.map((l) => `<tr${l.este_mes ? ' class="ahora"' : ""}>
      <td><strong>${escapar(l.labor)}</strong><span>${escapar(l.frecuencia)}</span></td>
      <td>${l.meses.length === 12 ? "Todo el año" : l.meses.map(escapar).join(", ")}</td>
      <td class="cal-fuente">${fuentesMini(l.fuentes)}</td></tr>`).join("");
  t.innerHTML = `<h4>📅 Calendario de labores · ${escapar(r.etapa)}</h4>
    <p class="tarjeta-sub">${escapar(r.region)} · de ${escapar(r.desde)} a ${escapar(r.hasta)}</p>
    <p><strong>En ${escapar(r.este_mes)}:</strong> ${esteMes.map((l) => escapar(l.labor)).join(", ") || "sin labores marcadas"}</p>
    <details><summary>Ver las ${r.labores.length} labores del año</summary>
      <div class="tabla-desliza"><table><thead><tr><th>Labor</th><th>Meses</th><th>Fuente</th></tr></thead><tbody>${filas}</tbody></table></div>
    </details>
    <p class="tarjeta-nota">${escapar(r.nota_region)}</p>`;
  return t;
}

const ETIQUETAS_DATOS = { resumen: "Resumen", sintomas: "Síntomas", diagnostico_preliminar: "Diagnóstico preliminar",
  provincia: "Provincia", etapa: "Etapa del cultivo", motivo: "Motivo" };

function tarjetaConfirmacion(conf, msg) {
  const t = el("section", "tarjeta confirmacion");
  const datos = Object.entries(conf.datos)
    .filter(([, v]) => v && v !== "no_indica")
    .map(([k, v]) => `<dt>${ETIQUETAS_DATOS[k] || k}</dt><dd>${escapar(String(v).replaceAll("_", " "))}</dd>`).join("");
  const pintar = () => {
    let pie;
    if (conf.estado === "confirmada") pie = `<p class="conf-ok">✅ Registrada con el código <strong>${escapar(conf.codigo)}</strong>. Guárdelo para el seguimiento del técnico.</p>`;
    else if (conf.estado === "cancelada") pie = `<p class="conf-no">No se registró.</p>`;
    else if (conf.estado === "caducada") pie = `<p class="conf-no">La propuesta caducó. Pida de nuevo el registro si lo necesita.</p>`;
    else pie = `<div class="conf-botones"><button type="button" class="btn-confirmar">Sí, registrar</button>
        <button type="button" class="btn-cancelar">No, gracias</button></div>`;
    t.innerHTML = `<h4>📝 ¿Registro esta consulta?</h4>
      <p>El asistente propone guardar estos datos para que un técnico dé seguimiento. <strong>No se guarda nada sin su confirmación.</strong></p>
      <dl>${datos}</dl>${pie}`;
    t.querySelector(".btn-confirmar")?.addEventListener("click", () => responderConfirmacion(true));
    t.querySelector(".btn-cancelar")?.addEventListener("click", () => responderConfirmacion(false));
  };
  const responderConfirmacion = async (si) => {
    t.querySelectorAll("button").forEach((b) => (b.disabled = true));
    try {
      const r = await fetch(`/consultas/${encodeURIComponent(conf.id)}/${si ? "confirmar" : "cancelar"}`, { method: "POST" });
      const cuerpo = await r.json().catch(() => ({}));
      if (r.status === 404) conf.estado = "caducada";
      else if (!r.ok) throw new Error();
      else if (si) Object.assign(conf, { estado: "confirmada", codigo: cuerpo.codigo });
      else conf.estado = "cancelada";
      guardarHistorial();
      pintar();
    } catch {
      t.querySelectorAll("button").forEach((b) => (b.disabled = false));
      mostrarError("No se pudo enviar su respuesta. Revise su conexión e intente de nuevo.");
    }
  };
  pintar();
  return t;
}

function tarjetaHerramienta(h, msg) {
  if (h.nombre === "diagnosticar_sintomas") return tarjetaDiagnostico(h.resultado);
  if (h.nombre === "calendario_labores") return tarjetaCalendario(h.resultado);
  return null; // registrar_consulta se muestra como tarjeta de confirmación
}

function pintarAsistente(partes, msg, terminado = true) {
  partes.cuerpo.innerHTML = aHtml(sinRecordatorio(msg.content || ""));
  partes.div.classList.toggle("abstencion", Boolean(msg.abstencion));
  partes.tarjetas.innerHTML = "";
  (msg.herramientas || []).forEach((h) => {
    const t = tarjetaHerramienta(h, msg);
    if (t) partes.tarjetas.append(t);
  });
  (msg.confirmaciones || []).forEach((c) => partes.tarjetas.append(tarjetaConfirmacion(c, msg)));
  partes.avisos.innerHTML = "";
  if (msg.abstencion) partes.avisos.append(el("p", "etiqueta-abstencion", "📭 Sin información en los manuales cargados"));
  if (msg.alerta) partes.avisos.append(el("p", "alerta-dosis", `⚠️ ${escapar(msg.alerta)}`));
  if (msg.aviso) partes.avisos.append(el("p", "aviso-dosis", `ℹ️ ${escapar(msg.aviso)}`));
  pintarFuentes(partes.fuentes, msg);
  partes.meta.innerHTML = "";
  if (terminado && msg.proveedor) {
    const clase = ["gemini", "groq"].includes(msg.proveedor) ? msg.proveedor : "";
    let html = `Generado por <span class="marca-ia ${clase}">${escapar(NOMBRES_IA[msg.proveedor] || msg.proveedor)}</span>`;
    if (msg.modelo) html += ` <span>${escapar(msg.modelo)}</span>`;
    if (msg.latencia_ms) html += ` <span>· ${(msg.latencia_ms / 1000).toFixed(1).replace(".", ",")} s</span>`;
    partes.meta.innerHTML = html;
  } else if (terminado && msg.abstencion) {
    partes.meta.innerHTML = "Respuesta del sistema (sin consultar al modelo)";
  }
}

function burbujaAsistente() {
  const div = el("div", "burbuja asistente");
  const partes = { div, cuerpo: el("div", "cuerpo"), tarjetas: el("div", "tarjetas"), avisos: el("div", "avisos"),
    fuentes: el("div", "fuentes"), meta: el("div", "meta") };
  div.append(partes.cuerpo, partes.tarjetas, partes.avisos, partes.fuentes, partes.meta);
  conversacion.appendChild(div);
  bienvenida.hidden = true;
  return partes;
}

function burbujaUsuario(texto) {
  const div = el("div", "burbuja usuario");
  div.textContent = texto;
  conversacion.appendChild(div);
  bienvenida.hidden = true;
  return div;
}

function indicadorEscribiendo(cuerpo, texto = "") {
  cuerpo.innerHTML = `<span class="escribiendo" aria-label="El asistente está escribiendo"><span></span><span></span><span></span></span>${texto ? ` <span class="estado-paso">${escapar(texto)}</span>` : ""}`;
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
  historial.forEach((m) => (m.role === "user" ? burbujaUsuario(m.content) : pintarAsistente(burbujaAsistente(), m)));
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
  const divUsuario = burbujaUsuario(texto);
  const partes = burbujaAsistente();
  indicadorEscribiendo(partes.cuerpo, "Buscando en los manuales…");
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

  const msg = { role: "assistant", content: "", fuentes: [], citadas: [], herramientas: [], confirmaciones: [] };
  let fin = null;

  const deshacer = (mensaje) => {
    // Nada llegó: se quita el intento y se devuelve el texto al campo para reintentar.
    divUsuario.remove();
    partes.div.remove();
    bienvenida.hidden = historial.length > 0;
    campo.value = texto;
    ajustarAltura();
    if (mensaje) mostrarError(mensaje);
  };

  try {
    const respuesta = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensaje: texto, historial: historialParaEnviar(), tema: tema || null }),
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
        switch (evento.tipo) {
          case "fuentes":
            msg.fuentes = evento.fragmentos;
            msg.cuarentena = evento.cuarentena || 0;
            pintarFuentes(partes.fuentes, msg);
            indicadorEscribiendo(partes.cuerpo, evento.fragmentos.length ? `Leyendo ${evento.fragmentos.length} fragmentos…` : "Pensando…");
            break;
          case "texto":
            msg.content += evento.texto;
            partes.cuerpo.innerHTML = aHtml(sinRecordatorio(msg.content));
            break;
          case "herramienta": {
            msg.herramientas.push({ nombre: evento.nombre, resultado: evento.resultado });
            const t = tarjetaHerramienta(evento, msg);
            if (t) partes.tarjetas.append(t);
            if (!msg.content) indicadorEscribiendo(partes.cuerpo, "Preparando la respuesta…");
            break;
          }
          case "confirmacion": {
            const conf = { id: evento.id, datos: evento.datos, estado: "pendiente" };
            msg.confirmaciones.push(conf);
            partes.tarjetas.append(tarjetaConfirmacion(conf, msg));
            break;
          }
          case "alerta":
            msg.alerta = evento.mensaje;
            break;
          case "aviso":
            msg.aviso = evento.mensaje;
            break;
          case "error":
            partes.div.classList.add("incompleta");
            mostrarError(evento.mensaje);
            break;
          case "fin":
            fin = evento;
            break;
        }
        bajar();
      }
    }

    if (fin) {
      Object.assign(msg, { citadas: fin.citadas || [], abstencion: fin.abstencion, proveedor: fin.proveedor,
        modelo: fin.modelo, latencia_ms: fin.latencia_ms });
      pintarAsistente(partes, msg);
      historial.push({ role: "user", content: texto }, msg);
      guardarHistorial();
      abrirNube(true); // el avatar recuerda confirmar con un técnico
      bajar();
    } else if (!msg.content && !msg.herramientas.length) {
      deshacer("El asistente no respondió. Intente de nuevo.");
    } else if (cajaError.hidden) {
      partes.div.classList.add("incompleta");
      mostrarError("La respuesta se cortó a la mitad. Vuelva a enviar su pregunta.");
    }
  } catch (error) {
    if (error.name === "AbortError" && motivo === "usuario") {
      // Detenida a propósito: sin mensaje de error. Lo recibido se queda en pantalla, pero no se
      // guarda en el historial (una respuesta a medias confundiría al modelo en la siguiente pregunta).
      if (msg.content) partes.div.classList.add("detenida");
      else deshacer();
      return;
    }
    const mensaje = error.name === "AbortError"
      ? "El asistente tardó demasiado en responder. Revise su señal e intente de nuevo."
      : "No se pudo conectar con el asistente. Revise su conexión a internet e intente de nuevo.";
    if (msg.content) {
      partes.div.classList.add("incompleta");
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

// ---------------------------------------------------------------- citas: [n] lleva a su fuente
conversacion.addEventListener("click", (e) => {
  const boton = e.target.closest(".cita");
  if (!boton) return;
  const burbuja = boton.closest(".burbuja");
  const fuente = burbuja?.querySelector(`.fuente[data-n="${boton.dataset.n}"]`);
  if (!fuente) return;
  const det = fuente.closest("details");
  if (det) det.open = true;
  fuente.scrollIntoView({ behavior: "smooth", block: "nearest" });
  fuente.classList.remove("resaltada");
  void fuente.offsetWidth;
  fuente.classList.add("resaltada");
});

// ---------------------------------------------------------------- filtro por tema (metadatos)
function aplicarFiltro(nuevo) {
  tema = temas[nuevo] ? nuevo : "";
  escribir(CLAVE_FILTRO, tema);
  selectorTema.value = tema;
  filtroActivo.hidden = !tema;
  $("#filtro-activo-texto").textContent = temas[tema] || "";
}

selectorTema.addEventListener("change", () => aplicarFiltro(selectorTema.value));
$("#quitar-filtro").addEventListener("click", () => aplicarFiltro(""));

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

async function cargarServicio() {
  const estado = $("#estado");
  const texto = $("#estado-texto");
  try {
    const [salud, fuentes] = await Promise.all([fetch("/health").then((r) => r.json()), fetch("/fuentes").then((r) => r.json())]);
    if (salud.llm) {
      const principal = NOMBRES_IA[salud.llm.principal] || salud.llm.principal;
      const respaldo = salud.llm.respaldo ? ` · respaldo ${NOMBRES_IA[salud.llm.respaldo] || salud.llm.respaldo}` : "";
      const busqueda = salud.indice ? ` · ${salud.indice.fragmentos} fragmentos` : "";
      texto.textContent = `En línea · ${principal}${respaldo}${busqueda}`;
      estado.className = "estado ok";
    } else {
      texto.textContent = "Servicio sin configurar";
      estado.className = "estado mal";
    }
    temas = Object.fromEntries(fuentes.temas.map((t) => [t.id, t.etiqueta]));
    selectorTema.innerHTML = `<option value="">Todos los temas</option>` +
      fuentes.temas.map((t) => `<option value="${escapar(t.id)}">${escapar(t.etiqueta)}</option>`).join("");
    aplicarFiltro(tema);
    $("#lista-fuentes").innerHTML = fuentes.documentos.map((d) =>
      `<li><a href="${escapar(d.url)}" target="_blank" rel="noopener noreferrer">${escapar(d.titulo)}</a><span>${escapar(d.institucion)} · ${escapar(d.anio)}</span></li>`).join("");
    pintarHistorial(); // las etiquetas de tema ya están disponibles
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
cargarServicio();
