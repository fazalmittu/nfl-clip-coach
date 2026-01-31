"""Column category tree for NFL play-by-play data.

Organizes ~314 columns into categories so the LLM can first pick relevant
categories, then see only the columns it needs.
"""

from dataclasses import dataclass, field


@dataclass
class Category:
    name: str
    description: str
    columns: list[str] = field(default_factory=list)


CATEGORIES: list[Category] = [
    Category(
        name="game_info",
        description="Game metadata: teams, week, season, date, stadium, weather, coaches, surface, roof, betting lines",
        columns=[
            "play_id", "game_id", "home_team", "away_team", "season_type", "week",
            "posteam", "posteam_type", "defteam", "game_date", "season",
            "stadium", "game_stadium", "stadium_id", "weather", "temp", "wind",
            "roof", "surface", "home_coach", "away_coach", "location",
            "div_game", "spread_line", "total_line", "result", "total",
            "nfl_api_id",
        ],
    ),
    Category(
        name="play_situation",
        description="Down, distance, field position, quarter, time, game clock, play clock, game half, score, timeouts",
        columns=[
            "qtr", "down", "ydstogo", "yardline_100", "side_of_field", "yrdln",
            "goal_to_go", "time", "quarter_seconds_remaining",
            "half_seconds_remaining", "game_seconds_remaining", "game_half",
            "quarter_end", "play_clock", "start_time", "time_of_day",
            "end_clock_time",
            "posteam_score", "defteam_score", "score_differential",
            "total_home_score", "total_away_score", "home_score", "away_score",
            "posteam_score_post", "defteam_score_post", "score_differential_post",
            "posteam_timeouts_remaining", "defteam_timeouts_remaining",
            "home_timeouts_remaining", "away_timeouts_remaining",
            "timeout", "timeout_team",
        ],
    ),
    Category(
        name="play_type",
        description="Type of play: pass, rush, punt, kickoff, field goal, extra point, spike, kneel, scramble, play description text",
        columns=[
            "play_type", "play_type_nfl", "desc", "play", "special",
            "special_teams_play", "st_play_type",
            "shotgun", "no_huddle", "qb_dropback", "qb_kneel", "qb_spike",
            "qb_scramble", "aborted_play", "play_deleted",
        ],
    ),
    Category(
        name="passing",
        description="Passing stats: passer, receiver, pass attempt, completion, air yards, YAC, pass length/location, incompletion, passing yards",
        columns=[
            "pass_attempt", "complete_pass", "incomplete_pass", "passing_yards",
            "air_yards", "yards_after_catch", "pass_length", "pass_location",
            "pass", "cp", "cpoe", "qb_epa",
            "passer_player_id", "passer_player_name", "passer", "passer_id",
            "passer_jersey_number",
            "receiver_player_id", "receiver_player_name", "receiver", "receiver_id",
            "receiver_jersey_number",
        ],
    ),
    Category(
        name="rushing",
        description="Rushing stats: rusher, rush attempt, rushing yards, run location, run gap",
        columns=[
            "rush_attempt", "rushing_yards", "run_location", "run_gap",
            "rush",
            "rusher_player_id", "rusher_player_name", "rusher", "rusher_id",
            "rusher_jersey_number",
        ],
    ),
    Category(
        name="scoring",
        description="Scoring events: touchdown, pass TD, rush TD, return TD, extra point, two-point conversion, field goal, safety, TD player",
        columns=[
            "touchdown", "pass_touchdown", "rush_touchdown", "return_touchdown",
            "td_team", "td_player_name", "td_player_id",
            "extra_point_attempt", "extra_point_result", "extra_point_prob",
            "two_point_attempt", "two_point_conv_result", "two_point_conversion_prob",
            "field_goal_attempt", "field_goal_result", "kick_distance",
            "safety", "safety_player_name", "safety_player_id",
            "sp",
            "defensive_two_point_attempt", "defensive_two_point_conv",
            "defensive_extra_point_attempt", "defensive_extra_point_conv",
        ],
    ),
    Category(
        name="yards_and_results",
        description="Yards gained, net yards, first downs, success, series info",
        columns=[
            "yards_gained", "ydsnet", "success", "first_down",
            "first_down_rush", "first_down_pass", "first_down_penalty",
            "third_down_converted", "third_down_failed",
            "fourth_down_converted", "fourth_down_failed",
            "series", "series_success", "series_result",
            "order_sequence",
        ],
    ),
    Category(
        name="turnovers",
        description="Turnovers: interceptions, fumbles, fumble recovery, fumble lost",
        columns=[
            "interception", "interception_player_id", "interception_player_name",
            "fumble", "fumble_forced", "fumble_not_forced", "fumble_out_of_bounds",
            "fumble_lost", "fumbled_1_team", "fumbled_1_player_id",
            "fumbled_1_player_name", "fumbled_2_player_id", "fumbled_2_player_name",
            "fumbled_2_team",
            "fumble_recovery_1_team", "fumble_recovery_1_yards",
            "fumble_recovery_1_player_id", "fumble_recovery_1_player_name",
            "fumble_recovery_2_team", "fumble_recovery_2_yards",
            "fumble_recovery_2_player_id", "fumble_recovery_2_player_name",
            "forced_fumble_player_1_team", "forced_fumble_player_1_player_id",
            "forced_fumble_player_1_player_name",
            "forced_fumble_player_2_team", "forced_fumble_player_2_player_id",
            "forced_fumble_player_2_player_name",
        ],
    ),
    Category(
        name="defense_and_tackles",
        description="Defensive stats: sacks, QB hits, tackles, TFLs, pass defense, tackle assists",
        columns=[
            "sack", "qb_hit", "tackled_for_loss", "solo_tackle", "assist_tackle",
            "tackle_with_assist",
            "sack_player_id", "sack_player_name",
            "half_sack_1_player_id", "half_sack_1_player_name",
            "half_sack_2_player_id", "half_sack_2_player_name",
            "qb_hit_1_player_id", "qb_hit_1_player_name",
            "qb_hit_2_player_id", "qb_hit_2_player_name",
            "tackle_for_loss_1_player_id", "tackle_for_loss_1_player_name",
            "tackle_for_loss_2_player_id", "tackle_for_loss_2_player_name",
            "solo_tackle_1_team", "solo_tackle_1_player_id", "solo_tackle_1_player_name",
            "solo_tackle_2_team", "solo_tackle_2_player_id", "solo_tackle_2_player_name",
            "assist_tackle_1_player_id", "assist_tackle_1_player_name", "assist_tackle_1_team",
            "assist_tackle_2_player_id", "assist_tackle_2_player_name", "assist_tackle_2_team",
            "assist_tackle_3_player_id", "assist_tackle_3_player_name", "assist_tackle_3_team",
            "assist_tackle_4_player_id", "assist_tackle_4_player_name", "assist_tackle_4_team",
            "tackle_with_assist_1_player_id", "tackle_with_assist_1_player_name", "tackle_with_assist_1_team",
            "tackle_with_assist_2_player_id", "tackle_with_assist_2_player_name", "tackle_with_assist_2_team",
            "pass_defense_1_player_id", "pass_defense_1_player_name",
            "pass_defense_2_player_id", "pass_defense_2_player_name",
        ],
    ),
    Category(
        name="penalties",
        description="Penalty info: penalty flag, team, player, yards, type, replay/challenge",
        columns=[
            "penalty", "penalty_team", "penalty_player_id", "penalty_player_name",
            "penalty_yards", "penalty_type",
            "replay_or_challenge", "replay_or_challenge_result",
        ],
    ),
    Category(
        name="kicking_and_punting",
        description="Kicking/punting: punt stats, kickoff stats, touchback, blocked punt, fair catch, returner info",
        columns=[
            "punt_attempt", "kickoff_attempt",
            "punt_blocked", "touchback",
            "punt_inside_twenty", "punt_in_endzone", "punt_out_of_bounds",
            "punt_downed", "punt_fair_catch",
            "kickoff_inside_twenty", "kickoff_in_endzone", "kickoff_out_of_bounds",
            "kickoff_downed", "kickoff_fair_catch",
            "own_kickoff_recovery", "own_kickoff_recovery_td",
            "own_kickoff_recovery_player_id", "own_kickoff_recovery_player_name",
            "punter_player_id", "punter_player_name",
            "kicker_player_name", "kicker_player_id",
            "punt_returner_player_id", "punt_returner_player_name",
            "kickoff_returner_player_name", "kickoff_returner_player_id",
            "blocked_player_id", "blocked_player_name",
        ],
    ),
    Category(
        name="laterals",
        description="Lateral plays: lateral receptions, rushes, returns, recoveries and associated players",
        columns=[
            "lateral_reception", "lateral_rush", "lateral_return", "lateral_recovery",
            "lateral_receiver_player_id", "lateral_receiver_player_name", "lateral_receiving_yards",
            "lateral_rusher_player_id", "lateral_rusher_player_name", "lateral_rushing_yards",
            "lateral_sack_player_id", "lateral_sack_player_name",
            "lateral_interception_player_id", "lateral_interception_player_name",
            "lateral_punt_returner_player_id", "lateral_punt_returner_player_name",
            "lateral_kickoff_returner_player_id", "lateral_kickoff_returner_player_name",
        ],
    ),
    Category(
        name="returns",
        description="Return plays: return team, return yards, return touchdowns",
        columns=[
            "return_team", "return_yards", "return_touchdown",
            "out_of_bounds", "home_opening_kickoff",
        ],
    ),
    Category(
        name="win_probability",
        description="Win probability and EPA: WP, WPA, home WP",
        columns=[
            "wp", "wpa", "home_wp", "home_wp_post",
        ],
    ),
    Category(
        name="drive_info",
        description="Drive-level stats: drive number, play count, time of possession, first downs, yards, start/end info",
        columns=[
            "drive", "fixed_drive", "fixed_drive_result",
            "drive_real_start_time", "drive_play_count",
            "drive_time_of_possession", "drive_first_downs",
            "drive_inside20", "drive_ended_with_score",
            "drive_quarter_start", "drive_quarter_end",
            "drive_yards_penalized", "drive_start_transition", "drive_end_transition",
            "drive_game_clock_start", "drive_game_clock_end",
            "drive_start_yard_line", "drive_end_yard_line",
            "drive_play_id_started", "drive_play_id_ended",
            "end_yard_line",
        ],
    ),
    Category(
        name="fantasy",
        description="Fantasy football: fantasy player name, ID, points",
        columns=[
            "fantasy_player_name", "fantasy_player_id", "fantasy", "fantasy_id",
            "name", "jersey_number", "id",
        ],
    ),
]

CATEGORY_MAP: dict[str, Category] = {c.name: c for c in CATEGORIES}


def get_category_summary() -> str:
    """One-line-per-category summary for the LLM to pick from."""
    lines = []
    for cat in CATEGORIES:
        lines.append(f"- {cat.name}: {cat.description}")
    return "\n".join(lines)


def get_columns_for_categories(names: list[str]) -> list[str]:
    """Return deduplicated column list for the given category names."""
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        cat = CATEGORY_MAP.get(name)
        if cat is None:
            continue
        for col in cat.columns:
            if col not in seen:
                seen.add(col)
                result.append(col)
    return result
