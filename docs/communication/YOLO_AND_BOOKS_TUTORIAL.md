# 两件事的完整教程
## 一、柳大华三件套的正确用法 ｜ 二、YOLO 棋子识别从零到上线

**写给**：项目负责人（你）  
**性质**：你可以亲自动手的部分，不依赖 GLM5  
**时间估计**：棋书处理半天，YOLO 数据采集两天，训练一晚上

---

# 第一部分：柳大华三件套的正确用法

## 为什么不做 RAG

你的判断完全正确。这三本书的内容是：**棋谱符号 + 棋局图片 + 少量文字**。

向量化之后检索回来的是「炮二平五、马8进7」这类符号，LLM 拿到之后不知道怎么用，因为它需要的是「这类局面的棋理判断」，而不是走法列表。

正确的方式是：**把棋谱转成结构化数据，存进 Neo4j，按张力类型组织。**

---

## 目标数据结构

每道棋题，在 Neo4j 里长这样：

```
(:ChessProblem {
    id: "liu_attack_047",
    source: "柳大华攻杀入门",
    chapter: "第三章 马后炮",
    
    fen: "3k5/4C4/4N4/9/9/9/9/9/9/4K4 b - - 0 1",
    
    tension_type: "material_vs_initiative",   ← 对应你的张力检测器
    kill_pattern: "马后炮",                    ← 对应你的标准杀法标签
    
    solution_moves: ["..."],                  ← 正确解法的走法序列
    key_principle: "马控将位，炮将军，将无路可逃",  ← 这道题的棋理要点
    difficulty: "beginner"
})
```

Agent 检测到 `is_cannon_double_attack` + `is_discovered_check` 张力时，查 Neo4j：
「有没有类似的经典案例？」→ 返回柳大华书里的对应题目 + 棋理要点。

Agent 说出来的话就变成：「这个形态在柳大华的攻杀入门里有经典例题，核心是……」

这就是知识库有名家背书的效果。

---

## 具体操作步骤

### 第一步：整理棋谱（两小时）

翻开三本书，把每道题的信息记录到一个 Excel 表格里：

| 字段 | 说明 | 示例 |
|------|------|------|
| id | 自己编的唯一ID | `liu_attack_047` |
| source | 书名简称 | `攻杀入门` / `防守入门` / `残局入门` |
| chapter | 章节 | `第三章 马后炮` |
| kill_pattern | 杀法名称（如果有） | `马后炮` / `铁门栓` / `双车错` |
| key_principle | 你读这道题的感受，一两句话 | `马控将位后炮将军必死` |
| difficulty | 难度 | `beginner` |
| notes | 其他备注 | 可以空着 |

**暂时不填 FEN**，那个后面用工具生成。

目标：先把 50-100 道题的基本信息整理出来。不需要全部三本书，每本书选最有代表性的章节。

---

### 第二步：棋谱转 FEN（关键步骤）

这是最花时间的地方。有两种方法：

**方法 A：用现成工具录入（推荐）**

下载象棋软件「象棋巫师」或「中国象棋软件」（都是免费的），按照书里的棋谱走法一步步录入，走到题目的初始局面，然后导出 FEN。

操作：文件 → 导出 → 复制 FEN 字符串 → 粘贴到 Excel 表格。

每道题大概 3-5 分钟，50 道题三四个小时搞定。

**方法 B：让 GLM5 批量生成（有风险，需要验证）**

把棋谱符号描述给 GLM5，让它生成 FEN。**但必须用你的规则引擎验证每个 FEN 是否合法**，不能直接用，因为 GLM5 在棋盘坐标上很容易出错。

---

### 第三步：标注张力类型（一小时）

回到 Excel，为每道题加一列 `tension_type`，从你的九种张力类型里选一个最匹配的：

```
material_vs_initiative   → 多数进攻题
king_safety_critical     → 王攻、闪将题
sleeping_piece           → 子力调动题
speed_race               → 速度争夺题
```

这一步不需要精确，大概对就行。

---

### 第四步：批量导入 Neo4j（GLM5 做这个）

把整理好的 Excel 给 GLM5，让他写导入脚本：

```python
# GLM5 需要写的脚本
import pandas as pd
from neo4j import GraphDatabase

df = pd.read_excel("liudahua_problems.xlsx")

with driver.session() as session:
    for _, row in df.iterrows():
        session.run("""
            CREATE (:ChessProblem {
                id: $id,
                source: $source,
                fen: $fen,
                tension_type: $tension_type,
                kill_pattern: $kill_pattern,
                key_principle: $key_principle
            })
        """, **row.to_dict())
```

