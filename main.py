"""
main.py - 執行入口
Smart Traffic Intersection Environment

整合測試腳本，用於：
1. 實例化 TrafficEnv
2. 執行隨機動作迴圈測試
3. 驗證 reset() 和 step() 功能
4. 測試視覺化渲染
"""

import sys
import time
from typing import Optional

# 導入環境

# 導入環境
from grid_env import GridTrafficEnv


# =============================================================================
# Grid Simulation (Modular)
# =============================================================================

def run_grid_simulation(
    vehicle_count: int = 5,
    seed: int = None,
    max_steps: int = 1000,
    grid_size: int = 5,
    agent_mode: bool = False
) -> dict:
    """
    執行網格交通模擬 (模組化函式)
    
    Args:
        vehicle_count: 車輛數量
        seed: 隨機種子
        max_steps: 最大步數
        grid_size: 網格邏輯大小 (5=small, 11=medium, 21=large)
        agent_mode: 是否為 Agent 模式 (手動控制紅綠燈)
        
    Returns:
        Dict: 模擬結果統計
    """
    import time as time_module
    import pygame
    from grid_env import GridTrafficEnv
    
    # 創建環境
    env = GridTrafficEnv(render_mode="human", seed=seed, grid_size=grid_size, max_steps=max_steps)
    env.set_fixed_vehicle_mode(vehicle_count)
    
    # 設定 Agent 模式
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
        # Agent 決策
        if agent_mode:
            import agent
            agent.step(env)
        
        # 先執行環境步驟和渲染 (這會初始化 pygame)
        obs, reward, term, trunc, info = env.step(0)
        env.render()
        step += 1
        
        # 處理 pygame 事件 (關閉視窗) - 必須在 render 之後
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("\n[Window closed by user]")
                user_quit = True
                break
        
        if user_quit:
            break
        
        # 檢查是否所有車輛都已到達 (沒有車輛在路上)
        if info['vehicle_count'] == 0:
            break
    
    end_time = time_module.time()
    elapsed = end_time - start_time
    
    # 結果統計
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


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    # 解析命令列參數
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = "help"
    
    if mode in ["random", "agent"] and len(sys.argv) > 2 and sys.argv[2].lower() in ["small", "medium", "large"]:
        run_mode = mode
        grid_mode = sys.argv[2].lower()
        
        # 決定網格大小
        grid_sizes = {
            "small": 5,     # 5x5 邏輯 = 11x11 實際
            "medium": 11,   # 11x11 邏輯 = 23x23 實際
            "large": 21,    # 21x21 邏輯 = 43x43 實際
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
        
        # 解析車輛數量
        vehicle_count = max(5, grid_size // 2)
        
        if len(sys.argv) > 3:
            try:
                vehicle_count = int(sys.argv[3])
            except ValueError:
                pass
        
        # 使用隨機種子
        import random as rand_module
        seed = rand_module.randint(1, 99999)
        
        print(f"Grid size: {grid_size}x{grid_size} (actual: {grid_size*2+1}x{grid_size*2+1})")
        print(f"Vehicles: {vehicle_count}")
        print(f"Seed: {seed}")
        
        if run_mode == "random":
            # Random 模式：紅綠燈自動循環
            run_grid_simulation(vehicle_count, seed=seed, grid_size=grid_size)
        else:
            # Agent 模式：紅綠燈由 Agent 控制
            print("\n[Agent mode - Manual traffic light control]")
            print("Running agent logic from agent.py...")
            run_grid_simulation(vehicle_count, seed=seed, grid_size=grid_size, agent_mode=True)
    else:
        print("Usage: python main.py <mode> <grid_size> [vehicle_count]")
        print("\nModes:")
        print("  random <size> [N]  - Random mode (traffic lights auto-cycle)")
        print("  agent <size> [N]   - Agent mode (manual traffic light control)")
        print("\nGrid sizes:")
        print("  small   - 5x5 maze (11x11 actual)")
        print("  medium  - 11x11 maze (23x23 actual)")
        print("  large   - 21x21 maze (43x43 actual)")
        print("\nExamples:")
        print("  py main.py random small 10")
        print("  py main.py agent medium 20")
