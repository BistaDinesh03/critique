from typing import Dict, List


def calculate_stats(responses: list) -> Dict:
    """Calculate aggregated statistics from responses.

    Args:
        responses: List of Response objects with clarity and would_use fields.

    Returns:
        Dict with total count, clarity percentages, and would_use percentages.
    """
    total = len(responses)

    if total == 0:
        return {
            "total": 0,
            "clarity": {
                "very_clear": 0,
                "mostly_clear": 0,
                "confusing": 0,
            },
            "would_use": {
                "yes": 0,
                "maybe": 0,
                "no": 0,
            },
        }

    # Count clarity values
    clarity_counts = {"very_clear": 0, "mostly_clear": 0, "confusing": 0}
    would_use_counts = {"yes": 0, "maybe": 0, "no": 0}

    for response in responses:
        clarity = response.clarity
        would_use = response.would_use

        if clarity in clarity_counts:
            clarity_counts[clarity] += 1
        if would_use in would_use_counts:
            would_use_counts[would_use] += 1

    # Calculate percentages (rounded to 1 decimal place)
    clarity_pcts = {
        key: round((count / total) * 100, 1)
        for key, count in clarity_counts.items()
    }
    would_use_pcts = {
        key: round((count / total) * 100, 1)
        for key, count in would_use_counts.items()
    }

    return {
        "total": total,
        "clarity": clarity_pcts,
        "would_use": would_use_pcts,
    }
