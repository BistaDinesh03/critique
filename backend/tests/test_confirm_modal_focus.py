from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent.parent
UI_JS = REPO_DIR / "static" / "ui.js"


def test_confirm_modal_focus_trap_and_listener_cleanup():
    """Verify showConfirmModal saves and restores focus, traps Tab, and removes keydown listener."""
    source = UI_JS.read_text(encoding="utf-8")

    # Saves previous active element
    assert "var previousActiveElement = document.activeElement;" in source

    # Restores focus on close
    assert "previousActiveElement.focus();" in source

    # Cleans up keydown listener in closeModal so every exit path (cancel, confirm, backdrop, Escape) cleans up
    assert "document.removeEventListener('keydown', keyHandler);" in source

    # Focus trap cycling for Tab and Shift+Tab
    assert "e.key === 'Tab'" in source
    assert "e.shiftKey" in source
    assert "last.focus()" in source
    assert "first.focus()" in source
