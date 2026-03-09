from __future__ import annotations

from ..models import Candidate, EvaluationResult


def estimate_mutation_score(candidate: Candidate, evaluation: EvaluationResult) -> float:
    """Heuristic resilience score in the range [0, 20]."""
    if not evaluation.target_matched:
        return 0.0

    features = candidate.features
    score = 10.0

    if features.get("uses_id"):
        score += 6.0
    if features.get("uses_data_attr"):
        score += 4.0

    stable_attr_count = float(features.get("stable_attr_count", 0))
    if stable_attr_count >= 2:
        score += 3.0
    elif stable_attr_count >= 1:
        score += 2.0

    if features.get("uses_ancestor_anchor"):
        score += 1.5

    if features.get("uses_position"):
        score -= 6.0
    if features.get("uses_text"):
        score -= 5.0

    dynamic_tokens = float(features.get("dynamic_tokens", 0))
    score -= dynamic_tokens * 3.0

    return max(0.0, min(20.0, round(score, 2)))
