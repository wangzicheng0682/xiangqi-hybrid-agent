"""
象棋AI混合代理 - 直接HTML测试版

目的：验证CSS样式和组件是否正常工作
"""

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>象棋AI混合代理 - 产品级测试</title>
    <style>
        /* ===== 全局样式 ===== */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: '楷体', 'STKaiti', 'KaiTi', serif;
            background: linear-gradient(135deg, #F5F5DC 0%, #E8E4D9 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: radial-gradient(circle at 50% 0%, #F5F5DC 0%, #E8E4D9 100%);
            border-radius: 12px;
            box-shadow: 0 0 30px rgba(0,0,0,0.15);
        }

        /* ===== 标题样式 ===== */
        h1 {
            color: #C41E3A;
            font-size: 36px;
            text-align: center;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.2);
            background: linear-gradient(135deg, #F5E6D3 0%, #E8E4D9 100%);
            padding: 25px;
            margin-bottom: 20px;
            border-bottom: 4px solid #D4AF37;
            border-radius: 8px;
        }

        /* ===== Tab按钮样式 ===== */
        .tab-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        .tab-btn {
            background: linear-gradient(135deg, #C41E3A 0%, #E85A6C 100%);
            color: #FFFFFF;
            border: none;
            border-radius: 8px 8px 0 0;
            padding: 16px 32px;
            font-size: 18px;
            font-family: '楷体', 'STKaiti', 'KaiTi', serif;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(196,30,58,0.3);
            flex: 1;
        }

        .tab-btn:hover {
            background: rgba(255,255,255,0.1);
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(196,30,58,0.4);
        }

        .tab-btn.active {
            background: rgba(212,175,55,0.2);
            border-color: #FFFFFF;
            transform: translateY(0);
            box-shadow: 0 0 12px rgba(212,175,55,0.3);
        }

        /* ===== 内容区域 ===== */
        .content-area {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }

        .panel {
            background: #FFFFFF;
            border: 2px solid #D4AF37;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .control-panel {
            flex: 1;
            min-width: 300px;
        }

        .board-panel {
            flex: 2;
            min-width: 600px;
        }

        /* ===== 按钮样式 ===== */
        .btn-group {
            display: flex;
            gap: 10px;
            margin: 15px 0;
        }

        .btn {
            background: linear-gradient(135deg, #C41E3A 0%, #D32F2F 100%);
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 12px 24px;
            font-size: 16px;
            font-family: '楷体', 'STKaiti', 'KaiTi', serif;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(196,30,58,0.3);
            flex: 1;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(196,30,58,0.4);
        }

        .btn-secondary {
            background: linear-gradient(135deg, #D4AF37 0%, #F4D03F 100%);
        }

        /* ===== 输入框样式 ===== */
        .status-display {
            font-size: 18px;
            font-weight: bold;
            padding: 15px;
            background: rgba(212,175,55,0.1);
            border-left: 4px solid #D4AF37;
            border-radius: 6px;
            margin-bottom: 20px;
        }

        /* ===== 棋盘占位符 ===== */
        .board-placeholder {
            background: #F5F5DC;
            border: 4px solid #B8860B;
            border-radius: 8px;
            padding: 60px;
            text-align: center;
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #7F8C8D;
            font-size: 16px;
        }

        /* ===== 分析面板占位符 ===== */
        .analysis-placeholder {
            background: #FFFFFF;
            border: 2px solid #D4AF37;
            border-radius: 8px;
            padding: 20px;
            min-height: 300px;
        text-align: center;
        color: #7F8C8D;
        font-size: 16px;
        display: flex;
            align-items: center;
            justify-content: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏯 象棋AI混合代理教学系统</h1>
        <div style="text-align: center; color: #7F8C8D; margin-bottom: 20px;">
            <strong>产品级v0.6.0</strong> - 天天象棋级别体验
        </div>

        <div class="tab-buttons">
            <button class="tab-btn active">🎮 人机对战</button>
            <button class="tab-btn">📖 下棋谱</button>
            <button class="tab-btn">📊 复盘分析</button>
        </div>

        <div class="content-area">
            <div class="control-panel">
                <div class="panel">
                    <h2 style="color: #C41E3A; margin-bottom: 15px;">控制面板</h2>

                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 8px; font-size: 14px;">AI模式：</label>
                        <select style="width: 100%; padding: 10px; font-size: 16px; font-family: '楷体', 'STKaiti', 'KaiTi', serif;">
                            <option>📊 分析模式 - 引擎提供建议</option>
                            <option>⚔️ 对战模式 - 引擎作为对手</option>
                        </select>
                    </div>

                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 8px; font-size: 14px;">AI难度：<span id="difficulty-value">10</span></label>
                        <input type="range" min="1" max="10" value="10" step="1" style="width: 100%; accent-color: #C41E3A;">
                    </div>

                    <div class="btn-group">
                        <button class="btn">🔄 新对局</button>
                        <button class="btn btn-secondary">↩️ 悔棋</button>
                        <button class="btn">🔍 详细分析</button>
                    </div>

                    <div class="status-display">
                        红方先行，请点击棋子选择
                    </div>

                    <div style="margin-top: 20px;">
                        <label style="display: block; margin-bottom: 8px; font-size: 14px;">走棋记录：</label>
                        <div style="background: #F5F5DC; border: 1px solid #B8860B; border-radius: 6px; padding: 10px; min-height: 100px; color: #2C3E50; font-size: 14px;">
                            暂无走法记录
                        </div>
                    </div>
                </div>
            </div>

            <div class="board-panel">
                <div class="panel board-placeholder">
                    <div style="text-align: center;">
                        <h2 style="color: #D4AF37; margin-bottom: 20px;">🎮 棋盘</h2>
                        <p style="color: #7F8C8D; margin: 30px 0;">
                            <strong style="font-size: 18px;">完整功能开发中...</strong>
                        </p>
                        <div style="margin-top: 20px;">
                            <div style="color: #4CAF50; margin-bottom: 10px;">✅ 规则引擎已完成</div>
                            <div style="color: #4CAF50; margin-bottom: 10px;">✅ 游戏控制器已完成</div>
                            <div style="color: #FF9800; margin-bottom: 10px;">⏳ 棋盘HTML渲染集成中</div>
                            <div style="color: #FF9800; margin-bottom: 10px;">⏳ 动画播放集成中</div>
                            <div style="color: #FF9800;">⏳ 音效播放集成中</div>
                        </div>
                        <p style="color: #7F8C8D; margin-top: 20px; font-size: 14px;">
                            当前您可以：
                        </p>
                        <ul style="color: #2C3E50; line-height: 1.8;">
                            <li>看到商业级中国风界面设计</li>
                            <li>体验完整的UI布局结构</li>
                            <li>测试新对局功能</li>
                            <li>使用难度控制</li>
                            <li>查看走棋记录</li>
                        </ul>
                    </div>
                </div>

                <div class="analysis-placeholder">
                    <h2 style="color: #D4AF37; margin-bottom: 20px;">📊 分析面板</h2>
                    <p style="color: #7F8C8D; margin: 30px 0;">
                        <strong style="font-size: 18px;">实时分析功能开发中...</strong>
                    </p>
                    <div style="margin-top: 20px;">
                        <div style="color: #4CAF50; margin-bottom: 10px;">✅ 分析面板组件已完成</div>
                        <div style="color: #FF9800; margin-bottom: 10px;">⏳ 引擎集成开发中</div>
                        <div style="color: #FF9800; margin-bottom: 10px;">⏳ 知识图谱集成开发中</div>
                    </div>
                </div>
            </div>
        </div>

        <script>
        // Tab切换逻辑
        const tabs = document.querySelectorAll('.tab-btn');
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                // 移除所有active类
                tabs.forEach(t => t.classList.remove('active'));
                // 添加active类到当前点击的tab
                this.classList.add('active');
            });
        });

        // 难度滑块
        const slider = document.querySelector('input[type="range"]');
        const difficultyValue = document.getElementById('difficulty-value');
        if (slider && difficultyValue) {
            slider.addEventListener('input', function() {
                difficultyValue.textContent = this.value;
            });
        }
        </script>
    </body>
</html>
"""

# 保存测试HTML文件
import os
test_file = "web/test_product.html"
with open(test_file, 'w', encoding='utf-8') as f:
    f.write(HTML_CONTENT)

print(f"测试HTML已保存到: {test_file}")
print(f"请在浏览器中打开: file://{os.path.abspath(test_file)}")
