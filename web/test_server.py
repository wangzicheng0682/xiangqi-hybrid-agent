"""
简单的HTTP服务器 - 用于测试产品级HTML

启动命令:
    python web/test_server.py
"""

import http.server
import socketserver
import os
from pathlib import Path

PORT = 8888
DIRECTORY = Path(__file__).parent


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 默认返回index.html
        if self.path == '/' or self.path == '':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            # 读取HTML文件
            html_file = DIRECTORY / 'test_product.html'
            if html_file.exists():
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                self.wfile.write(html_content.encode('utf-8'))
            elif self.path.endswith('.html'):
                # 处理其他HTML文件请求
                html_file = DIRECTORY / self.path[1:]
                if html_file.exists():
                    with open(html_file, 'rb') as f:
                        html_content = f.read()
                    self.wfile.write(html_content.encode('utf-8'))
            else:
                self.send_error(404, "File Not Found")


def main():
    """主函数"""
    # 切换到web目录
    os.chdir(DIRECTORY)

    # 创建HTTP服务器
    server = http.server.HTTPServer(("0.0.0.0", PORT), CustomHTTPRequestHandler)

    print("""
    ========================================
    象棋AI混合代理 - 产品级HTML测试服务器
    ========================================

    服务器地址：http://localhost:{PORT}
    HTML文件：{DIRECTORY / 'test_product.html'}

    按 Ctrl+C 停止服务器
    ========================================
    """)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"\n服务器启动失败: {e}")


if __name__ == "__main__":
    main()
