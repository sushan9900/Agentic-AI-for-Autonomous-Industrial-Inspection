# Phase 5D — Code-Level Performance & Timing Audit Report

**Audit Target:** Phase 5D End-to-End Performance & Reliability Benchmark  
**Date:** 2026-09-02  
**Scope:** Code-level inspection of timing boundaries, stage isolation, warm-up mechanics, CLI flags, and hardware utilization.  
**Files Audited:**
- `scripts/evaluation/benchmark_end_to_end.py`
- `scripts/evaluation/reliability_runner.py`
- `scripts/evaluation/benchmark_config.py`
- `scripts/evaluation/performance_metrics.py`
- `scripts/evaluation/resource_monitor.py`
- `backend/app/services/end_to_end_inspection.py`
- `backend/app/agents/inspection_agent.py`
- `vision/inference/pipeline.py`
- `vision/models/yolo_seg.py`
- `backend/app/evaluation/llm_evaluator.py`

---

## 1. Executive Summary of Audit

The reported Phase 5D numbers from the initial trial run (`--runs 1 --warmup 0`):
- End-to-End Mean: **68.07 s**
- YOLO11n-seg Inference Mean: **5249.09 ms (5.25 s)**
- Gemma 3 Generation Mean: **61255.05 ms (61.26 s)**
- Total Execution Time: **720.32 s**

The audit revealed that **the production code and models are functioning as designed**, but the **benchmarking harness contained instrumentation bugs and architectural redundancies that caused severe timing artifacts and cold-start contamination**:
1. **YOLO 5.25 s Cause:** On a fresh process with `--warmup 0`, the benchmark timed the first raw call to `pipeline.model.predict(...)`. This measured initial CUDA context creation, PyTorch CUDA library initialization, and Ultralytics graph compilation (~5.1s) rather than steady-state inference (~39 ms). In addition, YOLO inference was executed **twice** per inspection.
2. **Gemma 3 61.26 s Cause:** With `--warmup 0`, Ollama experienced a cold model load from disk into GPU VRAM (~25–30s). Furthermore, `InspectionDecisionAgent` passes a complete multi-stage industrial evidence payload with history, thresholds, and incidents (~400+ tokens) rather than the lightweight 40-token synthetic prompt evaluated in Phase 5C.
3. **Double Execution Redundancy:** The benchmark timer manually executed stages (validation, preprocessing, YOLO inference, and database lookups) and then called `pipeline.run_inspection_evidence()` and `inspection_decision_agent.run_inspection()`, causing perception and DB retrieval to be executed twice per cycle.
4. **CLI Flag Inflexibility:** Running with `--runs 1 --warmup 0` still triggered the 10-image workload and 10 failure-recovery tests sequentially (~650 seconds), because CLI control flags were insufficiently granular.

---

## 2. Detailed Audit Findings

### Finding 1: YOLO Inference Timing Cold-Start Contamination & Double Inference
- **Classification:** `[BUG]` & `[EXPECTED COLD START]`
- **Evidence from Source Code:**
  In `scripts/evaluation/reliability_runner.py` (lines 98–121):
  ```python
  # C. YOLO Model Inference (CUDA Synchronized)
  sync_cuda()
  t0 = time.perf_counter()
  try:
      raw_predictions = pipeline.model.predict(str(image_path_obj), confidence_threshold=vision_settings.VISION_CONFIDENCE_THRESHOLD)
  except TypeError:
      raw_predictions = pipeline.model.predict(preprocessed)
  sync_cuda()
  stage_times["C_yolo_inference_ms"] = (time.perf_counter() - t0) * 1000.0
  ...
  # E. VisionEvidence Construction
  t0 = time.perf_counter()
  vision_evidence = pipeline.run_inspection_evidence(
      image_path=str(image_path_obj),
      component_id=component_id,
      inspection_id=assigned_insp_id,
      component_type="pipeline"
  )
  stage_times["E_evidence_construction_ms"] = (time.perf_counter() - t0) * 1000.0
  ```
- **Why It Matters:**
  1. In PyTorch on Windows with CUDA, the very first forward pass on an uninitialized process initializes the CUDA driver context, memory allocators, and cuDNN kernels. Because `--warmup 0` was specified, `C_yolo_inference_ms` measured this 5.1-second one-time engine initialization.
  2. In Stage E, `pipeline.run_inspection_evidence(...)` executed preprocessing, forward inference, postprocessing, and evidence construction a **second time**. Notice from the audit log that Stage E took only **152.44 ms** total (of which warm YOLO inference was ~38 ms).
  3. The benchmark reported Stage C as steady-state inference, leading to the false impression that YOLO took 5.25 seconds.
- **Required Correction:**
  - Separate one-time engine initialization from steady-state inference.
  - Eliminate the redundant duplicate call to `pipeline.model.predict()`. Let `pipeline.run_inspection_evidence(...)` execute perception and extract the high-resolution internal breakdown (`evidence.processing.inference_ms`, `preprocessing_ms`, etc.) directly from `VisionEvidence.processing`.
