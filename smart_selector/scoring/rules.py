from __future__ import annotations

from ..config import SelectorConfig
from ..models import Candidate, EvaluationResult, ScoreBreakdown
from .stability import estimate_mutation_score


def _selector_depth(candidate: Candidate) -> int:
    depth = candidate.features.get("selector_depth")
    if isinstance(depth, (int, float)):
        return int(depth)

    selector = candidate.selector
    if candidate.selector_type == "xpath":
        return max(1, selector.count("/"))
    return max(1, selector.count(" ") + selector.count(">") + 1)


def _uniqueness_score(match_count: int) -> float:
    if match_count == 1:
        return 45.0
    if match_count == 2:
        return 28.0
    if match_count <= 5:
        return 16.0
    if match_count <= 12:
        return 8.0
    return 0.0


def _stability_level(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


class CandidateScorer:
    def __init__(self, config: SelectorConfig):
        self.config = config

    def score(self, candidate: Candidate, evaluation: EvaluationResult) -> tuple[ScoreBreakdown, str]:
        if not evaluation.target_matched:
            breakdown = ScoreBreakdown(
                uniqueness_score=0.0,
                anchor_score=0.0,
                readability_score=0.0,
                mutation_score=0.0,
                fragility_penalty=100.0,
                total_score=0.0,
            )
            return breakdown, "D"

        features = candidate.features
        uniqueness = _uniqueness_score(evaluation.match_count)

        anchor = 0.0
        if features.get("uses_id"):
            anchor += 20.0
        if features.get("uses_data_attr"):
            anchor += 14.0

        stable_attr_count = float(features.get("stable_attr_count", 0))
        anchor += min(12.0, stable_attr_count * 5.0)

        if features.get("uses_ancestor_anchor"):
            anchor += 6.0

        depth = _selector_depth(candidate)
        selector_length = len(candidate.selector)

        length_penalty = min(22.0, selector_length * 0.16)
        depth_penalty = max(0, depth - 4) * 2.2

        readability = 24.0 - length_penalty - depth_penalty
        if candidate.selector_type == "css":
            readability += 1.0
        readability = max(0.0, round(readability, 2))

        fragility = 0.0
        if features.get("uses_position"):
            fragility += 12.0
        if features.get("uses_text"):
            fragility += 10.0
        if features.get("uses_absolute"):
            fragility += 18.0

        fragility += float(features.get("dynamic_tokens", 0)) * 5.0
        if evaluation.match_count > 1:
            fragility += 4.0

        if depth > 8:
            fragility += (depth - 8) * 2.5
        if selector_length > 120:
            fragility += min(25.0, (selector_length - 120) * 0.12)

        fragility = round(fragility, 2)

        mutation = estimate_mutation_score(candidate, evaluation) if self.config.enable_mutation_score else 0.0
        total = max(0.0, min(100.0, round(uniqueness + anchor + readability + mutation - fragility, 2)))

        breakdown = ScoreBreakdown(
            uniqueness_score=uniqueness,
            anchor_score=round(anchor, 2),
            readability_score=readability,
            mutation_score=mutation,
            fragility_penalty=fragility,
            total_score=total,
        )
        return breakdown, _stability_level(total)
