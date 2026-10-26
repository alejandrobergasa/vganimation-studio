'use strict';
// Un hilo de conversación con un agente (el principal o el de una fase en paralelo): recibe los eventos del servidor (SSE) y los pinta.
// Las llamadas a herramientas seguidas se agrupan en un solo bloque plegable; el texto del agente se pinta como Markdown.

function tsAHora(ts) {
  const m = /^(\d+):(\d+):(\d+)$/.exec(ts || '');
  if (!m) return null;
  const d = new Date();
  d.setHours(+m[1], +m[2], +m[3], 0);
  if (d.getTime() > Date.now() + 1000) d.setDate(d.getDate() - 1);
  return d.getTime();
}

// cb: { estado(carril, ocupado), proyecto(), uso(carril, ev|null), fin(carril, ev) }
function crearHilo(slug, carril, cb) {
  const el = h('div', { class: 'mensajes', 'data-carril': carril });
  const trabajando = h('div', { class: 'trabajando', hidden: true }, spinner(), h('span', {}, 'Trabajando…'), h('span', { class: 't-seg' }));
  const colaEl = h('div', { class: 'cola' });
  el.append(trabajando, colaEl);

  let ocupado = false, t0 = null, ultimoUsuario = null, proximo = 0, cerrado = false, es = null, temporizador = null;
  let vivo = null, grupo = null, pintandoVivo = false;
  const filas = {};

  const ins = n => el.insertBefore(n, trabajando);
  const cerca = () => el.scrollHeight - el.scrollTop - el.clientHeight < 100;
  const abajo = () => requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });

  function burbujaUsuario(ev) {
    const cambio = /^✎ Cambio #/.test(ev.texto);
    return h('div', { class: 'msg usuario' + (cambio ? ' cambio' : '') }, ev.texto,
      ev.adjuntos && ev.adjuntos.length ? h('div', { class: 'adjs' }, ev.adjuntos.map(a =>
        a.tipo === 'imagen' ? h('img', { src: a.url, title: a.nombre, onclick: () => ampliar(a.url) })
          : a.tipo === 'video' ? h('video', { src: a.url, controls: true, preload: 'metadata' })
            : h('a', { href: a.url, target: '_blank', class: 'adj' }, (a.tipo === 'audio' ? '🎵 ' : '📄 ') + a.nombre))) : null);
  }

  const mensajeAgente = texto => { const d = h('div', { class: 'msg agente md' }); d.append(md(texto)); return d; };

  // ---- bloque de acciones
  function iconoGrupo(g) {
    const nuevo = g.pend > 0 ? spinner() : h('span', { class: 'ei ' + (g.fallos ? 'cambios' : 'aprobada') }, g.fallos ? '!' : '✓');
    g.icono.replaceWith(nuevo);
    g.icono = nuevo;
  }

  function textoGrupo(g, ultima) {
    g.nEl.textContent = g.n + (g.n === 1 ? ' acción' : ' acciones') + (g.fallos ? ' · ' + g.fallos + ' con error' : '');
    if (ultima) g.ultEl.textContent = ' · ' + ultima;
  }

  function nuevoGrupo() {
    const icono = spinner();
    const nEl = h('span', { class: 'ac-n' }), ultEl = h('span', { class: 'ac-ult' });
    const lista = h('div', { class: 'ac-lista' });
    const det = h('details', { class: 'grupo-acc' }, h('summary', {}, icono, nEl, ultEl), lista);
    grupo = { det, lista, icono, nEl, ultEl, n: 0, pend: 0, fallos: 0 };
    ins(det);
  }

  function marcarFila(f, ok, texto) {
    const nuevo = ok === null ? h('span', { class: 'ei pendiente' }, '·') : h('span', { class: 'ei ' + (ok ? 'aprobada' : 'cambios') }, ok ? '✓' : '✗');
    f.est.replaceWith(nuevo);
    f.est = nuevo;
    f.hecho = true;
    f.grupo.pend = Math.max(0, f.grupo.pend - 1);
    if (ok === false) {
      f.grupo.fallos++;
      f.fila.classList.add('error');
      if (texto) f.fila.append(h('div', { class: 'ac-err' }, texto));
    }
    textoGrupo(f.grupo);
    iconoGrupo(f.grupo);
  }

  function cerrarPendientes() {
    for (const f of Object.values(filas)) if (!f.hecho) marcarFila(f, null);
  }

  // ---- texto en escritura: se vuelve a pintar el Markdown con cada trozo, como mucho una vez por fotograma
  function pintarVivo() {
    if (!vivo || pintandoVivo) return;
    pintandoVivo = true;
    requestAnimationFrame(() => {
      pintandoVivo = false;
      if (!vivo) return;
      const pegado = cerca();
      vivo.el.replaceChildren(md(vivo.raw));
      if (pegado) el.scrollTop = el.scrollHeight;
    });
  }

  function pintarCola(textos) {
    colaEl.replaceChildren(...textos.map(t => h('div', { class: 'msg usuario encola' }, t, h('span', { class: 'etq' }, 'en cola'))));
    abajo();
  }

  function fijarOcupado(o, ts) {
    if (o === ocupado) return;
    ocupado = o;
    trabajando.hidden = !o;
    t0 = o ? (tsAHora(ts || ultimoUsuario) || Date.now()) : null;
    if (!o) { cerrarPendientes(); vivo = null; grupo = null; cb.uso(carril, null); }
    cb.estado(carril, o);
  }

  function pintar(ev) {
    if (ev.n != null) proximo = ev.n + 1;
    const pegado = cerca();
    switch (ev.t) {
      case 'usuario': grupo = null; vivo = null; ultimoUsuario = ev.ts; ins(burbujaUsuario(ev)); break;
      case 'delta':
        grupo = null;
        if (!vivo) { vivo = { el: h('div', { class: 'msg agente md' }), raw: '' }; ins(vivo.el); }
        vivo.raw += ev.texto; pintarVivo(); return;
      case 'asistente':
        if (vivo) { vivo.el.remove(); vivo = null; }
        grupo = null;
        if (ev.texto && ev.texto.trim()) ins(mensajeAgente(ev.texto));
        break;
      case 'herramienta': {
        vivo = null;
        if (!grupo) nuevoGrupo();
        const est = spinner('peq');
        const fila = h('div', { class: 'ac-fila' }, est, h('b', {}, ev.nombre), ev.resumen ? h('span', { class: 'ac-txt' }, ev.resumen) : null);
        grupo.lista.append(fila);
        grupo.n++; grupo.pend++;
        filas[ev.id] = { fila, est, grupo, hecho: false };
        textoGrupo(grupo, ev.nombre + (ev.resumen ? ': ' + ev.resumen : ''));
        iconoGrupo(grupo);
        break; }
      case 'resultado': {
        const f = filas[ev.id];
        if (f && !f.hecho) marcarFila(f, !!ev.ok, ev.ok ? null : (ev.resumen || 'falló'));
        return; }
      case 'fin': {
        vivo = null; grupo = null;
        const u = ev.uso;
        const partes = [];
        if (ev.duracion) partes.push(Math.round(ev.duracion) + ' s');
        if (u) partes.push('⬇ ' + fmtTok(entradaTotal(u)) + ' · ⬆ ' + fmtTok(u.salida));
        if (ev.coste != null) partes.push((ev.coste_estimado ? '≈ ' : '') + fmtUsd(ev.coste));
        if (partes.length) ins(h('div', { class: 'msg sistema' }, partes.join('  ·  ')));
        cb.fin(carril, ev);
        break; }
      case 'uso_vivo': cb.uso(carril, ev); return;
      case 'error': vivo = null; grupo = null; ins(h('div', { class: 'msg error' }, '✗ ' + ev.texto)); break;
      case 'sistema': ins(h('div', { class: 'msg sistema' }, ev.texto)); break;
      case 'estado': fijarOcupado(ev.estado === 'trabajando', ev.ts); return;
      case 'cola': pintarCola(ev.textos || []); return;
      case 'proyecto': cb.proyecto(); return;
      default: return;
    }
    if (pegado) abajo();
  }

  const url = () => '/api/proyectos/' + slug + '/eventos?desde=' + proximo + (carril !== 'principal' ? '&carril=' + carril : '');
  function conectar() {
    if (cerrado || /[?&]nosse/.test(location.search)) return;
    es = new EventSource(url());
    es.onmessage = m => { try { pintar(JSON.parse(m.data)); } catch (e) { console.error(e); } };
    es.onerror = () => { es.close(); es = null; if (!cerrado) setTimeout(conectar, 1500); };
  }

  function tick() {
    if (!ocupado || !t0) return;
    const s = Math.round((Date.now() - t0) / 1000);
    trabajando.querySelector('.t-seg').textContent = '· ' + fmtTiempo(s);
  }

  conectar();
  return {
    carril, el,
    get ocupado() { return ocupado; },
    tick,
    cerrar() { cerrado = true; if (es) es.close(); clearTimeout(temporizador); },
    alMostrar() { requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; }); },
  };
}
