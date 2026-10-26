'use strict';
// Valedores Studio: interfaz de un solo fichero, sin dependencias. El texto del usuario/agente siempre entra por textContent.

const $vista = document.getElementById('vista');
const $aviso = document.getElementById('aviso');
let ESTADO = null;          // /api/estado
let limpiar = [];           // funciones a llamar al cambiar de pantalla (SSE, temporizadores)

// ---------------------------------------------------------------- utilidades
function h(tag, attrs, ...hijos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'value') e.value = v;
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const c of hijos.flat()) if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(c));
  return e;
}

function avisar(texto, ms = 3000) {
  $aviso.textContent = texto; $aviso.hidden = false;
  clearTimeout(avisar.t); avisar.t = setTimeout(() => { $aviso.hidden = true; }, ms);
}

async function api(ruta, opts = {}) {
  const o = Object.assign({ headers: {} }, opts);
  if (o.metodo) { o.method = o.metodo; delete o.metodo; }
  if (o.method && o.method !== 'GET') o.headers['X-Estudio'] = '1';
  if (o.json !== undefined) { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(o.json); delete o.json; }
  const r = await fetch(ruta, o);
  let d = null;
  try { d = await r.json(); } catch (e) { /* sin cuerpo */ }
  if (!r.ok) throw new Error((d && d.error) || ('Error ' + r.status));
  return d;
}

function tamano(n) {
  if (n > 1 << 30) return (n / (1 << 30)).toFixed(1) + ' GB';
  if (n > 1 << 20) return (n / (1 << 20)).toFixed(1) + ' MB';
  return Math.max(1, Math.round(n / 1024)) + ' KB';
}

async function cargarEstado() { ESTADO = await api('/api/estado'); return ESTADO; }
const juegoPor = id => ESTADO.juegos.find(j => j.id === id);

function ampliar(src) {
  const m = h('div', { class: 'modal', onclick: () => m.remove() }, h('img', { src }));
  document.body.append(m);
}

function selector(opciones, actual, onchange) {
  const s = h('select', { onchange: () => onchange(s.value) },
    opciones.map(([v, t]) => h('option', { value: v, selected: v === actual }, t)));
  return s;
}

