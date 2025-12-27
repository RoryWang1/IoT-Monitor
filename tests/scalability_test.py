import asyncio
import aiohttp
import time
import random
import json
import logging
from datetime import datetime

# Configuration
API_URL = "http://localhost:8002/api/v1/devices/report"  # Adjust endpoint as needed
NUM_AGENTS = 500  # Target concurrency
DURATION_SECONDS = 60
REPORT_INTERVAL = 1.0  # Seconds between reports per agent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VirtualAgent:
    def __init__(self, agent_id, session):
        self.agent_id = f"virtual-agent-{agent_id:04d}"
        self.session = session
        self.is_active = True

    async def run(self):
        while self.is_active:
            try:
                start_time = time.time()
                payload = self.generate_payload()
                async with self.session.post(API_URL, json=payload) as response:
                    latency = (time.time() - start_time) * 1000
                    status = response.status
                    # logger.debug(f"Agent {self.agent_id}: Status {status}, Latency {latency:.2f}ms")
                    StatsCollector.record(status, latency)
            except Exception as e:
                logger.error(f"Agent {self.agent_id} error: {e}")
                StatsCollector.record("error", 0)
            
            await asyncio.sleep(REPORT_INTERVAL + random.uniform(-0.1, 0.1))

    def generate_payload(self):
        # Simulate realistic IoT payload
        return {
            "device_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "cpu_usage": random.uniform(10, 80),
                "memory_usage": random.uniform(20, 60),
                "temperature": random.uniform(30, 60)
            },
            "network": {
                "bytes_sent": random.randint(100, 5000),
                "bytes_received": random.randint(100, 5000),
                "packets_sent": random.randint(10, 50),
                "active_ports": [80, 443, 22] if random.random() > 0.9 else [80]
            }
        }

class StatsCollector:
    requests = 0
    errors = 0
    latencies = []
    
    @classmethod
    def record(cls, status, latency):
        cls.requests += 1
        if status != 200:
            cls.errors += 1
        else:
            cls.latencies.append(latency)

async def main():
    logger.info(f"Starting Scalability Test: {NUM_AGENTS} Agents, {DURATION_SECONDS}s Duration")
    
    async with aiohttp.ClientSession() as session:
        agents = [VirtualAgent(i, session) for i in range(NUM_AGENTS)]
        
        # Start all agents
        tasks = [asyncio.create_task(agent.run()) for agent in agents]
        
        # Run for duration
        start_time = time.time()
        while (time.time() - start_time) < DURATION_SECONDS:
            await asyncio.sleep(5)
            # Periodic status report
            current_reqs = StatsCollector.requests
            elapsed = time.time() - start_time
            rps = current_reqs / elapsed
            avg_lat = sum(StatsCollector.latencies) / len(StatsCollector.latencies) if StatsCollector.latencies else 0
            logger.info(f"Time: {elapsed:.1f}s | RPS: {rps:.2f} | Avg Latency: {avg_lat:.2f}ms | Errors: {StatsCollector.errors}")
            
        # Stop agents
        for agent in agents:
            agent.is_active = False
        
        # Cancel tasks
        for task in tasks:
            task.cancel()
            
    # Final Report
    total_reqs = StatsCollector.requests
    avg_lat = sum(StatsCollector.latencies) / len(StatsCollector.latencies) if StatsCollector.latencies else 0
    logger.info("="*50)
    logger.info("FINAL RESULTS")
    logger.info(f"Total Requests: {total_reqs}")
    logger.info(f"Average RPS: {total_reqs / DURATION_SECONDS:.2f}")
    logger.info(f"Average Latency: {avg_lat:.2f}ms")
    logger.info(f"Error Rate: {(StatsCollector.errors / total_reqs)*100:.2f}%")
    logger.info("="*50)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
