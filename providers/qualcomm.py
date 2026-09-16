import os
import time
import pathlib
import json
from dotenv import load_dotenv
from providers.base import BaseAIProvider, ProviderResponse

class QualcommAIHubProvider(BaseAIProvider):
    def __init__(
        self,
        name: str = "qualcomm_ai_hub",
        target_device: str = "Snapdragon 8 Elite QRD",
        simulated_latency_ms: float = 0.0,
        should_fail: bool = False,
        invalid_json: bool = False,
        model_path: str | None = None,
        input_dataset_path: str | None = None,
    ):
        super().__init__(name=name)
        self.target_device = target_device
        self.simulated_latency_ms = simulated_latency_ms
        self.should_fail = should_fail
        self.invalid_json = invalid_json

        root_dir = pathlib.Path(__file__).parent.parent.resolve()
        load_dotenv(dotenv_path=root_dir / ".env")
        self.api_token = os.getenv("QAI_HUB_API_TOKEN")
        self.model_path = model_path or os.getenv("QAI_HUB_MODEL_PATH")
        self.input_dataset_path = input_dataset_path or os.getenv("QAI_HUB_INPUT_DATASET_PATH")

    def execute(self, prompt: str, **kwargs) -> ProviderResponse:
        start_time = time.perf_counter()

        if self.simulated_latency_ms > 0:
            time.sleep(self.simulated_latency_ms / 1000.0)

        if self.should_fail:
            return ProviderResponse(
                provider_name=self.name,
                success=False,
                output_text="",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                error_message="Simulated edge device failure / out of memory",
            )

        if self.invalid_json:
            output_text = '{"status": "error", invoice_id: 123}'
        else:
            output_text = '{"status": "success", "invoice_id": "INV-REAL-99", "amount": 890.00}'

        if self.simulated_latency_ms > 0:
            return ProviderResponse(
                provider_name=f"Qualcomm ({self.target_device}, simulated)",
                success=True,
                output_text=output_text,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                raw_metadata={"device": self.target_device, "simulated": True},
            )

        if not self.api_token:
            return ProviderResponse(
                provider_name=self.name,
                success=False,
                output_text="",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                error_message="QAI_HUB_API_TOKEN is not set.",
            )

        if not self.model_path or not self.input_dataset_path:
            return ProviderResponse(
                provider_name=self.name,
                success=False,
                output_text="",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                error_message=(
                    "Real Qualcomm inference requires QAI_HUB_MODEL_PATH and "
                    "QAI_HUB_INPUT_DATASET_PATH. Device discovery succeeded, "
                    "but no model inference job was configured."
                ),
            )

        try:
            import qai_hub as hub
            client = hub.Client(config=hub.ClientConfig(api_token=self.api_token))

            # Query real physical/hosted devices on Qualcomm AI Hub Workbench
            devices = client.get_devices(name=self.target_device)
            if not devices:
                raise RuntimeError(f"Qualcomm device '{self.target_device}' not found on AI Hub.")
            
            target = devices[0]
            
            # Submit profiling or inference job to Qualcomm device
            # Note: Pass your compiled model handle / ONNX / TFLite asset here
            # job = hub.submit_inference_job(model=compiled_model, device=target, inputs=...)
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            
            job = client.submit_inference_job(
                model=self.model_path,
                device=target,
                inputs=self.input_dataset_path,
                name="edge-guard-inference",
            )
            output_data = job.download_output_data()
            output_text = json.dumps(output_data, default=str)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return ProviderResponse(
                provider_name=f"Qualcomm ({target.name})",
                success=True,
                output_text=output_text,
                latency_ms=elapsed_ms,
                raw_metadata={
                    "device": target.name,
                    "execution": "ai_hub_inference_job",
                    "job_url": str(job.url),
                }
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ProviderResponse(
                provider_name=self.name,
                success=False,
                output_text="",
                latency_ms=elapsed_ms,
                error_message=f"Qualcomm AI Hub execution failed: {str(e)}"
            )