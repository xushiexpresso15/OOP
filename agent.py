"""
agent.py - 智慧交通號誌控制 Agent

注意事項 (Notes for Developers):
1. 這個檔案是用來實作 Agent 的邏輯。
2. 使用者執行 `py main.py agent <size> [vehicle_count]` 時，主程式會呼叫這裡的 `step` 函式。
3. 您可以通過 `env` 參數與環境互動：
   - env.get_intersection_states(): 取得所有路口的狀態 (紅綠燈、剩餘時間等)
   - env.control_intersection(position, action): 控制指定路口
     - position: (x, y) 座標，從 states 中取得
     - action: 可以是 'toggle' (切換), 'ns_green' (南北綠), 'ew_green' (東西綠), 或 'hold' (保持)
   - env.get_vehicle_states(): 取得所有車輛資訊 (位置、目的地、類型等)
   - env.update_intersections(): 手動推進紅綠燈計時器 (必須呼叫，否則時間不會動)
   
實作目標：
- 設計一個演算法或是規則，根據車流量動態調整紅綠燈，讓交通更順暢。
"""

def step(env):
    """
    Agent 的決策邏輯
    
    這個函式會在每個模擬步驟被呼叫一次。
    
    Args:
        env: GridTrafficEnv 實例
    """
    
    # 1. 觀察環境
    # intersection_states = env.get_intersection_states()
    # vehicle_states = env.get_vehicle_states()
    
    # print(f"Vehicles: {len(vehicle_states)}")
    # for v in vehicle_states:
    #     print(f"  - Pos: {v['position']} -> Dest: {v['destination']}")
    
    # 2. 實作您的控制邏輯 (範例：全部路口保持不變)
    # for state in states:
    #     pos = state['position']
    #     env.control_intersection(pos, 'hold')
    
    # 3. 重要：必須手動更新紅綠燈計時器
    env.update_intersections()
