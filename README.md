# Edge-Guard

Adaptive runtime and policy engine for edge AI.

Edge-Guard is an AI Infra Summit 2026 project for the **Qualcomm Model-to-device Innovation** track. It gives an application a deterministic way to choose between an edge execution path, cloud fallback, and safe degradation when latency, output quality, privacy, or availability requirements are not met.

## The Problem

Local AI is fast, private, and inexpensive, but edge execution is not always predictable. A device can be slow, unavailable, or return malformed structured output. Sending every request to the cloud solves availability but increases latency, cost, and data exposure.

Edge-Guard makes that tradeoff explicit and enforceable:

```text
Application request
	|
	v
Edge-Guard Runtime
	|
	v
Deterministic Policy Engine
	|
	v
Local / Qualcomm execution
	|
	v
Schema validation and latency checks
	|
   +----+----+
   |         |
   v         v
Cloud     Degrade
fallback  safely
	|
	v
Telemetry and visible decision
```

## What It Demonstrates

- `LOCAL_SUCCESS`: local execution meets the latency and schema policy.
- `LOCAL_LATENCY_VIOLATION`: local execution exceeds the configured SLA and is routed to cloud when permitted.
- `LOCAL_SCHEMA_FAILURE`: malformed structured output is detected and routed to cloud when permitted.
- `LOCAL_FAILURE_TRIGGERED_CLOUD`: local execution fails and cloud fallback is allowed.
- `LOCAL_FAILED_PRIVACY_BLOCK`: local execution fails while strict privacy blocks cloud transmission.
- `CLOUD_PROVIDER_UNAVAILABLE`: the request degrades safely when no fallback provider is available.
- Structured telemetry containing route, decision reason, latency, validation state, and final output.
- A repeatable comparison of `LOCAL_ONLY`, `CLOUD_ONLY`, and `EDGE_GUARD` workloads.

## Qualcomm Integration Status

The project uses the official `qai-hub` Python client and the Qualcomm AI Hub Workbench device-discovery workflow.

Verified integration details:

| Item | Current implementation |
| --- | --- |
| Qualcomm technology | Qualcomm AI Hub / AI Hub Workbench client |
| Target device | Snapdragon 8 Elite QRD by default |
| Authentication | `QAI_HUB_API_TOKEN` through `qai_hub.Client` |
| Verified operation | Authenticated device discovery |
| Provider boundary | `QualcommAIHubProvider` |
| Inference job | Opt-in through model and input-dataset paths |

Important technical disclosure: AI Hub Workbench executes inference on a hosted Qualcomm device, not on the laptop's local NPU. The provider now submits a real inference job when `QAI_HUB_MODEL_PATH` and `QAI_HUB_INPUT_DATASET_PATH` are configured. Without those values, it fails explicitly after authentication rather than pretending that inference occurred.

## Architecture

```text
dashboard/app.py or HTTP client
	      |
	      v
       engine/runtime.py
	      |
	      v
       policies/policy.py
	  /          \
	 v            v
 providers/       validation/
 qualcomm.py     validator.py
 local.py             |
 cloud.py             v
	  telemetry/logger.py
	      |
	      v
       benchmarks/suite.py
```

### Components

- `engine/runtime.py`: executes local work, validates it, applies policy, and invokes fallback or degradation.
- `policies/policy.py`: deterministic latency, privacy, fallback, and schema decisions.
- `providers/qualcomm.py`: Qualcomm AI Hub client integration and controlled edge simulation options.
- `providers/local.py`: deterministic local provider used by tests and benchmarks.
- `providers/cloud.py`: OpenRouter fallback provider and offline `MockCloudProvider`.
- `validation/validator.py`: JSON object and required-key validation.
- `telemetry/logger.py`: in-memory structured event log and summary metrics.
- `benchmarks/suite.py`: reproducible local, cloud, and adaptive comparisons.
- `dashboard/app.py`: Streamlit playground, telemetry view, and benchmark view.
- `main.py`: FastAPI service exposing health, execution, telemetry, and benchmark endpoints.

