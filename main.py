import sys
import pathlib

# Ensure project root is in sys.path
root_dir = pathlib.Path(__file__).parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

from engine.runtime import EdgeGuardRuntime, ExecutionRequest, ExecutionResponse
from providers.qualcomm import QualcommAIHubProvider
from providers.cloud import OpenRouterCloudProvider
from telemetry.logger import TelemetryLogger
from benchmarks.suite import BenchmarkSuite

app = FastAPI(
    title="Edge-Guard API Engine",
    description="Adaptive Runtime & Policy Engine for Edge AI (Qualcomm Track)",
    version="1.0.0",
)

# Initialize Edge-Guard Engine with Qualcomm & Cloud Providers
qualcomm_provider = QualcommAIHubProvider()
cloud_provider = OpenRouterCloudProvider()
runtime = EdgeGuardRuntime(
    local_provider=qualcomm_provider, cloud_provider=cloud_provider
)
telemetry = TelemetryLogger()


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "engine": "Edge-Guard Runtime v1.0.0"}


@app.post("/v1/execute", response_model=ExecutionResponse)
def execute_prompt(request: ExecutionRequest) -> ExecutionResponse:
    """Submits an AI execution request and returns policy evaluation result."""
    try:
        return runtime.process_request(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/telemetry")
def get_telemetry_logs() -> List[Dict[str, Any]]:
    """Retrieves raw execution telemetry logs."""
    return telemetry.get_all_events()


@app.get("/v1/telemetry/summary")
def get_telemetry_summary() -> Dict[str, Any]:
    """Retrieves aggregated telemetry summary metrics."""
    return telemetry.get_summary_stats()


@app.post("/v1/benchmark")
def run_benchmark_suite(count: int = 10) -> Dict[str, Any]:
    """Executes a comparative benchmark suite across execution modes."""
    suite = BenchmarkSuite(requests_count=count)
    results = suite.run_comparison()
    return {k: v.model_dump() for k, v in results.items()}
