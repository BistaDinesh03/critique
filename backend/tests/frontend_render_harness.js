// Test-only harness: executes every <script> a frontend page declares (inline
// blocks and local /static/*.js assets) inside a minimal DOM stub and returns
// the HTML the page actually produced.
//
// It exists so pytest can assert on the real rendering boundary (the string that
// gets assigned to innerHTML) instead of on an isolated helper function.
//
// Usage: node frontend_render_harness.js <scenario.json>
//   {
//     "page": "C:/.../frontend/discover.html",
//     "calls": [
//       { "fn": "showProjects", "args": [[ {...} ]] },
//       { "clickCreatedContaining": "Continue with email" },
//       { "dispatchDocumentClickCreated": "Continue with email" },
//       { "checkInput": {"name": "clarity", "value": "very_clear"} },
//       { "submitId": "response-form" },
//       { "evaluate": "formatAge('2026-09-24T10:00:00Z')", "as": "age" }
//     ],
//     "fetch": { "/api/projects/?": { "status": 200, "body": { ... } } },
//     "location": "/project/1/results",
//     "read": { "byId": "content" }   // or { "created": true }
//   }
//
// Prints a single JSON object on stdout:
//   { errors: [], html, created, createdMeta, flags, requests, storage, ids, values }
// `created`/`createdMeta` only contain elements that are actually attached to
// the document (a node the page built but never appended is never shown to
// anyone); `createdMeta` exposes reflected properties (href, type, name,
// className) of those elements; `flags` maps element ids to visibility state;
// `requests` lists every fetch issued after setup; `storage` is a dump of
// sessionStorage/localStorage after the calls.

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

// Faithful model of the HTML fragment serialization the browser performs for a
// text node: &, nbsp, < and > are escaped, quotes are NOT. This is what made
// the original textContent->innerHTML helper unsafe inside attributes.
function serializeText(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/\u00A0/g, '&nbsp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function detachChildren(el) {
  (el.children || []).forEach((child) => {
    if (child) child.parentNode = null;
  });
  el.children = [];
}

