'use strict';
// Pantalla de un proyecto: cabecera con el consumo, el mapa del vídeo (fases y elementos, en paralelo donde se puede),
// detalle / cambios / ficheros, y a la derecha el chat con el agente (plegable y redimensionable).

function pref(clave, valor) {
  try {
    if (valor === undefined) return JSON.parse(localStorage.getItem('vga.' + clave));
    localStorage.setItem('vga.' + clave, JSON.stringify(valor));
  } catch (e) { /* sin almacenamiento: se usa el valor por defecto */ }
  return null;
}

// Fases que dependen (directa o indirectamente) de `fase`, según el mapa de dependencias del servidor.
function posterioresDe(fase) {
  const dep = ESTADO.dependencias, out = new Set(), pend = [fase];
  while (pend.length) {
    const x = pend.pop();
    for (const [f, ds] of Object.entries(dep)) if (ds.includes(x) && !out.has(f)) { out.add(f); pend.push(f); }
  }
  return out;
}

function nivelesDeFases() {
  const dep = ESTADO.dependencias, niv = {};
  const nivel = id => (id in niv ? niv[id] : (niv[id] = dep[id].length ? 1 + Math.max(...dep[id].map(nivel)) : 0));
  Object.keys(dep).forEach(nivel);
  return niv;
}

