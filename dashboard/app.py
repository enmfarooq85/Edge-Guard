import sys
import pathlib

# Add the project root directory to Python's module path
root_dir = pathlib.Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st
import pandas as pd
from engine.runtime import EdgeGuardRuntime, ExecutionRequest
from policies.policy import ExecutionPolicy, DecisionRoute
from providers.qualcomm import QualcommAIHubProvider
from providers.cloud import OpenRouterCloudProvider
from telemetry.logger import TelemetryLogger
from benchmarks.suite import BenchmarkSuite

st.set_page_config(page_title="Edge-Guard Runtime Dashboard", layout="wide")

st.title("🛡️ Edge-Guard: Adaptive Policy Engine for Edge AI")
st.caption("Qualcomm Model-to-Device Innovation Track | Real-Time Telemetry & Routing Control")

st.sidebar.header("⚙️ Policy Configuration")
latency_sla = st.sidebar.slider("Latency SLA (ms)", 50, 1000, 200, step=10)
strict_privacy = st.sidebar.checkbox("Strict Privacy Mode (Block Cloud)", value=False)
allow_fallback = st.sidebar.checkbox("Allow Cloud Fallback", value=True)
require_schema = st.sidebar.checkbox("Require Valid JSON Schema", value=True)

# Simulated Edge Execution Controls
st.sidebar.subheader("🧪 Simulated Edge Conditions")
local_latency = st.sidebar.slider("Local Provider Latency (ms)", 20, 800, 120, step=10)
simulate_local_failure = st.sidebar.checkbox("Simulate Edge Device Failure", value=False)
simulate_invalid_json = st.sidebar.checkbox("Simulate Malformed JSON Output", value=False)

# Initialize Edge-Guard Engine
local_prov = QualcommAIHubProvider(target_device="Snapdragon 8 Gen 3")
cloud_prov = OpenRouterCloudProvider()

runtime = EdgeGuardRuntime(local_prov, cloud_prov)
telemetry = TelemetryLogger()

tab1, tab2, tab3 = st.tabs(["🚀 Live Playground", "📊 Telemetry & Logs", "📈 Benchmarks"])

with tab1:
    st.subheader("Interactive Prompt Execution")
    prompt = st.text_area("Input Request Prompt", "Extract invoice details: INV-9921 for $450.00")
    
    if st.button("Execute Request"):
        required_keys = ["invoice_id"] if require_schema else None
        policy = ExecutionPolicy(
            latency_sla_ms=latency_sla,
            strict_privacy=strict_privacy,
            allow_cloud_fallback=allow_fallback,
            required_schema_keys=required_keys
        )
        
        res = runtime.process_request(ExecutionRequest(prompt=prompt, policy=policy))
        
        # Display Decision Result Badge
        if res.selected_route == DecisionRoute.LOCAL:
            st.success(f"**Route Selected: LOCAL** | Decision Code: `{res.decision_code}`")
        elif res.selected_route == DecisionRoute.CLOUD:
            st.warning(f"**Route Selected: CLOUD** | Decision Code: `{res.decision_code}`")
        else:
            st.error(f"**Route Selected: DEGRADE** | Decision Code: `{res.decision_code}`")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Latency", f"{res.total_latency_ms:.1f} ms")
            st.write("**Reasoning:**", res.reason)
        with col2:
            st.write("**Final Output:**")
            st.code(res.output_text, language="json")

with tab2:
    st.subheader("System Observability & Event Log")
    events = telemetry.get_all_events()
    if events:
        df = pd.DataFrame(events)
        st.dataframe(df, use_container_width=True)
        stats = telemetry.get_summary_stats()
        st.json(stats)
    else:
        st.info("No execution events logged yet. Execute requests in the playground tab.")

with tab3:
    st.subheader("Performance Comparison (LOCAL vs CLOUD vs EDGE-GUARD)")
    if st.button("Run Benchmark Suite (20 Requests)"):
        with st.spinner("Running comparative workloads..."):
            suite = BenchmarkSuite(requests_count=20)
            results = suite.run_comparison()
            res_df = pd.DataFrame([r.model_dump() for r in results.values()])
            st.dataframe(res_df, use_container_width=True)
            
            st.bar_chart(res_df.set_index("mode")[["p50_latency_ms", "p95_latency_ms", "avg_latency_ms"]])