---

### 第五步：接入 Agent（GLM5 做这个）

在知识库查询接口里加一条查询路径：

```python
def query_for_tension(tension_type: str) -> List[dict]:
    # 原有的棋理原则
    principles = PRINCIPLES.get(tension_type, [])
    
    # 新增：从 Neo4j 查经典案例
    neo4j_examples = neo4j_client.query("""
        MATCH (p:ChessProblem {tension_type: $tension_type})
        RETURN p.key_principle, p.kill_pattern, p.source
        LIMIT 2
    """, tension_type=tension_type)
    
    # 合并返回
    return {
        "principles": principles,
        "examples": neo4j_examples  # Agent 可以引用：「柳大华书中的经典案例显示……」
    }
```

---

# 第二部分：YOLO 棋子识别从零到上线

## 先找现成权重

在自己拍照之前，先看看有没有可以直接用或微调的现成权重，能省大量时间。

### 现成资源评估

**GitHub 上有一个基于 YOLOv5 的中国象棋识别工具**（189 stars，2024年更新），搜索关键词：

```
GitHub 搜索：xiangqi yolov5
```

找到后下载，先用它的权重对你自己的棋盘拍一张照片测试一下，看识别效果。

**Roboflow Universe** 上也有西洋棋的检测数据集，但类别标签是西洋棋棋子（king/queen/rook...），和中国象棋的 14 个类别不匹配，需要重新标注。不建议用这个。

**我的判断**：现成的中国象棋 YOLO 权重质量参差不齐，大概率需要你自己拍照补充数据微调。但「站在现成权重的肩膀上微调」比「从头训练」快 10 倍。建议先找一个凑合能用的权重，再微调。

---

## 你的 14 个类别

中国象棋 YOLO 模型需要识别 **14 个类别 + 1 个棋盘**：

```python
CLASSES = [
    # 红方（7个）
    "red_king",    # 帅
    "red_guard",   # 仕
    "red_bishop",  # 相
    "red_knight",  # 马
    "red_rook",    # 车
    "red_cannon",  # 炮
    "red_pawn",    # 兵
    
    # 黑方（7个）
    "black_king",   # 将
    "black_guard",  # 士
    "black_bishop", # 象
    "black_knight", # 马
    "black_rook",   # 车
    "black_cannon", # 炮
    "black_pawn",   # 卒
    
    # 棋盘本体（用于定位和透视变换）
    "board"
]
```

---

## 拍照指南

### 拍多少张

**最低可用**：每类棋子 30 张，共 14×30 = 420 张图片  
**推荐数量**：每类棋子 50 张，共约 700 张  
**时间估计**：两个下午

不需要每张图片只有一个棋子——一张棋盘照片里有 32 个棋子，一张图可以贡献 32 个标注。实际上你只需要拍 **50-80 张整棋盘照片**，就能覆盖足够的样本数量。

---

### 怎么拍（关键）

YOLO 的识别效果取决于训练数据的多样性。你需要故意制造以下变化：

**角度变化（最重要）**

```
俯视 90°（正上方）      ← 必须有，最标准
斜视 60°               ← 必须有，最常见拍法
斜视 45°               ← 必须有
侧面约 30°             ← 要有几张
```

**光线变化**

```
自然光（白天窗边）
室内白炽灯
室内冷光灯
有阴影的情况
```

**棋子材质变化（如果有的话）**

```
木质棋子
塑料棋子
磁性棋子
```

**背景变化**

```
标准棋盘布
不同颜色的桌面
棋盘周围有杂物
```

**棋局状态**

```
开局（棋子集中）
中局（棋子分散，有吃子后的稀疏局面）
残局（棋子很少）
```

### 拍照操作要点

```
1. 棋盘要铺平，四个角都在画面里
2. 对焦清晰，棋子上的字要能看清楚
3. 照片分辨率不低于 1080p
4. 每换一种条件，拍 5-10 张
5. 手机竖拍横拍都要有
```

---

## 标注指南

### 工具选择：用 Roboflow（强烈推荐）

不要用本地标注工具。Roboflow 是网页版，免费账号够用，有两个关键功能：

