from __future__ import annotations

from lxml import html
from lxml.etree import _Element


def parse_html(source: str) -> _Element:
    """Parse HTML source into an lxml document."""
    return html.fromstring(source)
