from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class DecisionRoute(str, Enum):
    LOCAL = "LOCAL"
    CLOUD = "CLOUD"
    DEGRADE = "DEGRADE"

class ExecutionPolicy(BaseModel):
    latency_sla_ms: float = 200.0
    required_schema_keys: Optional[List[str]] = None
    allow_cloud_fallback: bool = True
    strict_privacy: bool = False
    allow_degradation: bool = True

class PolicyDecision(BaseModel):
    selected_route: DecisionRoute
    decision_code: str
    reason: str
    local_evaluated: bool = False
    cloud_evaluated: bool = False
    policy_passed: bool = False

class PolicyEngine:
    @staticmethod
    def evaluate_local_execution(
        policy: ExecutionPolicy,
        local_success: bool,
        local_latency_ms: float,
        schema_valid: bool = True,
        schema_error: Optional[str] = None
    ) -> PolicyDecision:
        """Evaluates whether local execution satisfied policy or if fallback/degradation is required."""
        
        # Scenario 1: Local execution hard failure (e.g. crash / out of memory)
        if not local_success:
            if policy.strict_privacy or not policy.allow_cloud_fallback:
                return PolicyDecision(
                    selected_route=DecisionRoute.DEGRADE,
                    decision_code="LOCAL_FAILED_PRIVACY_BLOCK",
                    reason="Local execution failed and cloud fallback is forbidden by policy.",
                    local_evaluated=True,
                    cloud_evaluated=False,
                    policy_passed=False
                )
            return PolicyDecision(
                selected_route=DecisionRoute.CLOUD,
                decision_code="LOCAL_FAILURE_TRIGGERED_CLOUD",
                reason="Local execution failed; falling back to cloud provider.",
                local_evaluated=True,
                cloud_evaluated=True,
                policy_passed=False
            )

        # Scenario 2: Latency SLA violation
        if local_latency_ms > policy.latency_sla_ms:
            if policy.strict_privacy or not policy.allow_cloud_fallback:
                return PolicyDecision(
                    selected_route=DecisionRoute.DEGRADE,
                    decision_code="LATENCY_VIOLATION_PRIVACY_BLOCK",
                    reason=f"Local latency ({local_latency_ms:.1f}ms) exceeded SLA ({policy.latency_sla_ms:.1f}ms). Cloud fallback blocked by privacy policy.",
                    local_evaluated=True,
                    cloud_evaluated=False,
                    policy_passed=False
                )
            return PolicyDecision(
                selected_route=DecisionRoute.CLOUD,
                decision_code="LOCAL_LATENCY_VIOLATION",
                reason=f"Local latency ({local_latency_ms:.1f}ms) exceeded SLA ({policy.latency_sla_ms:.1f}ms). Routing to cloud.",
                local_evaluated=True,
                cloud_evaluated=True,
                policy_passed=False
            )

        # Scenario 3: Structured output schema failure
        if not schema_valid:
            if policy.strict_privacy or not policy.allow_cloud_fallback:
                return PolicyDecision(
                    selected_route=DecisionRoute.DEGRADE,
                    decision_code="SCHEMA_INVALID_PRIVACY_BLOCK",
                    reason=f"Local output invalid ({schema_error}). Cloud fallback blocked by privacy policy.",
                    local_evaluated=True,
                    cloud_evaluated=False,
                    policy_passed=False
                )
            return PolicyDecision(
                selected_route=DecisionRoute.CLOUD,
                decision_code="LOCAL_SCHEMA_FAILURE",
                reason=f"Local output failed schema validation ({schema_error}). Routing to cloud.",
                local_evaluated=True,
                cloud_evaluated=True,
                policy_passed=False
            )

        # Scenario 4: All local policy checks passed successfully
        return PolicyDecision(
            selected_route=DecisionRoute.LOCAL,
            decision_code="LOCAL_SUCCESS",
            reason="Local execution satisfied all policy requirements (SLA, Schema, Privacy).",
            local_evaluated=True,
            cloud_evaluated=False,
            policy_passed=True
        )