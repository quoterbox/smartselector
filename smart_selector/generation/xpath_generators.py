from __future__ import annotations

from itertools import combinations

from ..config import SelectorConfig
from ..dom.index import DomIndex, TargetContext, normalize_whitespace
from ..models import Candidate
from .base import (
    CandidateGenerator,
    class_predicate_xpath,
    dynamic_token_count,
    limit_candidates,
    meaningful_classes,
    node_tag,
    position_among_same_tag,
    stable_attributes_of,
    xpath_literal,
)


def _trim_text(value: str, max_len: int = 48) -> str:
    text = normalize_whitespace(value)
    return text[:max_len].strip()


class XPathStableAttributeGenerator(CandidateGenerator):
    name = "XPathStableAttribute"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        target = context.target
        target_tag = context.target_tag

        candidates: list[Candidate] = []
        for attr_name, attr_value in stable_attributes_of(target, config):
            selector = f"//{target_tag}[@{attr_name}={xpath_literal(attr_value)}]"
            candidates.append(
                Candidate(
                    selector=selector,
                    selector_type="xpath",
                    strategy=self.name,
                    explain=f"stable attribute @{attr_name}",
                    features={
                        "stable_attr_count": 1,
                        "uses_id": attr_name == "id",
                        "uses_data_attr": attr_name.startswith("data-"),
                        "selector_depth": 2,
                        "dynamic_tokens": dynamic_token_count(attr_value, config),
                    },
                )
            )

        return limit_candidates(candidates, config.max_candidates_per_generator)


class XPathAttributeComboGenerator(CandidateGenerator):
    name = "XPathAttributeCombo"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        attrs = stable_attributes_of(context.target, config)
        if len(attrs) < 2:
            return []

        candidates: list[Candidate] = []
        target_tag = context.target_tag
        for size in (2, 3):
            for combo in combinations(attrs, size):
                predicate = " and ".join(
                    f"@{name}={xpath_literal(value)}" for name, value in combo
                )
                selector = f"//{target_tag}[{predicate}]"
                candidates.append(
                    Candidate(
                        selector=selector,
                        selector_type="xpath",
                        strategy=self.name,
                        explain=f"combination of {size} stable attributes",
                        features={
                            "stable_attr_count": size,
                            "uses_data_attr": any(name.startswith("data-") for name, _ in combo),
                            "uses_id": any(name == "id" for name, _ in combo),
                            "selector_depth": 2,
                            "dynamic_tokens": sum(dynamic_token_count(value, config) for _, value in combo),
                        },
                    )
                )

        return limit_candidates(candidates, config.max_candidates_per_generator)


class XPathAncestorAnchorGenerator(CandidateGenerator):
    name = "XPathAncestorAnchor"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        target = context.target
        target_tag = context.target_tag
        target_attrs = stable_attributes_of(target, config)
        target_classes = meaningful_classes(target, config, index)[: config.max_class_tokens]
        target_predicates: list[str] = [
            f"@{attr_name}={xpath_literal(attr_value)}" for attr_name, attr_value in target_attrs[:1]
        ]
        target_predicates.extend(class_predicate_xpath(class_name) for class_name in target_classes[:1])

        candidates: list[Candidate] = []
        for depth, ancestor in enumerate(context.ancestors[1 : config.max_anchor_depth + 1], start=1):
            ancestor_tag = node_tag(ancestor)
            anchor_predicates: list[str] = []

            for attr_name, attr_value in stable_attributes_of(ancestor, config):
                anchor_predicates.append(f"@{attr_name}={xpath_literal(attr_value)}")
                break

            if not anchor_predicates:
                ancestor_classes = meaningful_classes(ancestor, config, index)
                if ancestor_classes:
                    anchor_predicates.append(class_predicate_xpath(ancestor_classes[0]))

            if not anchor_predicates:
                continue

            anchor_expr = f"//{ancestor_tag}[{' and '.join(anchor_predicates)}]"
            if target_predicates:
                selector = f"{anchor_expr}//{target_tag}[{' and '.join(target_predicates)}]"
            else:
                selector = f"{anchor_expr}//{target_tag}"

            candidates.append(
                Candidate(
                    selector=selector,
                    selector_type="xpath",
                    strategy=self.name,
                    explain=f"anchored at ancestor depth {depth}",
                    features={
                        "stable_attr_count": int(bool(target_attrs)),
                        "uses_ancestor_anchor": True,
                        "ancestor_depth": depth,
                        "class_tokens": len(target_classes[:1]),
                        "selector_depth": 3 + depth,
                        "dynamic_tokens": 0,
                    },
                )
            )

        return limit_candidates(candidates, config.max_candidates_per_generator)


class XPathClassChainGenerator(CandidateGenerator):
    name = "XPathClassChain"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        classes = meaningful_classes(context.target, config, index)
        if not classes:
            return []

        picked = classes[: config.max_class_tokens]
        predicates = " and ".join(class_predicate_xpath(token) for token in picked)
        selector = f"//{context.target_tag}[{predicates}]"

        return [
            Candidate(
                selector=selector,
                selector_type="xpath",
                strategy=self.name,
                explain=f"meaningful class chain ({len(picked)})",
                features={
                    "stable_attr_count": 0,
                    "class_tokens": len(picked),
                    "selector_depth": 2,
                    "dynamic_tokens": 0,
                },
            )
        ]


