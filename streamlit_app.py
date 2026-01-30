import os
import re
import pandas as pd
import streamlit as st
from datetime import datetime

from race_preprocessing import preprocess_race
from pace_chart import show_pace_chart
from lap_position_chart import show_lap_position_chart
from driver_pace_chart import show_driver_pace_chart
from driver_pace_comparison_chart import show_driver_pace_comparison
from team_driver_pace_comparison import show_team_driver_pace_comparison
from results_table import show_results_table
from gap_evolution_chart import show_gap_evolution_chart, show_cumulative_time_chart
from stint_pace_chart import show_stint_pace_chart
from team_season_comparison import show_team_season_comparison
from track_analysis import show_track_analysis
from practice_analysis import show_practice_analysis
from race_stats import show_race_stats
from race_tyre_analysis import show_tyre_analysis

DATA_DIR = "data"

# ------------------------------------------------------------------
# Regex helpers
# ------------------------------------------------------------------
RACE_CSV_RE = re.compile(r"^(.+)\.csv$", re.IGNORECASE)
SESSION_CSV_RE = re.compile(r"^(.+?)_(practice|session)(\d+)\.csv$", re.IGNORECASE)


# ------------------------------------------------------------------
# Cached helpers
# ------------------------------------------------------------------
def get_event_names(series_path):
    events = {}
    for f in os.listdir(series_path):
        if not f.lower().endswith(".csv"):
            continue

        race_match = RACE_CSV_RE.match(f)
        session_match = SESSION_CSV_RE.match(f)

        if session_match:
            base_name = session_match.group(1).lower()
            event = events.setdefault(base_name, {"race_file": None, "sessions": []})
            event["sessions"].append(f)

        elif race_match:
            base_name = race_match.group(1).lower()
            event = events.setdefault(base_name, {"race_file": None, "sessions": []})
            event["race_file"] = f

    return events


@st.cache_data(show_spinner=False)
def load_race_file_index(data_dir):
    race_files = {}

    for year in sorted(os.listdir(data_dir)):
        year_path = os.path.join(data_dir, year)
        if not os.path.isdir(year_path):
            continue

        series_dict = {}

        for series in sorted(os.listdir(year_path)):
            series_path = os.path.join(year_path, series)
            if not os.path.isdir(series_path):
                continue

            events = get_event_names(series_path)
            if events:
                series_dict[series] = events

        if series_dict:
            race_files[year] = series_dict

    return race_files


@st.cache_data(show_spinner="Loading race data…")
def load_race_data(file_path, year, series):
    df = pd.read_csv(file_path, delimiter=";")
    df.columns = df.columns.str.strip()

    if "\ufeffNUMBER" in df.columns:
        df.rename(columns={"\ufeffNUMBER": "NUMBER"}, inplace=True)

    df["YEAR"] = year
    df["SERIES"] = series

    df["NUMBER"] = df["NUMBER"].astype(str).str.strip()
    df["TEAM"] = df["TEAM"].astype(str).str.strip()

    df["CAR_ID"] = (
        df["YEAR"].astype(str) + "_" +
        df["SERIES"].astype(str) + "_" +
        df["TEAM"] + "_" +
        df["NUMBER"]
    )

    return df


@st.cache_data(show_spinner=False)
def parse_race_start_date(filename):
    date_match = re.search(r"_(\d{8})", filename)
    if not date_match:
        return None
    try:
        return datetime.strptime(date_match.group(1), "%Y%m%d").date()
    except ValueError:
        return None


@st.cache_data(show_spinner=False)
def get_class_df(df, race_class):
    return df[df["CLASS"] == race_class]


# ------------------------------------------------------------------
# Load race index (cached)
# ------------------------------------------------------------------
race_files = load_race_file_index(DATA_DIR)

# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
st.sidebar.header("Configuration")

selected_series = st.sidebar.selectbox("Series", ["IMSA", "FIA WEC"])

page = st.sidebar.selectbox(
    "Page",
    [
        "Overview",
        "Team by team",
        "Team season comparison",
        "Track analysis",
        "Practice / Test analysis",
    ],
)

selected_year = st.sidebar.selectbox(
    "Year",
    sorted(race_files.keys(), reverse=True),
)

available_series_for_year = race_files[selected_year].keys()

if selected_series not in available_series_for_year:
    st.error(f"No {selected_series} data available for {selected_year}.")
    st.stop()

events_for_series = race_files[selected_year][selected_series]


