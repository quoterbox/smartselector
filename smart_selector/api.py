from __future__ import annotations

from .config import SelectorConfig
from .engine import SelectorOrchestrator, build_collection_selector as _build_collection_selector
from .models import BuildResult, CollectionSelectorResult, SelectorVariant


def build_selectors(
    html: str,
    absolute_xpath: str,
    config: SelectorConfig | None = None,
) -> BuildResult:
    orchestrator = SelectorOrchestrator(config)
    return orchestrator.build(html, absolute_xpath)


def build_best_selector(
    html: str,
    absolute_xpath: str,
    config: SelectorConfig | None = None,
) -> SelectorVariant | None:
    result = build_selectors(html, absolute_xpath, config)
    return result.variants[0] if result.variants else None


def build_xpath_variants(
    html: str,
    absolute_xpath: str,
    config: SelectorConfig | None = None,
) -> list[SelectorVariant]:
    result = build_selectors(html, absolute_xpath, config)
    return result.xpath_variants


def build_css_variants(
    html: str,
    absolute_xpath: str,
    config: SelectorConfig | None = None,
) -> list[SelectorVariant]:
    result = build_selectors(html, absolute_xpath, config)
    return result.css_variants


def build_text_variants(
    html: str,
    absolute_xpath: str,
    config: SelectorConfig | None = None,
) -> list[SelectorVariant]:
    result = build_selectors(html, absolute_xpath, config)
    return result.variants_with_text


def build_collection_selector(
    html: str,
    first_absolute_xpath: str,
    second_absolute_xpath: str,
    config: SelectorConfig | None = None,
) -> CollectionSelectorResult:
    return _build_collection_selector(
        html=html,
        first_absolute_xpath=first_absolute_xpath,
        second_absolute_xpath=second_absolute_xpath,
        config=config,
    )


def analyze_selector(
    html: str,
    absolute_xpath: str,
    config: SelectorConfig | None = None,
) -> dict:
    result = build_selectors(html, absolute_xpath, config)
    return result.to_dict()


def analyze_collection_selector(
    html: str,
    first_absolute_xpath: str,
    second_absolute_xpath: str,
    config: SelectorConfig | None = None,
) -> dict:
    result = build_collection_selector(
        html=html,
        first_absolute_xpath=first_absolute_xpath,
        second_absolute_xpath=second_absolute_xpath,
        config=config,
    )
    return result.to_dict()
