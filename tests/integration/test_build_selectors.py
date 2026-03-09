from dataclasses import dataclass
from pathlib import Path

import pytest
from lxml import html as lxml_html

from smart_selector import build_collection_selector, build_selectors


@dataclass(frozen=True)
class FixtureCase:
    file_name: str
    unique_query: str
    text_query: str
    collection_first_query: str
    collection_second_query: str


FIXTURES: list[FixtureCase] = [
    FixtureCase(
        file_name="amazon.html",
        unique_query="//*[@id='nav-search-submit-button']",
        text_query="(//a[normalize-space()='Gift Cards'])[1]",
        collection_first_query="(//*[@data-component-type='s-search-result'])[1]",
        collection_second_query="(//*[@data-component-type='s-search-result'])[2]",
    ),
    FixtureCase(
        file_name="coinmarketcap.html",
        unique_query="//*[@id='__next']",
        text_query="(//*[@data-test='global-header__crypto-historical-snapshots'])[1]",
        collection_first_query="(//table//tbody/tr[.//a[contains(@href, '/currencies/')]])[1]",
        collection_second_query="(//table//tbody/tr[.//a[contains(@href, '/currencies/')]])[2]",
    ),
    FixtureCase(
        file_name="dailyscraper.html",
        unique_query="//*[@id='masthead']",
        text_query="(//a[normalize-space()='Checkout'])[1]",
        collection_first_query="((//ul[contains(@class, 'products')])[1]/li)[1]",
        collection_second_query="((//ul[contains(@class, 'products')])[1]/li)[2]",
    ),
    FixtureCase(
        file_name="habr.html",
        unique_query="//*[@id='app']",
        text_query="(//h1[normalize-space()='Моя лента'])[1]",
        collection_first_query="(//article[@data-test-id='articles-list-item'])[1]",
        collection_second_query="(//article[@data-test-id='articles-list-item'])[2]",
    ),
    FixtureCase(
        file_name="ozon.html",
        unique_query="(//input[@name='text' and @placeholder='Искать на Ozon'])[1]",
        text_query="(//a[normalize-space()='Электроника'])[1]",
        collection_first_query=(
            "(//*[@data-widget='tileGridDesktop']"
            "//div[contains(concat(' ', normalize-space(@class), ' '), ' tile-root ')])[1]"
        ),
        collection_second_query=(
            "(//*[@data-widget='tileGridDesktop']"
            "//div[contains(concat(' ', normalize-space(@class), ' '), ' tile-root ')])[2]"
        ),
    ),
    FixtureCase(
        file_name="reddit.html",
        unique_query="//*[@id='main-content']",
        text_query="(//a[starts-with(@id,'post-title-')])[1]",
        collection_first_query="(//article[@data-post-id])[1]",
        collection_second_query="(//article[@data-post-id])[2]",
    ),
    FixtureCase(
        file_name="worldcoinindex.html",
        unique_query="//table[@id='myTable']",
        text_query="(//span[normalize-space()='Market cap:'])[1]",
        collection_first_query="(//table[@id='myTable']//tbody/tr)[1]",
        collection_second_query="(//table[@id='myTable']//tbody/tr)[2]",
    ),
]


def _fixture_html(name: str) -> str:
    path = Path("html_examples") / name
    return path.read_text(encoding="utf-8", errors="ignore")


def _absolute_xpath(html_source: str, query: str) -> str:
    doc = lxml_html.fromstring(html_source)
    nodes = doc.xpath(query)
    assert nodes, f"Target query did not match: {query}"
    return doc.getroottree().getpath(nodes[0])


def _per_type_key(variant):
    return (0 if variant.is_unique else 1, -variant.score, variant.match_count, len(variant.selector))


@pytest.mark.parametrize("case", FIXTURES, ids=[case.file_name for case in FIXTURES])
def test_build_selectors_produces_ranked_variants(case: FixtureCase) -> None:
    html_source = _fixture_html(case.file_name)
    absolute_xpath = _absolute_xpath(html_source, case.unique_query)

    result = build_selectors(html_source, absolute_xpath)

    assert result.target_found is True
    assert result.variants, "expected at least one selector variant"
    assert result.xpath_variants
    assert result.css_variants
    assert result.best_xpath is not None
    assert result.best_css is not None

    assert all(variant.target_matched for variant in result.variants)
    assert any(variant.is_unique for variant in result.variants), "expected at least one unique selector"

    top_scores = [variant.score for variant in result.variants]
    assert top_scores == sorted(top_scores, reverse=True)

    assert result.xpath_variants == sorted(result.xpath_variants, key=_per_type_key)
    assert result.css_variants == sorted(result.css_variants, key=_per_type_key)


@pytest.mark.parametrize("case", FIXTURES, ids=[case.file_name for case in FIXTURES])
def test_build_selectors_accepts_absolute_xpath_from_browser_copy(case: FixtureCase) -> None:
    html_source = _fixture_html(case.file_name)
    absolute_xpath = _absolute_xpath(html_source, case.unique_query)

    # lxml getpath() yields browser-like absolute path from the root.
    assert absolute_xpath.startswith("/html")

    result = build_selectors(html_source, absolute_xpath)

    assert result.target_found is True
    assert result.best_xpath is not None or result.best_css is not None


@pytest.mark.parametrize("case", FIXTURES, ids=[case.file_name for case in FIXTURES])
def test_build_selectors_accepts_non_absolute_xpath_input(case: FixtureCase) -> None:
    html_source = _fixture_html(case.file_name)

    result = build_selectors(html_source, case.unique_query)

    assert result.target_found is True
    assert result.variants


@pytest.mark.parametrize("case", FIXTURES, ids=[case.file_name for case in FIXTURES])
def test_build_selectors_returns_text_based_variants(case: FixtureCase) -> None:
    html_source = _fixture_html(case.file_name)
    absolute_xpath = _absolute_xpath(html_source, case.text_query)

    result = build_selectors(html_source, absolute_xpath)

    assert result.target_found is True
    assert result.variants_with_text, "expected text-based xpath variants"
    assert all(variant.is_text_based for variant in result.variants_with_text)
    assert all(variant.selector_type == "xpath" for variant in result.variants_with_text)


@pytest.mark.parametrize("case", FIXTURES, ids=[case.file_name for case in FIXTURES])
def test_build_collection_selector_for_neighboring_nodes(case: FixtureCase) -> None:
    html_source = _fixture_html(case.file_name)
    first_xpath = _absolute_xpath(html_source, case.collection_first_query)
    second_xpath = _absolute_xpath(html_source, case.collection_second_query)

    result = build_collection_selector(html_source, first_xpath, second_xpath)

    assert result.ok is True
    assert result.collection_xpath is not None
    assert result.collection_css is not None
    assert result.item_xpath_template is not None
    assert result.item_css_template is not None
    assert result.sample_item_xpath is not None
    assert result.sample_item_css is not None
    assert "{i}" in result.item_xpath_template
    assert "{i}" in result.item_css_template
    assert result.estimated_count >= 2


def test_build_selectors_returns_target_not_found_for_wrong_xpath() -> None:
    html_source = _fixture_html("amazon.html")
    result = build_selectors(html_source, "/html/body/does-not-exist")

    assert result.target_found is False
    assert result.variants == []
    assert result.xpath_variants == []
    assert result.css_variants == []
    assert result.variants_with_text == []
    assert result.best_xpath is None
    assert result.best_css is None


def test_all_html_examples_are_covered_by_integration_fixtures() -> None:
    html_files = {path.name for path in Path("html_examples").glob("*.html")}
    fixture_files = {case.file_name for case in FIXTURES}

    assert fixture_files == html_files

