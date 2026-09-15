from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import time

class ProviderResponse(BaseModel):
    provider_name: str
    success: bool
    output_text: str
    latency_ms: float
    error_message: Optional[str] = None
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseAIProvider(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def execute(self, prompt: str, **kwargs) -> ProviderResponse:
        """Execute prompt against provider and return standard ProviderResponse."""
        pass

    def execute_with_telemetry(self, prompt: str, **kwargs) -> ProviderResponse:
        """Wraps execution with automatic latency measurement."""
        start_time = time.perf_counter()
        try:
            response = self.execute(prompt, **kwargs)
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ProviderResponse(
                provider_name=self.name,
                success=False,
                output_text="",
                latency_ms=elapsed_ms,
                error_message=str(e)
            )
        return response