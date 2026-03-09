from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Pattern


DEFAULT_STABLE_ATTRIBUTES = (
    "id",
    "data-testid",
    "data-test",
    "data-qa",
    "aria-label",
    "name",
    "role",
    "itemprop",
    "title",
    "href",
    "type",
)


def _compile_patterns(values: tuple[str, ...]) -> tuple[Pattern[str], ...]:
    return tuple(re.compile(value, re.IGNORECASE) for value in values)


@dataclass(slots=True)
class SelectorConfig:
    stable_attributes: tuple[str, ...] = DEFAULT_STABLE_ATTRIBUTES
    max_variants: int = 12
    max_candidates_per_generator: int = 20
    max_class_tokens: int = 3
    max_anchor_depth: int = 4
    text_min_length: int = 8
    text_max_length: int = 120
    include_debug_report: bool = False
    enable_text_fallback: bool = True
    enable_position_fallback: bool = True
    enable_mutation_score: bool = True
    class_noise_patterns: tuple[Pattern[str], ...] = field(
        default_factory=lambda: _compile_patterns(
            (
                r"^(sm|md|lg|xl|2xl):",
                r"^(hover|focus|active|disabled):",
                r"^(css|style|sc)-[a-z0-9_-]{4,}$",
                r"^[a-f0-9]{8,}$",
                r"^v-\w+$",
                r"^nuxt",
            )
        )
    )
    value_noise_patterns: tuple[Pattern[str], ...] = field(
        default_factory=lambda: _compile_patterns(
            (
                r"^\d{6,}$",
                r"^[a-f0-9]{16,}$",
                r"^[0-9a-f]{8}-[0-9a-f-]{20,}$",
                r"^ember\d+$",
                r"^react-",
                r"^css-",
            )
        )
    )

    def is_noisy_value(self, value: str) -> bool:
        if not value:
            return True
        return any(pattern.search(value) for pattern in self.value_noise_patterns)

    def is_noisy_class(self, class_name: str) -> bool:
        if not class_name:
            return True
        return any(pattern.search(class_name) for pattern in self.class_noise_patterns)
