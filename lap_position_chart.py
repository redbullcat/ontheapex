import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from race_preprocessing import preprocess_lap_position_data  # Assuming you added this to race_preprocessing.py


@st.cache_data(show_spinner="Preprocessing lap position data…")
def preprocess_lap_position_data(df):
    """
    Preprocess lap position data for each class:
    - Convert ELAPSED to seconds if needed
    - Prepare position DataFrame per class
    - Prepare car_colors dict per class
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

        # Map colors for cars based on their team (case-insensitive)
        car_colors = {}
        teams = class_df['TEAM'].dropna().unique()
        for team in teams:
            cars_in_team = class_df[class_df["TEAM"].str.lower() == team.lower()]["NUMBER"].unique()
            color = None
            # You might want to customize how colors are assigned if team_colors not provided here
            # For now leave None or set default color here if needed
            for car in cars_in_team:
                car_colors[car] = None  # Will be overridden later by team_colors if given

        result[cls] = (position_df, car_colors, max_lap)

    return result


def show_lap_position_chart(df, team_colors):
    # --- Preprocessing with caching ---
    preprocessed = preprocess_lap_position_data(df)

    available_classes = sorted(preprocessed.keys())
    if not available_classes:
        st.warning("No classes available in data for lap position chart.")
        return

    # Select default class - pick the class with the most laps completed (heuristic for "top class")
    def class_max_lap(cls):
        return preprocessed[cls][2]  # max_lap

    default_class = max(available_classes, key=class_max_lap)

    st.subheader("Lap-by-Lap Position Chart")

    selected_classes = st.multiselect(
        "Select Class for Lap Position Chart",
        available_classes,
        default=[default_class]  # Default to the top class only
    )

    if not selected_classes:
        st.warning("No classes selected for lap position chart.")
        return

    for cls in selected_classes:
        with st.expander(f"Class: {cls}", expanded=True):
            st.markdown(f"### {cls}")

            if cls not in preprocessed:
                st.write(f"No lap position data available for class {cls}.")
                continue

            position_df, car_colors, max_lap = preprocessed[cls]

            # Car selector default to all cars in class
            available_cars = [car for car in position_df.values.flatten() if car is not None]
            available_cars = sorted(available_cars)

            selected_cars = st.multiselect(
                f"Select Cars for {cls}",
                available_cars,
                default=available_cars,
                key=f"cars_{cls}"
            )
            if not selected_cars:
                st.write(f"No cars selected for class {cls}.")
                continue

            # Lap range slider
            lap_range = st.slider(
                f"Select lap range for {cls}",
                min_value=1,
                max_value=int(max_lap),
                value=(1, int(max_lap)),
                step=1,
                key=f"lap_range_{cls}"
            )

            start_lap, end_lap = lap_range

            # Prepare color mapping for selected cars from team_colors
            # Override None with actual colors from team_colors if available
            for car in available_cars:
                if car_colors.get(car) is None:
                    # Find team for this car from original df
                    car_team = df[(df['CLASS'] == cls) & (df['NUMBER'] == car)]['TEAM'].dropna().unique()
                    if car_team.size > 0:
                        team_name = car_team[0].lower()
                        car_colors[car] = team_colors.get(team_name, "#888888")
                    else:
                        car_colors[car] = "#888888"

            fig_lap = go.Figure()

            for car_number in selected_cars:
                positions = []
                laps = []
                for lap in range(start_lap, end_lap + 1):
                    col = f'Lap {lap}'
                    if car_number in position_df[col].values:
                        pos = position_df.index[position_df[col] == car_number][0]
                        positions.append(pos)
                        laps.append(lap)
                    else:
                        positions.append(None)
                        laps.append(lap)

                if not any(p is not None for p in positions):
                    continue

                fig_lap.add_trace(go.Scatter(
                    x=laps,
                    y=positions,
                    mode='lines+markers',
                    name=f"Car {car_number}",
                    line_shape='hv',
                    line=dict(color=car_colors.get(car_number, '#888888'), width=2),
                    connectgaps=False,
                    hovertemplate='Lap %{x}<br>Position %{y}<br>Car %{text}',
                    text=[car_number]*len(laps),
                ))

            fig_lap.update_layout(
                title=f"Lap-by-Lap Position Chart - {cls}",
                xaxis_title="Lap Number",
                yaxis_title="Race Position",
                yaxis_autorange="reversed",
                yaxis=dict(dtick=1),
                plot_bgcolor="#2b2b2b",
                paper_bgcolor="#2b2b2b",
                font=dict(color="white"),
                legend=dict(title="Car Number", yanchor="top", y=0.99, xanchor="left", x=0.01),
                margin=dict(l=60, r=10, t=50, b=50),
                hovermode="x unified",
            )

            st.plotly_chart(fig_lap, use_container_width=True)
