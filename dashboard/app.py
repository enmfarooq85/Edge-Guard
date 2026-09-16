import pathlib
import sys

root_dir = pathlib.Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pandas as pd
import streamlit as st

from benchmarks.suite import BenchmarkSuite
from engine.runtime import EdgeGuardRuntime, ExecutionRequest
from policies.policy import DecisionRoute, ExecutionPolicy
from providers.cloud import OpenRouterCloudProvider
from providers.qualcomm import QualcommAIHubProvider
from telemetry.logger import TelemetryLogger

st.set_page_config(page_title="Edge-Guard | AI Routing Control", layout="wide")

st.markdown(
    """
    <style>
    :root { color-scheme: light; }
    [data-testid="stAppViewContainer"] { background: #f4f6f8; color: #17212b; }
    [data-testid="stAppViewContainer"] main { color: #17212b; }
    [data-testid="stHeader"] { background: #f4f6f8; }
    [data-testid="stSidebar"] { background: #17212b; }
    [data-testid="stSidebar"] * { color: #edf2f7; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #cbd5df !important; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea { color: #17212b !important; background: #ffffff !important; }
    h1, h2, h3, h4, h5, h6 { color: #17212b !important; }
    [data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] li,
    [data-testid="stAppViewContainer"] label, [data-testid="stAppViewContainer"] small { color: #34495e; }
    .brand { border-bottom: 1px solid #d9e0e7; padding-bottom: 18px; margin-bottom: 24px; }
    .eyebrow { color: #52718a; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
    .hero-title { color: #17212b; font-size: 2.25rem; font-weight: 750; margin: 4px 0 8px; }
    .hero-copy { color: #52606d; font-size: 1.05rem; line-height: 1.55; max-width: 820px; }
    .path { background: white; border: 1px solid #d9e0e7; border-radius: 6px; padding: 16px; min-height: 116px; }
    .path-title { color: #17212b; font-size: 1rem; font-weight: 700; margin-bottom: 6px; }
    .path-copy { color: #52606d; font-size: 0.88rem; line-height: 1.4; }
    .route-local { border-left: 5px solid #16855b; }
    .route-cloud { border-left: 5px solid #c47a18; }
    .route-degrade { border-left: 5px solid #c13b3b; }
    .result { background: white; border: 1px solid #d9e0e7; border-radius: 6px; padding: 18px; margin: 18px 0; }
    .result-label { color: #52606d; font-size: 0.76rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
    .result-route { color: #17212b; font-size: 1.6rem; font-weight: 750; margin: 3px 0; }
    [data-baseweb="tab-list"] { border-bottom: 1px solid #b8c5d0; gap: 8px; }
    button[data-baseweb="tab"], [role="tab"] { color: #34495e !important; background: transparent !important; font-weight: 650; }
    button[data-baseweb="tab"][aria-selected="true"], [role="tab"][aria-selected="true"] { color: #0b6b5a !important; border-bottom-color: #0b6b5a !important; }
    [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li { color: #34495e; }
    [data-testid="stWidgetLabel"] p { color: #34495e !important; font-weight: 600; }
    [data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input { color: #17212b !important; background: #ffffff !important; border: 1px solid #aebbc7; }
    [data-testid="stDataFrame"] { border: 1px solid #d9e0e7; background: #ffffff; }
    [data-testid="stMetric"] { background: #ffffff; border: 1px solid #d9e0e7; border-radius: 6px; padding: 12px; }
    [data-testid="stMetricLabel"] p { color: #52606d !important; }
    [data-testid="stMetricValue"] { color: #17212b !important; }
    [data-testid="stAlert"] { color: #17212b !important; background: #ffffff; border: 1px solid #b8c5d0; }
    [data-testid="stAlert"] p { color: #34495e !important; }
    [data-testid="stCode"] { background: #17212b !important; color: #f4f6f8 !important; border-radius: 5px; }
    [data-testid="stCode"] code { color: #f4f6f8 !important; }
    div.stButton > button { border-radius: 4px; font-weight: 650; color: #17212b; background: #ffffff; border: 1px solid #8fa1b2; }
    div.stButton > button[kind="primary"] { color: #ffffff; background: #0b6b5a; border-color: #0b6b5a; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5, [data-testid="stSidebar"] h6,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] small, [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #ffffff !important; }
    [data-testid="stSidebar"] [data-testid="stAlert"] { background: #243445 !important; border: 1px solid #638099; }
    [data-testid="stSidebar"] [data-testid="stAlert"] p,
    [data-testid="stSidebar"] [data-testid="stAlert"] span { color: #ffffff !important; }
    [data-testid="stSidebar"] [data-baseweb="slider"] [role="slider"] { background: #ffffff !important; border-color: #ffffff !important; }
    [data-testid="stSidebar"] [data-baseweb="slider"] > div > div { background: #75b9ad !important; }
    [data-testid="stSidebar"] input[type="checkbox"] + div { border-color: #ffffff; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="brand">
      <div class="eyebrow">AI execution control plane</div>
      <div class="hero-title">Edge-Guard</div>
      <div class="hero-copy">
        Ask once. Edge-Guard chooses the safest working execution path: use the
        edge when it is fast and valid, use cloud when policy permits recovery,
        or stop safely when private data must stay local.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("## Request policy")
latency_sla = st.sidebar.slider("Maximum local latency (ms)", 50, 1000, 200, step=10)
strict_privacy = st.sidebar.checkbox("Block cloud for private requests", value=False)
allow_fallback = st.sidebar.checkbox("Allow cloud recovery", value=True)
require_schema = st.sidebar.checkbox("Require valid JSON output", value=True)

st.sidebar.markdown("## Edge demo controls")
st.sidebar.caption("These controls simulate an edge device so the routing policy can be tested without hardware.")
local_latency = st.sidebar.slider("Simulated edge latency (ms)", 20, 800, 120, step=10)
simulate_local_failure = st.sidebar.checkbox("Simulate edge failure", value=False)
simulate_invalid_json = st.sidebar.checkbox("Simulate invalid edge output", value=False)

st.sidebar.markdown("## Current execution mode")
st.sidebar.info("Demo simulation\n\nThe dashboard uses deterministic edge behavior for repeatable testing. Real Qualcomm AI Hub inference is an optional provider mode, not this simulation.")

local_prov = QualcommAIHubProvider(
    target_device="Snapdragon 8 Elite QRD",
    simulated_latency_ms=local_latency,
    should_fail=simulate_local_failure,
    invalid_json=simulate_invalid_json,
)
cloud_prov = OpenRouterCloudProvider()
runtime = EdgeGuardRuntime(local_prov, cloud_prov)
telemetry = TelemetryLogger()

st.markdown("### How a request is decided")
path_columns = st.columns(3)
path_content = [
    ("Edge / local", "Fast and private. Used when the simulated device meets the latency and output rules.", "route-local"),
    ("Cloud recovery", "Used when the edge is slow, unavailable, or invalid and policy permits sending the request out.", "route-cloud"),
    ("Safe degradation", "Used when recovery is forbidden by privacy policy or no provider can complete the request.", "route-degrade"),
]
for column, (title, copy, style) in zip(path_columns, path_content):
    with column:
        st.markdown(f'<div class="path {style}"><div class="path-title">{title}</div><div class="path-copy">{copy}</div></div>', unsafe_allow_html=True)

tab_playground, tab_telemetry, tab_benchmarks = st.tabs(["Request playground", "Decision log", "Performance comparison"])

with tab_playground:
    st.subheader("Test the routing decision")
    st.caption("Change the policy or edge demo controls in the sidebar, then send a request.")
    prompt = st.text_area("Request", "Extract invoice details: INV-9921 for $450.00", height=110)

    if st.button("Evaluate request", type="primary", use_container_width=True):
        required_keys = ["invoice_id"] if require_schema else None
        policy = ExecutionPolicy(
            latency_sla_ms=latency_sla,
            strict_privacy=strict_privacy,
            allow_cloud_fallback=allow_fallback,
            required_schema_keys=required_keys,
        )
        response = runtime.process_request(ExecutionRequest(prompt=prompt, policy=policy))
        route_class = {
            DecisionRoute.LOCAL: "route-local",
            DecisionRoute.CLOUD: "route-cloud",
            DecisionRoute.DEGRADE: "route-degrade",
        }[response.selected_route]
        st.markdown(
            f'<div class="result {route_class}"><div class="result-label">Selected execution path</div><div class="result-route">{response.selected_route.value}</div><div>{response.reason}</div></div>',
            unsafe_allow_html=True,
        )
        metric_columns = st.columns(3)
        metric_columns[0].metric("Decision code", response.decision_code)
        metric_columns[1].metric("Total latency", f"{response.total_latency_ms:.1f} ms")
        metric_columns[2].metric("Policy passed", "Yes" if response.policy_passed else "No")
        st.markdown("#### Final response")
        st.code(response.output_text, language="json")

with tab_telemetry:
    st.subheader("Why did the system choose that path?")
    events = telemetry.get_all_events()
    if events:
        event_frame = pd.DataFrame(events)
        summary = telemetry.get_summary_stats()
        summary_columns = st.columns(5)
        summary_columns[0].metric("Requests", summary["total_requests"])
        summary_columns[1].metric("Edge", summary["local_routes"])
        summary_columns[2].metric("Cloud", summary["cloud_routes"])
        summary_columns[3].metric("Degraded", summary["degrade_routes"])
        summary_columns[4].metric("Average latency", f"{summary['avg_latency_ms']:.1f} ms")
        st.dataframe(event_frame, use_container_width=True, hide_index=True)
    else:
        st.info("No decisions recorded yet. Evaluate a request in the playground.")

with tab_benchmarks:
    st.subheader("Compare execution strategies")
    st.caption("The benchmark runs the same deterministic workload through edge-only, cloud-only, and adaptive routing modes.")
    if st.button("Run 20-request comparison", type="primary"):
        with st.spinner("Running comparison..."):
            results = BenchmarkSuite(requests_count=20).run_comparison()
        result_frame = pd.DataFrame([result.model_dump() for result in results.values()])
        st.dataframe(result_frame, use_container_width=True, hide_index=True)
        st.bar_chart(result_frame.set_index("mode")[["p50_latency_ms", "p95_latency_ms", "avg_latency_ms"]])