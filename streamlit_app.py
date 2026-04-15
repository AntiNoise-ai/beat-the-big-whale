from __future__ import annotations

import base64
import io
import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import plotly.graph_objects as go
import pydeck as pdk
import pypdfium2 as pdfium
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
CACHE_DIR = ROOT / ".cache"
TFL_STANDARD_TUBE_MAP_URL = "https://content.tfl.gov.uk/standard-tube-map.pdf"

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

LINE_API_IDS = {
    "Bakerloo": "bakerloo",
    "Central": "central",
    "Circle": "circle",
    "District": "district",
    "Hammersmith & City": "hammersmith-city",
    "Jubilee": "jubilee",
    "Metropolitan": "metropolitan",
    "Northern": "northern",
    "Piccadilly": "piccadilly",
    "Victoria": "victoria",
    "Waterloo & City": "waterloo-city",
}

LINE_COLORS = {
    "Bakerloo": [137, 78, 36],
    "Central": [220, 36, 31],
    "Circle": [255, 205, 0],
    "District": [0, 121, 52],
    "Hammersmith & City": [236, 155, 173],
    "Jubilee": [161, 165, 167],
    "Metropolitan": [117, 16, 86],
    "Northern": [0, 0, 0],
    "Piccadilly": [0, 25, 168],
    "Victoria": [0, 152, 216],
    "Waterloo & City": [147, 206, 186],
}

_SCALE = 4.5 / 2.2  # ratio between new and original render scale
def _s(x: int, y: int) -> dict:
    return {"x": round(x * _SCALE), "y": round(y * _SCALE)}

