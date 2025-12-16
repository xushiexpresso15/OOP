from enum import Enum
from typing import List, Tuple, Dict, Optional, Set
import random
import heapq
import math

from objects import TrafficLight, LightState

class PerlinNoise:
    def __init__(self, seed: int = None):
        if seed is not None:
            random.seed(seed)
        self.p = list(range(256))
        random.shuffle(self.p)
        self.p = self.p + self.p
    
    def _fade(self, t: float) -> float:
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + t * (b - a)
    
    def _grad(self, hash_val: int, x: float, y: float) -> float:
        h = hash_val & 3
        if h == 0: return x + y
        elif h == 1: return -x + y
        elif h == 2: return x - y
        else: return -x - y
    
    def noise(self, x: float, y: float) -> float:
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u = self._fade(xf)
        v = self._fade(yf)
        aa = self.p[self.p[xi] + yi]
        ab = self.p[self.p[xi] + yi + 1]
        ba = self.p[self.p[xi + 1] + yi]
        bb = self.p[self.p[xi + 1] + yi + 1]
        x1 = self._lerp(self._grad(aa, xf, yf), self._grad(ba, xf - 1, yf), u)
        x2 = self._lerp(self._grad(ab, xf, yf - 1), self._grad(bb, xf - 1, yf - 1), u)
        return self._lerp(x1, x2, v)

class GridCell(Enum):
    EMPTY = 0 #牆壁
    ROAD = 1 #道路
    INTERSECTION = 2 #路口