function makeElement(tagName, created) {
  const state = { html: null, text: '' };
  // Classes are real state: pages open and close UI by toggling a class (the
  // mobile nav, for one) and then read it back, so a no-op classList would hide
  // the very state the tests are trying to observe.
  const classes = new Set();

  const el = {
    tagName: String(tagName || 'div').toUpperCase(),
    value: '',
    checked: false,
    disabled: false,
    id: '',
    style: {},
    dataset: {},
    attributes: {},
    children: [],
    parentNode: null,
    classList: {
      add(...names) {
        names.forEach((name) => name && classes.add(name));
      },
      remove(...names) {
        names.forEach((name) => classes.delete(name));
      },
      // Returns the resulting state like the DOM does, which is what callers
      // use to report whether the panel they toggled is now open.
      toggle(name, force) {
        const turnOn = force === undefined ? !classes.has(name) : !!force;
        if (turnOn) classes.add(name);
        else classes.delete(name);
        return turnOn;
      },
      contains(name) {
        return classes.has(name);
      },
      get length() {
        return classes.size;
      },
    },
    setAttribute(k, v) {
      if (k === 'class') {
        el.className = v;
        return;
      }
      this.attributes[k] = v;
    },
    getAttribute(k) {
      if (k === 'class') return el.className || null;
      return k in this.attributes ? this.attributes[k] : null;
    },
    removeAttribute(k) {
      if (k === 'class') {
        el.className = '';
        return;
      }
      delete this.attributes[k];
    },
    hasAttribute(k) {
      return k in this.attributes;
    },
    // The markup this element owns, without anything it may have appended:
    // used for assertions and for locating the element a test wants to act on.
    ownInnerHTML() {
      return state.html !== null ? state.html : serializeText(state.text);
    },
    // Clears only the markup this element owns, leaving nodes the page
    // appended alone. The capture reset uses this instead of assigning
    // innerHTML: that reset is harness bookkeeping, not something a page does,
    // and now that ids nest for real (so a click can reach an ancestor's
    // listener) wiping children would destroy persistent UI built during load,
    // such as the injected nav login menu.
    resetMarkup() {
      state.html = null;
      state.text = '';
    },
    contains(other) {
      let node = other;
      const seen = new Set();
      while (node && !seen.has(node)) {
        if (node === this) return true;
        seen.add(node);
        node = node.parentNode;
      }
      return false;
    },
    appendChild(child) {
      this.children.push(child);
      if (child) child.parentNode = this;
      return child;
    },
    insertBefore(child, ref) {
      if (!ref) return this.appendChild(child);
      const i = this.children.indexOf(ref);
      if (i < 0) return this.appendChild(child);
      this.children.splice(i, 0, child);
      if (child) child.parentNode = this;
      return child;
    },
    removeChild(child) {
      const i = this.children.indexOf(child);
      if (i >= 0) this.children.splice(i, 1);
      return child;
    },
    handlers: [],
    addEventListener(type, fn) {
      this.handlers.push({ type, fn });
    },
    removeEventListener() {},
    dispatchEvent() {
      return true;
    },
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    },
    focus() {},
    blur() {},
    click() {},
    reset() {},
    scrollIntoView() {},
    remove() {},
    getBoundingClientRect() {
      return { top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 };
    },
  };

  Object.defineProperties(el, {
    // Kept in sync with classList so pages (and tests) see one source of truth.
    className: {
      configurable: true,
      enumerable: true,
      get() {
        return Array.from(classes).join(' ');
      },
      set(value) {
        classes.clear();
        String(value === null || value === undefined ? '' : value)
          .split(/\s+/)
          .filter(Boolean)
          .forEach((name) => classes.add(name));
      },
    },
    innerHTML: {
      configurable: true,
      enumerable: true,
      get() {
        return state.html !== null ? state.html : serializeText(state.text);
      },
      set(value) {
        state.html = value === null || value === undefined ? '' : String(value);
        // Faithful to the browser: assigning innerHTML replaces the element's
        // children, so the old ones leave the document (their click targets are
        // detached by the time outer listeners run).
        detachChildren(el);
      },
    },
    textContent: {
      configurable: true,
      enumerable: true,
      get() {
        return state.text;
      },
      set(value) {
        state.text = value === null || value === undefined ? '' : String(value);
        state.html = null;
        detachChildren(el);
      },
    },
    innerText: {
      configurable: true,
      enumerable: true,
      get() {
        return state.text;
      },
      set(value) {
        state.text = value === null || value === undefined ? '' : String(value);
        state.html = null;
        detachChildren(el);
      },
    },
  });

  if (created) created.push(el);
  return el;
}

function makeStorage() {
  const map = new Map();
  return {
    getItem(k) {
      return map.has(k) ? map.get(k) : null;
    },
    setItem(k, v) {
      map.set(k, String(v));
    },
    removeItem(k) {
      map.delete(k);
    },
    clear() {
      map.clear();
    },
    key(i) {
      return Array.from(map.keys())[i] === undefined ? null : Array.from(map.keys())[i];
    },
    get length() {
      return map.size;
    },
  };
}

function makeFetch(routes) {
  const requests = [];
  const fetchImpl = function fetch(url, options) {
    const target = String(url);
    requests.push({
      url: target,
      method: (options && options.method) || 'GET',
      body: options && options.body ? String(options.body) : '',
    });
    const key = Object.keys(routes).find((k) => target.indexOf(k) !== -1);
    const spec = key ? routes[key] : { status: 404, body: {} };
    const status = spec.status || 200;
    return Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(spec.body),
      text: () => Promise.resolve(JSON.stringify(spec.body)),
      headers: { get: () => null },
    });
  };
  fetchImpl.requests = requests;
  return fetchImpl;
}

