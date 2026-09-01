"""Inference benchmarking script: measures cold model load time, warm latency distributions, and determinism."""

import json
import statistics
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch
from vision.inference.pipeline import InferencePipeline
from vision.models.yolo_seg import YOLOSegmentationModel

MODEL_PATH = Path("experiments/vision/deepcrack/baseline/weights/best.pt")
TEST_IMAGE = Path("data/processed/deepcrack/yolo/images/test/11112.jpg")


def benchmark_inference(num_warmup: int = 5, num_iterations: int = 25):
    print("=== Vision Inference Latency & Determinism Benchmark ===")
    if not MODEL_PATH.exists():
        print(f"Error: Model checkpoint {MODEL_PATH} not found.", file=sys.stderr)
        return
    if not TEST_IMAGE.exists():
        print(f"Error: Test image {TEST_IMAGE} not found.", file=sys.stderr)
        return

    device = "0" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    # 1. Cold Load Timing
    t0 = time.perf_counter()
    model = YOLOSegmentationModel(model_path=MODEL_PATH, device=device, confidence_threshold=0.25)
    model.load()
    pipeline = InferencePipeline(model=model)
    cold_load_time_ms = (time.perf_counter() - t0) * 1000.0
    print(f"Cold Model Load Time: {cold_load_time_ms:.2f} ms")

    # 2. Warmup iterations
    print(f"\nWarming up ({num_warmup} iterations)...")
    for _ in range(num_warmup):
        _ = pipeline.run_inspection_evidence(str(TEST_IMAGE), component_id="PIPE-BENCH")

    # 3. Timed Iterations
    print(f"Benchmarking ({num_iterations} iterations)...")
    latencies_inf = []
    latencies_total = []
    detection_counts = []
    confidences = []

    for i in range(num_iterations):
        t_iter_start = time.perf_counter()
        ev = pipeline.run_inspection_evidence(str(TEST_IMAGE), component_id="PIPE-BENCH")
        t_iter_end = time.perf_counter()

        latencies_inf.append(ev.processing.inference_ms)
        latencies_total.append((t_iter_end - t_iter_start) * 1000.0)
        detection_counts.append(len(ev.detections))
        if ev.detections:
            confidences.append(ev.detections[0].confidence)

    # 4. Determinism Check
    is_count_deterministic = len(set(detection_counts)) == 1
    max_conf_diff = max(confidences) - min(confidences) if confidences else 0.0
    is_conf_deterministic = max_conf_diff < 1e-4

    # 5. GPU VRAM
    vram_allocated_mb = 0.0
    if torch.cuda.is_available():
        vram_allocated_mb = torch.cuda.memory_allocated(0) / (1024 * 1024)

    benchmark_results = {
        "device": device,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "gpu_vram_allocated_mb": round(vram_allocated_mb, 2),
        "cold_load_time_ms": round(cold_load_time_ms, 2),
        "iterations": num_iterations,
        "inference_latency_ms": {
            "mean": round(statistics.mean(latencies_inf), 2),
            "median": round(statistics.median(latencies_inf), 2),
            "min": round(min(latencies_inf), 2),
            "max": round(max(latencies_inf), 2),
            "std": round(statistics.stdev(latencies_inf), 2) if len(latencies_inf) > 1 else 0.0
        },
        "total_latency_ms": {
            "mean": round(statistics.mean(latencies_total), 2),
            "median": round(statistics.median(latencies_total), 2),
            "min": round(min(latencies_total), 2),
            "max": round(max(latencies_total), 2),
        },
        "determinism": {
            "detection_count_stable": is_count_deterministic,
            "detection_count": detection_counts[0] if detection_counts else 0,
            "confidence_max_delta": round(max_conf_diff, 6),
            "confidence_stable": is_conf_deterministic
        }
    }

    out_file = Path("experiments/vision/deepcrack/reports/benchmark_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    print("\n--- Benchmark Summary ---")
    print(f"  Inference Latency (Mean):   {benchmark_results['inference_latency_ms']['mean']} ms")
    print(f"  Inference Latency (Median): {benchmark_results['inference_latency_ms']['median']} ms")
    print(f"  Inference Latency (Min):    {benchmark_results['inference_latency_ms']['min']} ms")
    print(f"  Inference Latency (Max):    {benchmark_results['inference_latency_ms']['max']} ms")
    print(f"  Total Latency (Mean):       {benchmark_results['total_latency_ms']['mean']} ms")
    print(f"  GPU VRAM Allocated:         {benchmark_results['gpu_vram_allocated_mb']} MB")
    print(f"  Detection Count Stable:     {is_count_deterministic} ({detection_counts[0]} detections)")
    print(f"  Confidence Max Delta:       {max_conf_diff:.6f}")
    print(f"  Saved to:                   {out_file}")

    return benchmark_results


if __name__ == "__main__":
    benchmark_inference()
