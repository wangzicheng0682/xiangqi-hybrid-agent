"""
超简单的HTTP服务器 - 直接返回HTML内容

启动命令:
    python web/simple_server.py
"""

import http.server
import socketserver
import os
from pathlib import Path

PORT = 8888
DIRECTORY = Path(__file__).parent


class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 直接返回HTML内容
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>象棋AI混合代理 - 产品级</title>
    <style>
        body {
            font-family: '楷体', 'STKaiti', 'KaiTi', serif;
            background: linear-gradient(135deg, #F5F5DC 0%, #E8E4D9 100%);
            margin: 0;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #FFFFFF;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }

        h1 {
            color: #C41E3A;
            text-align: center;
            font-size: 32px;
            margin-bottom: 30px;
            text-shadow: 3px 3px 6px rgba(0, 0, 0, 0.2);
        }

        .status {
            background: rgba(212, 175, 55, 0.1);
            border-left: 4px solid #D4AF37;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 20px;
            color: #2C3E50;
            font-size: 16px;
        }

        .success {
            color: #4CAF50;
            font-weight: bold;
        }

        .info {
            background: rgba(76, 175, 80, 0.1);
            border-left: 4px solid #4CAF50;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 20px;
            color: #2C3E50;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        .tab-btn {
            flex: 1;
            padding: 15px 25px;
            background: linear-gradient(135deg, #C41E3A, #E85A6C);
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(196, 30, 58, 0.3);
            transition: all 0.3s;
        }

        .tab-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(196, 30, 58, 0.4);
        }

        .tab-btn.active {
            background: linear-gradient(135deg, #212, 175, 55, #2);
            transform: translateY(0);
        }

        .feature {
            background: #F5F5DC;
            border: 2px solid #D4AF37;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 10px;
        }

        .feature h2 {
            color: #C41E3A;
            margin-bottom: 15px;
            font-size: 20px;
        }

        .feature ul {
            list-style: none;
            padding-left: 0;
        }

        .feature li {
            padding: 10px 0;
            color: #2C3E50;
            margin-bottom: 8px;
        }

        .feature li:before {
            content: "✅ ";
            color: #4CAF50;
            margin-right: 10px;
            font-weight: bold;
        }

        .feature li span {
            color: #7F8C8D;
        font-size: 14px;
        }

        .coming-soon {
            color: #FF9800;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏯 象棋AI混合代理 - 产品级v0.6.0</h1>

        <div class="tabs">
            <button class="tab-btn active">人机对战</button>
            <button class="tab-btn">下棋谱</button>
            <button class="tab-btn">复盘</button>
        </div>

        <div class="feature">
            <div class="status">
                <strong>✅ 已完成</strong>：产品级UI设计系统
                <ul>
                    <li><span>中国风配色方案（朱红/墨黑/鎏金/翠绿/宣纸白）</span></li>
                    <li><span>3D立体棋子效果（径向渐变+多层阴影）</span></li>
                    <li><span>贝塞尔曲线动画系统（60fps流畅度）</span></li>
                    <li><span>完整音效系统（8种棋子+特殊音效）</span></li>
                </ul>
            </div>

            <div class="feature">
                <h2>✅ 已完成</h2>
                <ul>
                    <li><span>完整规则引擎（所有棋子走法+将军检测）</span></li>
                    <li><span>游戏控制器（走棋交互+状态管理）</span></li>
                    <li><span>棋盘HTML渲染器（楚河汉界+九宫格）</span></li>
                </ul>
            </div>

            <div class="feature">
                <h2>⏳️ 开发中</h2>
                <ul>
                    <li>棋盘交互逻辑（点击选中→走棋）</li>
                    <li>分析面板集成</li>
                    <li>PGN文件解析</li>
                    <li>复盘分析功能</li>
                </ul>
            </div>

            <div class="info">
                <strong>📝 访问地址</strong>
                <ul>
                    <li>当前Gradio应用：<code>http://localhost:7867</code>（商业级测试版）</li>
                    <li>直接HTML：<code>http://localhost:8888</code>（产品级展示版）</li>
                </ul>
            </div>

        <div class="info">
                <strong>🚀 下载测试HTML</strong>
                <p>如需在浏览器中直接打开HTML文件查看效果，可以打开：</p>
                <code>web/test_product.html</code>
            </div>
    </div>
</body>
</html>
        """

        # 发送HTML响应
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))


def main():
    """主函数"""
    # 切换到web目录
    os.chdir(DIRECTORY)

    # 创建HTTP服务器
    server = http.server.HTTPServer(("0.0.0.0", PORT), SimpleHTTPRequestHandler)

    print("""
    ========================================
    象棋AI混合代理 - 产品级测试服务器
    ========================================

    服务器地址：http://localhost:{PORT}

    按Ctrl+C 停止服务器
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
