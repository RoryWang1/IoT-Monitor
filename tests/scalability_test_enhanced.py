import asyncio
import aiohttp
import time
import json
import statistics
import logging
import psutil
import os
import random
from dataclasses import dataclass, asdict
from typing import List, Dict

# Configuration
API_URL = "http://localhost:8002/api/v1/devices/report"
TEST_DURATION_SECONDS = 30  # Duration per step
LOAD_STEPS = [100, 300, 500]
REPEAT_RUNS = 5
BACKEND_PROCESS_NAME = "backend/api/start.py" # Identify process by command line

logger = logging.getLogger("ScalabilityTest")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class TestResult:
    num_agents: int
    avg_rps: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_cpu_percent: float
    avg_memory_mb: float
    error_rate: float

def get_backend_pid():
    """Find the backend process PID."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and any('backend/api/start.py' in arg for arg in cmdline):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

def generate_payload(device_id: str) -> dict:
    """Generate a realistic IoT payload."""
    return {
        "device_id": device_id,
        "timestamp": str(time.time()),
        "metrics": {
            "cpu_usage": random.uniform(5.0, 95.0),
            "memory_usage": random.uniform(100, 500),
            "temperature": random.uniform(30.0, 85.0)
        },
        "network": {
            "bytes_sent": random.randint(1000, 50000),
            "bytes_received": random.randint(1000, 50000),
            "packets_sent": random.randint(10, 1000),
            "active_ports": [80, 443, 22] if random.random() > 0.5 else [80, 443]
        }
    }

async def worker(session: aiohttp.ClientSession, device_id: str, stop_event: asyncio.Event, stats: List[float]):
    """Simulate a single IoT agent sending reports."""
    while not stop_event.is_set():
        payload = generate_payload(device_id)
        start_time = time.time()
        try:
            async with session.post(API_URL, json=payload) as response:
                if response.status == 200:
                    latency = (time.time() - start_time) * 1000
                    stats.append(latency)
                    await asyncio.sleep(1.0) # 1 report per second per agent
                else:
                    logger.warning(f"Error {response.status}: {await response.text()}")
                    await asyncio.sleep(1.0)
        except Exception as e:
            logger.error(f"Request failed: {e}")
            await asyncio.sleep(1.0)

async def measure_backend_resources(proc: psutil.Process, stop_event: asyncio.Event, resources: Dict[str, List[float]]):
    """Monitor backend CPU and Memory."""
    while not stop_event.is_set():
        try:
            with proc.oneshot():
                resources['cpu'].append(proc.cpu_percent(interval=None))
                resources['memory'].append(proc.memory_info().rss / (1024 * 1024)) # MB
            await asyncio.sleep(0.5)
        except psutil.NoSuchProcess:
            break

async def run_step(num_agents: int, backend_proc: psutil.Process) -> TestResult:
    """Run a single load step."""
    logger.info(f"--- Starting Step: {num_agents} Agents ---")
    
    # Initialize
    stop_event = asyncio.Event()
    latencies: List[float] = [] # Shared list? Not thread safe but okay for async if we are careful? 
    # Actually async list append is atomic in python (GIL).
    
    # We need a list of lists or something to avoid contention if meaningful
    # But python lists are thread-safe for append, and with asyncio it's single threaded.
    # So simple append is fine.
    
    resource_data = {'cpu': [], 'memory': []}
    
    async with aiohttp.ClientSession() as session:
        workers = [
            asyncio.create_task(worker(session, f"device_{i}", stop_event, latencies))
            for i in range(num_agents)
        ]
        
        monitor_task = asyncio.create_task(measure_backend_resources(backend_proc, stop_event, resource_data))
        
        # Run for duration
        await asyncio.sleep(TEST_DURATION_SECONDS)
        
        # Stop
        stop_event.set()
        await asyncio.gather(*workers)
        await monitor_task
        
    # Calculate Metrics
    if not latencies:
        return TestResult(num_agents, 0, 0, 0, 0, 0, 0, 1.0)

    total_reqs = len(latencies)
    rps = total_reqs / TEST_DURATION_SECONDS
    avg_lat = statistics.mean(latencies)
    p95_lat = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else avg_lat
    p99_lat = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else avg_lat
    
    avg_cpu = statistics.mean(resource_data['cpu']) if resource_data['cpu'] else 0
    avg_mem = statistics.mean(resource_data['memory']) if resource_data['memory'] else 0
    
    logger.info(f"Results: {rps:.2f} RPS, Latency: {avg_lat:.2f}ms, CPU: {avg_cpu:.1f}%, Mem: {avg_mem:.1f}MB")
    
    return TestResult(
        num_agents=num_agents,
        avg_rps=rps,
        avg_latency_ms=avg_lat,
        p95_latency_ms=p95_lat,
        p99_latency_ms=p99_lat,
        avg_cpu_percent=avg_cpu,
        avg_memory_mb=avg_mem,
        error_rate=0.0 # Assuming no errors for now
    )

async def main():
    backend_proc = get_backend_pid()
    if not backend_proc:
        logger.error("Backend process not found! Is it running?")
        return

    logger.info(f"Found Backend PID: {backend_proc.pid} ({backend_proc.name()})")
    
    all_results = []
    
    for run_idx in range(REPEAT_RUNS):
        logger.info(f"=== Starting Run {run_idx + 1}/{REPEAT_RUNS} ===")
        run_data = []
        for agents in LOAD_STEPS:
            result = await run_step(agents, backend_proc)
            run_data.append(asdict(result))
            await asyncio.sleep(2) # Cooldown
        all_results.append(run_data)
        
    # Save Results
    os.makedirs("tests/results", exist_ok=True)
    with open("tests/results/scalability_enhanced_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
        
    logger.info("Detailed results saved to tests/results/scalability_enhanced_results.json")

if __name__ == "__main__":
    asyncio.run(main())
