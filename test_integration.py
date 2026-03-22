import requests
import json

BASE_URL = 'http://localhost:8000'

def test_health():
    try:
        r = requests.get(f'{BASE_URL}/health', timeout=5)
        print(f'健康检查: {r.status_code} - {r.json()}')
        return True
    except Exception as e:
        print(f'健康检查失败: {e}')
        return False

def test_legal_moves():
    board = [
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
    try:
        r = requests.post(f'{BASE_URL}/api/legal-moves', json={'board': board, 'row': 7, 'col': 1}, timeout=5)
        print(f'合法走法: {r.status_code} - {r.json()}')
        return True
    except Exception as e:
        print(f'合法走法失败: {e}')
        return False

def test_move():
    board = [
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
    try:
        r = requests.post(f'{BASE_URL}/api/move', json={
            'board': board,
            'from_row': 7, 'from_col': 1,
            'to_row': 5, 'to_col': 1,
            'red_to_move': True
        }, timeout=5)
        print(f'移动棋子: {r.status_code}')
        if r.status_code == 200:
            data = r.json()
            print(f'  FEN: {data["fen"][:50]}...')
            print(f'  被吃: {data["captured"] or "无"}')
        else:
            print(f'  错误: {r.text}')
        return r.status_code == 200
    except Exception as e:
        print(f'移动棋子失败: {e}')
        return False

def test_analyze():
    fen = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1'
    board = [
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
    try:
        r = requests.post(f'{BASE_URL}/api/analyze', json={
            'fen': fen,
            'board': board,
            'use_vision': False
        }, timeout=30)
        print(f'分析局面: {r.status_code}')
        if r.status_code == 200:
            data = r.json()
            print(f'  讲解: {data["explanation"][:100]}...')
        else:
            print(f'  错误: {r.text}')
        return r.status_code == 200
    except Exception as e:
        print(f'分析局面失败: {e}')
        return False

if __name__ == '__main__':
    print('=' * 50)
    print('系统联调测试')
    print('=' * 50)
    
    results = []
    results.append(('健康检查', test_health()))
    results.append(('合法走法', test_legal_moves()))
    results.append(('移动棋子', test_move()))
    results.append(('分析局面', test_analyze()))
    
    print('=' * 50)
    print('测试结果:')
    for name, passed in results:
        status = '✅ 通过' if passed else '❌ 失败'
        print(f'  {name}: {status}')
    print('=' * 50)
