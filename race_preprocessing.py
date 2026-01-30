import streamlit as st
import pandas as pd

@st.cache_data(show_spinner="Preprocessing race data…")
def preprocess_race(df):
    """
    Minimal, shared preprocessing:
    - Convert LAP_TIME to seconds
    - Drop invalid laps
    - Return a clean dataframe for reuse
    """

    df = df.copy()

    def lap_to_seconds(x):
        try:
            mins, secs = x.split(":")
            return int(mins) * 60 + float(secs)
        except Exception:
            return None

    df["LAP_TIME_SECONDS"] = df["LAP_TIME"].apply(lap_to_seconds)
    df = df.dropna(subset=["LAP_TIME_SECONDS"])

    return df


@st.cache_data(show_spinner="Preprocessing lap position data…")
def preprocess_lap_position_data(df):
    """
    Preprocess lap position data for each class:
    - Prepare position DataFrame per class
    - Prepare car_colors dict per class (empty placeholder, colors assigned later)
    - Calculate max lap per class
    Returns dict keyed by class: (position_df, car_colors, max_lap)
    """

    result = {}

    available_classes = df['CLASS'].dropna().unique()

    for cls in available_classes:
        class_df = df[df['CLASS'] == cls]

        max_lap = class_df["LAP_NUMBER"].max()
        if pd.isna(max_lap) or max_lap < 1:
            continue

        lap_positions = {f'Lap {i}': [None] * class_df['NUMBER'].nunique() for i in range(1, int(max_lap) + 1)}

        for lap in range(1, int(max_lap) + 1):
            lap_df = class_df[class_df['LAP_NUMBER'] == lap].sort_values("ELAPSED").reset_index(drop=True)
            unique_cars_in_lap = lap_df["NUMBER"].unique()
            for pos, car_number in enumerate(unique_cars_in_lap, start=1):
                if pos - 1 < len(lap_positions[f'Lap {lap}']):
                    lap_positions[f'Lap {lap}'][pos - 1] = car_number

        position_df = pd.DataFrame(lap_positions)
        position_df.index.name = 'Position'
        position_df.index = position_df.index + 1

        # Placeholder empty car_colors dict - will assign actual colors later
        car_colors = {}

        result[cls] = (position_df, car_colors, max_lap)

    return result
