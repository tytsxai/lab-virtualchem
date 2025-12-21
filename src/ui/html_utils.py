from __future__ import annotations

import html


def escape_html(text: object) -> str:
    if text is None:
        return ""
    return html.escape(str(text), quote=True)

