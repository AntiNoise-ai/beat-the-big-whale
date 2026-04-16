from __future__ import annotations

import base64
import io
import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd
from PIL import Image
import plotly.graph_objects as go
import pydeck as pdk
import pypdfium2 as pdfium
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tube_london_ads.models import FEATURE_NAMES, StationFeatureVector
from tube_london_ads.profiles import (
    BUSINESS_PROFILES,
    PROFILE_DESCRIPTIONS,
    PROFILE_LABELS,
)
from tube_london_ads.scoring import recommend

VECTORS_PATH = ROOT / "data" / "processed" / "station_feature_vectors_real.json"
SCHEMATIC_POSITIONS_PATH = ROOT / "data" / "processed" / "schematic_positions.json"
FEATURE_TABLE_PATH = ROOT / "data" / "processed" / "station_feature_table_real.csv"
STATION_REFERENCE_PATH = ROOT / "data" / "processed" / "station_reference_with_counts.csv"
CACHE_DIR = ROOT / ".cache"
TFL_STANDARD_TUBE_MAP_URL = "https://content.tfl.gov.uk/standard-tube-map.pdf"

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

SCHEMATIC_STATION_POSITIONS: dict = (
    json.loads(SCHEMATIC_POSITIONS_PATH.read_text())
    if SCHEMATIC_POSITIONS_PATH.exists()
    else {}
)

# ---------------------------------------------------------------------------
# Pricing model
# ---------------------------------------------------------------------------

def weekly_cost(footfall_proxy: float) -> int:
    """Indicative weekly cost for one 4-sheet panel at a station."""
    if footfall_proxy >= 8:
        return 850
    if footfall_proxy >= 6:
        return 550
    if footfall_proxy >= 4:
        return 320
    if footfall_proxy >= 2:
        return 190
    return 110


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

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
    merged["line_list"] = merged["lines"].fillna("").map(
        lambda value: [part for part in str(value).split("|") if part]
    )
    return merged


@st.cache_data
def load_results(
    industry: str, top_k: int, value_mode: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame]:
    station_frame = load_station_frame()
    result = recommend(
        industry=industry, top_k=top_k, stations=load_vectors(), value_mode=value_mode
    )

    station_rows = []
    for rec in result.stations:
        matches = station_frame.loc[station_frame["station_name"] == rec.station_name]
        if matches.empty:
            continue
        row = matches.iloc[0].to_dict()
        row["score"] = rec.score
        row["top_reasons"] = " | ".join(rec.top_reasons)
        row["context_notes"] = " | ".join(rec.context_notes)
        row["feature_breakdown"] = rec.feature_breakdown
        # Compute cost/impression columns here so they travel with the dataframe
        fp = float(row.get("footfall_proxy", 0) or 0)
        row["weekly_cost_est"] = weekly_cost(fp)
        annual = float(row.get("annualised_total", 0) or 0)
        row["weekly_impressions"] = int(annual / 52) if annual > 0 else 0
        wi = row["weekly_impressions"]
        wc = row["weekly_cost_est"]
        row["cpm"] = round((wc / wi) * 1000, 2) if wi > 0 else None
        station_rows.append(row)

    stations_df = pd.DataFrame(station_rows)
    if stations_df.empty:
        return stations_df, pd.DataFrame(columns=["line", "score"])

    stations_df["primary_line"] = stations_df["line_list"].map(
        lambda lines: lines[0] if lines else "Other"
    )
    stations_df["line_color"] = stations_df["primary_line"].map(
        lambda line: LINE_COLORS.get(line, [255, 140, 0])
    )
    stations_df["score_radius"] = stations_df["score"].map(
        lambda value: max(9000, int(value * 220))
    )
    stations_df["label"] = stations_df.apply(
        lambda row: f"{row['station_name']} ({row['score']:.1f})", axis=1
    )

    # Audience fit % — normalise score to 0-100 relative to the top scorer
    max_score = stations_df["score"].max()
    stations_df["audience_fit_pct"] = (
        (stations_df["score"] / max_score * 100).round(0).astype(int)
        if max_score > 0
        else 0
    )

    line_df = pd.DataFrame(
        [{"line": line, "score": score} for line, score in result.line_scores.items()]
    ).sort_values("score", ascending=False)

    return stations_df, line_df