async function pantallaProyecto(slug) {
  let vp = await api('/api/proyectos/' + slug);
  sincronizarReloj(vp.ahora);
  const j = juegoPor(vp.proyecto.juego);
  const st = { sel: { tipo: 'fase', id: vp.proyecto.fase_actual }, auto: true, pestana: 'detalle', carril: 'principal', chatAbierto: pref('chatAbierto') !== false };
  const hilos = {};
  const usoVivo = {};                       // consumo del turno en curso de cada carril (aún no está en el total)
  let huellas = {};

  const fase = id => vp.fases.find(f => f.id === id);
  const elemento = id => vp.elementos.find(e => e.id === id);
  const hayTrabajo = () => vp.carriles.some(c => c.ocupado);

  // ================================================================ esqueleto
  const cab = h('header', { class: 'proy-cab' });
  const tareasEl = h('div', { class: 'tareas' });
  const mapaInt = h('div', { class: 'mapa-int' });
  const cables = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  cables.setAttribute('class', 'cables');
  const mapaEl = h('div', { class: 'mapa' }, mapaInt);
  const pestanasEl = h('div', { class: 'pestanas', role: 'tablist' });
  const cuerpoEl = h('div', { class: 'pestana-cuerpo' });
  const principal = h('section', { class: 'proy-main' },
    h('div', { class: 'mapa-caja' }, h('div', { class: 'mapa-tit' }, h('h2', {}, 'Mapa del vídeo'), leyenda()), tareasEl, mapaEl),
    pestanasEl, cuerpoEl);
  const sep = h('div', { class: 'sep', title: 'Arrastra para cambiar el ancho del chat' });
  const tabsChat = h('div', { class: 'chat-tabs' });
  const hilosEl = h('div', { class: 'hilos' });
  const velo = h('div', { class: 'velo', hidden: true }, 'Suelta los ficheros para adjuntarlos');
  const chips = h('div', { class: 'chips' });
  const texto = h('textarea', { rows: 1, placeholder: 'Escribe al agente… (Enter envía · Mayús+Enter salto de línea)' });
  const btnEnviar = h('button', { class: 'primario', onclick: () => enviar() }, 'Enviar');
  const btnParar = h('button', { class: 'peligro', hidden: true, onclick: () => api('/api/proyectos/' + slug + '/parar?carril=' + st.carril, { metodo: 'POST' }) }, 'Parar');
  const selectorFicheros = h('input', { type: 'file', multiple: true, hidden: true });
  const btnClip = h('button', { class: 'icono', title: 'Adjuntar fotos, vídeos, audios o assets', onclick: () => selectorFicheros.click() }, '📎');
  const compositor = h('div', { class: 'compositor' }, chips, texto, h('div', { class: 'pie' }, btnClip, h('span', { class: 'grow' }), btnParar, btnEnviar, selectorFicheros));
  const panelChat = h('aside', { class: 'chat-panel' }, tabsChat, hilosEl, compositor, velo);
  const cuerpo = h('div', { class: 'proy-cuerpo' }, principal, sep, panelChat);
  $vista.replaceChildren(h('div', { class: 'proy' }, cab, cuerpo));

  function leyenda() {
    return h('div', { class: 'leyenda' }, ['en_curso', 'validar', 'aprobada', 'cambios', 'pendiente'].map(e => h('span', {}, iconoEstado(e), ' ' + ESTADO_CORTO[e])));
  }

  // ================================================================ cabecera (los botones se crean una vez; solo cambian sus textos)
  const usoE = h('span', { class: 'u-e' }), usoS = h('span', { class: 'u-s' }), usoC = h('span', { class: 'u-c' });
  const btnUso = h('button', { class: 'uso', onclick: () => abrirUso() }, h('span', { class: 'punto-vivo', title: 'El agente está trabajando' }), usoE, usoS, usoC);
  const btnCambio = h('button', { class: 'primario', onclick: () => dialogoCambio(st.sel) }, '✎ Pedir cambio');
  const btnAjustes = h('button', { class: 'icono', title: 'Ajustes del proyecto', onclick: () => abrirAjustes() }, '⚙');
  const chatNum = h('span', { class: 'ins' });
  const btnChat = h('button', { class: 'chat-toggle', title: 'Mostrar u ocultar el chat', onclick: () => alternarChat() }, '💬', chatNum);
  const pillValidar = h('button', { class: 'pill-validar', hidden: true, onclick: () => { const f = vp.fases.find(x => x.estado === 'validar'); if (f) seleccionar('fase', f.id); } });
  const titulo = h('h1', {});
  const subtitulo = h('span', { class: 'suave' });
  cab.append(h('a', { class: 'atras', href: '#/proyectos', title: 'Todos los proyectos' }, '‹'),
    h('div', { class: 'cab-titulo' }, titulo, subtitulo), pillValidar, h('span', { class: 'grow' }),
    h('div', { class: 'cab-der' }, btnUso, btnCambio, btnAjustes, btnChat));

  function totalConVivo() {
    const t = Object.assign({}, vp.uso.total);
    for (const v of Object.values(usoVivo)) for (const k of ['entrada', 'salida', 'cache_leida', 'cache_escrita']) t[k] += v[k] || 0;
    return t;
  }

  function textoCoste(t) {
    if (!t.turnos) return fmtUsd(0);
    if (t.coste_completo) return fmtUsd(t.coste);
    return t.coste > 0 ? '≥ ' + fmtUsd(t.coste) : 'sin precio';
  }

  function pintarCab() {
    const p = vp.proyecto, t = totalConVivo();
    titulo.textContent = p.titulo;
    const fmt = j && j.formatos.find(f => f.id === p.formato);
    subtitulo.textContent = (j ? j.corto : p.juego) + (fmt ? ' · ' + fmt.nombre : '');
    usoE.textContent = '⬇ ' + fmtTok(entradaTotal(t));
    usoS.textContent = '⬆ ' + fmtTok(t.salida);
    usoC.textContent = textoCoste(t);
    btnUso.title = 'Entrada: ' + fmtTok(t.entrada) + ' nueva + ' + fmtTok(t.cache_leida + t.cache_escrita) + ' de caché · Salida: ' + fmtTok(t.salida) +
      (t.coste_completo ? '' : '\nHay turnos sin precio (Codex sin precios en valedores.toml).') + '\nClic para ver el desglose por fases.';
    btnUso.classList.toggle('vivo', hayTrabajo());
    const nv = vp.fases.filter(f => f.estado === 'validar');
    pillValidar.hidden = !nv.length;
    pillValidar.textContent = nv.length ? '⏳ Espera tu validación: ' + nv.map(f => f.nombre).join(', ') : '';
    chatNum.replaceChildren(hayTrabajo() ? spinner('peq') : '');
  }

  function abrirUso() {
    if (document.querySelector('.pop.uso-pop')) { document.querySelector('.pop.uso-pop').cerrar(); return; }
    const u = vp.uso, t = totalConVivo();
    const fila = (nombre, d, extra) => h('tr', { class: extra || '' }, h('td', {}, nombre),
      h('td', { class: 'n' }, fmtTok(d.entrada)), h('td', { class: 'n' }, fmtTok((d.cache_leida || 0) + (d.cache_escrita || 0))),
      h('td', { class: 'n' }, fmtTok(d.salida)), h('td', { class: 'n' }, extra === 'total' ? textoCoste(t) : d.coste ? fmtUsd(d.coste) : '—'));
    const filas = vp.fases.filter(f => u.por_fase[f.id]).map(f => fila(ICONO_FASE[f.id] + ' ' + f.nombre, u.por_fase[f.id]));
    if (u.por_fase.sin_fase) filas.push(fila('Otros', u.por_fase.sin_fase));
    popover(btnUso, [
        h('h3', {}, 'Consumo del proyecto'),
        filas.length ? h('table', { class: 'tabla-uso' },
          h('thead', {}, h('tr', {}, h('th', {}, 'Fase'), h('th', { class: 'n' }, 'Entrada'), h('th', { class: 'n' }, 'Caché'), h('th', { class: 'n' }, 'Salida'), h('th', { class: 'n' }, 'Precio'))),
          h('tbody', {}, filas),
          h('tfoot', {}, fila('Total', Object.assign({}, t, { coste: t.coste }), 'total')))
          : h('p', { class: 'suave' }, 'Todavía no hay consumo: aparecerá cuando el agente termine su primer turno.'),
        h('p', { class: 'suave pequeno' }, 'Entrada = tokens nuevos; caché = tokens reutilizados de turnos anteriores (se pagan mucho más baratos). ' +
          'Si un turno toca varias fases, su consumo se reparte según la actividad del agente en cada una. ' +
          (t.coste_completo ? '' : 'El precio solo lo informa Claude Code; para Codex defínelo en valedores.toml ([precios]). ') +
          (t.sin_desglose ? 'Hay ' + fmtTok(t.sin_desglose) + ' tokens de turnos antiguos sin desglose.' : '')),
    ], { clase: 'uso-pop' });
  }

  function abrirAjustes() {
    const p = vp.proyecto, ag = ESTADO.agentes[p.agente];
    const guardar = async (campo, valor) => { try { await api('/api/proyectos/' + slug, { metodo: 'PATCH', json: { [campo]: valor } }); pend(); } catch (e) { avisar(e.message); } };
    popover(btnAjustes, [
      h('h3', {}, 'Ajustes del proyecto'),
      h('label', {}, 'Agente'),
      selector(Object.keys(ESTADO.agentes).map(k => [k, ESTADO.agentes[k].nombre]), p.agente, async v => {
        const a = ESTADO.agentes[v];
        if (!a.disponible) { avisar('«' + a.nombre + '» no está instalado.'); refrescar(); return; }
        await api('/api/proyectos/' + slug, { metodo: 'PATCH', json: { agente: v, modelo: a.modelo_defecto, esfuerzo: a.esfuerzo_defecto } }); await refrescar();
        document.querySelector('.pop') && document.querySelector('.pop').cerrar(); abrirAjustes();
      }),
      h('label', {}, 'Modelo'), selector(ag.modelos.map(m => [m.id, m.nombre]), p.modelo, v => guardar('modelo', v)),
      h('label', {}, 'Esfuerzo'), selector(ag.esfuerzos.map(e => [e, e]), p.esfuerzo, v => guardar('esfuerzo', v)),
      h('label', {}, 'Ritmo'), selector(Object.entries(ESTADO.ritmos).map(([k, t]) => [k, t.split(':')[0]]), p.ritmo, v => guardar('ritmo', v)),
      h('label', {}, 'Permisos del agente'), selector(Object.entries(ESTADO.permisos).map(([k, t]) => [k, t.split(':')[0]]), p.permisos || 'normal', v => guardar('permisos', v)),
    ], { clase: 'ajustes-pop' });
  }

  // ================================================================ selección
  function seleccionar(tipo, id, manual) {
    st.sel = { tipo, id };
    if (manual !== false) st.auto = false;
    st.pestana = 'detalle';
    pintarMapa(); pintarPestanas(); pintarCuerpo();
  }

  // ================================================================ mapa
  function cambiosPendientes() { return vp.cambios.filter(c => c.estado === 'pendiente' || c.estado === 'en_curso'); }

  function tarjetaElemento(e, pendientes) {
    const hay = pendientes.some(c => c.objetivos.some(o => o.tipo === 'elemento' && o.id === e.id));
    const esSel = st.sel.tipo === 'elemento' && st.sel.id === e.id;
    return h('div', {
      class: 'el est-' + e.estado + (esSel ? ' sel' : ''), 'data-el': e.id, title: e.nombre + ' · ' + ESTADO_TXT[e.estado] + (e.nota ? '\n' + e.nota : ''),
      onclick: ev => { ev.stopPropagation(); seleccionar('elemento', e.id); },
    }, h('span', { class: 'el-ico' }, ICONO_TIPO[e.tipo] || '📦'), h('span', { class: 'el-nom' }, e.nombre),
    hay ? h('span', { class: 'tag cambio', title: 'Tiene un cambio pendiente' }, '✎') : null, iconoEstado(e.estado),
    e.estado === 'en_curso' ? barraTiempo(e, { fina: true, sinTexto: true }) : null);
  }

  function nodoFase(f, pendientes) {
    const els = vp.elementos.filter(e => e.fase === f.id);
    const uso = vp.uso.por_fase[f.id];
    const carril = vp.carriles.find(c => c.id === f.id);
    const nCambios = pendientes.filter(c => c.fases_marcadas.includes(f.id) || c.objetivos.some(o => o.tipo === 'fase' && o.id === f.id)).length;
    const esSel = st.sel.tipo === 'fase' && st.sel.id === f.id;
    return h('div', { class: 'nodo est-' + f.estado + (esSel ? ' sel' : ''), 'data-fase': f.id },
      h('div', { class: 'nodo-cab', onclick: () => seleccionar('fase', f.id) },
        iconoEstado(f.estado), h('span', { class: 'nodo-ico' }, ICONO_FASE[f.id]), h('b', {}, f.nombre),
        carril && carril.ocupado ? h('span', { class: 'tag par', title: 'Un agente aparte está trabajando en esta fase' }, '⇉ aparte') : null,
        nCambios ? h('span', { class: 'tag cambio', title: nCambios + ' cambio(s) pendiente(s)' }, '✎ ' + nCambios) : null),
      f.estado === 'en_curso' ? barraTiempo(f, { fina: true }) : h('div', { class: 'nodo-estado' }, ESTADO_TXT[f.estado]),
      els.length ? h('div', { class: 'elementos' + (els.length > 4 ? ' dos' : '') }, els.map(e => tarjetaElemento(e, pendientes))) : null,
      uso && (uso.entrada || uso.salida || uso.cache_leida) ? h('div', { class: 'nodo-pie', title: 'Consumo de esta fase' },
        '⬇ ' + fmtTok(entradaTotal(uso)) + '  ⬆ ' + fmtTok(uso.salida) + (uso.coste ? '  ·  ' + fmtUsd(uso.coste) : '')) : null);
  }

  function pintarMapa() {
    const pendientes = cambiosPendientes();
    const niv = nivelesDeFases();
    const columnas = [];
    vp.fases.forEach(f => { (columnas[niv[f.id]] = columnas[niv[f.id]] || []).push(f); });
    mapaInt.replaceChildren(cables, h('div', { class: 'capas' }, columnas.map(fs => h('div', { class: 'capa' }, fs.map(f => nodoFase(f, pendientes))))));
    requestAnimationFrame(pintarCables);
  }

  function pintarCables() {
    if (!mapaInt.isConnected) return;
    const r0 = mapaInt.getBoundingClientRect();
    cables.setAttribute('width', mapaInt.scrollWidth);
    cables.setAttribute('height', mapaInt.scrollHeight);
    const caminos = [];
    const sel = st.sel.tipo === 'fase' ? st.sel.id : (elemento(st.sel.id) || {}).fase;
    const unir = (a, b, clase) => {
      if (!a || !b) return;
      const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      const x1 = ra.right - r0.left, y1 = ra.top + ra.height / 2 - r0.top, x2 = rb.left - r0.left, y2 = rb.top + rb.height / 2 - r0.top;
      const dx = Math.max(24, (x2 - x1) / 2);
      const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      p.setAttribute('d', 'M' + x1 + ',' + y1 + ' C' + (x1 + dx) + ',' + y1 + ' ' + (x2 - dx) + ',' + y2 + ' ' + x2 + ',' + y2);
      p.setAttribute('class', clase);
      caminos.push(p);
    };
    for (const [f, deps] of Object.entries(ESTADO.dependencias)) {
      const destino = fase(f);
      for (const d of deps) {
        const origen = fase(d);
        let c = 'cable';
        if (origen.estado === 'aprobada' || origen.estado === 'omitida') c += ' hecho';
        if (destino.estado === 'en_curso') c += ' activo';
        if (sel && (f === sel || d === sel)) c += ' resalta';
        unir(mapaInt.querySelector('[data-fase="' + d + '"]'), mapaInt.querySelector('[data-fase="' + f + '"]'), c);
      }
    }
    for (const e of vp.elementos) {
      for (const d of e.depende || []) {
        const o = elemento(d);
        if (o && o.fase !== e.fase) unir(mapaInt.querySelector('[data-el="' + d + '"]'), mapaInt.querySelector('[data-el="' + e.id + '"]'),
          'cable fino' + (st.sel.tipo === 'elemento' && (st.sel.id === e.id || st.sel.id === d) ? ' resalta' : ''));
      }
    }
    cables.replaceChildren(...caminos);
  }
  new ResizeObserver(() => requestAnimationFrame(pintarCables)).observe(mapaEl);

  function pintarTareas() {
    tareasEl.replaceChildren(...vp.tareas.map(t => h('div', { class: 'tarea' }, spinner(), h('b', {}, t.etiqueta),
      h('span', { class: 'suave' }, t.fase ? ICONO_FASE[t.fase] + ' ' + (fase(t.fase) || {}).nombre : ''), barraTiempo(t))));
    tareasEl.hidden = !vp.tareas.length;
  }

  // ================================================================ pestañas
  function pintarPestanas() {
    const nc = cambiosPendientes().length;
    pestanasEl.replaceChildren(...[['detalle', 'Detalle'], ['cambios', 'Cambios' + (vp.cambios.length ? ' (' + vp.cambios.length + ')' : ''), nc], ['ficheros', 'Ficheros']]
      .map(([id, txt, n]) => h('button', { class: 'pestana' + (st.pestana === id ? ' on' : ''), role: 'tab', onclick: () => { st.pestana = id; pintarPestanas(); pintarCuerpo(); } },
        txt, n ? h('span', { class: 'ins alerta' }, n) : null)));
  }

  function pintarCuerpo() {
    const f = st.pestana === 'detalle' ? detalle() : st.pestana === 'cambios' ? listaCambios() : ficherosProyecto();
    cuerpoEl.replaceChildren(f);
  }

  // ---- visor de ficheros
  function bloqueArchivo(a) {
    const cab = h('div', { class: 'arch-cab' }, h('span', { class: 'arch-nom' }, a.nombre), h('a', { href: a.url, target: '_blank', class: 'suave' }, 'abrir ↗'));
    if (a.tipo === 'video') return h('div', { class: 'arch' }, cab, h('video', { src: a.url, controls: true, preload: 'metadata' }));
    if (a.tipo === 'audio') return h('div', { class: 'arch' }, cab, h('audio', { src: a.url, controls: true }));
    if (a.tipo === 'texto' || a.tipo === 'codigo') {
      const doc = h('div', { class: 'doc cerrado' }, 'Cargando…');
      const mas = h('button', { class: 'texto', onclick: () => { const c = doc.classList.toggle('cerrado'); mas.textContent = c ? 'Ver completo ▾' : 'Ver menos ▴'; } }, 'Ver completo ▾');
      fetch(a.url).then(r => r.text()).then(t => {
        t = t.slice(0, 80000);
        if (/\.md$/i.test(a.nombre)) { doc.className = 'doc md cerrado'; doc.replaceChildren(md(t)); }
        else { doc.className = 'doc cerrado'; doc.replaceChildren(h('pre', {}, t)); }
        requestAnimationFrame(() => { if (doc.scrollHeight <= doc.clientHeight + 4) mas.hidden = true; });
      }).catch(() => { doc.textContent = '(no se pudo leer)'; });
      return h('div', { class: 'arch' }, cab, doc, mas);
    }
    return h('div', { class: 'arch' }, cab);
  }

  function visor(arts) {
    if (!arts.length) return h('p', { class: 'suave' }, 'Todavía no hay nada que ver aquí.');
    const imgs = arts.filter(a => a.tipo === 'imagen');
    return h('div', { class: 'visor' },
      imgs.length ? h('div', { class: 'miniaturas' }, imgs.map(a => h('img', { src: a.url, loading: 'lazy', title: a.nombre, onclick: () => ampliar(a.url) }))) : null,
      arts.filter(a => a.tipo !== 'imagen').map(bloqueArchivo));
  }

  // ---- detalle de una fase o de un elemento
  function detalle() {
    return st.sel.tipo === 'elemento' && elemento(st.sel.id) ? detalleElemento(elemento(st.sel.id)) : detalleFase(fase(st.sel.tipo === 'fase' ? st.sel.id : vp.proyecto.fase_actual) || vp.fases[0]);
  }

  function cabDetalle(icono, nombre, estado, extra) {
    return h('div', { class: 'det-cab' }, h('span', { class: 'det-ico' }, icono), h('h3', {}, nombre),
      h('span', { class: 'chip-est est-' + estado }, iconoEstado(estado), ' ' + ESTADO_TXT[estado]), extra || null);
  }

  function detalleFase(f) {
    const par = vp.paralelo[f.id], carril = vp.carriles.find(c => c.id === f.id);
    const ritmo = vp.proyecto.ritmo;
    const acc = [];
    const fin = ritmo === 'paso_a_paso' ? ' y párate al terminarla para que la valide.' : '.';
    if (f.estado === 'validar') {
      acc.push(h('button', { class: 'ok', onclick: () => aprobar(f) }, '✓ Aprobar'),
        h('button', { onclick: () => dialogoCambio({ tipo: 'fase', id: f.id }) }, '✎ Pedir cambios'));
    } else if (f.estado === 'pendiente') {
      acc.push(h('button', { class: 'primario', disabled: !par.puede, title: par.puede ? '' : par.motivo, onclick: () => enviarPrincipal('Haz ahora la fase «' + f.nombre + '»' + fin) }, '▶ Hacer ahora'),
        h('button', { disabled: !par.puede || (carril && carril.ocupado), title: par.puede ? 'Un agente aparte la hace mientras sigues con lo demás' : par.motivo, onclick: () => iniciarParalelo(f.id) }, '⇉ En paralelo'));
    } else if (f.estado === 'cambios') {
      acc.push(h('button', { class: 'primario', onclick: () => enviarPrincipal('Rehaz la fase «' + f.nombre + '» con los cambios pendientes (mira su nota y la pestaña de cambios)' + fin) }, '▶ Rehacer ahora'),
        h('button', { onclick: () => iniciarParalelo(f.id) }, '⇉ En paralelo'));
    } else if (f.estado === 'aprobada' || f.estado === 'omitida') {
      acc.push(h('button', { onclick: () => dialogoCambio({ tipo: 'fase', id: f.id }) }, '✎ Pedir un cambio'),
        h('button', { class: 'texto', onclick: () => decidir(f, 'reabrir') }, 'Reabrir'));
    }
    if (f.estado !== 'omitida' && f.estado !== 'aprobada') acc.push(h('button', { class: 'texto', onclick: () => decidir(f, 'omitir') }, 'Omitir'));
    const hijos = vp.elementos.filter(e => e.fase === f.id);
    return h('div', { class: 'detalle' },
      cabDetalle(ICONO_FASE[f.id], f.nombre, f.estado, carril && carril.ocupado ? h('span', { class: 'tag par' }, '⇉ agente aparte') : null),
      h('p', { class: 'suave' }, f.resumen),
      f.estado === 'en_curso' ? h('div', { class: 'det-prog' }, barraTiempo(f)) : null,
      f.nota ? h('div', { class: 'nota' }, f.nota) : null,
      h('div', { class: 'acciones' }, acc),
      hijos.length ? h('div', { class: 'sub-els' }, hijos.map(e => h('button', { class: 'chip-el est-' + e.estado, onclick: () => seleccionar('elemento', e.id) },
        iconoEstado(e.estado), ' ' + (ICONO_TIPO[e.tipo] || '') + ' ' + e.nombre))) : null,
      visor(f.artefactos));
  }

  function detalleElemento(e) {
    const f = fase(e.fase);
    const deps = (e.depende || []).map(d => elemento(d)).filter(Boolean);
    const cambios = vp.cambios.filter(c => c.objetivos.some(o => o.tipo === 'elemento' && o.id === e.id));
    return h('div', { class: 'detalle' },
      cabDetalle(ICONO_TIPO[e.tipo] || '📦', e.nombre, e.estado),
      h('p', { class: 'suave' }, e.tipo + ' de la fase ', h('a', { href: 'javascript:void(0)', onclick: () => seleccionar('fase', e.fase) }, f.nombre),
        deps.length ? ' · depende de ' : '', ...deps.flatMap((d, i) => [i ? ', ' : '', h('a', { href: 'javascript:void(0)', onclick: () => seleccionar('elemento', d.id) }, d.nombre)])),
      e.estado === 'en_curso' ? h('div', { class: 'det-prog' }, barraTiempo(e)) : null,
      e.nota ? h('div', { class: 'nota' }, e.nota) : null,
      h('div', { class: 'acciones' }, h('button', { class: 'primario', onclick: () => dialogoCambio({ tipo: 'elemento', id: e.id }) }, '✎ Pedir un cambio a esto'),
        h('button', { class: 'texto', onclick: () => seleccionar('fase', e.fase) }, 'Ver la fase')),
      cambios.length ? h('p', { class: 'suave' }, 'Cambios pedidos sobre esto: ' + cambios.map(c => '#' + c.id + ' (' + c.estado + ')').join(', ')) : null,
      visor(e.artefactos));
  }

  // ---- cambios
  function nombreObjetivo(o) {
    if (o.tipo === 'fase') { const f = fase(o.id); return (ICONO_FASE[o.id] || '') + ' ' + (f ? f.nombre : o.id); }
    const e = elemento(o.id);
    return (e ? (ICONO_TIPO[e.tipo] || '') + ' ' + e.nombre : o.id);
  }

  function listaCambios() {
    const cs = [...vp.cambios].reverse();
    if (!cs.length) {
      return h('div', { class: 'vacio' }, h('p', {}, 'Aún no has pedido ningún cambio.'),
        h('p', { class: 'suave' }, 'Puedes pedir un cambio de cualquier parte del vídeo, en cualquier momento, aunque ya esté aprobada o sea de una fase anterior. ' +
          'El estudio marca lo que hay que rehacer y el agente decide el alcance real.'),
        h('button', { class: 'primario', onclick: () => dialogoCambio(st.sel) }, '✎ Pedir un cambio'));
    }
    const estado = { pendiente: 'Pendiente', en_curso: 'Rehaciendo…', hecho: 'Hecho', descartado: 'Descartado' };
    return h('div', { class: 'cambios' }, cs.map(c => h('div', { class: 'cambio-item est-c-' + c.estado },
      h('div', { class: 'cambio-cab' }, h('b', {}, '#' + c.id), c.estado === 'en_curso' ? spinner('peq') : null,
        h('span', { class: 'chip-est c-' + c.estado }, estado[c.estado] || c.estado), h('span', { class: 'suave' }, c.creado), h('span', { class: 'grow' }),
        c.estado === 'pendiente' || c.estado === 'en_curso' ? h('button', { class: 'texto', onclick: () => estadoCambio(c, 'hecho') }, 'Marcar hecho') : null,
        c.estado === 'pendiente' ? h('button', { class: 'texto', onclick: () => estadoCambio(c, 'descartado') }, 'Descartar') : null),
      h('p', { class: 'cambio-txt' }, c.texto),
      h('div', { class: 'cambio-obj' },
        c.objetivos.length ? c.objetivos.map(o => h('button', { class: 'chip-obj', onclick: () => seleccionar(o.tipo, o.id) }, nombreObjetivo(o)))
          : h('span', { class: 'suave' }, 'Todo el vídeo (lo decide el agente)'),
        c.afectadas.length ? h('span', { class: 'suave' }, ' · también: ' + c.afectadas.map(a => (fase(a) || {}).nombre).join(', ')) : null))));
  }

  async function estadoCambio(c, estado) {
    try { await api('/api/proyectos/' + slug + '/cambio/' + c.id, { metodo: 'PATCH', json: { estado } }); pend(); } catch (e) { avisar(e.message); }
  }

  // ---- ficheros
  function ficherosProyecto() {
    const salida = vp.videos;
    return h('div', { class: 'ficheros' },
      h('h3', {}, 'Tus ficheros de entrada'), h('p', { class: 'suave' }, 'Fotos, vídeos de referencia, audios o assets que el agente puede usar. También puedes soltarlos en el chat.'),
      vp.entradas.length ? h('div', { class: 'lista-arch' }, vp.entradas.map(e => h('div', {}, h('span', {}, { imagen: '🖼️', video: '🎬', audio: '🎵' }[e.tipo] || '📄'), ' ', h('a', { href: e.url, target: '_blank' }, e.nombre))))
        : h('p', { class: 'suave' }, 'Nada todavía.'),
      subidor(slug, pend),
      h('h3', {}, 'Vídeos de salida'),
      salida.length ? h('div', { class: 'cuadricula' }, salida.map(f => h('div', { class: 'c' },
        f.tipo === 'video' ? h('video', { src: f.url, controls: true, preload: 'metadata' }) : h('img', { src: f.url, loading: 'lazy', onclick: () => ampliar(f.url) }),
        h('div', { title: f.ruta }, h('a', { href: f.url, target: '_blank' }, f.nombre), ' · ' + tamano(f.tam))))) : h('p', { class: 'suave' }, 'Aún no hay vídeos.'),
      h('h3', {}, 'Archivos del proyecto'),
      h('div', { class: 'lista-arch' }, vp.archivos.map(a => h('div', {}, h('a', { href: a.url, target: '_blank' }, a.nombre), h('span', { class: 'suave' }, ' · ' + tamano(a.tam))))));
  }

  // ================================================================ acciones sobre fases
  async function decidir(f, accion) {
    try { await api('/api/proyectos/' + slug + '/fase', { metodo: 'POST', json: { fase: f.id, accion } }); pend(); } catch (e) { avisar(e.message); }
  }

  async function aprobar(f) {
    try { await api('/api/proyectos/' + slug + '/fase', { metodo: 'POST', json: { fase: f.id, accion: 'aprobar' } }); } catch (e) { avisar(e.message); return; }
    await refrescar();
    const listas = vp.fases.filter(x => x.estado === 'pendiente' && vp.paralelo[x.id].puede);
    const conCambios = vp.fases.some(x => x.estado === 'cambios');
    if (vp.proyecto.ritmo === 'de_una') { enviarPrincipal('✅ Fase «' + f.nombre + '» aprobada. Sigue.'); return; }
    if (listas.length >= 2) { dialogoSeguir(f, listas); return; }
    if (listas.length === 1 || conCambios) {
      enviarPrincipal('✅ Fase «' + f.nombre + '» aprobada. Sigue con lo siguiente (primero las fases con cambios por rehacer, luego las pendientes) y párate al terminar la siguiente fase.');
    } else avisar('Fase aprobada. No queda nada pendiente.');
  }

  function dialogoSeguir(f, listas) {
    const nombres = listas.map(x => x.nombre).join(' y ');
    dialogo('«' + f.nombre + '» aprobada · ¿cómo seguimos?', h('div', {},
      h('p', {}, nombres + ' no dependen una de otra: se pueden hacer a la vez con un agente para cada una. ' +
        'Es más rápido, pero gasta algo más (cada agente lee el proyecto por su cuenta) y tendrás que validar las dos.')),
    cerrar => [
      h('button', { onclick: cerrar }, 'Solo aprobar'),
      h('button', { onclick: () => { cerrar(); enviarPrincipal('✅ Fase «' + f.nombre + '» aprobada. Sigue con la siguiente y párate al terminarla.'); } }, 'Una tras otra'),
      h('button', { class: 'primario', onclick: async () => { cerrar(); for (const x of listas) await iniciarParalelo(x.id); } }, '⇉ A la vez (' + listas.length + ' agentes)'),
    ], 520);
  }

  // ================================================================ cambio: se puede pedir sobre cualquier cosa y en cualquier momento
  function dialogoCambio(pre) {
    const objetivos = new Map();
    if (pre && (pre.tipo === 'fase' ? fase(pre.id) : elemento(pre.id))) objetivos.set(pre.tipo + ':' + pre.id, { tipo: pre.tipo, id: pre.id });
    const excluidas = new Set();
    const area = h('textarea', { rows: 4, placeholder: 'Qué quieres que cambie. Vale «la música es muy lenta» o algo muy concreto.' });
    const zonaObj = h('div', { class: 'obj-zona' });
    const zonaAf = h('div', { class: 'afect' });
    const aviso = h('p', { class: 'suave pequeno' });

    const clave = (t, id) => t + ':' + id;
    function chip(texto, t, id, estado) {
      const on = objetivos.has(clave(t, id));
      return h('button', { class: 'chip-obj' + (on ? ' on' : ''), type: 'button', onclick: () => { if (on) objetivos.delete(clave(t, id)); else objetivos.set(clave(t, id), { tipo: t, id }); excluidas.clear(); repintar(); } },
        estado ? iconoEstado(estado) : null, ' ' + texto);
    }

    function afectadas() {
      const base = new Set();
      for (const o of objetivos.values()) base.add(o.tipo === 'fase' ? o.id : (elemento(o.id) || {}).fase);
      const post = new Set();
      base.forEach(f => posterioresDe(f).forEach(x => post.add(x)));
      base.forEach(f => post.delete(f));
      return vp.fases.filter(f => post.has(f.id) && f.estado !== 'pendiente');
    }

    function repintar() {
      zonaObj.replaceChildren(
        h('div', { class: 'obj-fila' }, h('span', { class: 'obj-et' }, 'Fases'), vp.fases.map(f => chip((ICONO_FASE[f.id] || '') + ' ' + f.nombre, 'fase', f.id, f.estado))),
        vp.elementos.length ? h('div', { class: 'obj-fila' }, h('span', { class: 'obj-et' }, 'Elementos'),
          vp.elementos.map(e => chip((ICONO_TIPO[e.tipo] || '') + ' ' + e.nombre, 'elemento', e.id, e.estado))) : null,
        objetivos.size ? null : h('p', { class: 'suave pequeno' }, 'Sin elegir nada: «todo el vídeo / no lo sé». El agente decide qué hay que tocar.'));
      const af = afectadas();
      zonaAf.replaceChildren(...(af.length ? [
        h('p', { class: 'obj-et' }, 'Lo que viene después y ya tiene trabajo hecho (se marcará para rehacer):'),
        ...af.map(f => h('label', { class: 'casilla' }, h('input', {
          type: 'checkbox', checked: !excluidas.has(f.id), onchange: ev => { if (ev.target.checked) excluidas.delete(f.id); else excluidas.add(f.id); },
        }), ' ' + (ICONO_FASE[f.id] || '') + ' ' + f.nombre, h('span', { class: 'suave' }, ' · ' + ESTADO_CORTO[f.estado]))),
        h('p', { class: 'suave pequeno' }, 'El agente comprobará el alcance real y te avisará si el cambio toca algo más.'),
      ] : []));
      aviso.textContent = hayTrabajo() ? 'El agente está trabajando: el cambio quedará en cola y lo atenderá al terminar su turno actual.' : '';
    }
    repintar();

    const d = dialogo('✎ Pedir un cambio', h('div', {}, h('label', {}, '¿Qué quieres cambiar?'), area, h('label', {}, '¿En qué parte?'), zonaObj, zonaAf, aviso),
      cerrar => [
        h('button', { onclick: cerrar }, 'Cancelar'),
        h('button', { class: 'primario', onclick: async ev => {
          if (!area.value.trim()) { area.focus(); return; }
          ev.target.disabled = true;
          try {
            const c = await api('/api/proyectos/' + slug + '/cambio', { metodo: 'POST', json: {
              texto: area.value, objetivos: [...objetivos.values()], afectadas: afectadas().filter(f => !excluidas.has(f.id)).map(f => f.id) } });
            cerrar();
            avisar('Cambio #' + c.id + (c.en_cola ? ' en cola' : ' enviado al agente'));
            st.pestana = 'cambios'; st.auto = false;
            abrirChat(true); await refrescar();
          } catch (e) { avisar(e.message, 4500); ev.target.disabled = false; }
        } }, 'Enviar cambio'),
      ], 640);
    area.focus();
    return d;
  }

  // ================================================================ chat
  const cbHilo = {
    estado: (carril, ocupado) => { pintarTabsChat(); pintarCab(); actualizarEnviar(); },
    proyecto: () => pend(),
    uso: (carril, ev) => { if (ev) usoVivo[carril] = ev; else delete usoVivo[carril]; pintarCab(); },
    fin: (carril) => { delete usoVivo[carril]; pend(); },
  };

  function sincronizarHilos() {
    for (const c of vp.carriles) if (!hilos[c.id]) {
      hilos[c.id] = crearHilo(slug, c.id, cbHilo);
      limpiar.push(() => hilos[c.id].cerrar());
    }
  }

  function pintarTabsChat() {
    tabsChat.replaceChildren(...vp.carriles.map(c => {
      const hilo = hilos[c.id];
      const ocupado = hilo ? hilo.ocupado : c.ocupado;
      const f = c.id === 'principal' ? null : fase(c.id);
      return h('button', { class: 'tab-chat' + (st.carril === c.id ? ' on' : ''), onclick: () => cambiarCarril(c.id), title: f ? 'Agente que trabaja en paralelo en «' + f.nombre + '»' : 'Agente principal' },
        ocupado ? spinner('peq') : null, f ? (ICONO_FASE[f.id] + ' ' + f.nombre) : 'Principal');
    }), h('span', { class: 'grow' }), h('button', { class: 'icono', title: 'Ocultar el chat', onclick: () => alternarChat() }, '⟩'));
  }

  function cambiarCarril(id) {
    st.carril = id;
    sincronizarHilos();
    hilosEl.replaceChildren(hilos[id].el);
    hilos[id].alMostrar();
    pintarTabsChat(); actualizarEnviar();
  }

  function actualizarEnviar() {
    const hilo = hilos[st.carril];
    const o = hilo && hilo.ocupado;
    btnParar.hidden = !o;
    btnEnviar.textContent = o ? 'Encolar' : 'Enviar';
    texto.placeholder = o ? 'El agente está trabajando… lo que escribas se enviará al terminar su turno' : 'Escribe al agente… (Enter envía · Mayús+Enter salto de línea)';
  }

  function aplicarChat() {
    cuerpo.classList.toggle('sin-chat', !st.chatAbierto);
    panelChat.hidden = !st.chatAbierto;
    sep.hidden = !st.chatAbierto;
    btnChat.classList.toggle('on', st.chatAbierto);
    requestAnimationFrame(pintarCables);
  }
  function abrirChat(si) { st.chatAbierto = si; pref('chatAbierto', si); aplicarChat(); if (si) hilos[st.carril].alMostrar(); }
  function alternarChat() { abrirChat(!st.chatAbierto); }

  const anchoGuardado = pref('chatAncho');
  if (anchoGuardado) cuerpo.style.setProperty('--chat-w', anchoGuardado + 'px');
  sep.addEventListener('pointerdown', ev => {
    ev.preventDefault();
    sep.setPointerCapture(ev.pointerId);
    const mover = e => {
      const r = cuerpo.getBoundingClientRect();
      const w = Math.max(320, Math.min(r.width * 0.7, r.right - e.clientX));
      cuerpo.style.setProperty('--chat-w', Math.round(w) + 'px');
      pref('chatAncho', Math.round(w));
    };
    const soltar = () => { sep.removeEventListener('pointermove', mover); sep.removeEventListener('pointerup', soltar); requestAnimationFrame(pintarCables); };
    sep.addEventListener('pointermove', mover);
    sep.addEventListener('pointerup', soltar);
  });

  // ---- enviar
  async function postChat(cuerpoJson) {
    return api('/api/proyectos/' + slug + '/chat', { metodo: 'POST', json: cuerpoJson });
  }

  async function enviarPrincipal(t) {
    try { await postChat({ texto: t, carril: 'principal' }); abrirChat(true); cambiarCarril('principal'); } catch (e) { avisar(e.message, 4500); }
  }

  async function iniciarParalelo(id) {
    try { await postChat({ carril: id }); abrirChat(true); await refrescar(); cambiarCarril(id); } catch (e) { avisar(e.message, 4500); }
  }

  // adjuntos: se suben a entrada/<slug>/ nada más elegirlos y viajan con el siguiente mensaje
  const adjuntos = [];
  function pintarChips() {
    chips.replaceChildren(...adjuntos.map(a => h('div', { class: 'chip' + (a.error ? ' error' : '') },
      a.tipo === 'imagen' && a.url ? h('img', { src: a.url }) : h('span', { class: 'ico' }, { video: '🎬', audio: '🎵' }[a.tipo] || '📄'),
      h('span', { class: 'nom', title: a.error || a.nombre }, a.error ? a.error : a.nombre),
      a.url || a.error ? null : h('span', { class: 'prog' }, Math.round((a.progreso || 0) * 100) + '%'),
      h('button', { class: 'x', title: 'Quitar', onclick: () => { adjuntos.splice(adjuntos.indexOf(a), 1); pintarChips(); } }, '×'))));
  }
  function adjuntar(files) {
    for (const f of files) {
      if (!f.name) continue;
      const a = { nombre: f.name, tipo: 'otro', progreso: 0 };
      adjuntos.push(a); pintarChips();
      subirFichero(f, slug, p => { a.progreso = p; pintarChips(); })
        .then(d => { Object.assign(a, d); pintarChips(); pend(); })
        .catch(e => {
          a.error = e.message; pintarChips();
          setTimeout(() => { const i = adjuntos.indexOf(a); if (i >= 0) { adjuntos.splice(i, 1); pintarChips(); } }, 4000);
        });
    }
  }
  selectorFicheros.addEventListener('change', () => { adjuntar([...selectorFicheros.files]); selectorFicheros.value = ''; });
  let arrastres = 0;
  panelChat.addEventListener('dragenter', e => { if (e.dataTransfer.types.includes('Files')) { e.preventDefault(); arrastres++; velo.hidden = false; } });
  panelChat.addEventListener('dragover', e => { if (e.dataTransfer.types.includes('Files')) e.preventDefault(); });
  panelChat.addEventListener('dragleave', () => { if (--arrastres <= 0) { arrastres = 0; velo.hidden = true; } });
  panelChat.addEventListener('drop', e => { e.preventDefault(); arrastres = 0; velo.hidden = true; adjuntar([...e.dataTransfer.files]); });
  texto.addEventListener('paste', e => {
    const fs = [...(e.clipboardData ? e.clipboardData.files : [])];
    if (!fs.length) return;
    e.preventDefault();
    adjuntar(fs.map(f => (f.name && f.name !== 'image.png') ? f : new File([f], 'captura_' + Date.now() + '.png', { type: f.type })));
  });

  async function enviar(msg, rutas) {
    const t = (msg || texto.value).trim();
    const listos = msg ? (rutas || []).map(r => ({ ruta: r, url: true })) : adjuntos.filter(a => a.url);
    if (!t && !listos.length) return;
    if (!msg && adjuntos.some(a => !a.url && !a.error)) { avisar('Espera a que terminen de subirse los adjuntos.'); return; }
    try {
      await postChat({ texto: t, adjuntos: listos.map(a => a.ruta), carril: st.carril });
      if (!msg) { texto.value = ''; texto.style.height = ''; adjuntos.length = 0; pintarChips(); }
    } catch (e) { avisar(e.message, 4500); }
  }
  texto.addEventListener('keydown', ev => { if (ev.key === 'Enter' && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); enviar(); } });
  texto.addEventListener('input', () => { texto.style.height = 'auto'; texto.style.height = Math.min(texto.scrollHeight, 180) + 'px'; });

  // ================================================================ refresco
  function huella(...v) { return JSON.stringify(v, (k, x) => (k === 'artefactos' || k === 'ahora' ? undefined : x)); }

  function pintar() {
    pintarCab();
    const hm = huella(vp.fases, vp.elementos, vp.cambios, vp.uso.por_fase, vp.carriles, vp.paralelo, st.sel);
    if (huellas.mapa !== hm) { huellas.mapa = hm; pintarMapa(); }
    const ht = huella(vp.tareas);
    if (huellas.tareas !== ht) { huellas.tareas = ht; pintarTareas(); }
    const hp = huella(vp.cambios.length, cambiosPendientes().length, st.pestana);
    if (huellas.pest !== hp) { huellas.pest = hp; pintarPestanas(); }
    const hc = huella(st.pestana, st.sel, st.pestana === 'detalle' ? [fase(st.sel.id), elemento(st.sel.id), vp.paralelo, vp.carriles, vp.proyecto.ritmo, (vp.fases.find(f => f.id === st.sel.id) || {}).artefactos, (elemento(st.sel.id) || {}).artefactos] : st.pestana === 'cambios' ? [vp.cambios, vp.fases, vp.elementos] : [vp.entradas, vp.videos, vp.archivos.length]);
    if (huellas.cuerpo !== hc) { huellas.cuerpo = hc; pintarCuerpo(); }
    sincronizarHilos();
    pintarTabsChat();
    actualizarEnviar();
  }

  let enCurso = false, repetir = false;
  async function refrescar() {
    if (enCurso) { repetir = true; return; }
    enCurso = true;
    try {
      const nuevo = await api('/api/proyectos/' + slug);
      sincronizarReloj(nuevo.ahora);
      const anterior = vp.proyecto.fase_actual;
      vp = nuevo;
      if (st.auto && vp.proyecto.fase_actual !== anterior) st.sel = { tipo: 'fase', id: vp.proyecto.fase_actual };
      pintar();
    } catch (e) { /* el servidor puede estar reiniciándose */ }
    enCurso = false;
    if (repetir) { repetir = false; refrescar(); }
  }
  let tmr = null;
  function pend() { clearTimeout(tmr); tmr = setTimeout(refrescar, 350); }
  limpiar.push(() => clearTimeout(tmr));
  const reloj = setInterval(() => { tickBarras(); Object.values(hilos).forEach(x => x.tick()); }, 1000);
  limpiar.push(() => clearInterval(reloj));
  limpiar.push(() => document.querySelectorAll('.pop').forEach(p => p.remove()));

  // ================================================================ arranque
  aplicarChat();
  pintar();
  cambiarCarril('principal');
  const primero = sessionStorage.getItem('primer-' + slug);
  if (primero) {
    sessionStorage.removeItem('primer-' + slug);
    let m = { texto: primero, adjuntos: [] };
    try { m = JSON.parse(primero); } catch (e) { /* texto simple */ }
    setTimeout(() => enviar(m.texto, m.adjuntos), 300);
  }
}
