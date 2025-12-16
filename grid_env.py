import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import random

from objects import Vehicle, Car, Ambulance, Direction
from grid_map import GridMap, GridCell, Intersection


class GridTrafficEnv(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 10}
    GRID_SIZE = 5
    MAX_VEHICLES = 10
    VEHICLE_SPAWN_PROB = 0.15
    AMBULANCE_SPAWN_PROB = 0.02
    MAX_STEPS = 300
    
    def __init__(self, render_mode: Optional[str] = None, seed: int = None, grid_size: int = 5, max_steps: int = 300):
        super().__init__()
        
        self.render_mode = render_mode
        self.map_seed = seed
        self.grid_size = grid_size
        self.max_steps = max_steps
        
        if grid_size <= 5:
            self.MAX_VEHICLES = 10
        elif grid_size <= 11:
            self.MAX_VEHICLES = 25
        else:
            self.MAX_VEHICLES = 50
        
        self.action_space = spaces.Discrete(1)
        
        obs_size = 2 + grid_size * grid_size
        self.observation_space = spaces.Box(
            low=0, high=100, shape=(obs_size,), dtype=np.float32
        )
        
        self.grid_map: Optional[GridMap] = None
        self.vehicles: List[Vehicle] = []
        self.current_step = 0
        self.arrived_count = 0
        
        self._fixed_vehicle_mode = False
        self._fixed_vehicle_count = 0
        self._agent_mode = False
        self._renderer = None
    
    def set_fixed_vehicle_mode(self, vehicle_count: int):
        self._fixed_vehicle_mode = True
        self._fixed_vehicle_count = vehicle_count
    
    def set_agent_mode(self, enabled: bool = True):
        self._agent_mode = enabled
    
    
    def get_intersections(self) -> list:
        if self.grid_map is None:
            return []
        return list(self.grid_map.intersections.values())
    
    def get_intersection_states(self) -> list:
        return [inter.get_state() for inter in self.get_intersections()]
    
    def get_vehicle_states(self) -> list:
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
        #用agent API控制紅綠燈
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
        elif action == 'ns_yellow':
            intersection.set_ns_yellow()
        elif action == 'ew_yellow':
            intersection.set_ew_yellow()
        elif action == 'hold':
            pass
        else:
            return False
        
        return True
    
    def update_intersections(self):
        if self.grid_map:
            self.grid_map.update_all_intersections()
    
    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        map_seed = self.map_seed if self.map_seed else (seed or random.randint(0, 10000))
        self.grid_map = GridMap(width=self.grid_size, height=self.grid_size, seed=map_seed)
        
        self.vehicles = []
        self.current_step = 0
        self.arrived_count = 0
        self.total_spawned_vehicles = 0
        
        self._spawn_initial_vehicles()
        
        return self._get_observation(), self._get_info()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self.current_step += 1
        if not self._agent_mode:
            self.grid_map.update_all_intersections()
        self._move_vehicles()
        if not self._fixed_vehicle_mode:
            self._spawn_vehicles()
        reward = self._calculate_reward()
        
        terminated = False
        truncated = self.current_step >= self.max_steps
        
        return self._get_observation(), reward, terminated, truncated, self._get_info()
    
    def render(self):
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
        if self._renderer:
            self._renderer.close()
            self._renderer = None
            
    def _spawn_initial_vehicles(self):
        boundary = self.grid_map.get_boundary_cells()
        random.shuffle(boundary)
        
        if self._fixed_vehicle_mode:
            num_vehicles = self._fixed_vehicle_count
        else:
            num_vehicles = random.randint(3, 5)
        
        max_vehicles = len(boundary)
        num_vehicles = min(num_vehicles, max_vehicles)
        min_dist = (self.grid_map.actual_width + self.grid_map.actual_height) // 6
        used_starts = set()
        spawned = 0
        
        for i in range(num_vehicles):
            start = None
            for b in boundary:
                if b not in used_starts:
                    start = b
                    used_starts.add(b)
                    break
            
            if not start:
                break
            
            candidates = [b for b in boundary if b != start]
            far_candidates = [ #終點不能離起點太近
                b for b in candidates 
                if (abs(b[0] - start[0]) + abs(b[1] - start[1])) >= min_dist
            ]
            available_ends = far_candidates if far_candidates else candidates
            
            if not available_ends:
                break
            
            end = random.choice(available_ends)
            path = self.grid_map.dijkstra(start, end)
            
            if path:
                vehicle = Car(Direction.NORTH, grid_position=start, destination=end)
                vehicle.set_path(path)
                self.vehicles.append(vehicle)
                spawned += 1
            else:
                used_starts.discard(start)
        
        self.total_spawned_vehicles = spawned
        print(f"Vehicles spawned: {spawned} (requested: {num_vehicles})")
    
    def _spawn_vehicles(self):
        if self._fixed_vehicle_mode:
            return
        
        if len(self.vehicles) >= self.MAX_VEHICLES:
            return
        
        if random.random() < self.VEHICLE_SPAWN_PROB:
            boundary = self.grid_map.get_boundary_cells()
            self._spawn_single_vehicle(boundary)
            if self._spawn_single_vehicle(boundary):
                 self.total_spawned_vehicles += 1
    
    def _spawn_single_vehicle(self, boundary: List[Tuple[int, int]]):
        if len(boundary) < 2:
            return
        
        occupied = set()
        for v in self.vehicles:
            if v.grid_position:
                occupied.add(v.grid_position)
            if v.destination:
                occupied.add(v.destination)
        
        available_starts = [b for b in boundary if b not in occupied]
        if not available_starts:
            return
        
        start = random.choice(available_starts)
        min_dist = (self.grid_map.actual_width + self.grid_map.actual_height) // 6
        candidates = [b for b in boundary if b not in occupied and b != start]

        far_candidates = [
            b for b in candidates 
            if (abs(b[0] - start[0]) + abs(b[1] - start[1])) >= min_dist
        ]
        
        available_ends = far_candidates if far_candidates else candidates
        
        if not available_ends:
            return
        
        end = random.choice(available_ends)
        path = self.grid_map.dijkstra(start, end)
        
        if not path:
            return
        
        vehicle = Car(Direction.NORTH, grid_position=start, destination=end)
        vehicle.set_path(path)
        self.vehicles.append(vehicle)
    
    def _move_vehicles(self):
        remaining = []
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
            next_pos = None
            move_direction = "n"
            move_axis = "ns"
            
            if vehicle.path_index < len(vehicle.path) - 1:
                next_pos = vehicle.path[vehicle.path_index + 1]
                dx = next_pos[0] - pos[0]
                dy = next_pos[1] - pos[1]
                new_direction = None
                if dy < 0:
                    move_direction = "n"
                    move_axis = "ns"
                    new_direction = Direction.NORTH
                elif dy > 0:
                    move_direction = "s"
                    move_axis = "ns"
                    new_direction = Direction.SOUTH
                elif dx > 0:
                    move_direction = "e"
                    move_axis = "ew"
                    new_direction = Direction.EAST
                else:
                    move_direction = "w"
                    move_axis = "ew"
                    new_direction = Direction.WEST
                    
                if new_direction:
                    vehicle.direction = new_direction
            
            can_move = True
            if next_pos and next_pos in occupied:
                if move_direction in occupied[next_pos]:
                    other = occupied[next_pos][move_direction]
                    if other != vehicle:
                        can_move = False
            
            if can_move and next_pos and next_pos in self.grid_map.intersections:
                intersection = self.grid_map.intersections[next_pos]
                can_move = intersection.can_pass(move_axis)
            
            if can_move:
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
    
    def _get_observation(self) -> np.ndarray:
        obs = [
            len(self.vehicles),
            self.arrived_count,
        ]
        for y in range(self.GRID_SIZE):
            for x in range(self.GRID_SIZE):
                cell = self.grid_map.grid[y][x]
                obs.append(cell.value)
        
        return np.array(obs, dtype=np.float32)
    
    def _calculate_reward(self) -> float:
        reward = 0.0
        reward += self.arrived_count * 0.1
        for v in self.vehicles:
            reward -= 0.01
        
        return reward
    
    def _get_info(self) -> Dict[str, Any]:
        return {
            "step": self.current_step,
            "vehicle_count": len(self.vehicles),
            "arrived_count": self.arrived_count,
            "intersection_count": len(self.grid_map.intersections) if self.grid_map else 0,
            "total_spawned": self.total_spawned_vehicles,
            "total_throughput": self.arrived_count,
            "ambulance_throughput": 0
        }

#test module
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