// ---------------------------------------------------------------- enrutado
async function ruta() {
  limpiar.forEach(f => { try { f(); } catch (e) { /* nada */ } });
  limpiar = [];
  const hash = location.hash.replace(/^#/, '') || '/';
  document.querySelectorAll('[data-nav]').forEach(a => {
    const k = a.dataset.nav;
    a.classList.toggle('activo', (k === 'inicio' && hash === '/') || (k !== 'inicio' && hash.startsWith('/' + k)) ||
      (k === 'proyectos' && hash.startsWith('/p/')));
  });
  try {
    await cargarEstado();
    let m;
    if (hash === '/') pantallaJuegos();
    else if (hash === '/proyectos') pantallaProyectos();
    else if ((m = hash.match(/^\/p\/([\w-]+)$/))) await pantallaProyecto(m[1]);
    else if (hash === '/bandejas') await pantallaBandejas();
    else if (hash === '/sistema') await pantallaSistema();
    else $vista.replaceChildren(h('div', { class: 'pagina' }, 'No existe esta pantalla.'));
  } catch (e) {
    $vista.replaceChildren(h('div', { class: 'pagina' }, h('h1', {}, 'Algo ha fallado'), h('p', { class: 'suave' }, e.message)));
  }
}
window.addEventListener('hashchange', ruta);

// ---------------------------------------------------------------- juegos
function galeria(imgs) {
  const g = h('div', { class: 'galeria' });
  if (!imgs.length) { g.append(h('div', { class: 'vacia' }, '🎮')); return g; }
  const els = imgs.map((s, i) => h('img', { src: s, loading: 'lazy', class: i === 0 ? 'on' : '', alt: '' }));
  g.append(...els);
  if (els.length > 1) {
    let i = 0, t = null;
    const paso = () => { els[i].classList.remove('on'); i = (i + 1) % els.length; els[i].classList.add('on'); };
    g.addEventListener('mouseenter', () => { paso(); t = setInterval(paso, 1400); });
    g.addEventListener('mouseleave', () => { clearInterval(t); });
  }
  return g;
}

function pantallaJuegos() {
  const rej = h('div', { class: 'rejilla' }, ESTADO.juegos.map(j => {
    const acc = h('div', { class: 'acciones' },
      h('button', { class: 'primario', onclick: () => formularioProyecto(j) }, 'Crear vídeo'));
    if (j.rom && j.estado !== 'al_dia') acc.append(h('button', { onclick: () => extraer(j) }, j.estado === 'sin_extraer' ? 'Extraer assets' : 'Actualizar assets'));
    return h('div', { class: 'juego' },
      galeria(j.vistas),
      h('div', { class: 'cuerpo' },
        h('div', { class: 'fila', style: 'justify-content:space-between;align-items:center' },
          h('h3', {}, j.nombre), h('span', { class: 'etiqueta ' + j.estado }, j.etiqueta)),
        h('p', {}, j.descripcion),
        !j.rom && j.estado === 'sin_rom' ? h('p', { class: 'suave' }, 'Deja tu ROM (código ' + j.rom_codigos.join(' / ') + ') en la carpeta roms/.') : null,
        acc));
  }));
  $vista.replaceChildren(h('div', { class: 'pagina' },
    h('h1', {}, '¿De qué juego va el vídeo?'),
    h('p', { class: 'sub' }, 'Elige un juego, cuéntale la idea al agente y ve validando cada parte.'),
    rej));
}

function opcionesAgente(sel, cont) {
  const ag = ESTADO.agentes;
  const modelos = ag[sel.agente].modelos.map(m => [m.id, m.nombre]);
  cont.replaceChildren(
    h('div', { class: 'fila' },
      h('div', {}, h('label', {}, 'Modelo'), selector(modelos, sel.modelo, v => { sel.modelo = v; })),
      h('div', {}, h('label', {}, 'Esfuerzo'), selector(ag[sel.agente].esfuerzos.map(e => [e, e]), sel.esfuerzo, v => { sel.esfuerzo = v; }))));
}

function formularioProyecto(j) {
  const ag = ESTADO.agentes;
  const disp = Object.keys(ag).filter(k => ag[k].disponible);
  if (!disp.length) { avisar('No hay ningún agente instalado (claude o codex).', 5000); return; }
  const sel = { agente: disp[0], modelo: ag[disp[0]].modelo_defecto, esfuerzo: ag[disp[0]].esfuerzo_defecto, ritmo: 'paso_a_paso', formato: (j.formatos[0] || {}).id };
  const cont = h('div');
  opcionesAgente(sel, cont);
  const titulo = h('input', { placeholder: 'Título del vídeo' });
  const brief = h('textarea', { rows: 8, placeholder: 'Tu idea o el guion tal cual: qué pasa, quién sale, el tono, la duración… Puedes dejarlo corto y afinarlo en el chat.' });
  const err = h('p', { class: 'suave' });
  const modal = h('div', { class: 'modal', onclick: ev => { if (ev.target === modal) modal.remove(); } },
    h('div', { class: 'tarjeta', style: 'width:min(640px,100%);max-height:100%;overflow:auto' },
      h('h2', { style: 'margin-top:0' }, 'Nuevo vídeo de ' + j.corto),
      h('label', {}, 'Título'), titulo,
      h('div', { class: 'fila' },
        h('div', {}, h('label', {}, 'Formato'), selector(j.formatos.map(f => [f.id, f.nombre]), sel.formato, v => { sel.formato = v; })),
        h('div', {}, h('label', {}, 'Ritmo'), selector(Object.entries(ESTADO.ritmos).map(([k, t]) => [k, t.split(':')[0]]), sel.ritmo, v => { sel.ritmo = v; }))),
      h('p', { class: 'suave', style: 'font-size:13px' }, 'Paso a paso: se detiene en cada fase para que valides. De una: lo hace todo seguido.'),
      h('label', {}, 'Agente'),
      selector(Object.keys(ag).map(k => [k, ag[k].nombre + (ag[k].disponible ? '' : ' (no instalado)')]), sel.agente, v => {
        if (!ag[v].disponible) { avisar('«' + ag[v].nombre + '» no está instalado.'); return; }
        sel.agente = v; sel.modelo = ag[v].modelo_defecto; sel.esfuerzo = ag[v].esfuerzo_defecto; opcionesAgente(sel, cont);
      }),
      cont,
      h('label', {}, 'Idea / guion'), brief, err,
      h('div', { class: 'acciones', style: 'margin-top:14px;justify-content:flex-end' },
        h('button', { onclick: () => modal.remove() }, 'Cancelar'),
        h('button', { class: 'primario', onclick: async ev => {
          ev.target.disabled = true;
          try {
            const p = await api('/api/proyectos', { metodo: 'POST', json: {
              titulo: titulo.value, juego: j.id, formato: sel.formato, ritmo: sel.ritmo, agente: sel.agente, modelo: sel.modelo,
              esfuerzo: sel.esfuerzo, brief: brief.value } });
            if (brief.value.trim()) {
              const seguir = sel.ritmo === 'de_una' ? 'Hazlo todo seguido y enséñame el resultado final.' : 'Empieza por la fase «idea» y párate para que la valide.';
              sessionStorage.setItem('primer-' + p.slug, 'Esta es mi idea (también está en brief.md):\n\n' + brief.value.trim() + '\n\n' + seguir);
            }
            modal.remove();
            location.hash = '#/p/' + p.slug;
          } catch (e) { err.textContent = e.message; ev.target.disabled = false; }
        } }, 'Crear y empezar'))));
  document.body.append(modal);
  titulo.focus();
}

async function extraer(j) {
  const reg = h('div', { class: 'reg' }, 'Iniciando…');
  const estado = h('span', { class: 'etiqueta aviso' }, 'extrayendo');
  const cerrar = h('button', { onclick: () => { clearInterval(t); modal.remove(); ruta(); } }, 'Cerrar');
  const modal = h('div', { class: 'modal' }, h('div', { class: 'tarjeta', style: 'width:min(760px,100%)' },
    h('h2', { style: 'margin-top:0' }, 'Extrayendo assets de ' + j.corto + ' ', estado), reg,
    h('div', { class: 'acciones', style: 'margin-top:12px;justify-content:flex-end' }, cerrar)));
  document.body.append(modal);
  let t = null;
  try { await api('/api/extraer/' + j.id, { metodo: 'POST' }); } catch (e) { reg.textContent = e.message; return; }
  let desde = 0; reg.textContent = '';
  t = setInterval(async () => {
    try {
      const d = await api('/api/extraer/' + j.id + '?desde=' + desde);
      if (d.lineas.length) { reg.append(document.createTextNode(d.lineas.join('\n') + '\n')); reg.scrollTop = reg.scrollHeight; }
      desde = d.total;
      if (d.estado !== 'corriendo') {
        clearInterval(t); estado.textContent = d.estado === 'ok' ? 'terminado' : 'con error';
        estado.className = 'etiqueta ' + (d.estado === 'ok' ? 'al_dia' : 'error');
      }
    } catch (e) { clearInterval(t); }
  }, 1000);
}

// ---------------------------------------------------------------- lista de proyectos
function pantallaProyectos() {
  const ps = ESTADO.proyectos;
  $vista.replaceChildren(h('div', { class: 'pagina' },
    h('h1', {}, 'Proyectos'), h('p', { class: 'sub' }, 'Cada vídeo es un proyecto con su chat y sus fases.'),
    ps.length ? h('div', { class: 'lista' }, ps.map(p => {
      const j = juegoPor(p.juego);
      const pend = Object.entries(p.fases).find(([, f]) => f.estado === 'validar');
      return h('div', { class: 'item', onclick: () => { location.hash = '#/p/' + p.slug; } },
        h('div', { class: 'grow' }, h('div', { class: 't' }, p.titulo),
          h('div', { class: 'suave', style: 'font-size:13px' }, (j ? j.corto : p.juego) + ' · ' + p.actualizado)),
        pend ? h('span', { class: 'est validar' }, 'espera tu validación: ' + pend[0]) : h('span', { class: 'est' }, 'fase: ' + p.fase_actual));
    })) : h('div', { class: 'tarjeta' }, 'Aún no hay proyectos. ', h('a', { href: '#/' }, 'Crea el primero eligiendo un juego.')),
  ));
}

// ---------------------------------------------------------------- proyecto + chat
async function pantallaProyecto(slug) {
  let vp = await api('/api/proyectos/' + slug);
  let faseSel = vp.proyecto.fase_actual;
  const j = juegoPor(vp.proyecto.juego);

  const colIzq = h('div', { class: 'col izq' });
  const mensajes = h('div', { class: 'mensajes' });
  const texto = h('textarea', { rows: 2, placeholder: 'Escribe al agente… (Enter envía, Mayús+Enter salto de línea)' });
  const btnEnviar = h('button', { class: 'primario', onclick: () => enviar() }, 'Enviar');
  const btnParar = h('button', { class: 'peligro', hidden: true, onclick: () => api('/api/proyectos/' + slug + '/parar', { metodo: 'POST' }) }, 'Parar');
  const estadoTxt = h('span', { class: 'suave' });
  const rapidos = h('div', { class: 'rapidos' }, [
    ['Solo el guion', 'Hazme solo la fase de guion y párate para que la valide.'],
    ['Solo la música', 'Hazme solo la música (con audio de muestra) y párate para que la escuche.'],
    ['Storyboard', 'Prepara el storyboard y párate para validarlo.'],
    ['Previsualización', 'Genera la previsualización (fotogramas clave) y párate.'],
    ['Todo de una', 'Hazlo todo seguido hasta el vídeo final y la revisión, y enséñame solo el resultado.'],
  ].map(([t, m]) => h('button', { onclick: () => enviar(m) }, t)));
  const colCentro = h('div', { class: 'col chat' }, mensajes,
    h('div', { class: 'compositor' }, rapidos, texto, h('div', { class: 'pie' }, btnEnviar, btnParar, estadoTxt)));
  const colDer = h('div', { class: 'col der' });
  $vista.replaceChildren(h('div', { class: 'proyecto' }, colIzq, colCentro, colDer));

  // ---- chat
  let vivo = null, ocupado = vp.ocupado;
  const herr = {};
  const abajo = () => { mensajes.scrollTop = mensajes.scrollHeight; };
  function fijarOcupado(o) {
    ocupado = o; btnEnviar.disabled = o; btnParar.hidden = !o;
    estadoTxt.replaceChildren(o ? h('span', { class: 'puntos' }, 'El agente está trabajando') : '');
  }
  function pintar(ev) {
    switch (ev.t) {
      case 'usuario': mensajes.append(h('div', { class: 'msg usuario' }, ev.texto)); break;
      case 'delta':
        if (!vivo) { vivo = h('div', { class: 'msg agente' }); mensajes.append(vivo); }
        vivo.append(document.createTextNode(ev.texto)); break;
      case 'asistente':
        if (vivo) { vivo.remove(); vivo = null; }
        if (ev.texto && ev.texto.trim()) mensajes.append(h('div', { class: 'msg agente' }, ev.texto)); break;
      case 'herramienta': {
        vivo = null;
        const e = h('div', { class: 'herr', title: ev.resumen }, '⚙ ' + ev.nombre + (ev.resumen ? ': ' + ev.resumen : ''));
        herr[ev.id] = e; mensajes.append(e); break; }
      case 'resultado':
        if (herr[ev.id] && !ev.ok) herr[ev.id].append(' ✗ ' + (ev.resumen || 'falló'));
        break;
      case 'fin': vivo = null;
        if (ev.duracion || ev.coste) mensajes.append(h('div', { class: 'msg sistema' }, 'Turno terminado' + (ev.duracion ? ' en ' + ev.duracion.toFixed(0) + ' s' : '') + (ev.coste ? ' · ' + ev.coste.toFixed(3) + ' $' : '')));
        break;
      case 'error': vivo = null; mensajes.append(h('div', { class: 'msg error' }, '✗ ' + ev.texto)); break;
      case 'sistema': mensajes.append(h('div', { class: 'msg sistema' }, ev.texto)); break;
      case 'estado': fijarOcupado(ev.estado === 'trabajando'); if (!ocupado) vivo = null; return;
      case 'proyecto': refrescar(); return;
    }
    abajo();
  }

  async function enviar(msg) {
    const t = (msg || texto.value).trim();
    if (!t || ocupado) return;
    if (!msg) texto.value = '';
    try { await api('/api/proyectos/' + slug + '/chat', { metodo: 'POST', json: { texto: t } }); }
    catch (e) { avisar(e.message, 4500); }
  }
  texto.addEventListener('keydown', ev => { if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); enviar(); } });

  if (!/[?&]nosse/.test(location.search)) {      // ?nosse: sin tiempo real (para capturas de pantalla automáticas)
    const es = new EventSource('/api/proyectos/' + slug + '/eventos');
    es.onmessage = m => pintar(JSON.parse(m.data));
    limpiar.push(() => es.close());
  }

  // ---- paneles
  async function refrescar() {
    try { vp = await api('/api/proyectos/' + slug); } catch (e) { return; }
    pintarIzq(); pintarDer();
  }
  let tmr = null;
  const pend = () => { clearTimeout(tmr); tmr = setTimeout(refrescar, 400); };
  limpiar.push(() => clearTimeout(tmr));

  function pintarIzq() {
    const p = vp.proyecto, ag = ESTADO.agentes[p.agente];
    const guardar = async (campo, valor) => {
      try { await api('/api/proyectos/' + slug, { metodo: 'PATCH', json: { [campo]: valor } }); pend(); } catch (e) { avisar(e.message); }
    };
    colIzq.replaceChildren(
      h('h2', { style: 'margin-top:0' }, p.titulo),
      h('div', { class: 'suave', style: 'font-size:13px' }, j ? j.nombre : p.juego),
      h('label', {}, 'Agente'),
      selector(Object.keys(ESTADO.agentes).map(k => [k, ESTADO.agentes[k].nombre]), p.agente, async v => {
        const a = ESTADO.agentes[v];
        if (!a.disponible) { avisar('«' + a.nombre + '» no está instalado.'); refrescar(); return; }
        await api('/api/proyectos/' + slug, { metodo: 'PATCH', json: { agente: v, modelo: a.modelo_defecto, esfuerzo: a.esfuerzo_defecto } }); pend();
      }),
      h('label', {}, 'Modelo'), selector(ag.modelos.map(m => [m.id, m.nombre]), p.modelo, v => guardar('modelo', v)),
      h('label', {}, 'Esfuerzo'), selector(ag.esfuerzos.map(e => [e, e]), p.esfuerzo, v => guardar('esfuerzo', v)),
      h('label', {}, 'Ritmo'), selector(Object.entries(ESTADO.ritmos).map(([k, t]) => [k, t.split(':')[0]]), p.ritmo, v => guardar('ritmo', v)),
      h('label', {}, 'Permisos del agente'), selector(Object.entries(ESTADO.permisos).map(([k, t]) => [k, t.split(':')[0]]), p.permisos || 'normal', v => guardar('permisos', v)),
      h('h2', {}, 'Fases'),
      ...vp.fases.map(f => h('div', { class: 'fase' + (f.id === faseSel ? ' actual' : ''), onclick: () => { faseSel = f.id; pintarIzq(); pintarDer(); } },
        h('div', { class: 'n' }, f.nombre, h('span', { class: 'est ' + f.estado }, f.estado.replace('_', ' '))),
        h('div', { class: 'r' }, f.resumen))));
  }

  async function mostrar(a) {
    if (a.tipo === 'video') return h('video', { src: a.url, controls: true, preload: 'metadata' });
    if (a.tipo === 'audio') return h('audio', { src: a.url, controls: true });
    if (a.tipo === 'imagen') return h('img', { src: a.url, loading: 'lazy', onclick: () => ampliar(a.url), style: 'cursor:zoom-in' });
    if (a.tipo === 'texto' || a.tipo === 'codigo') {
      const pre = h('pre', {}, 'Cargando…');
      fetch(a.url).then(r => r.text()).then(t => { pre.textContent = t.slice(0, 60000); }).catch(() => { pre.textContent = '(no se pudo leer)'; });
      return pre;
    }
    return null;
  }

  async function pintarDer() {
    const f = vp.fases.find(x => x.id === faseSel) || vp.fases[0];
    const caja = h('div', { class: 'visor' }, h('h3', {}, f.nombre), h('div', { class: 'suave', style: 'font-size:13px' }, f.resumen));
    if (f.nota) caja.append(h('p', {}, h('b', {}, 'Nota: '), f.nota));
    const decidir = (accion) => async () => {
      let nota = '';
      if (accion === 'cambios') { nota = prompt('¿Qué hay que cambiar?'); if (!nota) return; }
      try {
        await api('/api/proyectos/' + slug + '/fase', { metodo: 'POST', json: { fase: f.id, accion, nota } });
        if (accion === 'aprobar') enviar('✅ Fase «' + f.id + '» aprobada. Sigue con la siguiente' + (vp.proyecto.ritmo === 'paso_a_paso' ? ' y párate al terminarla.' : '.'));
        else if (accion === 'cambios') enviar('Cambios en la fase «' + f.id + '»: ' + nota);
        pend();
      } catch (e) { avisar(e.message); }
    };
    caja.append(h('div', { class: 'validacion' },
      h('button', { class: 'ok', onclick: decidir('aprobar'), disabled: f.estado === 'aprobada' }, 'Aprobar'),
      h('button', { onclick: decidir('cambios') }, 'Pedir cambios'),
      f.estado === 'omitida' || f.estado === 'aprobada' ? h('button', { onclick: decidir('reabrir') }, 'Reabrir') : h('button', { onclick: decidir('omitir') }, 'Omitir')));
    const imgs = f.artefactos.filter(a => a.tipo === 'imagen');
    if (imgs.length > 1) {
      caja.append(h('div', { class: 'miniaturas' }, imgs.map(a => h('img', { src: a.url, loading: 'lazy', onclick: () => ampliar(a.url) }))));
    }
    for (const a of f.artefactos) {
      if (imgs.length > 1 && a.tipo === 'imagen') continue;
      const v = await mostrar(a);
      caja.append(h('div', { class: 'suave', style: 'font-size:12.5px;margin:6px 0 3px' }, a.nombre), v);
    }
    if (!f.artefactos.length) caja.append(h('p', { class: 'suave' }, 'Todavía no hay nada que ver en esta fase.'));
    const otros = vp.entradas;
    colDer.replaceChildren(caja,
      h('h3', { style: 'font-size:15px' }, 'Tus ficheros de entrada'),
      ...(otros.length ? otros.map(e => h('div', { class: 'arch' }, h('a', { href: e.url, target: '_blank' }, e.nombre))) : [h('p', { class: 'suave' }, 'Nada todavía.')]),
      subidor(slug, pend));
  }

  pintarIzq(); pintarDer(); fijarOcupado(ocupado);
  const primero = sessionStorage.getItem('primer-' + slug);
  if (primero) { sessionStorage.removeItem('primer-' + slug); setTimeout(() => enviar(primero), 300); }
}