// Executes every <script> the page declares, in document order: inline blocks
// and local /static/*.js assets (so shared helpers such as ui.js are the real
// ones under test). External URLs are skipped.
function repoRootFor(pagePath) {
  let dir = path.dirname(path.resolve(pagePath));
  for (let i = 0; i < 8; i++) {
    if (fs.existsSync(path.join(dir, 'static', 'ui.js'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return process.cwd();
}

function pageScripts(html, root) {
  const out = [];
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    const attrs = m[1] || '';
    const srcMatch = attrs.match(/\bsrc\s*=\s*["']([^"']+)["']/i);
    if (srcMatch) {
      const src = srcMatch[1].split('?')[0];
      if (!/^(https?:)?\/\//i.test(src) && src.startsWith('/')) {
        const file = path.join(root, src.replace(/^\/+/, ''));
        if (fs.existsSync(file)) {
          out.push({ label: src, code: fs.readFileSync(file, 'utf8') });
        } else {
          out.push({ label: src, missing: true });
        }
      }
      continue;
    }
    if (m[2].trim()) out.push({ label: 'inline', code: m[2] });
  }
  return out;
}

function settle(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const scenarioPath = process.argv[2];
  if (!scenarioPath) throw new Error('scenario path required');
  // Strip a possible UTF-8 BOM (Windows editors add one) before parsing.
  const scenario = JSON.parse(fs.readFileSync(scenarioPath, 'utf8').replace(/^﻿/, ''));

  const html = fs.readFileSync(scenario.page, 'utf8').replace(/^﻿/, '');
  const errors = [];
  const created = [];
  const elements = new Map();

  const documentHandlers = [];

  // Radio-group state lives here, not in element objects: the feedback form's
  // inputs are produced by innerHTML strings, so there is no element to flip.
  // document.querySelector('input[name="..."]:checked') reads from this map.
  const checkedInputs = new Map();

  // A radio the page cannot hold in an element object (its markup came from an
  // innerHTML string) is answered through this proxy, whose checked state is
  // the harness-level radio-group map -- same read/write behaviour as the DOM.
  const inputProxy = (name, value) => ({
    tagName: 'INPUT',
    type: 'radio',
    name,
    get value() {
      return value;
    },
    get checked() {
      return checkedInputs.get(name) === value;
    },
    set checked(v) {
      if (v) checkedInputs.set(name, value);
      else if (checkedInputs.get(name) === value) checkedInputs.delete(name);
    },
  });

  const documentStub = {
    documentElement: null,
    body: null,
    cookie: 'critique_csrf=test-token',
    hidden: false,
    title: '',
    readyState: 'complete',
    getElementById(id) {
      if (!elements.has(id)) {
        const el = makeElement('div');
        elements.set(id, el);
        // Mirror the browser: an element with an id is in the document, so it
        // has a parent and can take part in layout/manipulation.
        if (documentStub.body) documentStub.body.appendChild(el);
      }
      return elements.get(id);
    },
    createElement(tag) {
      return makeElement(tag, created);
    },
    createTextNode(text) {
      return { nodeValue: text };
    },
    querySelector(sel) {
      // Narrow but real: the only attribute selectors any page uses are on the
      // feedback form's radios, whose group state has no element object here.
      // Every other selector keeps the old not-found behaviour.
      const m = /^input\[name="([^"]+)"\](?:\[value="([^"]*)"\])?(:checked)?$/.exec(String(sel || ''));
      if (!m) return null;
      const name = m[1];
      const value = m[2];
      if (m[3] === ':checked') {
        if (!checkedInputs.has(name)) return null;
        return inputProxy(name, checkedInputs.get(name));
      }
      if (value !== undefined) return inputProxy(name, value);
      return checkedInputs.has(name) ? inputProxy(name, checkedInputs.get(name)) : null;
    },
    querySelectorAll() {
      return [];
    },
    addEventListener(type, fn) {
      documentHandlers.push({ type, fn });
    },
    removeEventListener() {},
    write() {},
  };
  documentStub.body = makeElement('body');
  documentStub.documentElement = makeElement('html');

  // scenario.location may carry a query string ("/project/1?resume=feedback"):
  // pages branch on window.location.search (the auth resume flags), so it has
  // to reach them the way a real URL would -- pathname stays clean, because
  // pages also derive ids from it.
  const rawLocation = scenario.location || '/';
  const queryAt = rawLocation.indexOf('?');
  const locationPathname = queryAt === -1 ? rawLocation : rawLocation.slice(0, queryAt);
  const locationSearch = queryAt === -1 ? '' : rawLocation.slice(queryAt);

  const locationStub = {
    pathname: locationPathname,
    search: locationSearch,
    hash: '',
    origin: 'http://testserver',
    protocol: 'http:',
    host: 'testserver',
    href: 'http://testserver/',
  };
  const historyStub = {
    replaceState() {},
    pushState() {},
    back() {},
  };

  const localStorage = makeStorage();
  const sessionStorage = makeStorage();

  const analyticsStub = {
    trackEvent() {},
    pageView() {},
    track() {},
  };

  const windowStub = {
    location: locationStub,
    history: historyStub,
    localStorage,
    sessionStorage,
    document: documentStub,
    CritiqueAnalytics: analyticsStub,
    addEventListener() {},
    removeEventListener() {},
    open() {},
    scrollTo() {},
    matchMedia() {
      return { matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} };
    },
    getComputedStyle() {
      return { getPropertyValue() { return ''; } };
    },
    requestAnimationFrame(fn) {
      return setTimeout(fn, 0);
    },
    cancelAnimationFrame(id) {
      clearTimeout(id);
    },
    navigator: {
      clipboard: {
        writeText: () => Promise.resolve(),
      },
      userAgent: 'test-harness',
    },
  };

  const fetchStub = makeFetch(scenario.fetch || {});

  // --- event plumbing -----------------------------------------------------
  const eventPathOf = (target) => {
    const path = [];
    const seen = new Set();
    let node = target;
    while (node && !seen.has(node)) {
      path.push(node);
      seen.add(node);
      node = node.parentNode;
    }
    path.push(documentStub, windowStub);
    return path;
  };

  const makeEvent = (type, target, path) => ({
    type,
    bubbles: type === 'click' || type === 'submit',
    cancelable: true,
    defaultPrevented: false,
    propagationStopped: false,
    target,
    preventDefault() {
      this.defaultPrevented = true;
    },
    stopPropagation() {
      this.propagationStopped = true;
    },
    composedPath() {
      return path;
    },
  });

  const bubbleToDocument = (event, errs) => {
    try {
      documentHandlers
        .filter((h) => h.type === event.type)
        .forEach((h) => h.fn(event));
    } catch (e) {
      errs.push(`document ${event.type}: ${e && e.message ? e.message : String(e)}`);
    }
  };

  // A real click bubbles from the target's parent up to the document, and every
  // listener on the way sees it unless a handler stopped propagation. The
  // target's own listeners have already run, so the walk starts above it.
  const bubbleAlongPath = (event, errs) => {
    for (const node of event.composedPath()) {
      if (event.propagationStopped) return;
      if (node === event.target) continue;
      const handlers = node === documentStub
        ? documentHandlers
        : (node && node.handlers) || [];
      handlers
        .filter((h) => h.type === event.type)
        .forEach((h) => {
          try {
            h.fn(event);
          } catch (e) {
            errs.push(`bubble ${event.type}: ${e && e.message ? e.message : String(e)}`);
          }
        });
    }
  };

  const sandbox = {
    document: documentStub,
    window: windowStub,
    location: locationStub,
    history: historyStub,
    localStorage,
    sessionStorage,
    navigator: windowStub.navigator,
    fetch: fetchStub,
    setTimeout(fn, ms) {
      const delay = Math.min(Number(ms) || 0, 2);
      return setTimeout(fn, delay);
    },
    clearTimeout(id) {
      clearTimeout(id);
    },
    setInterval() {
      return 0;
    },
    clearInterval() {},
    queueMicrotask(fn) {
      queueMicrotask(fn);
    },
    requestAnimationFrame(fn) {
      return setTimeout(fn, 0);
    },
    cancelAnimationFrame(id) {
      clearTimeout(id);
    },
    console,
    URL,
    CritiqueAnalytics: analyticsStub,
    CritiqueUI: {
      showToast() {},
      showConfirmModal() {},
      showLoginModal() {},
    },
    trackPageView() {},
    trackEvent() {},
    alert() {},
    confirm() {
      return true;
    },
    prompt() {
      return '';
    },
  };

  const ctx = vm.createContext(sandbox);

  // Give the ids that exist in the page markup their real nesting. The stub
  // otherwise creates every element on demand as a flat child of <body>, which
  // meant a click on #login-btn could never reach the #navbar-nav listener that
  // closes the mobile menu -- so bugs that only appear through ancestor
  // bubbling (mobile login menu collapsing the instant it opened) could be
  // neither reproduced nor caught here. Script and style bodies are skipped:
  // they contain markup-shaped strings that are not part of the document.
  const VOID_TAGS = new Set([
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
    'param', 'source', 'track', 'wbr',
    // inline SVG fragments that are never explicitly closed
    'path', 'circle', 'rect', 'line', 'polyline', 'polygon', 'ellipse', 'use', 'stop',
  ]);

  const buildIdTree = (source) => {
    const text = source.replace(/<!--[\s\S]*?-->/g, '');
    const tagRe = /<\s*(\/?)\s*([a-zA-Z][a-zA-Z0-9]*)((?:"[^"]*"|'[^']*'|[^>])*?)(\/?)\s*>/g;
    const stack = [{ tag: 'body', el: documentStub.body }];
    const parentOf = () => {
      for (let i = stack.length - 1; i >= 0; i--) if (stack[i].el) return stack[i].el;
      return documentStub.body;
    };
    let m;
    while ((m = tagRe.exec(text))) {
      const closing = m[1] === '/';
      const tag = m[2].toLowerCase();
      const attrs = m[3] || '';
      const selfClosing = m[4] === '/' || VOID_TAGS.has(tag);

      if (closing) {
        // Pop up to the matching open tag; unclosed tags in the source are
        // dropped along the way, the way a browser's parser recovers.
        for (let i = stack.length - 1; i > 0; i--) {
          if (stack[i].tag === tag) {
            stack.length = i;
            break;
          }
        }
        continue;
      }

      if (tag === 'script' || tag === 'style') {
        const end = text.indexOf('</' + tag, tagRe.lastIndex);
        if (end !== -1) tagRe.lastIndex = end;
        if (!selfClosing) stack.push({ tag, el: null });
        continue;
      }

      const idMatch = /\sid\s*=\s*["']([^"']+)["']/.exec(attrs);
      const classMatch = /\sclass\s*=\s*["']([^"']*)["']/.exec(attrs);
      let el = null;
      if (idMatch && !elements.has(idMatch[1]) && !selfClosing) {
        el = makeElement(tag);
        el.id = idMatch[1];
        if (classMatch) el.className = classMatch[1];
        elements.set(idMatch[1], el);
        parentOf().appendChild(el);
      }

      if (!selfClosing) stack.push({ tag, el });
    }
  };

  buildIdTree(html);

  const blocks = pageScripts(html, repoRootFor(scenario.page));
  blocks.forEach((block, i) => {
    if (block.missing) {
      errors.push(`script ${block.label}: file not found`);
      return;
    }
    try {
      vm.runInContext(block.code, ctx, { filename: `${scenario.page}#${block.label}-${i + 1}` });
    } catch (e) {
      errors.push(`script ${i + 1}: ${e && e.message ? e.message : String(e)}`);
    }
  });

  // Let page-initiated async work (loaders, auth checks) settle, then reset the
  // capture buffers so only the invoked render call is measured.
  await settle(50);
  created.length = 0;
  fetchStub.requests.length = 0;
  elements.forEach((el) => {
    el.resetMarkup();
  });

  const calls = scenario.calls || [];
  // Values read back from the page (see the `evaluate` call type).
  const values = {};
  for (const call of calls) {
    if (call.setValuePlaceholder) {
      const { placeholder, value } = call.setValuePlaceholder;
      const target = created.find((el) => el.placeholder === placeholder);
      if (!target) {
        errors.push(`setValue: no created element with placeholder ${JSON.stringify(placeholder)}`);
      } else {
        target.value = value;
      }
      continue;
    }

    // Pick a radio: group state only (one value per name), like the DOM.
    if (call.checkInput) {
      const { name, value } = call.checkInput;
      if (!name || value === undefined || value === null) {
        errors.push('checkInput: needs {name, value}');
      } else {
        checkedInputs.set(name, value);
      }
      continue;
    }

    const wantsClick = call.clickCreatedContaining || call.clickId;
    const wantsSubmit = call.submitCreatedContaining || call.submitId;
    if (wantsClick || wantsSubmit) {
      const type = wantsSubmit ? 'submit' : 'click';
      let target = null;
      let label = '';
      if (call.submitId) {
        // A form submit fired by the form itself, so its own submit listener runs.
        label = `#${call.submitId}`;
        target = elements.get(call.submitId) || null;
      } else if (call.clickId) {
        label = `#${call.clickId}`;
        target = elements.get(call.clickId) || null;
      } else {
        const needle = wantsSubmit || call.clickCreatedContaining;
        label = JSON.stringify(needle);
        target = created.find(
          (el) => String(el.ownInnerHTML() || '').indexOf(needle) !== -1
        );
        // A submit is fired by the form, which is the parent of the button.
        if (target && wantsSubmit && target.parentNode && target.parentNode.handlers) {
          target = target.parentNode;
        }
      }
      if (!target) {
        errors.push(`${type}: no element for ${label}`);
        continue;
      }

      // Capture the event path now, exactly as a browser does when it starts
      // dispatching: a re-render triggered by a handler must not rewrite it.
      const path = eventPathOf(target);
      const handlers = target.handlers.filter((h) => h.type === type);
      if (!handlers.length) {
        errors.push(`${type}: no ${type} handler on ${label}`);
        continue;
      }
      const event = makeEvent(type, target, path);
      try {
        handlers.forEach((h) => h.fn(event));
      } catch (e) {
        errors.push(`${type}: ${e && e.message ? e.message : String(e)}`);
      }

      // A click (or a form submit) keeps bubbling up the tree unless a handler
      // stopped it.
      if (event.bubbles && !event.propagationStopped) {
        bubbleAlongPath(event, errors);
      }
      continue;
    }

    // A click that lands straight on the document (i.e. outside the menu).
    if (call.dispatchDocumentClickId || call.dispatchDocumentClickCreated) {
      let target = null;
      let label = '';
      if (call.dispatchDocumentClickId) {
        label = `#${call.dispatchDocumentClickId}`;
        target = elements.get(call.dispatchDocumentClickId) || null;
      } else {
        const needle = call.dispatchDocumentClickCreated;
        label = JSON.stringify(needle);
        target = created.find(
          (el) => String(el.ownInnerHTML() || '').indexOf(needle) !== -1
        );
      }
      if (!target) {
        errors.push(`document click: no element for ${label}`);
        continue;
      }
      bubbleToDocument(makeEvent('click', target, eventPathOf(target)), errors);
      continue;
    }

    // Read a value straight out of the page -- a pure helper's return value,
    // for example -- instead of having to render it into the DOM first.
    if (call.evaluate) {
      let value;
      try {
        value = vm.runInContext(call.evaluate, ctx);
      } catch (e) {
        errors.push(`evaluate ${call.evaluate}: ${e && e.message ? e.message : String(e)}`);
        continue;
      }
      if (value && typeof value.then === 'function') value = await value;
      values[call.as || call.evaluate] = value;
      continue;
    }

    let fn;
    try {
      fn = vm.runInContext(call.fn, ctx);
    } catch (e) {
      errors.push(`lookup ${call.fn}: ${e && e.message ? e.message : String(e)}`);
      continue;
    }
    if (typeof fn !== 'function') {
      errors.push(`lookup ${call.fn}: not a function (${typeof fn})`);
      continue;
    }
    try {
      const result = fn.apply(null, call.args || []);
      if (result && typeof result.then === 'function') await result;
    } catch (e) {
      errors.push(`call ${call.fn}: ${e && e.message ? e.message : String(e)}`);
    }
  }

  await settle(50);

  const ids = {};
  elements.forEach((el, id) => {
    ids[id] = el.innerHTML;
  });

  // Only elements that are actually in the document count as rendered: a node
  // the page built but never appended is never shown to anyone.
  const isAttached = (el) => {
    let node = el;
    const seen = new Set();
    while (node && !seen.has(node)) {
      if (node === documentStub.body) return true;
      seen.add(node);
      node = node.parentNode;
    }
    return false;
  };
  const rendered = created.filter(isAttached);

  const createdHtml = rendered.map((el) => el.ownInnerHTML()).filter(Boolean);
  const createdMeta = rendered.map((el) => ({
    tag: el.tagName,
    className: el.className,
    href: el.href,
    type: el.type,
    name: el.name,
    placeholder: el.placeholder,
    text: el.textContent,
  }));

  // Visibility/state flags keyed by element id, so tests can assert on things
  // like an open/closed menu rather than on markup alone.
  const flags = {};
  const flagOf = (el) => ({
    hidden: !!el.hidden,
    ariaExpanded: el.getAttribute ? el.getAttribute('aria-expanded') : null,
    ariaLabel: el.getAttribute ? el.getAttribute('aria-label') : null,
    // Loading placeholders are announced through aria-busy and hidden with
    // display, so tests can assert that a placeholder actually resolved
    // (or was removed on failure) instead of guessing from markup.
    ariaBusy: el.getAttribute ? el.getAttribute('aria-busy') : null,
    display: el.style ? el.style.display || null : null,
    // Classes carry open/closed state (the mobile nav's navbar-nav-open).
    className: el.className || null,
  });
  elements.forEach((el, id) => {
    flags[id] = flagOf(el);
  });
  // Walk the document too: some ids (the injected nav menu) belong to elements
  // the page built before the capture buffers were reset.
  const stack = [documentStub.body];
  const seen = new Set();
  while (stack.length) {
    const node = stack.pop();
    if (!node || seen.has(node)) continue;
    seen.add(node);
    if (node.id) flags[node.id] = flagOf(node);
    (node.children || []).forEach((child) => stack.push(child));
  }

  let out = '';
  const read = scenario.read || {};
  if (read.byId) out = ids[read.byId] || '';
  else if (read.created) out = createdHtml.join('\n');

  const dumpStorage = (storage) => {
    const out = {};
    for (let i = 0; i < storage.length; i++) {
      const key = storage.key(i);
      out[key] = storage.getItem(key);
    }
    return out;
  };

  process.stdout.write(
    JSON.stringify({
      errors,
      html: out,
      created: createdHtml,
      createdMeta,
      flags,
      requests: fetchStub.requests,
      storage: { session: dumpStorage(sessionStorage), local: dumpStorage(localStorage) },
      ids,
      values,
    })
  );
}

process.on('unhandledRejection', (err) => {
  // Page code we execute may reject; record instead of crashing the harness.
  process.stderr.write(`unhandledRejection: ${err && err.message ? err.message : String(err)}\n`);
});

main().catch((e) => {
  process.stderr.write(`${e && e.stack ? e.stack : String(e)}\n`);
  process.exit(1);
});
