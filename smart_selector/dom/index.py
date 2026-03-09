from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from lxml.etree import _Element

from ..config import SelectorConfig


def normalize_whitespace(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split())


@dataclass(slots=True)
class TargetContext:
    doc: _Element
    target: _Element
    target_path: str
    absolute_xpath: str
    ancestors: list[_Element]
    target_tag: str
    target_text: str


@dataclass(slots=True)
class DomIndex:
    class_counts: dict[str, int]
    attribute_counts: dict[tuple[str, str], int]
    text_counts: dict[str, int]
    tag_counts: dict[str, int]

    def class_frequency(self, class_name: str) -> int:
        return self.class_counts.get(class_name, 0)

    def attribute_frequency(self, name: str, value: str) -> int:
        return self.attribute_counts.get((name, value), 0)

    def text_frequency(self, text: str) -> int:
        return self.text_counts.get(text, 0)


def _iter_ancestors(target: _Element) -> Iterable[_Element]:
    current: _Element | None = target
    while current is not None:
        yield current
        current = current.getparent()


def _safe_tag(node: _Element) -> str:
    return node.tag if isinstance(node.tag, str) else "*"


def build_target_context(doc: _Element, target: _Element, absolute_xpath: str) -> TargetContext:
    tree = doc.getroottree()
    path = tree.getpath(target)
    return TargetContext(
        doc=doc,
        target=target,
        target_path=path,
        absolute_xpath=absolute_xpath,
        ancestors=list(_iter_ancestors(target)),
        target_tag=_safe_tag(target),
        target_text=normalize_whitespace("".join(target.itertext())),
    )


def build_dom_index(doc: _Element, config: SelectorConfig) -> DomIndex:
    class_counts: dict[str, int] = {}
    attribute_counts: dict[tuple[str, str], int] = {}
    text_counts: dict[str, int] = {}
    tag_counts: dict[str, int] = {}

    tracked_attributes = set(config.stable_attributes)
    tracked_attributes.update({"class", "href", "src", "alt"})

    for node in doc.iter():
        if not isinstance(node.tag, str):
            continue

        tag_counts[node.tag] = tag_counts.get(node.tag, 0) + 1

        for attr_name, attr_value in node.attrib.items():
            if attr_name not in tracked_attributes:
                continue
            normalized = normalize_whitespace(attr_value)
            if not normalized or len(normalized) > 180:
                continue
            key = (attr_name, normalized)
            attribute_counts[key] = attribute_counts.get(key, 0) + 1

            if attr_name == "class":
                for class_name in normalized.split():
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1

        # Keep indexing lightweight: only direct text content, no full subtree scan.
        text_value = normalize_whitespace(node.text)
        if config.text_min_length <= len(text_value) <= config.text_max_length:
            text_counts[text_value] = text_counts.get(text_value, 0) + 1

    return DomIndex(
        class_counts=class_counts,
        attribute_counts=attribute_counts,
        text_counts=text_counts,
        tag_counts=tag_counts,
    )
