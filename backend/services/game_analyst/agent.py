"""Conversational NFL game analyst agent."""

from __future__ import annotations

import re
import logging

import anthropic

from services.data import load_data, get_category_summary
from .executor import execute_query

logger = logging.getLogger(__name__)

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"


def _build_game_summary() -> str:
    """Build a concise statistical summary of the loaded game from the DataFrame."""
    try:
        df = load_data()

        home = df["home_team"].dropna().iloc[0] if "home_team" in df.columns else "?"
        away = df["away_team"].dropna().iloc[0] if "away_team" in df.columns else "?"
        date = df["game_date"].dropna().iloc[0] if "game_date" in df.columns else "?"

        home_score = int(df["total_home_score"].dropna().max()) if "total_home_score" in df.columns else "?"
        away_score = int(df["total_away_score"].dropna().max()) if "total_away_score" in df.columns else "?"

        parts = [
            f"Game: {away} @ {home} on {date}",
            f"Final Score: {home} {home_score}, {away} {away_score}",
        ]

        # Key passers
        if "passer_player_name" in df.columns:
            passers = df["passer_player_name"].dropna().unique().tolist()
            parts.append(f"Passers: {', '.join(passers)}")

        # Key rushers
        if "rusher_player_name" in df.columns:
            rushers = df["rusher_player_name"].dropna().unique().tolist()
            parts.append(f"Rushers: {', '.join(rushers)}")

        # Key receivers
        if "receiver_player_name" in df.columns:
            receivers = df["receiver_player_name"].dropna().unique().tolist()
            parts.append(f"Receivers: {', '.join(receivers)}")

        # Touchdowns with detail
        if "touchdown" in df.columns:
            tds = df[df["touchdown"] == 1]
            td_count = len(tds)
            parts.append(f"Total TDs: {td_count}")
            if "td_player_name" in tds.columns:
                td_players = tds["td_player_name"].dropna().unique().tolist()
                if td_players:
                    parts.append(f"TD scorers: {', '.join(td_players)}")
            # Per-team TD breakdown
            if "posteam" in tds.columns:
                for team in tds["posteam"].dropna().unique():
                    team_tds = tds[tds["posteam"] == team]
                    scorers = team_tds["td_player_name"].dropna().tolist() if "td_player_name" in team_tds.columns else []
                    parts.append(f"  {team} TDs ({len(team_tds)}): {', '.join(scorers) if scorers else 'N/A'}")

        # Passing stats per passer
        if "passer_player_name" in df.columns and "passing_yards" in df.columns:
            pass_plays = df[df["pass_attempt"] == 1] if "pass_attempt" in df.columns else df[df["passer_player_name"].notna()]
            for passer in pass_plays["passer_player_name"].dropna().unique():
                p = pass_plays[pass_plays["passer_player_name"] == passer]
                completions = int(p["complete_pass"].sum()) if "complete_pass" in p.columns else "?"
                attempts = len(p)
                yards = int(p["passing_yards"].sum())
                p_tds = int(p["pass_touchdown"].sum()) if "pass_touchdown" in p.columns else 0
                p_ints = int(p["interception"].sum()) if "interception" in p.columns else 0
                parts.append(f"  {passer}: {completions}/{attempts}, {yards} yds, {p_tds} TD, {p_ints} INT")

        # Rushing stats per rusher (top rushers)
        if "rusher_player_name" in df.columns and "rushing_yards" in df.columns:
            rush_plays = df[df["rush_attempt"] == 1] if "rush_attempt" in df.columns else df[df["rusher_player_name"].notna()]
            for rusher in rush_plays["rusher_player_name"].dropna().unique():
                r = rush_plays[rush_plays["rusher_player_name"] == rusher]
                carries = len(r)
                if carries < 2:
                    continue
                yards = int(r["rushing_yards"].sum())
                r_tds = int(r["rush_touchdown"].sum()) if "rush_touchdown" in r.columns else 0
                parts.append(f"  {rusher}: {carries} carries, {yards} yds, {r_tds} TD")

        # Turnovers
        if "interception" in df.columns:
            ints_total = int(df["interception"].sum())
            parts.append(f"Interceptions: {ints_total}")
        if "fumble_lost" in df.columns:
            fumbles = int(df["fumble_lost"].sum())
            parts.append(f"Fumbles lost: {fumbles}")

        # Quarters
        if "qtr" in df.columns:
            quarters = sorted(df["qtr"].dropna().unique().tolist())
            parts.append(f"Quarters played: {', '.join(str(int(q)) for q in quarters)}")

        # Key columns the LLM should use (exact names)
        key_cols = [
            "qtr", "down", "ydstogo", "yardline_100", "time", "desc", "play_type",
            "yards_gained", "passing_yards", "rushing_yards", "air_yards", "yards_after_catch",
            "passer_player_name", "receiver_player_name", "rusher_player_name",
            "posteam", "defteam", "posteam_score", "defteam_score",
            "touchdown", "pass_touchdown", "rush_touchdown", "td_player_name",
            "interception", "fumble", "fumble_lost", "sack",
            "pass_attempt", "complete_pass", "rush_attempt",
            "first_down", "third_down_converted", "fourth_down_converted",
            "field_goal_attempt", "field_goal_result", "kick_distance",
            "penalty", "penalty_team", "penalty_type", "penalty_yards",
            "wpa", "wp", "drive", "fixed_drive", "fixed_drive_result",
            "home_team", "away_team", "total_home_score", "total_away_score",
            "shotgun", "no_huddle", "qb_dropback",
        ]
        parts.append(f"\nKey column names (use these exact names): {', '.join(key_cols)}")

        # Sample row so LLM sees data format
        sample = df[df["play_type"].isin(["pass", "run"])].head(1)
        if not sample.empty:
            row = sample.iloc[0]
            parts.append(
                f"\nSample play row: qtr={row.get('qtr')}, time={row.get('time')}, "
                f"down={row.get('down')}, ydstogo={row.get('ydstogo')}, "
                f"play_type={row.get('play_type')}, yards_gained={row.get('yards_gained')}, "
                f"posteam={row.get('posteam')}, passer_player_name={row.get('passer_player_name')}, "
                f"rusher_player_name={row.get('rusher_player_name')}, "
                f"desc={str(row.get('desc'))[:120]}"
            )

        return "\n".join(parts)
    except Exception as e:
        logger.warning("Failed to build game summary: %s", e)
        return "(Game summary unavailable)"