**自动标注辅助**：上传图片后，Roboflow 会用它的模型给出初始标注框，你只需要检查和修正，不需要从零画框。

**自动数据增强**：导出时可以自动生成翻转、旋转、亮度变化的增强数据，相当于把 700 张图变成 2000 张。

### Roboflow 操作步骤

**第一步：注册账号**
访问 `roboflow.com`，免费注册，选 Public 项目。

**第二步：创建项目**
```
Project Type: Object Detection
Project Name: xiangqi-piece-detection
```

**第三步：上传图片**
把拍的照片全部上传，一次性传完。

**第四步：配置类别**
在 Classes 里输入上面 14 个类别名称。

**第五步：开始标注**

Roboflow 的标注界面：
- 快捷键 `B`：画矩形框
- 按住拖动：框住棋子
- 松开后选择类别
- 下一张：`→`

**关键技巧：用 Auto-Label 加速**

在 Roboflow 里找到 `Auto-Label` 功能，上传前几十张手动标注好的图片后，后续图片 Roboflow 会自动给出框，你只需要：
- 确认框的位置对不对
- 确认类别对不对
- 修正错误的地方

这能让标注速度提升 3-5 倍。

**第六步：数据增强配置**

标注完成后，点 `Generate`，配置增强：

```
Preprocessing:
  - Resize: 640×640（YOLO 标准输入尺寸）

Augmentation（勾选以下）:
  - Flip: Horizontal（水平翻转）
  - Rotation: -15° to +15°（轻微旋转）
  - Brightness: -25% to +25%（亮度变化）
  - Blur: 0 to 1px（轻微模糊，模拟手抖）
```

**第七步：导出数据集**

```
Format: YOLOv8
Split: 70% train / 20% val / 10% test
```

下载 zip 文件，解压后得到这个结构：
```
dataset/
├── train/
│   ├── images/   ← 训练图片
│   └── labels/   ← 对应的标注文件（.txt）
├── val/
│   ├── images/
│   └── labels/
├── test/
│   ├── images/
│   └── labels/
└── data.yaml     ← 数据集配置文件
```

---

## 训练教程（菜鸟版）

### 环境准备

**用 Google Colab（最省事，免费 GPU）**

访问 `colab.research.google.com`，新建笔记本，把运行环境改成 GPU：
```
菜单 → 修改 → 笔记本设置 → 硬件加速器 → GPU → 保存
```

### 完整训练代码

把下面的代码复制进 Colab，一格一格运行：

**第一格：安装依赖**
```python
!pip install ultralytics
!pip install roboflow
```

**第二格：挂载 Google Drive（用来保存模型）**
```python
from google.colab import drive
drive.mount('/content/drive')
```

**第三格：上传数据集**

把从 Roboflow 下载的 zip 文件上传到 Colab，然后解压：

```python
import zipfile
with zipfile.ZipFile('your_dataset.zip', 'r') as z:
    z.extractall('/content/dataset')
```

或者直接用 Roboflow API 下载（更方便）：

```python
from roboflow import Roboflow

rf = Roboflow(api_key="你的API_KEY")  # 在 Roboflow 账号设置里找
project = rf.workspace("你的workspace").project("xiangqi-piece-detection")
dataset = project.version(1).download("yolov8")
```

**第四格：开始训练**

```python
from ultralytics import YOLO

# 加载预训练模型（如果有现成象棋权重就换成那个路径）
model = YOLO('yolov8n.pt')  # n=nano，最小最快，适合手机端

# 开始训练
results = model.train(
    data='/content/dataset/data.yaml',  # 数据集配置
    epochs=100,          # 训练轮数，100轮约需1-2小时
    imgsz=640,           # 输入图片尺寸
    batch=16,            # 批次大小，如果报内存错误就改成8
    patience=20,         # 20轮没有提升就提前停止
    save=True,
    project='/content/drive/MyDrive/xiangqi_yolo',  # 保存到 Google Drive
    name='run1'
)
```

**第五格：查看训练结果**

```python
# 查看训练指标
import matplotlib.pyplot as plt
from PIL import Image

# 显示训练曲线
img = Image.open('/content/drive/MyDrive/xiangqi_yolo/run1/results.png')
plt.imshow(img)
plt.axis('off')
plt.show()
```

**第六格：测试模型**

