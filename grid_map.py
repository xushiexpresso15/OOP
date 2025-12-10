"""
grid_map.py - 迷宮式網格地圖生成模組
Smart Traffic Intersection Environment

使用 Perlin noise 生成 5x5 迷宮式道路系統：
- 迷宮的路線就是馬路
- 保證所有道路連通
- 路口有獨立紅綠燈
"""

from enum import Enum
from typing import List, Tuple, Dict, Optional, Set
import random
import heapq
import math

from objects import TrafficLight, LightState


# =============================================================================
# Perlin Noise Implementation
# =============================================================================

class PerlinNoise:
    """簡化版 Perlin noise 實作"""
    
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


# =============================================================================
# Grid Cell Types
# =============================================================================

class GridCell(Enum):
    """網格格子類型"""
    EMPTY = 0           # 空地 (牆壁)
    ROAD = 1            # 道路 (迷宮路徑)
    INTERSECTION = 2    # 路口


# =============================================================================
# Intersection Class
# =============================================================================

class Intersection:
    """
    路口類別 - 每個路口有獨立紅綠燈
    
    提供 Agent 控制紅綠燈的 API：
    - toggle(): 切換紅綠燈方向
    - set_ns_green(): 強制設定南北向為綠燈
    - set_ew_green(): 強制設定東西向為綠燈
    - get_state(): 取得當前狀態
    """
    
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.id = f"intersection_{x}_{y}"
        
        # 隨機決定初始狀態和時間，讓每個路口獨立
        if random.random() < 0.5:
            self.traffic_light_ns = TrafficLight(f"NS_{x}_{y}", LightState.GREEN)
            self.traffic_light_ew = TrafficLight(f"EW_{x}_{y}", LightState.RED)
        else:
            self.traffic_light_ns = TrafficLight(f"NS_{x}_{y}", LightState.RED)
            self.traffic_light_ew = TrafficLight(f"EW_{x}_{y}", LightState.GREEN)
        
        # 隨機化初始計時器，讓各路口不同步
        offset = random.randint(0, 20)
        self.traffic_light_ns._timer = max(1, self.traffic_light_ns._timer - offset)
        self.traffic_light_ew._timer = max(1, self.traffic_light_ew._timer - offset)
    
    @property
    def position(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    # =========================================================================
    # 自動更新 (random 模式使用)
    # =========================================================================
    
    def update(self):
        """自動更新紅綠燈 (用於 random 模式)"""
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
    
    # =========================================================================
    # Agent 控制 API
    # =========================================================================
    
    def toggle(self):
        """
        切換紅綠燈方向 (Agent 動作)
        
        如果當前 NS 是綠燈/黃燈，則切換到 EW 綠燈
        如果當前 EW 是綠燈/黃燈，則切換到 NS 綠燈
        """
        ns = self.traffic_light_ns
        ew = self.traffic_light_ew
        
        if ns.state in [LightState.GREEN, LightState.YELLOW]:
            ns.set_state(LightState.RED)
            ew.set_state(LightState.GREEN)
        else:
            ew.set_state(LightState.RED)
            ns.set_state(LightState.GREEN)
    
    def set_ns_green(self):
        """強制設定南北向為綠燈 (Agent 動作)"""
        self.traffic_light_ns.set_state(LightState.GREEN)
        self.traffic_light_ew.set_state(LightState.RED)
    
    def set_ew_green(self):
        """強制設定東西向為綠燈 (Agent 動作)"""
        self.traffic_light_ns.set_state(LightState.RED)
        self.traffic_light_ew.set_state(LightState.GREEN)
    
    def get_state(self) -> dict:
        """
        取得當前路口狀態 (用於 Agent 觀察)
        
        Returns:
            dict: {
                'position': (x, y),
                'ns_state': 'green'/'yellow'/'red',
                'ew_state': 'green'/'yellow'/'red',
                'ns_timer': int,
                'ew_timer': int,
            }
        """
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


# =============================================================================
# Grid Map Class - 迷宮式生成
# =============================================================================

class GridMap:
    """
    5x5 迷宮式網格地圖
    
    使用隨機深度優先搜尋 (DFS) 生成迷宮
    迷宮的路徑即為道路
    """
    
    DEFAULT_SIZE = 5
    
    def __init__(self, width: int = DEFAULT_SIZE, height: int = DEFAULT_SIZE, seed: int = None):
        self.width = width
        self.height = height
        self.seed = seed
        
        # 實際網格大小是 2*size+1 (牆壁 + 通道)
        self.actual_width = width * 2 + 1
        self.actual_height = height * 2 + 1
        
        # 網格陣列
        self.grid: List[List[GridCell]] = [
            [GridCell.EMPTY for _ in range(self.actual_width)] 
            for _ in range(self.actual_height)
        ]
        
        self.intersections: Dict[Tuple[int, int], Intersection] = {}
        
        # 生成迷宮
        self._generate_maze(seed)
    
    def _generate_maze(self, seed: int = None):
        """
        使用 DFS + Perlin noise 生成迷宮
        """
        if seed is not None:
            random.seed(seed)
        
        noise = PerlinNoise(seed=seed)
        
        # 迷宮的邏輯格子座標 (不含牆壁)
        visited = set()
        stack = [(0, 0)]
        visited.add((0, 0))
        
        # 設定起點為道路
        self.grid[1][1] = GridCell.ROAD
        
        while stack:
            cx, cy = stack[-1]
            
            # 取得未訪問的鄰居
            neighbors = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if (nx, ny) not in visited:
                        # 使用 noise 決定優先順序
                        noise_val = noise.noise(nx * 0.5, ny * 0.5)
                        neighbors.append((noise_val, nx, ny, dx, dy))
            
            if neighbors:
                # 根據 noise 排序，選擇優先方向
                neighbors.sort(reverse=True)
                _, nx, ny, dx, dy = neighbors[0]
                
                # 打通牆壁
                wall_x = 1 + cx * 2 + dx
                wall_y = 1 + cy * 2 + dy
                self.grid[wall_y][wall_x] = GridCell.ROAD
                
                # 設定新格子為道路
                cell_x = 1 + nx * 2
                cell_y = 1 + ny * 2
                self.grid[cell_y][cell_x] = GridCell.ROAD
                
                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                stack.pop()
        
        # 添加額外的路徑讓迷宮更開放
        self._add_extra_paths(noise)
        
        # 確保邊界有出入口
        self._add_boundary_exits()
        
        # 識別路口
        self._identify_intersections()
    
    def _add_extra_paths(self, noise: PerlinNoise):
        """添加額外路徑讓迷宮不那麼單調"""
        for y in range(1, self.actual_height - 1, 2):
            for x in range(1, self.actual_width - 1, 2):
                if self.grid[y][x] == GridCell.ROAD:
                    # 隨機打通一些牆壁
                    for dx, dy in [(1, 0), (0, 1)]:
                        wx, wy = x + dx, y + dy
                        if wx < self.actual_width - 1 and wy < self.actual_height - 1:
                            if self.grid[wy][wx] == GridCell.EMPTY:
                                noise_val = noise.noise(wx * 0.3, wy * 0.3)
                                if noise_val > 0.2:
                                    self.grid[wy][wx] = GridCell.ROAD
    
    def _add_boundary_exits(self):
        """確保邊界有多個出入口"""
        # 上邊界 - 所有連接到道路的點
        for x in range(1, self.actual_width - 1, 2):
            if self.grid[1][x] == GridCell.ROAD:
                self.grid[0][x] = GridCell.ROAD
        
        # 下邊界
        for x in range(1, self.actual_width - 1, 2):
            if self.grid[self.actual_height - 2][x] == GridCell.ROAD:
                self.grid[self.actual_height - 1][x] = GridCell.ROAD
        
        # 左邊界
        for y in range(1, self.actual_height - 1, 2):
            if self.grid[y][1] == GridCell.ROAD:
                self.grid[y][0] = GridCell.ROAD
        
        # 右邊界
        for y in range(1, self.actual_height - 1, 2):
            if self.grid[y][self.actual_width - 2] == GridCell.ROAD:
                self.grid[y][self.actual_width - 1] = GridCell.ROAD
    
    def _identify_intersections(self):
        """識別路口 (3個以上方向連接的道路格子)"""
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
        """取得可通行的鄰居"""
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.actual_width and 0 <= ny < self.actual_height:
                if self.grid[ny][nx] != GridCell.EMPTY:
                    neighbors.append((nx, ny))
        return neighbors
    
    def get_boundary_cells(self) -> List[Tuple[int, int]]:
        """取得邊界上的道路 (出入口)"""
        boundary = []
        
        # 上下邊界
        for x in range(self.actual_width):
            if self.grid[0][x] != GridCell.EMPTY:
                boundary.append((x, 0))
            if self.grid[self.actual_height - 1][x] != GridCell.EMPTY:
                boundary.append((x, self.actual_height - 1))
        
        # 左右邊界
        for y in range(1, self.actual_height - 1):
            if self.grid[y][0] != GridCell.EMPTY:
                boundary.append((0, y))
            if self.grid[y][self.actual_width - 1] != GridCell.EMPTY:
                boundary.append((self.actual_width - 1, y))
        
        return boundary
    
    def update_all_intersections(self):
        """更新所有路口紅綠燈"""
        for intersection in self.intersections.values():
            intersection.update()
    
    def dijkstra(self, start: Tuple[int, int], end: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """Dijkstra 最短路徑"""
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


# =============================================================================
# Module Test
# =============================================================================

if __name__ == "__main__":
    print("=== Testing Maze Grid Map ===\n")
    
    grid = GridMap(seed=42)
    print(f"Grid size: {grid.actual_width}x{grid.actual_height}")
    print(f"\nMaze:")
    print(grid)
    print(f"\nIntersections: {len(grid.intersections)}")
    print(f"Boundary exits: {len(grid.get_boundary_cells())}")
    
    # 測試路徑
    boundary = grid.get_boundary_cells()
    if len(boundary) >= 2:
        path = grid.dijkstra(boundary[0], boundary[-1])
        print(f"\nPath from {boundary[0]} to {boundary[-1]}: {len(path) if path else 0} steps")
    
    print("\n=== Test Complete ===")
