"""
Clean raw play-by-play CSV: keep only the 49ers vs Lions NFC Championship game
and drop unnecessary columns.
Output: niners_lions_play_by_play_2023.csv
"""
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
RAW_CSV = DATA_DIR / "raw_play_by_play_2023.csv"
OUTPUT_CSV = DATA_DIR / "niners_lions_play_by_play_2023.csv"

GAME_ID = "2023_21_DET_SF"

COLUMNS_TO_REMOVE = [
    # Definitely Redundant
    "old_game_id",
    "def_wp",
    "away_wp",
    "away_wp_post",
    # Vegas/Betting metrics
    "vegas_wpa",
    "vegas_home_wpa",
    "vegas_wp",
    "vegas_home_wp",
    # EPA metrics
    "ep",
    "epa",
    "air_epa",
    "yac_epa",
    "comp_air_epa",
    "comp_yac_epa",
    # Total/Cumulative EPA stats
    "total_home_epa",
    "total_away_epa",
    "total_home_rush_epa",
    "total_away_rush_epa",
    "total_home_pass_epa",
    "total_away_pass_epa",
    "total_home_comp_air_epa",
    "total_away_comp_air_epa",
    "total_home_comp_yac_epa",
    "total_away_comp_yac_epa",
    "total_home_raw_air_epa",
    "total_away_raw_air_epa",
    "total_home_raw_yac_epa",
    "total_away_raw_yac_epa",
    # Total/Cumulative WPA stats
    "total_home_rush_wpa",
    "total_away_rush_wpa",
    "total_home_pass_wpa",
    "total_away_pass_wpa",
    "total_home_comp_air_wpa",
    "total_away_comp_air_wpa",
    "total_home_comp_yac_wpa",
    "total_away_comp_yac_wpa",
    "total_home_raw_air_wpa",
    "total_away_raw_air_wpa",
    "total_home_raw_yac_wpa",
    "total_away_raw_yac_wpa",
    # Probability distributions
    "no_score_prob",
    "opp_fg_prob",
    "opp_safety_prob",
    "opp_td_prob",
    "fg_prob",
    "safety_prob",
    "td_prob",
    # WPA components
    "air_wpa",
    "yac_wpa",
    "comp_air_wpa",
    "comp_yac_wpa",
    # Expected YAC metrics
    "xyac_epa",
    "xyac_mean_yardage",
    "xyac_median_yardage",
    "xyac_success",
    "xyac_fd",
    # Advanced probability metrics
    "xpass",
    "pass_oe",
]


def main():
    df = pd.read_csv(RAW_CSV)
    original_rows = len(df)

    df = df[df["game_id"] == GAME_ID]
    filtered_rows = len(df)

    cols_present = [c for c in COLUMNS_TO_REMOVE if c in df.columns]
    cols_missing = [c for c in COLUMNS_TO_REMOVE if c not in df.columns]
    if cols_missing:
        print(f"Columns not in CSV (skipped): {cols_missing}")

    df = df.drop(columns=cols_present, errors="ignore")

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Read {original_rows} rows, kept {filtered_rows} rows for {GAME_ID}")
    print(f"Removed {len(cols_present)} columns, wrote {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
