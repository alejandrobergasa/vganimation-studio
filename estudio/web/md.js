'use strict';
// Markdown a nodos DOM. Nunca usa innerHTML: todo el texto entra por createTextNode, así que el contenido del agente no puede inyectar HTML.
// Admite: títulos, párrafos, listas (anidadas, numeradas y de tareas), citas, bloques de código, tablas, reglas, **negrita**, *cursiva*,
// ~~tachado~~, `código`, enlaces e imágenes. Los enlaces solo pueden ser http(s), mailto, anclas o ficheros del repo (proyectos/, salida/, entrada/…).

const MD_RUTA_REPO = /^(?:\.\/)?((?:proyectos|salida|entrada|biblioteca)\/[^\s`'"<>]+?\.[A-Za-z0-9]{1,5})(?::\d+)?$/;

// Ruta del repo -> URL para verla en el navegador (o null si no es una ruta que el estudio sirva).
function urlRepo(ruta) {
  const m = MD_RUTA_REPO.exec((ruta || '').trim());
  return m ? '/api/archivo?ruta=' + encodeURIComponent(m[1]) : null;
}

function mdUrlSegura(u) {
  u = (u || '').trim();
  if (/^https?:\/\//i.test(u) || /^mailto:/i.test(u) || u.startsWith('#')) return u;
  if (u.startsWith('/api/archivo?')) return u;
  return urlRepo(u);
}

function mdEnlace(href, hijos) {
  const a = document.createElement('a');
  a.href = href;
  if (/^https?:/i.test(href) || href.startsWith('/api/')) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
  a.append(...hijos);
  return a;
}

function mdInline(texto, padre) {
  let i = 0, buf = '';
  const vaciar = () => { if (buf) { padre.append(document.createTextNode(buf)); buf = ''; } };
  const hijos = t => { const f = document.createDocumentFragment(); mdInline(t, f); return [...f.childNodes]; };
  while (i < texto.length) {
    const r = texto.slice(i);
    const c = texto[i];
    let m;
    if (c === '\\' && i + 1 < texto.length && /[\\`*_{}\[\]()#+\-.!|~>]/.test(texto[i + 1])) { buf += texto[i + 1]; i += 2; continue; }
    if (c === '`' && (m = /^(`+)([\s\S]*?[^`])\1(?!`)/.exec(r))) {
      vaciar();
      const cod = document.createElement('code');
      const t = m[2].replace(/^ (.*) $/, '$1');
      cod.textContent = t;
      const u = urlRepo(t);
      if (u) padre.append(mdEnlace(u, [cod])); else padre.append(cod);
      i += m[0].length; continue;
    }
    if (c === '!' && (m = /^!\[([^\]]*)\]\(((?:[^()\s]|\([^()\s]*\))+)(?:\s+"[^"]*")?\)/.exec(r))) {
      const u = mdUrlSegura(m[2]);
      vaciar();
      if (u && u.startsWith('/api/archivo?')) {
        const img = document.createElement('img');
        img.src = u; img.alt = m[1]; img.setAttribute('loading', 'lazy'); img.className = 'md-img';
        padre.append(img);
      } else padre.append(document.createTextNode(m[1] || m[2]));
      i += m[0].length; continue;
    }
    if (c === '[' && (m = /^\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)(?:\s+"[^"]*")?\)/.exec(r))) {
      const u = mdUrlSegura(m[2]);
      vaciar();
      if (u) padre.append(mdEnlace(u, hijos(m[1]))); else padre.append(...hijos(m[1]));
      i += m[0].length; continue;
    }
    if ((c === '*' || c === '_') && (m = /^(\*\*|__)(?=\S)([\s\S]*?\S)\1/.exec(r)) && (c === '*' || !/\w/.test(texto[i - 1] || ''))) {
      vaciar();
      const e = document.createElement('strong'); e.append(...hijos(m[2])); padre.append(e);
      i += m[0].length; continue;
    }
    if (c === '~' && (m = /^~~(?=\S)([\s\S]*?\S)~~/.exec(r))) {
      vaciar();
      const e = document.createElement('del'); e.append(...hijos(m[1])); padre.append(e);
      i += m[0].length; continue;
    }
    if ((c === '*' || c === '_') && (m = /^([*_])(?=[^\s*_])([\s\S]*?[^\s*_])\1/.exec(r))) {
      const antes = texto[i - 1] || '', despues = texto[i + m[0].length] || '';
      if (c === '*' || (!/\w/.test(antes) && !/\w/.test(despues))) {
        vaciar();
        const e = document.createElement('em'); e.append(...hijos(m[2])); padre.append(e);
        i += m[0].length; continue;
      }
    }
    if (c === 'h' && (m = /^https?:\/\/[^\s<>]+/.exec(r))) {
      const url = m[0].replace(/[.,;:!?)\]'"]+$/, '');
      vaciar();
      padre.append(mdEnlace(url, [document.createTextNode(url)]));
      i += url.length; continue;
    }
    buf += c; i++;
  }
  vaciar();
}

const MD_ITEM = /^(\s*)([-*+]|\d{1,3}[.)])\s+(.*)$/;
const MD_FILA_TABLA = /^\s*\|?.*\|.*$/;
const MD_SEP_TABLA = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/;

function mdCeldas(linea) {
  let t = linea.trim();
  if (t.startsWith('|')) t = t.slice(1);
  if (t.endsWith('|') && !t.endsWith('\\|')) t = t.slice(0, -1);
  return t.split(/(?<!\\)\|/).map(c => c.trim().replace(/\\\|/g, '|'));
}

function mdEsInicioBloque(l, siguiente) {
  return /^\s*```/.test(l) || /^#{1,6}\s/.test(l) || /^\s*>/.test(l) || MD_ITEM.test(l) || /^\s*([-*_])(\s*\1){2,}\s*$/.test(l) ||
    (MD_FILA_TABLA.test(l) && l.includes('|') && siguiente != null && MD_SEP_TABLA.test(siguiente) && siguiente.includes('-'));
}

function mdLista(lineas, i, sangria) {
  // Una lista con sus sublistas; devuelve [elemento, siguiente índice].
  const m0 = MD_ITEM.exec(lineas[i]);
  const ordenada = /\d/.test(m0[2]);
  const lista = document.createElement(ordenada ? 'ol' : 'ul');
  if (ordenada && parseInt(m0[2], 10) !== 1) lista.start = parseInt(m0[2], 10);
  while (i < lineas.length) {
    const m = MD_ITEM.exec(lineas[i]);
    if (!m || m[1].length !== sangria) break;
    if (/\d/.test(m[2]) !== ordenada) break;
    const li = document.createElement('li');
    let texto = m[3];
    const tarea = /^\[( |x|X)\]\s+(.*)$/.exec(texto);
    if (tarea) {
      const cb = document.createElement('input');
      cb.type = 'checkbox'; cb.disabled = true;
      if (tarea[1] !== ' ') cb.setAttribute('checked', '');
      li.append(cb, document.createTextNode(' '));
      texto = tarea[2];
    }
    mdInline(texto, li);
    i++;
    // continuación del elemento: líneas más sangradas (sublistas o texto)
    while (i < lineas.length) {
      const l = lineas[i];
      if (!l.trim()) {
        const sig = MD_ITEM.exec(lineas[i + 1] || '');
        if (sig && sig[1].length > sangria) { i++; continue; }
        break;
      }
      const mi = MD_ITEM.exec(l);
      if (mi && mi[1].length > sangria) {
        const [sub, j] = mdLista(lineas, i, mi[1].length);
        li.append(sub); i = j;
      } else if (!mi && /^\s+\S/.test(l) && l.search(/\S/) > sangria) {
        li.append(document.createElement('br'));
        mdInline(l.trim(), li); i++;
      } else break;
    }
    lista.append(li);
    if (i < lineas.length && !lineas[i].trim()) {            // línea en blanco entre elementos del mismo nivel
      const sig = MD_ITEM.exec(lineas[i + 1] || '');
      if (sig && sig[1].length === sangria) i++;
    }
  }
  return [lista, i];
}

function mdBloques(texto, padre) {
  const lineas = texto.replace(/\r\n?/g, '\n').split('\n');
  let i = 0;
  while (i < lineas.length) {
    const l = lineas[i];
    let m;
    if (!l.trim()) { i++; continue; }
    if ((m = /^\s*```\s*([\w+-]*)\s*$/.exec(l))) {
      const cuerpo = [];
      i++;
      while (i < lineas.length && !/^\s*```\s*$/.test(lineas[i])) cuerpo.push(lineas[i++]);
      i++;                                                  // cierre (si no lo hay, es un bloque aún en escritura)
      const pre = document.createElement('pre');
      const cod = document.createElement('code');
      if (m[1]) pre.dataset.lang = m[1];
      cod.textContent = cuerpo.join('\n');
      pre.append(cod); padre.append(pre);
      continue;
    }
    if ((m = /^(#{1,6})\s+(.*?)\s*#*\s*$/.exec(l))) {
      const h = document.createElement('h' + Math.min(6, m[1].length + 1));       // # -> h2: el título de la página ya es un h1
      mdInline(m[2], h); padre.append(h); i++; continue;
    }
    if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(l)) { padre.append(document.createElement('hr')); i++; continue; }
    if (/^\s*>/.test(l)) {
      const cita = [];
      while (i < lineas.length && /^\s*>/.test(lineas[i])) cita.push(lineas[i++].replace(/^\s*>\s?/, ''));
      const bq = document.createElement('blockquote');
      mdBloques(cita.join('\n'), bq); padre.append(bq); continue;
    }
    if (l.includes('|') && i + 1 < lineas.length && MD_SEP_TABLA.test(lineas[i + 1]) && lineas[i + 1].includes('-')) {
      const cab = mdCeldas(l);
      const alin = mdCeldas(lineas[i + 1]).map(c => (c.startsWith(':') && c.endsWith(':') ? 'center' : c.endsWith(':') ? 'right' : ''));
      i += 2;
      const tabla = document.createElement('table');
      const th = document.createElement('thead'), trh = document.createElement('tr');
      cab.forEach((c, k) => { const e = document.createElement('th'); mdInline(c, e); if (alin[k]) e.style.textAlign = alin[k]; trh.append(e); });
      th.append(trh); tabla.append(th);
      const tb = document.createElement('tbody');
      while (i < lineas.length && lineas[i].trim() && lineas[i].includes('|')) {
        const tr = document.createElement('tr');
        const cs = mdCeldas(lineas[i++]);
        cab.forEach((_, k) => { const e = document.createElement('td'); mdInline(cs[k] || '', e); if (alin[k]) e.style.textAlign = alin[k]; tr.append(e); });
        tb.append(tr);
      }
      tabla.append(tb);
      const caja = document.createElement('div'); caja.className = 'md-tabla'; caja.append(tabla); padre.append(caja);
      continue;
    }
    if ((m = MD_ITEM.exec(l))) {
      const [lista, j] = mdLista(lineas, i, m[1].length);
      padre.append(lista); i = j; continue;
    }
    // párrafo: hasta una línea en blanco o el inicio de otro bloque; los saltos de línea simples se respetan
    const p = document.createElement('p');
    let primera = true;
    while (i < lineas.length && lineas[i].trim() && (primera || !mdEsInicioBloque(lineas[i], lineas[i + 1]))) {
      if (!primera) p.append(document.createElement('br'));
      mdInline(lineas[i].replace(/\s+$/, ''), p);
      primera = false; i++;
    }
    padre.append(p);
  }
}

function md(texto) {
  const f = document.createDocumentFragment();
  mdBloques(String(texto || ''), f);
  return f;
}
