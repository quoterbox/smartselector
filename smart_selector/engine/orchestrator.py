from __future__ import annotations

from collections import Counter

from ..config import SelectorConfig
from ..dom import build_dom_index, build_target_context, parse_html, resolve_target
from ..generation import build_css_generators, build_xpath_generators
from ..models import BuildResult, Candidate, EvaluatedCandidate, SelectorVariant
from ..scoring import CandidateScorer
from ..validation import SelectorEvaluator


def _mixed_sort_key(variant: SelectorVariant) -> tuple[float, int, int]:
    return (-variant.score, variant.match_count, len(variant.selector))


def _type_sort_key(variant: SelectorVariant) -> tuple[int, float, int, int]:
    # Prefer unique variants inside per-type views, then score.
    return (0 if variant.is_unique else 1, -variant.score, variant.match_count, len(variant.selector))


class SelectorOrchestrator:
    def __init__(self, config: SelectorConfig | None = None):
        self.config = config or SelectorConfig()
        self.xpath_generators = build_xpath_generators()
        self.css_generators = build_css_generators()
        self.evaluator = SelectorEvaluator()
        self.scorer = CandidateScorer(self.config)

    def build(self, html_source: str, absolute_xpath: str) -> BuildResult:
        doc = parse_html(html_source)
        target = resolve_target(doc, absolute_xpath)
        if target is None:
            return BuildResult(
                target_found=False,
                absolute_xpath=absolute_xpath,
                variants=[],
                xpath_variants=[],
                css_variants=[],
                variants_with_text=[],
                best_xpath=None,
                best_css=None,
                debug_report={"error": "target_not_found"},
            )

        context = build_target_context(doc, target, absolute_xpath)
        index = build_dom_index(doc, self.config)

        raw_candidates = self._collect_candidates(context, index)
        deduped_candidates = self._dedupe(raw_candidates)
        evaluated_candidates = [
            EvaluatedCandidate(candidate=candidate, evaluation=self.evaluator.evaluate(candidate, context))
            for candidate in deduped_candidates
        ]

        valid_candidates = [item for item in evaluated_candidates if item.evaluation.target_matched]

        all_variants: list[SelectorVariant] = []
        for item in valid_candidates:
            breakdown, level = self.scorer.score(item.candidate, item.evaluation)
            all_variants.append(
                SelectorVariant(
                    selector=item.candidate.selector,
                    selector_type=item.candidate.selector_type,
                    strategy=item.candidate.strategy,
                    score=breakdown.total_score,
                    stability_level=level,
                    match_count=item.evaluation.match_count,
                    target_matched=item.evaluation.target_matched,
                    is_unique=item.evaluation.match_count == 1,
                    explain=item.candidate.explain,
                    is_text_based=bool(item.candidate.features.get("uses_text")),
                    breakdown=breakdown,
                )
            )

        all_variants.sort(key=_mixed_sort_key)

        limit = self.config.max_variants
        mixed_variants = all_variants[:limit]

        xpath_variants = [variant for variant in all_variants if variant.selector_type == "xpath"]
        css_variants = [variant for variant in all_variants if variant.selector_type == "css"]
        text_variants = [variant for variant in all_variants if variant.is_text_based]

        xpath_variants.sort(key=_type_sort_key)
        css_variants.sort(key=_type_sort_key)
        text_variants.sort(key=_type_sort_key)

        xpath_variants = xpath_variants[:limit]
        css_variants = css_variants[:limit]
        text_variants = text_variants[:limit]

        best_xpath = xpath_variants[0].selector if xpath_variants else None
        best_css = css_variants[0].selector if css_variants else None

        debug_report = self._debug_report(raw_candidates, deduped_candidates, evaluated_candidates)
        if not self.config.include_debug_report:
            debug_report = {}

        return BuildResult(
            target_found=True,
            absolute_xpath=absolute_xpath,
            variants=mixed_variants,
            xpath_variants=xpath_variants,
            css_variants=css_variants,
            variants_with_text=text_variants,
            best_xpath=best_xpath,
            best_css=best_css,
            debug_report=debug_report,
        )

    def _collect_candidates(self, context, index) -> list[Candidate]:
        candidates: list[Candidate] = []
        generators = [*self.xpath_generators, *self.css_generators]
        for generator in generators:
            try:
                candidates.extend(generator.generate(context, index, self.config))
            except Exception as exc:
                candidates.append(
                    Candidate(
                        selector="",
                        selector_type="xpath",
                        strategy=generator.name,
                        explain=f"generator_failed:{exc}",
                        features={"invalid": True},
                    )
                )

        return [candidate for candidate in candidates if candidate.selector]

    def _dedupe(self, candidates: list[Candidate]) -> list[Candidate]:
        seen: set[tuple[str, str]] = set()
        deduped: list[Candidate] = []
        for candidate in candidates:
            key = (candidate.selector_type, candidate.selector)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)
        return deduped

    def _debug_report(
        self,
        raw: list[Candidate],
        deduped: list[Candidate],
        evaluated: list[EvaluatedCandidate],
    ) -> dict[str, object]:
        return {
            "raw_candidates": len(raw),
            "deduped_candidates": len(deduped),
            "target_matched_candidates": sum(1 for item in evaluated if item.evaluation.target_matched),
            "strategy_counts": dict(Counter(candidate.strategy for candidate in deduped)),
            "errors": [
                {
                    "strategy": item.candidate.strategy,
                    "selector": item.candidate.selector,
                    "error": item.evaluation.error,
                }
                for item in evaluated
                if item.evaluation.error
            ],
        }
