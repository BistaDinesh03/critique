import pytest

from app.config import Settings


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        pytest.param(None, {"BistaDinesh03"}, id="unset"),
        pytest.param("", set(), id="empty"),
        pytest.param("alice,bob", {"alice", "bob"}, id="list"),
        pytest.param(" alice, , bob, ", {"alice", "bob"}, id="whitespace-and-empty-entries"),
        pytest.param("Alice, BOB", {"Alice", "BOB"}, id="preserves-case"),
    ],
)

def test_analytics_owner_usernames(monkeypatch, env_value, expected):
    if env_value is None:
        monkeypatch.delenv("ANALYTICS_OWNER_USERNAMES", raising=False)
    else:
        monkeypatch.setenv("ANALYTICS_OWNER_USERNAMES", env_value)

    assert Settings().ANALYTICS_OWNER_USERNAMES == expected
