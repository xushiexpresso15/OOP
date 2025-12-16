import pygame
import numpy as np
import math
import time
from typing import Dict, List, Any, Optional, Tuple

from objects import Vehicle, Car, Ambulance, TrafficLight, LightState, Direction, TurnType


class GridRenderer:
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 800
    
    ANIMATION_DURATION = 0.05
    ANIMATION_FRAMES = 3
    
    COLORS = {
        "background": (34, 139, 34),       # 背景綠色
        "wall": (34, 139, 34),             # 牆壁 = 草地
        "road": (50, 50, 50),              # 柏油路深灰色
        "road_line": (255, 255, 255),      # 白色道路線
        "road_edge": (80, 80, 80),         # 道路邊緣
        "intersection": (60, 60, 60),      # 路口

        #車子
        "car_body": (30, 100, 200),        # 藍色車身
        "car_window": (150, 200, 255),     # 淺藍色車窗
        "ambulance_body": (255, 50, 50),   # 紅色救護車
        "ambulance_cross": (255, 255, 255), # 白色十字
        
        #紅綠燈
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
        self._screen.fill(self.COLORS["background"])
        
        grid_map = render_data.get("grid_map")
        
        if grid_map:
            cell_size = self._get_cell_size(grid_map)
            self._draw_roads(grid_map, cell_size)
            self._draw_traffic_lights(grid_map, cell_size)
            vehicles = render_data.get("vehicles", [])
            self._draw_vehicles(vehicles, cell_size)
        
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
    
    
    def _draw_roads(self, grid_map, cell_size: int):
        from grid_map import GridCell
        
        for y in range(grid_map.actual_height):
            for x in range(grid_map.actual_width):
                cell = grid_map.grid[y][x]
                
                if cell == GridCell.EMPTY:
                    continue
                
                rect = pygame.Rect(
                    x * cell_size, y * cell_size,
                    cell_size, cell_size
                )
                
                pygame.draw.rect(self._screen, self.COLORS["road"], rect)
                pygame.draw.rect(self._screen, self.COLORS["road_edge"], rect, 2)
                if cell == GridCell.INTERSECTION:
                    cx, cy = self._cell_to_pixel(x, y, cell_size)
                    pygame.draw.circle(self._screen, self.COLORS["road_line"], 
                                      (cx, cy), 3)
                else:
                    self._draw_road_markings(x, y, cell_size, grid_map)
    
    def _draw_road_markings(self, x: int, y: int, cell_size: int, grid_map):
        from grid_map import GridCell
        
        cx, cy = self._cell_to_pixel(x, y, cell_size)
        has_north = y > 0 and grid_map.grid[y-1][x] != GridCell.EMPTY
        has_south = y < grid_map.actual_height-1 and grid_map.grid[y+1][x] != GridCell.EMPTY
        has_west = x > 0 and grid_map.grid[y][x-1] != GridCell.EMPTY
        has_east = x < grid_map.actual_width-1 and grid_map.grid[y][x+1] != GridCell.EMPTY
        
        line_len = cell_size // 4
        if has_north or has_south:
            pygame.draw.line(self._screen, self.COLORS["road_line"], (cx, cy - line_len), (cx, cy + line_len), 1)
        if has_west or has_east:
            pygame.draw.line(self._screen, self.COLORS["road_line"], (cx - line_len, cy), (cx + line_len, cy), 1)
            
    
    def _draw_traffic_lights(self, grid_map, cell_size: int):
        for (x, y), intersection in grid_map.intersections.items():
            px, py = self._cell_to_pixel(x, y, cell_size)
            self._draw_single_traffic_light(
                px - cell_size // 3, py - cell_size // 4,
                intersection.traffic_light_ns.state,
                vertical=True
            )
            
            self._draw_single_traffic_light(
                px + cell_size // 4, py - cell_size // 3,
                intersection.traffic_light_ew.state,
                vertical=False
            )
    
    def _draw_single_traffic_light(self, x: int, y: int, state: LightState, vertical: bool):
        r = self.LIGHT_RADIUS
        spacing = r * 2 + 4
        
        if vertical:
            box_w, box_h = r * 2 + 6, spacing * 3 + 4
            box_x, box_y = x - box_w // 2, y - box_h // 2
            pygame.draw.rect(self._screen, self.COLORS["light_box"], (box_x, box_y, box_w, box_h))
            pygame.draw.rect(self._screen, (80, 80, 80), (box_x, box_y, box_w, box_h), 1)
            
            lights_pos = [
                (x, y - spacing), #red
                (x, y), #Yellow
                (x, y + spacing), #green
            ]
        else:
            box_w, box_h = spacing * 3 + 4, r * 2 + 6
            box_x, box_y = x - box_w // 2, y - box_h // 2
            pygame.draw.rect(self._screen, self.COLORS["light_box"],
                           (box_x, box_y, box_w, box_h))
            pygame.draw.rect(self._screen, (80, 80, 80),
                           (box_x, box_y, box_w, box_h), 1)
            
            lights_pos = [
                (x - spacing, y), 
                (x, y),
                (x + spacing, y),
            ]
        
        light_colors = [
            (self.COLORS["light_red"] if state == LightState.RED else self.COLORS["light_off"]),
            (self.COLORS["light_yellow"] if state == LightState.YELLOW else self.COLORS["light_off"]),
            (self.COLORS["light_green"] if state == LightState.GREEN else self.COLORS["light_off"]),
        ]
        
        for pos, color in zip(lights_pos, light_colors):
            pygame.draw.circle(self._screen, color, pos, r)
            if color != self.COLORS["light_off"]:
                glow = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*color[:3], 80), (r*2, r*2), r*2)
                self._screen.blit(glow, (pos[0] - r*2, pos[1] - r*2))
    
    def _draw_vehicles(self, vehicles: List[Vehicle], cell_size: int):
        for vehicle in vehicles:
            if vehicle.grid_position is None:
                continue
            
            x, y = vehicle.grid_position
            px, py = self._cell_to_pixel(x, y, cell_size)
            
            # 畫車道
            lane_offset = cell_size // 4
            move_dir = self._get_vehicle_direction(vehicle)
            #靠右行駛
            if move_dir == "n":
                px -= lane_offset
            elif move_dir == "s":
                px += lane_offset
            elif move_dir == "e":
                py -= lane_offset
            elif move_dir == "w":
                py += lane_offset
            
            if vehicle.path and len(vehicle.path) > vehicle.path_index: # draw car route
                self._draw_path(vehicle.path, vehicle.path_index, cell_size)
            
            if isinstance(vehicle, Ambulance):
                self._draw_ambulance(px, py, move_dir)
            else:
                self._draw_car(px, py, move_dir)
            
            if vehicle.destination:
                dx, dy = vehicle.destination
                dpx, dpy = self._cell_to_pixel(dx, dy, cell_size)
                pygame.draw.rect(self._screen, self.COLORS["destination"],
                               (dpx - 6, dpy - 6, 12, 12), 2)
    
    def _get_vehicle_direction(self, vehicle) -> str:
        if hasattr(vehicle, 'direction') and vehicle.direction:
            d = vehicle.direction
            if hasattr(d, 'value'):
                d = d.value
            if d.lower() in ['north', 'n']: return 'n'
            if d.lower() in ['south', 's']: return 's'
            if d.lower() in ['east', 'e']: return 'e'
            if d.lower() in ['west', 'w']: return 'w'
            
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
    
    def _draw_rotated_surface(self, x: int, y: int, surface: pygame.Surface, direction: str):
        angle = 0
        if direction == "e":
            angle = -90
        elif direction == "s":
            angle = 180
        elif direction == "w":
            angle = 90
        
        if angle != 0:
            rotated_surface = pygame.transform.rotate(surface, angle)
        else:
            rotated_surface = surface
            
        rect = rotated_surface.get_rect(center=(x, y))
        self._screen.blit(rotated_surface, rect)

    def _draw_car(self, x: int, y: int, direction: str):
        size = self.VEHICLE_SIZE
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        w, h = size - 8, size
        cx, cy = size // 2, size // 2
        
        body_rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
        pygame.draw.rect(surface, self.COLORS["car_body"], body_rect, border_radius=4)
        roof_rect = pygame.Rect(cx - w//2 + 2, cy - h//4, w - 4, h//2)
        pygame.draw.rect(surface, self.COLORS["car_window"], roof_rect, border_radius=2)
        pygame.draw.circle(surface, (255, 255, 200), (cx - w//2 + 3, cy - h//2 + 2), 2)
        pygame.draw.circle(surface, (255, 255, 200), (cx + w//2 - 3, cy - h//2 + 2), 2)
        pygame.draw.circle(surface, (200, 50, 50), (cx - w//2 + 3, cy + h//2 - 2), 2)
        pygame.draw.circle(surface, (200, 50, 50), (cx + w//2 - 3, cy + h//2 - 2), 2)
        self._draw_rotated_surface(x, y, surface, direction)
    
    def _draw_ambulance(self, x: int, y: int, direction: str):
        size = self.VEHICLE_SIZE + 4
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        w, h = size - 6, size
        cx, cy = size // 2, size // 2
        
        body_rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
        pygame.draw.rect(surface, self.COLORS["ambulance_body"], body_rect, border_radius=4)
        cross_size = 6
        pygame.draw.line(surface, self.COLORS["ambulance_cross"], (cx - cross_size, cy), (cx + cross_size, cy), 3)
        pygame.draw.line(surface, self.COLORS["ambulance_cross"], (cx, cy - cross_size), (cx, cy + cross_size), 3)
        pygame.draw.circle(surface, (255, 100, 100), (cx, cy - h//4), 3)
        pygame.draw.circle(surface, (255, 255, 255), (cx - w//2 + 3, cy - h//2 + 2), 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx + w//2 - 3, cy - h//2 + 2), 2)
        self._draw_rotated_surface(x, y, surface, direction)
    
    def _draw_path(self, path: List[Tuple[int, int]], current_index: int, cell_size: int):
        if len(path) < 2:
            return
        
        for i in range(current_index, len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            px1, py1 = self._cell_to_pixel(x1, y1, cell_size)
            px2, py2 = self._cell_to_pixel(x2, y2, cell_size)
            
            pygame.draw.line(self._screen, self.COLORS["path"],
                           (px1, py1), (px2, py2), 2)
    
    #UI
    def _draw_info(self, render_data: Dict[str, Any]):
        panel = pygame.Rect(5, 5, 140, 75)
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

class Renderer(GridRenderer):
    pass


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
