from __future__ import annotations

from itertools import combinations

from ..config import SelectorConfig
from ..dom.index import DomIndex, TargetContext
from ..models import Candidate
from .base import (
    CandidateGenerator,
    css_attribute_value,
    dynamic_token_count,
    limit_candidates,
    meaningful_classes,
    node_tag,
    position_among_same_tag,
    safe_css_identifier,
    stable_attributes_of,
)


def _attribute_css(name: str, value: str) -> str:
    return f"[{name}={css_attribute_value(value)}]"


def _ancestor_anchor_css(ancestor, index: DomIndex, config: SelectorConfig) -> tuple[str | None, int]:
    for attr_name, attr_value in stable_attributes_of(ancestor, config):
        if attr_name == "id" and safe_css_identifier(attr_value):
            return f"#{attr_value}", 1
        return f"{node_tag(ancestor)}{_attribute_css(attr_name, attr_value)}", 1

    classes = [
        token for token in meaningful_classes(ancestor, config, index) if safe_css_identifier(token)
    ]
    if classes:
        return node_tag(ancestor) + f".{classes[0]}", 0

    return None, 0


class CssStableAttributeGenerator(CandidateGenerator):
    name = "CssStableAttribute"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        target = context.target
        tag = context.target_tag
        candidates: list[Candidate] = []

        for attr_name, attr_value in stable_attributes_of(target, config):
            if attr_name == "id" and safe_css_identifier(attr_value):
                selector = f"#{attr_value}"
            else:
                selector = f"{tag}{_attribute_css(attr_name, attr_value)}"

            candidates.append(
                Candidate(
                    selector=selector,
                    selector_type="css",
                    strategy=self.name,
                    explain=f"stable attribute {attr_name}",
                    features={
                        "stable_attr_count": 1,
                        "uses_id": attr_name == "id",
                        "uses_data_attr": attr_name.startswith("data-"),
                        "selector_depth": 1,
                        "dynamic_tokens": dynamic_token_count(attr_value, config),
                    },
                )
            )

        return limit_candidates(candidates, config.max_candidates_per_generator)


class CssAttributeComboGenerator(CandidateGenerator):
    name = "CssAttributeCombo"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        attrs = stable_attributes_of(context.target, config)
        if len(attrs) < 2:
            return []

        tag = context.target_tag
        candidates: list[Candidate] = []
        for size in (2, 3):
            for combo in combinations(attrs, size):
                suffix = "".join(_attribute_css(name, value) for name, value in combo)
                selector = f"{tag}{suffix}"
                candidates.append(
                    Candidate(
                        selector=selector,
                        selector_type="css",
                        strategy=self.name,
                        explain=f"combination of {size} stable attributes",
                        features={
                            "stable_attr_count": size,
                            "uses_id": any(name == "id" for name, _ in combo),
                            "uses_data_attr": any(name.startswith("data-") for name, _ in combo),
                            "selector_depth": 1,
                            "dynamic_tokens": sum(dynamic_token_count(value, config) for _, value in combo),
                        },
                    )
                )

        return limit_candidates(candidates, config.max_candidates_per_generator)


class CssClassChainGenerator(CandidateGenerator):
    name = "CssClassChain"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        classes = [token for token in meaningful_classes(context.target, config, index) if safe_css_identifier(token)]
        if not classes:
            return []

        selected = classes[: config.max_class_tokens]
        selector = context.target_tag + "".join(f".{token}" for token in selected)
        return [
            Candidate(
                selector=selector,
                selector_type="css",
                strategy=self.name,
                explain=f"meaningful class chain ({len(selected)})",
                features={
                    "class_tokens": len(selected),
                    "selector_depth": 1,
                    "dynamic_tokens": 0,
                },
            )
        ]


