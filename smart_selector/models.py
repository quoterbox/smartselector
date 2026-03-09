from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


SelectorType = Literal["xpath", "css"]


@dataclass(slots=True)
class Candidate:
    selector: str
    selector_type: SelectorType
    strategy: str
    explain: str
    features: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationResult:
    match_count: int
    target_matched: bool
    error: str | None = None


@dataclass(slots=True)
class EvaluatedCandidate:
    candidate: Candidate
    evaluation: EvaluationResult


@dataclass(slots=True)
class ScoreBreakdown:
    uniqueness_score: float
    anchor_score: float
    readability_score: float
    mutation_score: float
    fragility_penalty: float
    total_score: float

    def to_dict(self) -> dict[str, float]:
        return {
            "uniqueness_score": self.uniqueness_score,
            "anchor_score": self.anchor_score,
            "readability_score": self.readability_score,
            "mutation_score": self.mutation_score,
            "fragility_penalty": self.fragility_penalty,
            "total_score": self.total_score,
        }


@dataclass(slots=True)
class SelectorVariant:
    selector: str
    selector_type: SelectorType
    strategy: str
    score: float
    stability_level: str
    match_count: int
    target_matched: bool
    is_unique: bool
    explain: str
    is_text_based: bool
    breakdown: ScoreBreakdown

    def to_dict(self) -> dict[str, Any]:
        return {
            "selector": self.selector,
            "selector_type": self.selector_type,
            "strategy": self.strategy,
            "score": self.score,
            "stability_level": self.stability_level,
            "match_count": self.match_count,
            "target_matched": self.target_matched,
            "is_unique": self.is_unique,
            "explain": self.explain,
            "is_text_based": self.is_text_based,
            "breakdown": self.breakdown.to_dict(),
        }


@dataclass(slots=True)
class BuildResult:
    target_found: bool
    absolute_xpath: str
    variants: list[SelectorVariant]
    xpath_variants: list[SelectorVariant]
    css_variants: list[SelectorVariant]
    variants_with_text: list[SelectorVariant]
    best_xpath: str | None
    best_css: str | None
    debug_report: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_found": self.target_found,
            "absolute_xpath": self.absolute_xpath,
            "best_xpath": self.best_xpath,
            "best_css": self.best_css,
            "variants": [variant.to_dict() for variant in self.variants],
            "xpath_variants": [variant.to_dict() for variant in self.xpath_variants],
            "css_variants": [variant.to_dict() for variant in self.css_variants],
            "variants_with_text": [variant.to_dict() for variant in self.variants_with_text],
            "debug_report": self.debug_report,
        }


@dataclass(slots=True)
class CollectionSelectorResult:
    ok: bool
    reason: str | None
    first_input_xpath: str
    second_input_xpath: str
    resolved_first_xpath: str | None
    resolved_second_xpath: str | None
    collection_xpath: str | None
    collection_css: str | None
    item_xpath_template: str | None
    item_css_template: str | None
    sample_item_xpath: str | None
    sample_item_css: str | None
    estimated_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "first_input_xpath": self.first_input_xpath,
            "second_input_xpath": self.second_input_xpath,
            "resolved_first_xpath": self.resolved_first_xpath,
            "resolved_second_xpath": self.resolved_second_xpath,
            "collection_xpath": self.collection_xpath,
            "collection_css": self.collection_css,
            "item_xpath_template": self.item_xpath_template,
            "item_css_template": self.item_css_template,
            "sample_item_xpath": self.sample_item_xpath,
            "sample_item_css": self.sample_item_css,
            "estimated_count": self.estimated_count,
        }
