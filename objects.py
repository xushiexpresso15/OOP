from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


class Direction(Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


class LightState(Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class TurnType(Enum):
    STRAIGHT = "straight" # 直行
    LEFT = "left" # 左轉
    RIGHT = "right" # 右轉

class Vehicle(ABC):
    """
    定義車子應該長怎樣
    繼承他的class必須實作move()、get_priority()
    
    Attributes:
        direction (Direction): 車輛的行進方向
        lane (int): 車道編號 
        position (float): 在車道中的位置
        wait_time (int): 累計等待時間
        priority_weight (int): 權重
    """
    
    def __init__(self, direction: Direction, lane: int = 0, 
                 grid_position: tuple = None, destination: tuple = None):
        #init constructor
        import random
        self._direction = direction
        self._lane = lane
        self._position = 0.0
        self._wait_time = 0
        self._priority_weight = 1

        turn_rand = random.random()
        if turn_rand < 0.6:
            self._turn_type = TurnType.STRAIGHT
        elif turn_rand < 0.8:
            self._turn_type = TurnType.LEFT
        else:
            self._turn_type = TurnType.RIGHT
        
        self._grid_position = grid_position
        self._destination = destination
        self._path = []
        self._path_index = 0
    
    #encapsulation
    @property
    def direction(self) -> Direction:
        return self._direction

    @direction.setter
    def direction(self, value: Direction):
        self._direction = value
    
    @property
    def lane(self) -> int:
        return self._lane
    
    @property
    def position(self) -> float:
        return self._position
    
    @position.setter
    def position(self, value: float):
        self._position = max(0.0, min(1.0, value))
    
    @property
    def wait_time(self) -> int:
        return self._wait_time
    
    @property
    def priority_weight(self) -> int:
        return self._priority_weight
    
    @property
    def turn_type(self) -> "TurnType":
        return self._turn_type
    
    @property
    def grid_position(self) -> tuple:
        return self._grid_position
    
    @grid_position.setter
    def grid_position(self, value: tuple):
        self._grid_position = value
    
    @property
    def destination(self) -> tuple:
        return self._destination
    
    @property
    def path(self) -> list:
        return self._path
    
    @property
    def path_index(self) -> int:
        return self._path_index
    
    def set_path(self, path: list):
        self._path = path
        self._path_index = 0
    
    def move_on_grid(self) -> bool:
        if not self._path or self._path_index >= len(self._path) - 1:
            return True  #到終點了
        
        self._path_index += 1
        self._grid_position = self._path[self._path_index]
        return self._grid_position == self._destination
    
    def has_reached_destination(self) -> bool:
        return self._grid_position == self._destination
    
    #Polymorphysm
    @abstractmethod
    def move(self, can_move: bool) -> bool:
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        pass
    
    def increment_wait_time(self):
        self._wait_time += 1
    
    def reset_wait_time(self):
        self._wait_time = 0
    
    def has_passed(self) -> bool:
        return self._position >= 1.0
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(dir={self._direction.value}, pos={self._position:.2f}, wait={self._wait_time})"

#繼承vehicle
class Car(Vehicle):
    MOVE_SPEED = 0.25
    
    def __init__(self, direction: Direction, lane: int = 0, 
                 grid_position: tuple = None, destination: tuple = None):
        super().__init__(direction, lane, grid_position, destination)
        self._priority_weight = 1 #一般車子權重是1
    
    def move(self, can_move: bool) -> bool:
        if can_move:
            self._position += self.MOVE_SPEED
            self.reset_wait_time()
        else:
            self.increment_wait_time()
        
        return self.has_passed()
    
    def get_priority(self) -> int:
        return self._priority_weight + (self._wait_time // 10)

class Ambulance(Vehicle):
    MOVE_SPEED = 0.30
    SIREN_PRIORITY_BONUS = 10
    
    def __init__(self, direction: Direction, lane: int = 0, siren_on: bool = True, grid_position: tuple = None, destination: tuple = None):
        super().__init__(direction, lane, grid_position, destination)
        self._priority_weight = 5  #救護車權重較高
        self._is_siren_on = siren_on
    
    @property
    def is_siren_on(self) -> bool:
        return self._is_siren_on
    
    @is_siren_on.setter
    def is_siren_on(self, value: bool):
        self._is_siren_on = value
    
    def move(self, can_move: bool) -> bool:
        if can_move:
            self._position += self.MOVE_SPEED
            self.reset_wait_time()
        else:
            self.increment_wait_time()
        
        return self.has_passed()
    
    def get_priority(self) -> int:
        base_priority = self._priority_weight
        siren_bonus = self.SIREN_PRIORITY_BONUS if self._is_siren_on else 0
        wait_penalty_multiplier = 2
        
        return base_priority + siren_bonus + (self._wait_time * wait_penalty_multiplier)


class TrafficLight:
    #紅綠燈
    import random as _random
    
    GREEN_TIME_MIN = 10 #綠燈10~20秒
    GREEN_TIME_MAX = 20
    YELLOW_TIME = 2
    RED_TIME_MIN = 10 #紅燈10~25秒
    RED_TIME_MAX = 25
    
    # 黃燈不可通過的臨界時間
    YELLOW_NO_PASS_THRESHOLD = 1
    
    def __init__(self, name: str, initial_state: LightState = LightState.RED):
        import random
        self._name = name
        self._state = initial_state
        self._timer = self._get_random_duration(initial_state)
        self._current_green_time = random.randint(self.GREEN_TIME_MIN, self.GREEN_TIME_MAX)
        self._current_red_time = random.randint(self.RED_TIME_MIN, self.RED_TIME_MAX)
    
    def _get_random_duration(self, state: LightState) -> int:
        """
        Args:
            state: 燈號狀態
        Returns:
            int: 持續時間 
        """
        import random
        if state == LightState.GREEN:
            return random.randint(self.GREEN_TIME_MIN, self.GREEN_TIME_MAX)
        elif state == LightState.YELLOW:
            return self.YELLOW_TIME
        else:  # RED
            return 999
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def state(self) -> LightState:
        return self._state
    
    @property
    def timer(self) -> int:
        return self._timer
    
    @property
    def is_green(self) -> bool:
        return self._state == LightState.GREEN
    
    @property
    def is_yellow(self) -> bool:
        return self._state == LightState.YELLOW
    
    @property
    def is_red(self) -> bool:
        return self._state == LightState.RED
    
    @property
    def can_pass(self) -> bool:
        if self._state == LightState.GREEN:
            return True
        elif self._state == LightState.YELLOW:
            return self._timer > self.YELLOW_NO_PASS_THRESHOLD
        else:  # RED
            return False
    
    def set_state(self, new_state: LightState):
        self._state = new_state
        self._timer = self._get_random_duration(new_state)
    
    def tick(self) -> bool:
        self._timer -= 1
        
        if self._timer <= 0:
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
        agent 模式需要一個強制切換紅綠燈的模組
        """
        if self._state == LightState.GREEN:
            self.set_state(LightState.YELLOW)
        elif self._state == LightState.YELLOW:
            self.set_state(LightState.RED)
        else:  # RED
            self.set_state(LightState.GREEN)
    
    def get_display_info(self) -> dict:
        return {
            "state": self._state.value,
            "timer": self._timer,
            "can_pass": self.can_pass,
        }
    
    def __repr__(self) -> str:
        return f"TrafficLight({self._name}, state={self._state.value}, timer={self._timer}s, can_pass={self.can_pass})"
    

def create_vehicle(vehicle_type: str, direction: Direction, lane: int = 0) -> Vehicle:
    """
    Args:
        vehicle_type: 車輛類型
        direction: 行進方向
        lane: 車道編號
        
    Returns:
        Vehicle: 創建的車輛object
        
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

if __name__ == "__main__":
    #test object creation
    print("=== Testing Objects Module ===\n")
    
    # test car
    car = Car(Direction.NORTH, lane=0)
    ambulance = Ambulance(Direction.EAST, lane=1, siren_on=True)
    
    print(f"Created: {car}")
    print(f"Created: {ambulance}")
    print(f"Car priority: {car.get_priority()}")
    print(f"Ambulance priority: {ambulance.get_priority()}")
    
    # test movement
    print("\n--- Simulating Movement ---")
    for step in range(5):
        car_passed = car.move(can_move=(step % 2 == 0))
        ambulance_passed = ambulance.move(can_move=True)
        print(f"Step {step + 1}: Car pos={car.position:.2f}, Ambulance pos={ambulance.position:.2f}")
    
    # test traffic light
    print("\n--- Testing Traffic Light ---")
    light = TrafficLight("NS", LightState.GREEN)
    print(f"Initial: {light}")
    
    for _ in range(3):
        light.toggle()
        print(f"After toggle: {light}")
    
    print("\n=== All Tests Passed ===")