class XPathTextFallbackGenerator(CandidateGenerator):
    name = "XPathTextFallback"

    def _target_text_candidates(self, context: TargetContext, config: SelectorConfig) -> list[Candidate]:
        text = normalize_whitespace(context.target_text)
        if len(text) < config.text_min_length or len(text) > config.text_max_length:
            return []

        exact_selector = f"//{context.target_tag}[normalize-space(string())={xpath_literal(text)}]"
        candidates = [
            Candidate(
                selector=exact_selector,
                selector_type="xpath",
                strategy=self.name,
                explain="exact visible text on target",
                features={
                    "uses_text": True,
                    "text_scope": "target",
                    "selector_depth": 2,
                    "dynamic_tokens": 0,
                },
            )
        ]

        prefix = _trim_text(text)
        if len(prefix) >= config.text_min_length:
            partial_selector = (
                f"//{context.target_tag}[contains(normalize-space(string()), {xpath_literal(prefix)})]"
            )
            candidates.append(
                Candidate(
                    selector=partial_selector,
                    selector_type="xpath",
                    strategy=self.name,
                    explain="partial visible text on target",
                    features={
                        "uses_text": True,
                        "text_scope": "target",
                        "selector_depth": 2,
                        "dynamic_tokens": 0,
                    },
                )
            )

        return candidates

    def _parent_text_candidates(self, context: TargetContext, config: SelectorConfig) -> list[Candidate]:
        candidates: list[Candidate] = []
        for depth, ancestor in enumerate(context.ancestors[1 : config.max_anchor_depth + 1], start=1):
            parent_text = normalize_whitespace("".join(ancestor.itertext()))
            if len(parent_text) < config.text_min_length or len(parent_text) > config.text_max_length:
                continue

            fragment = _trim_text(parent_text)
            if len(fragment) < config.text_min_length:
                continue

            ancestor_tag = node_tag(ancestor)
            selector = (
                f"//{ancestor_tag}[contains(normalize-space(string()), {xpath_literal(fragment)})]"
                f"//{context.target_tag}"
            )
            candidates.append(
                Candidate(
                    selector=selector,
                    selector_type="xpath",
                    strategy=self.name,
                    explain=f"text on ancestor depth {depth}",
                    features={
                        "uses_text": True,
                        "text_scope": "ancestor",
                        "ancestor_depth": depth,
                        "uses_ancestor_anchor": True,
                        "selector_depth": 3 + depth,
                        "dynamic_tokens": 0,
                    },
                )
            )

            if len(candidates) >= 2:
                break

        return candidates

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        if not config.enable_text_fallback:
            return []

        output = [
            *self._target_text_candidates(context, config),
            *self._parent_text_candidates(context, config),
        ]
        return limit_candidates(output, config.max_candidates_per_generator)


class XPathPositionFallbackGenerator(CandidateGenerator):
    name = "XPathPositionFallback"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        if not config.enable_position_fallback:
            return []

        parent = context.target.getparent()
        if parent is None:
            return []

        target_tag = context.target_tag
        position = position_among_same_tag(context.target)

        anchor = None
        parent_tag = node_tag(parent)
        for attr_name, attr_value in stable_attributes_of(parent, config):
            anchor = f"//{parent_tag}[@{attr_name}={xpath_literal(attr_value)}]"
            break

        if anchor is None:
            parent_classes = meaningful_classes(parent, config, index)
            if parent_classes:
                anchor = f"//{parent_tag}[{class_predicate_xpath(parent_classes[0])}]"

        if anchor is None:
            return []

        selector = f"{anchor}/{target_tag}[{position}]"
        return [
            Candidate(
                selector=selector,
                selector_type="xpath",
                strategy=self.name,
                explain=f"position fallback in parent ({position})",
                features={
                    "uses_position": True,
                    "uses_ancestor_anchor": True,
                    "ancestor_depth": 1,
                    "selector_depth": 4,
                    "dynamic_tokens": 0,
                },
            )
        ]


class XPathAbsoluteFallbackGenerator(CandidateGenerator):
    name = "XPathAbsoluteFallback"

    def generate(self, context: TargetContext, index: DomIndex, config: SelectorConfig) -> list[Candidate]:
        selector = context.absolute_xpath
        depth = max(1, selector.count("/"))
        return [
            Candidate(
                selector=selector,
                selector_type="xpath",
                strategy=self.name,
                explain="absolute xpath fallback",
                features={
                    "uses_absolute": True,
                    "uses_position": True,
                    "selector_depth": depth,
                    "dynamic_tokens": 0,
                },
            )
        ]


def build_xpath_generators() -> list[CandidateGenerator]:
    return [
        XPathStableAttributeGenerator(),
        XPathAttributeComboGenerator(),
        XPathAncestorAnchorGenerator(),
        XPathClassChainGenerator(),
        XPathTextFallbackGenerator(),
        XPathPositionFallbackGenerator(),
        XPathAbsoluteFallbackGenerator(),
    ]
