/* Layout canvas (production). Vanilla JS, no libraries.
 *
 * Python renders the diagram (render_for_editor) and pushes the SVG plus a state
 * payload through the QWebChannel bridge (documentChanged). This page:
 *   fetch → DOMParser('image/svg+xml') → import the root into #canvas,
 *   find each slot's rendered elements by the data-jd-slot annotation Python
 *   added (token scan only as a fallback for unannotated SVGs),
 *   draw an overlay <svg> sharing the template viewBox with hit rects, corner
 *   grips, hidden/added/profile-only outlines and "+N" overflow badges.
 * Pointer events land on the overlay only (draw.io foreignObjects hit-test
 * badly). A finished gesture is reported once (bridge.applyGesture); Python
 * builds and persists the op, re-renders and pushes a new document, which
 * replaces the optimistic local preview.
 */
(function () {
  'use strict';

  const SVG_NS = 'http://www.w3.org/2000/svg';
  const TOKEN_RE = /\b(BUTTON_\d+|POV_\d+_[URDL]+|AXIS_[A-Z][A-Z0-9_]*|[A-Z][A-Z0-9_]*?_MODIFIER_\d+(?:_[A-Z]+)?|[A-Z][A-Z0-9_]*?_MODIFIERS|TEMPLATE_NAME|CURRENT_DATE)\b/gi;
  const GRIP_PX = 7;
  const MIN_SIZE = 6;
  const ZOOM_STEPS = [0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 3, 4];
  const MODIFIER_ROLES = new Set(['modifier', 'modifier_key', 'modifier_action', 'modifiers']);

  const now = () => performance.now();
  const $ = (id) => document.getElementById(id);
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const round1 = (v) => Math.round(v * 10) / 10;

  // ── State ──────────────────────────────────────────────────────────────
  const canvas = $('canvas');
  const overlay = $('overlay');
  const stage = $('stage');
  const viewport = $('viewport');

  let bridge = null;
  let svg = null;
  let vb = { x: 0, y: 0, w: 0, h: 0 };
  let zoom = 1;
  let payload = { slots: [], overflow: {}, supported: true };
  const items = new Map(); // target -> item
  let selectedKey = null;
  let drag = null;
  let fitPending = true;

  // ── Coordinates ────────────────────────────────────────────────────────
  function toRoot(clientX, clientY) {
    const r = overlay.getBoundingClientRect();
    return { x: vb.x + ((clientX - r.left) / r.width) * vb.w, y: vb.y + ((clientY - r.top) / r.height) * vb.h };
  }
  function clientFromRoot(x, y) {
    const r = overlay.getBoundingClientRect();
    return { x: r.left + ((x - vb.x) / vb.w) * r.width, y: r.top + ((y - vb.y) / vb.h) * r.height };
  }
  function rectToRoot(cr) {
    const a = toRoot(cr.left, cr.top);
    const b = toRoot(cr.right, cr.bottom);
    return { x: a.x, y: a.y, w: b.x - a.x, h: b.y - a.y };
  }
  function union(a, b) {
    if (!a) return b;
    if (!b) return a;
    const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
    return { x, y, w: Math.max(a.x + a.w, b.x + b.w) - x, h: Math.max(a.y + a.h, b.y + b.h) - y };
  }
  function fromRect(r) {
    return r ? { x: r.x, y: r.y, w: r.width, h: r.height } : null;
  }

  // ── Loading ────────────────────────────────────────────────────────────
  async function loadDocument(url, payloadJson) {
    const t0 = now();
    let next = payload;
    try { next = JSON.parse(payloadJson || '{}'); } catch (e) { console.error('bad payload', e); }
    try {
      const resp = await fetch(url, { cache: 'no-store' });
      if (!resp.ok) throw new Error('document fetch failed: ' + resp.status);
      const text = await resp.text();
      const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
      const err = doc.querySelector('parsererror');
      if (err) throw new Error('SVG parse error: ' + norm(err.textContent).slice(0, 200));

      const keepSelection = next.selected !== undefined ? next.selected : selectedKey;
      teardownCanvas();
      payload = next;
      svg = document.importNode(doc.documentElement, true);
      // Pin the colour scheme so light-dark() resolves as the exporter does.
      svg.style.colorScheme = 'light';
      const vbAttr = (svg.getAttribute('viewBox') || '').split(/[\s,]+/).map(Number);
      const w = parseFloat(svg.getAttribute('width')) || vbAttr[2] || 800;
      const h = parseFloat(svg.getAttribute('height')) || vbAttr[3] || 600;
      vb = vbAttr.length === 4 && vbAttr.every((n) => !isNaN(n)) ? { x: vbAttr[0], y: vbAttr[1], w: vbAttr[2], h: vbAttr[3] } : { x: 0, y: 0, w, h };
      svg.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
      overlay.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
      canvas.appendChild(svg);
      if (fitPending) { fitPending = false; zoomFit(); } else { setZoom(zoom); }

      buildItems();
      buildHandles();
      if (keepSelection && items.has(keepSelection)) select(keepSelection, true); else select(null, true);
      setStatus('');
      report({ type: 'load', ms: round1(now() - t0), slots: items.size, bytes: text.length });
      if (bridge) bridge.ready(JSON.stringify({ loadMs: round1(now() - t0), slots: items.size, bytes: text.length }));
    } catch (e) {
      console.error(e);
      setStatus(String(e && e.message ? e.message : e), true);
      if (bridge) bridge.ready(JSON.stringify({ error: String(e) }));
    }
  }

  function teardownCanvas() {
    items.clear();
    selectedKey = null;
    drag = null;
    canvas.replaceChildren();
    overlay.replaceChildren();
    svg = null;
  }

  // ── Items (from the Python payload, geometry from annotations) ─────────
  function elementsFor(target) {
    if (!svg) return [];
    const quoted = target.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    return [...svg.querySelectorAll(`[data-jd-slot="${quoted}"]`)];
  }
  function measure(elements) {
    let box = null;
    for (const el of elements) {
      const cr = el.getBoundingClientRect();
      if (cr.width > 0 && cr.height > 0) box = union(box, rectToRoot(cr));
    }
    return box;
  }
  function buildItems() {
    const slots = payload.slots || [];
    if (slots.length) {
      for (const info of slots) {
        const elements = elementsFor(info.target);
        let bbox = fromRect(info.bbox);
        if (!bbox) bbox = measure(elements);
        if (!bbox) continue;
        const isAdded = !!info.added_uid;
        const kind = isAdded ? (info.role === 'note' ? 'note' : 'added') : 'slot';
        items.set(info.target, {
          target: info.target, info, elements, bbox, kind,
          movable: info.movable !== false, resizable: !!info.resizable, hidden: !!info.hidden,
          layer: info.layer || null, handle: null, live: { dx: 0, dy: 0, box: null },
        });
      }
      return;
    }
    // Fallback: no annotations (legacy / unsupported template) — show read-only outlines.
    const seen = new Set();
    for (const sw of svg.querySelectorAll('switch')) {
      const text = norm(sw.textContent);
      const m = text.match(TOKEN_RE);
      if (!m) continue;
      let key = m[0].toLowerCase() + '#1', n = 2;
      while (seen.has(key)) key = `${m[0].toLowerCase()}#${n++}`;
      seen.add(key);
      const label = sw.parentElement && sw.parentElement.localName === 'g' ? sw.parentElement : sw;
      const prev = label.previousElementSibling;
      const elements = prev && ['rect', 'ellipse', 'path', 'image'].includes(prev.localName) ? [prev, label] : [label];
      const bbox = measure(elements);
      if (!bbox) continue;
      items.set(key, { target: key, info: { key: m[0].toLowerCase(), role: 'action' }, elements, bbox, kind: 'slot', movable: false, resizable: false, hidden: false, layer: null, handle: null, live: { dx: 0, dy: 0, box: null } });
    }
  }

  function currentBox(item) {
    const b = item.live.box || item.bbox;
    return { x: b.x + item.live.dx, y: b.y + item.live.dy, w: b.w, h: b.h };
  }

  // ── Overlay handles ────────────────────────────────────────────────────
  function buildHandles() {
    overlay.replaceChildren();
    for (const item of items.values()) createHandle(item);
    drawBadges();
  }
  function createHandle(item) {
    const g = document.createElementNS(SVG_NS, 'g');
    const classes = ['handle'];
    if (item.kind !== 'slot') classes.push('added');
    if (item.kind === 'note') classes.push('note');
    if (item.resizable) classes.push('resizable');
    if (item.hidden) classes.push('hidden');
    if (item.layer === 'profile') classes.push('profile');
    if (!item.movable) classes.push('locked');
    g.setAttribute('class', classes.join(' '));
    g.dataset.key = item.target;
    const title = document.createElementNS(SVG_NS, 'title');
    title.textContent = item.info.key ? item.info.key.toUpperCase() : item.target;
    g.appendChild(title);
    const hit = document.createElementNS(SVG_NS, 'rect');
    hit.setAttribute('class', 'hit');
    g.appendChild(hit);
    for (const c of ['nw', 'ne', 'sw', 'se']) {
      const grip = document.createElementNS(SVG_NS, 'rect');
      grip.setAttribute('class', `grip ${c}`);
      g.appendChild(grip);
    }
    if (item.hidden) {
      const mark = document.createElementNS(SVG_NS, 'path');
      mark.setAttribute('class', 'hidden-mark');
      g.appendChild(mark);
    }
    overlay.appendChild(g);
    item.handle = g;
    updateHandle(item);
  }
  function updateHandle(item) {
    if (!item.handle) return;
    const b = currentBox(item);
    const hit = item.handle.children[1];
    hit.setAttribute('x', b.x);
    hit.setAttribute('y', b.y);
    hit.setAttribute('width', Math.max(b.w, 1));
    hit.setAttribute('height', Math.max(b.h, 1));
    const gs = GRIP_PX / zoom, half = gs / 2;
    const corners = { nw: [b.x, b.y], ne: [b.x + b.w, b.y], sw: [b.x, b.y + b.h], se: [b.x + b.w, b.y + b.h] };
    for (let i = 2; i < 6; i++) {
      const grip = item.handle.children[i];
      const c = corners[grip.getAttribute('class').split(' ')[1]];
      grip.setAttribute('x', c[0] - half);
      grip.setAttribute('y', c[1] - half);
      grip.setAttribute('width', gs);
      grip.setAttribute('height', gs);
    }
    const mark = item.handle.querySelector('.hidden-mark');
    if (mark) mark.setAttribute('d', `M ${b.x} ${b.y} L ${b.x + b.w} ${b.y + b.h} M ${b.x + b.w} ${b.y} L ${b.x} ${b.y + b.h}`);
  }
  function drawBadges() {
    const overflow = payload.overflow || {};
    for (const item of items.values()) {
      const info = item.info;
      if (item.kind !== 'slot' || info.role !== 'action' || !info.input_key) continue;
      const count = overflow[info.input_key.toUpperCase()];
      if (!count) continue;
      const b = item.bbox;
      const g = document.createElementNS(SVG_NS, 'g');
      g.setAttribute('class', 'badge');
      const size = Math.max(14, Math.min(20, b.h * 0.6));
      const label = `+${count}`;
      const width = size * (0.55 + 0.45 * label.length);
      const rect = document.createElementNS(SVG_NS, 'rect');
      rect.setAttribute('x', b.x + b.w - width / 2);
      rect.setAttribute('y', b.y - size / 2);
      rect.setAttribute('width', width);
      rect.setAttribute('height', size);
      rect.setAttribute('rx', size / 2);
      const text = document.createElementNS(SVG_NS, 'text');
      text.setAttribute('x', b.x + b.w);
      text.setAttribute('y', b.y);
      text.setAttribute('font-size', size * 0.7);
      text.textContent = label;
      g.appendChild(rect);
      g.appendChild(text);
      overlay.appendChild(g);
    }
  }

  // ── Optimistic local preview during a gesture ──────────────────────────
  function wrapForDrag(item) {
    if (item.wrappers) return;
    const byParent = new Map();
    for (const el of item.elements) {
      let node = el;
      // Climb out of Python's own move/hide wrappers so siblings stay together.
      while (node.parentNode && node.parentNode !== svg && node.parentNode.getAttribute && node.parentNode.getAttribute('data-jd-op') !== null) node = node.parentNode;
      if (!node.parentNode) continue;
      if (!byParent.has(node.parentNode)) byParent.set(node.parentNode, []);
      const list = byParent.get(node.parentNode);
      if (!list.includes(node)) list.push(node);
    }
    item.wrappers = [];
    for (const [parent, nodes] of byParent) {
      const g = document.createElementNS(SVG_NS, 'g');
      g.setAttribute('class', 'jd-live');
      parent.insertBefore(g, nodes[0]);
      for (const n of nodes) g.appendChild(n);
      item.wrappers.push(g);
    }
  }
  function applyLive(item) {
    const { dx, dy } = item.live;
    if (!item.wrappers) return;
    for (const g of item.wrappers) {
      if (Math.abs(dx) < 1e-6 && Math.abs(dy) < 1e-6) g.removeAttribute('transform');
      else g.setAttribute('transform', `translate(${round1(dx)} ${round1(dy)})`);
    }
  }
  function applyLiveResize(item) {
    const b = item.live.box;
    if (!b) return;
    for (const el of item.elements) {
      if (el.localName === 'rect') {
        el.setAttribute('x', b.x); el.setAttribute('y', b.y);
        el.setAttribute('width', Math.max(1, b.w)); el.setAttribute('height', Math.max(1, b.h));
      }
    }
  }

  // ── Selection ──────────────────────────────────────────────────────────
  function select(key, silent) {
    if (selectedKey && items.get(selectedKey)) items.get(selectedKey).handle.classList.remove('selected');
    selectedKey = key && items.has(key) ? key : null;
    if (selectedKey) {
      const h = items.get(selectedKey).handle;
      h.classList.add('selected');
      overlay.appendChild(h); // raise
    }
    if (bridge) bridge.selectSlot(selectedKey || '');
  }

  // ── Pointer interaction ────────────────────────────────────────────────
  function onPointerDown(e) {
    if (e.button !== 0) return;
    viewport.focus({ preventScroll: true });
    const handle = e.target.closest('.handle');
    if (!handle) { select(null); return; }
    const key = handle.dataset.key;
    const item = items.get(key);
    if (!item) return;
    select(key);
    if (!item.movable) return;
    const grip = e.target.classList.contains('grip') ? e.target.getAttribute('class').split(' ')[1] : null;
    if (grip && !item.resizable) return;
    drag = { key, item, grip, start: toRoot(e.clientX, e.clientY), startBox: currentBox(item), moved: false };
    try { overlay.setPointerCapture(e.pointerId); } catch (err) { /* synthetic events have no active pointer */ }
    e.preventDefault();
  }
  function onPointerMove(e) {
    if (!drag) return;
    const p = toRoot(e.clientX, e.clientY);
    const ddx = p.x - drag.start.x, ddy = p.y - drag.start.y;
    if (!drag.moved && Math.hypot(ddx, ddy) < 0.5) return;
    drag.moved = true;
    const item = drag.item;
    if (drag.grip) {
      const b = { ...drag.startBox };
      if (drag.grip.includes('e')) b.w = Math.max(MIN_SIZE, b.w + ddx);
      if (drag.grip.includes('s')) b.h = Math.max(MIN_SIZE, b.h + ddy);
      if (drag.grip.includes('w')) { const nw = Math.max(MIN_SIZE, b.w - ddx); b.x += b.w - nw; b.w = nw; }
      if (drag.grip.includes('n')) { const nh = Math.max(MIN_SIZE, b.h - ddy); b.y += b.h - nh; b.h = nh; }
      item.live.box = b;
      applyLiveResize(item);
    } else {
      wrapForDrag(item);
      item.live.dx = ddx;
      item.live.dy = ddy;
      applyLive(item);
    }
    updateHandle(item);
  }
  function onPointerUp(e) {
    if (!drag) return;
    const d = drag;
    drag = null;
    try { overlay.releasePointerCapture(e.pointerId); } catch (err) { /* ignore */ }
    if (!d.moved) return;
    const item = d.item;
    if (d.grip) {
      const b = item.live.box;
      sendGesture({ gesture: 'resize', target: item.target, dx: round1(b.x - item.bbox.x), dy: round1(b.y - item.bbox.y), width: round1(b.w), height: round1(b.h) });
    } else {
      sendGesture({ gesture: 'move', target: item.target, dx: round1(item.live.dx), dy: round1(item.live.dy) });
    }
  }
  function sendGesture(g) {
    if (!bridge) { setStatus('Bridge not connected', true); return; }
    bridge.applyGesture(JSON.stringify(g), (res) => {
      let r = {};
      try { r = JSON.parse(res); } catch (e) { r = { ok: false, error: String(e) }; }
      if (!r.ok) {
        setStatus(r.error || 'Change rejected', true);
        const item = items.get(g.target);
        if (item) { item.live = { dx: 0, dy: 0, box: null }; applyLive(item); updateHandle(item); }
      }
    });
  }
  function onDoubleClick(e) {
    const handle = e.target.closest('.handle');
    if (!handle) return;
    const item = items.get(handle.dataset.key);
    if (item && item.kind === 'note' && bridge) bridge.editNote(item.info.added_uid || item.target);
  }

  // ── Keyboard ───────────────────────────────────────────────────────────
  function nudge(dx, dy) {
    const item = selectedKey ? items.get(selectedKey) : null;
    if (!item || !item.movable) return;
    wrapForDrag(item);
    item.live.dx += dx; item.live.dy += dy;
    applyLive(item); updateHandle(item);
    if (bridge) bridge.nudge(item.target, dx, dy);
  }
  function onKeyDown(e) {
    const step = e.shiftKey ? 10 : 1;
    const map = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    if (map[e.key]) { e.preventDefault(); nudge(...map[e.key]); return; }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); if (bridge) { if (e.shiftKey) bridge.redo(); else bridge.undo(); } return; }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') { e.preventDefault(); if (bridge) bridge.redo(); return; }
    if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); if (selectedKey && bridge) bridge.hideSelected(selectedKey); return; }
    if (e.key === 'Escape') { select(null); return; }
    if (e.key === '+' || e.key === '=') { zoomStep(1); return; }
    if (e.key === '-') { zoomStep(-1); return; }
    if (e.key === '0') { zoomFit(); }
  }

  // ── Zoom ───────────────────────────────────────────────────────────────
  function setZoom(z) {
    zoom = Math.max(0.1, Math.min(8, z));
    if (!svg) return;
    const w = vb.w * zoom, h = vb.h * zoom;
    for (const el of [svg, overlay]) { el.setAttribute('width', w); el.setAttribute('height', h); }
    stage.style.width = `${w}px`;
    stage.style.height = `${h}px`;
    for (const item of items.values()) updateHandle(item);
    if (bridge) bridge.zoomChanged(Math.round(zoom * 100));
  }
  function zoomStep(dir) {
    const idx = ZOOM_STEPS.findIndex((s) => s >= zoom - 1e-6);
    const next = dir > 0 ? ZOOM_STEPS[Math.min(ZOOM_STEPS.length - 1, (idx < 0 ? ZOOM_STEPS.length - 1 : idx) + 1)] : ZOOM_STEPS[Math.max(0, (idx < 0 ? ZOOM_STEPS.length : idx) - 1)];
    setZoom(next);
  }
  function zoomFit() {
    const r = viewport.getBoundingClientRect();
    if (!vb.w || !vb.h || r.width < 60) { setZoom(1); return; }
    setZoom(Math.min((r.width - 48) / vb.w, (r.height - 48) / vb.h));
  }
  function onZoomRequested(cmd) {
    if (cmd === 'in') zoomStep(1);
    else if (cmd === 'out') zoomStep(-1);
    else if (cmd === 'fit') zoomFit();
    else if (cmd === '100') setZoom(1);
  }

  function setStatus(msg, isError) {
    const el = $('status');
    el.textContent = msg;
    el.hidden = !msg;
    el.classList.toggle('error', !!isError);
  }
  function report(obj) {
    if (bridge) bridge.report(JSON.stringify(obj));
  }

  // ── Bridge ─────────────────────────────────────────────────────────────
  function connectBridge() {
    return new Promise((resolve, reject) => {
      if (typeof QWebChannel === 'undefined') return reject(new Error('qwebchannel.js did not load'));
      if (typeof qt === 'undefined' || !qt.webChannelTransport) return reject(new Error('qt.webChannelTransport missing'));
      new QWebChannel(qt.webChannelTransport, (channel) => resolve(channel.objects.bridge));
    });
  }

  // ── Test / screenshot helpers ──────────────────────────────────────────
  function pointerEvent(type, x, y) {
    return new PointerEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, buttons: type === 'pointerup' ? 0 : 1 });
  }
  function simulateDrag(key, dx, dy, grip) {
    const item = items.get(key);
    if (!item) return false;
    const b = currentBox(item);
    const scale = overlay.getBoundingClientRect().width / vb.w;
    let target, start;
    if (grip) {
      target = item.handle.querySelector('.grip.' + grip);
      const corner = { nw: [b.x, b.y], ne: [b.x + b.w, b.y], sw: [b.x, b.y + b.h], se: [b.x + b.w, b.y + b.h] }[grip];
      start = clientFromRoot(corner[0], corner[1]);
    } else {
      target = item.handle.querySelector('.hit');
      start = clientFromRoot(b.x + b.w / 2, b.y + b.h / 2);
    }
    target.dispatchEvent(pointerEvent('pointerdown', start.x, start.y));
    overlay.dispatchEvent(pointerEvent('pointermove', start.x + (dx * scale) / 2, start.y + (dy * scale) / 2));
    overlay.dispatchEvent(pointerEvent('pointermove', start.x + dx * scale, start.y + dy * scale));
    overlay.dispatchEvent(pointerEvent('pointerup', start.x + dx * scale, start.y + dy * scale));
    return true;
  }

  window.jd = {
    get items() { return items; },
    get payload() { return payload; },
    get zoom() { return zoom; },
    get selected() { return selectedKey; },
    select, setZoom, zoomFit, zoomStep, nudge, simulateDrag,
    keys: () => [...items.keys()],
    currentBox: (key) => (items.has(key) ? currentBox(items.get(key)) : null),
    handleClasses: (key) => (items.has(key) ? items.get(key).handle.getAttribute('class') : null),
    badgeCount: () => overlay.querySelectorAll('.badge').length,
  };

  // ── Boot ───────────────────────────────────────────────────────────────
  function bind() {
    overlay.addEventListener('pointerdown', onPointerDown);
    overlay.addEventListener('pointermove', onPointerMove);
    overlay.addEventListener('pointerup', onPointerUp);
    overlay.addEventListener('pointercancel', onPointerUp);
    overlay.addEventListener('dblclick', onDoubleClick);
    document.addEventListener('keydown', onKeyDown);
    viewport.addEventListener('wheel', (e) => { if (e.ctrlKey) { e.preventDefault(); zoomStep(e.deltaY < 0 ? 1 : -1); } }, { passive: false });
  }
  async function boot() {
    bind();
    try {
      bridge = await connectBridge();
      bridge.documentChanged.connect((url, json) => { loadDocument(url, json); });
      bridge.selectRequested.connect((key) => select(key || null, true));
      bridge.zoomRequested.connect(onZoomRequested);
      bridge.ready(JSON.stringify({ boot: true }));
    } catch (e) {
      setStatus(String(e && e.message ? e.message : e), true);
      console.error(e);
    }
  }
  boot();
})();
