import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Production Performance Dashboard",
    layout="wide"
)

# --------------------------------------------------
# DATA LOADING (GitHub RAW)
# --------------------------------------------------
BASE_URL = "https://raw.githubusercontent.com/firmansyahr/Production-Performance-Analysis-and-Continuous-Improvement/"
BRANCH = "master"
RAW_PATH = f"{BASE_URL}{BRANCH}/data/raw/"

@st.cache_data
def load_data():
    minutely = pd.read_csv(
        RAW_PATH + "factory_data.csv",
        parse_dates=["timestamp"]
    )
    oee_day = pd.read_csv(RAW_PATH + "oee_by_day.csv")
    downtime = pd.read_csv(RAW_PATH + "downtime_pareto.csv")
    spc = pd.read_csv(RAW_PATH + "spc_xbar_r.csv")
    return minutely, oee_day, downtime, spc

df_minutely, df_oee_day, df_downtime, df_spc = load_data()

IDEAL_RATE = 6

# --------------------------------------------------
# SIDEBAR FILTER
# --------------------------------------------------
st.sidebar.header("Filters")

machine = st.sidebar.selectbox(
    "Select Machine",
    sorted(df_minutely["machine"].unique())
)

# --------------------------------------------------
# KPI CALCULATION
# --------------------------------------------------
daily_oee = (
    df_minutely[df_minutely["machine"] == machine]
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

# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------
st.title("Production Performance Dashboard")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Average OEE", f"{daily_oee['oee'].mean():.2%}")
col2.metric("Availability", f"{daily_oee['availability'].mean():.2%}")
col3.metric("Performance", f"{daily_oee['performance'].mean():.2%}")
col4.metric("Quality", f"{daily_oee['quality'].mean():.2%}")

# --------------------------------------------------
# OEE TREND
# --------------------------------------------------
st.subheader("OEE Trend")

fig, ax = plt.subplots()
ax.plot(daily_oee["day"], daily_oee["oee"], marker="o")
ax.set_xlabel("Day")
ax.set_ylabel("OEE")
ax.set_ylim(0, 1)
st.pyplot(fig)

# --------------------------------------------------
# DOWNTIME PARETO
# --------------------------------------------------
st.subheader("Downtime Pareto")

dt_machine = (
    df_downtime[df_downtime["machine"] == machine]
    .groupby("cause")["minutes"]
    .sum()
    .reset_index()
    .sort_values("minutes", ascending=False)
)

dt_machine["cum_pct"] = dt_machine["minutes"].cumsum() / dt_machine["minutes"].sum()

fig, ax1 = plt.subplots()

ax1.bar(dt_machine["cause"], dt_machine["minutes"])
ax1.set_ylabel("Downtime Minutes")
ax1.set_xticklabels(dt_machine["cause"], rotation=45)

ax2 = ax1.twinx()
ax2.plot(dt_machine["cause"], dt_machine["cum_pct"], marker="o")
ax2.axhline(0.8, linestyle="--")
ax2.set_ylabel("Cumulative %")

st.pyplot(fig)

# --------------------------------------------------
# SPC SUMMARY
# --------------------------------------------------
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

# --------------------------------------------------
# KEY INSIGHTS
# --------------------------------------------------
st.subheader("Key Insights")

st.markdown("""
- Availability is the primary contributor to OEE loss.
- Process mean and variability are statistically stable.
- Downtime losses are driven by assignable operational causes.
- Improvement efforts should focus on downtime reduction rather than process re-centering.
""")