# Cache it once on first import
_game_summary: str | None = None


def _get_game_summary() -> str:
    global _game_summary
    if _game_summary is None:
        _game_summary = _build_game_summary()
    return _game_summary


SYSTEM_PROMPT = """\
You are an expert NFL coach and game analyst embedded in a video clip coaching app. \
You have access to play-by-play data for NFL games loaded in a pandas DataFrame called `df`.

You are part of an app that can show video clips of plays. When the user asks to \
"show me" plays, find plays, or asks about specific plays (e.g. "show me Purdy's touchdowns"), \
you should answer with the play details from the data. The app will separately offer to \
show the actual video clips—your job is to provide the analysis and play information. \
NEVER say you can't show clips or video. Just answer the question about the plays.

Here is a summary of the current game data you have access to:
{game_summary}

When the user asks a question that requires specific data lookups or statistics, \
write Python/pandas code to answer it. Put the code in a ```python code block. \
The code MUST assign its final answer to a variable called `result`.

Available column categories:
{categories}

Important notes:
- Player names in the data use first initial + last name format (e.g. "B.Purdy", "J.Goff", "C.McCaffrey")
- When filtering by player name, use .str.contains() for flexibility
- The "desc" column contains the full play-by-play text description of each play
- The "passer_player_name" column is the passer, "rusher_player_name" is the rusher, "receiver_player_name" is the receiver
- For touchdowns, check the "touchdown" column (1 = TD) and "td_player_name" for who scored

When you don't need data analysis (e.g. general football questions), just \
answer directly without code. You know the game details from the summary above—use \
that knowledge to give direct, informed answers when possible.

Keep responses concise and conversational. Do NOT include raw code or data in your \
final answer to the user—always summarize findings in natural language. \
NEVER say you cannot show video or clips—the app handles that.
"""

GAME_CONTEXT_PROMPT = """\
The user has selected this game in the app: "{game_context}". \
ALL questions are about this specific game. The data you have is ONLY from this game. \
Every stat, every play, every answer refers to this game. \
NEVER hedge or say "this could refer to a different game/season/timeframe". \
NEVER ask for clarification about which game. Just answer directly and confidently \
about this game.
"""


# In-memory session store: session_id -> list of message dicts
_sessions: dict[str, list[dict]] = {}


def _get_session(session_id: str) -> list[dict]:
    if session_id not in _sessions:
        _sessions[session_id] = []
    return _sessions[session_id]


def chat(session_id: str, message: str, game_context: str | None = None) -> str:
    """Process a chat message and return the assistant's response."""
    history = _get_session(session_id)
    history.append({"role": "user", "content": message})

    system = SYSTEM_PROMPT.format(
        categories=get_category_summary(),
        game_summary=_get_game_summary(),
    )
    if game_context:
        system = system + "\n\n" + GAME_CONTEXT_PROMPT.format(game_context=game_context)

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=history,
    )

    assistant_text = response.content[0].text

    # Check for python code block
    code_match = re.search(r"```python\n(.*?)```", assistant_text, re.DOTALL)
    if code_match:
        code = code_match.group(1).strip()
        df = load_data()
        query_result = execute_query(code, df)

        # If code execution errored, try to answer without code
        if query_result.startswith("Error executing code:"):
            logger.warning("Code execution failed: %s", query_result)
            # Retry without code - ask Claude to just answer from the game summary
            retry_response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=(
                    "You are an NFL analyst. The data query failed. Answer the user's "
                    "question as best you can using this game context:\n\n"
                    f"{_get_game_summary()}"
                ),
                messages=[
                    {"role": "user", "content": message},
                ],
            )
            final_answer = retry_response.content[0].text
            history.append({"role": "assistant", "content": final_answer})
            return final_answer

        # Ask Claude to summarize the result
        game_ctx = game_context or "the selected game"
        summary_response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=(
                f"You are an NFL analyst. The data is from one specific game: {game_ctx}. "
                "Summarize the data result concisely for the user. "
                "Use natural language, not code or raw data. Be direct and confident. "
                "NEVER hedge about which game or timeframe—all data is from this one game. "
                "Do NOT offer to look up more info or ask if the user wants details."
            ),
            messages=[
                {"role": "user", "content": f"Question: {message}\n\nData result:\n{query_result}"},
            ],
        )
        final_answer = summary_response.content[0].text
        history.append({"role": "assistant", "content": final_answer})
        return final_answer

    history.append({"role": "assistant", "content": assistant_text})
    return assistant_text
