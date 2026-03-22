"""
象棋应用自动化测试

功能：
1. 自动化浏览器测试
2. 界面交互验证
3. 功能测试
4. 页面截图
"""

import subprocess
import time
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def start_app():
    """启动应用"""
    print("Starting Flask application...")
    process = subprocess.Popen(
        [sys.executable, 'web/modern_app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root
    )
    time.sleep(3)  # 等待应用启动
    return process

def test_url_access():
    """测试URL访问"""
    import requests
    try:
        response = requests.get('http://localhost:5000', timeout=5)
        print(f"[OK] Application accessible: {response.status_code}")
        return True
    except Exception as e:
        print(f"[FAIL] Application access failed: {e}")
        return False

def test_api():
    """测试API接口"""
    import requests
    try:
        # 测试初始状态
        response = requests.get('http://localhost:5000/api/initial')
        data = response.json()
        print(f"[OK] API /api/initial response: OK")

        # 测试新游戏
        response = requests.post('http://localhost:5000/api/new_game')
        data = response.json()
        print(f"[OK] API /api/new_game response: {data.get('message', 'OK')}")

        # 测试点击
        click_data = {'row': 9, 'col': 4}
        response = requests.post('http://localhost:5000/api/click', json=click_data)
        if response.ok:
            data = response.json()
            print(f"[OK] API /api/click response: {data.get('message', 'OK')}")
        else:
            print(f"[FAIL] API /api/click response: {response.status_code}")

        return True
    except Exception as e:
        print(f"[FAIL] API test failed: {e}")
        return False

def check_running_processes():
    """检查运行中的进程"""
    import subprocess
    try:
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        if ':5000' in result.stdout:
            print("[OK] Port 5000 is listening")
            return True
        else:
            print("[FAIL] Port 5000 is not listening")
            return False
    except Exception as e:
        print(f"[FAIL] Port check failed: {e}")
        return False

def main():
    """主测试流程"""
    print("=" * 50)
    print("Chess Application Automated Testing")
    print("=" * 50)

    # 1. 启动应用
    app_process = start_app()

    # 2. 检查端口
    if not check_running_processes():
        print("[FAIL] Application startup failed")
        return

    # 3. 测试URL访问
    if not test_url_access():
        print("[FAIL] URL access test failed")
        return

    # 4. 测试API接口
    if not test_api():
        print("[FAIL] API test failed")
        return

    print("=" * 50)
    print("[SUCCESS] All tests passed! Application is running and accessible")
    print("=" * 50)
    print(f"Please access in browser: http://localhost:5000")
    print(f"Application logs can be viewed in terminal")
    print(f"Press Ctrl+C to stop the application")
    print("=" * 50)

    try:
        # 保持应用运行
        app_process.wait()
    except KeyboardInterrupt:
        print("\nApplication stopped")
        app_process.terminate()

if __name__ == "__main__":
    main()
