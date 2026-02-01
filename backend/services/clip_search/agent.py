"""NL-to-filters agent: two-step LLM process using Claude."""

from __future__ import annotations

import json
import os

import logging

import anthropic

logger = logging.getLogger(__name__)

from services.data import get_category_summary, get_columns_for_categories, CATEGORIES
from .filter import (
    FilterCondition,
    FilterGroup,
    PlayQuery,
    SequenceStep,
    RankFilter,
    DriveFilter,
    DrivePlayPosition,
)

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


# ── Step 2: parse query into PlayQuery ──────────────────────────────────────

def parse_query(query: str) -> PlayQuery:
    """Convert a natural-language query into a structured PlayQuery."""
    categories = select_categories(query)
    columns = get_columns_for_categories(categories)

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are converting a natural-language NFL query into a structured JSON object "
                    "for filtering a pandas DataFrame of play-by-play data.\n\n"
                    "Available columns:\n" + ", ".join(columns) + "\n\n"
                    "Return a JSON object with this top-level schema (no other text):\n"
                    "{\n"
                    '  "type": "filter" | "sequence" | "drive",\n'
                    '  // include the relevant fields for the chosen type (see below)\n'
                    '  "rank": { ... } // optional pre-filter\n'
                    "}\n\n"
                    '## Type "filter" — single play matching\n'
                    "Use for queries about individual plays.\n"
                    '{"type": "filter", "filters": {"logic": "and", "conditions": [...]}}\n\n'
                    '## Type "sequence" — play A followed by play B\n'
                    "Use when the query describes a play followed by another event (in same drive or next drive).\n"
                    '{"type": "sequence",\n'
                    ' "anchor": {"logic": "and", "conditions": [...]},\n'
                    ' "then": [{"scope": "same_drive"|"next_play"|"next_drive", '
                    '"filters": {"logic": "and", "conditions": [...]}}]}\n\n'
                    "Scope values:\n"
                    '- "next_play": exactly the next play in the drive\n'
                    '- "same_drive": any later play in the same drive\n'
                    '- "next_drive": any play in the immediately following drive\n\n'
                    '## Type "drive" — entire drives matching criteria\n'
                    "Use for queries about drives (e.g. drives with no penalties, drives ending in FG).\n"
                    '{"type": "drive", "drive_filter": {\n'
                    '  "include": {"logic": "and", "conditions": [...]},  // at least one play matches\n'
                    '  "include_min_count": 1,  // default 1; set higher for "3+ first downs"\n'
                    '  "exclude": {"logic": "and", "conditions": [...]}   // NO play in drive matches\n'
                    '  "play_at": {"position": 1, "filters": {...}}  // Nth play of drive must match (1-indexed)\n'
                    "}}\n"
                    "play_at examples: drive started with a rush → position=1, play_type=run. "
                    "Second play was a pass → position=2, play_type=pass.\n\n"
                    '## Optional "rank" — limit results by ordering\n'
                    '{"rank": {"group_by": [...], "rank_column": "...", '
                    '"rank_order": "asc"|"desc", "rank": 1, "top_n": null}}\n\n'
                    'IMPORTANT — "rank" vs "top_n":\n'
                    '- "rank" (int): return ONLY the Nth item. "first touchdown" → rank=1. "second sack" → rank=2.\n'
                    '- "top_n" (int or null): return the first N items. "first 2 touchdowns" → top_n=2. "top 5 longest plays" → top_n=5.\n'
                    "  When top_n is set, rank is ignored.\n"
                    '- If the user says "first/last N <things>", ALWAYS use top_n=N, NOT rank=N.\n'
                    "Examples:\n"
                    "- Longest drive → rank_column=drive_time_of_possession, rank_order=desc, rank=1\n"
                    "- First drive of each quarter → group_by=[drive_quarter_start], rank_column=drive, rank_order=asc\n"
                    "- First sack of the game → use type=filter with rank on play_id asc, rank=1\n"
                    "- First 2 touchdowns → use type=filter with rank on play_id asc, top_n=2\n"
                    "- Last 3 plays → rank on play_id desc, top_n=3\n\n"
                    "Condition operators: eq, neq, gt, lt, gte, lte, contains, not_contains, isin\n\n"
                    "Key conventions:\n"
                    "- Binary columns (touchdown, sack, fumble, etc.) use eq 1 or eq 0\n"
                    "- Player names are like 'P.Mahomes', 'T.Kelce' (first initial dot last name)\n"
                    "- Team abbreviations: KC, BUF, SF, PHI, DAL, DET, etc.\n"
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
    logger.info(f"LLM output: {raw}")
    return _parse_play_query(raw)


def _parse_filter_group(data: dict) -> FilterGroup:
    """Recursively parse a raw dict into FilterGroup/FilterCondition."""
    conditions = []
    for item in data["conditions"]:
        if "conditions" in item:
            conditions.append(_parse_filter_group(item))
        else:
            conditions.append(FilterCondition(**item))
    return FilterGroup(logic=data["logic"], conditions=conditions)


def _parse_play_query(data: dict) -> PlayQuery:
    """Parse raw LLM JSON into a PlayQuery."""
    q = PlayQuery(type=data["type"])

    if data.get("filters"):
        q.filters = _parse_filter_group(data["filters"])

    if data.get("anchor"):
        q.anchor = _parse_filter_group(data["anchor"])

    if data.get("then"):
        q.then = [
            SequenceStep(
                scope=s["scope"],
                filters=_parse_filter_group(s["filters"]),
            )
            for s in data["then"]
        ]

    if data.get("drive_filter"):
        df_raw = data["drive_filter"]
        q.drive_filter = DriveFilter(
            include=_parse_filter_group(df_raw["include"]) if df_raw.get("include") else None,
            include_min_count=df_raw.get("include_min_count", 1),
            exclude=_parse_filter_group(df_raw["exclude"]) if df_raw.get("exclude") else None,
            play_at=DrivePlayPosition(
                position=df_raw["play_at"]["position"],
                filters=_parse_filter_group(df_raw["play_at"]["filters"]),
            ) if df_raw.get("play_at") else None,
        )

    if data.get("rank"):
        q.rank = RankFilter(**data["rank"])

    return q
