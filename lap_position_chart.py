import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from race_preprocessing import preprocess_race


@st.cache_data(show_spinner="Preprocessing lap positions per class…")
def preprocess_lap_positions(df, team_colors, classes):
    pre_df = preprocess_race(df)

    result = {}

    for cls in classes:
        class_df = pre_df[pre_df["CLASS"] == cls]

        max_lap = class_df["LAP_NUMBER"].max()
        if pd.isna(max_lap) or max_lap < 1:
            # Skip classes with no lap data
            continue

        max_position = class_df[class_df['LAP_NUMBER'].between(1, max_lap)]\
            .groupby("LAP_NUMBER")["NUMBER"].nunique().max()

        lap_positions = {f'Lap {i}': [None] * max_position for i in range(1, int(max_lap) + 1)}

        for lap in range(1, int(max_lap) + 1):
            lap_df = class_df[class_df['LAP_NUMBER'] == lap].sort_values("ELAPSED").reset_index(drop=True)
            unique_cars_in_lap = lap_df["NUMBER"].unique()
            for pos, car_number in enumerate(unique_cars_in_lap, start=1):
                if pos - 1 < max_position:
                    lap_positions[f'Lap {lap}'][pos - 1] = car_number

        position_df = pd.DataFrame(lap_positions)
        position_df.index.name = 'Position'
        position_df.index = position_df.index + 1

        # Map colors for cars based on team
        car_colors = {}
        for team, color in team_colors.items():
            cars_in_team = class_df[class_df["TEAM"].str.lower() == team.lower()]["NUMBER"].unique()
            for car in cars_in_team:
                car_colors[car] = color

        # Default color fallback
        for car in position_df.values.flatten():
            if car and car not in car_colors:
                car_colors[car] = "#888888"

        result[cls] = (position_df, car_colors, int(max_lap))

    return result


def get_top_class_by_max_lap(df):
    max_laps = df.groupby("CLASS")["LAP_NUMBER"].max()
    if max_laps.empty:
        return None
    return max_laps.idxmax()


def show_lap_position_chart(df, team_colors):
    available_classes = sorted(df['CLASS'].dropna().unique())
    if not available_classes:
        st.warning("No classes available in data for lap position chart.")
        return

    top_class = get_top_class_by_max_lap(df)
    default_selection = [top_class] if top_class in available_classes else available_classes

    selected_classes = st.multiselect("Select Class for Lap Position Chart", available_classes, default=default_selection)
    if not selected_classes:
        st.warning("No classes selected for lap position chart.")
        return

    st.subheader("Lap-by-Lap Position Chart")

    # Preprocess once for selected classes
    preprocessed = preprocess_lap_positions(df, team_colors, selected_classes)

    tabs = st.tabs(selected_classes)
    for tab, cls in zip(tabs, selected_classes):
        with tab:
            st.markdown(f"### {cls}")

            if cls not in preprocessed:
                st.write(f"No lap data available for class {cls}.")
                continue

            position_df, car_colors, max_lap = preprocessed[cls]

            # Car selector default to all cars in class
            available_cars = sorted(position_df.values.flatten())
            available_cars = [car for car in available_cars if car is not None]

            selected_cars = st.multiselect(f"Select Cars for {cls}", available_cars, default=available_cars, key=f"cars_{cls}")
            if not selected_cars:
                st.write(f"No cars selected for class {cls}.")
                continue

            lap_range = st.slider(
                f"Select lap range for {cls}",
                min_value=1,
                max_value=max_lap,
                value=(1, max_lap),
                step=1,
                key=f"lap_range_{cls}"
            )
            start_lap, end_lap = lap_range

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

            st.plotly_chart(fig_lap, width='stretch')
