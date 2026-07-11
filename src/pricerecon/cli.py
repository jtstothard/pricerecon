"""CLI entry point."""

import asyncio
from pathlib import Path

import uvicorn

from pricerecon.config import get_settings


def main() -> None:
    """Run the PriceRecon server."""
    settings = get_settings()

    # Ensure we're running from the right directory for imports
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    uvicorn.run(
        "pricerecon.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()