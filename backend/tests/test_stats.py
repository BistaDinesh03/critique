from app.stats import calculate_stats
from app.models import Response


class MockResponse:
    """Simple mock for Response objects."""
    def __init__(self, clarity, would_use):
        self.clarity = clarity
        self.would_use = would_use


def test_calculate_stats_zero_responses():
    """Test stats with no responses."""
    stats = calculate_stats([])
    assert stats["total"] == 0
    assert stats["clarity"]["very_clear"] == 0
    assert stats["clarity"]["mostly_clear"] == 0
    assert stats["clarity"]["confusing"] == 0
    assert stats["would_use"]["yes"] == 0
    assert stats["would_use"]["maybe"] == 0
    assert stats["would_use"]["no"] == 0


def test_calculate_stats_one_response():
    """Test stats with one response."""
    responses = [MockResponse("very_clear", "yes")]
    stats = calculate_stats(responses)
    
    assert stats["total"] == 1
    assert stats["clarity"]["very_clear"] == 100.0
    assert stats["clarity"]["mostly_clear"] == 0
    assert stats["clarity"]["confusing"] == 0
    assert stats["would_use"]["yes"] == 100.0
    assert stats["would_use"]["maybe"] == 0
    assert stats["would_use"]["no"] == 0


def test_calculate_stats_many_responses():
    """Test stats with multiple responses."""
    responses = [
        MockResponse("very_clear", "yes"),
        MockResponse("very_clear", "yes"),
        MockResponse("mostly_clear", "maybe"),
        MockResponse("confusing", "no"),
    ]
    stats = calculate_stats(responses)
    
    assert stats["total"] == 4
    # Clarity: 2 very_clear (50%), 1 mostly_clear (25%), 1 confusing (25%)
    assert stats["clarity"]["very_clear"] == 50.0
    assert stats["clarity"]["mostly_clear"] == 25.0
    assert stats["clarity"]["confusing"] == 25.0
    # Would use: 2 yes (50%), 1 maybe (25%), 1 no (25%)
    assert stats["would_use"]["yes"] == 50.0
    assert stats["would_use"]["maybe"] == 25.0
    assert stats["would_use"]["no"] == 25.0


def test_calculate_stats_rounding():
    """Test that percentages are rounded to 1 decimal place."""
    # 3 responses: 33.333...% each
    responses = [
        MockResponse("very_clear", "yes"),
        MockResponse("mostly_clear", "maybe"),
        MockResponse("confusing", "no"),
    ]
    stats = calculate_stats(responses)
    
    assert stats["total"] == 3
    assert stats["clarity"]["very_clear"] == 33.3
    assert stats["clarity"]["mostly_clear"] == 33.3
    assert stats["clarity"]["confusing"] == 33.3
    assert stats["would_use"]["yes"] == 33.3
    assert stats["would_use"]["maybe"] == 33.3
    assert stats["would_use"]["no"] == 33.3


def test_calculate_stats_all_same():
    """Test stats when all responses are the same."""
    responses = [
        MockResponse("very_clear", "yes"),
        MockResponse("very_clear", "yes"),
        MockResponse("very_clear", "yes"),
    ]
    stats = calculate_stats(responses)
    
    assert stats["total"] == 3
    assert stats["clarity"]["very_clear"] == 100.0
    assert stats["clarity"]["mostly_clear"] == 0
    assert stats["clarity"]["confusing"] == 0
    assert stats["would_use"]["yes"] == 100.0
    assert stats["would_use"]["maybe"] == 0
    assert stats["would_use"]["no"] == 0