# ---------------------------------------------------------------------------
# Budget allocation
# ---------------------------------------------------------------------------

def build_media_plan(stations_df: pd.DataFrame, weekly_budget: float) -> pd.DataFrame:
    """Greedy selection: pick stations from ranked list until budget exhausted."""
    plan_rows = []
    remaining = weekly_budget
    for _, row in stations_df.iterrows():
        cost = row["weekly_cost_est"]
        if cost <= remaining:
            plan_rows.append(row)
            remaining -= cost
        if remaining <= 0:
            break
    return pd.DataFrame(plan_rows).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Map / chart builders
# ---------------------------------------------------------------------------

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
        req = urllib.request.Request(
            TFL_STANDARD_TUBE_MAP_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
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

    covered = stations_df[
        stations_df["station_name"].isin(SCHEMATIC_STATION_POSITIONS)
    ].copy()
    covered = covered.reset_index(drop=True)

    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source=f"data:image/png;base64,{b64}",
            xref="x",
            yref="y",
            x=0,
            y=img_height,
            sizex=img_width,
            sizey=img_height,
            sizing="stretch",
            layer="below",
        )
    )

    for rank, row in covered.iterrows():
        pos = SCHEMATIC_STATION_POSITIONS[row["station_name"]]
        px, py = pos["x"], img_height - pos["y"]
        r, g, b = row["line_color"]
        color = f"rgb({r},{g},{b})"
        hover = (
            f"<b>#{rank + 1} {row['station_name']}</b><br>"
            f"Score: {row['score']:.2f}<br>"
            f"Lines: {row['lines']}<br>"
            f"Annual entries/exits: {row['annualised_total_m']:.1f}M<br>"
            f"Borough: {row.get('borough_name', 'N/A')}"
        )
        fig.add_trace(
            go.Scatter(
                x=[px],
                y=[py],
                mode="markers+text",
                marker=dict(size=22, color=color, line=dict(color="white", width=3)),
                text=[str(rank + 1)],
                textfont=dict(color="white", size=11, family="Arial Black"),
                textposition="middle center",
                hovertemplate=hover + "<extra></extra>",
                name=row["station_name"],
                showlegend=True,
            )
        )

    fig.update_layout(
        xaxis=dict(
            range=[0, img_width],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            fixedrange=False,
        ),
        yaxis=dict(
            range=[0, img_height],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            fixedrange=False,
            scaleanchor="x",
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            title="Top stations",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#ccc",
            borderwidth=1,
            font=dict(size=11),
            x=1.01,
            y=1,
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


def build_line_network_for_display(
    line_df: pd.DataFrame, focus_line: str
) -> pd.DataFrame:
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


def build_map(
    stations_df: pd.DataFrame, line_df: pd.DataFrame, focus_line: str
) -> pdk.Deck:
    network_df = build_line_network_for_display(line_df, focus_line)
    if focus_line != "All":
        network_df = network_df.loc[network_df["line"] == focus_line].copy()
        filtered_stations = stations_df.loc[
            stations_df["line_list"].map(lambda lines: focus_line in lines)
        ].copy()
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
        get_text_anchor="start",
        get_alignment_baseline="bottom",
        get_pixel_offset=[8, -8],
    )

    mid_lat = filtered_stations["latitude"].mean()
    mid_lon = filtered_stations["longitude"].mean()
    return pdk.Deck(
        map_style="light",
        initial_view_state=pdk.ViewState(
            latitude=mid_lat, longitude=mid_lon, zoom=10.2, pitch=0
        ),
        layers=[line_layer, station_layer, text_layer],
        tooltip={
            "html": (
                "<b>{station_name}</b><br/>"
                "Score: {score}<br/>"
                "Lines: {lines}<br/>"
                "Annual entries/exits: {annualised_total_m}M"
            ),
            "style": {"backgroundColor": "#111827", "color": "white"},
        },
    )


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Beat the Big Whale — Campaign Planner", layout="wide")

# ---------------------------------------------------------------------------
# Step 1 — Campaign Brief
# ---------------------------------------------------------------------------

st.title("Beat the Big Whale")
st.caption("Build a smarter London Underground media plan — without a big-agency budget")

st.markdown("### Step 1 — Campaign Brief")

brief_col1, brief_col2 = st.columns([3, 2])
with brief_col1:
    inner_a, inner_b = st.columns(2)
    with inner_a:
        brand_name = st.text_input("Company / Brand", value="DJI", placeholder="e.g. DJI")
    with inner_b:
        product_desc = st.text_input(
            "Product / What you're advertising",
            value="Osmo Action 5 Pro camera",
            placeholder="e.g. Osmo Action 5 Pro camera",
        )

with brief_col2:
    inner_c, inner_d = st.columns(2)
    with inner_c:
        budget_total = st.number_input(
            "Total budget (£)", min_value=500, max_value=500_000,
            value=10_000, step=500,
        )
    with inner_d:
        duration_weeks = st.number_input(
            "Duration (weeks)", min_value=1, max_value=52, value=4, step=1
        )

profile_col, rank_col, topk_col = st.columns([3, 2, 1])
with profile_col:
    profile_options = list(BUSINESS_PROFILES)
    profile_display = [PROFILE_LABELS.get(p, p) for p in profile_options]
    default_idx = profile_options.index("consumer_tech") if "consumer_tech" in profile_options else 0
    selected_display = st.selectbox(
        "Audience profile",
        options=profile_display,
        index=default_idx,
    )
    industry = profile_options[profile_display.index(selected_display)]

with rank_col:
    ranking_mode = st.radio(
        "Ranking",
        ["Reach  —  max impressions", "Value  —  hidden gems"],
        index=0,
        help=(
            "**Reach**: ranks by total weighted score. Surfaces the biggest, most central stations.\n\n"
            "**Value / Hidden gems**: ranks by audience fit divided by footfall. "
            "Surfaces stations where your target demographic is strong but overall "
            "footfall (and thus likely ad cost) is lower."
        ),
    )
    value_mode = ranking_mode.startswith("Value")

with topk_col:
    top_k = st.slider("Candidate pool", min_value=5, max_value=30, value=20,
                      help="How many top stations to score and display before budget allocation")

# Show profile description
profile_desc = PROFILE_DESCRIPTIONS.get(industry, "")
if profile_desc:
    st.caption(f"Profile: {profile_desc}")

weekly_budget = budget_total / duration_weeks

# ---------------------------------------------------------------------------
# Load data (cached on industry + top_k + value_mode)
# ---------------------------------------------------------------------------

stations_df, line_df = load_results(industry, top_k, value_mode)

if stations_df.empty:
    st.error("No station data found. Check that the data files are present.")
    st.stop()

# ---------------------------------------------------------------------------
# Step 2 — Media Plan Table
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown("### Step 2 — Media Plan")

plan_df = build_media_plan(stations_df, weekly_budget)

if plan_df.empty:
    st.warning(
        f"Weekly budget of £{weekly_budget:,.0f} is too low to include any station. "
        "Try increasing your budget or duration."
    )
else:
    plan_display = plan_df[[
        "station_name", "lines", "zone", "weekly_impressions",
        "weekly_cost_est", "cpm", "audience_fit_pct",
    ]].copy()
    plan_display.index = range(1, len(plan_display) + 1)
    plan_display.index.name = "#"

    # Format columns
    plan_display["weekly_impressions"] = plan_display["weekly_impressions"].map(
        lambda v: f"{v:,}"
    )
    plan_display["weekly_cost_est"] = plan_display["weekly_cost_est"].map(
        lambda v: f"£{v:,}"
    )
    plan_display["cpm"] = plan_display["cpm"].map(
        lambda v: f"£{v:.2f}" if v is not None else "—"
    )
    plan_display["audience_fit_pct"] = plan_display["audience_fit_pct"].map(
        lambda v: f"{v}%"
    )

    plan_display.columns = [
        "Station", "Line(s)", "Zone", "Weekly impressions",
        "Cost/wk (est.)", "CPM", "Audience fit",
    ]

    st.dataframe(plan_display, use_container_width=True)

    budget_note_col1, budget_note_col2 = st.columns(2)
    with budget_note_col1:
        st.caption(
            f"Budget split: £{budget_total:,} total / {duration_weeks} weeks "
            f"= **£{weekly_budget:,.0f}/week**. "
            f"Stations selected greedily from highest-ranked until weekly budget is exhausted."
        )
    with budget_note_col2:
        st.caption(
            "Cost estimates are indicative only (one 4-sheet panel per station per week). "
            "Actual TfL/media owner rates will vary."
        )

# ---------------------------------------------------------------------------
# Step 3 — Campaign Summary KPIs
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown("### Step 3 — Campaign Summary")

if not plan_df.empty:
    total_stations = len(plan_df)
    total_weekly_impr = int(plan_df["weekly_impressions"].sum())
    total_campaign_impr = total_weekly_impr * duration_weeks
    total_weekly_spend = int(plan_df["weekly_cost_est"].sum())
    total_spend = total_weekly_spend * duration_weeks

    valid_cpms = plan_df["cpm"].dropna()
    blended_cpm = (
        round((total_weekly_spend / total_weekly_impr) * 1000, 2)
        if total_weekly_impr > 0
        else None
    )

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Stations in plan", total_stations)
    kpi2.metric(
        "Weekly impressions",
        f"{total_weekly_impr / 1_000:.0f}K" if total_weekly_impr >= 1000 else str(total_weekly_impr),
    )
    kpi3.metric(
        "Campaign impressions",
        f"{total_campaign_impr / 1_000_000:.2f}M" if total_campaign_impr >= 1_000_000
        else f"{total_campaign_impr / 1_000:.0f}K",
    )
    kpi4.metric(
        "Blended CPM",
        f"£{blended_cpm:.2f}" if blended_cpm is not None else "—",
    )
    kpi5.metric(
        "Budget utilised",
        f"£{total_spend:,}",
        delta=f"of £{budget_total:,} ({total_spend / budget_total * 100:.0f}%)" if budget_total > 0 else None,
        delta_color="off",
    )

    # ROAS estimator
    st.markdown("#### ROAS Estimate")
    st.caption(
        "Rough illustrative estimate only. These are not guarantees — they are a framework "
        "for sanity-checking reach relative to conversion assumptions."
    )

    roas_col1, roas_col2, roas_col3 = st.columns(3)
    with roas_col1:
        consider_rate_pct = st.slider(
            "% of reached people who consider a purchase",
            min_value=0.01, max_value=1.0, value=0.10, step=0.01,
            format="%.2f%%",
        )
    with roas_col2:
        conversion_rate_pct = st.slider(
            "% of those who convert",
            min_value=0.5, max_value=20.0, value=3.0, step=0.5,
            format="%.1f%%",
        )
    with roas_col3:
        aov = st.slider(
            "Average order value (£)",
            min_value=10, max_value=2000, value=350, step=10,
        )

    consider_rate = consider_rate_pct / 100
    conversion_rate = conversion_rate_pct / 100
    estimated_buyers = total_campaign_impr * consider_rate * conversion_rate
    estimated_revenue = estimated_buyers * aov
    roas = estimated_revenue / total_spend if total_spend > 0 else 0

    roas_a, roas_b, roas_c, roas_d = st.columns(4)
    roas_a.metric("Est. considerers", f"{int(total_campaign_impr * consider_rate):,}")
    roas_b.metric("Est. converters", f"{int(estimated_buyers):,}")
    roas_c.metric("Est. revenue", f"£{estimated_revenue:,.0f}")
    roas_d.metric("Est. ROAS", f"{roas:.1f}×")

    st.markdown(
        f"""
**Formula:** {total_campaign_impr:,} campaign impressions
× {consider_rate_pct:.2f}% consideration rate
× {conversion_rate_pct:.1f}% conversion rate
× £{aov} AOV
= **£{estimated_revenue:,.0f} estimated revenue**
÷ £{total_spend:,} spend
= **{roas:.1f}× ROAS**

_These numbers are directional. OOH attribution is hard — use this to pressure-test assumptions, not to forecast P&L._
"""
    )

# ---------------------------------------------------------------------------
# Step 4 — Why this works (station cards)
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(f"### Step 4 — Why this works for {brand_name}")

if not plan_df.empty:
    for rank_idx, (_, row) in enumerate(plan_df.iterrows(), start=1):
        station_label = f"#{rank_idx}  {row['station_name']}  —  {row['lines']}  |  Zone {row['zone']}"
        with st.expander(station_label, expanded=(rank_idx <= 3)):
            card_left, card_right = st.columns([2, 1])
            with card_left:
                st.markdown(f"**Why it works for {brand_name} ({product_desc})**")
                reasons = str(row.get("top_reasons", "")).split(" | ")
                for reason in reasons:
                    if reason.strip():
                        st.markdown(f"- {reason.strip()}")

                context_raw = str(row.get("context_notes", "")).split(" | ")
                context_items = [c.strip() for c in context_raw if c.strip()]
                if context_items:
                    st.markdown("**Context:**")
                    for item in context_items:
                        st.markdown(f"- {item}")

            with card_right:
                wi = row.get("weekly_impressions", 0)
                wc = row.get("weekly_cost_est", 0)
                fit = row.get("audience_fit_pct", 0)
                borough = row.get("borough_name", "N/A")
                annual_m = row.get("annualised_total_m", 0)

                st.markdown("**Station stats**")
                st.markdown(f"- Borough: {borough}")
                st.markdown(f"- Annual footfall: {annual_m:.1f}M entries/exits")
                st.markdown(f"- Weekly impressions: {wi:,}")
                st.markdown(f"- Est. cost/week: £{wc:,}")
                st.markdown(f"- Audience match: **{fit}%**")

# ---------------------------------------------------------------------------
# Step 5 — Map views
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown("### Step 5 — Map views")

line_focus_options = ["All"] + line_df["line"].tolist()
focus_line = st.selectbox("Map line focus", line_focus_options, index=0)

geo_tab, classic_tab = st.tabs(["Geographic network view", "Classic TfL map reference"])

with geo_tab:
    st.caption(
        "Tube lines drawn from TfL route sequences. "
        "Top lines for the current profile are visually emphasized."
    )
    st.pydeck_chart(build_map(stations_df, line_df, focus_line), width="stretch")

with classic_tab:
    get_official_tfl_map_image()
    covered_count = int(
        stations_df["station_name"].isin(SCHEMATIC_STATION_POSITIONS).sum()
    )
    st.caption(
        "Official TfL schematic Tube map — hover over markers for details, "
        "scroll to zoom, drag to pan."
    )
    st.plotly_chart(
        build_official_map_plotly(stations_df),
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "modeBarButtonsToAdd": ["resetScale2d"],
        },
    )
    st.write(
        f"Overlay coverage: {covered_count}/{len(stations_df)} "
        "top stations mapped onto the schematic view"
    )
    st.markdown("Top recommended stations on that map:")
    for idx, row in stations_df.iterrows():
        marker = "✓" if row["station_name"] in SCHEMATIC_STATION_POSITIONS else "•"
        st.write(f"{marker} {idx + 1}. {row['station_name']} — {row['lines']}")

# ---------------------------------------------------------------------------
# Step 6 — Line rankings
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown("### Step 6 — Line rankings")
st.caption("Average score among the top stations, broken down by line.")
if not line_df.empty:
    st.bar_chart(line_df.set_index("line"))

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    "Proxy-based campaign planning tool. Recommendations are based on demographic and POI data, "
    "not guaranteed ROI. Always validate with actual TfL media owner rate cards before committing budget."
)
st.code(
    "cd /srv/agents/beat-the-big-whale && . .venv/bin/activate && streamlit run streamlit_app.py",
    language="bash",
)
