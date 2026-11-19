import json
import shutil
import pytest
from tests.test_project_share import run

pytestmark = [
    pytest.mark.frontend_render,
    pytest.mark.skipif(
        shutil.which("node") is None,
        reason="node is required to run the frontend rendering harness",
    ),
]

SETUP = {'evaluate': """
var scrollListeners = [], clickListeners = [], scrollCalls = [];
var btn = document.getElementById('back-to-top');
var origWinAdd = window.addEventListener;
window.addEventListener = function(type, fn, opts) {
  if (type === 'scroll') scrollListeners.push(fn);
  if (origWinAdd) return origWinAdd.call(window, type, fn, opts);
};
var origBtnAdd = btn.addEventListener;
btn.addEventListener = function(type, fn, opts) {
  if (type === 'click') clickListeners.push(fn);
  if (origBtnAdd) return origBtnAdd.call(btn, type, fn, opts);
};
window.scrollTo = function(opts) { scrollCalls.push(opts); };
window.scrollY = 0;
CritiqueUI.initBackToTop();
true
"""}


def scroll_to(y):
    return {
        'evaluate': "window.scrollY = %d; scrollListeners.forEach(function(f){ f(); }); btn.hidden" % y,
        'as': 'hidden_%d' % y,
    }


@pytest.mark.parametrize('y,hidden', [(0, True), (300, True), (301, False), (1000, False)])
def test_threshold(tmp_path, y, hidden):
    result = run(tmp_path, 'discover.html', [SETUP, scroll_to(y)])
    assert result['values']['hidden_%d' % y] is hidden


def test_hides_again_when_scrolled_back_up(tmp_path):
    result = run(tmp_path, 'discover.html', [SETUP, scroll_to(500), scroll_to(0)])
    assert result['values']['hidden_500'] is False
    assert result['values']['hidden_0'] is True


@pytest.mark.parametrize('reduced,behavior', [(True, 'auto'), (False, 'smooth')])
def test_click_scrolls_to_top(tmp_path, reduced, behavior):
    click = {'evaluate': """
window.matchMedia = function() { return { matches: %s }; };
clickListeners.forEach(function(f){ f(); });
JSON.stringify(scrollCalls)
""" % ('true' if reduced else 'false'), 'as': 'calls'}
    result = run(tmp_path, 'discover.html', [SETUP, click])
    calls = json.loads(result['values']['calls'])
    assert len(calls) == 1
    assert calls[0]['top'] == 0
    assert calls[0]['behavior'] == behavior


def test_missing_button_does_not_throw(tmp_path):
    js = ("document.getElementById = function() { return null; }; "
          "CritiqueUI.initBackToTop(); true")
    run(tmp_path, 'discover.html', [{'evaluate': js}])