SCHEMATIC_STATION_POSITIONS = {
    "Liverpool Street": _s(1351, 808),
    "Oxford Circus": _s(1013, 871),
    "Tottenham Court Road": _s(1119, 924),
    "Monument": _s(1316, 965),
    "Piccadilly Circus": _s(1087, 991),
    "Bank": _s(1300, 932),
    "Leicester Square": _s(1121, 1034),
    "Moorgate": _s(1274, 852),
    "Barbican": _s(1230, 884),
    "Aldgate": _s(1460, 912),
    "Blackfriars": _s(1189, 1039),
    "St. Paul's": _s(1228, 949),
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
    reference["annualised_total"] = pd.to_numeric(reference["annualised_total"], errors="coerce")
    features["annualised_total"] = pd.to_numeric(features["annualised_total"], errors="coerce")
    merged = features.merge(
        reference,
        on=["station_id", "station_name", "annualised_total"],
        how="left",
    )
    merged["annualised_total_m"] = merged["annualised_total"] / 1_000_000
    merged["line_list"] = merged["lines"].fillna("").map(lambda value: [part for part in str(value).split("|") if part])
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
    if stations_df.empty:
        return stations_df, pd.DataFrame(columns=["line", "score"])

    stations_df["primary_line"] = stations_df["line_list"].map(lambda lines: lines[0] if lines else "Other")
    stations_df["line_color"] = stations_df["primary_line"].map(lambda line: LINE_COLORS.get(line, [255, 140, 0]))
    stations_df["score_radius"] = stations_df["score"].map(lambda value: max(9000, int(value * 220)))
    stations_df["label"] = stations_df.apply(lambda row: f"{row['station_name']} ({row['score']:.1f})", axis=1)

    line_df = pd.DataFrame(
        [{"line": line, "score": score} for line, score in result.line_scores.items()]
    ).sort_values("score", ascending=False)
    return stations_df, line_df


@st.cache_data
def fetch_tube_network() -> pd.DataFrame:
    rows = []
    for line_name, api_id in LINE_API_IDS.items():
        url = f"https://api.tfl.gov.uk/Line/{api_id}/Route/Sequence/all"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            payload = json.load(response)
        for idx, line_string in enumerate(payload.get("lineStrings", [])):
            coordinates = json.loads(line_string)
            rows.append(
                {
                    "line": line_name,
                    "path": [[point[0], point[1]] for point in coordinates],
                    "color": LINE_COLORS.get(line_name, [120, 120, 120]),
                    "width": 3,
                    "segment": idx,
                }
            )
    return pd.DataFrame(rows)


@st.cache_data
def get_official_tfl_map_image() -> bytes:
    CACHE_DIR.mkdir(exist_ok=True)
    pdf_path = CACHE_DIR / "standard-tube-map.pdf"
    png_path = CACHE_DIR / "standard-tube-map-page1.png"

    if not pdf_path.exists():
        req = urllib.request.Request(TFL_STANDARD_TUBE_MAP_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            pdf_path.write_bytes(response.read())

    if not png_path.exists() or png_path.stat().st_mtime < pdf_path.stat().st_mtime:
        pdf = pdfium.PdfDocument(str(pdf_path))
        page = pdf[0]
        image = page.render(scale=4.5).to_pil()
        image.save(png_path)

    return png_path.read_bytes()


def build_official_map_plotly(stations_df: pd.DataFrame) -> go.Figure:
    img = Image.open(CACHE_DIR / "standard-tube-map-page1.png").convert("RGB")
    img_width, img_height = img.size

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    covered = stations_df[stations_df["station_name"].isin(SCHEMATIC_STATION_POSITIONS)].copy()
    covered = covered.head(8).reset_index(drop=True)

    fig = go.Figure()

    fig.add_layout_image(
        dict(
            source=f"data:image/png;base64,{b64}",
            xref="x", yref="y",
            x=0, y=img_height,
            sizex=img_width, sizey=img_height,
            sizing="stretch",
            layer="below",
        )
    )

    for rank, row in covered.iterrows():
        pos = SCHEMATIC_STATION_POSITIONS[row["station_name"]]
        px, py = pos["x"], img_height - pos["y"]  # flip y for plotly
        r, g, b = row["line_color"]
        color = f"rgb({r},{g},{b})"
        hover = (
            f"<b>#{rank + 1} {row['station_name']}</b><br>"
            f"Score: {row['score']:.2f}<br>"
            f"Lines: {row['lines']}<br>"
            f"Annual entries/exits: {row['annualised_total_m']:.1f}M<br>"
            f"Borough: {row.get('borough_name', 'N/A')}"
        )
        fig.add_trace(go.Scatter(
            x=[px], y=[py],
            mode="markers+text",
            marker=dict(size=22, color=color, line=dict(color="white", width=3)),
            text=[str(rank + 1)],
            textfont=dict(color="white", size=11, family="Arial Black"),
            textposition="middle center",
            hovertemplate=hover + "<extra></extra>",
            name=row["station_name"],
            showlegend=True,
        ))

    fig.update_layout(
        xaxis=dict(range=[0, img_width], showgrid=False, zeroline=False, showticklabels=False, fixedrange=False),
        yaxis=dict(range=[0, img_height], showgrid=False, zeroline=False, showticklabels=False, fixedrange=False, scaleanchor="x"),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            title="Top stations",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#ccc",
            borderwidth=1,
            font=dict(size=11),
            x=1.01, y=1,
        ),
        height=680,
        dragmode="pan",
    )
    return fig


def build_feature_chart_data(row: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feature": [FRIENDLY_FEATURE_NAMES[name] for name in FEATURE_NAMES],
            "value": [row[name] for name in FEATURE_NAMES],
        }
    ).sort_values("value", ascending=False)


def build_line_network_for_display(line_df: pd.DataFrame, focus_line: str) -> pd.DataFrame:
    network = fetch_tube_network().copy()
    top_lines = set(line_df["line"].head(4).tolist()) if not line_df.empty else set()

    def style_row(row: pd.Series) -> pd.Series:
        line = row["line"]
        if focus_line != "All" and line != focus_line:
            row["color"] = [210, 210, 210]
            row["width"] = 1
        elif line in top_lines:
            row["width"] = 6
        else:
            row["width"] = 3
        return row

    return network.apply(style_row, axis=1)


