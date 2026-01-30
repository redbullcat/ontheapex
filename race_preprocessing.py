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
