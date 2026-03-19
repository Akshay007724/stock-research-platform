#!/usr/bin/env python3
"""
Standalone database initialisation script.
Run this to create PostgreSQL tables without starting the full application.

Usage:
    cd /path/to/stock-research-platform
    pip install -r backend/requirements.txt
    python scripts/init_db.py
"""
from __future__ import annotations

import asyncio
import os
import sys

# Allow importing from backend/app without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


async def main() -> None:
    from app.database import init_db

    print("Initialising database tables…")
    await init_db()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