- **Production Code Modification:** None. Production `InferencePipeline` and `YOLOSegmentationModel` are working correctly.

---

### Finding 2: Gemma 3 Latency Discrepancy (61.26 s vs Phase 5C 27.26 s)
- **Classification:** `[EXPECTED COLD START]` & `[LIMITATION]`
- **Evidence from Source Code:**
  1. In `backend/app/agents/inspection_agent.py` (lines 271–359):
     ```python
     t0 = time.time()
     prompt = AgentPromptBuilder.build_prompt(...)  # Constructs 400+ token comprehensive evidence prompt
     provider = self._get_provider()
     gen_response = provider.generate(gen_request)
     ...
     trace_recorder.record_step(stage="GENERATE_WORK_ORDER", ..., duration_ms=(time.time() - t0) * 1000)
     ```
  2. In `backend/app/evaluation/llm_evaluator.py` (lines 270–276, Phase 5C benchmark):
     ```python
     sample_prompt = (
         "### AUTHORITATIVE INDUSTRIAL INSPECTION EVIDENCE & CONTEXT PACKAGE:\n"
         "{\"inspection_id\": \"insp-benchmark-01\", \"asset_id\": \"ASSET-PL-01\", \"defect_type\": \"crack\", \"risk_score\": 90}\n\n"
         "### INSTRUCTIONS FOR WORK-ORDER DRAFT SYNTHESIS:\n"
         "Generate JSON with contextual_summary, engineering_justification, recommended_action, required_inspection_methods, safety_notes."
     )
     ```
- **Why It Matters:**
  1. **Ollama Cold Load:** If Ollama has unloaded `gemma3:latest` to disk due to idle timeout, the first call loads 4.3B parameters into VRAM (~25–30s) before token generation begins. With `--warmup 0`, this cold load was captured directly in Run 1.
  2. **Prompt Size & Complexity:** Phase 5C benchmarked an abbreviated 40-token synthetic prompt. In Phase 5D, `AgentPromptBuilder` injects full asset specs, 3 defect polygons, severity features, engineering threshold rules, and similar historical incidents (over 400 tokens), followed by generating 350+ tokens of rigorous JSON. On an RTX 3050 Laptop GPU, warm generation of this full draft takes ~28–32s. Cold load + full generation = ~61 seconds.
  3. **Stage Boundary:** `duration_ms` in `trace_recorder` includes prompt construction, Ollama HTTP generation, JSON validation, and grounding sanitization.
- **Required Correction:**
  - Execute a pre-benchmark warm-up call to Ollama to ensure the model is resident in VRAM before steady-state timing.
  - Document that the full end-to-end prompt payload is significantly richer than the isolated micro-prompt in Phase 5C.
- **Production Code Modification:** None. Production agent synthesis and Ollama client are working correctly.

---

### Finding 3: Warm-up Logic Fails to Guarantee Warm State When warmup=0
- **Classification:** `[SUSPICIOUS]`
- **Evidence from Source Code:**
  In `scripts/evaluation/reliability_runner.py` (lines 194–204):
  ```python
  print(f"Executing Warmup Runs: {n_warmup} cycle(s)...")
  for w_idx in range(n_warmup):
      _, _ = self.timer.run_instrumented_e2e(...)
  ```
- **Why It Matters:**
  When CLI users pass `--warmup 0 --runs 1`, the warmup loop is bypassed completely. The benchmark then immediately runs Run 1, marks it as "Steady-State Mean", and computes throughput from a cold-start cycle. This is misleading for an operational benchmark.
- **Required Correction:**
  - Introduce an explicit `warmup_subsystems()` function that pre-heats CUDA/YOLO and Ollama if steady-state measurement is requested, or clearly label runs as `[COLD START]` when `warmup == 0`.
- **Production Code Modification:** None.

---

### Finding 4: Multi-Image Workload & Failure Tests Execute Unconditionally
- **Classification:** `[BUG]` (CLI control logic)
- **Evidence from Source Code:**
  In `scripts/evaluation/benchmark_end_to_end.py` (lines 96–106):
  ```python
  # 2. Multi-Image Workload across 10 Real Images
  multi_img_data = []
  if not args.skip_multi_image:
      multi_img_data = runner.run_multi_image_workload(db=db)
  ...
  # 3. Controlled Failure Recovery Tests (10 scenarios)
  failure_tests = runner.run_failure_recovery_tests()
  ```
- **Why It Matters:**
  A user attempting a quick sanity check (`--runs 1 --warmup 0`) expected a 1-minute test, but the script automatically executed:
  - 1 run on `11112.jpg` (~68 s)
  - 10 full image inspections across the test set (~600 s)
  - 10 failure-recovery test cases (~50 s)
  Total: **720.32 seconds (12 minutes)**.
- **Required Correction:**
  - Add explicit CLI flags:
    - `--mode {all, repeatability, multi-image, failures, quick}`
    - `--skip-failures`
  - Allow developers to run isolated components without triggering the 12-minute full suite.