```python
# 用一张新图片测试
model = YOLO('/content/drive/MyDrive/xiangqi_yolo/run1/weights/best.pt')

results = model('/content/test_image.jpg', conf=0.5)  # conf=置信度阈值
results[0].save('/content/result.jpg')  # 保存带标注框的结果图

# 显示结果
from IPython.display import Image as IpyImage
IpyImage('/content/result.jpg')
```

---

## 如何判断训练结果够不够好

训练完看这两个指标：

```
mAP50 > 0.85   ← 可以用了
mAP50 > 0.92   ← 很好
mAP50 > 0.95   ← 非常好，基本不需要手动校正
```

mAP50 在训练日志里和 results.png 里都能看到。

**如果结果不好（mAP50 < 0.80）**，通常是这几个原因：

```
原因1：数据太少 → 再拍50张，重点补充识别错误的棋子类型
原因2：标注质量差 → 回 Roboflow 检查标注，框要框紧棋子，不要太松
原因3：某类棋子样本极少 → 检查每类棋子的数量，数量少的重点补充
原因4：epochs 不够 → 改成 200 再训练一次
```

---

## 训练完成后的模型集成

训练完的模型是一个 `best.pt` 文件，约 6MB（nano 版本）。

给 GLM5 的接入接口设计：

```python
# core/vision/board_detector.py

from ultralytics import YOLO
import numpy as np

class XiangqiBoardDetector:
    
    def __init__(self, model_path: str):
        self.model = YOLO(model_path)
        
        # 类别到棋子名称的映射
        self.class_to_piece = {
            0: "红帅", 1: "红仕", 2: "红相", 3: "红马",
            4: "红车", 5: "红炮", 6: "红兵",
            7: "黑将", 8: "黑士", 9: "黑象", 10: "黑马",
            11: "黑车", 12: "黑炮", 13: "黑卒",
        }
    
    def detect(self, image_path: str) -> dict:
        results = self.model(image_path, conf=0.5)[0]
        
        pieces = []
        for box in results.boxes:
            pieces.append({
                "piece": self.class_to_piece[int(box.cls)],
                "confidence": float(box.conf),
                "bbox": box.xyxy[0].tolist(),
                # 网格位置需要后处理：把像素坐标映射到棋盘格子
                "grid_position": self._pixel_to_grid(box.xyxy[0])
            })
        
        # 按置信度排序，低置信度的标记为需要确认
        low_conf = [p for p in pieces if p["confidence"] < 0.80]
        
        return {
            "success": len(pieces) > 0,
            "pieces": pieces,
            "low_confidence_pieces": low_conf,
            "fen": self._pieces_to_fen(pieces),
        }
    
    def _pixel_to_grid(self, bbox):
        """把像素坐标转换成棋盘格子坐标（需要先检测棋盘四个角）"""
        # 这部分需要配合棋盘边界检测来实现
        pass
    
    def _pieces_to_fen(self, pieces) -> str:
        """把检测到的棋子列表转换成 FEN 字符串"""
        pass
```

`_pixel_to_grid` 和 `_pieces_to_fen` 这两个方法是最复杂的部分，让 GLM5 来实现——思路是先用四个棋盘角点做透视变换，把斜拍的棋盘矫正成正视图，然后按格子划分区域。

---

## 时间规划

```
今天下午：
  ├── 整理柳大华三件套，填 Excel（2小时）
  └── 在网上找现成象棋 YOLO 权重，测试一下效果

明天：
  ├── 上午：拍棋盘照片（各种角度、光线）目标 60 张
  └── 下午：Roboflow 上传、标注（每张约 15 分钟，共 15 小时）
            → 用 Auto-Label 可以压缩到 5-8 小时

后天：
  ├── 在 Google Colab 跑训练（设置好参数，等 1-2 小时）
  └── 看结果，如果 mAP50 > 0.85，给 GLM5 集成进去
  
    如果 mAP50 < 0.80：
  └── 再补充 30 张针对性图片，重新训练
```

---

## 一句话总结

棋书：用象棋巫师把棋谱转成 FEN，填进 Excel，给 GLM5 批量导入 Neo4j，用张力类型组织。

YOLO：先找 GitHub 上的现成权重测试，大概率需要微调。用 Roboflow 标注（有 Auto-Label 辅助），Google Colab 免费 GPU 跑训练，目标 mAP50 > 0.85。

两件事都可以你自己操作，不需要等 GLM5。

---

*本文档由 Claude Sonnet 撰写，授权给本项目无限制使用。*
