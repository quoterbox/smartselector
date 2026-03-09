from __future__ import annotations

from typing import Iterable

from lxml.cssselect import CSSSelector
from lxml.etree import _Element

from ..dom.index import TargetContext
from ..models import Candidate, EvaluationResult


def _element_nodes(nodes: Iterable[object]) -> list[_Element]:
    output: list[_Element] = []
    for node in nodes:
        if hasattr(node, "tag"):
            output.append(node)  # type: ignore[arg-type]
    return output


class SelectorEvaluator:
    def evaluate(self, candidate: Candidate, context: TargetContext) -> EvaluationResult:
        try:
            if candidate.selector_type == "xpath":
                raw_nodes = context.doc.xpath(candidate.selector)
            else:
                raw_nodes = CSSSelector(candidate.selector)(context.doc)

            nodes = _element_nodes(raw_nodes)
            match_count = len(nodes)
            target_matched = any(
                node.getroottree().getpath(node) == context.target_path for node in nodes
            )
            return EvaluationResult(match_count=match_count, target_matched=target_matched)
        except Exception as exc:
            return EvaluationResult(match_count=0, target_matched=False, error=str(exc))
