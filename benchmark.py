
import sys
import os

# Ensure we can import modules from the current directory
sys.path.append(os.getcwd())

from main import run_grid_simulation

def run_comparison():
    print("Running Traffic Simulation Comparison...")
    print("=" * 60)
    
    grid_size = 11 # Medium
    vehicle_count = 20
    seed = 42 # Fixed seed for fair comparison
    
    # 1. Run Baseline (Random)
    print(f"\n[1/2] Running Baseline (Random Logic)...")
    base_result = run_grid_simulation(
        vehicle_count=vehicle_count,
        seed=seed,
        grid_size=grid_size,
        agent_mode=False # Random mode
    )
    
    # 2. Run Agent (Smart Logic)
    print(f"\n[2/2] Running Agent (Smart Logic)...")
    agent_result = run_grid_simulation(
        vehicle_count=vehicle_count,
        seed=seed,
        grid_size=grid_size,
        agent_mode=True # Agent mode
    )
    
    # 3. Generate Report
    report = []
    report.append("Traffic Control Performance Comparison")
    report.append("======================================")
    report.append(f"Map Size: Medium (11x11)")
    report.append(f"Vehicles: {vehicle_count}")
    report.append(f"Seed: {seed}")
    report.append("")
    report.append(f"{'Metric':<20} | {'Baseline (Random)':<15} | {'Agent (Smart)':<15} | {'Improvement'}")
    report.append("-" * 75)
    
    # Metrics
    metrics = [
        ("Time Elapsed (s)", "time_elapsed", False), # False means lower is better
        ("Steps Taken", "total_steps", False),
        ("Vehicles Arrived", "vehicles_arrived", True) # True means higher is better
    ]
    
    for label, key, higher_is_better in metrics:
        base_val = base_result[key]
        agent_val = agent_result[key]
        
        diff = agent_val - base_val
        pct = 0
        if base_val != 0:
            pct = (diff / base_val) * 100
            
        sign = "+" if diff > 0 else ""
        
        # Determine if improved
        improved = False
        if higher_is_better and diff > 0: improved = True
        if not higher_is_better and diff < 0: improved = True
        
        imp_str = "BETTER" if improved else "WORSE"
        if diff == 0: imp_str = "SAME"
        
        report.append(f"{label:<20} | {base_val:<15.2f} | {agent_val:<15.2f} | {sign}{pct:.1f}% ({imp_str})")
        
    report.append("-" * 75)
    report.append("\nImplementation Logic:")
    report.append("1. Baseline: Traffic lights cycle automatically on fixed/random timers.")
    report.append("2. Agent: Monitors queue lengths at each intersection.")
    report.append("   - Calculates green light duration: Min 5s + (3s * waiting_cars).")
    report.append("   - Max limitation: 30s.")
    report.append("   - Switches priority dynamically based on traffic demand.")

    report_text = "\n".join(report)
    print("\n" + report_text)
    
    # Save to file
    with open("comparison_result.txt", "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nReport saved to {os.path.abspath('comparison_result.txt')}")

if __name__ == "__main__":
    run_comparison()
