import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta

# =========================
# Helper: parse HOUR with rollover per car
# =========================

def parse_hour_with_date_and_rollover(df: pd.DataFrame, race_start_date: datetime.date) -> pd.Series:
    """
    Converts 'HOUR' column (formatted hh:mm:ss.sss or hh:mm:ss) into absolute datetimes
    with rollover handling per car (grouped by 'NUMBER').
    """
    def parse_time(val):
        for fmt in ("%H:%M:%S.%f", "%H:%M:%S"):
            try:
                return datetime.strptime(val, fmt).time()
            except Exception:
                continue
        return None

    hour_dt = pd.Series(index=df.index, dtype="datetime64[ns]")

    for car_id, car_df in df.sort_values("LAP_NUMBER").groupby("NUMBER"):
        current_date = race_start_date
        last_time = None

        for idx, row in car_df.iterrows():
            t = parse_time(row["HOUR"])
            if t is None:
                hour_dt.loc[idx] = pd.NaT
                continue

            # If current lap time is less than previous, day rollover
            if last_time and t < last_time:
                current_date += timedelta(days=1)

            last_time = t
            hour_dt.loc[idx] = datetime.combine(current_date, t)

    return hour_dt


# =========================
# Helper: convert LAP_TIME string to seconds float
# =========================

def time_to_seconds(time_str):
    try:
        parts = str(time_str).split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        else:
            return float(time_str)
    except:
        return None


# =========================
# Main chart function
# =========================

def show_gap_evolution_chart(df, team_colors, race_start_date):
    st.header("📉 Gap Evolution Chart")

    required_cols = {'CLASS', 'NUMBER', 'LAP_TIME', 'LAP_NUMBER', 'TEAM', 'ELAPSED', 'HOUR'}
    if not required_cols.issubset(df.columns):
        st.warning(f"Required columns missing: {required_cols - set(df.columns)}")
        return

    df = df.copy()

    # Parse HOUR into absolute datetime per car with rollover
    df['HOUR_DT'] = parse_hour_with_date_and_rollover(df, race_start_date)

    # Parse ELAPSED into timedelta for sanity (optional)
    df['ELAPSED_TD'] = pd.to_timedelta(df['ELAPSED'], errors='coerce')

    # Convert LAP_TIME to seconds
    df['LAP_TIME_SEC'] = df['LAP_TIME'].apply(time_to_seconds)

    # Select race class
    selected_class = st.selectbox("Select class:", sorted(df['CLASS'].dropna().unique()))

    class_df = df[df['CLASS'] == selected_class].copy()

    car_numbers = sorted(class_df['NUMBER'].dropna().unique())
    selected_cars = st.multiselect(
        "Select cars to compare:",
        options=car_numbers,
        default=car_numbers[:3] if len(car_numbers) >= 3 else car_numbers
    )

    if not selected_cars:
        st.info("Please select at least one car to display.")
        return

    selected_df = class_df[class_df['NUMBER'].isin(selected_cars)].copy()

    selected_df['LAP_NUMBER'] = pd.to_numeric(selected_df['LAP_NUMBER'], errors='coerce')
    selected_df = selected_df.dropna(subset=['HOUR_DT', 'LAP_NUMBER'])
    selected_df['LAP_NUMBER'] = selected_df['LAP_NUMBER'].astype(int)

    min_lap = int(selected_df['LAP_NUMBER'].min())
    max_lap = int(selected_df['LAP_NUMBER'].max())

    lap_range = st.slider(
        "Select lap range to display",
        min_value=min_lap,
        max_value=max_lap,
        value=(min_lap, max_lap)
    )

    selected_df = selected_df[
        (selected_df['LAP_NUMBER'] >= lap_range[0]) &
        (selected_df['LAP_NUMBER'] <= lap_range[1])
    ]

    if selected_df.empty:
        st.info("No data available for selected filters.")
        return

    race_start_dt = datetime.combine(race_start_date, datetime.min.time())

    # Compute cumulative time in seconds from race start datetime
    selected_df['CUM_TIME_SEC'] = (selected_df['HOUR_DT'] - race_start_dt).dt.total_seconds()

    # Determine fastest finisher by minimum final cumulative time
    final_times = selected_df.groupby('NUMBER')['CUM_TIME_SEC'].max()
    fastest_car = final_times.idxmin()

    # Reference cumulative times of fastest car by lap
    ref_df = selected_df[selected_df['NUMBER'] == fastest_car][['LAP_NUMBER', 'CUM_TIME_SEC']].rename(
        columns={'CUM_TIME_SEC': 'FASTEST_CUM_TIME'}
    )

    # Merge to calculate gap to fastest per lap (seconds)
    merged = selected_df.merge(ref_df, on='LAP_NUMBER', how='left')
    merged['GAP_TO_FASTEST'] = merged['CUM_TIME_SEC'] - merged['FASTEST_CUM_TIME']

    # Build Plotly figure
    fig = go.Figure()

    for car in selected_cars:
        car_data = merged[merged['NUMBER'] == car]
        if car_data.empty:
            continue

        team_name = car_data['TEAM'].iloc[0] if 'TEAM' in car_data.columns else ''
        color = team_colors.get(team_name, "#AAAAAA")

        fig.add_trace(go.Scatter(
            x=car_data['LAP_NUMBER'],
            y=car_data['GAP_TO_FASTEST'],
            mode='lines+markers',
            name=f"{car} – {team_name}",
            line=dict(width=2, color=color),
            marker=dict(size=4)
        ))

    fig.update_layout(
        title=f"Gap Evolution – {selected_class}",
        xaxis_title="Lap Number",
        yaxis_title="Gap to Fastest (seconds)",
        plot_bgcolor="#2b2b2b",
        paper_bgcolor="#2b2b2b",
        font=dict(color="white"),
        xaxis=dict(color='white', gridcolor="#444"),
        yaxis=dict(color='white', gridcolor="#444"),
        legend=dict(bgcolor='rgba(0,0,0,0)')
    )

    st.plotly_chart(fig, use_container_width=True)