class CssAncestorAnchorGenerator(CandidateGenerator):
    name = "CssAncestorAnchor"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        target = context.target
        target_tag = node_tag(target)

        target_part: str | None = None
        target_attrs = stable_attributes_of(target, config)
        if target_attrs:
            first_attr, first_value = target_attrs[0]
            target_part = f"{target_tag}{_attribute_css(first_attr, first_value)}"

        if target_part is None:
            target_classes = [
                token
                for token in meaningful_classes(target, config, index)
                if safe_css_identifier(token)
            ]
            if target_classes:
                target_part = target_tag + "".join(
                    f".{token}" for token in target_classes[:1]
                )

        if target_part is None:
            target_part = target_tag

        candidates: list[Candidate] = []
        for depth, ancestor in enumerate(context.ancestors[1 : config.max_anchor_depth + 1], start=1):
            anchor_part, stable_attr_count = _ancestor_anchor_css(ancestor, index, config)
            if anchor_part is None:
                continue

            selector = f"{anchor_part} {target_part}"
            candidates.append(
                Candidate(
                    selector=selector,
                    selector_type="css",
                    strategy=self.name,
                    explain=f"anchored at ancestor depth {depth}",
                    features={
                        "uses_ancestor_anchor": True,
                        "ancestor_depth": depth,
                        "stable_attr_count": max(stable_attr_count, int(bool(target_attrs))),
                        "selector_depth": 1 + depth,
                        "dynamic_tokens": 0,
                    },
                )
            )

        return limit_candidates(candidates, config.max_candidates_per_generator)


class CssAnchoredPathGenerator(CandidateGenerator):
    name = "CssAnchoredPath"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        candidates: list[Candidate] = []

        for depth, ancestor in enumerate(context.ancestors[1 : config.max_anchor_depth + 1], start=1):
            anchor_part, stable_attr_count = _ancestor_anchor_css(ancestor, index, config)
            if anchor_part is None:
                continue

            chain: list = []
            current = context.target
            while current is not None and current is not ancestor:
                chain.append(current)
                current = current.getparent()

            if current is not ancestor:
                continue

            chain.reverse()
            if not chain or len(chain) > 6:
                continue

            trail = [f"{node_tag(node)}:nth-of-type({position_among_same_tag(node)})" for node in chain]
            selector = anchor_part + " > " + " > ".join(trail)

            candidates.append(
                Candidate(
                    selector=selector,
                    selector_type="css",
                    strategy=self.name,
                    explain=f"anchored local path depth {depth}",
                    features={
                        "uses_position": True,
                        "uses_ancestor_anchor": True,
                        "ancestor_depth": depth,
                        "stable_attr_count": stable_attr_count,
                        "selector_depth": len(trail) + 1,
                        "dynamic_tokens": 0,
                    },
                )
            )

        return limit_candidates(candidates, config.max_candidates_per_generator)


class CssPositionFallbackGenerator(CandidateGenerator):
    name = "CssPositionFallback"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        if not config.enable_position_fallback:
            return []

        parent = context.target.getparent()
        if parent is None:
            return []

        parent_anchor, stable_attr_count = _ancestor_anchor_css(parent, index, config)
        if parent_anchor is None:
            return []

        position = position_among_same_tag(context.target)
        selector = f"{parent_anchor} > {node_tag(context.target)}:nth-of-type({position})"
        return [
            Candidate(
                selector=selector,
                selector_type="css",
                strategy=self.name,
                explain=f"position fallback in parent ({position})",
                features={
                    "uses_position": True,
                    "uses_ancestor_anchor": True,
                    "ancestor_depth": 1,
                    "stable_attr_count": stable_attr_count,
                    "selector_depth": 2,
                    "dynamic_tokens": 0,
                },
            )
        ]


class CssStructureFallbackGenerator(CandidateGenerator):
    name = "CssStructureFallback"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        segments: list[str] = []
        for node in reversed(context.ancestors):
            tag = node_tag(node)
            if tag == "*":
                continue

            parent = node.getparent()
            if parent is None or tag in {"html", "body"}:
                segments.append(tag)
                continue

            position = position_among_same_tag(node)
            segments.append(f"{tag}:nth-of-type({position})")

        if not segments:
            return []

        selector = " > ".join(segments)
        return [
            Candidate(
                selector=selector,
                selector_type="css",
                strategy=self.name,
                explain="structural css fallback",
                features={
                    "uses_absolute": True,
                    "uses_position": True,
                    "selector_depth": len(segments),
                    "dynamic_tokens": 0,
                },
            )
        ]


def build_css_generators() -> list[CandidateGenerator]:
    return [
        CssStableAttributeGenerator(),
        CssAttributeComboGenerator(),
        CssClassChainGenerator(),
        CssAncestorAnchorGenerator(),
        CssAnchoredPathGenerator(),
        CssPositionFallbackGenerator(),
        CssStructureFallbackGenerator(),
    ]
