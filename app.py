import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import hashlib

# Page configuration
st.set_page_config(
    page_title="Sudan Intervention",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
def check_credentials():
    def login_entered():
        username = st.session_state["username"]
        password = st.session_state["password"]
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if username in st.secrets["credentials"]:
            if st.secrets["credentials"][username] == password_hash:
                st.session_state["authenticated"] = True
                st.session_state["current_user"] = username
                del st.session_state["password"]
                return
        st.session_state["authenticated"] = False

    if st.session_state.get("authenticated", False):
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Login", use_container_width=True):
                login_entered()
                if not st.session_state.get("authenticated", False):
                    st.error("Invalid username or password")
                else:
                    st.rerun()
        with col_btn2:
            if st.button("Create an account", use_container_width=True):
                st.info("Account creation feature coming soon!")
    return False

if not check_credentials():
    st.stop()

if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.session_state["current_user"] = None
    st.rerun()

st.sidebar.success(f"⚠️ Logged in as: {st.session_state.get('current_user', 'Unknown')}")

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric label { color: #8b92a8 !important; font-size: 14px !important; }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 32px !important;
        font-weight: bold !important;
    }
    h1 { color: #ffffff; font-size: 28px; margin-bottom: 5px; }
    h3 { color: #8b92a8; font-size: 16px; font-weight: normal; margin-top: 0; }
    .sidebar .sidebar-content { background-color: #1e2130; }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# AGENCY INITIALS HELPER
# ─────────────────────────────────────────────
def make_initials(name: str) -> str:
    """Return uppercase initials for an organisation name."""
    if not isinstance(name, str):
        return name
    # Strip common filler words before extracting initials
    stop = {"the", "of", "for", "and", "in", "to", "a", "an", "on", "&"}
    words = [w for w in name.split() if w.lower() not in stop]
    return "".join(w[0].upper() for w in words if w)

# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
@st.cache_data
@st.cache_data
@st.cache_data
@st.cache_data
def load_data():
    df = pd.read_csv('project_summary_v2.csv', low_memory=False)
    df['ActualStartDate'] = pd.to_datetime(df['ActualStartDate'], format='mixed', dayfirst=True)
    df['ActualEndDate']   = pd.to_datetime(df['ActualEndDate'],   format='mixed', dayfirst=True)
    df['StartYear'] = df['ActualStartDate'].dt.year
    df['EndYear']   = df['ActualEndDate'].dt.year
    df['AgencyInitials'] = df['OrganizationName'].apply(make_initials)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()


# ─────────────────────────────────────────────
# AI HELPERS
# ─────────────────────────────────────────────
def generate_data_summary(df):
    summary = {
        "total_records": len(df),
        "date_range": {
            "start": df['ActualStartDate'].min().strftime('%d %B %Y') if not df.empty else "N/A",
            "end":   df['ActualEndDate'].max().strftime('%d %B %Y')   if not df.empty else "N/A",
        },
        "projects":      {"total": df['ChfProjectCode'].nunique(),
                          "by_status": df['ProjectStatus'].value_counts().to_dict()},
        "organizations": {"total": df['OrganizationName'].nunique(),
                          "top_5": df['OrganizationName'].value_counts().head(5).to_dict()},
        "sectors":       {"distribution": df['Cluster'].value_counts().to_dict()},
        "locations":     {"total_states":  df['AdminLocation1'].nunique(),
                          "top_5_states":  df['AdminLocation1'].value_counts().head(5).to_dict()},
        "budget": {
            "total":   f"${df['Budget'].sum():,.2f}"    if 'Budget' in df.columns else "N/A",
            "average": f"${df['Budget'].mean():,.2f}"   if 'Budget' in df.columns else "N/A",
            "median":  f"${df['Budget'].median():,.2f}" if 'Budget' in df.columns else "N/A",
        },
    }
    return summary

def get_llm_summary_ollama(data_summary, model_name):
    try:
        import requests
        prompt = f"""You are a humanitarian data analyst. Based on the following data summary from Sudan interventions, provide a brief, insightful analysis in 3-4 paragraphs. Focus on key trends, patterns, and actionable insights.

Data Summary:
{json.dumps(data_summary, indent=2)}

Please provide:
1. Overview of the intervention landscape
2. Key sectors and their distribution
3. Geographic coverage insights
4. Budget allocation patterns
5. Any notable trends or recommendations

Keep the response concise, professional, and actionable."""
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={'model': model_name, 'prompt': prompt, 'stream': False},
            timeout=60
        )
        if response.status_code == 200:
            return response.json()['response']
        return f"Error: Unable to generate summary (Status: {response.status_code})"
    except requests.exceptions.ConnectionError:
        return "⚠️ **Ollama is not running**. Please start Ollama by running `ollama serve` in your terminal."
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def get_simple_summary(data_summary):
    summary = f"""**Overview:**
The current filtered dataset contains **{data_summary['total_records']} intervention records** across **{data_summary['projects']['total']} unique projects**, spanning from {data_summary['date_range']['start']} to {data_summary['date_range']['end']}.

**Organisational Landscape:**
{data_summary['organizations']['total']} implementing agencies are involved.
"""
    for org, count in list(data_summary['organizations']['top_5'].items())[:5]:
        summary += f"  - {org}: {count} projects\n"

    summary += "\n**Sectoral Distribution:**\n"
    for sector, count in list(data_summary['sectors']['distribution'].items())[:5]:
        pct = (count / data_summary['total_records']) * 100
        summary += f"  - {sector}: {count} interventions ({pct:.1f}%)\n"

    summary += f"\n**Geographic Coverage:** {data_summary['locations']['total_states']} states\n"
    for state, count in list(data_summary['locations']['top_5_states'].items())[:5]:
        summary += f"  - {state}: {count} interventions\n"

    summary += f"""
**Budget Analysis:**
- Total: {data_summary['budget']['total']}
- Average: {data_summary['budget']['average']}
- Median: {data_summary['budget']['median']}

**Project Status:**
"""
    for status, count in data_summary['projects']['by_status'].items():
        pct = (count / data_summary['total_records']) * 100
        summary += f"  - {status}: {count} ({pct:.1f}%)\n"

    return summary

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("<h1>Intervention Overview</h1>", unsafe_allow_html=True)
st.markdown("<h3>Summary of ongoing and completed interventions by location, sector, and partner</h3>", unsafe_allow_html=True)
st.markdown("---")

# ─────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────
with st.sidebar:
    try:
        st.image("United-Nations_logo.webp", use_container_width=True)
    except Exception:
        pass
    st.markdown("## Durable Solutions Unit")
    st.markdown("---")
    st.markdown("### ⊙ Filters")

    # ── Date range ──────────────────────────────
    st.markdown("#### Date Range")
    min_year = int(df['StartYear'].min()) if not df['StartYear'].isna().all() else 2020
    max_year = int(df['EndYear'].max())   if not df['EndYear'].isna().all()   else datetime.now().year
    year_range = list(range(min_year, max_year + 1))

    col_y1, col_y2 = st.columns(2)
    with col_y1:
        start_year = st.selectbox("Start Year", options=year_range, index=0)
    with col_y2:
        end_year = st.selectbox("End Year", options=year_range, index=len(year_range) - 1)

    if start_year > end_year:
        st.warning("⚠️ Start year must be ≤ end year")

    st.markdown("---")

    # ── Agency (show initials in selector, keep full names for filtering) ──
    agency_options = ['All'] + sorted(df['OrganizationName'].unique().tolist())

    # Build display label: "WFP (World Food Programme)"  — initials first
    def agency_label(name):
        if name == 'All':
            return 'All'
        initials = make_initials(name)
        return f"{initials} ({name})" if initials != name else name

    agency_display = {name: agency_label(name) for name in agency_options}

    selected_agency_labels = st.multiselect(
        "Ξ Agency",
        options=list(agency_display.values()),
        default=['All']
    )
    # Map display labels back to raw names
    label_to_name = {v: k for k, v in agency_display.items()}
    selected_agency = [label_to_name[l] for l in selected_agency_labels if l in label_to_name]
    if not selected_agency:
        selected_agency = ['All']

    # ── Intervention type ────────────────────────
    intervention_types = ['All'] + sorted(df['Cluster'].dropna().unique().tolist())
    selected_intervention = st.multiselect("▤ Intervention Type", options=intervention_types, default=['All'])

    # ── Location (state) ─────────────────────────
    locations = ['All'] + sorted(df['AdminLocation1'].dropna().unique().tolist())
    selected_location = st.multiselect("▣ Location (State)", options=locations, default=['All'])

    # ── Project ──────────────────────────────────
    projects_list = ['All'] + sorted(df['ProjectTitle'].dropna().unique().tolist())
    selected_project = st.multiselect("▦ Project", options=projects_list, default=['All'])

    # ── Status ───────────────────────────────────
    statuses = ['All'] + sorted(df['ProjectStatus'].dropna().unique().tolist())
    selected_status = st.multiselect("▢ Implementation Status", options=statuses, default=['All'])

    st.markdown("---")
    st.markdown("#### AI Analysis")
    ai_model = st.selectbox(
        "Select AI Model",
        options=["Simple Summary (No AI)", "Ollama (llama3.2)", "Ollama (mistral)"],
    )

    st.markdown("---")
    if st.button("🔄 Reset All Filters", use_container_width=True):
        st.rerun()

# ─────────────────────────────────────────────
# APPLY FILTERS
# ─────────────────────────────────────────────
filtered_df = df.copy()

filtered_df = filtered_df[
    (filtered_df['StartYear'] >= start_year) &
    (filtered_df['EndYear']   <= end_year)
]

if 'All' not in selected_agency:
    filtered_df = filtered_df[filtered_df['OrganizationName'].isin(selected_agency)]

if 'All' not in selected_intervention:
    filtered_df = filtered_df[filtered_df['Cluster'].isin(selected_intervention)]

if 'All' not in selected_location:
    filtered_df = filtered_df[filtered_df['AdminLocation1'].isin(selected_location)]

if 'All' not in selected_project:
    filtered_df = filtered_df[filtered_df['ProjectTitle'].isin(selected_project)]

if 'All' not in selected_status:
    filtered_df = filtered_df[filtered_df['ProjectStatus'].isin(selected_status)]

if len(filtered_df) < len(df):
    st.info(f"Showing {len(filtered_df):,} of {len(df):,} total records | {start_year} – {end_year}")

# ─────────────────────────────────────────────
# KPI METRICS  (no comparison percentages)
# ─────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("◳ Total Interventions", f"{len(filtered_df):,}")
with col2:
    st.metric("◰ Total Projects", f"{filtered_df['ChfProjectCode'].nunique():,}")
with col3:
    st.metric("◱ States Covered", f"{filtered_df['AdminLocation1'].nunique():,}")
with col4:
    st.metric("◲ Implementing Agencies", f"{filtered_df['OrganizationName'].nunique():,}")

st.markdown("---")

# ─────────────────────────────────────────────
# MAP — one dot per project at locality level
# zoom to state bbox when a state filter is active
# ─────────────────────────────────────────────
st.markdown("### Intervention Map")
st.markdown("One dot per project at locality level. Select a state to zoom in.")

map_data = filtered_df.dropna(subset=['Lat_Admin2', 'Lon_Admin2'])
st.caption(f"Map is rendering {len(map_data)} points from {len(filtered_df)} filtered rows.")


# ── Determine map centre & zoom ───────────────
# Default: full Sudan view
DEFAULT_LAT, DEFAULT_LON, DEFAULT_ZOOM = 12.8, 30.2, 4.5

if 'All' not in selected_location and len(selected_location) > 0:
    # Zoom to the bounding box of the selected state(s)
    state_data = map_data[map_data['AdminLocation1'].isin(selected_location)]
    if not state_data.empty:
        lat_min = state_data['Lat_Admin2'].min()
        lat_max = state_data['Lat_Admin2'].max()
        lon_min = state_data['Lon_Admin2'].min()
        lon_max = state_data['Lon_Admin2'].max()
        center_lat = (lat_min + lat_max) / 2
        center_lon = (lon_min + lon_max) / 2
        # Estimate zoom: tighter bbox → higher zoom
        lat_span = max(lat_max - lat_min, 0.5)
        lon_span = max(lon_max - lon_min, 0.5)
        span = max(lat_span, lon_span)
        # Empirical mapping: span ~10° → zoom 5, span ~2° → zoom 7
        import math
        zoom_level = max(4.5, min(8.5, 6.5 - math.log2(span / 2)))
    else:
        center_lat, center_lon, zoom_level = DEFAULT_LAT, DEFAULT_LON, DEFAULT_ZOOM
else:
    center_lat, center_lon, zoom_level = DEFAULT_LAT, DEFAULT_LON, DEFAULT_ZOOM

if len(map_data) > 0:
    fig_map = go.Figure()

    # ── GeoJSON boundary layer ─────────────────
    try:
        with open('sudan_admin2.geojson', 'r', encoding='utf-8') as f:
            sudan_geojson = json.load(f)

        locality_names = [
            feat['properties'].get('adm2_name', '')
            for feat in sudan_geojson['features']
        ]

        fig_map.add_trace(go.Choroplethmapbox(
            geojson=sudan_geojson,
            locations=locality_names,
            z=[1] * len(locality_names),
            featureidkey="properties.adm2_name",
            colorscale=[[0, 'rgba(255,255,255,0.05)'], [1, 'rgba(255,255,255,0.05)']],
            showscale=False,
            marker_opacity=1,
            marker_line_width=0.6,
            marker_line_color='#555577',
            hovertemplate='<b>%{location}</b><extra></extra>',
            name='Localities'
        ))

        # Locality label centroids
        locality_centroids = []
        for feat in sudan_geojson['features']:
            name = feat['properties'].get('adm2_name', '')
            coords = feat['geometry']['coordinates']
            try:
                if feat['geometry']['type'] == 'Polygon':
                    lons = [c[0] for c in coords[0]]
                    lats = [c[1] for c in coords[0]]
                elif feat['geometry']['type'] == 'MultiPolygon':
                    lons = [c[0] for c in coords[0][0]]
                    lats = [c[1] for c in coords[0][0]]
                else:
                    continue
                locality_centroids.append({
                    'name': name,
                    'lon': sum(lons) / len(lons),
                    'lat': sum(lats) / len(lats),
                })
            except Exception:
                continue

        if locality_centroids:
            fig_map.add_trace(go.Scattermapbox(
                lon=[c['lon'] for c in locality_centroids],
                lat=[c['lat'] for c in locality_centroids],
                mode='text',
                text=[c['name'] for c in locality_centroids],
                textfont=dict(size=8, color='#aaaacc', family='Arial'),
                hoverinfo='skip',
                showlegend=False,
                name='Locality Names'
            ))

    except FileNotFoundError:
        st.warning("⚠️ sudan_admin2.geojson not found — boundary layer skipped.")
    except Exception as e:
        st.error(f"Error loading GeoJSON: {e}")

    # ── ONE DOT PER PROJECT at locality level ──
    # Each row in map_data represents one project-locality record.
    # We de-duplicate so each (ChfProjectCode, AdmLoc2) pair is a single dot.
    project_dots = (
        map_data
        .drop_duplicates(subset=['ChfProjectCode', 'AdmLoc2'])
        .copy()
    )

    # Shorten agency name to initials for hover
    project_dots['AgencyShort'] = project_dots['OrganizationName'].apply(make_initials)

    # Format dates for hover
    project_dots['StartFmt'] = project_dots['ActualStartDate'].dt.strftime('%-d %B %Y')
    project_dots['EndFmt']   = project_dots['ActualEndDate'].dt.strftime('%-d %B %Y')

    # Status → colour mapping
    status_colors = {
        'Ongoing':   '#00d4aa',
        'Completed': '#4e9af1',
        'Pipeline':  '#f4c542',
        'Cancelled': '#e05c5c',
    }

    def status_color(s):
        for key in status_colors:
            if isinstance(s, str) and key.lower() in s.lower():
                return status_colors[key]
        return '#a0a0c0'

    project_dots['dot_color'] = project_dots['ProjectStatus'].apply(status_color)

    fig_map.add_trace(go.Scattermapbox(
        lon=project_dots['Lon_Admin2'],
        lat=project_dots['Lat_Admin2'],
        mode='markers',
        marker=dict(
            size=9,
            color=project_dots['dot_color'],
            opacity=0.85,
        ),
        text=project_dots['AdmLoc2'],
        customdata=project_dots[[
            'ChfProjectCode',
            'AgencyShort',
            'ProjectStatus',
            'StartFmt',
            'EndFmt',
            'Budget',
            'AdminLocation1',
        ]].values,
        hovertemplate=(
            '<b>%{text}</b> — %{customdata[6]}<br>'
            'Project : %{customdata[0]}<br>'
            'Agency  : %{customdata[1]}<br>'
            'Status  : %{customdata[2]}<br>'
            'Start   : %{customdata[3]}<br>'
            'End     : %{customdata[4]}<br>'
            'Budget  : $%{customdata[5]:,.0f}'
            '<extra></extra>'
        ),
        name='Projects',
    ))

    # ── Legend for status colours (manual) ────
    for status, color in status_colors.items():
        fig_map.add_trace(go.Scattermapbox(
            lon=[None], lat=[None],
            mode='markers',
            marker=dict(size=10, color=color),
            name=status,
            showlegend=True,
        ))

    # ── Map layout ─────────────────────────────
    fig_map.update_layout(
        mapbox=dict(
            style='carto-darkmatter',
            center=dict(lat=center_lat, lon=center_lon),
            zoom=zoom_level,
        ),
        height=620,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font=dict(color='#ffffff'),
        showlegend=True,
        legend=dict(
            bgcolor='rgba(30,33,48,0.85)',
            font=dict(color='#ffffff', size=12),
            title=dict(text='Status', font=dict(color='#aaaacc')),
            x=0.01, y=0.99,
            xanchor='left', yanchor='top',
        ),
        hoverlabel=dict(
            bgcolor="#1e2130",
            font_size=12,
            font_family="Arial",
            font_color='#ffffff',
        ),
    )

    st.plotly_chart(fig_map, use_container_width=True)

else:
    st.info("No location data available for the selected filters.")

st.markdown("---")

# ─────────────────────────────────────────────
# PROJECT STATUS TABLE
# ─────────────────────────────────────────────
st.markdown("### Project Status")

table_data = filtered_df[[
    'ChfProjectCode',
    'OrganizationName',
    'ActualStartDate',
    'ActualEndDate',
    'ProjectStatus',
    'AdminLocation1',
    'Budget',
]].copy()

# Shorten agency name to initials
table_data['OrganizationName'] = table_data['OrganizationName'].apply(make_initials)

table_data.columns = ['Project', 'Agency', 'Start Date', 'End Date', 'Status', 'State', 'Total Fund']

# Date format: "14 March 2024"
table_data['Start Date'] = pd.to_datetime(table_data['Start Date']).dt.strftime('%d %B %Y')
table_data['End Date']   = pd.to_datetime(table_data['End Date']).dt.strftime('%d %B %Y')

table_data['Total Fund'] = table_data['Total Fund'].apply(
    lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A"
)

st.dataframe(
    table_data,
    use_container_width=True,
    height=400,
    hide_index=True,
    column_config={
        "Project":    st.column_config.TextColumn("Project",    width="medium"),
        "Agency":     st.column_config.TextColumn("Agency",     width="small"),
        "Start Date": st.column_config.TextColumn("Start Date", width="small"),
        "End Date":   st.column_config.TextColumn("End Date",   width="small"),
        "Status":     st.column_config.TextColumn("Status",     width="small"),
        "State":      st.column_config.TextColumn("State",      width="small"),
        "Total Fund": st.column_config.TextColumn("Total Fund", width="small"),
    },
)

csv = table_data.to_csv(index=False).encode('utf-8')
st.download_button(
    label="⬇ Download Data as CSV",
    data=csv,
    file_name=f'sudan_interventions_{start_year}_{end_year}_{datetime.now().strftime("%Y%m%d")}.csv',
    mime='text/csv',
)

st.markdown("---")

# ─────────────────────────────────────────────
# AI SUMMARY
# ─────────────────────────────────────────────
st.markdown("### Auto-Generated Data Insights")

if st.button("Generate AI Summary", type="primary", use_container_width=True):
    with st.spinner("Analysing data and generating insights…"):
        data_summary = generate_data_summary(filtered_df)

        if ai_model == "Simple Summary (No AI)":
            ai_summary = get_simple_summary(data_summary)
        elif ai_model.startswith("Ollama"):
            model_map = {
                "Ollama (llama3.2)": "llama3.2",
                "Ollama (mistral)":  "mistral",
            }
            ai_summary = get_llm_summary_ollama(data_summary, model_map.get(ai_model, "llama3.2"))
        else:
            ai_summary = get_simple_summary(data_summary)

        st.markdown(ai_summary)
else:
    st.info("Click the button above to generate an AI-powered analysis of the filtered data.")

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#8b92a8; font-size:12px;'>"
    "Sudan Intervention Dashboard | Data updated regularly"
    "</p>",
    unsafe_allow_html=True,
)