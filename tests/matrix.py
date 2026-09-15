import unittest
from engine.runtime import EdgeGuardRuntime, ExecutionRequest
from policies.policy import ExecutionPolicy, DecisionRoute
from providers.local import MockLocalProvider
from providers.cloud import MockCloudProvider

class TestEdgeGuardPolicyEngine(unittest.TestCase):

    def test_t01_local_success(self):
        """T01: Local execution succeeds within SLA and matches schema -> LOCAL"""
        local = MockLocalProvider(simulated_latency_ms=50.0)
        cloud = MockCloudProvider()
        runtime = EdgeGuardRuntime(local, cloud)

        req = ExecutionRequest(
            prompt="Extract invoice data",
            policy=ExecutionPolicy(latency_sla_ms=200.0, required_schema_keys=["invoice_id"])
        )
        res = runtime.process_request(req)

        self.assertEqual(res.selected_route, DecisionRoute.LOCAL)
        self.assertEqual(res.decision_code, "LOCAL_SUCCESS")
        self.assertTrue(res.policy_passed)

    def test_t02_latency_violation_triggers_cloud(self):
        """T02: Local exceeds latency SLA -> CLOUD"""
        local = MockLocalProvider(simulated_latency_ms=300.0)
        cloud = MockCloudProvider()
        runtime = EdgeGuardRuntime(local, cloud)

        req = ExecutionRequest(
            prompt="Extract invoice data",
            policy=ExecutionPolicy(latency_sla_ms=200.0)
        )
        res = runtime.process_request(req)

        self.assertEqual(res.selected_route, DecisionRoute.CLOUD)
        self.assertEqual(res.decision_code, "LOCAL_LATENCY_VIOLATION")

    def test_t03_schema_failure_triggers_cloud(self):
        """T03: Local produces invalid schema -> CLOUD"""
        local = MockLocalProvider(simulated_latency_ms=50.0, invalid_json=True)
        cloud = MockCloudProvider()
        runtime = EdgeGuardRuntime(local, cloud)

        req = ExecutionRequest(
            prompt="Extract invoice data",
            policy=ExecutionPolicy(latency_sla_ms=200.0, required_schema_keys=["invoice_id"])
        )
        res = runtime.process_request(req)

        self.assertEqual(res.selected_route, DecisionRoute.CLOUD)
        self.assertEqual(res.decision_code, "LOCAL_SCHEMA_FAILURE")

    def test_t04_privacy_policy_blocks_cloud(self):
        """T04: Local exceeds SLA but strict privacy is enabled -> DEGRADE"""
        local = MockLocalProvider(simulated_latency_ms=300.0)
        cloud = MockCloudProvider()
        runtime = EdgeGuardRuntime(local, cloud)

        req = ExecutionRequest(
            prompt="Extract sensitive document",
            policy=ExecutionPolicy(latency_sla_ms=200.0, strict_privacy=True)
        )
        res = runtime.process_request(req)

        self.assertEqual(res.selected_route, DecisionRoute.DEGRADE)
        self.assertEqual(res.decision_code, "LATENCY_VIOLATION_PRIVACY_BLOCK")

    def test_t05_local_failure_with_cloud_fallback(self):
        """T05: Local execution fails completely -> CLOUD"""
        local = MockLocalProvider(should_fail=True)
        cloud = MockCloudProvider()
        runtime = EdgeGuardRuntime(local, cloud)

        req = ExecutionRequest(
            prompt="Process request",
            policy=ExecutionPolicy(allow_cloud_fallback=True)
        )
        res = runtime.process_request(req)

        self.assertEqual(res.selected_route, DecisionRoute.CLOUD)
        self.assertEqual(res.decision_code, "LOCAL_FAILURE_TRIGGERED_CLOUD")

    def test_t06_both_providers_unavailable(self):
        """T06: Local fails and no cloud provider is registered -> DEGRADE"""
        local = MockLocalProvider(should_fail=True)
        runtime = EdgeGuardRuntime(local, cloud_provider=None)

        req = ExecutionRequest(
            prompt="Process request",
            policy=ExecutionPolicy(allow_cloud_fallback=True)
        )
        res = runtime.process_request(req)

        self.assertEqual(res.selected_route, DecisionRoute.DEGRADE)
        self.assertEqual(res.decision_code, "CLOUD_PROVIDER_UNAVAILABLE")

if __name__ == "__main__":
    unittest.main()