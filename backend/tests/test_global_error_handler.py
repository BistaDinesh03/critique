"""Global client-side error handler in static/ui.js (issue #788).

Loads ui.js into a Node vm with a tiny DOM stub, fires window `error` and
`unhandledrejection` events, and inspects the notice the handler renders.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

UI_JS = Path(__file__).resolve().parent.parent.parent / "static" / "ui.js"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="node is required to run ui.js"
)

DRIVER = r"""
const fs = require('fs');
const vm = require('vm');
function el(tag) {
  const e = {
    tagName: tag.toUpperCase(), children: [], attrs: {}, handlers: {}, style: {},
    parentNode: null, id: '', className: '', textContent: '',
    classList: { add() {}, remove() {}, contains() { return false; } },
    setAttribute(k, v) { this.attrs[k] = v; },
    getAttribute(k) { return this.attrs[k]; },
    appendChild(c) { c.parentNode = this; this.children.push(c); return c; },
    removeChild(c) { this.children = this.children.filter((x) => x !== c); c.parentNode = null; return c; },
    remove() { if (this.parentNode) this.parentNode.removeChild(this); },
    addEventListener(t, f) { (this.handlers[t] = this.handlers[t] || []).push(f); },
    removeEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
  };
  return e;
}
function walk(n, out) { out.push(n); n.children.forEach((c) => walk(c, out)); return out; }
const body = el('body');
const doc = {
  body, readyState: 'complete',
  createElement: el,
  getElementById(id) { return walk(body, []).find((n) => n.id === id) || null; },
  querySelector() { return null; }, querySelectorAll() { return []; },
  addEventListener() {}, removeEventListener() {},
};
const winHandlers = {};
let reloads = 0;
const logged = [];
const win = {
  document: doc,
  location: { pathname: '/', search: '', reload() { reloads += 1; } },
  addEventListener(t, f) { (winHandlers[t] = winHandlers[t] || []).push(f); },
  removeEventListener() {},
  matchMedia() { return { matches: false }; },
  setTimeout, clearTimeout,
  fetch() { return Promise.resolve({ ok: false, status: 401, json: async () => ({}) }); },
};
win.window = win;
const fakeConsole = { error: (...a) => logged.push(a.map(String).join(' ')), log() {}, warn() {} };
const ctx = vm.createContext({ window: win, document: doc, console: fakeConsole, setTimeout, clearTimeout, fetch: win.fetch, location: win.location, Promise });
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);

const steps = JSON.parse(process.argv[2]);
const prevented = [];
for (const s of steps) {
  if (s.type === 'error' || s.type === 'unhandledrejection') {
    const ev = s.type === 'error'
      ? { type: 'error', message: s.message, error: s.name ? Object.assign(new Error(s.message), { name: s.name, stack: 'STACKTRACE at secret.js:1' }) : undefined, preventDefault() { prevented.push(1); } }
      : { type: 'unhandledrejection', reason: Object.assign(new Error(s.message), { name: s.name || 'Error', stack: 'STACKTRACE at secret.js:1' }), preventDefault() { prevented.push(1); } };
    (winHandlers[s.type] || []).forEach((f) => f(ev));
  } else if (s.type === 'click') {
    const b = walk(body, []).find((n) => n.attrs['data-error-action'] === s.action);
    if (b) (b.handlers.click || []).forEach((f) => f({ preventDefault() {}, stopPropagation() {} }));
  }
}
const nodes = walk(body, []);
const banners = nodes.filter((n) => n.attrs['data-global-error'] !== undefined);
process.stdout.write(JSON.stringify({
  listeners: Object.keys(winHandlers),
  banners: banners.length,
  role: banners[0] && banners[0].attrs.role,
  text: nodes.map((n) => n.textContent).join(' '),
  actions: nodes.map((n) => n.attrs['data-error-action']).filter(Boolean),
  logged, reloads, prevented: prevented.length,
}));
"""


def run(steps):
    proc = subprocess.run(
        ["node", "-e", DRIVER, str(UI_JS), json.dumps(steps)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_normal_flow_registers_listeners_and_stays_silent():
    r = run([])
    assert "error" in r["listeners"] and "unhandledrejection" in r["listeners"]
    assert r["banners"] == 0 and r["logged"] == []


def test_runtime_error_logged_and_friendly_notice_shown():
    r = run([{"type": "error", "message": "boom is not a function", "name": "TypeError"}])
    assert r["banners"] == 1
    assert r["role"] == "alert"
    assert any("boom is not a function" in line for line in r["logged"])
    assert "Something went wrong" in r["text"]
    assert "boom" not in r["text"] and "STACKTRACE" not in r["text"] and "TypeError" not in r["text"]
    assert r["prevented"] == 0
    assert "reload" in r["actions"] and "dismiss" in r["actions"]


def test_unhandled_rejection_logged_and_notice_shown():
    r = run([{"type": "unhandledrejection", "message": "network exploded"}])
    assert r["banners"] == 1
    assert any("network exploded" in line for line in r["logged"])
    assert "network exploded" not in r["text"] and "STACKTRACE" not in r["text"]
    assert r["prevented"] == 0


def test_error_loop_renders_single_banner():
    r = run([{"type": "error", "message": f"e{i}", "name": "Error"} for i in range(25)])
    assert r["banners"] == 1


def test_benign_noise_ignored():
    r = run([
        {"type": "error", "message": "ResizeObserver loop completed with undelivered notifications."},
        {"type": "error", "message": "ResizeObserver loop limit exceeded"},
        {"type": "unhandledrejection", "message": "The user aborted a request.", "name": "AbortError"},
    ])
    assert r["banners"] == 0


def test_reload_action_reloads_page():
    r = run([{"type": "error", "message": "x", "name": "Error"}, {"type": "click", "action": "reload"}])
    assert r["reloads"] == 1


def test_dismiss_removes_notice_and_later_errors_can_show_again():
    r = run([{"type": "error", "message": "x", "name": "Error"}, {"type": "click", "action": "dismiss"}])
    assert r["banners"] == 0 and r["reloads"] == 0
