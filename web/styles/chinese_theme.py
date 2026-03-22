"""
中国风主题样式系统 - 天天象棋级别

目标：专业级中国象棋UI设计，媲美天天象棋等顶级平台
"""

# CSS变量定义
CHINESE_THEME = {
    # 主色调
    'primary_red': '#C41E3A',      # 朱红 - 红方主色
    'primary_black': '#1A1A1A',     # 墨黑 - 黑方主色
    'gold': '#D4AF37',              # 鎏金 - 装饰色
    'jade': '#00A86B',               # 翠绿 - 状态色
    'paper': '#F5F5DC',             # 宣纸白 - 背景色

    # 辅助色
    'red_light': '#E85A6C',
    'black_light': '#333333',
    'gold_light': '#F4D03F',
    'jade_light': '#00B894',

    # 棋子色
    'piece_red': '#E63946',
    'piece_black': '#2C3E50',
    'piece_text_red': '#FFFFFF',
    'piece_text_black': '#FFFFFF',

    # 边框色
    'border': '#B8860B',             # 木纹框
    'shadow': 'rgba(0, 0, 0, 0.2)',  # 柔和阴影

    # 文本色
    'text_primary': '#2C3E50',
    'text_secondary': '#7F8C8D',
    'text_highlight': '#C0392B',
}

