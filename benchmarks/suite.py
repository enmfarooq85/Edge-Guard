import time
from typing import List, Dict, Any
from pydantic import BaseModel

from engine.runtime import EdgeGuardRuntime, ExecutionRequest
from policies.policy import ExecutionPolicy, DecisionRoute
from providers.local import MockLocalProvider
from providers.cloud import OpenRouterCloudProvider

class BenchmarkResult(BaseModel):
    mode: str
    total_requests: int
    local_count: int
    cloud_count: int
    degrade_count: int
    p50_latency_ms: float
    p95_latency_ms: float
    avg_latency_ms: float
    success_rate_pct: float

class BenchmarkSuite:
    def __init__(self, requests_count: int = 20):
        self.requests_count = requests_count

    def run_comparison(self) -> Dict[str, BenchmarkResult]:
        """Runs identical workloads through LOCAL-ONLY, CLOUD-ONLY, and EDGE-GUARD modes."""
        
        # Simulated workload parameters (varying latencies and occasional failures)
        prompts = [f"Task payload sample {i}" for i in range(self.requests_count)]
        policy = ExecutionPolicy(latency_sla_ms=150.0, required_schema_keys=["invoice_id"])

        results = {}

        # 1. Local-Only Mode
        results["LOCAL_ONLY"] = self._run_mode("LOCAL_ONLY", prompts, policy)

        # 2. Cloud-Only Mode
        results["CLOUD_ONLY"] = self._run_mode("CLOUD_ONLY", prompts, policy)

        # 3. Edge-Guard Adaptive Mode
        results["EDGE_GUARD"] = self._run_mode("EDGE_GUARD", prompts, policy)

        return results

    def _run_mode(self, mode: str, prompts: List[str], policy: ExecutionPolicy) -> BenchmarkResult:
        latencies: List[float] = []
        local_cnt, cloud_cnt, degrade_cnt, successes = 0, 0, 0, 0

        for idx, prompt in enumerate(prompts):
            # Simulate edge resource fluctuation (every 4th request has high latency)
            sim_lat = 220.0 if (idx % 4 == 0) else 80.0
            sim_fail = (idx % 9 == 0)

            local_prov = MockLocalProvider(simulated_latency_ms=sim_lat, should_fail=sim_fail)
            cloud_prov = OpenRouterCloudProvider(simulated_latency_ms=350.0)

            if mode == "LOCAL_ONLY":
                res = local_prov.execute_with_telemetry(prompt)
                latencies.append(res.latency_ms)
                local_cnt += 1
                if res.success:
                    successes += 1

            elif mode == "CLOUD_ONLY":
                res = cloud_prov.execute_with_telemetry(prompt)
                latencies.append(res.latency_ms)
                cloud_cnt += 1
                if res.success:
                    successes += 1

            elif mode == "EDGE_GUARD":
                runtime = EdgeGuardRuntime(local_prov, cloud_prov)
                res = runtime.process_request(ExecutionRequest(prompt=prompt, policy=policy))
                latencies.append(res.total_latency_ms)
                
                if res.selected_route == DecisionRoute.LOCAL:
                    local_cnt += 1
                elif res.selected_route == DecisionRoute.CLOUD:
                    cloud_cnt += 1
                else:
                    degrade_cnt += 1

                if res.selected_route != DecisionRoute.DEGRADE:
                    successes += 1

        latencies.sort()
        n = len(latencies)
        p50 = latencies[int(n * 0.50)] if n > 0 else 0.0
        p95 = latencies[int(n * 0.95)] if n > 0 else 0.0
        avg = sum(latencies) / n if n > 0 else 0.0

        return BenchmarkResult(
            mode=mode,
            total_requests=len(prompts),
            local_count=local_cnt,
            cloud_count=cloud_cnt,
            degrade_count=degrade_cnt,
            p50_latency_ms=round(p50, 2),
            p95_latency_ms=round(p95, 2),
            avg_latency_ms=round(avg, 2),
            success_rate_pct=round((successes / len(prompts)) * 100.0, 1)
        )