import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from folium.plugins import Fullscreen, MarkerCluster
from streamlit_folium import st_folium

from src.database.connection import get_connection
from src.database.crud import (
    create_traffic_sign,
    delete_traffic_sign,
    update_traffic_sign,
)
from src.database.queries import (
    query_1_streets_over_speed_limit_with_sign_count,
    query_2_damaged_signs_with_street,
    query_3_active_lights_with_intersection,
    query_4_traffic_lights_with_intersections,
    query_5_ml_with_signs,
    query_6_longest_roads_with_sign_count,
    query_7_average_road_length,
    query_8_streets_without_signs,
    query_9_signs_by_condition,
    query_10_high_confidence_ml_with_link_status,
)
from src.ml.detector import detect_image


APP_TITLE = "Katastar saobraćajne signalizacije"
MODEL_PATH = ROOT / "models" / "best.pt"
ANALYSIS_DIR = ROOT / "results" / "analysis"
UPLOADS_DIR = ROOT / "data" / "images"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_custom_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;650;700&display=swap');

        :root {
            --bg: #0b0c0e;
            --bg-alt: #101114;
            --surface: #15171a;
            --surface-hover: #1a1c20;
            --border: rgba(255, 255, 255, 0.08);
            --border-strong: rgba(255, 255, 255, 0.14);
            --text-primary: #e9eaec;
            --text-secondary: #9a9ea6;
            --text-tertiary: #6b6f77;
            --accent: #3b82f6;
            --accent-strong: #2f6fe0;
            --accent-soft: rgba(59, 130, 246, 0.12);
            --success: #22c55e;
            --warning: #d69e2e;
            --danger: #ef4444;
            --radius: 8px;
            --radius-sm: 6px;
        }

        html, body, .stApp {
            font-family: "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, Arial, sans-serif;
        }

        .stApp {
            background-color: var(--bg);
            background-image:
                radial-gradient(circle at 1px 1px, rgba(255, 255, 255, 0.09) 1.3px, transparent 0),
                radial-gradient(circle at 88% 0%, rgba(59, 130, 246, 0.16), transparent 36%),
                radial-gradient(circle at 0% 96%, rgba(139, 92, 246, 0.13), transparent 38%),
                radial-gradient(circle at 60% 38%, rgba(20, 184, 166, 0.06), transparent 48%);
            background-repeat: repeat, no-repeat, no-repeat, no-repeat;
            background-size: 24px 24px, auto, auto, auto;
            background-attachment: fixed;
            color: var(--text-primary);
        }

        * {
            scrollbar-width: thin;
            scrollbar-color: var(--border-strong) transparent;
        }

        ::-webkit-scrollbar {
            width: 9px;
            height: 9px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border-strong);
            border-radius: 999px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.22);
        }

        ::selection {
            background: rgba(59, 130, 246, 0.32);
            color: #ffffff;
        }

        a, a:visited {
            color: var(--accent);
        }

        button:focus-visible,
        input:focus-visible,
        div[tabindex]:focus-visible {
            outline: 2px solid var(--accent) !important;
            outline-offset: 1px;
        }

        input[type="checkbox"],
        input[type="radio"] {
            accent-color: var(--accent);
        }

        div[data-testid="stSlider"] div[role="slider"] {
            background-color: var(--accent) !important;
            border-color: var(--accent) !important;
        }

        div[data-testid="stSlider"] div[data-baseweb="slider"] > div > div {
            background: var(--accent) !important;
        }

        div[data-testid="stSpinner"] > div {
            border-top-color: var(--accent) !important;
        }

        @keyframes fade-in-up {
            from {
                opacity: 0;
                transform: translateY(4px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .block-container {
            max-width: 1480px;
            padding-top: 1.5rem;
            padding-bottom: 4rem;
        }

        header[data-testid="stHeader"] {
            background: var(--bg);
            border-bottom: 1px solid var(--border);
        }

        #MainMenu, footer {
            visibility: hidden;
        }

        section[data-testid="stSidebar"] {
            background-color: var(--bg-alt);
            background-image: radial-gradient(circle at 25% 0%, rgba(59, 130, 246, 0.16), transparent 42%);
            border-right: 1px solid var(--border);
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 0.8rem;
        }

        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            padding: 0.9rem 0.95rem;
            margin-bottom: 1.1rem;
            border-bottom: 1px solid var(--border);
        }

        .brand-icon {
            flex: none;
            width: 32px;
            height: 32px;
            display: grid;
            place-items: center;
            border-radius: var(--radius-sm);
            color: #ffffff;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            background: var(--accent-strong);
        }

        .brand-text {
            min-width: 0;
        }

        .brand-title {
            color: var(--text-primary);
            font-size: 0.88rem;
            font-weight: 650;
            line-height: 1.3;
        }

        .brand-subtitle {
            color: var(--text-tertiary);
            font-size: 0.72rem;
            line-height: 1.4;
        }

        div[role="radiogroup"] {
            gap: 0.05rem;
        }

        div[role="radiogroup"] > label {
            padding: 0.52rem 0.7rem !important;
            margin: 0 !important;
            border-radius: var(--radius-sm) !important;
            border-left: 2px solid transparent;
            transition: background-color 0.12s ease, border-color 0.12s ease;
        }

        div[role="radiogroup"] > label:hover {
            background: var(--surface-hover);
        }

        div[role="radiogroup"] > label:has(input:checked) {
            background: var(--accent-soft);
            border-left-color: var(--accent);
        }

        div[role="radiogroup"] > label p {
            font-size: 0.85rem !important;
            font-weight: 500;
        }

        h1, h2, h3, h4 {
            color: var(--text-primary);
            letter-spacing: -0.01em;
        }

        p, label, .stMarkdown {
            color: inherit;
        }

        .hero-card {
            position: relative;
            overflow: hidden;
            padding: 1.25rem 1.4rem;
            margin-bottom: 1.25rem;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            border-top: 2px solid var(--accent);
            background-color: var(--surface);
            animation: fade-in-up 0.35s ease;
        }

        .hero-card::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background-image:
                linear-gradient(90deg, rgba(255, 255, 255, 0.06) 1px, transparent 1px),
                linear-gradient(0deg, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
            background-size: 28px 28px;
            background-position: -1px -1px;
            -webkit-mask-image: linear-gradient(115deg, black 0%, black 38%, transparent 78%);
            mask-image: linear-gradient(115deg, black 0%, black 38%, transparent 78%);
        }

        .hero-head {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }

        .hero-icon {
            flex: none;
            width: 42px;
            height: 42px;
            display: grid;
            place-items: center;
            border-radius: 10px;
        }

        .hero-eyebrow {
            color: var(--text-tertiary);
            font-size: 0.7rem;
            font-weight: 650;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }

        .hero-title {
            color: var(--text-primary);
            font-size: clamp(1.35rem, 2.2vw, 1.7rem);
            font-weight: 650;
            line-height: 1.25;
            margin: 0;
        }

        .hero-text {
            position: relative;
            z-index: 1;
            color: var(--text-secondary);
            max-width: 860px;
            margin: 0.7rem 0 0;
            line-height: 1.6;
            font-size: 0.9rem;
        }

        .stat-card {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            height: 100%;
            padding: 0.95rem 1.05rem;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: var(--surface);
            transition: border-color 0.15s ease, transform 0.15s ease;
        }

        .stat-card:hover {
            border-color: var(--border-strong);
            transform: translateY(-1px);
        }

        .stat-icon {
            flex: none;
            width: 38px;
            height: 38px;
            display: grid;
            place-items: center;
            border-radius: 9px;
        }

        .stat-value {
            color: var(--text-primary);
            font-size: 1.35rem;
            font-weight: 650;
            line-height: 1.2;
            font-variant-numeric: tabular-nums;
        }

        .stat-label {
            color: var(--text-tertiary);
            font-size: 0.74rem;
            font-weight: 550;
            margin-top: 0.15rem;
        }

        .status-row {
            position: relative;
            z-index: 1;
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.9rem;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.32rem 0.62rem 0.32rem 0.55rem;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            border-left: 2px solid var(--border-strong);
            background: var(--bg-alt);
            color: var(--text-secondary);
            font-size: 0.75rem;
            font-weight: 500;
            transition: border-color 0.15s ease;
        }

        .status-pill:has(.dot-ok) {
            border-left-color: var(--success);
        }

        .status-pill:has(.dot-off) {
            border-left-color: var(--danger);
        }

        .dot {
            position: relative;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            flex: none;
        }

        .dot-ok {
            background: var(--success);
            box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.55);
            animation: pulse-ok 2.4s ease-out infinite;
        }

        .dot-off {
            background: var(--danger);
        }

        @keyframes pulse-ok {
            0% {
                box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.45);
            }
            70% {
                box-shadow: 0 0 0 5px rgba(34, 197, 94, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
            }
        }

        .section-heading {
            display: flex;
            align-items: end;
            justify-content: space-between;
            gap: 1rem;
            margin: 1.6rem 0 0.8rem;
            padding-bottom: 0.7rem;
            border-bottom: 1px solid var(--border);
        }

        .section-title {
            color: var(--text-primary);
            font-size: 1rem;
            font-weight: 650;
        }

        .section-copy {
            color: var(--text-tertiary);
            font-size: 0.8rem;
            margin-top: 0.15rem;
        }

        .panel-card {
            height: 100%;
            padding: 1.05rem 1.15rem;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            background: var(--surface);
            transition: border-color 0.15s ease, transform 0.15s ease;
        }

        .panel-card:hover {
            border-color: var(--border-strong);
        }

        .panel-title {
            color: var(--text-primary);
            font-size: 0.88rem;
            font-weight: 650;
            margin-bottom: 0.3rem;
        }

        .panel-copy {
            color: var(--text-secondary);
            font-size: 0.8rem;
            line-height: 1.5;
        }

        .system-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.6rem 0;
            border-bottom: 1px solid var(--border);
        }

        .system-item:last-child {
            border-bottom: none;
        }

        .system-label {
            color: var(--text-tertiary);
            font-size: 0.8rem;
        }

        .system-value {
            color: var(--text-primary);
            font-size: 0.8rem;
            font-weight: 600;
            text-align: right;
        }

        div[data-testid="stMetric"] {
            min-height: 108px;
            padding: 0.95rem 1.05rem;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: var(--surface);
            transition: border-color 0.15s ease;
        }

        div[data-testid="stMetric"]:hover {
            border-color: var(--border-strong);
        }

        div[data-testid="stMetric"] label {
            color: var(--text-tertiary) !important;
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        div[data-testid="stMetricValue"] {
            color: var(--text-primary) !important;
            font-size: 1.55rem !important;
            font-weight: 650 !important;
            font-feature-settings: "tnum" 1;
            font-variant-numeric: tabular-nums;
        }

        div[data-testid="stMetricDelta"] {
            color: var(--accent) !important;
        }

        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] > div,
        div[data-baseweb="select"] > div {
            background-color: var(--bg-alt) !important;
            border-color: var(--border-strong) !important;
            border-radius: var(--radius-sm) !important;
        }

        div[data-baseweb="input"] > div:focus-within,
        div[data-baseweb="textarea"] > div:focus-within,
        div[data-baseweb="select"] > div:focus-within {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 1px var(--accent-soft);
        }

        .stButton > button,
        div[data-testid="stFormSubmitButton"] > button,
        button[kind="primary"] {
            border: 1px solid var(--accent-strong) !important;
            border-radius: var(--radius-sm) !important;
            padding: 0.5rem 1rem !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            color: #ffffff !important;
            background: var(--accent-strong) !important;
            transition: background-color 0.12s ease, border-color 0.12s ease;
        }

        .stButton > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover {
            background: var(--accent) !important;
            border-color: var(--accent) !important;
        }

        .stButton > button:disabled,
        div[data-testid="stFormSubmitButton"] > button:disabled {
            opacity: 0.4 !important;
            cursor: not-allowed;
        }

        .stDownloadButton > button {
            border: 1px solid var(--border-strong) !important;
            border-radius: var(--radius-sm) !important;
            padding: 0.5rem 1rem !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            color: var(--text-primary) !important;
            background: transparent !important;
            transition: border-color 0.12s ease, background-color 0.12s ease;
        }

        .stDownloadButton > button:hover {
            border-color: var(--accent) !important;
            background: var(--accent-soft) !important;
            color: var(--text-primary) !important;
        }

        section[data-testid="stFileUploaderDropzone"] {
            min-height: 170px;
            display: flex;
            align-items: center;
            background: var(--bg-alt);
            border: 1px dashed var(--border-strong);
            border-radius: var(--radius);
            transition: border-color 0.15s ease;
        }

        section[data-testid="stFileUploaderDropzone"]:hover {
            border-color: var(--accent);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
        }

        div[data-testid="stDataFrame"] [role="columnheader"] {
            background: var(--bg-alt) !important;
            color: var(--text-secondary) !important;
            font-weight: 600 !important;
            font-size: 0.78rem !important;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        div[data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {
            background: var(--surface-hover) !important;
        }

        button[data-baseweb="tab"] {
            font-weight: 550;
            font-size: 0.85rem;
            color: var(--text-tertiary);
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--text-primary);
        }

        div[data-baseweb="tab-highlight"] {
            background-color: var(--accent) !important;
        }

        div[data-testid="stExpander"] {
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: var(--surface);
            transition: border-color 0.15s ease;
        }

        div[data-testid="stExpander"]:hover {
            border-color: var(--border-strong);
        }

        .sidebar-nav-label {
            color: var(--text-tertiary);
            font-size: 0.68rem;
            font-weight: 650;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding: 0 0.95rem;
            margin-bottom: 0.5rem;
        }

        div[data-testid="stAlert"] {
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
        }

        .sidebar-status {
            margin-top: 1rem;
            padding: 0.8rem 0.95rem;
            border-top: 1px solid var(--border);
        }

        .sidebar-status-title {
            color: var(--text-tertiary);
            font-size: 0.68rem;
            font-weight: 650;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.6rem;
        }

        .sidebar-status-row {
            display: flex;
            justify-content: space-between;
            gap: 0.7rem;
            color: var(--text-secondary);
            font-size: 0.78rem;
            padding: 0.28rem 0;
        }

        .sidebar-footer {
            color: var(--text-tertiary);
            font-size: 0.68rem;
            line-height: 1.5;
            margin-top: 0.6rem;
            padding: 0 0.95rem;
        }

        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .hero-card {
                padding: 1.1rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_custom_styles()


def read_dataframe(query: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def read_geodata(query: str) -> gpd.GeoDataFrame:
    conn = get_connection()
    try:
        return gpd.read_postgis(query, conn, geom_col="geom")
    finally:
        conn.close()


def database_status() -> tuple[bool, str]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT current_database();")
        database_name = cur.fetchone()[0]
        cur.close()
        conn.close()
        return True, str(database_name)
    except Exception:
        return False, "Nedostupna"


def model_status() -> tuple[bool, str]:
    if MODEL_PATH.exists():
        size_mb = MODEL_PATH.stat().st_size / (1024 * 1024)
        return True, f"{size_mb:.1f} MB"
    return False, "Nije pronađen"


ICON_STROKE = 'fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'

ICONS = {
    "dashboard": f'<svg viewBox="0 0 18 18" width="18" height="18" {ICON_STROKE}>'
    '<rect x="2.6" y="2.6" width="5.6" height="5.6" rx="1.1"/>'
    '<rect x="9.8" y="2.6" width="5.6" height="5.6" rx="1.1"/>'
    '<rect x="2.6" y="9.8" width="5.6" height="5.6" rx="1.1"/>'
    '<rect x="9.8" y="9.8" width="5.6" height="5.6" rx="1.1"/></svg>',
    "map": f'<svg viewBox="0 0 18 18" width="18" height="18" {ICON_STROKE}>'
    '<path d="M9 15.5S3.4 9.9 3.4 6.4A5.6 5.6 0 0 1 9 0.8a5.6 5.6 0 0 1 5.6 5.6c0 3.5-5.6 9.1-5.6 9.1z"/>'
    '<circle cx="9" cy="6.4" r="2"/></svg>',
    "table": f'<svg viewBox="0 0 18 18" width="18" height="18" {ICON_STROKE}>'
    '<rect x="2.5" y="3.5" width="13" height="11" rx="1.4"/>'
    '<line x1="2.5" y1="8" x2="15.5" y2="8"/>'
    '<line x1="8.7" y1="3.5" x2="8.7" y2="14.5"/></svg>',
    "crud": f'<svg viewBox="0 0 18 18" width="18" height="18" {ICON_STROKE}>'
    '<path d="M3 15.5V13l8-8 2.5 2.5-8 8H3z"/>'
    '<line x1="10" y1="4" x2="12.5" y2="6.5"/></svg>',
    "sql": f'<svg viewBox="0 0 18 18" width="18" height="18" {ICON_STROKE}>'
    '<ellipse cx="9" cy="4.5" rx="6" ry="2.2"/>'
    '<path d="M3 4.5v9c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2v-9"/>'
    '<path d="M3 9c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2"/></svg>',
    "analysis": f'<svg viewBox="0 0 18 18" width="18" height="18" {ICON_STROKE}>'
    '<path d="M9 2.5l7 3.8-7 3.8-7-3.8 7-3.8z"/>'
    '<path d="M2 10l7 3.8 7-3.8"/>'
    '<path d="M2 13.2l7 3.8 7-3.8"/></svg>',
    "ml": f'<svg viewBox="0 0 18 18" width="18" height="18" {ICON_STROKE}>'
    '<path d="M6 5l1-2h4l1 2h2.5A1.5 1.5 0 0 1 16 6.5v7A1.5 1.5 0 0 1 14.5 15h-11A1.5 1.5 0 0 1 2 13.5v-7A1.5 1.5 0 0 1 3.5 5H6z"/>'
    '<circle cx="9" cy="9.8" r="3"/></svg>',
    "road": f'<svg viewBox="0 0 18 18" width="18" height="18" {ICON_STROKE}>'
    '<path d="M6.5 2.5L3.5 15.5"/><path d="M11.5 2.5l3 13"/>'
    '<line x1="9" y1="3.5" x2="9" y2="5.5"/><line x1="9" y1="8" x2="9" y2="10"/><line x1="9" y1="12.5" x2="9" y2="14.5"/></svg>',
    "sign": f'<svg viewBox="0 0 18 18" width="18" height="18" {ICON_STROKE}>'
    '<path d="M9 2.5l7 12.5H2z"/><line x1="9" y1="7" x2="9" y2="10.5"/>'
    '<circle cx="9" cy="12.6" r="0.35" fill="currentColor" stroke="none"/></svg>',
    "light": f'<svg viewBox="0 0 18 18" width="18" height="18" {ICON_STROKE}>'
    '<rect x="6" y="2" width="6" height="14" rx="3"/>'
    '<circle cx="9" cy="5.2" r="1" fill="currentColor" stroke="none"/>'
    '<circle cx="9" cy="9" r="1" fill="currentColor" stroke="none"/>'
    '<circle cx="9" cy="12.8" r="1" fill="currentColor" stroke="none"/></svg>',
    "intersection": f'<svg viewBox="0 0 18 18" width="18" height="18" {ICON_STROKE}>'
    '<path d="M9 2v14"/><path d="M2 9h14"/>'
    '<rect x="6" y="6" width="6" height="6" rx="1"/></svg>',
}

PAGE_META = {
    "dashboard": {"icon": "dashboard", "accent": "#3b82f6", "soft": "rgba(59, 130, 246, 0.14)"},
    "map": {"icon": "map", "accent": "#14b8a6", "soft": "rgba(20, 184, 166, 0.14)"},
    "tables": {"icon": "table", "accent": "#8b5cf6", "soft": "rgba(139, 92, 246, 0.14)"},
    "crud": {"icon": "crud", "accent": "#f59e0b", "soft": "rgba(245, 158, 11, 0.14)"},
    "sql": {"icon": "sql", "accent": "#6366f1", "soft": "rgba(99, 102, 241, 0.14)"},
    "analysis": {"icon": "analysis", "accent": "#f43f5e", "soft": "rgba(244, 63, 94, 0.14)"},
    "ml": {"icon": "ml", "accent": "#06b6d4", "soft": "rgba(6, 182, 212, 0.14)"},
}


def page_header(eyebrow: str, title: str, description: str, page_key: str = "dashboard") -> None:
    db_ok, db_text = database_status()
    model_ok, model_text = model_status()

    db_class = "dot-ok" if db_ok else "dot-off"
    model_class = "dot-ok" if model_ok else "dot-off"
    meta = PAGE_META[page_key]

    st.markdown(
        f"""
        <div class="hero-card" style="border-top-color:{meta['accent']};">
            <div class="hero-head">
                <div class="hero-icon" style="background:{meta['soft']}; color:{meta['accent']};">
                    {ICONS[meta['icon']]}
                </div>
                <div>
                    <div class="hero-eyebrow" style="color:{meta['accent']};">{html.escape(eyebrow)}</div>
                    <div class="hero-title">{html.escape(title)}</div>
                </div>
            </div>
            <p class="hero-text">{html.escape(description)}</p>
            <div class="status-row">
                <span class="status-pill">
                    <span class="dot {db_class}"></span>
                    PostGIS: {html.escape(db_text)}
                </span>
                <span class="status-pill">
                    <span class="dot {model_class}"></span>
                    YOLO model: {html.escape(model_text)}
                </span>
                <span class="status-pill">200 klasa signalizacije</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(icon_key: str, accent: str, soft: str, label: str, value: str) -> str:
    return f"""
        <div class="stat-card">
            <div class="stat-icon" style="background:{soft}; color:{accent};">{ICONS[icon_key]}</div>
            <div>
                <div class="stat-value">{html.escape(value)}</div>
                <div class="stat-label">{html.escape(label)}</div>
            </div>
        </div>
        """


def section_heading(title: str, copy: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-heading">
            <div>
                <div class="section-title">{html.escape(title)}</div>
                <div class="section-copy">{html.escape(copy)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_panel(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="panel-card">
            <div class="panel-title">{html.escape(title)}</div>
            <div class="panel-copy">{html.escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_table_count(table_name: str) -> int:
    try:
        result = read_dataframe(f"SELECT COUNT(*) AS broj FROM {table_name};")
        return int(result.iloc[0]["broj"])
    except Exception:
        return 0


def dataframe_download(df: pd.DataFrame, filename: str, label: str = "Preuzmi CSV") -> None:
    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label=label,
        data=csv_data,
        file_name=filename,
        mime="text/csv",
        icon=":material/download:",
        use_container_width=True,
    )


def dashboard_page() -> None:
    page_header(
        "GIS CONTROL CENTER",
        "Pregled sistema saobraćajne signalizacije",
        "Centralizovani pregled putne infrastrukture, signalizacije, prostornih analiza i automatskih YOLO detekcija.",
        "dashboard",
    )

    counts = {
        "Ulice": get_table_count("ulice"),
        "Znakovi": get_table_count("saobracajni_znakovi"),
        "Semafori": get_table_count("semafori"),
        "Raskrsnice": get_table_count("raskrsnice"),
        "ML detekcije": get_table_count("ml_detekcije"),
    }

    stats = [
        ("road", "#3b82f6", "rgba(59, 130, 246, 0.14)", "Ulice", counts["Ulice"]),
        ("sign", "#f59e0b", "rgba(245, 158, 11, 0.14)", "Saobraćajni znakovi", counts["Znakovi"]),
        ("light", "#14b8a6", "rgba(20, 184, 166, 0.14)", "Semafori", counts["Semafori"]),
        ("intersection", "#8b5cf6", "rgba(139, 92, 246, 0.14)", "Raskrsnice", counts["Raskrsnice"]),
        ("ml", "#06b6d4", "rgba(6, 182, 212, 0.14)", "ML detekcije", counts["ML detekcije"]),
    ]
    metric_cols = st.columns(5)
    for col, (icon_key, accent, soft, label, value) in zip(metric_cols, stats):
        with col:
            st.markdown(
                stat_card(icon_key, accent, soft, label, f"{value:,}".replace(",", ".")),
                unsafe_allow_html=True,
            )

    section_heading(
        "Operativni pregled",
        "Poslednje aktivnosti, distribucija podataka i stanje sistema.",
    )

    left, right = st.columns([1.35, 0.65], gap="large")

    with left:
        st.markdown("#### Poslednje ML detekcije")
        try:
            latest_ml = read_dataframe(
                """
                SELECT id, klasa, confidence, naziv_slike, datum
                FROM ml_detekcije
                ORDER BY id DESC
                LIMIT 10;
                """
            )
            if latest_ml.empty:
                st.info("Još nema ML detekcija u bazi.")
            else:
                st.dataframe(latest_ml, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.warning(f"Podaci nisu dostupni: {exc}")

    with right:
        db_ok, db_text = database_status()
        model_ok, model_text = model_status()
        st.markdown(
            f"""
            <div class="panel-card">
                <div class="panel-title">Stanje sistema</div>
                <div class="system-item">
                    <span class="system-label">PostgreSQL / PostGIS</span>
                    <span class="system-value">{'Povezano' if db_ok else 'Nedostupno'}</span>
                </div>
                <div class="system-item">
                    <span class="system-label">Baza</span>
                    <span class="system-value">{html.escape(db_text)}</span>
                </div>
                <div class="system-item">
                    <span class="system-label">YOLO model</span>
                    <span class="system-value">{'Spreman' if model_ok else 'Nedostaje'}</span>
                </div>
                <div class="system-item">
                    <span class="system-label">Veličina modela</span>
                    <span class="system-value">{html.escape(model_text)}</span>
                </div>
                <div class="system-item">
                    <span class="system-label">Broj klasa</span>
                    <span class="system-value">200</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    chart_left, chart_right = st.columns(2, gap="large")

    with chart_left:
        st.markdown("#### Znakovi po stanju")
        try:
            condition_df = read_dataframe(
                """
                SELECT COALESCE(stanje, 'nepoznato') AS stanje, COUNT(*) AS broj
                FROM saobracajni_znakovi
                GROUP BY COALESCE(stanje, 'nepoznato')
                ORDER BY broj DESC;
                """
            )
            if condition_df.empty:
                st.info("Nema podataka za prikaz.")
            else:
                st.bar_chart(
                    condition_df.set_index("stanje"),
                    color="#f59e0b",
                    use_container_width=True,
                )
        except Exception as exc:
            st.warning(f"Grafikon nije dostupan: {exc}")

    with chart_right:
        st.markdown("#### Ulice po kategoriji")
        try:
            roads_df = read_dataframe(
                """
                SELECT COALESCE(tip_ulice, 'nepoznato') AS kategorija, COUNT(*) AS broj
                FROM ulice
                GROUP BY COALESCE(tip_ulice, 'nepoznato')
                ORDER BY broj DESC
                LIMIT 12;
                """
            )
            if roads_df.empty:
                st.info("Nema podataka za prikaz.")
            else:
                st.bar_chart(
                    roads_df.set_index("kategorija"),
                    color="#3b82f6",
                    use_container_width=True,
                )
        except Exception as exc:
            st.warning(f"Grafikon nije dostupan: {exc}")


MAP_TILES = {
    "Svetla mapa": "CartoDB positron",
    "Tamna mapa": "CartoDB dark_matter",
    "OpenStreetMap": "OpenStreetMap",
}

# folium.Icon prihvata samo ovaj fiksni skup imenovanih boja (Bootstrap/Glyphicon
# paleta) — zato se za markere nudi selectbox nad ovom listom, dok se za linijski
# sloj ulica nudi slobodan izbor boje preko color_picker (hex).
MARKER_COLOR_OPTIONS = [
    "red", "orange", "green", "purple", "blue", "darkred", "darkblue",
    "darkgreen", "cadetblue", "darkpurple", "pink", "lightblue",
    "lightgreen", "gray", "black", "beige",
]

MARKER_ICON_OPTIONS = {
    "Znak (info)": "info-sign",
    "Upozorenje": "warning-sign",
    "Zastava": "flag",
    "Zvezda": "star",
    "Semafor (ok)": "ok-sign",
    "Kamera": "camera",
}


def map_page() -> None:
    page_header(
        "SPATIAL INTELLIGENCE",
        "Interaktivna GIS mapa",
        "Pregledaj ulice, znakove, semafore, raskrsnice i ML detekcije kroz slojevitu prostornu vizualizaciju.",
        "map",
    )

    with st.expander("Podešavanja mape", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        show_roads = c1.checkbox("Ulice", True)
        show_signs = c2.checkbox("Znakovi", True)
        show_lights = c3.checkbox("Semafori", True)
        show_ml = c4.checkbox("ML detekcije", True)
        tile_label = c5.selectbox("Stil mape", list(MAP_TILES.keys()))

        p1, p2, p3 = st.columns(3)
        center_lat = p1.number_input("Centralna širina", value=45.2671, format="%.6f")
        center_lon = p2.number_input("Centralna dužina", value=19.8335, format="%.6f")
        zoom = p3.slider("Početni zoom", 5, 18, 13)

    with st.expander("Podešavanja simbologije (boje i stil slojeva)", expanded=False):
        st.caption(
            "Izgled svakog sloja je moguće prilagoditi nezavisno. Za linijski sloj "
            "ulica bira se proizvoljna boja i debljina linije; za tačkaste slojeve "
            "bira se boja markera iz dostupne palete i ikonica."
        )

        st.markdown("**Ulice**")
        r1, r2, r3 = st.columns(3)
        roads_color = r1.color_picker("Boja linije", "#38bdf8")
        roads_weight = r2.slider("Debljina linije", 1.0, 8.0, 2.4, 0.2)
        roads_opacity = r3.slider("Providnost linije", 0.1, 1.0, 0.66, 0.05)

        st.markdown("**Saobraćajni znakovi**")
        s1, s2, s3 = st.columns(3)
        signs_color = s1.selectbox(
            "Boja markera", MARKER_COLOR_OPTIONS,
            index=MARKER_COLOR_OPTIONS.index("orange"), key="signs_color",
        )
        signs_icon_label = s2.selectbox(
            "Ikonica", list(MARKER_ICON_OPTIONS.keys()), index=0, key="signs_icon",
        )
        highlight_stop = s3.checkbox(
            "Posebno istakni STOP znakove (crveno)", value=True, key="signs_highlight_stop",
        )

        st.markdown("**Semafori**")
        l1, l2 = st.columns(2)
        lights_color = l1.selectbox(
            "Boja markera", MARKER_COLOR_OPTIONS,
            index=MARKER_COLOR_OPTIONS.index("green"), key="lights_color",
        )
        lights_icon_label = l2.selectbox(
            "Ikonica", list(MARKER_ICON_OPTIONS.keys()), index=4, key="lights_icon",
        )

        st.markdown("**ML detekcije**")
        m1, m2 = st.columns(2)
        ml_color = m1.selectbox(
            "Boja markera", MARKER_COLOR_OPTIONS,
            index=MARKER_COLOR_OPTIONS.index("purple"), key="ml_color",
        )
        ml_icon_label = m2.selectbox(
            "Ikonica", list(MARKER_ICON_OPTIONS.keys()), index=5, key="ml_icon",
        )

        signs_icon = MARKER_ICON_OPTIONS[signs_icon_label]
        lights_icon = MARKER_ICON_OPTIONS[lights_icon_label]
        ml_icon = MARKER_ICON_OPTIONS[ml_icon_label]

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles=MAP_TILES[tile_label],
        control_scale=True,
    )
    Fullscreen(position="topright").add_to(m)

    loaded = []

    if show_roads:
        try:
            roads = read_geodata(
                """
                SELECT id, naziv, tip_ulice, ogranicenje_brzine, duzina_km,
                       ST_SimplifyPreserveTopology(geom, 0.00005) AS geom
                FROM ulice
                WHERE geom IS NOT NULL;
                """
            )
            if not roads.empty:
                folium.GeoJson(
                    roads,
                    name="Ulice",
                    tooltip=folium.GeoJsonTooltip(
                        fields=["naziv", "tip_ulice", "ogranicenje_brzine"],
                        aliases=["Naziv:", "Tip:", "Ograničenje:"],
                    ),
                    style_function=lambda _feature, _c=roads_color, _w=roads_weight, _o=roads_opacity: {
                        "color": _c,
                        "weight": _w,
                        "opacity": _o,
                    },
                ).add_to(m)
                loaded.append(f"Ulice: {len(roads)}")
        except Exception as exc:
            st.warning(f"Sloj ulica nije učitan: {exc}")

    if show_signs:
        try:
            signs = read_geodata(
                """
                SELECT id, tip_znaka, opis, stanje, geom
                FROM saobracajni_znakovi
                WHERE geom IS NOT NULL;
                """
            )
            sign_group = folium.FeatureGroup(name="Saobraćajni znakovi")
            sign_cluster = MarkerCluster(name="Znakovi - klasteri").add_to(sign_group)
            for _, row in signs.iterrows():
                if row.geom is None:
                    continue
                sign_type = str(row.get("tip_znaka", "nepoznato"))
                marker_color = "red" if (highlight_stop and sign_type.lower() == "stop") else signs_color
                popup = (
                    f"<b>Saobraćajni znak</b><br>"
                    f"<b>Tip:</b> {html.escape(sign_type)}<br>"
                    f"<b>Opis:</b> {html.escape(str(row.get('opis', '')))}<br>"
                    f"<b>Stanje:</b> {html.escape(str(row.get('stanje', '')))}"
                )
                folium.Marker(
                    location=[row.geom.y, row.geom.x],
                    popup=popup,
                    tooltip=sign_type,
                    icon=folium.Icon(color=marker_color, icon=signs_icon),
                ).add_to(sign_cluster)
            sign_group.add_to(m)
            loaded.append(f"Znakovi: {len(signs)}")
        except Exception as exc:
            st.warning(f"Sloj znakova nije učitan: {exc}")

    if show_lights:
        try:
            lights = read_geodata(
                """
                SELECT id, status, tip, geom
                FROM semafori
                WHERE geom IS NOT NULL;
                """
            )
            light_group = folium.FeatureGroup(name="Semafori")
            light_cluster = MarkerCluster(name="Semafori - klasteri").add_to(light_group)
            for _, row in lights.iterrows():
                if row.geom is None:
                    continue
                popup = (
                    "<b>Semafor</b><br>"
                    f"<b>Status:</b> {html.escape(str(row.get('status', '')))}<br>"
                    f"<b>Tip:</b> {html.escape(str(row.get('tip', '')))}"
                )
                folium.Marker(
                    location=[row.geom.y, row.geom.x],
                    popup=popup,
                    tooltip="Semafor",
                    icon=folium.Icon(color=lights_color, icon=lights_icon),
                ).add_to(light_cluster)
            light_group.add_to(m)
            loaded.append(f"Semafori: {len(lights)}")
        except Exception as exc:
            st.warning(f"Sloj semafora nije učitan: {exc}")

    if show_ml:
        try:
            ml_data = read_geodata(
                """
                SELECT id, klasa, confidence, naziv_slike, datum, geom
                FROM ml_detekcije
                WHERE geom IS NOT NULL
                ORDER BY id DESC;
                """
            )
            ml_group = folium.FeatureGroup(name="ML detekcije")
            ml_cluster = MarkerCluster(name="ML - klasteri").add_to(ml_group)
            for _, row in ml_data.iterrows():
                if row.geom is None:
                    continue
                popup = (
                    "<b>YOLO detekcija</b><br>"
                    f"<b>Klasa:</b> {html.escape(str(row.get('klasa', '')))}<br>"
                    f"<b>Pouzdanost:</b> {float(row.get('confidence', 0)):.1%}<br>"
                    f"<b>Slika:</b> {html.escape(str(row.get('naziv_slike', '')))}<br>"
                    f"<b>Datum:</b> {html.escape(str(row.get('datum', '')))}"
                )
                folium.Marker(
                    location=[row.geom.y, row.geom.x],
                    popup=popup,
                    tooltip=f"ML: {row.get('klasa', '')}",
                    icon=folium.Icon(color=ml_color, icon=ml_icon),
                ).add_to(ml_cluster)
            ml_group.add_to(m)
            loaded.append(f"ML: {len(ml_data)}")
        except Exception as exc:
            st.warning(f"Sloj ML detekcija nije učitan: {exc}")

    folium.LayerControl(collapsed=False).add_to(m)

    if loaded:
        st.caption(" • ".join(loaded))

    st_folium(
        m,
        height=720,
        use_container_width=True,
        returned_objects=[],
        key="traffic_map",
    )


TABLES = {
    "Ulice": "ulice",
    "Saobraćajni znakovi": "saobracajni_znakovi",
    "Semafori": "semafori",
    "Raskrsnice": "raskrsnice",
    "ML detekcije": "ml_detekcije",
}


def tables_page() -> None:
    page_header(
        "DATA EXPLORER",
        "Pregled baze podataka",
        "Pretražuj, filtriraj i izvozi podatke iz ključnih tabela katastra saobraćajne signalizacije.",
        "tables",
    )

    controls = st.columns([1.2, 1.4, 0.7])
    label = controls[0].selectbox("Tabela", list(TABLES.keys()))
    search_term = controls[1].text_input("Pretraga u rezultatima", placeholder="Unesi pojam...")
    limit = controls[2].selectbox("Broj redova", [50, 100, 200, 500], index=2)

    table_name = TABLES[label]
    try:
        df = read_dataframe(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT {int(limit)};")
    except Exception as exc:
        st.error(f"Tabela nije dostupna: {exc}")
        return

    if search_term:
        mask = df.astype(str).apply(
            lambda column: column.str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        df = df.loc[mask]

    m1, m2, m3 = st.columns(3)
    m1.metric("Prikazano redova", len(df))
    m2.metric("Broj kolona", len(df.columns))
    m3.metric("Izabrana tabela", label)

    st.dataframe(df, use_container_width=True, hide_index=True, height=560)
    dataframe_download(df, f"{table_name}.csv", "Preuzmi prikazane podatke")


CONDITION_OPTIONS = ["dobro", "ostecen", "potrebno odrzavanje"]


def crud_page() -> None:
    page_header(
        "ASSET MANAGEMENT",
        "Upravljanje saobraćajnim znakovima",
        "Dodaj nove elemente katastra, ažuriraj njihovo stanje ili ukloni nevažeće zapise iz sistema.",
        "crud",
    )

    tab_add, tab_edit, tab_delete = st.tabs(
        [
            ":material/add_circle: Dodaj znak",
            ":material/edit: Izmeni znak",
            ":material/delete: Obriši znak",
        ]
    )

    with tab_add:
        left, right = st.columns([1.15, 0.85], gap="large")
        with left:
            with st.form("add_sign_form", clear_on_submit=False):
                st.markdown("#### Osnovni podaci")
                tip = st.text_input("Tip znaka", "rucno_dodat_znak")
                opis = st.text_area("Opis", "Ručno dodat znak kroz aplikaciju")
                stanje = st.selectbox("Stanje", CONDITION_OPTIONS)
                proizvodjac = st.text_input("Proizvođač", "Korisnički unos")

                c1, c2 = st.columns(2)
                lon = c1.number_input("Geografska dužina", value=19.8335, format="%.6f")
                lat = c2.number_input("Geografska širina", value=45.2671, format="%.6f")

                submitted = st.form_submit_button(
                    "Dodaj znak u katastar",
                    icon=":material/add:",
                    use_container_width=True,
                )

            if submitted:
                try:
                    create_traffic_sign(tip, opis, stanje, proizvodjac, lon, lat)
                    st.success("Znak je uspešno dodat u katastar.")
                except Exception as exc:
                    st.error(f"Dodavanje nije uspelo: {exc}")

        with right:
            info_panel(
                "Kontrolisan unos",
                "Svaki znak dobija opisne atribute i geografsku lokaciju u koordinatnom sistemu EPSG:4326.",
            )
            st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=13)

    with tab_edit:
        with st.form("edit_sign_form"):
            st.markdown("#### Ažuriranje stanja")
            sign_id = st.number_input("ID znaka", min_value=1, step=1)
            novo_stanje = st.selectbox("Novo stanje", CONDITION_OPTIONS, key="edit_condition")
            submitted = st.form_submit_button(
                "Sačuvaj izmene", icon=":material/save:", use_container_width=True
            )

        if submitted:
            try:
                update_traffic_sign(sign_id, novo_stanje)
                st.success("Podaci o znaku su uspešno ažurirani.")
            except Exception as exc:
                st.error(f"Izmena nije uspela: {exc}")

    with tab_delete:
        st.warning("Brisanje je trajna operacija. Proveri ID pre potvrde.")
        with st.form("delete_sign_form"):
            delete_id = st.number_input("ID znaka za brisanje", min_value=1, step=1)
            confirmation = st.checkbox("Potvrđujem da želim da obrišem ovaj zapis")
            submitted = st.form_submit_button(
                "Trajno obriši znak", icon=":material/delete_forever:", use_container_width=True
            )

        if submitted:
            if not confirmation:
                st.error("Potrebno je potvrditi brisanje.")
            else:
                try:
                    delete_traffic_sign(delete_id)
                    st.success("Znak je obrisan iz baze.")
                except Exception as exc:
                    st.error(f"Brisanje nije uspelo: {exc}")


QUERY_DEFINITIONS = {
    "Ulice sa ograničenjem > 50 km/h i broj znakova": {
        "function": query_1_streets_over_speed_limit_with_sign_count,
        "description": "JOIN ulice + saobraćajni znakovi: saobraćajnice sa višim ograničenjem i broj znakova na njima.",
    },
    "Oštećeni znakovi sa ulicom": {
        "function": query_2_damaged_signs_with_street,
        "description": "JOIN znakovi + ulice: znakovi koji nisu u dobrom stanju, sa nazivom ulice.",
    },
    "Aktivni semafori sa raskrsnicom": {
        "function": query_3_active_lights_with_intersection,
        "description": "JOIN semafori + raskrsnice: aktivni semafori i naziv pripadajuće raskrsnice.",
    },
    "Semafori na kontrolisanim raskrsnicama": {
        "function": query_4_traffic_lights_with_intersections,
        "description": "JOIN semafori + raskrsnice filtrirano po tipu raskrsnice.",
    },
    "Povezivanje ML detekcija i znakova": {
        "function": query_5_ml_with_signs,
        "description": "JOIN ML detekcije + znakovi: poredi automatske detekcije sa postojećim zapisima katastra.",
    },
    "Najduže ulice i broj znakova": {
        "function": query_6_longest_roads_with_sign_count,
        "description": "JOIN ulice + znakovi: rangira ulice prema dužini i broju znakova na njima.",
    },
    "Prosečna dužina po kategoriji": {
        "function": query_7_average_road_length,
        "description": "Računa prosečnu dužinu ulica po kategoriji.",
    },
    "Ulice bez evidentiranih znakova": {
        "function": query_8_streets_without_signs,
        "description": "Anti-join ulice + znakovi: glavne ulice koje još nemaju nijedan evidentiran znak.",
    },
    "Broj znakova po stanju": {
        "function": query_9_signs_by_condition,
        "description": "Analizira stanje elemenata vertikalne signalizacije.",
    },
    "ML detekcije visoke pouzdanosti": {
        "function": query_10_high_confidence_ml_with_link_status,
        "description": "LEFT JOIN ML detekcije + znakovi: detekcije sa confidence > 0.85 i status povezanosti sa katastrom.",
    },
}


def sql_queries_page() -> None:
    page_header(
        "QUERY LAB",
        "SQL analitički centar",
        "Pokreni pripremljene poslovne i prostorne upite nad PostgreSQL/PostGIS bazom podataka.",
        "sql",
    )

    selected = st.selectbox("Izaberi analizu", list(QUERY_DEFINITIONS.keys()))
    definition = QUERY_DEFINITIONS[selected]
    info_panel("Opis upita", definition["description"])

    if st.button("Pokreni SQL upit", icon=":material/play_arrow:", use_container_width=True):
        try:
            with st.spinner("Izvršavanje upita..."):
                st.session_state["sql_result"] = definition["function"]()
                st.session_state["sql_result_name"] = selected
        except Exception as exc:
            st.error(f"Upit nije izvršen: {exc}")

    result = st.session_state.get("sql_result")
    result_name = st.session_state.get("sql_result_name")

    if isinstance(result, pd.DataFrame) and result_name == selected:
        st.metric("Broj rezultata", len(result))
        st.dataframe(result, use_container_width=True, hide_index=True, height=520)
        dataframe_download(result, "sql_rezultat.csv")


ANALYSIS_FILES = {
    "Najbliža ulica za svaki znak": "znakovi_najbliza_ulica.csv",
    "Znakovi u blizini semafora": "znakovi_u_blizini_semafora.csv",
    "Broj znakova po tipu": "broj_znakova_po_tipu.csv",
    "Semafori u blizini raskrsnica": "semafori_u_blizini_raskrsnica.csv",
    "ML detekcije naspram katastra": "ml_detekcije_vs_katastar.csv",
    "Znakovi na glavnim putevima": "overlay_intersection_znakovi_glavni_putevi.csv",
    "Ulice van pokrivenosti signalizacije": "overlay_difference_ulice_van_signalizacije.csv",
}


def analysis_page() -> None:
    page_header(
        "SPATIAL ANALYTICS",
        "Rezultati prostornih analiza",
        "Pregled gotovih GeoPandas analiza, prostornih spojeva, buffer operacija i overlay rezultata.",
        "analysis",
    )

    selected_label = st.selectbox("Izaberi rezultat", list(ANALYSIS_FILES.keys()))
    selected_path = ANALYSIS_DIR / ANALYSIS_FILES[selected_label]

    if not selected_path.exists():
        st.warning(
            "Rezultat još nije generisan. Pokreni spatial_analysis.py i overlay_analysis.py."
        )
        return

    try:
        df = pd.read_csv(selected_path)
    except Exception as exc:
        st.error(f"Fajl nije moguće pročitati: {exc}")
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Broj redova", len(df))
    m2.metric("Broj kolona", len(df.columns))
    m3.metric("Format", "CSV")

    st.dataframe(df, use_container_width=True, hide_index=True, height=570)
    dataframe_download(df, selected_path.name, "Preuzmi rezultat analize")


ML_HISTORY_QUERY = """
    SELECT id, klasa, confidence, naziv_slike, datum, model, opis
    FROM ml_detekcije
    ORDER BY id DESC
    LIMIT 200;
"""


def ml_page() -> None:
    page_header(
        "COMPUTER VISION",
        "AI detekcija saobraćajnih znakova",
        "Analiziraj fotografije modelom treniranim od nule, evidentiraj detekcije i poveži ih sa geografskom lokacijom.",
        "ml",
    )

    tab_detect, tab_history, tab_correct = st.tabs(
        [
            ":material/smart_toy: Nova detekcija",
            ":material/history: Istorija detekcija",
            ":material/build: Korekcija zapisa",
        ]
    )

    with tab_detect:
        model_ok, model_text = model_status()
        if not model_ok:
            st.error(
                "Model nije pronađen. Očekivana putanja je models/best.pt."
            )

        left, right = st.columns([1.35, 0.65], gap="large")

        with left:
            st.markdown("#### Ulazna fotografija")
            uploaded_file = st.file_uploader(
                "Prevuci fotografiju ili izaberi fajl",
                type=["jpg", "jpeg", "png"],
                label_visibility="collapsed",
            )

        with right:
            st.markdown("#### Parametri detekcije")
            lon = st.number_input(
                "Geografska dužina",
                value=19.8335,
                format="%.6f",
                key="ml_lon",
            )
            lat = st.number_input(
                "Geografska širina",
                value=45.2671,
                format="%.6f",
                key="ml_lat",
            )
            min_conf = st.slider(
                "Minimalna pouzdanost",
                min_value=0.0,
                max_value=1.0,
                value=0.25,
                step=0.05,
            )
            run_detection = st.button(
                "Pokreni AI detekciju",
                icon=":material/bolt:",
                use_container_width=True,
                disabled=not model_ok,
            )

        image_path = None
        if uploaded_file is not None:
            UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            safe_name = Path(uploaded_file.name).name
            image_path = UPLOADS_DIR / safe_name
            image_path.write_bytes(uploaded_file.getbuffer())

            preview, metadata = st.columns([1.35, 0.65], gap="large")
            with preview:
                st.image(
                    str(image_path),
                    caption="Ulazna fotografija",
                    use_container_width=True,
                )
            with metadata:
                st.markdown(
                    f"""
                    <div class="panel-card">
                        <div class="panel-title">Podaci o zadatku</div>
                        <div class="system-item">
                            <span class="system-label">Fajl</span>
                            <span class="system-value">{html.escape(safe_name)}</span>
                        </div>
                        <div class="system-item">
                            <span class="system-label">Lokacija</span>
                            <span class="system-value">{lat:.5f}, {lon:.5f}</span>
                        </div>
                        <div class="system-item">
                            <span class="system-label">Prag</span>
                            <span class="system-value">{min_conf:.0%}</span>
                        </div>
                        <div class="system-item">
                            <span class="system-label">Model</span>
                            <span class="system-value">{html.escape(model_text)}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if run_detection:
            if image_path is None:
                st.warning("Prvo učitaj fotografiju.")
            else:
                try:
                    with st.spinner("YOLO model analizira fotografiju..."):
                        detections = detect_image(
                            image_path,
                            lon,
                            lat,
                            min_confidence=min_conf,
                        )
                    st.session_state["last_detections"] = detections
                except Exception as exc:
                    st.error(f"Detekcija nije uspela: {exc}")

        detections = st.session_state.get("last_detections", [])
        if detections:
            st.success(f"Detekcija završena. Pronađeno objekata: {len(detections)}")

            result_left, result_right = st.columns([1.2, 0.8], gap="large")
            with result_left:
                result_path = detections[0].get("rezultat")
                if result_path and Path(result_path).exists():
                    st.image(
                        result_path,
                        caption="Rezultat detekcije",
                        use_container_width=True,
                    )
            with result_right:
                detection_df = pd.DataFrame(detections)
                avg_conf = detection_df["confidence"].mean() if "confidence" in detection_df else 0
                c1, c2 = st.columns(2)
                c1.metric("Detektovani objekti", len(detection_df))
                c2.metric("Prosečan confidence", f"{avg_conf:.1%}")
                st.dataframe(
                    detection_df,
                    use_container_width=True,
                    hide_index=True,
                    height=360,
                )

    with tab_history:
        try:
            ml_df = read_dataframe(ML_HISTORY_QUERY)
        except Exception as exc:
            st.error(f"Istorija nije dostupna: {exc}")
            ml_df = pd.DataFrame()

        if ml_df.empty:
            st.info("Još nema sačuvanih ML detekcija.")
        else:
            h1, h2, h3 = st.columns(3)
            h1.metric("Ukupno prikazano", len(ml_df))
            h2.metric("Prosečan confidence", f"{ml_df['confidence'].mean():.1%}")
            h3.metric("Broj klasa", ml_df["klasa"].nunique())

            filter_text = st.text_input(
                "Filtriraj istoriju",
                placeholder="Klasa, naziv slike, model...",
            )
            filtered = ml_df
            if filter_text:
                mask = ml_df.astype(str).apply(
                    lambda column: column.str.contains(filter_text, case=False, na=False)
                ).any(axis=1)
                filtered = ml_df.loc[mask]

            st.dataframe(filtered, use_container_width=True, hide_index=True, height=540)
            dataframe_download(filtered, "ml_detekcije.csv")

    with tab_correct:
        info_panel(
            "Ručna verifikacija",
            "Koriguj klasu, confidence ili opis automatske detekcije nakon stručne provere rezultata.",
        )
        with st.form("edit_ml_detection_form"):
            det_id = st.number_input("ID ML detekcije", min_value=1, step=1)
            nova_klasa = st.text_input("Nova klasa")
            novi_conf = st.number_input(
                "Novi confidence",
                min_value=0.0,
                max_value=1.0,
                value=0.90,
                step=0.01,
            )
            novi_opis = st.text_area("Novi opis", "Ručno verifikovana ML detekcija")
            submitted = st.form_submit_button(
                "Sačuvaj korekciju", icon=":material/save:", use_container_width=True
            )

        if submitted:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE ml_detekcije
                    SET klasa = %s,
                        confidence = %s,
                        opis = %s
                    WHERE id = %s;
                    """,
                    (nova_klasa, novi_conf, novi_opis, det_id),
                )
                conn.commit()
                cur.close()
                conn.close()
                st.success("Atributi ML detekcije su uspešno izmenjeni.")
            except Exception as exc:
                st.error(f"Korekcija nije uspela: {exc}")


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="brand-icon">KS</div>
                <div class="brand-text">
                    <div class="brand-title">Katastar signalizacije</div>
                    <div class="brand-subtitle">GIS evidencija i AI detekcija</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        navigation = {
            ":material/space_dashboard: Dashboard": "Dashboard",
            ":material/map: Interaktivna mapa": "Mapa",
            ":material/table_chart: Pregled tabela": "Tabele",
            ":material/edit_square: Upravljanje znakovima": "CRUD",
            ":material/database: SQL analitika": "SQL upiti",
            ":material/layers: Prostorne analize": "Prostorne analize",
            ":material/photo_camera: AI detekcija": "ML detekcija",
        }

        st.markdown('<div class="sidebar-nav-label">Navigacija</div>', unsafe_allow_html=True)
        selected_label = st.radio(
            "Navigacija",
            list(navigation.keys()),
            label_visibility="collapsed",
        )

        db_ok, db_text = database_status()
        model_ok, model_text = model_status()
        st.markdown(
            f"""
            <div class="sidebar-status">
                <div class="sidebar-status-title">Status platforme</div>
                <div class="sidebar-status-row">
                    <span>Baza</span>
                    <strong>{'Online' if db_ok else 'Offline'}</strong>
                </div>
                <div class="sidebar-status-row">
                    <span>Model</span>
                    <strong>{'Spreman' if model_ok else 'Nedostaje'}</strong>
                </div>
                <div class="sidebar-status-row">
                    <span>Klase</span>
                    <strong>200</strong>
                </div>
            </div>
            <div class="sidebar-footer">
                PostgreSQL • PostGIS • GeoPandas • Folium • YOLOv8
            </div>
            """,
            unsafe_allow_html=True,
        )

        return navigation[selected_label]


def main() -> None:
    page = render_sidebar()

    pages = {
        "Dashboard": dashboard_page,
        "Mapa": map_page,
        "Tabele": tables_page,
        "CRUD": crud_page,
        "SQL upiti": sql_queries_page,
        "Prostorne analize": analysis_page,
        "ML detekcija": ml_page,
    }

    pages[page]()


if __name__ == "__main__":
    main()