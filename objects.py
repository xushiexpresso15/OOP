"""
objects.py - 物件定義模組
Smart Traffic Intersection Environment

定義模擬中的實體，使用 OOP 原則：
- 抽象類別 (Abstract Base Class): Vehicle
- 繼承 (Inheritance): Car, Ambulance
- 多型 (Polymorphism): 不同車輛類型的優先級行為
- 封裝 (Encapsulation): TrafficLight 狀態管理
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


class Direction(Enum):
    """車輛行進方向的列舉"""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


class LightState(Enum):
    """紅綠燈狀態的列舉"""
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class TurnType(Enum):
    """車輛轉向類型的列舉"""
    STRAIGHT = "straight"  # 直行
    LEFT = "left"          # 左轉
    RIGHT = "right"        # 右轉


# =============================================================================
# Abstract Base Class: Vehicle
# =============================================================================

class Vehicle(ABC):
    """
    車輛抽象基礎類別
    
    這是所有車輛類型的父類別，定義了共同的屬性和抽象方法。
    子類別必須實作 move() 和 get_priority() 方法。
    
    Attributes:
        direction (Direction): 車輛的行進方向
        lane (int): 車道編號 (0-based)
        position (float): 在車道中的位置 (0.0 = 起點, 1.0 = 通過路口)
        wait_time (int): 累計等待時間 (步數)
        priority_weight (int): 優先權重 (用於獎勵計算)
    """
    
    def __init__(self, direction: Direction, lane: int = 0, 
                 grid_position: tuple = None, destination: tuple = None):
        """
        初始化車輛
        
        Args:
            direction: 車輛行進方向
            lane: 車道編號，預設為 0
            grid_position: 在網格中的位置 (x, y)，用於 10x10 網格模式
            destination: 目的地座標，用於 10x10 網格模式
        """
        import random
        self._direction = direction
        self._lane = lane
        self._position = 0.0  # 起始位置 (舊版相容)
        self._wait_time = 0
        self._priority_weight = 1  # 預設權重，子類別可覆寫
        
        # 隨機決定轉向類型 (直行60%、左轉20%、右轉20%)
        turn_rand = random.random()
        if turn_rand < 0.6:
            self._turn_type = TurnType.STRAIGHT
        elif turn_rand < 0.8:
            self._turn_type = TurnType.LEFT
        else:
            self._turn_type = TurnType.RIGHT
        
        # 網格導航屬性 (用於 10x10 網格模式)
        self._grid_position = grid_position  # (x, y) 當前格子座標
        self._destination = destination       # (x, y) 目的地座標
        self._path = []                       # Dijkstra 計算的路徑
        self._path_index = 0                  # 當前在路徑中的位置
    
    # -------------------------------------------------------------------------
    # Properties (封裝)
    # -------------------------------------------------------------------------
    
    @property
    def direction(self) -> Direction:
        """取得車輛行進方向"""
        return self._direction
    
    @property
    def lane(self) -> int:
        """取得車道編號"""
        return self._lane
    
    @property
    def position(self) -> float:
        """取得車輛位置"""
        return self._position
    
    @position.setter
    def position(self, value: float):
        """設定車輛位置"""
        self._position = max(0.0, min(1.0, value))
    
    @property
    def wait_time(self) -> int:
        """取得累計等待時間"""
        return self._wait_time
    
    @property
    def priority_weight(self) -> int:
        """取得優先權重"""
        return self._priority_weight
    
    @property
    def turn_type(self) -> "TurnType":
        """取得轉向類型 (直行/左轉/右轉)"""
        return self._turn_type
    
    # -------------------------------------------------------------------------
    # Grid Navigation Properties (網格導航)
    # -------------------------------------------------------------------------
    
    @property
    def grid_position(self) -> tuple:
        """取得在網格中的位置 (x, y)"""
        return self._grid_position
    
    @grid_position.setter
    def grid_position(self, value: tuple):
        """設定在網格中的位置"""
        self._grid_position = value
    
    @property
    def destination(self) -> tuple:
        """取得目的地座標"""
        return self._destination
    
    @property
    def path(self) -> list:
        """取得路徑"""
        return self._path
    
    @property
    def path_index(self) -> int:
        """取得當前在路徑中的位置"""
        return self._path_index
    
    def set_path(self, path: list):
        """
        設定路徑 (由 Dijkstra 計算)
        
        Args:
            path: 路徑座標列表
        """
        self._path = path
        self._path_index = 0
    
    def move_on_grid(self) -> bool:
        """
        在網格中沿路徑移動一格
        
        Returns:
            bool: 是否已到達目的地
        """
        if not self._path or self._path_index >= len(self._path) - 1:
            return True  # 已到達
        
        self._path_index += 1
        self._grid_position = self._path[self._path_index]
        return self._grid_position == self._destination
    
    def has_reached_destination(self) -> bool:
        """
        檢查是否已到達目的地
        
        Returns:
            bool: 是否到達
        """
        return self._grid_position == self._destination
    
    # -------------------------------------------------------------------------
    # Abstract Methods (多型)
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def move(self, can_move: bool) -> bool:
        """
        移動車輛或等待
        
        Args:
            can_move: 是否可以移動 (綠燈時為 True)
            
        Returns:
            bool: 如果車輛通過路口則返回 True
        """
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """
        取得車輛的動態優先級
        
        Returns:
            int: 優先級分數 (越高越優先)
        """
        pass
    
    # -------------------------------------------------------------------------
    # Common Methods
    # -------------------------------------------------------------------------
    
    def increment_wait_time(self):
        """增加等待時間"""
        self._wait_time += 1
    
    def reset_wait_time(self):
        """重置等待時間"""
        self._wait_time = 0
    
    def has_passed(self) -> bool:
        """
        檢查車輛是否已通過路口
        
        Returns:
            bool: 位置 >= 1.0 表示已通過
        """
        return self._position >= 1.0
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(dir={self._direction.value}, pos={self._position:.2f}, wait={self._wait_time})"


# =============================================================================
# Concrete Class: Car (繼承)
# =============================================================================

class Car(Vehicle):
    """
    一般車輛類別
    
    繼承自 Vehicle，代表普通的汽車。
    優先權重為 1，移動速度標準。
    """
    
    MOVE_SPEED = 0.25  # 每步移動距離
    
    def __init__(self, direction: Direction, lane: int = 0, 
                 grid_position: tuple = None, destination: tuple = None):
        """
        初始化一般車輛
        
        Args:
            direction: 車輛行進方向
            lane: 車道編號
            grid_position: 網格位置 (用於 10x10 模式)
            destination: 目的地 (用於 10x10 模式)
        """
        super().__init__(direction, lane, grid_position, destination)
        self._priority_weight = 1  # 一般車輛權重
    
    def move(self, can_move: bool) -> bool:
        """
        移動車輛
        
        Args:
            can_move: 是否可以移動
            
        Returns:
            bool: 是否通過路口
        """
        if can_move:
            self._position += self.MOVE_SPEED
            self.reset_wait_time()
        else:
            self.increment_wait_time()
        
        return self.has_passed()
    
    def get_priority(self) -> int:
        """
        取得優先級 (考慮等待時間)
        
        Returns:
            int: 基礎權重 + 等待時間加成
        """
        return self._priority_weight + (self._wait_time // 10)


# =============================================================================
# Concrete Class: Ambulance (繼承 + 多型)
# =============================================================================

class Ambulance(Vehicle):
    """
    救護車類別
    
    繼承自 Vehicle，代表緊急救護車輛。
    具有更高的優先權重和特殊的警笛狀態。
    
    多型實作：
    - 更高的 priority_weight (5)
    - 警笛開啟時優先級進一步提升
    - 可能有不同的移動邏輯
    """
    
    MOVE_SPEED = 0.30  # 救護車速度較快
    SIREN_PRIORITY_BONUS = 10  # 警笛開啟時的額外優先級
    
    def __init__(self, direction: Direction, lane: int = 0, siren_on: bool = True,
                 grid_position: tuple = None, destination: tuple = None):
        """
        初始化救護車
        
        Args:
            direction: 車輛行進方向
            lane: 車道編號
            siren_on: 警笛是否開啟，預設為 True
            grid_position: 網格位置 (用於 10x10 模式)
            destination: 目的地 (用於 10x10 模式)
        """
        super().__init__(direction, lane, grid_position, destination)
        self._priority_weight = 5  # 救護車權重較高
        self._is_siren_on = siren_on
    
    @property
    def is_siren_on(self) -> bool:
        """取得警笛狀態"""
        return self._is_siren_on
    
    @is_siren_on.setter
    def is_siren_on(self, value: bool):
        """設定警笛狀態"""
        self._is_siren_on = value
    
    def move(self, can_move: bool) -> bool:
        """
        移動救護車
        
        救護車有較快的移動速度。
        
        Args:
            can_move: 是否可以移動
            
        Returns:
            bool: 是否通過路口
        """
        if can_move:
            self._position += self.MOVE_SPEED
            self.reset_wait_time()
        else:
            self.increment_wait_time()
        
        return self.has_passed()
    
    def get_priority(self) -> int:
        """
        取得優先級 (多型 - 考慮警笛狀態)
        
        救護車的優先級計算與一般車輛不同：
        - 基礎權重較高
        - 警笛開啟時有額外加成
        - 等待時間的懲罰權重更大
        
        Returns:
            int: 計算後的優先級分數
        """
        base_priority = self._priority_weight
        siren_bonus = self.SIREN_PRIORITY_BONUS if self._is_siren_on else 0
        wait_penalty_multiplier = 2  # 救護車等待的懲罰更大
        
        return base_priority + siren_bonus + (self._wait_time * wait_penalty_multiplier)


# =============================================================================
# Class: TrafficLight
# =============================================================================

class TrafficLight:
    """
    紅綠燈類別 (符合現實設計)
    
    管理單一方向組的紅綠燈狀態 (例如：南北向或東西向)。
    使用狀態機模式管理燈號切換，自動循環 綠→黃→紅→綠。
    
    現實時間設計：
    - 綠燈：40~80 秒 (隨機)
    - 黃燈：3 秒 (剩 1 秒時車輛不能通過)
    - 紅燈：由對向的 (綠燈 + 黃燈) 時間決定 (同步控制)
    
    Attributes:
        name (str): 燈號名稱 (例如："NS" 或 "EW")
        state (LightState): 當前燈號狀態
        timer (int): 當前狀態的剩餘時間 (秒)
    """
    
    import random as _random
    
    # 時間範圍設定 (秒) - 縮短週期讓模擬更快
    GREEN_TIME_MIN = 10
    GREEN_TIME_MAX = 20
    YELLOW_TIME = 2
    RED_TIME_MIN = 10
    RED_TIME_MAX = 25
    
    # 黃燈不可通過的臨界時間 (剩餘秒數)
    YELLOW_NO_PASS_THRESHOLD = 1
    
    def __init__(self, name: str, initial_state: LightState = LightState.RED):
        """
        初始化紅綠燈
        
        Args:
            name: 燈號名稱識別
            initial_state: 初始狀態，預設為紅燈
        """
        import random
        self._name = name
        self._state = initial_state
        self._timer = self._get_random_duration(initial_state)
        
        # 儲存當前週期的時間設定
        self._current_green_time = random.randint(self.GREEN_TIME_MIN, self.GREEN_TIME_MAX)
        self._current_red_time = random.randint(self.RED_TIME_MIN, self.RED_TIME_MAX)
    
    def _get_random_duration(self, state: LightState) -> int:
        """
        根據狀態取得持續時間
        
        注意：在同步模式下，紅燈時間由對向的綠燈+黃燈決定，
        這裡只設置一個佔位值，實際由環境控制。
        
        Args:
            state: 燈號狀態
            
        Returns:
            int: 持續時間 (秒)
        """
        import random
        if state == LightState.GREEN:
            return random.randint(self.GREEN_TIME_MIN, self.GREEN_TIME_MAX)
        elif state == LightState.YELLOW:
            return self.YELLOW_TIME
        else:  # RED
            # 紅燈時間由同步控制決定，這裡設為最大值作為佔位
            # 實際上紅燈會在對向黃燈結束時被切換成綠燈
            return 999  # 佔位值，不會實際用到
    
    @property
    def name(self) -> str:
        """取得燈號名稱"""
        return self._name
    
    @property
    def state(self) -> LightState:
        """取得當前狀態"""
        return self._state
    
    @property
    def timer(self) -> int:
        """取得剩餘時間 (秒)"""
        return self._timer
    
    @property
    def is_green(self) -> bool:
        """檢查是否為綠燈"""
        return self._state == LightState.GREEN
    
    @property
    def is_yellow(self) -> bool:
        """檢查是否為黃燈"""
        return self._state == LightState.YELLOW
    
    @property
    def is_red(self) -> bool:
        """檢查是否為紅燈"""
        return self._state == LightState.RED
    
    @property
    def can_pass(self) -> bool:
        """
        檢查車輛是否可以通過
        
        規則：
        - 綠燈：可以通過
        - 黃燈且剩餘時間 > 1 秒：可以通過
        - 黃燈且剩餘時間 <= 1 秒：不可通過
        - 紅燈：不可通過
        
        Returns:
            bool: 車輛是否可以通行
        """
        if self._state == LightState.GREEN:
            return True
        elif self._state == LightState.YELLOW:
            return self._timer > self.YELLOW_NO_PASS_THRESHOLD
        else:  # RED
            return False
    
    def set_state(self, new_state: LightState):
        """
        設定燈號狀態並重置計時器
        
        Args:
            new_state: 新的燈號狀態
        """
        self._state = new_state
        self._timer = self._get_random_duration(new_state)
    
    def tick(self) -> bool:
        """
        時間遞減 (每個 step 呼叫一次，代表 1 秒)
        
        自動循環：綠燈 → 黃燈 → 紅燈 → 綠燈
        
        Returns:
            bool: 如果狀態發生轉換則返回 True
        """
        self._timer -= 1
        
        if self._timer <= 0:
            # 自動轉換到下一個狀態 (完整循環)
            if self._state == LightState.GREEN:
                self.set_state(LightState.YELLOW)
            elif self._state == LightState.YELLOW:
                self.set_state(LightState.RED)
            else:  # RED
                self.set_state(LightState.GREEN)
            return True
        
        return False
    
    def force_toggle(self):
        """
        強制切換燈號 (由 Agent 觸發)
        
        狀態轉換邏輯：
        - GREEN -> YELLOW (準備變紅)
        - YELLOW -> RED (變紅)
        - RED -> GREEN (變綠)
        """
        if self._state == LightState.GREEN:
            self.set_state(LightState.YELLOW)
        elif self._state == LightState.YELLOW:
            self.set_state(LightState.RED)
        else:  # RED
            self.set_state(LightState.GREEN)
    
    def get_display_info(self) -> dict:
        """
        取得顯示用資訊
        
        Returns:
            dict: 包含燈號狀態和剩餘時間的字典
        """
        return {
            "state": self._state.value,
            "timer": self._timer,
            "can_pass": self.can_pass,
        }
    
    def __repr__(self) -> str:
        return f"TrafficLight({self._name}, state={self._state.value}, timer={self._timer}s, can_pass={self.can_pass})"


# =============================================================================
# Factory Function (Optional Helper)
# =============================================================================

def create_vehicle(vehicle_type: str, direction: Direction, lane: int = 0) -> Vehicle:
    """
    車輛工廠函式
    
    根據類型字串創建對應的車輛物件。
    
    Args:
        vehicle_type: 車輛類型 ("car" 或 "ambulance")
        direction: 行進方向
        lane: 車道編號
        
    Returns:
        Vehicle: 創建的車輛物件
        
    Raises:
        ValueError: 未知的車輛類型
    """
    vehicle_type = vehicle_type.lower()
    
    if vehicle_type == "car":
        return Car(direction, lane)
    elif vehicle_type == "ambulance":
        return Ambulance(direction, lane)
    else:
        raise ValueError(f"Unknown vehicle type: {vehicle_type}")


# =============================================================================
# Module Test
# =============================================================================

if __name__ == "__main__":
    # 測試物件創建
    print("=== Testing Objects Module ===\n")
    
    # 測試車輛
    car = Car(Direction.NORTH, lane=0)
    ambulance = Ambulance(Direction.EAST, lane=1, siren_on=True)
    
    print(f"Created: {car}")
    print(f"Created: {ambulance}")
    print(f"Car priority: {car.get_priority()}")
    print(f"Ambulance priority: {ambulance.get_priority()}")
    
    # 模擬移動
    print("\n--- Simulating Movement ---")
    for step in range(5):
        car_passed = car.move(can_move=(step % 2 == 0))
        ambulance_passed = ambulance.move(can_move=True)
        print(f"Step {step + 1}: Car pos={car.position:.2f}, Ambulance pos={ambulance.position:.2f}")
    
    # 測試紅綠燈
    print("\n--- Testing Traffic Light ---")
    light = TrafficLight("NS", LightState.GREEN)
    print(f"Initial: {light}")
    
    for _ in range(3):
        light.toggle()
        print(f"After toggle: {light}")
    
    print("\n=== All Tests Passed ===")
