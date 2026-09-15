import time
from providers.base import BaseAIProvider, ProviderResponse

class MockLocalProvider(BaseAIProvider):
    def __init__(self, name: str = "mock_local", simulated_latency_ms: float = 120.0, should_fail: bool = False, invalid_json: bool = False):
        super().__init__(name=name)
        self.simulated_latency_ms = simulated_latency_ms
        self.should_fail = should_fail
        self.invalid_json = invalid_json

    def execute(self, prompt: str, **kwargs) -> ProviderResponse:
        start = time.perf_counter()
        time.sleep(self.simulated_latency_ms / 1000.0)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        if self.should_fail:
            return ProviderResponse(
                provider_name=self.name,
                success=False,
                output_text="",
                latency_ms=elapsed_ms,
                error_message="Local execution device failure / out of memory"
            )

        if self.invalid_json:
            output = '{"status": "error", invoice_id: 123}'  # Malformed JSON
        else:
            output = '{"status": "success", "invoice_id": "INV-1002", "amount": 250.00}'

        return ProviderResponse(
            provider_name=self.name,
            success=True,
            output_text=output,
            latency_ms=elapsed_ms
        )