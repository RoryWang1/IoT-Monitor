import json
import math
import random
import os
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict

# Configuration
SIMULATION_DURATION = 60 # Seconds per phase
PHASES = ['Normal', 'Mirai', 'Exfiltration']
PACKET_LOSS_RATES = [0.0, 0.1, 0.3, 0.5]
ALPHA = 0.5 # Volume Weight (Default)
BETA = 0.5 # Frequency Weight (Default)

logger = logging.getLogger("AttackSim")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class TimeStep:
    timestamp: int
    phase: str
    packet_count: int
    byte_count: int
    distinct_ports: List[int]
    risk_score: float
    packet_loss_rate: float

def simulate_traffic(phase: str, loss_rate: float) -> (int, int, List[int]):
    """Generate traffic stats for a single second based on phase."""
    
    # 1. Generate ideal traffic
    if phase == 'Normal':
        # Web browsing / MQTT: Moderate packets, moderate bytes
        packets = random.randint(10, 50)
        bytes_vol = packets * random.randint(500, 1500) # Avg 1KB
        ports = [80, 443, 1883]
    elif phase == 'Mirai':
        # Botnet Scanning: High packets, Tiny bytes
        packets = random.randint(200, 500) 
        bytes_vol = packets * random.randint(40, 100) # Avg 60B
        ports = [23, 2323, 8080]
    elif phase == 'Exfiltration':
        # Data Theft: Low packets, Huge bytes
        packets = random.randint(20, 60)
        bytes_vol = packets * random.randint(10000, 50000) # Avg 30KB (Jumbo frames)
        ports = [443] # Hiding in HTTPS
        
    # 2. Apply Packet Loss (Robustness)
    packets = int(packets * (1.0 - loss_rate))
    bytes_vol = int(bytes_vol * (1.0 - loss_rate))
    
    return packets, bytes_vol, ports

def calculate_risk_score(packets: int, bytes_vol: int, ports: List[int]) -> float:
    """
    The Core Algorithm (Python implementation of Eq. 4).
    Score = alpha * Log(Bytes) + beta * Frequency_Score + Port_Penalty
    """
    if packets == 0: return 0.0
    
    # 1. Log-Normalized Volume Score
    # Assume Max observed bytes = 1,000,000 for normalization
    v_score = math.log10(bytes_vol + 1) / math.log10(1000000 + 1)  
    v_score = min(v_score, 1.0)
    
    # 2. Frequency Score (Packets per second normalized)
    # Assume Max normal pps = 100
    f_score = min(packets / 100.0, 1.0) 
    
    # 3. Port Penalty
    port_penalty = 0.0
    dangerous_ports = [23, 2323, 22]
    if any(p in dangerous_ports for p in ports):
        port_penalty = 0.4
        
    # Total Score
    # Specific tuning: Mirai triggers F-score, Exfil triggers V-score
    # In real backend this comes from config, here we test the theory.
    
    # Normal traffic should be < 0.5
    # Attack traffic should be > 0.7
    
    # Mirai: High F-score (1.0), Low V-score (~0.2). Eq: 0.5*0.2 + 0.5*1.0 + 0.4 = 0.1 + 0.5 + 0.4 = 1.0 (Detected)
    # Exfil: Low F-score (~0.3), High V-score (1.0). Eq: 0.5*1.0 + 0.5*0.3 + 0.0 = 0.5 + 0.15 = 0.65 (Suspicious)
    
    total = (ALPHA * v_score) + (BETA * f_score) + port_penalty
    return min(total, 1.0) * 100 # Scale to 0-100

def run_simulation() -> List[TimeStep]:
    results = []
    
    for loss in PACKET_LOSS_RATES:
        logger.info(f"Running Simulation with {loss*100}% Packet Loss...")
        
        current_time = 0
        for phase in PHASES:
            for _ in range(SIMULATION_DURATION):
                packets, bytes_vol, ports = simulate_traffic(phase, loss)
                score = calculate_risk_score(packets, bytes_vol, ports)
                
                results.append(TimeStep(
                    timestamp=current_time,
                    phase=phase,
                    packet_count=packets,
                    byte_count=bytes_vol,
                    distinct_ports=ports,
                    risk_score=score,
                    packet_loss_rate=loss
                ))
                current_time += 1
                
    return results

def main():
    data = run_simulation()
    
    # Convert to pure dict list
    output = [asdict(d) for d in data]
    
    os.makedirs("tests/results", exist_ok=True)
    with open("tests/results/attack_simulation_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    logger.info("Attack simulation results saved.")

if __name__ == "__main__":
    main()
