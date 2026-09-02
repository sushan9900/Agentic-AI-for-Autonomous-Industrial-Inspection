"""System, process, and GPU resource monitoring for Phase 5D performance benchmarking."""

import os
import platform
import sys
from typing import Any, Dict, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


class ResourceMonitor:
    """Monitors system hardware, process memory, and CUDA GPU VRAM utilization."""

    def __init__(self) -> None:
        self.process = psutil.Process(os.getpid()) if PSUTIL_AVAILABLE else None

    @staticmethod
    def get_environment_info() -> Dict[str, Any]:
        """Collects detected system and execution environment telemetry."""
        cuda_available = TORCH_AVAILABLE and torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_available else "NOT_AVAILABLE"
        gpu_device_count = torch.cuda.device_count() if cuda_available else 0

        # CUDA VRAM total capacity
        gpu_vram_total_mb = "NOT_AVAILABLE"
        if cuda_available:
            try:
                gpu_vram_total_mb = round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 2)
            except Exception:
                pass

        return {
            "os_system": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "python_version": sys.version.split()[0],
            "pytorch_version": torch.__version__ if TORCH_AVAILABLE else "NOT_AVAILABLE",
            "cuda_available": cuda_available,
            "gpu_device_count": gpu_device_count,
            "gpu_name": gpu_name,
            "gpu_vram_total_mb": gpu_vram_total_mb
        }

    def reset_gpu_peak_stats(self) -> None:
        """Resets peak CUDA memory tracking stats for stage/run isolation."""
        if TORCH_AVAILABLE and torch.cuda.is_available():
            try:
                torch.cuda.reset_peak_memory_stats(0)
            except Exception:
                pass

    def sample_resources(self) -> Dict[str, Any]:
        """Captures a snapshot of current host, process, and GPU memory metrics."""
        # 1. CPU & RAM
        cpu_percent = "NOT_AVAILABLE"
        process_rss_mb = "NOT_AVAILABLE"
        system_ram_total_mb = "NOT_AVAILABLE"
        system_ram_available_mb = "NOT_AVAILABLE"
        system_ram_percent = "NOT_AVAILABLE"

        if PSUTIL_AVAILABLE and self.process is not None:
            try:
                cpu_percent = psutil.cpu_percent(interval=None)
                mem_info = self.process.memory_info()
                process_rss_mb = round(mem_info.rss / (1024 * 1024), 2)

                sys_mem = psutil.virtual_memory()
                system_ram_total_mb = round(sys_mem.total / (1024 * 1024), 2)
                system_ram_available_mb = round(sys_mem.available / (1024 * 1024), 2)
                system_ram_percent = sys_mem.percent
            except Exception:
                pass

        # 2. GPU VRAM
        gpu_allocated_mb = "NOT_AVAILABLE"
        gpu_reserved_mb = "NOT_AVAILABLE"
        gpu_peak_allocated_mb = "NOT_AVAILABLE"

        if TORCH_AVAILABLE and torch.cuda.is_available():
            try:
                gpu_allocated_mb = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 2)
                gpu_reserved_mb = round(torch.cuda.memory_reserved(0) / (1024 * 1024), 2)
                gpu_peak_allocated_mb = round(torch.cuda.max_memory_allocated(0) / (1024 * 1024), 2)
            except Exception:
                pass

        return {
            "cpu_utilization_percent": cpu_percent,
            "process_rss_mb": process_rss_mb,
            "system_ram_total_mb": system_ram_total_mb,
            "system_ram_available_mb": system_ram_available_mb,
            "system_ram_percent": system_ram_percent,
            "gpu_allocated_mb": gpu_allocated_mb,
            "gpu_reserved_mb": gpu_reserved_mb,
            "gpu_peak_allocated_mb": gpu_peak_allocated_mb
        }