## Requirements

- Python 3.10 or newer
- OpenRouter API key for live cloud fallback
- Qualcomm AI Hub API token for live device discovery
- Optional: a Qualcomm AI Hub account with an available target device

## Setup

From the `Edge-Guard` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set these values in `.env`:

```text
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL_NAME=nvidia/nemotron-3.5-lightning:free
QAI_HUB_API_TOKEN=your_qai_hub_token
QAI_HUB_MODEL_PATH=path/to/model.onnx
QAI_HUB_INPUT_DATASET_PATH=path/to/inputs.h5
```

Never commit `.env` or API tokens. Rotate any credential that has been exposed in shell history, screenshots, logs, or shared documents.

## Run the Services

Start the FastAPI backend:

```powershell
uvicorn main:app --reload --port 8000
```

Open the API at `http://localhost:8000`. The health endpoint is:

```text
http://localhost:8000/health
```

Start the dashboard in a second terminal:

```powershell
python -m streamlit run dashboard/app.py --server.port 8501
```

Open `http://localhost:8501` for the Live Playground, Telemetry, and Benchmarks tabs.

## API Examples

Execute a request with a latency and schema policy:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/v1/execute `
  -ContentType "application/json" `
  -Body '{"prompt":"Extract invoice INV-9921","policy":{"latency_sla_ms":200,"required_schema_keys":["invoice_id"],"allow_cloud_fallback":true,"strict_privacy":false}}'
```

Run the comparison benchmark:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/v1/benchmark?count=20"
```

## Demo Script

1. Open the dashboard and leave the latency SLA at `200 ms`.
2. Run with simulated latency below the SLA and observe `LOCAL`.
3. Raise simulated local latency above the SLA and observe `CLOUD`.
4. Enable malformed JSON and observe schema validation trigger fallback.
5. Enable simulated edge failure and strict privacy together and observe `DEGRADE`.
6. Open Telemetry to explain the selected route, reason, latency, and validation state.
7. Run the benchmark tab and compare `LOCAL_ONLY`, `CLOUD_ONLY`, and `EDGE_GUARD`.

The sidebar simulation controls are deliberately deterministic so the policy behavior can be demonstrated without repeatedly calling external services.

## Tests and Benchmarks

Run the six-scenario policy matrix:

```powershell
python -m unittest tests/matrix.py
```

The matrix covers local success, latency fallback, schema fallback, privacy blocking, local failure fallback, and missing cloud provider degradation.

Run a benchmark from Python:

```powershell
python -c "from benchmarks.suite import BenchmarkSuite; print(BenchmarkSuite(20).run_comparison())"
```

The benchmark uses the same workload shape for all modes and records total latency, P50, P95, average latency, route counts, degradation count, and success rate. Its local and cloud providers are deterministic mocks; these results are engineering comparison evidence, not a claim about universal Qualcomm hardware performance.

## Current Validation

The current repository has verified:

- Six policy tests passing with `python -m unittest tests/matrix.py`.
- Benchmark execution for all three modes.
- Authenticated Qualcomm AI Hub access and device discovery.
- Dashboard simulation routes for local success, cloud fallback, schema failure, and privacy degradation.

## Limitations and Next Step

The real Qualcomm inference path is implemented, but it requires a compatible model artifact and input dataset. Until those are configured and a job completes successfully, describe the Qualcomm portion as authenticated AI Hub device discovery plus an available inference bridge, not as completed local NPU inference.

## Project Status

- Phase A: complete. Test matrix and offline benchmark fallback are fixed.
- Phase B: complete. Qualcomm authentication and dashboard simulations are wired and validated.
- Phase C: documentation complete. Real compiled Qualcomm model inference remains the major technical follow-up before claiming a full device-side MVP.
