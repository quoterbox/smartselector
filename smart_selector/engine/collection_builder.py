from __future__ import annotations

import re

from ..config import SelectorConfig
from ..dom import build_dom_index, parse_html, resolve_target
from ..generation.base import (
    class_predicate_xpath,
    css_attribute_value,
    meaningful_classes,
    safe_css_identifier,
    stable_attributes_of,
    xpath_literal,
)
from ..models import CollectionSelectorResult


SEGMENT_PATTERN = re.compile(r"^(?P<tag>[^\[]+?)(?:\[(?P<index>\d+)\])?$")


def _segments(xpath: str) -> list[str]:
    return [segment for segment in xpath.strip().split("/") if segment]


def _parse_segment(segment: str) -> tuple[str, int | None]:
    match = SEGMENT_PATTERN.match(segment)
    if not match:
        return segment, None
    tag = match.group("tag")
    index = match.group("index")
    return tag, int(index) if index is not None else None


def _join_xpath(segments: list[str]) -> str:
    return "/" + "/".join(segments)


def _segment_to_css(segment: str, *, template: bool = False) -> str:
    tag, index = _parse_segment(segment)
    if tag == "*":
        tag = "div"

    if template:
        return f"{tag}:nth-of-type({{i}})"
    if index is None:
        return tag
    return f"{tag}:nth-of-type({index})"


def _suffix_tail(after_a: list[str], after_b: list[str]) -> list[str]:
    if after_a == after_b:
        return after_a

    suffix: list[str] = []
    ia = len(after_a) - 1
    ib = len(after_b) - 1
    while ia >= 0 and ib >= 0 and after_a[ia] == after_b[ib]:
        suffix.insert(0, after_a[ia])
        ia -= 1
        ib -= 1
    return suffix


def _anchor_for_ancestor(doc, ancestor_xpath: str, config: SelectorConfig):
    nodes = doc.xpath(ancestor_xpath)
    if not nodes:
        return None, None

    ancestor = nodes[0]
    index = build_dom_index(doc, config)
    tag = ancestor.tag if isinstance(ancestor.tag, str) else "div"

    attrs = stable_attributes_of(ancestor, config)
    if attrs:
        attr_name, attr_value = attrs[0]
        xpath_anchor = f"//{tag}[@{attr_name}={xpath_literal(attr_value)}]"
        if attr_name == "id" and safe_css_identifier(attr_value):
            css_anchor = f"#{attr_value}"
        else:
            css_anchor = f"{tag}[{attr_name}={css_attribute_value(attr_value)}]"
        return xpath_anchor, css_anchor

    classes = meaningful_classes(ancestor, config, index)
    if classes:
        chosen = classes[0]
        xpath_anchor = f"//{tag}[{class_predicate_xpath(chosen)}]"
        css_anchor = f"{tag}.{chosen}" if safe_css_identifier(chosen) else None
        return xpath_anchor, css_anchor

    return None, None


def _best_anchor(doc, prefix: list[str], config: SelectorConfig):
    for depth in range(len(prefix), 0, -1):
        ancestor_xpath = _join_xpath(prefix[:depth])
        xpath_anchor, css_anchor = _anchor_for_ancestor(doc, ancestor_xpath, config)
        if xpath_anchor is not None or css_anchor is not None:
            return depth, xpath_anchor, css_anchor
    return None, None, None


