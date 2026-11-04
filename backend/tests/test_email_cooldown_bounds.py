"""Regression tests bounding the per-email magic-link cooldown map (issue #106).

The magic-link request endpoint is unauthenticated, so every distinct
normalized email becomes a permanent dict entry. These tests pin the same
bounding pattern the general rate limiter got in #48: a periodic sweep of
fully-expired entries plus a hard cap with LRU eviction.
"""

import time

import pytest

import app.auth as auth_module


@pytest.fixture(autouse=True)
def reset_cooldown_map():
    auth_module._EMAIL_COOLDOWN.clear()
    auth_module._email_cooldown_calls = 0
    yield
    auth_module._EMAIL_COOLDOWN.clear()
    auth_module._email_cooldown_calls = 0


def test_second_request_within_window_is_blocked():
    check = auth_module._email_cooldown_check_and_set
    assert check("user@example.com") is False
    assert check("user@example.com") is True


def test_map_stays_bounded_under_distinct_email_flood():
    check = auth_module._email_cooldown_check_and_set
    max_keys = auth_module._EMAIL_COOLDOWN_MAX_TRACKED_KEYS
    for i in range(max_keys + 500):
        check(f"user{i}@example.com")
    assert len(auth_module._EMAIL_COOLDOWN) <= max_keys


def test_lru_eviction_removes_the_oldest_email_first():
    check = auth_module._email_cooldown_check_and_set
    max_keys = auth_module._EMAIL_COOLDOWN_MAX_TRACKED_KEYS
    for i in range(max_keys):
        check(f"user{i}@example.com")
    assert len(auth_module._EMAIL_COOLDOWN) == max_keys
    assert "user0@example.com" in auth_module._EMAIL_COOLDOWN

    check("fresh@example.com")

    assert len(auth_module._EMAIL_COOLDOWN) == max_keys
    assert "user0@example.com" not in auth_module._EMAIL_COOLDOWN
    assert "fresh@example.com" in auth_module._EMAIL_COOLDOWN


def test_sweep_drops_fully_expired_entries_and_keeps_active_ones():
    now = time.time()
    auth_module._EMAIL_COOLDOWN["expired@example.com"] = now - (
        auth_module._EMAIL_COOLDOWN_SECONDS + 1
    )
    auth_module._EMAIL_COOLDOWN["active@example.com"] = now

    auth_module._sweep_expired_email_cooldown(now)

    assert "expired@example.com" not in auth_module._EMAIL_COOLDOWN
    assert "active@example.com" in auth_module._EMAIL_COOLDOWN


def test_periodic_sweep_runs_on_interval_and_releases_memory():
    check = auth_module._email_cooldown_check_and_set
    auth_module._email_cooldown_calls = (
        auth_module._EMAIL_COOLDOWN_SWEEP_INTERVAL - 1
    )
    now = time.time()
    # An old entry that the sweep must remove, plus one the sweep must keep.
    auth_module._EMAIL_COOLDOWN["stale@example.com"] = now - (
        auth_module._EMAIL_COOLDOWN_SECONDS + 1
    )

    assert check("new@example.com") is False
    assert auth_module._email_cooldown_calls == auth_module._EMAIL_COOLDOWN_SWEEP_INTERVAL
    assert "stale@example.com" not in auth_module._EMAIL_COOLDOWN
    assert "new@example.com" in auth_module._EMAIL_COOLDOWN