- **Production Code Modification:** None.

---

### Finding 5: Total Benchmark Duration Obscures Component Breakdown
- **Classification:** `[SUSPICIOUS]`
- **Evidence from Source Code:**
  In `scripts/evaluation/benchmark_end_to_end.py` (line 120):
  ```python
  total_dur_s = round(time.perf_counter() - t_total_start, 2)
  ```
- **Why It Matters:**
  `total_dur_s` (720.32 s) combines the repeatability trials, the 10-image workload, and failure recovery. The report presented this under "Total Benchmark Execution = 720.32 s" alongside "End-to-End Mean = 68.07 s", creating confusion as to where the 720 seconds were spent.
- **Required Correction:**
  - Explicitly break down execution time into:
    1. Primary Repeatability Benchmark Duration (s)
    2. Multi-Image Workload Duration (s)
    3. Failure Recovery Test Duration (s)
    4. Total Script Duration (s)
- **Production Code Modification:** None.

---

### Finding 6: Redundant Duplicate Retrieval and Processing in Benchmark Timer
- **Classification:** `[BUG]` (Benchmarking harness redundancy)
- **Evidence from Source Code:**
  In `scripts/evaluation/reliability_runner.py`:
  - Lines 133–163 execute tool lookups for asset context, maintenance history, thresholds, and incidents.
  - Lines 214–221 execute `inspection_decision_agent.run_inspection()`, which executes the identical database lookups all over again.
  - Lines 98–106 execute YOLO inference directly; line 115 executes `pipeline.run_inspection_evidence()`, which runs YOLO inference again.
- **Why It Matters:**
  Every inspection measured by the benchmark was actually performing **double perception and double database querying**. While the DB overhead was small (~200 ms), the architectural redundancy in the benchmarking script introduces noise and unmeasured orchestration deltas.
- **Required Correction:**
  Refactor `run_instrumented_e2e` to reuse the existing `ProcessingTrace` from `VisionEvidence` and `AgentReasoningTrace` from `AgentInspectionDecision` directly, rather than running stages twice.
- **Production Code Modification:** None.

---

## 3. Summary Classification Table

| Component / Subsystem | Issue Identified | Audit Classification | Needs Production Fix? |
| :--- | :--- | :---: | :---: |
| **YOLO Perception** | 5.25s was cold CUDA context & driver load on first run | `[EXPECTED COLD START]` | **NO** |
| **YOLO Harness** | YOLO inference executed twice per inspection | `[BUG]` (Harness only) | **NO** |
| **Gemma 3 Generation** | 61.26s was cold model load from disk + 400-token prompt | `[EXPECTED COLD START]` | **NO** |
| **Warm-up Handling** | `--warmup 0` reported cold-start run as "Steady-State" | `[SUSPICIOUS]` | **NO** |
| **CLI Workflow** | `--runs 1` ran 10-image workload and failure suite unconditionally | `[BUG]` (CLI only) | **NO** |
| **Report Breakdown** | 720s wall-clock lacked component phase breakdown | `[SUSPICIOUS]` | **NO** |
| **Decision Policy & Invariants** | Deterministic fields 100% consistent; Review gate enforced | `[CORRECT]` | **NO** |
| **Safety & Fallbacks** | All 10 failure modes handled safely; zero auto-dispatch | `[CORRECT]` | **NO** |

---

## 4. Recommended Fixes for Benchmarking Harness

1. **Refactor `PipelineStageTimer.run_instrumented_e2e` in `scripts/evaluation/reliability_runner.py`:**
   - Call `pipeline.run_inspection_evidence(...)` once.
   - Extract `validation_ms`, `preprocessing_ms`, `inference_ms`, `postprocessing_ms`, and `evidence_construction_ms` from `evidence.processing`.
   - Call `inspection_decision_agent.run_inspection(...)` once.
   - Extract stage durations directly from `decision.reasoning_trace`.
   - Time database persistence and review gate validation.
   - This eliminates all duplicate executions and guarantees exact stage-to-total alignment.
2. **Implement Explicit Subsystem Pre-Heating:**
   - When running steady-state benchmarks, run 1 dummy inference through YOLO (CUDA synchronized) and 1 dummy ping/generation through Ollama to load weights into VRAM before steady-state recording begins.
   - If `--warmup 0` is explicitly requested, tag the results as `[COLD START]` rather than `[STEADY STATE]`.
3. **Enhance CLI Options in `scripts/evaluation/benchmark_end_to_end.py`:**
   - Add `--mode {full, quick, repeatability, multi-image, failures}`.
   - Default `--mode quick` to run only 1 warmup + 1 measured run without running the 10-image suite.
   - Add `--skip-failures` flag.
4. **Separate Report Durations:**
   - In JSON and Markdown reports, break down total elapsed time into separate lines for Repeatability, Multi-Image Workload, and Failure Recovery.