class Intersection:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.id = f"intersection_{x}_{y}"
        
        if random.random() < 0.5:
            self.traffic_light_ns = TrafficLight(f"NS_{x}_{y}", LightState.GREEN)
            self.traffic_light_ew = TrafficLight(f"EW_{x}_{y}", LightState.RED)
        else:
            self.traffic_light_ns = TrafficLight(f"NS_{x}_{y}", LightState.RED)
            self.traffic_light_ew = TrafficLight(f"EW_{x}_{y}", LightState.GREEN)
        
        offset = random.randint(0, 20)
        self.traffic_light_ns._timer = max(1, self.traffic_light_ns._timer - offset)
        self.traffic_light_ew._timer = max(1, self.traffic_light_ew._timer - offset)
    
    @property
    def position(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    def update(self): 
        #random mode traffic light
        ns = self.traffic_light_ns
        ew = self.traffic_light_ew
        
        if ns.is_red and ew.is_green:
            ns._timer = ew.timer + ew.YELLOW_TIME
        elif ns.is_red and ew.is_yellow:
            ns._timer = ew.timer
        if ew.is_red and ns.is_green:
            ew._timer = ns.timer + ns.YELLOW_TIME
        elif ew.is_red and ns.is_yellow:
            ew._timer = ns.timer
        
        if ns.state in [LightState.GREEN, LightState.YELLOW]:
            state_changed = ns.tick()
            if state_changed and ns.is_red:
                ew.set_state(LightState.GREEN)
        elif ew.state in [LightState.GREEN, LightState.YELLOW]:
            state_changed = ew.tick()
            if state_changed and ew.is_red:
                ns.set_state(LightState.GREEN)
        else:
            ns.set_state(LightState.GREEN)
    
    def toggle(self):
        #for agent mode
        ns = self.traffic_light_ns
        ew = self.traffic_light_ew
        
        if ns.state in [LightState.GREEN, LightState.YELLOW]:
            ns.set_state(LightState.RED)
            ew.set_state(LightState.GREEN)
        else:
            ew.set_state(LightState.RED)
            ns.set_state(LightState.GREEN)
    
    def set_ns_green(self):
        self.traffic_light_ns.set_state(LightState.GREEN)
        self.traffic_light_ew.set_state(LightState.RED)
    
    def set_ew_green(self):
        self.traffic_light_ns.set_state(LightState.RED)
        self.traffic_light_ew.set_state(LightState.GREEN)
    
    def set_ns_yellow(self):
        self.traffic_light_ns.set_state(LightState.YELLOW)
        self.traffic_light_ew.set_state(LightState.RED)
    
    def set_ew_yellow(self):
        self.traffic_light_ns.set_state(LightState.RED)
        self.traffic_light_ew.set_state(LightState.YELLOW)
    
    def get_state(self) -> dict:
        return {
            'position': self.position,
            'ns_state': self.traffic_light_ns.state.value,
            'ew_state': self.traffic_light_ew.state.value,
            'ns_timer': self.traffic_light_ns.timer,
            'ew_timer': self.traffic_light_ew.timer,
            'ns_can_pass': self.traffic_light_ns.can_pass,
            'ew_can_pass': self.traffic_light_ew.can_pass,
        }
    
    def can_pass(self, direction: str) -> bool:
        if direction == "ns":
            return self.traffic_light_ns.can_pass
        else:
            return self.traffic_light_ew.can_pass

class GridMap:
    DEFAULT_SIZE = 5
    
    def __init__(self, width: int = DEFAULT_SIZE, height: int = DEFAULT_SIZE, seed: int = None):
        self.width = width
        self.height = height
        self.seed = seed
        
        self.actual_width = width * 2 + 1
        self.actual_height = height * 2 + 1
        
        self.grid: List[List[GridCell]] = [
            [GridCell.EMPTY for _ in range(self.actual_width)] 
            for _ in range(self.actual_height)
        ]
        
        self.intersections: Dict[Tuple[int, int], Intersection] = {}
        self._generate_maze(seed)
    
    def _generate_maze(self, seed: int = None):
        if seed is not None:
            random.seed(seed)
        
        noise = PerlinNoise(seed=seed) #noise物件
        visited = set()
        stack = [(0, 0)]
        visited.add((0, 0))
        self.grid[1][1] = GridCell.ROAD
        
        while stack:
            cx, cy = stack[-1]
            neighbors = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if (nx, ny) not in visited:
                        #使用 noise 決定優先順序
                        noise_val = noise.noise(nx * 0.5, ny * 0.5)
                        neighbors.append((noise_val, nx, ny, dx, dy))
            
            if neighbors:
                #根據 noise 排序選下一步要往哪裡走
                neighbors.sort(reverse=True)
                _, nx, ny, dx, dy = neighbors[0]
                
                wall_x = 1 + cx * 2 + dx #break the walls!!!
                wall_y = 1 + cy * 2 + dy
                self.grid[wall_y][wall_x] = GridCell.ROAD
                
                cell_x = 1 + nx * 2
                cell_y = 1 + ny * 2
                self.grid[cell_y][cell_x] = GridCell.ROAD
                
                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                stack.pop()
        
        self._add_extra_paths(noise)
        self._add_boundary_exits()
        self._identify_intersections()
    
    def _add_extra_paths(self, noise: PerlinNoise):
        for y in range(1, self.actual_height - 1, 2):
            for x in range(1, self.actual_width - 1, 2):
                if self.grid[y][x] == GridCell.ROAD:
                    # 隨機break the walls
                    for dx, dy in [(1, 0), (0, 1)]:
                        wx, wy = x + dx, y + dy
                        if wx < self.actual_width - 1 and wy < self.actual_height - 1:
                            if self.grid[wy][wx] == GridCell.EMPTY:
                                noise_val = noise.noise(wx * 0.3, wy * 0.3)
                                if noise_val > 0.2:
                                    self.grid[wy][wx] = GridCell.ROAD
    
    def _add_boundary_exits(self):
        for x in range(1, self.actual_width - 1, 2):
            if self.grid[1][x] == GridCell.ROAD:
                self.grid[0][x] = GridCell.ROAD
        
        for x in range(1, self.actual_width - 1, 2):
            if self.grid[self.actual_height - 2][x] == GridCell.ROAD:
                self.grid[self.actual_height - 1][x] = GridCell.ROAD
        
        for y in range(1, self.actual_height - 1, 2):
            if self.grid[y][1] == GridCell.ROAD:
                self.grid[y][0] = GridCell.ROAD
        
        for y in range(1, self.actual_height - 1, 2):
            if self.grid[y][self.actual_width - 2] == GridCell.ROAD:
                self.grid[y][self.actual_width - 1] = GridCell.ROAD
    
    def _identify_intersections(self):
        self.intersections.clear()
        
        for y in range(self.actual_height):
            for x in range(self.actual_width):
                if self.grid[y][x] == GridCell.EMPTY:
                    continue
                
                connections = 0
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.actual_width and 0 <= ny < self.actual_height:
                        if self.grid[ny][nx] != GridCell.EMPTY:
                            connections += 1
                
                if connections >= 3:
                    self.grid[y][x] = GridCell.INTERSECTION
                    self.intersections[(x, y)] = Intersection(x, y)
    
    def get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.actual_width and 0 <= ny < self.actual_height:
                if self.grid[ny][nx] != GridCell.EMPTY:
                    neighbors.append((nx, ny))
        return neighbors
    
    def get_boundary_cells(self) -> List[Tuple[int, int]]:
        boundary = []
        
        for x in range(self.actual_width):
            if self.grid[0][x] != GridCell.EMPTY:
                boundary.append((x, 0))
            if self.grid[self.actual_height - 1][x] != GridCell.EMPTY:
                boundary.append((x, self.actual_height - 1))
        
        for y in range(1, self.actual_height - 1):
            if self.grid[y][0] != GridCell.EMPTY:
                boundary.append((0, y))
            if self.grid[y][self.actual_width - 1] != GridCell.EMPTY:
                boundary.append((self.actual_width - 1, y))
        
        return boundary
    
    def update_all_intersections(self):
        for intersection in self.intersections.values():
            intersection.update()
    
    def dijkstra(self, start: Tuple[int, int], end: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        #用dijkstra演算法事先計算每台車子的最佳路徑
        if self.grid[start[1]][start[0]] == GridCell.EMPTY:
            return None
        if self.grid[end[1]][end[0]] == GridCell.EMPTY:
            return None
        
        heap = [(0, start[0], start[1], [start])]
        visited = set()
        
        while heap:
            cost, x, y, path = heapq.heappop(heap)
            
            if (x, y) == end:
                return path
            
            if (x, y) in visited:
                continue
            visited.add((x, y))
            
            for nx, ny in self.get_neighbors(x, y):
                if (nx, ny) not in visited:
                    heapq.heappush(heap, (cost + 1, nx, ny, path + [(nx, ny)]))
        
        return None
    
    def __repr__(self) -> str:
        symbols = {GridCell.EMPTY: '█', GridCell.ROAD: ' ', GridCell.INTERSECTION: '+'}
        lines = []
        for y in range(self.actual_height):
            line = ''.join(symbols[self.grid[y][x]] for x in range(self.actual_width))
            lines.append(line)
        return '\n'.join(lines)

# for test
if __name__ == "__main__":
    print("=== Testing Maze Grid Map ===\n")
    
    grid = GridMap(seed=42)
    print(f"Grid size: {grid.actual_width}x{grid.actual_height}")
    print(f"\nMaze:")
    print(grid)
    print(f"\nIntersections: {len(grid.intersections)}")
    print(f"Boundary exits: {len(grid.get_boundary_cells())}")
    
    boundary = grid.get_boundary_cells()
    if len(boundary) >= 2:
        path = grid.dijkstra(boundary[0], boundary[-1])
        print(f"\nPath from {boundary[0]} to {boundary[-1]}: {len(path) if path else 0} steps")
    
    print("\n=== Test Complete ===")
