from .index import DomIndex, TargetContext, build_dom_index, build_target_context
from .parser import parse_html
from .resolver import resolve_target

__all__ = [
    "DomIndex",
    "TargetContext",
    "build_dom_index",
    "build_target_context",
    "parse_html",
    "resolve_target",
]
