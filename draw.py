"""
draw.py - 視覺化模組 (迷宮網格版)
Smart Traffic Intersection Environment

改進的視覺化：
- 真實的馬路外觀
- 三燈號誌紅綠燈
- 車輛圖形
"""

import pygame
import numpy as np
import math
import time
from typing import Dict, List, Any, Optional, Tuple

from objects import Vehicle, Car, Ambulance, TrafficLight, LightState, Direction, TurnType


class GridRenderer:
    """網格地圖渲染器"""
    
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 800
    
    ANIMATION_DURATION = 0.05
    ANIMATION_FRAMES = 3
    
    # 顏色定義
    COLORS = {
        # 背景和環境
        "background": (34, 139, 34),       # 草地綠色
        "wall": (34, 139, 34),             # 牆壁 = 草地
        "road": (50, 50, 50),              # 柏油路深灰色
        "road_line": (255, 255, 255),      # 白色道路線
        "road_edge": (80, 80, 80),         # 道路邊緣
        "intersection": (60, 60, 60),      # 路口
        
        # 車輛
        "car_body": (30, 100, 200),        # 藍色車身
        "car_window": (150, 200, 255),     # 淺藍色車窗
        "ambulance_body": (255, 50, 50),   # 紅色救護車
        "ambulance_cross": (255, 255, 255), # 白色十字
        
        # 紅綠燈
        "light_box": (40, 40, 40),         # 燈箱
        "light_red": (255, 0, 0),
        "light_yellow": (255, 200, 0),
        "light_green": (0, 255, 0),
        "light_off": (60, 60, 60),
        
        # UI
        "text": (255, 255, 255),
        "text_bg": (0, 0, 0, 180),
        "path": (255, 255, 100),
        "destination": (255, 165, 0),
    }
    
    VEHICLE_SIZE = 24
    LIGHT_RADIUS = 6
    
    def __init__(self, render_mode: str = "human"):
        self.render_mode = render_mode
        self._screen = None
        self._clock = None
        self._font = None
        self._initialized = False
    
    def _init_pygame(self):
        if self._initialized:
            return
        
        pygame.init()
        pygame.display.set_caption("Smart Traffic Grid - Maze")
        
        if self.render_mode == "human":
            self._screen = pygame.display.set_mode(
                (self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
            )
        else:
            self._screen = pygame.Surface(
                (self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
            )
        
        self._clock = pygame.time.Clock()
        self._font = pygame.font.Font(None, 20)
        self._font_small = pygame.font.Font(None, 14)
        self._initialized = True
    
    def render(self, render_data: Dict[str, Any]) -> Optional[np.ndarray]:
        self._init_pygame()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
                return None
        
        return self._render_frame(render_data)
    
    def _render_frame(self, render_data: Dict[str, Any]) -> Optional[np.ndarray]:
        # 背景 (草地)
        self._screen.fill(self.COLORS["background"])
        
        grid_map = render_data.get("grid_map")
        
        if grid_map:
            cell_size = self._get_cell_size(grid_map)
            
            # 繪製道路
            self._draw_roads(grid_map, cell_size)
            
            # 繪製紅綠燈
            self._draw_traffic_lights(grid_map, cell_size)
            
            # 繪製車輛
            vehicles = render_data.get("vehicles", [])
            self._draw_vehicles(vehicles, cell_size)
        
        # 資訊面板
        self._draw_info(render_data)
        
        if self.render_mode == "human":
            pygame.display.flip()
            time.sleep(self.ANIMATION_DURATION)
            return None
        else:
            return np.transpose(
                np.array(pygame.surfarray.pixels3d(self._screen)),
                axes=(1, 0, 2)
            )
    
    def close(self):
        if self._initialized:
            pygame.quit()
            self._initialized = False
    
    def _get_cell_size(self, grid_map) -> int:
        return min(self.WINDOW_WIDTH // grid_map.actual_width,
                   self.WINDOW_HEIGHT // grid_map.actual_height)
    
    def _cell_to_pixel(self, x: int, y: int, cell_size: int) -> Tuple[int, int]:
        px = x * cell_size + cell_size // 2
        py = y * cell_size + cell_size // 2
        return px, py
    
    # =========================================================================
    # 繪製道路
    # =========================================================================
    
    def _draw_roads(self, grid_map, cell_size: int):
        """繪製真實感馬路"""
        from grid_map import GridCell
        
        for y in range(grid_map.actual_height):
            for x in range(grid_map.actual_width):
                cell = grid_map.grid[y][x]
                
                if cell == GridCell.EMPTY:
                    continue  # 草地背景已經畫了
                
                # 道路區域
                rect = pygame.Rect(
                    x * cell_size, y * cell_size,
                    cell_size, cell_size
                )
                
                # 繪製柏油路
                pygame.draw.rect(self._screen, self.COLORS["road"], rect)
                
                # 繪製道路邊緣
                pygame.draw.rect(self._screen, self.COLORS["road_edge"], rect, 2)
                
                # 路口特殊處理
                if cell == GridCell.INTERSECTION:
                    # 路口中心標記
                    cx, cy = self._cell_to_pixel(x, y, cell_size)
                    pygame.draw.circle(self._screen, self.COLORS["road_line"], 
                                      (cx, cy), 3)
                else:
                    # 一般道路：繪製中線虛線
                    self._draw_road_markings(x, y, cell_size, grid_map)
    
    def _draw_road_markings(self, x: int, y: int, cell_size: int, grid_map):
        """繪製道路標線"""
        from grid_map import GridCell
        
        cx, cy = self._cell_to_pixel(x, y, cell_size)
        
        # 檢查連接方向
        has_north = y > 0 and grid_map.grid[y-1][x] != GridCell.EMPTY
        has_south = y < grid_map.actual_height-1 and grid_map.grid[y+1][x] != GridCell.EMPTY
        has_west = x > 0 and grid_map.grid[y][x-1] != GridCell.EMPTY
        has_east = x < grid_map.actual_width-1 and grid_map.grid[y][x+1] != GridCell.EMPTY
        
        line_len = cell_size // 4
        
        # 垂直方向道路
        if has_north or has_south:
            pygame.draw.line(self._screen, self.COLORS["road_line"],
                           (cx, cy - line_len), (cx, cy + line_len), 1)
        
        # 水平方向道路
        if has_west or has_east:
            pygame.draw.line(self._screen, self.COLORS["road_line"],
                           (cx - line_len, cy), (cx + line_len, cy), 1)
    
    # =========================================================================
    # 繪製紅綠燈 (三燈)
    # =========================================================================
    
    def _draw_traffic_lights(self, grid_map, cell_size: int):
        """繪製三燈紅綠燈"""
        for (x, y), intersection in grid_map.intersections.items():
            px, py = self._cell_to_pixel(x, y, cell_size)
            
            # 南北向燈 (左側)
            self._draw_single_traffic_light(
                px - cell_size // 3, py - cell_size // 4,
                intersection.traffic_light_ns.state,
                vertical=True
            )
            
            # 東西向燈 (上方)
            self._draw_single_traffic_light(
                px + cell_size // 4, py - cell_size // 3,
                intersection.traffic_light_ew.state,
                vertical=False
            )
    
    def _draw_single_traffic_light(self, x: int, y: int, state: LightState, vertical: bool):
        """
        繪製單個三燈號誌
        
        垂直排列：紅-黃-綠
        """
        r = self.LIGHT_RADIUS
        spacing = r * 2 + 4
        
        if vertical:
            # 垂直排列的燈箱
            box_w, box_h = r * 2 + 6, spacing * 3 + 4
            box_x, box_y = x - box_w // 2, y - box_h // 2
            pygame.draw.rect(self._screen, self.COLORS["light_box"],
                           (box_x, box_y, box_w, box_h))
            pygame.draw.rect(self._screen, (80, 80, 80),
                           (box_x, box_y, box_w, box_h), 1)
            
            # 三個燈
            lights_pos = [
                (x, y - spacing),   # 紅燈
                (x, y),             # 黃燈
                (x, y + spacing),   # 綠燈
            ]
        else:
            # 水平排列的燈箱
            box_w, box_h = spacing * 3 + 4, r * 2 + 6
            box_x, box_y = x - box_w // 2, y - box_h // 2
            pygame.draw.rect(self._screen, self.COLORS["light_box"],
                           (box_x, box_y, box_w, box_h))
            pygame.draw.rect(self._screen, (80, 80, 80),
                           (box_x, box_y, box_w, box_h), 1)
            
            # 三個燈
            lights_pos = [
                (x - spacing, y),   # 紅燈
                (x, y),             # 黃燈
                (x + spacing, y),   # 綠燈
            ]
        
        # 繪製燈號
        light_colors = [
            (self.COLORS["light_red"] if state == LightState.RED else self.COLORS["light_off"]),
            (self.COLORS["light_yellow"] if state == LightState.YELLOW else self.COLORS["light_off"]),
            (self.COLORS["light_green"] if state == LightState.GREEN else self.COLORS["light_off"]),
        ]
        
        for pos, color in zip(lights_pos, light_colors):
            pygame.draw.circle(self._screen, color, pos, r)
            # 發光效果
            if color != self.COLORS["light_off"]:
                glow = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*color[:3], 80), (r*2, r*2), r*2)
                self._screen.blit(glow, (pos[0] - r*2, pos[1] - r*2))
    
    # =========================================================================
    # 繪製車輛
    # =========================================================================
    
    def _draw_vehicles(self, vehicles: List[Vehicle], cell_size: int):
        """繪製所有車輛 (含車道偏移)"""
        for vehicle in vehicles:
            if vehicle.grid_position is None:
                continue
            
            x, y = vehicle.grid_position
            px, py = self._cell_to_pixel(x, y, cell_size)
            
            # 計算車道偏移 (4個方向各佔不同車道)
            lane_offset = cell_size // 4
            move_dir = self._get_vehicle_direction(vehicle)
            
            # 根據行進方向偏移到對應車道
            if move_dir == "n":
                px -= lane_offset  # 北向：偏左
            elif move_dir == "s":
                px += lane_offset  # 南向：偏右
            elif move_dir == "e":
                py -= lane_offset  # 東向：偏上
            elif move_dir == "w":
                py += lane_offset  # 西向：偏下
            
            # 繪製路徑
            if vehicle.path and len(vehicle.path) > vehicle.path_index:
                self._draw_path(vehicle.path, vehicle.path_index, cell_size)
            
            # 繪製車輛
            if isinstance(vehicle, Ambulance):
                self._draw_ambulance(px, py)
            else:
                self._draw_car(px, py)
            
            # 目的地標記
            if vehicle.destination:
                dx, dy = vehicle.destination
                dpx, dpy = self._cell_to_pixel(dx, dy, cell_size)
                pygame.draw.rect(self._screen, self.COLORS["destination"],
                               (dpx - 6, dpy - 6, 12, 12), 2)
    
    def _get_vehicle_direction(self, vehicle) -> str:
        """取得車輛移動方向 (n/s/e/w)"""
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
    
    def _draw_car(self, x: int, y: int):
        """繪製汽車"""
        w, h = self.VEHICLE_SIZE, self.VEHICLE_SIZE - 4
        
        # 車身
        body_rect = pygame.Rect(x - w//2, y - h//2, w, h)
        pygame.draw.rect(self._screen, self.COLORS["car_body"], body_rect, border_radius=4)
        
        # 車頂
        roof_rect = pygame.Rect(x - w//3, y - h//3, w*2//3, h*2//3)
        pygame.draw.rect(self._screen, self.COLORS["car_window"], roof_rect, border_radius=2)
        
        # 車燈
        pygame.draw.circle(self._screen, (255, 255, 200), (x - w//2 + 3, y - h//4), 2)
        pygame.draw.circle(self._screen, (255, 255, 200), (x - w//2 + 3, y + h//4), 2)
        
        # 邊框
        pygame.draw.rect(self._screen, (20, 60, 120), body_rect, 1, border_radius=4)
    
    def _draw_ambulance(self, x: int, y: int):
        """繪製救護車"""
        w, h = self.VEHICLE_SIZE + 4, self.VEHICLE_SIZE
        
        # 車身
        body_rect = pygame.Rect(x - w//2, y - h//2, w, h)
        pygame.draw.rect(self._screen, self.COLORS["ambulance_body"], body_rect, border_radius=4)
        
        # 白色十字
        cross_size = 6
        pygame.draw.line(self._screen, self.COLORS["ambulance_cross"],
                        (x - cross_size, y), (x + cross_size, y), 3)
        pygame.draw.line(self._screen, self.COLORS["ambulance_cross"],
                        (x, y - cross_size), (x, y + cross_size), 3)
        
        # 警示燈
        pygame.draw.circle(self._screen, (255, 100, 100), (x, y - h//2 - 2), 3)
        
        # 邊框
        pygame.draw.rect(self._screen, (180, 30, 30), body_rect, 1, border_radius=4)
    
    def _draw_path(self, path: List[Tuple[int, int]], current_index: int, cell_size: int):
        """繪製車輛路徑"""
        if len(path) < 2:
            return
        
        for i in range(current_index, len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            px1, py1 = self._cell_to_pixel(x1, y1, cell_size)
            px2, py2 = self._cell_to_pixel(x2, y2, cell_size)
            
            pygame.draw.line(self._screen, self.COLORS["path"],
                           (px1, py1), (px2, py2), 2)
    
    # =========================================================================
    # 資訊面板
    # =========================================================================
    
    def _draw_info(self, render_data: Dict[str, Any]):
        """繪製資訊面板"""
        panel = pygame.Rect(5, 5, 140, 75)
        
        # 半透明背景
        s = pygame.Surface((140, 75), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self._screen.blit(s, (5, 5))
        pygame.draw.rect(self._screen, (100, 100, 100), panel, 1)
        
        step = render_data.get("step", 0)
        vehicle_count = len(render_data.get("vehicles", []))
        arrived = render_data.get("arrived_count", 0)
        
        texts = [
            f"Step: {step}",
            f"Vehicles: {vehicle_count}",
            f"Arrived: {arrived}",
        ]
        
        for i, text in enumerate(texts):
            surface = self._font.render(text, True, self.COLORS["text"])
            self._screen.blit(surface, (12, 12 + i * 20))


# =============================================================================
# 舊版相容
# =============================================================================

class Renderer(GridRenderer):
    """相容舊版"""
    pass


# =============================================================================
# Module Test
# =============================================================================

if __name__ == "__main__":
    print("=== Testing Grid Renderer ===\n")
    
    from grid_map import GridMap
    from objects import Car, Ambulance, Direction
    
    grid = GridMap(seed=42)
    boundary = grid.get_boundary_cells()
    vehicles = []
    
    if len(boundary) >= 2:
        car = Car(Direction.NORTH, grid_position=boundary[0], destination=boundary[-1])
        path = grid.dijkstra(boundary[0], boundary[-1])
        if path:
            car.set_path(path)
        vehicles.append(car)
    
    render_data = {
        "grid_map": grid,
        "vehicles": vehicles,
        "step": 0,
        "arrived_count": 0,
    }
    
    renderer = GridRenderer(render_mode="human")
    
    print("Displaying for 5 seconds...")
    start_time = time.time()
    
    while time.time() - start_time < 5:
        renderer.render(render_data)
        for v in vehicles:
            if not v.has_reached_destination():
                v.move_on_grid()
        render_data["step"] += 1
        time.sleep(0.1)
    
    renderer.close()
    print("\n=== Test Complete ===")
