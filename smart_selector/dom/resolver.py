from __future__ import annotations

import re

from lxml.etree import _Element


INDEX_PREDICATE_PATTERN = re.compile(r"\[(\d+)\]")


def _first_element(nodes: list[object]) -> _Element | None:
    if not nodes:
        return None
    first = nodes[0]
    return first if hasattr(first, "tag") else None


def _run_xpath(doc: _Element, xpath: str) -> _Element | None:
    try:
        nodes = doc.xpath(xpath)
    except Exception:
        return None
    return _first_element(nodes)


def _clamp_index_predicates(xpath: str) -> str:
    def replace(match: re.Match[str]) -> str:
        index = match.group(1)
        return f"[(position()={index}) or (last()<{index} and position()=last())]"

    return INDEX_PREDICATE_PATTERN.sub(replace, xpath)


def _strip_numeric_indexes(xpath: str) -> str:
    return INDEX_PREDICATE_PATTERN.sub("", xpath)


def _candidate_xpaths(absolute_xpath: str) -> list[str]:
    candidates: list[str] = []

    def add(value: str) -> None:
        if value and value not in candidates:
            candidates.append(value)

    add(absolute_xpath)
    add(_clamp_index_predicates(absolute_xpath))
    add(_strip_numeric_indexes(absolute_xpath))

    segments = [segment for segment in absolute_xpath.split("/") if segment]
    if len(segments) > 2:
        for offset in range(1, len(segments)):
            relative = "//" + "/".join(segments[offset:])
            add(relative)
            add(_clamp_index_predicates(relative))
            add(_strip_numeric_indexes(relative))

    return candidates


def resolve_target(doc: _Element, absolute_xpath: str) -> _Element | None:
    """Resolve target element by absolute XPath with tolerant fallbacks."""
    for candidate_xpath in _candidate_xpaths(absolute_xpath):
        element = _run_xpath(doc, candidate_xpath)
        if element is not None:
            return element
    return None


def resolve_target_strict(doc: _Element, absolute_xpath: str) -> _Element | None:
    """Resolve target element strictly by the provided XPath."""
    return _run_xpath(doc, absolute_xpath)

