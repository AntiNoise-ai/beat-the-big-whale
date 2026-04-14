from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tube_london_ads.models import FEATURE_NAMES, StationFeatureVector
from tube_london_ads.profiles import BUSINESS_PROFILES
from tube_london_ads.scoring import recommend

VECTORS_PATH = ROOT / "data" / "processed" / "station_feature_vectors_real.json"
FEATURE_TABLE_PATH = ROOT / "data" / "processed" / "station_feature_table_real.csv"
STATION_REFERENCE_PATH = ROOT / "data" / "processed" / "station_reference_with_counts.csv"

DISPLAY_COLUMNS = [
    "station_name",
    "score",
    "borough_name",
    "zone",
    "annualised_total",
    "lines",
    "top_reasons",
    "context_notes",
]

FRIENDLY_FEATURE_NAMES = {
    "resident_density": "Resident density",
    "daytime_workers": "Daytime workers",
    "retail_intensity": "Retail intensity",
    "dining_intensity": "Dining intensity",
    "tourism_intensity": "Tourism intensity",
    "office_intensity": "Office intensity",
    "student_presence": "Student presence",
    "family_presence": "Family presence",
    "affluence": "Affluence proxy",
    "interchange_score": "Interchange score",
    "footfall_proxy": "Footfall proxy",
    "zone_centrality": "Zone centrality",
}


@st.cache_data
def load_vectors() -> list[StationFeatureVector]:
    rows = json.loads(VECTORS_PATH.read_text())
    return [StationFeatureVector(**row) for row in rows]


@st.cache_data
def load_station_frame() -> pd.DataFrame:
    features = pd.read_csv(FEATURE_TABLE_PATH)
    reference = pd.read_csv(
        STATION_REFERENCE_PATH,
        usecols=["station_id", "station_name", "latitude", "longitude", "annualised_total"],
    )
    merged = features.merge(
        reference,
        on=["station_id", "station_name", "annualised_total"],
        how="left",
    )
    merged["annualised_total_m"] = merged["annualised_total"] / 1_000_000
    return merged


@st.cache_data
def load_results(industry: str, top_k: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    station_frame = load_station_frame()
    result = recommend(industry=industry, top_k=top_k, stations=load_vectors())

    station_rows = []
    for rec in result.stations:
        row = station_frame.loc[station_frame["station_name"] == rec.station_name].iloc[0].to_dict()
        row["score"] = rec.score
        row["top_reasons"] = " | ".join(rec.top_reasons)
        row["context_notes"] = " | ".join(rec.context_notes)
        row["feature_breakdown"] = rec.feature_breakdown
        station_rows.append(row)

    stations_df = pd.DataFrame(station_rows)
    line_df = pd.DataFrame(
        [{"line": line, "score": score} for line, score in result.line_scores.items()]
    ).sort_values("score", ascending=False)
    return stations_df, line_df


def build_feature_chart_data(row: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feature": [FRIENDLY_FEATURE_NAMES[name] for name in FEATURE_NAMES],
            "value": [row[name] for name in FEATURE_NAMES],
        }
    ).sort_values("value", ascending=False)


st.set_page_config(page_title="London Tube Advertising Recommender", layout="wide")

st.title("London Tube Advertising Recommender")
st.caption("Public-data-first station ranking for London Underground advertising ideas")

with st.sidebar:
    st.header("Campaign settings")
    industry = st.selectbox("Business profile", BUSINESS_PROFILES, index=BUSINESS_PROFILES.index("luxury_retail"))
    top_k = st.slider("Top stations", min_value=3, max_value=20, value=8)
    st.info("This is a strategy proxy tool, not an ROI predictor.")

stations_df, line_df = load_results(industry, top_k)

best_station = stations_df.iloc[0]
col1, col2, col3 = st.columns(3)
col1.metric("Top station", best_station["station_name"])
col2.metric("Top score", f"{best_station['score']:.2f}")
col3.metric("Top station footfall", f"{best_station['annualised_total_m']:.1f}M annual")

st.subheader("Recommended stations")
map_df = stations_df.rename(columns={"latitude": "lat", "longitude": "lon"})[["lat", "lon", "score", "station_name"]]
st.map(map_df, size="score", zoom=10)

st.dataframe(
    stations_df[DISPLAY_COLUMNS].rename(
        columns={
            "station_name": "Station",
            "score": "Score",
            "borough_name": "Borough",
            "zone": "Zone",
            "annualised_total": "Annual entries/exits",
            "lines": "Lines",
            "top_reasons": "Top reasons",
            "context_notes": "Context",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Best lines among current top stations")
st.bar_chart(line_df.set_index("line"))

station_options = stations_df["station_name"].tolist()
selected_station = st.selectbox("Inspect a station", station_options)
selected_row = stations_df.loc[stations_df["station_name"] == selected_station].iloc[0]

left, right = st.columns([1, 1])
with left:
    st.markdown(f"### {selected_row['station_name']}")
    st.write(f"Score: {selected_row['score']:.2f}")
    st.write(f"Lines: {selected_row['lines']}")
    st.write(f"Zone: {selected_row['zone']}")
    if pd.notna(selected_row.get("borough_name")):
        st.write(f"Borough: {selected_row['borough_name']}")
    st.write(f"Annual entries/exits: {selected_row['annualised_total_m']:.1f}M")
    if selected_row["top_reasons"]:
        st.write("Why it ranks well:")
        for item in str(selected_row["top_reasons"]).split(" | "):
            st.write(f"- {item}")
    if selected_row["context_notes"]:
        st.write("Context:")
        for item in str(selected_row["context_notes"]).split(" | "):
            st.write(f"- {item}")

with right:
    chart_df = build_feature_chart_data(selected_row)
    st.bar_chart(chart_df.set_index("feature"))

st.subheader("How to run locally")
st.code("cd london-tube-advertising && . .venv/bin/activate && streamlit run streamlit_app.py", language="bash")
