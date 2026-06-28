from __future__ import annotations

import os


async def get_headers() -> dict[str, str]:
    """Return HTTP headers used to authenticate requests to Context7."""

    api_key = os.getenv("CONTEXT7_API_KEY")
    if not api_key:
        raise RuntimeError(
            "CONTEXT7_API_KEY environment variable is not configured."
        )

    return {
        "Authorization": f"Bearer {api_key}",
    }