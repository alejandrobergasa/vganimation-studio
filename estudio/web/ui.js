'use strict';
// Piezas comunes de la interfaz: textos, iconos, formatos, indicadores de carga y barras de progreso basadas en el tiempo estimado.

const ESTADO_TXT = {
  pendiente: 'Pendiente', en_curso: 'En curso', validar: 'Espera tu validación', aprobada: 'Aprobada',
  cambios: 'Cambios por rehacer', omitida: 'Omitida',
};
const ESTADO_CORTO = { pendiente: 'pendiente', en_curso: 'en curso', validar: 'a validar', aprobada: 'aprobada', cambios: 'con cambios', omitida: 'omitida' };
const GLIFO_ESTADO = { pendiente: '○', validar: '●', aprobada: '✓', cambios: '✎', omitida: '–' };
const ICONO_FASE = { idea: '💡', guion: '📝', musica: '🎵', storyboard: '🧩', escenas: '🖼️', render: '🎞️', revision: '🔍' };
const ICONO_TIPO = {
  guion: '📝', musica: '🎵', personaje: '🧑', escenario: '🏞️', escena: '🎬', voz: '🗣️', efecto: '✨', texto: '🔤', imagen: '🖼️', video: '🎞️', otro: '📦',
};
const NOMBRE_CARRIL = { principal: 'Principal' };

// ---------------------------------------------------------------- formatos
function fmtTok(n) {
  n = Math.round(n || 0);
  if (n < 1000) return String(n);
  if (n < 1e6) return (n / 1000).toFixed(n < 10000 ? 1 : 0).replace('.', ',') + ' k';
  return (n / 1e6).toFixed(2).replace('.', ',') + ' M';
}

function fmtUsd(c) {
  if (c == null) return '— $';
  const dec = c === 0 ? 2 : c < 0.1 ? 3 : 2;
  return c.toLocaleString('es-ES', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + ' $';
}

function fmtTiempo(seg) {
  seg = Math.max(0, Math.round(seg));
  const m = Math.floor(seg / 60), s = seg % 60;
  if (m >= 60) return Math.floor(m / 60) + ':' + String(m % 60).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  return m + ':' + String(s).padStart(2, '0');
}

// Entrada total = lo nuevo + lo leído de caché + lo escrito en caché (todo lo que el modelo tuvo que leer).
const entradaTotal = u => (u.entrada || 0) + (u.cache_leida || 0) + (u.cache_escrita || 0);

// ---------------------------------------------------------------- indicadores
function spinner(clase) { return h('span', { class: 'spin' + (clase ? ' ' + clase : ''), role: 'status', 'aria-label': 'En proceso' }); }

function iconoEstado(estado) {
  if (estado === 'en_curso') return spinner();
  return h('span', { class: 'ei ' + estado, title: ESTADO_TXT[estado] }, GLIFO_ESTADO[estado] || '○');
}

// Reloj del servidor: las horas de inicio vienen de él, no del navegador.
let DESFASE = 0;
const ahoraServidor = () => Date.now() / 1000 + DESFASE;
function sincronizarReloj(servidorAhora) { if (servidorAhora) DESFASE = servidorAhora - Date.now() / 1000; }

const mediana = v => { const o = [...v].sort((a, b) => a - b); return o.length ? o[Math.floor(o.length / 2)] : null; };
const previstoDe = d => d.eta || (d.duraciones && d.duraciones.length ? mediana(d.duraciones) : null);

function calcProgreso(d, ahora) {
  const el = d.inicio ? Math.max(0, ahora - d.inicio) : 0;
  const eta = previstoDe(d);
  if (d.progreso != null) return { frac: d.progreso / 100, el, eta, real: true };
  if (!eta) return { frac: null, el, eta: null };
  return { frac: Math.min(el / eta, 0.96), el, eta, tarde: el > eta };
}

const barras = new Set();

// Barra de progreso de algo en curso. Con progreso real (`progreso`) lo enseña tal cual; si no, avanza con el tiempo hasta el estimado
// (`eta` del agente o la mediana de veces anteriores) y se queda al 96 % si tarda más; sin estimación es una barra indeterminada con el reloj.
function barraTiempo(d, opciones) {
  const o = opciones || {};
  const relleno = h('div', { class: 'rel' });
  const txt = h('span', { class: 'txt' });
  const el = h('div', { class: 'prog' + (o.fina ? ' fina' : '') }, h('div', { class: 'pista' }, relleno), o.sinTexto ? null : txt);
  const b = { el, d, relleno, txt };
  barras.add(b);
  actualizarBarra(b);
  return el;
}

function actualizarBarra(b) {
  const p = calcProgreso(b.d, ahoraServidor());
  b.el.classList.toggle('indet', p.frac == null);
  b.el.classList.toggle('tarde', !!p.tarde);
  b.relleno.style.width = p.frac == null ? '' : Math.round(p.frac * 100) + '%';
  let t;
  if (p.real) t = Math.round(p.frac * 100) + ' %' + (b.d.inicio ? ' · ' + fmtTiempo(p.el) : '');
  else if (p.tarde) t = fmtTiempo(p.el) + ' · tarda más de lo previsto';
  else if (p.eta) t = fmtTiempo(p.el) + ' / ~' + fmtTiempo(p.eta);
  else t = b.d.inicio ? fmtTiempo(p.el) : '';
  if (b.txt.textContent !== t) b.txt.textContent = t;
}

function tickBarras() {
  for (const b of barras) {
    if (!b.el.isConnected) { barras.delete(b); continue; }
    actualizarBarra(b);
  }
}

// ---------------------------------------------------------------- ventanas flotantes
// Popover anclado a un botón; se cierra al hacer clic fuera o con Escape. Devuelve la función que lo cierra.
function popover(ancla, contenido, opciones) {
  const o = opciones || {};
  const pop = h('div', { class: 'pop' + (o.clase ? ' ' + o.clase : '') }, contenido);
  document.body.append(pop);
  const r = ancla.getBoundingClientRect();
  const w = pop.offsetWidth;
  pop.style.top = Math.round(r.bottom + 8) + 'px';
  pop.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, o.izquierda ? r.left : r.right - w)) + 'px';
  const cerrar = () => { pop.remove(); document.removeEventListener('mousedown', fuera, true); document.removeEventListener('keydown', tecla, true); ancla.classList.remove('abierto'); };
  const fuera = e => { if (!pop.contains(e.target) && !ancla.contains(e.target)) cerrar(); };
  const tecla = e => { if (e.key === 'Escape') cerrar(); };
  document.addEventListener('mousedown', fuera, true);
  document.addEventListener('keydown', tecla, true);
  ancla.classList.add('abierto');
  pop.cerrar = cerrar;
  return cerrar;
}

function dialogo(titulo, cuerpo, acciones, ancho) {
  const cerrar = () => { m.remove(); document.removeEventListener('keydown', tecla, true); };
  const tecla = e => { if (e.key === 'Escape') cerrar(); };
  const m = h('div', { class: 'modal', onclick: ev => { if (ev.target === m) cerrar(); } },
    h('div', { class: 'tarjeta dialogo', style: ancho ? 'width:min(' + ancho + 'px,100%)' : null },
      h('h2', {}, titulo), cuerpo, h('div', { class: 'acciones fin' }, acciones(cerrar))));
  document.addEventListener('keydown', tecla, true);
  document.body.append(m);
  return { cerrar, el: m };
}
