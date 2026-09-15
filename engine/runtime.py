import uuid
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from providers.base import BaseAIProvider, ProviderResponse
from validation.validator import OutputValidator, ValidationResult
from policies.policy import ExecutionPolicy, PolicyDecision, PolicyEngine, DecisionRoute
from telemetry.logger import TelemetryLogger, TelemetryEvent

class ExecutionRequest(BaseModel):
    prompt: str
    policy: ExecutionPolicy = ExecutionPolicy()

class ExecutionResponse(BaseModel):
    request_id: str
    selected_route: DecisionRoute
    decision_code: str
    reason: str
    output_text: str
    total_latency_ms: float
    policy_passed: bool
    telemetry_event_id: str

class EdgeGuardRuntime:
    def __init__(self, local_provider: BaseAIProvider, cloud_provider: Optional[BaseAIProvider] = None):
        self.local_provider = local_provider
        self.cloud_provider = cloud_provider
        self.telemetry = TelemetryLogger()

    def process_request(self, request: ExecutionRequest) -> ExecutionResponse:
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        start_total = time.perf_counter()

        # 1. Execute local provider
        local_res = self.local_provider.execute_with_telemetry(request.prompt)

        # 2. Validate structured schema (if required by policy)
        schema_res = ValidationResult(is_valid=True)
        if local_res.success and request.policy.required_schema_keys:
            schema_res = OutputValidator.validate_json_structure(
                local_res.output_text,
                required_keys=request.policy.required_schema_keys
            )

        # 3. Evaluate Policy Engine against local metrics
        decision: PolicyDecision = PolicyEngine.evaluate_local_execution(
            policy=request.policy,
            local_success=local_res.success,
            local_latency_ms=local_res.latency_ms,
            schema_valid=schema_res.is_valid,
            schema_error=schema_res.error_reason
        )

        final_output = local_res.output_text
        cloud_res: Optional[ProviderResponse] = None
        cloud_success: Optional[bool] = None
        cloud_latency: Optional[float] = None

        # 4. Handle Policy Decisions (CLOUD fallback or DEGRADE)
        if decision.selected_route == DecisionRoute.CLOUD:
            if self.cloud_provider:
                cloud_res = self.cloud_provider.execute_with_telemetry(request.prompt)
                cloud_success = cloud_res.success
                cloud_latency = cloud_res.latency_ms
                if cloud_res.success:
                    final_output = cloud_res.output_text
                else:
                    decision.selected_route = DecisionRoute.DEGRADE
                    decision.decision_code = "CLOUD_FALLBACK_FAILED"
                    decision.reason = f"Cloud provider execution failed: {cloud_res.error_message}"
                    final_output = "Service currently degraded due to local and cloud execution failures."
            else:
                decision.selected_route = DecisionRoute.DEGRADE
                decision.decision_code = "CLOUD_PROVIDER_UNAVAILABLE"
                decision.reason = "Cloud fallback requested by policy, but no cloud provider is registered."
                final_output = "Service degraded: No cloud provider configured."

        elif decision.selected_route == DecisionRoute.DEGRADE:
            final_output = f"Service gracefully degraded. Reason: {decision.reason}"

        total_latency_ms = (time.perf_counter() - start_total) * 1000.0

        # 5. Record structured Telemetry event
        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        telemetry_event = TelemetryEvent(
            event_id=event_id,
            prompt=request.prompt,
            selected_route=decision.selected_route.value,
            decision_code=decision.decision_code,
            reason=decision.reason,
            policy_passed=decision.policy_passed,
            local_latency_ms=local_res.latency_ms,
            cloud_latency_ms=cloud_latency,
            total_latency_ms=total_latency_ms,
            local_success=local_res.success,
            cloud_success=cloud_success,
            schema_valid=schema_res.is_valid,
            final_output=final_output
        )
        self.telemetry.log_event(telemetry_event)

        return ExecutionResponse(
            request_id=request_id,
            selected_route=decision.selected_route,
            decision_code=decision.decision_code,
            reason=decision.reason,
            output_text=final_output,
            total_latency_ms=total_latency_ms,
            policy_passed=decision.policy_passed,
            telemetry_event_id=event_id
        )