# 自定义CSS
CHINESE_THEME_CSS = f"""
/* ========================================
   天天象棋级别 - 中国风主题样式
   ======================================== */

/* 1. 全局变量 */
:root {{
    --color-primary-red: {CHINESE_THEME['primary_red']};
    --color-primary-black: {CHINESE_THEME['primary_black']};
    --color-gold: {CHINESE_THEME['gold']};
    --color-jade: {CHINESE_THEME['jade']};
    --color-paper: {CHINESE_THEME['paper']};

    --color-red-light: {CHINESE_THEME['red_light']};
    --color-black-light: {CHINESE_THEME['black_light']};
    --color-gold-light: {CHINESE_THEME['gold_light']};
    --color-jade-light: {CHINESE_THEME['jade_light']};

    --color-piece-red: {CHINESE_THEME['piece_red']};
    --color-piece-black: {CHINESE_THEME['piece_black']};
    --color-piece-text-red: {CHINESE_THEME['piece_text_red']};
    --color-piece-text-black: {CHINESE_THEME['piece_text_black']};

    --color-border: {CHINESE_THEME['border']};
    --color-shadow: {CHINESE_THEME['shadow']};

    --color-text-primary: {CHINESE_THEME['text_primary']};
    --color-text-secondary: {CHINESE_THEME['text_secondary']};
    --color-text-highlight: {CHINESE_THEME['text_highlight']};

    --font-family: "楷体", "STKaiti", "KaiTi", "STSong", serif;
    --transition-speed: 0.3s;
    --animation-duration: 0.5s;
}}

/* 2. 棋盘容器 - 宣纸纹理背景 */
.chess-container {{
    position: relative;
    background:
        radial-gradient(circle at 30% 20%, var(--color-paper) 0%, #E8E4D9 100%);
    border: 4px solid var(--color-gold);
    border-radius: 8px;
    box-shadow:
        0 8px 32px var(--color-shadow),
        inset 0 1px 0 rgba(212, 175, 55, 0.1);
    overflow: hidden;
}}

/* 3. 棋盘 - 专业网格线 */
.chess-board {{
    position: relative;
    background: linear-gradient(135deg, var(--color-paper) 0%, #F0E8D0 100%);

    /* 楚河汉界 */
    .river {{
        position: absolute;
        top: 45%;  /* 第5-6行 */
        left: 0;
        right: 0;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-family);
        font-size: 24px;
        font-weight: bold;
        color: var(--color-text-primary);
        background: linear-gradient(90deg,
            transparent 0%,
            var(--color-gold) 50%,
            transparent 100%);
        border-top: 2px solid var(--color-border);
        border-bottom: 2px solid var(--color-border);
        letter-spacing: 1rem;
    }}

    .river::before {{
        content: '楚河';
    }}

    .river::after {{
        content: '汉界';
    }}

    /* 九宫格 - 虚线 */
    .palace {{
        position: absolute;
        width: 16.66%;
        height: 33.33%;
        border: 2px dashed var(--color-gold);
        opacity: 0.3;
        pointer-events: none;
    }}

    /* 顶部九宫 */
    .palace-top {{
        top: 0;
        left: 33.33%;
    }}

    /* 底部九宫 */
    .palace-bottom {{
        bottom: 0;
        left: 33.33%;
    }}
}}

/* 4. 棋子 - 3D立体效果 */
.chess-piece {{
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-family);
    font-weight: bold;
    font-size: 28px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    /* 3D立体基底 */
    background: radial-gradient(
        circle at 30% 30%,
        #FFFFFF 0%,
        #F5F5DC 50%,
        #E8E4D0 100%
    );

    /* 阴影 - 制造立体感 */
    box-shadow:
        0 6px 12px rgba(0, 0, 0, 0.3),
        0 3px 6px rgba(0, 0, 0, 0.2),
        inset 0 2px 4px rgba(255, 255, 255, 0.3),
        inset 0 1px 2px rgba(0, 0, 0, 0.1);

    /* 边框 */
    border: 3px solid;
}}

/* 红方棋子 */
.chess-piece.red {{
    color: var(--color-piece-text-red);
    border-color: var(--color-piece-red);
    text-shadow:
        1px 1px 2px rgba(0, 0, 0, 0.3);
}}

/* 黑方棋子 */
.chess-piece.black {{
    color: var(--color-piece-text-black);
    border-color: var(--color-piece-black);
    text-shadow:
        1px 1px 2px rgba(0, 0, 0, 0.3);
}}

/* 悬停效果 - 浮起 */
.chess-piece:hover {{
    transform: translateY(-8px) scale(1.1);
    box-shadow:
        0 12px 20px rgba(0, 0, 0, 0.4),
        0 6px 10px rgba(212, 175, 55, 0.3),
        inset 0 3px 6px rgba(255, 255, 255, 0.4);
}}

/* 选中状态 */
.chess-piece.selected {{
    transform: scale(1.15);
    box-shadow:
        0 0 20px var(--color-gold),
        0 0 40px rgba(212, 175, 55, 0.3),
        inset 0 4px 8px rgba(212, 175, 55, 0.4);
    animation: pulse-gold 1.5s infinite;
}}

@keyframes pulse-gold {{
    0%, 100% {{
        box-shadow:
            0 0 20px var(--color-gold),
            0 0 40px rgba(212, 175, 55, 0.3),
            inset 0 4px 8px rgba(212, 175, 55, 0.4);
    }}
    50% {{
        box-shadow:
            0 0 30px var(--color-gold),
            0 0 60px rgba(212, 175, 55, 0.5),
            inset 0 6px 12px rgba(212, 175, 55, 0.6);
    }}
}}

/* 可走位置提示 */
.valid-move {{
    position: absolute;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: radial-gradient(
        circle,
        var(--color-jade) 0%,
        transparent 70%
    );
    animation: pulse-jade 1.5s infinite;
}}

@keyframes pulse-jade {{
    0%, 100% {{ opacity: 0.3; }}
    50% {{ opacity: 0.7; }}
}}

/* 最后走法标记 */
.last-move {{
    position: absolute;
    width: 100%;
    height: 100%;
    background: rgba(0, 174, 107, 0.1);
    animation: flash-last-move 0.5s ease-out;
    pointer-events: none;
    z-index: 1;
}}

@keyframes flash-last-move {{
    0% {{ background: rgba(0, 174, 107, 0.3); }}
    100% {{ background: rgba(0, 174, 107, 0.1); }}
}}

/* 将军警报 */
.check-alert {{
    animation: check-alert 1s infinite;
}}

@keyframes check-alert {{
    0%, 100% {{
        border: 4px solid var(--color-piece-red);
    }}
    50% {{
        border: 4px solid var(--color-piece-red);
        box-shadow:
            0 0 10px rgba(230, 57, 70, 0.5);
    }}
}}

/* 5. 按钮样式 - 中国风按钮 */
.chinese-button {{
    background: linear-gradient(135deg, var(--color-primary-red) 0%, #D32F2F 100%);
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-family: var(--font-family);
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
    box-shadow:
        0 4px 12px rgba(196, 30, 58, 0.3);
}}

.chinese-button:hover {{
    transform: translateY(-2px);
    box-shadow:
        0 6px 16px rgba(196, 30, 58, 0.4);
}}

.chinese-button:active {{
    transform: translateY(0);
    box-shadow:
        0 2px 8px rgba(196, 30, 58, 0.2);
}}

/* 次要按钮 */
.chinese-button.secondary {{
    background: linear-gradient(135deg, var(--color-jade) 0%, #009973 100%);
}}

/* 危险按钮 */
.chinese-button.danger {{
    background: linear-gradient(135deg, var(--color-piece-red) 0%, #B91C1C 100%);
}}

/* 6. 分析面板样式 */
.analysis-panel {{
    background: linear-gradient(180deg, var(--color-paper) 0%, #F0E8D0 100%);
    border: 2px solid var(--color-border);
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 4px 12px var(--color-shadow);
}}

/* 评估条 */
.eval-bar {{
    width: 100%;
    height: 30px;
    background: var(--color-paper);
    border-radius: 15px;
    overflow: hidden;
    position: relative;
}}

.eval-bar-fill {{
    height: 100%;
    transition: width 0.5s ease-out;
    position: relative;
}}

.eval-bar-fill::after {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg,
        var(--color-jade) 0%,
        var(--color-primary-red) 50%,
        var(--color-jade) 100%);
    animation: shimmer 2s infinite;
}}

@keyframes shimmer {{
    0% {{ background-position: -200% 0; }}
    100% {{ background-position: 200% 0; }}
}}

/* 7. 导航组件样式 */
.nav-buttons {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}}

.nav-button {{
    background: linear-gradient(135deg, var(--color-gold) 0%, #B8860B 100%);
    color: var(--color-text-primary);
    border: 2px solid var(--color-border);
    border-radius: 6px;
    padding: 10px 20px;
    font-family: var(--font-family);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s;
    min-width: 100px;
}}

.nav-button:hover {{
    background: linear-gradient(135deg, var(--color-gold-light) 0%, #D4AF37 100%);
    transform: translateY(-2px);
}}

/* 8. 着法列表样式 */
.move-list {{
    max-height: 300px;
    overflow-y: auto;
    background: linear-gradient(180deg, var(--color-paper) 0%, #F0E8D0 100%);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 10px;
}}

.move-item {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    border-bottom: 1px solid var(--color-border);
    cursor: pointer;
    transition: all 0.2s;
}}

.move-item:hover {{
    background: rgba(212, 175, 55, 0.1);
}}

.move-item.current {{
    background: var(--color-gold-light);
    font-weight: bold;
}}

.move-number {{
    width: 50px;
    color: var(--color-text-secondary);
    font-size: 14px;
}}

.move-content {{
    flex: 1;
    color: var(--color-text-primary);
    font-size: 16px;
}}

/* 9. 响应式设计 */

/* 平板 - 768px-1024px */
@media (max-width: 1024px) {{
    .chess-piece {{
        width: 40px;
        height: 40px;
        font-size: 22px;
    }}

    .nav-button {{
        padding: 8px 16px;
        font-size: 12px;
        min-width: 80px;
    }}
}}

/* 手机 - <768px */
@media (max-width: 768px) {{
    .chess-piece {{
        width: 35px;
        height: 35px;
        font-size: 18px;
    }}

    .river {{
        font-size: 18px;
        letter-spacing: 0.5rem;
    }}

    .chinese-button {{
        padding: 8px 16px;
        font-size: 14px;
    }}

    .nav-button {{
        padding: 6px 12px;
        font-size: 11px;
        min-width: 60px;
    }}
}}

/* 10. 动画系统 */

/* 棋子移动动画 */
.move-animation {{
    animation: slide-move 0.3s ease-out;
}}

@keyframes slide-move {{
    0% {{
        transform: translateY(0) scale(1);
    }}
    50% {{
        transform: translateY(20px) scale(1.1);
        opacity: 0.8;
    }}
    100% {{
        transform: translateY(40px) scale(1);
    }}
}}

/* 吃子动画 */
.capture-animation {{
    animation: shrink-capture 0.2s ease-out forwards;
}}

@keyframes shrink-capture {{
    0% {{
        transform: scale(1);
        opacity: 1;
    }}
    100% {{
        transform: scale(0);
        opacity: 0;
    }}
}}

/* 将军动画 */
.checkmate-animation {{
    animation: king-checkmate 0.5s ease-out;
}}

@keyframes king-checkmate {{
    0%, 100% {{
        transform: scale(1);
    }}
    50% {{
        transform: scale(1.2) rotate(10deg);
    }}
}}

/* 11. 加载动画 */
.loading-spinner {{
    width: 40px;
    height: 40px;
    border: 4px solid var(--color-gold);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}}

@keyframes spin {{
    0% {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
}}

/* 12. Toast通知 */
.toast-notification {{
    position: fixed;
    top: 20px;
    right: 20px;
    background: var(--color-primary-black);
    color: var(--color-piece-text-black);
    padding: 15px 25px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    animation: slide-in 0.3s ease-out;
    z-index: 1000;
}}

@keyframes slide-in {{
    0% {{
        transform: translateX(400px);
        opacity: 0;
    }}
    100% {{
        transform: translateX(0);
        opacity: 1;
    }}
}}

.toast-notification.success {{
    background: var(--color-jade);
    color: #FFFFFF;
}}

.toast-notification.error {{
    background: var(--color-piece-red);
    color: #FFFFFF;
}}

.toast-notification.warning {{
    background: var(--color-gold);
    color: var(--color-text-primary);
}}
"""