def build_map(stations_df: pd.DataFrame, line_df: pd.DataFrame, focus_line: str) -> pdk.Deck:
    network_df = build_line_network_for_display(line_df, focus_line)
    if focus_line != "All":
        network_df = network_df.loc[network_df["line"] == focus_line].copy()
        filtered_stations = stations_df.loc[stations_df["line_list"].map(lambda lines: focus_line in lines)].copy()
        if filtered_stations.empty:
            filtered_stations = stations_df.copy()
    else:
        filtered_stations = stations_df.copy()

    line_layer = pdk.Layer(
        "PathLayer",
        data=network_df,
        get_path="path",
        get_color="color",
        get_width="width",
        width_min_pixels=2,
        pickable=True,
        opacity=0.78,
    )

    station_layer = pdk.Layer(
        "ScatterplotLayer",
        data=filtered_stations,
        get_position="[longitude, latitude]",
        get_fill_color="line_color",
        get_line_color=[255, 255, 255],
        get_line_width=2,
        line_width_min_pixels=1,
        get_radius="score_radius",
        radius_min_pixels=6,
        radius_max_pixels=22,
        pickable=True,
        opacity=0.92,
    )

    text_layer = pdk.Layer(
        "TextLayer",
        data=filtered_stations.head(8),
        get_position="[longitude, latitude]",
        get_text="station_name",
        get_size=13,
        size_units="pixels",
        get_color=[25, 25, 25],
        get_angle=0,
        get_text_anchor='start',
        get_alignment_baseline='bottom',
        get_pixel_offset=[8, -8],
    )

    mid_lat = filtered_stations["latitude"].mean()
    mid_lon = filtered_stations["longitude"].mean()
    return pdk.Deck(
        map_style="light",
        initial_view_state=pdk.ViewState(latitude=mid_lat, longitude=mid_lon, zoom=10.2, pitch=0),
        layers=[line_layer, station_layer, text_layer],
        tooltip={
            "html": "<b>{station_name}</b><br/>Score: {score}<br/>Lines: {lines}<br/>Annual entries/exits: {annualised_total_m}M",
            "style": {"backgroundColor": "#111827", "color": "white"},
        },
    )


st.set_page_config(page_title="Beat the Big Whale", layout="wide")

st.title("Beat the Big Whale")
st.caption("Use smarter location intelligence to beat big-budget spray-and-pray")

with st.sidebar:
    st.header("Campaign settings")
    industry = st.selectbox("Business profile", BUSINESS_PROFILES, index=BUSINESS_PROFILES.index("luxury_retail"))
    top_k = st.slider("Top stations", min_value=3, max_value=20, value=8)
    st.info("Proxy-based strategy tool for underdog teams, not an ROI guarantee.")

stations_df, line_df = load_results(industry, top_k)
line_focus_options = ["All"] + line_df["line"].tolist()
focus_line = st.selectbox("Map focus", line_focus_options, index=0)

best_station = stations_df.iloc[0]
col1, col2, col3 = st.columns(3)
col1.metric("Top station", best_station["station_name"])
col2.metric("Top score", f"{best_station['score']:.2f}")
col3.metric("Top station footfall", f"{best_station['annualised_total_m']:.1f}M annual")

st.subheader("Map views")
geo_tab, classic_tab = st.tabs(["Geographic network view", "Classic TfL map reference"])

with geo_tab:
    st.caption("Tube lines are drawn from TfL route sequences. Top lines for the current profile are visually emphasized.")
    st.pydeck_chart(build_map(stations_df, line_df, focus_line), width="stretch")

with classic_tab:
    get_official_tfl_map_image()
    covered_count = int(stations_df["station_name"].isin(SCHEMATIC_STATION_POSITIONS).sum())
    st.caption("Official TfL schematic Tube map — hover over markers for details, scroll to zoom, drag to pan.")
    st.plotly_chart(
        build_official_map_plotly(stations_df),
        use_container_width=True,
        config={"scrollZoom": True, "displayModeBar": True, "modeBarButtonsToAdd": ["resetScale2d"]},
    )
    st.write(f"Overlay coverage: {covered_count}/{min(len(stations_df), 8)} top stations currently mapped onto the schematic view")
    st.markdown("Top recommended stations on that map:")
    for idx, row in stations_df.head(8).iterrows():
        marker = "✓" if row["station_name"] in SCHEMATIC_STATION_POSITIONS else "•"
        st.write(f"{marker} {idx + 1}. {row['station_name']} — {row['lines']}")

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
    width="stretch",
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
st.code("cd /srv/agents/beat-the-big-whale && . .venv/bin/activate && streamlit run streamlit_app.py", language="bash")