function subidor(slug, tras) {
  const entrada = h('input', { type: 'file', multiple: true, hidden: true });
  const zona = h('div', { class: 'dropzona', onclick: () => entrada.click() }, 'Arrastra aquí fotos, vídeos, audios…', h('br'), h('span', { class: 'suave' }, 'o haz clic'));
  async function subir(files) {
    for (const f of files) {
      try {
        zona.firstChild.textContent = 'Subiendo ' + f.name + '…';
        await api('/api/entrada?nombre=' + encodeURIComponent(f.name) + (slug ? '&proyecto=' + slug : ''), { metodo: 'POST', body: f });
      } catch (e) { avisar(e.message, 4500); }
    }
    zona.firstChild.textContent = 'Arrastra aquí fotos, vídeos, audios…';
    avisar('Subido'); if (tras) tras();
  }
  entrada.addEventListener('change', () => subir([...entrada.files]));
  zona.addEventListener('dragover', e => { e.preventDefault(); zona.classList.add('sobre'); });
  zona.addEventListener('dragleave', () => zona.classList.remove('sobre'));
  zona.addEventListener('drop', e => { e.preventDefault(); zona.classList.remove('sobre'); subir([...e.dataTransfer.files]); });
  return h('div', {}, zona, entrada);
}

// ---------------------------------------------------------------- bandejas
function cuadricula(fs) {
  if (!fs.length) return h('p', { class: 'suave' }, 'Vacía.');
  return h('div', { class: 'cuadricula' }, fs.map(f => h('div', { class: 'c' },
    f.tipo === 'video' ? h('video', { src: f.url, controls: true, preload: 'metadata' })
      : f.tipo === 'imagen' ? h('img', { src: f.url, loading: 'lazy', onclick: () => ampliar(f.url) })
        : f.tipo === 'audio' ? h('audio', { src: f.url, controls: true, style: 'width:100%' }) : null,
    h('div', { title: f.ruta }, h('a', { href: f.url, target: '_blank' }, f.nombre), ' · ' + tamano(f.tam)))));
}