def event_display_name(event_key, event_data):
    if event_data["race_file"] is None and event_data["sessions"]:
        return f"{event_key.capitalize()} (Test Sessions)"
    return event_key.capitalize()


event_keys = sorted(events_for_series.keys())
display_names = [event_display_name(k, events_for_series[k]) for k in event_keys]

selected_event_idx = st.sidebar.selectbox(
    "Race",
    range(len(event_keys)),
    format_func=lambda i: display_names[i],
)

selected_event_key = event_keys[selected_event_idx]
selected_event = events_for_series[selected_event_key]

# ------------------------------------------------------------------
# Load race data (NOT for practice-only page)
# ------------------------------------------------------------------
df = None
race_start_date = None

if page != "Practice / Test analysis":
    if selected_event["race_file"] is None:
        st.error(f"No main race CSV found for {selected_event_key}.")
        st.stop()

    file_path = os.path.join(
        DATA_DIR,
        selected_year,
        selected_series,
        selected_event["race_file"],
    )

    df = load_race_data(file_path, selected_year, selected_series)
    df_pre = preprocess_race(df)  # ← NEW (cached, shared)
    race_start_date = parse_race_start_date(selected_event["race_file"])

# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
st.header(f"{selected_year} {selected_series} – {selected_event_key.capitalize()} Analysis")

# ------------------------------------------------------------------
# Team colours
# ------------------------------------------------------------------
team_colors = {
    'Cadillac Hertz Team JOTA': '#d4af37',
    'Peugeot TotalEnergies': '#BBD64D',
    'Ferrari AF Corse': '#d62728',
    'Toyota Gazoo Racing': '#000000',
    'BMW M Team WRT': '#2426a8',
    'Porsche Penske Motorsport': '#ffffff',
    'Alpine Endurance Team': '#2673e2',
    'Aston Martin Thor Team': '#01655c',
    'AF Corse': '#FCE903',
    'Proton Competition': '#fcfcff',
    'WRT': '#2426a8',
    'United Autosports': '#FF8000',
    'Akkodis ASP': '#ff443b',
    'Iron Dames': '#e5017d',
    'Manthey': '#0192cf',
    'Heart of Racing': '#242c3f',
    'Racing Spirit of Leman': '#428ca8',
    'Iron Lynx': '#fefe00',
    'TF Sport': '#eaaa1d',
    'Cadillac Wayne Taylor Racing': '#0E3463',
    'JDC-Miller MotorSports': '#F8D94A',
    'Acura Meyer Shank Racing w/Curb Agajanian': '#E6662C',
    'Cadillac Whelen': '#D53C35',
}

# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------
if page == "Overview":
    if race_start_date is None:
        st.error("Race start date not found or invalid.")
        st.stop()

    overview_tab, tyre_tab = st.tabs(["Overview", "Tyre analysis"])

    with overview_tab:
        show_race_stats(df, race_start_date)
        show_pace_chart(df_pre, team_colors)
        show_driver_pace_chart(df, team_colors)
        show_lap_position_chart(df, team_colors)
        show_driver_pace_comparison(df, team_colors)
        show_results_table(df, team_colors)
        show_gap_evolution_chart(df, team_colors, race_start_date)
        show_cumulative_time_chart(df, team_colors, race_start_date)
        show_stint_pace_chart(df, team_colors)

    with tyre_tab:
        show_tyre_analysis()

elif page == "Team by team":
    race_classes = sorted(df["CLASS"].dropna().unique())
    tabs = st.tabs(race_classes)

    for tab, race_class in zip(tabs, race_classes):
        with tab:
            class_df = get_class_df(df, race_class)
            if not class_df.empty:
                show_team_driver_pace_comparison(class_df, team_colors)

elif page == "Team season comparison":
    show_team_season_comparison(df, team_colors)

elif page == "Track analysis":
    show_track_analysis(df, team_colors)

elif page == "Practice / Test analysis":
    show_practice_analysis(
        data_dir=DATA_DIR,
        year=selected_year,
        series=selected_series,
        race=selected_event_key,
        team_colors=team_colors,
    )

# ------------------------------------------------------------------
# Debug
# ------------------------------------------------------------------
if df is not None:
    with st.expander("Debug: Car IDs"):
        debug_df = (
            df[["CAR_ID", "NUMBER", "TEAM", "CLASS"]]
            .drop_duplicates()
            .sort_values(["CLASS", "TEAM", "NUMBER"])
            .reset_index(drop=True)
        )

        st.dataframe(debug_df, use_container_width=True, hide_index=True)
