"""NL-to-filters agent: two-step LLM process using Claude."""

from __future__ import annotations

import json
import os

import anthropic

from .columns import get_category_summary, get_columns_for_categories, CATEGORIES
from .filter import FilterCondition, FilterGroup

client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var
MODEL = "claude-sonnet-4-20250514"


# ── Step 1: select relevant categories ──────────────────────────────────────

def select_categories(query: str) -> list[str]:
    """Ask Claude which column categories are relevant to the user's query."""
    category_summary = get_category_summary()
    all_names = [c.name for c in CATEGORIES]

    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are helping filter NFL play-by-play data. "
                    "Given the user's query, return a JSON list of category names "
                    "that contain columns relevant to answering it. "
                    "Return ONLY a JSON array of strings, nothing else.\n\n"
                    f"Available categories:\n{category_summary}\n\n"
                    f"User query: {query}"
                ),
            }
        ],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    names = json.loads(text)
    # Validate
    return [n for n in names if n in {c.name for c in CATEGORIES}]


# ── Step 2: parse query into filters ────────────────────────────────────────

def parse_query(query: str) -> FilterGroup:
    """Convert a natural-language query into a structured FilterGroup."""
    categories = select_categories(query)
    columns = get_columns_for_categories(categories)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are converting a natural-language NFL query into structured filters "
                    "for a pandas DataFrame of play-by-play data.\n\n"
                    "Available columns:\n" + ", ".join(columns) + "\n\n"
                    "Return a JSON object with this schema (no other text):\n"
                    "{\n"
                    '  "logic": "and" | "or",\n'
                    '  "conditions": [\n'
                    '    {"column": str, "operator": str, "value": ...},\n'
                    "    // or nested {\"logic\": ..., \"conditions\": [...]}\n"
                    "  ]\n"
                    "}\n\n"
                    "Operators: eq, neq, gt, lt, gte, lte, contains, not_contains, isin\n\n"
                    "Key conventions:\n"
                    "- Binary columns (touchdown, sack, fumble, etc.) use eq 1 or eq 0\n"
                    "- Player names are like 'P.Mahomes', 'T.Kelce' (first initial dot last name)\n"
                    "- Team abbreviations: KC, BUF, SF, PHI, DAL, etc.\n"
                    "- qtr is 1-5 (5 = OT)\n"
                    "- play_type values: pass, run, punt, kickoff, field_goal, no_play, qb_kneel, qb_spike\n"
                    "- For text search on 'desc' column, use 'contains' with a keyword\n\n"
                    f"Query: {query}"
                ),
            }
        ],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    raw = json.loads(text)
    return _parse_filter_group(raw)


def _parse_filter_group(data: dict) -> FilterGroup:
    """Recursively parse a raw dict into FilterGroup/FilterCondition."""
    conditions = []
    for item in data["conditions"]:
        if "conditions" in item:
            conditions.append(_parse_filter_group(item))
        else:
            conditions.append(FilterCondition(**item))
    return FilterGroup(logic=data["logic"], conditions=conditions)
