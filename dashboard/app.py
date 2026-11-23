"""Streamlit dashboard: passenger view, control room, model performance."""
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

API = "http://localhost:8000"

st.set_page_config(page_title="Rail ETA — SIH26028", layout="wide")
st.markdown("""
<style>
    .big {font-size: 2.2rem; font-weight: 700; color: #0B3D91;}
    .metric-card {background:#F4F6F9; border-radius:12px; padding:14px;}
</style>
""", unsafe_allow_html=True)

st.title("🚆 Dynamic Train Arrival Forecasting")
st.caption("SIH26028 · Ministry of Railways · Quantile ETA model with live simulation")

@st.cache_data(ttl=2)
def api_get(path):
    try:
        r = requests.get(f"{API}{path}", timeout=10)
        return r.json() if r.ok else {"error": "Backend Error"}
    except Exception as e:
        return {"error": str(e)}

trains = api_get("/trains")
if isinstance(trains, dict) and trains.get("error"):
    st.error("Backend not reachable. Start `uvicorn api.main:app --reload` first.")
    st.stop()

train_map = {t["train_no"]: f'{t["train_no"]} — {t["name"]}' for t in trains}

with st.sidebar:
    st.header("Controls")
    selected = st.selectbox("Train", list(train_map), format_func=lambda x: train_map[x])
    c1, c2 = st.columns(2)
    if c1.button("▶ Start", use_container_width=True):
        requests.post(f"{API}/simulate/start/{selected}")
        st.rerun()
    if c2.button("⏭ Tick", use_container_width=True):
        requests.post(f"{API}/simulate/tick")
        st.rerun()
    incident_min = st.slider("Incident minutes", 0, 180, 60, 15)
    if st.button("⚠ Inject incident", use_container_width=True):
        requests.post(f"{API}/simulate/incident/{selected}?minutes={incident_min}")
        st.rerun()
    st.divider()
    st.caption("Tick advances every active train by one station interval.")

# Fetch data (backend auto-starts if not running)
live = api_get(f"/live/{selected}")
predict = api_get(f"/predict/{selected}")
backtest = api_get("/backtest")
schedule = api_get(f"/schedule/{selected}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current station", live.get("current_station", "—"))
col2.metric("Delay", f'{live.get("current_delay", 0):.0f} min')
col3.metric("Next station", live.get("next_station") or "—")
col4.metric("Status", live.get("status", "—"))

tab_pass, tab_control, tab_model = st.tabs(
    ["👤 Passenger view", "🎛 Control room", "📊 Model performance"]
)

# ---------------- Passenger view ----------------
with tab_pass:
    if "predictions" not in predict:
        st.info("Start the simulation to see predictions.")
    else:
        st.subheader(f'{predict["train_name"]} · live ETA')
        df = pd.DataFrame(predict["predictions"])
        
        # Build the Plotly chart
        y = list(df["station_code"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=y, y=df["baseline_eta_min"], mode="lines+markers",
            name="Baseline (schedule + delay)", line=dict(dash="dot", color="#999"),
        ))
        fig.add_trace(go.Scatter(
            x=y, y=df["pred_eta_min"], mode="lines+markers",
            name="ML point ETA", line=dict(color="#0B3D91", width=3),
        ))
        fig.add_trace(go.Scatter(
            x=y + y[::-1],
            y=list(df["upper_eta_min"]) + list(df["lower_eta_min"][::-1]),
            fill="toself", fillcolor="rgba(11,61,145,0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="80% prediction interval",
        ))
        fig.update_layout(
            height=380, margin=dict(l=10, r=10, t=30, b=10),
            yaxis_title="Minutes from origin departure",
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Show the clean data table
        show = df[[
            "station_code", "scheduled_arrival", "baseline_eta",
            "pred_eta", "lower_eta", "upper_eta", "pred_delay",
        ]].rename(columns={
            "station_code": "Station", "scheduled_arrival": "Scheduled",
            "baseline_eta": "Baseline ETA", "pred_eta": "Predicted ETA",
            "lower_eta": "Earliest", "upper_eta": "Latest",
            "pred_delay": "Delay (min)",
        })
        st.dataframe(show, use_container_width=True, hide_index=True)

# ---------------- Control room ----------------
with tab_control:
    st.subheader("Network view")
    if isinstance(schedule, list):
        lats = [s["lat"] for s in schedule]
        lons = [s["lon"] for s in schedule]
        names = [s["station"] for s in schedule]
        current = live.get("current_station")
        colors = ["#E63946" if n == current else "#0B3D91" for n in names]
        fig = go.Figure(go.Scattergeo(
            lat=lats, lon=lons, text=names, mode="lines+markers+text",
            textposition="top center",
            marker=dict(size=10, color=colors),
            line=dict(width=3, color="#888"),
        ))
        fig.update_geos(
            scope="asia", showcountries=True, showland=True,
            landcolor="#F4F6F9", countrycolor="#CCC",
            lataxis_range=[5, 35], lonaxis_range=[65, 95],
        )
        fig.update_layout(height=480, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Downstream congestion profile")
    if isinstance(predict, dict) and "predictions" in predict:
        cdf = pd.DataFrame(predict["predictions"])
        fig2 = go.Figure(go.Bar(
            x=cdf["station_code"], y=cdf["pred_delay"],
            marker_color="#E63946",
        ))
        fig2.update_layout(
            height=280, yaxis_title="Predicted arrival delay (min)",
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("All active trains")
    live_all = api_get("/live")
    if isinstance(live_all, list) and live_all:
        st.dataframe(pd.DataFrame(live_all), use_container_width=True, hide_index=True)

# ---------------- Model performance ----------------
with tab_model:
    st.subheader("Held-out backtest vs baseline")
    if isinstance(backtest, dict) and "mae_model_min" in backtest:
        a, b, c, d = st.columns(4)
        a.metric("Baseline MAE", f'{backtest["mae_baseline_min"]} min')
        b.metric("Model MAE", f'{backtest["mae_model_min"]} min')
        c.metric("Improvement", f'{backtest["improvement_pct"]}%')
        d.metric("80% interval coverage", f'{backtest["interval_coverage_pct"]}%')
        
        # Clean table for metrics
        metrics_df = pd.DataFrame([backtest]).T.rename(columns={0: "Value"})
        st.dataframe(metrics_df, use_container_width=True)
    else:
        st.info("Run `python -m ml.train` to generate backtest metrics.")

    st.divider()
    st.markdown("""
    **How the model wins:** the baseline assumes the current delay persists unchanged.
    The quantile model learns route-specific recovery, congestion penalties, fog/rain
    effects, and how delay trends drift — and it returns an 80% prediction interval,
    not a false-precision point estimate.
    """)