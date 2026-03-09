from pathlib import Path

from lxml import html as lxml_html

from smart_selector import build_collection_selector, build_selectors


def _absolute_xpath(html_source: str, query: str) -> str:
    doc = lxml_html.fromstring(html_source)
    return doc.getroottree().getpath(doc.xpath(query)[0])


if __name__ == "__main__":
    html = Path("html_examples/amazon.html").read_text(encoding="utf-8", errors="ignore")
    abs_xpath = _absolute_xpath(html, "//*[@id='nav-search-submit-button']")

    result = build_selectors(html, abs_xpath)
    print("Best XPath:", result.best_xpath)
    print("Best CSS  :", result.best_css)

    print("Top-5 mixed variants:")
    for variant in result.variants[:5]:
        print(f"  - [{variant.selector_type}] {variant.selector} (score={variant.score}, unique={variant.is_unique})")

    print("Top-3 XPath variants:")
    for variant in result.xpath_variants[:3]:
        print(f"  - {variant.selector}")

    print("Top-3 CSS variants:")
    for variant in result.css_variants[:3]:
        print(f"  - {variant.selector}")

    print("Top-3 text variants:")
    for variant in result.variants_with_text[:3]:
        print(f"  - {variant.selector}")

    world = Path("html_examples/worldcoinindex.html").read_text(encoding="utf-8", errors="ignore")
    first = _absolute_xpath(world, "(//table[@id='myTable']//tbody/tr)[1]")
    second = _absolute_xpath(world, "(//table[@id='myTable']//tbody/tr)[2]")
    group = build_collection_selector(world, first, second)

    print("Collection XPath:", group.collection_xpath)
    print("Collection CSS  :", group.collection_css)
    print("Template XPath  :", group.item_xpath_template)
    print("Template CSS    :", group.item_css_template)
    print("Estimated count :", group.estimated_count)

