import os
import time
import requests
import pathlib
from dotenv import load_dotenv
from providers.base import BaseAIProvider, ProviderResponse

class OpenRouterCloudProvider(BaseAIProvider):
    def __init__(self, name: str = "openrouter_cloud", model_name: str = "openrouter/free"):
        super().__init__(name=name)
        
        # 1. Force load the .env file exactly when the provider is created
        root_dir = pathlib.Path(__file__).parent.parent.resolve()
        load_dotenv(dotenv_path=root_dir / ".env", override=True)
        
        # 2. Now fetch the variables securely
        self.model_name = os.getenv("OPENROUTER_MODEL_NAME", model_name)
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def execute(self, prompt: str, **kwargs) -> ProviderResponse:
        start_time = time.perf_counter()

        if not self.api_key:
            return ProviderResponse(
                provider_name=self.name,
                success=False,
                output_text="",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                error_message="OPENROUTER_API_KEY environment variable is not set."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/edge-guard",
            "X-Title": "Edge-Guard Runtime Engine"
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a fallback AI engine. Return valid JSON objects when requested."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=12.0)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return ProviderResponse(
                    provider_name=f"{self.name} ({self.model_name})",
                    success=True,
                    output_text=content,
                    latency_ms=elapsed_ms,
                    raw_metadata={"openrouter_id": data.get("id")}
                )
            else:
                return ProviderResponse(
                    provider_name=self.name,
                    success=False,
                    output_text="",
                    latency_ms=elapsed_ms,
                    error_message=f"OpenRouter API Error [{response.status_code}]: {response.text}"
                )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ProviderResponse(
                provider_name=self.name,
                success=False,
                output_text="",
                latency_ms=elapsed_ms,
                error_message=f"Network execution failure: {str(e)}"
            )