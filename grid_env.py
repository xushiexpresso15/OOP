"""
grid_env.py - 網格環境模組
Smart Traffic Intersection Environment (10x10 Grid)

10x10 網格版本的 Gymnasium 環境：
- 多個路口獨立紅綠燈
- 車輛使用 Dijkstra 導航到邊界出口
- Perlin noise 生成道路
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import random

from objects import Vehicle, Car, Ambulance, Direction
from grid_map import GridMap, GridCell, Intersection


class GridTrafficEnv(gym.Env):
    """
    10x10 網格交通環境
    
    Observation Space:
        - 每個格子的狀態 (100 維)
        - 車輛數量和位置資訊
        
    Action Space:
        - Discrete(1): 只有 HOLD (紅綠燈自動循環)
    """
    
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 10}
    
    # 環境參數
    GRID_SIZE = 5  # 5x5 迷宮 (實際 11x11 含牆壁)
    MAX_VEHICLES = 10
    VEHICLE_SPAWN_PROB = 0.15
    AMBULANCE_SPAWN_PROB = 0.02
    MAX_STEPS = 300
    
    def __init__(self, render_mode: Optional[str] = None, seed: int = None, grid_size: int = 5, max_steps: int = 300):
        """
        初始化網格環境
        
        Args:
            render_mode: 渲染模式
            seed: 隨機種子 (用於地圖生成)
            grid_size: 邏輯網格大小 (5=small, 11=medium, 21=large)
            max_steps: 最大步數
        """
        super().__init__()
        
        self.render_mode = render_mode
        self.map_seed = seed
        self.grid_size = grid_size
        self.max_steps = max_steps
        
        # 根據網格大小調整參數
        if grid_size <= 5:
            self.MAX_VEHICLES = 10
        elif grid_size <= 11:
            self.MAX_VEHICLES = 25
        else:
            self.MAX_VEHICLES = 50
        
        # Action Space: 只有 HOLD
        self.action_space = spaces.Discrete(1)
        
        # Observation Space: 簡化版
        # [車輛數量, 已到達數量, 路口紅綠燈狀態...]
        obs_size = 2 + grid_size * grid_size
        self.observation_space = spaces.Box(
            low=0, high=100, shape=(obs_size,), dtype=np.float32
        )
        
        # 內部狀態
        self.grid_map: Optional[GridMap] = None
        self.vehicles: List[Vehicle] = []
        self.current_step = 0
        self.arrived_count = 0
        
        # 固定車輛模式
        self._fixed_vehicle_mode = False
        self._fixed_vehicle_count = 0
        
        # Agent 模式 (手動控制紅綠燈)
        self._agent_mode = False
        
        # 渲染器
        self._renderer = None
    
    # =========================================================================
    # 模式設定
    # =========================================================================
    
    def set_fixed_vehicle_mode(self, vehicle_count: int):
        """
        設定固定車輛模式
        
        在此模式下，只會在 reset 時生成指定數量的車輛，
        之後不會再生成新車輛。
        
        Args:
            vehicle_count: 要生成的車輛數量
        """
        self._fixed_vehicle_mode = True
        self._fixed_vehicle_count = vehicle_count
    
    def set_agent_mode(self, enabled: bool = True):
        """
        設定 Agent 模式
        
        在 Agent 模式下：
        - 紅綠燈不會自動更新
        - Agent 需要手動呼叫 control_intersection() 來控制紅綠燈
        
        Args:
            enabled: 是否啟用 Agent 模式
        """
        self._agent_mode = enabled
    
    # =========================================================================
    # Agent 紅綠燈控制 API
    # =========================================================================
    
    def get_intersections(self) -> list:
        """
        取得所有路口列表 (用於 Agent)
        
        Returns:
            list: 路口物件列表
        """
        if self.grid_map is None:
            return []
        return list(self.grid_map.intersections.values())
    
    def get_intersection_states(self) -> list:
        """
        取得所有路口狀態 (用於 Agent 觀察)
        
        Returns:
            list: 每個路口的狀態字典
        """
        return [inter.get_state() for inter in self.get_intersections()]
    
    def get_vehicle_states(self) -> list:
        """
        取得所有車輛狀態 (用於 Agent 觀察)
        
        Returns:
            list: 每個車輛的狀態字典
                {
                    'position': (x, y),       # 當前網格位置
                    'destination': (x, y),    # 目的地網格位置
                    'direction': str,         # 行進方向 ('n', 's', 'e', 'w')
                    'type': str,              # 'car' 或 'ambulance'
                    'wait_time': int          # 已等待時間
                }
        """
        states = []
        for v in self.vehicles:
            if v.grid_position:
                states.append({
                    'position': v.grid_position,
                    'destination': v.destination,
                    'direction': v.direction.value,  # Enum to value
                    'type': 'ambulance' if isinstance(v, Ambulance) else 'car',
                    'wait_time': v.wait_time
                })
        return states
    
    def control_intersection(self, position: Tuple[int, int], action: str):
        """
        控制指定路口的紅綠燈 (Agent API)
        
        Args:
            position: 路口座標 (x, y)
            action: 動作
                - 'toggle': 切換方向
                - 'ns_green': 設定南北向綠燈
                - 'ew_green': 設定東西向綠燈
                - 'hold': 維持不變
        
        Returns:
            bool: 是否成功
        """
        if self.grid_map is None:
            return False
        
        if position not in self.grid_map.intersections:
            return False
        
        intersection = self.grid_map.intersections[position]
        
        if action == 'toggle':
            intersection.toggle()
        elif action == 'ns_green':
            intersection.set_ns_green()
        elif action == 'ew_green':
            intersection.set_ew_green()
        elif action == 'hold':
            pass  # 維持不變
        else:
            return False
        
        return True
    
    def update_intersections(self):
        """
        手動更新所有路口紅綠燈計時器 (Agent 模式下使用)
        
        在 Agent 模式下，Agent 可以：
        1. 先呼叫 control_intersection() 設定各路口
        2. 再呼叫此方法來 tick 計時器
        """
        if self.grid_map:
            self.grid_map.update_all_intersections()
    
    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        重置環境
        """
        super().reset(seed=seed)
        
        # 使用地圖種子或隨機種子
        map_seed = self.map_seed if self.map_seed else (seed or random.randint(0, 10000))
        
        # 生成地圖 (使用指定的網格大小)
        self.grid_map = GridMap(width=self.grid_size, height=self.grid_size, seed=map_seed)
        
        # 清空車輛
        self.vehicles = []
        self.current_step = 0
        self.arrived_count = 0
        
        # 生成初始車輛
        self._spawn_initial_vehicles()
        
        return self._get_observation(), self._get_info()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        執行一個時間步
        
        Args:
            action: 在 random 模式下忽略，在 agent 模式下由 agent 控制
        """
        self.current_step += 1
        
        # 只在 random 模式下自動更新紅綠燈
        if not self._agent_mode:
            self.grid_map.update_all_intersections()
        
        # 移動車輛
        self._move_vehicles()
        
        # 生成新車輛 (僅在非固定模式下)
        if not self._fixed_vehicle_mode:
            self._spawn_vehicles()
        
        # 計算獎勵
        reward = self._calculate_reward()
        
        # 檢查終止
        terminated = False
        truncated = self.current_step >= self.max_steps
        
        return self._get_observation(), reward, terminated, truncated, self._get_info()
    
    def render(self):
        """渲染環境"""
        if self.render_mode is None:
            return None
        
        if self._renderer is None:
            from draw import GridRenderer
            self._renderer = GridRenderer(self.render_mode)
        
        render_data = {
            "grid_map": self.grid_map,
            "vehicles": self.vehicles,
            "step": self.current_step,
            "arrived_count": self.arrived_count,
        }
        
        return self._renderer.render(render_data)
    
    def close(self):
        """關閉環境"""
        if self._renderer:
            self._renderer.close()
            self._renderer = None
    
    # =========================================================================
    # 車輛管理
    # =========================================================================
    
    def _spawn_initial_vehicles(self):
        """
        生成初始車輛
        
        每輛車有自己獨特的起點和終點
        """
        boundary = self.grid_map.get_boundary_cells()
        random.shuffle(boundary)  # 打亂順序
        
        # 決定要生成的車輛數量
        if self._fixed_vehicle_mode:
            num_vehicles = self._fixed_vehicle_count
        else:
            num_vehicles = random.randint(3, 5)
        
        # 確保有足夠的邊界點 (每輛車需要 1 個起點)
        max_vehicles = len(boundary)
        num_vehicles = min(num_vehicles, max_vehicles)
        
        # 分配唯一的起點 (終點可以重複)
        used_starts = set()
        spawned = 0
        
        for i in range(num_vehicles):
            # 找一個未使用的起點
            start = None
            for b in boundary:
                if b not in used_starts:
                    start = b
                    used_starts.add(b)
                    break
            
            if not start:
                break
            
            # 終點可以是任何其他邊界點 (不必唯一)
            available_ends = [b for b in boundary if b != start]
            if not available_ends:
                break
            
            end = random.choice(available_ends)
            
            # 計算路徑
            path = self.grid_map.dijkstra(start, end)
            
            if path:
                vehicle = Car(Direction.NORTH, grid_position=start, destination=end)
                vehicle.set_path(path)
                self.vehicles.append(vehicle)
                spawned += 1
            else:
                # 路徑不存在，釋放起點
                used_starts.discard(start)
    
    def _spawn_vehicles(self):
        """每步嘗試生成新車輛 (僅在非固定模式下)"""
        if self._fixed_vehicle_mode:
            return  # 固定模式下不生成新車輛
        
        if len(self.vehicles) >= self.MAX_VEHICLES:
            return
        
        if random.random() < self.VEHICLE_SPAWN_PROB:
            boundary = self.grid_map.get_boundary_cells()
            self._spawn_single_vehicle(boundary)
    
    def _spawn_single_vehicle(self, boundary: List[Tuple[int, int]]):
        """生成單一車輛 (用於動態生成)"""
        if len(boundary) < 2:
            return
        
        # 取得已被佔用的位置
        occupied = set()
        for v in self.vehicles:
            if v.grid_position:
                occupied.add(v.grid_position)
            if v.destination:
                occupied.add(v.destination)
        
        # 找未被佔用的起點
        available_starts = [b for b in boundary if b not in occupied]
        if not available_starts:
            return
        
        start = random.choice(available_starts)
        
        # 找未被佔用的終點
        available_ends = [b for b in boundary if b not in occupied and b != start]
        if not available_ends:
            return
        
        end = random.choice(available_ends)
        
        # 計算路徑
        path = self.grid_map.dijkstra(start, end)
        
        if not path:
            return
        
        # 創建車輛
        vehicle = Car(Direction.NORTH, grid_position=start, destination=end)
        vehicle.set_path(path)
        self.vehicles.append(vehicle)
    
    def _move_vehicles(self):
        """
        移動所有車輛
        
        使用 4 方向車道系統：
        - 相反方向 (n vs s, e vs w) 可以在同一格通過
        - 同方向的車輛不能疊在一起
        """
        remaining = []
        
        # 建立佔用位置字典: {position: {direction: vehicle}}
        # direction: "n", "s", "e", "w" (4個方向)
        occupied = {}
        for v in self.vehicles:
            if v.grid_position:
                pos = v.grid_position
                if pos not in occupied:
                    occupied[pos] = {}
                direction = self._get_vehicle_direction(v)
                occupied[pos][direction] = v
        
        for vehicle in self.vehicles:
            pos = vehicle.grid_position
            
            # 取得下一個位置和移動方向
            next_pos = None
            move_direction = "n"  # 預設
            move_axis = "ns"  # 用於紅綠燈檢查
            
            if vehicle.path_index < len(vehicle.path) - 1:
                next_pos = vehicle.path[vehicle.path_index + 1]
                dx = next_pos[0] - pos[0]
                dy = next_pos[1] - pos[1]
                
                # 4個具體方向
                if dy < 0:
                    move_direction = "n"  # 往上 (y 減少)
                    move_axis = "ns"
                elif dy > 0:
                    move_direction = "s"  # 往下 (y 增加)
                    move_axis = "ns"
                elif dx > 0:
                    move_direction = "e"  # 往右
                    move_axis = "ew"
                else:
                    move_direction = "w"  # 往左
                    move_axis = "ew"
            
            # 檢查是否可以移動
            can_move = True
            
            # 1. 檢查下一格同方向是否被佔用
            if next_pos and next_pos in occupied:
                if move_direction in occupied[next_pos]:
                    other = occupied[next_pos][move_direction]
                    if other != vehicle:
                        can_move = False
            
            # 2. 檢查下一格是否為路口，需要等紅綠燈
            # 車輛在進入路口之前等待，而不是在路口上等待
            if can_move and next_pos and next_pos in self.grid_map.intersections:
                intersection = self.grid_map.intersections[next_pos]
                can_move = intersection.can_pass(move_axis)
            
            if can_move:
                # 更新佔用位置
                old_dir = self._get_vehicle_direction(vehicle)
                if pos in occupied and old_dir in occupied[pos]:
                    del occupied[pos][old_dir]
                    if not occupied[pos]:
                        del occupied[pos]
                
                reached = vehicle.move_on_grid()
                
                if reached:
                    self.arrived_count += 1
                    continue
                else:
                    new_pos = vehicle.grid_position
                    new_dir = move_direction
                    if new_pos not in occupied:
                        occupied[new_pos] = {}
                    occupied[new_pos][new_dir] = vehicle
            
            remaining.append(vehicle)
        
        self.vehicles = remaining
    
    def _get_vehicle_direction(self, vehicle) -> str:
        """取得車輛具體移動方向 (n/s/e/w)"""
        if vehicle.path_index < len(vehicle.path) - 1:
            pos = vehicle.grid_position
            next_pos = vehicle.path[vehicle.path_index + 1]
            dx = next_pos[0] - pos[0]
            dy = next_pos[1] - pos[1]
            
            if dy < 0:
                return "n"
            elif dy > 0:
                return "s"
            elif dx > 0:
                return "e"
            else:
                return "w"
        return "n"
    
    # =========================================================================
    # 觀察值與獎勵
    # =========================================================================
    
    def _get_observation(self) -> np.ndarray:
        """生成觀察值"""
        obs = [
            len(self.vehicles),
            self.arrived_count,
        ]
        
        # 網格狀態 (0=empty, 1=road, 2=intersection)
        for y in range(self.GRID_SIZE):
            for x in range(self.GRID_SIZE):
                cell = self.grid_map.grid[y][x]
                obs.append(cell.value)
        
        return np.array(obs, dtype=np.float32)
    
    def _calculate_reward(self) -> float:
        """計算獎勵"""
        reward = 0.0
        
        # 獎勵到達的車輛
        reward += self.arrived_count * 0.1
        
        # 懲罰等待
        for v in self.vehicles:
            reward -= 0.01
        
        return reward
    
    def _get_info(self) -> Dict[str, Any]:
        """取得資訊"""
        return {
            "step": self.current_step,
            "vehicle_count": len(self.vehicles),
            "arrived_count": self.arrived_count,
            "intersection_count": len(self.grid_map.intersections) if self.grid_map else 0,
        }


# =============================================================================
# Module Test
# =============================================================================

if __name__ == "__main__":
    print("=== Testing Grid Traffic Environment ===\n")
    
    env = GridTrafficEnv(render_mode="human", seed=42)
    obs, info = env.reset()
    
    print(f"Observation shape: {obs.shape}")
    print(f"Initial info: {info}")
    print(f"\nRunning for 100 steps...")
    
    for step in range(100):
        obs, reward, term, trunc, info = env.step(0)
        env.render()
        
        if step % 20 == 0:
            print(f"Step {step}: vehicles={info['vehicle_count']}, arrived={info['arrived_count']}")
        
        if term or trunc:
            break
    
    env.close()
    print("\n=== Test Complete ===")
