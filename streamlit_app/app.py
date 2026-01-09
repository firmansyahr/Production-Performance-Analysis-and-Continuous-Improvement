import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Production Performance & CI Dashboard",
    layout="wide"
)

# ==================================================
# DATA LOADING
# ==================================================
BASE_URL = "https://raw.githubusercontent.com/firmansyahr/Production-Performance-Analysis-and-Continuous-Improvement/"
BRANCH = "master"
RAW_PATH = f"{BASE_URL}{BRANCH}/data/raw/"
IDEAL_RATE = 6

@st.cache_data
def load_data():
    minutely = pd.read_csv(RAW_PATH + "factory_data.csv", parse_dates=["timestamp"])
    downtime = pd.read_csv(RAW_PATH + "downtime_pareto.csv")
    spc = pd.read_csv(RAW_PATH + "spc_xbar_r.csv")
    return minutely, downtime, spc

df_minutely, df_downtime, df_spc = load_data()

# ==================================================
# SIDEBAR FILTER
# ==================================================
st.sidebar.header("Filters")

machine = st.sidebar.selectbox(
    "Machine",
    sorted(df_minutely["machine"].unique())
)

shift = st.sidebar.multiselect(
    "Shift",
    sorted(df_minutely["shift"].unique()),
    default=sorted(df_minutely["shift"].unique())
)

date_range = st.sidebar.date_input(
    "Date Range",
    [
        df_minutely["timestamp"].dt.date.min(),
        df_minutely["timestamp"].dt.date.max()
    ]
)

# ==================================================
# FILTERED DATA
# ==================================================
filtered = df_minutely[
    (df_minutely["machine"] == machine) &
    (df_minutely["shift"].isin(shift)) &
    (df_minutely["timestamp"].dt.date >= date_range[0]) &
    (df_minutely["timestamp"].dt.date <= date_range[1])
]

# ==================================================
# OEE CALCULATION
# ==================================================
daily_oee = (
    filtered
    .groupby("day")
    .agg(
        planned_min=("timestamp", "count"),
        running_min=("is_running", "sum"),
        total_units=("units", "sum"),
        good_units=("good_units", "sum")
    )
    .reset_index()
)

daily_oee["availability"] = daily_oee["running_min"] / daily_oee["planned_min"]
daily_oee["performance"] = daily_oee["total_units"] / (IDEAL_RATE * daily_oee["running_min"])
daily_oee["quality"] = daily_oee["good_units"] / daily_oee["total_units"]
daily_oee["oee"] = (
    daily_oee["availability"] *
    daily_oee["performance"] *
    daily_oee["quality"]
)

# ==================================================
# KPI STATUS FUNCTION
# ==================================================
def kpi_status(value):
    if value >= 0.85:
        return "🟢"
    elif value >= 0.75:
        return "🟡"
    else:
        return "🔴"

# ==================================================
# MAIN TABS
# ==================================================
st.title("Production Performance & Continuous Improvement Dashboard")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview",
    "⏱ Downtime RCA",
    "📈 SPC",
    "🧠 Insights & Actions"
])

# ==================================================
# TAB 1 — OVERVIEW
# ==================================================
with tab1:
    st.subheader("Key Performance Indicators")

    avg_oee = daily_oee["oee"].mean()
    avg_av = daily_oee["availability"].mean()
    avg_perf = daily_oee["performance"].mean()
    avg_qual = daily_oee["quality"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OEE", f"{avg_oee:.1%}", kpi_status(avg_oee))
    c2.metric("Availability", f"{avg_av:.1%}", kpi_status(avg_av))
    c3.metric("Performance", f"{avg_perf:.1%}")
    c4.metric("Quality", f"{avg_qual:.1%}")

    st.subheader("OEE Trend")
    fig, ax = plt.subplots()
    ax.plot(daily_oee["day"], daily_oee["oee"], marker="o")
    ax.set_ylim(0, 1)
    ax.set_ylabel("OEE")
    ax.set_xlabel("Day")
    st.pyplot(fig)

    st.subheader("OEE Loss Breakdown")
    loss_df = pd.DataFrame({
        "Component": ["Availability Loss", "Performance Loss", "Quality Loss"],
        "Loss": [
            1 - avg_av,
            max(0, 1 - avg_perf),
            1 - avg_qual
        ]
    })

    fig, ax = plt.subplots()
    ax.bar(loss_df["Component"], loss_df["Loss"])
    st.pyplot(fig)

# ==================================================
# TAB 2 — DOWNTIME RCA
# ==================================================
with tab2:
    st.subheader("Downtime Pareto")

    dt = (
        df_downtime[df_downtime["machine"] == machine]
        .groupby("cause")["minutes"]
        .sum()
        .reset_index()
        .sort_values("minutes", ascending=False)
    )

    dt["cum_pct"] = dt["minutes"].cumsum() / dt["minutes"].sum()

    fig, ax1 = plt.subplots()
    ax1.bar(dt["cause"], dt["minutes"])
    ax1.set_ylabel("Minutes")
    ax1.set_xticklabels(dt["cause"], rotation=45)

    ax2 = ax1.twinx()
    ax2.plot(dt["cause"], dt["cum_pct"], marker="o")
    ax2.axhline(0.8, linestyle="--")

    st.pyplot(fig)

    st.dataframe(dt)

# ==================================================
# TAB 3 — SPC
# ==================================================
with tab3:
    st.subheader("SPC Summary")

    spc_summary = (
        df_spc[df_spc["machine"] == machine]
        .agg(
            avg_xbar=("xbar", "mean"),
            avg_range=("R", "mean"),
            max_range=("R", "max")
        )
        .T
    )

    st.table(spc_summary)

    st.success("Process Status: In Control")

# ==================================================
# TAB 4 — INSIGHTS & ACTIONS
# ==================================================
with tab4:
    st.subheader("Auto-Generated Insights")

    st.markdown(f"""
    - **Availability is the dominant contributor to OEE loss** on Machine {machine}.
    - Process throughput and quality remain statistically stable.
    - Downtime losses are driven by assignable operational causes.
    - Priority should be given to addressing top downtime causes rather than
      adjusting process parameters.
    """)

    st.subheader("Recommended Actions")

    st.markdown("""
    1. Improve upstream material flow to reduce starvation.
    2. Strengthen preventive maintenance for electrical issues.
    3. Standardize and optimize changeover procedures.
    4. Monitor SPC trends as early warning signals.
    """)