async function pantallaBandejas() {
  const [ent, sal] = await Promise.all([api('/api/entrada'), api('/api/salida')]);
  $vista.replaceChildren(h('div', { class: 'pagina' },
    h('h1', {}, 'Entrada y salida'),
    h('p', { class: 'sub' }, 'Entrada: lo que dejas para que la IA lo use. Salida: los vídeos resultado (no se suben a Git).'),
    h('h2', {}, 'Bandeja de entrada'), subidor('', ruta), cuadricula(ent),
    h('h2', {}, 'Bandeja de salida'), cuadricula(sal)));
}

async function pantallaSistema() {
  const d = await api('/api/doctor');
  const icono = { ok: '✓', aviso: '!', error: '✗' };
  $vista.replaceChildren(h('div', { class: 'pagina' },
    h('h1', {}, 'Sistema'), h('p', { class: 'sub' }, 'Lo que el estudio necesita para funcionar (equivale a `python valedores.py doctor`).'),
    h('div', { class: 'tarjeta lista' }, d.map(x => h('div', {}, h('span', { class: 'etiqueta ' + (x.nivel === 'ok' ? 'al_dia' : x.nivel) }, icono[x.nivel]), ' ', x.texto))),
    h('h2', {}, 'ROMs y assets'),
    h('div', { class: 'tarjeta lista' }, ESTADO.juegos.map(j => h('div', { class: 'fila', style: 'align-items:center' },
      h('b', {}, j.nombre), h('span', { class: 'etiqueta ' + j.estado }, j.etiqueta),
      h('span', { class: 'suave' }, j.rom ? 'ROM detectada' : 'Falta la ROM (' + j.rom_codigos.join('/') + ')'),
      j.rom && j.estado !== 'al_dia' ? h('button', { onclick: () => extraer(j) }, 'Extraer') : h('span')))),
  ));
}

ruta();