def build_collection_selector(
    html: str,
    first_absolute_xpath: str,
    second_absolute_xpath: str,
    config: SelectorConfig | None = None,
) -> CollectionSelectorResult:
    cfg = config or SelectorConfig()
    doc = parse_html(html)

    first = resolve_target(doc, first_absolute_xpath)
    second = resolve_target(doc, second_absolute_xpath)

    if first is None or second is None:
        return CollectionSelectorResult(
            ok=False,
            reason="one_or_both_targets_not_found",
            first_input_xpath=first_absolute_xpath,
            second_input_xpath=second_absolute_xpath,
            resolved_first_xpath=None,
            resolved_second_xpath=None,
            collection_xpath=None,
            collection_css=None,
            item_xpath_template=None,
            item_css_template=None,
            sample_item_xpath=None,
            sample_item_css=None,
            estimated_count=0,
        )

    tree = doc.getroottree()
    resolved_first_xpath = tree.getpath(first)
    resolved_second_xpath = tree.getpath(second)

    segments_a = _segments(resolved_first_xpath)
    segments_b = _segments(resolved_second_xpath)

    common_len = 0
    for seg_a, seg_b in zip(segments_a, segments_b):
        if seg_a != seg_b:
            break
        common_len += 1

    if common_len >= len(segments_a) or common_len >= len(segments_b):
        return CollectionSelectorResult(
            ok=False,
            reason="targets_are_identical_or_ancestor_related",
            first_input_xpath=first_absolute_xpath,
            second_input_xpath=second_absolute_xpath,
            resolved_first_xpath=resolved_first_xpath,
            resolved_second_xpath=resolved_second_xpath,
            collection_xpath=None,
            collection_css=None,
            item_xpath_template=None,
            item_css_template=None,
            sample_item_xpath=None,
            sample_item_css=None,
            estimated_count=0,
        )

    diverge_a = segments_a[common_len]
    diverge_b = segments_b[common_len]
    diverge_tag_a, _ = _parse_segment(diverge_a)
    diverge_tag_b, _ = _parse_segment(diverge_b)

    if diverge_tag_a != diverge_tag_b:
        return CollectionSelectorResult(
            ok=False,
            reason="targets_do_not_share_sibling_tag",
            first_input_xpath=first_absolute_xpath,
            second_input_xpath=second_absolute_xpath,
            resolved_first_xpath=resolved_first_xpath,
            resolved_second_xpath=resolved_second_xpath,
            collection_xpath=None,
            collection_css=None,
            item_xpath_template=None,
            item_css_template=None,
            sample_item_xpath=None,
            sample_item_css=None,
            estimated_count=0,
        )

    prefix = segments_a[:common_len]
    tail = _suffix_tail(segments_a[common_len + 1 :], segments_b[common_len + 1 :])
    item_tag = diverge_tag_a

    full_collection_segments = [*prefix, item_tag, *tail]
    full_item_segments = [*prefix, f"{item_tag}[{{i}}]", *tail]

    collection_xpath = _join_xpath(full_collection_segments)
    item_xpath_template = _join_xpath(full_item_segments)

    collection_css = " > ".join(_segment_to_css(segment) for segment in full_collection_segments)
    item_css_template = " > ".join(
        [
            *(_segment_to_css(segment) for segment in prefix),
            _segment_to_css(item_tag, template=True),
            *(_segment_to_css(segment) for segment in tail),
        ]
    )

    anchor_depth, anchor_xpath, anchor_css = _best_anchor(doc, prefix, cfg)
    if anchor_depth is not None:
        suffix_after_anchor = full_collection_segments[anchor_depth:]

        if anchor_xpath is not None:
            collection_xpath = anchor_xpath
            if suffix_after_anchor:
                collection_xpath += "/" + "/".join(suffix_after_anchor)

            item_suffix_parts: list[str] = []
            divergence_global_index = len(prefix)
            for idx, segment in enumerate(suffix_after_anchor):
                global_index = anchor_depth + idx
                if global_index == divergence_global_index:
                    item_suffix_parts.append(f"{item_tag}[{{i}}]")
                else:
                    item_suffix_parts.append(segment)

            item_xpath_template = anchor_xpath
            if item_suffix_parts:
                item_xpath_template += "/" + "/".join(item_suffix_parts)

        if anchor_css is not None:
            suffix_css = [_segment_to_css(segment) for segment in suffix_after_anchor]
            item_suffix_css: list[str] = []
            divergence_global_index = len(prefix)
            for idx, segment in enumerate(suffix_after_anchor):
                global_index = anchor_depth + idx
                if global_index == divergence_global_index:
                    item_suffix_css.append(_segment_to_css(item_tag, template=True))
                else:
                    item_suffix_css.append(_segment_to_css(segment))

            collection_css = anchor_css
            if suffix_css:
                collection_css += " > " + " > ".join(suffix_css)

            item_css_template = anchor_css
            if item_suffix_css:
                item_css_template += " > " + " > ".join(item_suffix_css)

    estimated_count = 0
    try:
        estimated_count = len(doc.xpath(collection_xpath)) if collection_xpath else 0
    except Exception:
        estimated_count = 0

    sample_item_xpath = item_xpath_template.replace("{i}", "1") if item_xpath_template else None
    sample_item_css = item_css_template.replace("{i}", "1") if item_css_template else None

    return CollectionSelectorResult(
        ok=True,
        reason=None,
        first_input_xpath=first_absolute_xpath,
        second_input_xpath=second_absolute_xpath,
        resolved_first_xpath=resolved_first_xpath,
        resolved_second_xpath=resolved_second_xpath,
        collection_xpath=collection_xpath,
        collection_css=collection_css,
        item_xpath_template=item_xpath_template,
        item_css_template=item_css_template,
        sample_item_xpath=sample_item_xpath,
        sample_item_css=sample_item_css,
        estimated_count=estimated_count,
    )
