from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Iterable

from lxml.etree import _Element

from ..config import SelectorConfig
from ..dom.index import DomIndex, TargetContext, normalize_whitespace
from ..models import Candidate


UTILITY_CLASS_PREFIXES = (
    "sm:",
    "md:",
    "lg:",
    "xl:",
    "2xl:",
    "hover:",
    "focus:",
    "active:",
    "disabled:",
    "p-",
    "pt-",
    "pr-",
    "pb-",
    "pl-",
    "px-",
    "py-",
    "m-",
    "mt-",
    "mr-",
    "mb-",
    "ml-",
    "mx-",
    "my-",
    "w-",
    "h-",
    "min-",
    "max-",
    "text-",
    "bg-",
    "font-",
)

SAFE_CSS_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


class CandidateGenerator(ABC):
    name: str

    @abstractmethod
    def generate(
        self,
        context: TargetContext,
        index: DomIndex,
        config: SelectorConfig,
    ) -> list[Candidate]:
        raise NotImplementedError


def node_tag(node: _Element) -> str:
    return node.tag if isinstance(node.tag, str) else "*"


def split_classes(node: _Element) -> list[str]:
    value = node.get("class")
    if not value:
        return []
    return [token for token in value.split() if token]


def is_meaningful_class(class_name: str, config: SelectorConfig) -> bool:
    if not class_name:
        return False
    if class_name.startswith(UTILITY_CLASS_PREFIXES):
        return False
    return not config.is_noisy_class(class_name)


def meaningful_classes(node: _Element, config: SelectorConfig, index: DomIndex) -> list[str]:
    tokens = [token for token in split_classes(node) if is_meaningful_class(token, config)]
    return sorted(tokens, key=lambda token: (index.class_frequency(token), len(token)))


def safe_css_identifier(token: str) -> bool:
    return bool(SAFE_CSS_IDENTIFIER.match(token))


def xpath_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    chunks = value.split("'")
    quoted_chunks = [f"'{chunk}'" for chunk in chunks]
    return "concat(" + ", \"'\", ".join(quoted_chunks) + ")"


def css_attribute_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def class_predicate_xpath(class_name: str) -> str:
    return (
        "contains(concat(' ', normalize-space(@class), ' '),"
        f" ' {class_name} ')"
    )


def stable_attributes_of(
    node: _Element,
    config: SelectorConfig,
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for attr_name in config.stable_attributes:
        value = normalize_whitespace(node.get(attr_name))
        if not value:
            continue
        if config.is_noisy_value(value):
            continue
        pairs.append((attr_name, value))
    return pairs


def dynamic_token_count(value: str, config: SelectorConfig) -> int:
    return int(config.is_noisy_value(value))


def position_among_same_tag(node: _Element) -> int:
    parent = node.getparent()
    if parent is None:
        return 1

    tag = node_tag(node)
    position = 0
    for child in parent:
        if node_tag(child) == tag:
            position += 1
        if child is node:
            return position
    return 1


def limit_candidates(candidates: Iterable[Candidate], limit: int) -> list[Candidate]:
    output: list[Candidate] = []
    for candidate in candidates:
        output.append(candidate)
        if len(output) >= limit:
            break
    return output
