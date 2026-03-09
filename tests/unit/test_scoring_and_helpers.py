from lxml import html as lxml_html

from smart_selector.config import SelectorConfig
from smart_selector.dom.resolver import resolve_target, resolve_target_strict
from smart_selector.generation.base import meaningful_classes, xpath_literal
from smart_selector.models import Candidate, EvaluationResult
from smart_selector.scoring.rules import CandidateScorer


def test_xpath_literal_supports_single_and_double_quotes() -> None:
    value = "John's \"best\" quote"
    literal = xpath_literal(value)

    assert literal.startswith("concat(")


def test_meaningful_classes_filters_utility_and_noisy_tokens() -> None:
    config = SelectorConfig()
    doc = lxml_html.fromstring('<div class="text-sm cardRoot css-1a2b3c product-card"></div>')
    node = doc.xpath("//div")[0]

    classes = meaningful_classes(node, config, index=type("Idx", (), {"class_frequency": lambda *_: 1})())
    assert "text-sm" not in classes
    assert "css-1a2b3c" not in classes
    assert "product-card" in classes


def test_scorer_penalizes_position_based_selectors() -> None:
    scorer = CandidateScorer(SelectorConfig())

    robust_candidate = Candidate(
        selector="//button[@id='buy-button']",
        selector_type="xpath",
        strategy="test",
        explain="robust",
        features={"uses_id": True, "stable_attr_count": 1},
    )
    fragile_candidate = Candidate(
        selector="//div[4]/button[2]",
        selector_type="xpath",
        strategy="test",
        explain="fragile",
        features={"uses_position": True},
    )

    robust_score, _ = scorer.score(robust_candidate, EvaluationResult(match_count=1, target_matched=True))
    fragile_score, _ = scorer.score(fragile_candidate, EvaluationResult(match_count=1, target_matched=True))

    assert robust_score.total_score > fragile_score.total_score


def test_resolve_target_tolerant_falls_back_when_absolute_index_is_wrong() -> None:
    doc = lxml_html.fromstring("<html><body><div><div><span id='x'>ok</span></div></div></body></html>")
    broken_xpath = "/html/body/div[4]/div/span"

    strict = resolve_target_strict(doc, broken_xpath)
    tolerant = resolve_target(doc, broken_xpath)

    assert strict is None
    assert tolerant is not None
    assert tolerant.tag == "span"
