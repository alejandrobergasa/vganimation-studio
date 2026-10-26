'use strict';
// VGAnimation Studio: interfaz de un solo fichero, sin dependencias. El texto del usuario/agente siempre entra por textContent.

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

// Sube un fichero a entrada/ (o entrada/<proyecto>/) con progreso. Devuelve {ruta, nombre, tipo, url, tam}.
function subirFichero(file, slug, progreso) {
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest();
    x.open('POST', '/api/entrada?nombre=' + encodeURIComponent(file.name) + (slug ? '&proyecto=' + slug : ''));
    x.setRequestHeader('X-Estudio', '1');
    x.upload.onprogress = e => { if (e.lengthComputable && progreso) progreso(e.loaded / e.total); };
    x.onload = () => {
      let d = null;
      try { d = JSON.parse(x.responseText); } catch (e) { /* sin cuerpo */ }
      if (x.status >= 200 && x.status < 300) resolve(d); else reject(new Error((d && d.error) || ('Error ' + x.status)));
    };
    x.onerror = () => reject(new Error('No se pudo subir ' + file.name));
    x.send(file);
  });
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
    const acc = h('div', { class: 'acciones' });
    if (j.formatos.length) acc.append(h('button', { class: 'primario', onclick: () => formularioProyecto(j) }, 'Crear vídeo'));
    else acc.append(h('span', { class: 'suave' }, 'Extracción de recursos · motor de vídeo pendiente'));
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

  // adjuntos del formulario: se guardan en memoria y se suben al crear el proyecto (hace falta su carpeta)
  const locales = [];
  const chips = h('div', { class: 'chips' });
  const tipoLocal = f => /^image\//.test(f.type) ? 'imagen' : /^video\//.test(f.type) ? 'video' : /^audio\//.test(f.type) ? 'audio' : 'otro';
  function pintarLocales() {
    chips.replaceChildren(...locales.map(a => h('div', { class: 'chip' },
      a.tipo === 'imagen' ? h('img', { src: a.vista }) : h('span', { class: 'ico' }, { video: '🎬', audio: '🎵' }[a.tipo] || '📄'),
      h('span', { class: 'nom', title: a.file.name }, a.file.name),
      h('span', { class: 'prog' }, a.progreso != null ? Math.round(a.progreso * 100) + '%' : tamano(a.file.size)),
      h('button', { class: 'x', title: 'Quitar', onclick: () => { locales.splice(locales.indexOf(a), 1); pintarLocales(); } }, '×'))));
  }
  function anadir(files) {
    for (const f of files) {
      if (!f.name) continue;
      const tipo = tipoLocal(f);
      locales.push({ file: f, tipo, vista: tipo === 'imagen' ? URL.createObjectURL(f) : null });
    }
    pintarLocales();
  }
  const selFicheros = h('input', { type: 'file', multiple: true, hidden: true, onchange: () => { anadir([...selFicheros.files]); selFicheros.value = ''; } });
  const zonaAdj = h('div', { class: 'dropzona', style: 'padding:14px', onclick: () => selFicheros.click() },
    '📎 Adjunta fotos, vídeos de referencia, audios o assets (arrastra aquí o haz clic)');
  zonaAdj.addEventListener('dragover', e => { e.preventDefault(); zonaAdj.classList.add('sobre'); });
  zonaAdj.addEventListener('dragleave', () => zonaAdj.classList.remove('sobre'));
  zonaAdj.addEventListener('drop', e => { e.preventDefault(); zonaAdj.classList.remove('sobre'); anadir([...e.dataTransfer.files]); });
  brief.addEventListener('paste', e => {
    const fs = [...(e.clipboardData ? e.clipboardData.files : [])];
    if (!fs.length) return;
    e.preventDefault();
    anadir(fs.map(f => (f.name && f.name !== 'image.png') ? f : new File([f], 'captura_' + Date.now() + '.png', { type: f.type })));
  });

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
      h('label', {}, 'Idea / guion'), brief,
      h('label', {}, 'Adjuntos (opcional)'), chips, zonaAdj, selFicheros, err,
      h('div', { class: 'acciones', style: 'margin-top:14px;justify-content:flex-end' },
        h('button', { onclick: () => modal.remove() }, 'Cancelar'),
        h('button', { class: 'primario', onclick: async ev => {
          ev.target.disabled = true;
          try {
            const p = await api('/api/proyectos', { metodo: 'POST', json: {
              titulo: titulo.value, juego: j.id, formato: sel.formato, ritmo: sel.ritmo, agente: sel.agente, modelo: sel.modelo,
              esfuerzo: sel.esfuerzo, brief: brief.value } });
            const subidos = [];
            for (const a of locales) {
              a.progreso = 0; pintarLocales();
              const d = await subirFichero(a.file, p.slug, pr => { a.progreso = pr; pintarLocales(); });
              subidos.push(d.ruta);
            }
            if (brief.value.trim() || subidos.length) {
              const seguir = sel.ritmo === 'de_una' ? 'Hazlo todo seguido y enséñame el resultado final.' : 'Empieza por la fase «idea» y párate para que la valide.';
              const idea = brief.value.trim() ? 'Esta es mi idea (también está en brief.md):\n\n' + brief.value.trim() : 'Aún no tengo la idea escrita; mira los ficheros adjuntos y pregúntame lo que necesites.';
              sessionStorage.setItem('primer-' + p.slug, JSON.stringify({ texto: idea + '\n\n' + seguir, adjuntos: subidos }));
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
        h('div', { class: 'puntos-fases', title: ESTADO.fases.map(f => f.nombre + ': ' + ESTADO_CORTO[p.fases[f.id].estado]).join('\n') },
          ESTADO.fases.map(f => h('i', { class: p.fases[f.id].estado }))),
        pend ? h('span', { class: 'est validar' }, 'espera tu validación: ' + pend[0]) : h('span', { class: 'est' }, 'fase: ' + p.fase_actual));
    })) : h('div', { class: 'tarjeta' }, 'Aún no hay proyectos. ', h('a', { href: '#/' }, 'Crea el primero eligiendo un juego.')),
  ));
}

function subidor(slug, tras) {
  const entrada = h('input', { type: 'file', multiple: true, hidden: true });
  const zona = h('div', { class: 'dropzona', onclick: () => entrada.click() }, 'Arrastra aquí fotos, vídeos, audios…', h('br'), h('span', { class: 'suave' }, 'o haz clic'));
  async function subir(files) {
    for (const f of files) {
      try {
        zona.firstChild.textContent = 'Subiendo ' + f.name + '…';
        await subirFichero(f, slug, p => { zona.firstChild.textContent = 'Subiendo ' + f.name + ' ' + Math.round(p * 100) + '%'; });
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
