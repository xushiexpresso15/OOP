import sys
import time
from typing import Optional
from grid_env import GridTrafficEnv

def run_grid_simulation(
    vehicle_count: int = 5,
    seed: int = None,
    max_steps: int = 1000,
    grid_size: int = 5,
    agent_mode: bool = False
) -> dict:
    import time as time_module
    import pygame
    from grid_env import GridTrafficEnv
    
    env = GridTrafficEnv(render_mode="human", seed=seed, grid_size=grid_size, max_steps=max_steps)
    env.set_fixed_vehicle_mode(vehicle_count)
    
    if agent_mode:
        env.set_agent_mode(True)
    
    obs, info = env.reset()
    
    print(f"Grid: {env.grid_map.actual_width}x{env.grid_map.actual_height}")
    print(f"Intersections: {info['intersection_count']}")
    print(f"Vehicles spawned: {info['vehicle_count']}")
    print("\nRunning simulation... (Press X to close window)")
    
    start_time = time_module.time()
    step = 0
    user_quit = False
    
    while step < max_steps and not user_quit:
        if agent_mode:
            import agent
            agent.step(env)
        
        obs, reward, term, trunc, info = env.step(0)
        env.render()
        step += 1
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("\n[Window closed by user]")
                user_quit = True
                break
        
        if user_quit:
            break
        
        if info['vehicle_count'] == 0:
            break
    
    end_time = time_module.time()
    elapsed = end_time - start_time
    
    result = {
        "total_steps": step,
        "vehicles_arrived": info['arrived_count'],
        "target_vehicles": vehicle_count,
        "time_elapsed": elapsed,
        "completed": info['arrived_count'] == vehicle_count,
        "user_quit": user_quit,
    }
    
    print("\n" + "=" * 60)
    if user_quit:
        print("SIMULATION ABORTED")
    else:
        print("SIMULATION COMPLETE")
    print("=" * 60)
    print(f"Total steps: {step}")
    total_spawned = info.get('total_spawned', vehicle_count)
    print(f"Vehicles arrived: {info['arrived_count']} / {total_spawned}")
    print(f"Time elapsed: {elapsed:.2f} seconds")
    if step > 0:
        print(f"Average: {elapsed/step:.4f} seconds/step")
    print("=" * 60)
    
    env.close()
    return result

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = "help"
    
    if mode in ["random", "agent"] and len(sys.argv) > 2 and sys.argv[2].lower() in ["small", "medium", "large"]:
        run_mode = mode
        grid_mode = sys.argv[2].lower()
        
        grid_sizes = { #地圖大小
            "small": 5,
            "medium": 11,
            "large": 21,
        }
        
        if grid_mode not in grid_sizes:
            print(f"Error: Unknown grid size '{grid_mode}'")
            print("Valid sizes: small, medium, large")
            sys.exit(1)
        
        grid_size = grid_sizes[grid_mode]
        size_name = {5: "Small (5x5)", 11: "Medium (11x11)", 21: "Large (21x21)"}
        
        print("=" * 60)
        print(f"Smart Traffic Grid - {size_name.get(grid_size)}")
        print(f"Mode: {run_mode.upper()}")
        print("=" * 60)
        
        vehicle_count = max(5, grid_size // 2)
        
        if len(sys.argv) > 3:
            try:
                vehicle_count = int(sys.argv[3])
            except ValueError:
                pass
        
        import random as rand_module
        seed = rand_module.randint(1, 99999)
        
        print(f"Grid size: {grid_size}x{grid_size} (actual: {grid_size*2+1}x{grid_size*2+1})")
        print(f"Vehicles: {vehicle_count}")
        print(f"Seed: {seed}")
        
        if run_mode == "random":
            run_grid_simulation(vehicle_count, seed=seed, grid_size=grid_size)
        else:
            print("\n[Agent mode - Manual traffic light control]")
            print("Running agent logic from agent.py...")
            run_grid_simulation(vehicle_count, seed=seed, grid_size=grid_size, agent_mode=True)
    else:
        print("Usage: python main.py <mode> <grid_size> [vehicle_count]")
        print("\nEx:")
        print("  py main.py random small 10")
        print("  py main.py agent medium 20")
