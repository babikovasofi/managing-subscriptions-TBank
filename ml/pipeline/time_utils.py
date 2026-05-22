"""
Time utilities for the subscription pipeline.

Rule: all pipeline code uses get_simulation_today() — never datetime.now()
or date.today() — so the entire system operates relative to the fixed
simulation date stored in data/output/meta.json.

Public API:
  get_simulation_today() -> datetime  (cached after first read)
  days_between(d1, d2)   -> int
"""

import json
from datetime import date, datetime
from functools import lru_cache

from data.generator.config import META_OUTPUT_PATH


@lru_cache(maxsize=1)
def get_simulation_today() -> datetime:
    """
    Return the fixed simulation date from meta.json.

    Cached: meta.json is read exactly once per process.
    """
    with open(META_OUTPUT_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    return datetime.strptime(meta["simulation_today"], "%Y-%m-%d")


def days_between(d1: date | datetime, d2: date | datetime) -> int:
    """
    Return the signed number of days from d1 to d2 (d2 - d1).

    Accepts both date and datetime objects.
    """
    def _to_date(d: date | datetime) -> date:
        return d.date() if isinstance(d, datetime) else d

    return (_to_date(d2) - _to_date(d1)).days
