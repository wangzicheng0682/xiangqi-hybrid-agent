import requests
import json

initial_board = [
    ['r', 'n', 'b', 'a', 'k', 'a', 'b', 'n', 'r'],
    ['', '', '', '', '', '', '', '', ''],
    ['', 'c', '', '', '', '', '', 'c', ''],
    ['p', '', 'p', '', 'p', '', 'p', '', 'p'],
    ['', '', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', '', ''],
    ['P', '', 'P', '', 'P', '', 'P', '', 'P'],
    ['', 'C', '', '', '', '', '', 'C', ''],
    ['', '', '', '', '', '', '', '', ''],
    ['R', 'N', 'B', 'A', 'K', 'A', 'B', 'N', 'R'],
]

print("测试移动API - 红炮前进:")
response = requests.post(
    'http://localhost:8000/api/move',
    json={
        'board': initial_board,
        'from_row': 7,
        'from_col': 1,
        'to_row': 5,
        'to_col': 1,
        'red_to_move': True
    }
)
print(f"状态码：{response.status_code}")
print(f"响应：{json.dumps(response.json(), ensure_ascii=False, indent=2)}")
