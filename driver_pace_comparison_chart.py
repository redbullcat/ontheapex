import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from race_preprocessing import preprocess_race


# ------------------------------------------------------------
# Cached aggregation helpers (unchanged)
# ------------------------------------------------------------

@st.cache_data(show_spinner=False)
def get_sorted_driver_laps(pre_df: pd.DataFrame, driver: str) -> pd.DataFrame:
    """
    Cached sorted lap table for a single driver.
    """
    return (
        pre_df[pre_df["DRIVER_NAME"] == driver]
        .sort_values("LAP_TIME_SECONDS")
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def compute_driver_percentile_average(
    driver_laps: pd.DataFrame,
    percentile: int,
) -> float:
    """
    Cached percentile aggregation.
    """
    n_laps = len(driver_laps)
    if n_laps == 0:
        return None

    n_keep = max(1, int(n_laps * percentile / 100))
    return driver_laps.head(n_keep)["LAP_TIME_SECONDS"].mean()


# ------------------------------------------------------------
# Main chart
# ------------------------------------------------------------

def show_driver_pace_comparison(df, team_colors):
    st.markdown("## 🏁 Driver Pace Comparison by Top Lap Percentiles")

    # --------------------------------------------------------
    # UI: class + driver selection
    # --------------------------------------------------------

    available_classes = df["CLASS"].dropna().unique().tolist()
    selected_classes = st.multiselect(
        "Select class(es) to compare", available_classes
    )

    if not selected_classes:
        st.info("Please select at least one class.")
        return

    selected_drivers = []
    for race_class in selected_classes:
        class_drivers = (
            df[df["CLASS"] == race_class]["DRIVER_NAME"]
            .dropna()
            .unique()
            .tolist()
        )
        chosen = st.multiselect(
            f"Select drivers from {race_class}",
            class_drivers,
            key=f"drivers_{race_class}",
        )
        selected_drivers.extend(chosen)

    if len(selected_drivers) < 2:
        st.info("Please select at least two drivers to compare.")
        return

    # --------------------------------------------------------
    # UI: percentile selection
    # --------------------------------------------------------

    st.markdown("### Select Lap Percentiles to Display")
    percentile_options = [20, 40, 60, 80, 100]

    cols = st.columns(len(percentile_options))
    selected_percentiles = []
    for idx, p in enumerate(percentile_options):
        checked = cols[idx].checkbox(
            f"Top {p}%", value=(p == 100)
        )
        if checked:
            selected_percentiles.append(p)

    if not selected_percentiles:
        st.warning("Select at least one percentile range to display.")
        return

    # --------------------------------------------------------
    # Shared preprocessing cache (fixed)
    # --------------------------------------------------------

    pre_df = preprocess_race(df)

    # --------------------------------------------------------
    # Aggregation (cached)
    # --------------------------------------------------------

    data = []
    y_values_all = []

    for p in selected_percentiles:
        avg_pace = []
        for driver in selected_drivers:
            driver_laps = get_sorted_driver_laps(pre_df, driver)
            avg_time = compute_driver_percentile_average(
                driver_laps, p
            )
            avg_pace.append(avg_time)
            if avg_time is not None:
                y_values_all.append(avg_time)

        data.append((p, avg_pace))

    if not y_values_all:
        st.warning("No valid lap data available for selected drivers.")
        return

    # --------------------------------------------------------
    # Axis range
    # --------------------------------------------------------

    y_min = min(y_values_all)
    y_max = max(y_values_all)
    padding = (y_max - y_min) * 0.05

    y_range = [
        y_max + padding,
        max(0, y_min - padding),
    ]

    # --------------------------------------------------------
    # Rendering only
    # --------------------------------------------------------

    fig = go.Figure()

    for (p, avg_pace) in data:
        fig.add_trace(
            go.Bar(
                name=f"Top {p}%",
                x=selected_drivers,
                y=avg_pace,
                text=[
                    f"{t:.3f}" if t is not None else "–"
                    for t in avg_pace
                ],
                textposition="auto",
            )
        )

    fig.update_layout(
        barmode="group",
        title="Driver Average Pace by Lap Percentiles",
        xaxis_title="Driver",
        yaxis_title="Average Lap Time (seconds)",
        plot_bgcolor="#2b2b2b",
        paper_bgcolor="#2b2b2b",
        font_color="white",
        legend_title="Percentile Range",
    )

    fig.update_yaxes(autorange=False, range=y_range)

    st.plotly_chart(fig, use_container_width=True)
