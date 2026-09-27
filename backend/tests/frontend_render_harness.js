// Test-only harness: executes the *real* inline JavaScript of a frontend page
// inside a minimal DOM stub and returns the HTML the page actually produced.
//
// It exists so pytest can assert on the real rendering boundary (the string that
// gets assigned to innerHTML) instead of on an isolated helper function.
//
// Usage: node frontend_render_harness.js <scenario.json>
//   {
//     "page": "C:/.../frontend/discover.html",
//     "calls": [{ "fn": "showProjects", "args": [[ {...} ]] }],
//     "fetch": { "/api/projects/?": { "status": 200, "body": { ... } } },
//     "location": "/project/1/results",
//     "read": { "byId": "content" }   // or { "created": true }
//   }
//
// Prints a single JSON object on stdout: { errors: [], html, created, ids }.

'use strict';

const fs = require('fs');
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

function makeElement(tagName, created) {
  const state = { html: null, text: '' };

  const el = {
    tagName: String(tagName || 'div').toUpperCase(),
    value: '',
    checked: false,
    disabled: false,
    className: '',
    id: '',
    style: {},
    dataset: {},
    attributes: {},
    children: [],
    parentNode: null,
    classList: {
      add() {},
      remove() {},
      toggle() {},
      contains() {
        return false;
      },
    },
    setAttribute(k, v) {
      this.attributes[k] = v;
    },
    getAttribute(k) {
      return k in this.attributes ? this.attributes[k] : null;
    },
    removeAttribute(k) {
      delete this.attributes[k];
    },
    hasAttribute(k) {
      return k in this.attributes;
    },
    appendChild(child) {
      this.children.push(child);
      if (child) child.parentNode = this;
      return child;
    },
    removeChild(child) {
      const i = this.children.indexOf(child);
      if (i >= 0) this.children.splice(i, 1);
      return child;
    },
    addEventListener() {},
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
    innerHTML: {
      configurable: true,
      enumerable: true,
      get() {
        return state.html !== null ? state.html : serializeText(state.text);
      },
      set(value) {
        state.html = value === null || value === undefined ? '' : String(value);
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
  return function fetch(url) {
    const target = String(url);
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
}

function inlineScripts(html) {
  const out = [];
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    if (/\bsrc\s*=/i.test(m[1])) continue;
    if (m[2].trim()) out.push(m[2]);
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

  const documentStub = {
    documentElement: null,
    body: null,
    cookie: 'critique_csrf=test-token',
    hidden: false,
    title: '',
    readyState: 'complete',
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, makeElement('div'));
      return elements.get(id);
    },
    createElement(tag) {
      return makeElement(tag, created);
    },
    createTextNode(text) {
      return { nodeValue: text };
    },
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    },
    addEventListener() {},
    removeEventListener() {},
    write() {},
  };
  documentStub.body = makeElement('body');
  documentStub.documentElement = makeElement('html');

  const locationStub = {
    pathname: scenario.location || '/',
    search: '',
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

  const sandbox = {
    document: documentStub,
    window: windowStub,
    location: locationStub,
    history: historyStub,
    localStorage,
    sessionStorage,
    navigator: windowStub.navigator,
    fetch: makeFetch(scenario.fetch || {}),
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
  const blocks = inlineScripts(html);
  blocks.forEach((code, i) => {
    try {
      vm.runInContext(code, ctx, { filename: `${scenario.page}#script-${i + 1}` });
    } catch (e) {
      errors.push(`script ${i + 1}: ${e && e.message ? e.message : String(e)}`);
    }
  });

  // Let page-initiated async work (loaders, auth checks) settle, then reset the
  // capture buffers so only the invoked render call is measured.
  await settle(50);
  created.length = 0;
  elements.forEach((el) => {
    el.innerHTML = '';
  });

  const calls = scenario.calls || [];
  for (const call of calls) {
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

  const createdHtml = created.map((el) => el.innerHTML).filter(Boolean);

  let out = '';
  const read = scenario.read || {};
  if (read.byId) out = ids[read.byId] || '';
  else if (read.created) out = createdHtml.join('\n');

  process.stdout.write(JSON.stringify({ errors, html: out, created: createdHtml, ids }));
}

process.on('unhandledRejection', (err) => {
  // Page code we execute may reject; record instead of crashing the harness.
  process.stderr.write(`unhandledRejection: ${err && err.message ? err.message : String(err)}\n`);
});

main().catch((e) => {
  process.stderr.write(`${e && e.stack ? e.stack : String(e)}\n`);
  process.exit(1);
});
