象棋AI混合代理

教学与对弈系统

详细产品与工程落地文档

Version 1.0

2025年3月

目  录

（提示：首次打开请右键点击目录，选择“更新域”刷新页码）

1. 产品概述与核心定位	3

1.1 项目背景与意义	3

1.2 核心价值主张	4

1.3 目标用户画像	5

2. 系统架构设计	6

2.1 混合Neuro-Symbolic架构总览	6

2.2 战术计算引擎：Pikafish	7

2.3 双轨知识存储系统	9

2.4 多模态大模型中枢	11

2.5 智能代理编排：LangGraph	13

3. 核心功能模块详细设计	15

3.1 下棋谱模式（核心教学打谱）	15

3.2 人机对战模式（实战陪练）	18

3.3 对弈辅助分析模式	20

4. 落地实现详细指南	22

4.1 Sprint 1：MVP核心底座搭建	22

4.2 Sprint 2：知识注入与Agent编排	26

4.3 Sprint 3：多模态感知与图谱构建	30

4.4 Sprint 4：高阶特征与联调	34

5. 团队AI赋能开发协议	38

5.1 开发原则与规范	38

5.2 AI辅助开发工作流	40

5.3 代码审查与测试策略	42

6. 代码实现参考	44

6.1 Pikafish UCI封装工具	44

6.2 LangGraph Agent编排	48

6.3 棋书PDF向量化脚本	52

6.4 Gradio前端界面	56

7. 迭代演进与维护	60

附录A：术语表	62

附录B：参考资源	64

1. 产品概述与核心定位

Xiangqi Hybrid LLM-Agent Analysis System（象棋AI混合代理教学与对弈系统）是一个开源的中国象棋智能分析、对弈与讲解系统。其核心目标是构建一个“战术引擎级精确 + 战略大师级讲解 + 可追溯知识 + 视觉感知能力”的综合平台，以超越纯LLM的分析能力。项目通过将符号系统的高精度计算与大语言模型的智能讲解深度融合，打造出一个既具备人类大师级战略洞察，又能进行精确战术计算的象棋AI助手。

1.1 项目背景与意义

中国象棋作为中华民族的文化瑰宝，拥有数千年的历史传承和深厚的文化底蕴。在人工智能时代，如何让AI更好地理解和讲解象棋，成为一个兼具技术挑战和文化价值的课题。传统的象棋引擎（如Pikafish）虽然计算能力强大，但缺乏人类化的讲解能力；而纯大语言模型虽然能“说人话”，却容易出现“幻觉”问题，给出错误的棋局分析。

本项目正是在这一背景下应运而生。我们提出“混合代理（Hybrid Agent）”架构，将符号系统的严谨性与深度学习的灵活性相结合：用专业象棋引擎保证战术计算的零失误，用知识图谱和向量检索提供可追溯的历史数据，用大语言模型生成人类友好的讲解，用视觉模型实现棋盘图像的理解。这种“Neuro-Symbolic”（神经-符号）混合方法，代表了AI在复杂博弈领域应用的前沿方向。

1.1.1 技术发展趋势

近年来，大语言模型（LLM）技术的突破为AI应用带来了革命性的变化。GPT系列、Claude、DeepSeek等模型展现出强大的语言理解和生成能力。然而，在垂直领域（如象棋）的应用中，纯LLM方案面临以下挑战：

“幻觉”问题：LLM可能编造不存在的棋谱或错误的战术分析

知识时效性：训练数据有截止日期，无法获取最新的开局研究

计算精度：LLM不擅长精确的数值计算，难以准确评估局面优劣

可解释性：黑盒模型难以解释为什么给出某个建议

混合代理架构正是为了解决这些问题而设计。通过将LLM与专业工具（象棋引擎、知识库、视觉模型）结合，我们既保留了LLM的语言优势，又获得了符号系统的精确性和可解释性。

1.1.2 教育应用场景

本项目的目标用户主要是象棋初学者和中级玩家。对于这部分用户，传统的象棋软件存在以下痛点：专业引擎给出的“最佳着法”往往难以理解，缺乏“为什么”的解释；棋书内容浩如烟海，难以快速找到与当前局面相关的知识；人机对战时，AI对手要么太弱缺乏挑战，要么太强让人挫败。

我们的系统致力于解决这些痛点：通过自然语言讲解让初学者理解每一步的战术意图；通过知识检索引用经典棋书，让学习有据可依；通过可调节的AI难度，提供恰到好处的挑战。系统不仅是“下棋工具”，更是“象棋教练”。

1.2 核心价值主张

核心价值：超越纯LLM的分析能力，将符号系统的高精度计算与大语言模型的智能讲解深度融合。

系统不仅能告诉你“怎么走”，还能像人类教练一样引经据典地告诉你“为什么这么走”。这一价值主张体现在以下四个维度：

1.2.1 战术引擎级精确

系统采用Pikafish作为战术计算引擎。Pikafish是当前中国象棋领域棋力最强的开源引擎之一，采用神经网络评估（NNUE技术）和强大搜索算法，能够深度分析棋局并计算出最优走法。搜索深度可达20-30层，保证零漏算的战术精确性。

与纯LLM相比，引擎的计算结果是确定性的、可验证的。当系统给出“红方胜率65%”的评估时，这个数值来自引擎的精确计算，而非LLM的猜测。这种精确性是系统可信度的基础。

1.2.2 战略大师级讲解

系统通过DeepSeek大模型生成自然语言讲解。DeepSeek在中文理解和复杂推理方面表现出色，能够胜任棋局讲解中的多步推理和知识融合任务。讲解内容不仅包括“走什么”，还包括：当前局面的战略态势分析、关键棋子的作用和位置评价、可能的后续变化预测、历史相似局面的参考。

1.2.3 知识可追溯

系统遵循“Grounded-first”（知识引用优先）原则。所有讲解内容必须引用知识图谱或棋书原文，不能纯靠LLM编造。例如，当解释某开局策略时，系统会优先检索《梅花谱》中的相关论述作为依据。用户可以看到每一条建议的“出处”，增强信任感和学习效果。

1.2.4 视觉感知能力

系统引入Qwen2.5-VL视觉模型，实现棋盘图像的理解。用户可以上传棋盘照片或截图，系统自动识别棋子位置、分析局面态势。视觉描述将作为讲解的重要输入，例如：“红方底线车马炮三子归边，形成强大攻势”。这种“看得懂棋盘”的能力，使系统能够处理更丰富的输入形式，也增强了讲解的直观性。

1.3 目标用户画像

系统主要面向以下三类用户群体：

1.3.1 象棋初学者

特征：刚接触象棋或棋龄在1年以内，掌握基本规则但缺乏系统学习。需求：理解基本战术原理、学习常见开局、避免常见错误。系统价值：通过“下棋谱模式”学习经典棋局，通过自然语言讲解理解每一步的意图。

1.3.2 中级爱好者

特征：有一定棋龄（1-5年），能独立完成对局但水平提升遇到瓶颈。需求：深入理解战略思想、学习高级战术、分析自己的对局。系统价值：通过“人机对战模式”进行针对性训练，通过“对弈分析模式”复盘学习。

1.3.3 象棋教育工作者

特征：象棋教练、学校象棋社团指导老师、象棋培训机构教师。需求：教学辅助工具、学生作业批改、教学素材准备。系统价值：作为教学演示工具，快速生成局面分析，引用经典棋书作为教学依据。

三类用户的详细画像如下表所示：

表1-1：目标用户画像

2. 系统架构设计

本系统采用混合Neuro-Symbolic架构，由四个核心基础组件构成，彻底解决AI幻觉并提升专业度。这种架构设计遵循“工具优先”和“知识引用优先”的核心原则，确保系统的输出既准确又具有可解释性。

2.1 混合Neuro-Symbolic架构总览

系统的整体架构可以用以下公式概括：

系统 = Pikafish（战术引擎）+ 知识库（图谱+向量）+ LLM（DeepSeek）+ 视觉（Qwen-VL）+ Agent编排（LangGraph）

四大核心组件的职责分工如下：

战术计算引擎（Pikafish）：基于UCI协议与神经网络评估（NNUE技术）的开源引擎，提供零漏算的战术计算，搜索深度可达20-30层

双轨知识存储库：知识图谱（GraphRAG）存储历史棋局和胜率统计，书籍向量库（Books RAG）存储经典棋书内容

多模态大模型中枢：DeepSeek负责复杂推理与对话生成，Qwen2.5-VL提供视觉感知能力

智能代理编排（LangGraph）：采用ReAct模式，通过节点与边管理“思考-调用工具-生成”的状态机工作流

这种架构的核心优势在于：每个组件专注于自己最擅长的任务，通过LangGraph进行协调，形成“1+1>2”的协同效应。引擎保证精确性，知识库提供可追溯性，LLM负责自然语言生成，视觉模型扩展输入形式，Agent编排确保流程的正确性。

2.2 战术计算引擎：Pikafish

2.2.1 Pikafish简介

Pikafish是项目战术计算的核心引擎，源自国际象棋引擎Stockfish，是当前中国象棋领域棋力最强的开源引擎之一。它采用先进的神经网络评估（NNUE技术）和强大搜索算法，能够深度分析棋局并计算出最优走法。

Pikafish遵循UCI（Universal Chess Interface）协议，这是一种通用的引擎通信协议，允许引擎与图形界面或代理程序通过标准命令交互。这意味着Pikafish本身不包含图形界面，需要通过UCI命令控制。

2.2.2 UCI协议通信机制

项目通过Python脚本以子进程方式启动Pikafish，并通过标准输入/输出与其进行UCI命令交互。核心命令包括：

# UCI协议核心命令示例
uci           # 初始化引擎，获取引擎信息
isready       # 确认引擎就绪
position fen ...  # 设置棋局（FEN格式）
go depth 20   # 发起深度为20层的搜索
bestmove ...  # 引擎返回最佳走法

在LangGraph代理中，Pikafish被封装为Tool 1，即一个可被调用的工具。当LLM需要获取战术信息时，会通过ReAct/Plan-and-Execute等策略调用此工具，将当前棋局（FEN格式）传递给引擎，并读取引擎输出的评估结果。

2.2.3 战术精确性保障

Pikafish利用神经网络评估和强大搜索，能在复杂局面下计算出零漏算的精确着法。其计算深度通常设定在20-30层，以保证对战略态势的准确判断。NNUE（Neural Network Universal Evaluation）技术使得引擎的评估函数更加准确，能够捕捉到传统手工编写评估函数难以发现的微妙局面特征。

引擎输出的关键信息包括：

最佳走法（bestmove）：引擎计算出的当前最优着法

局面评估（score）：以“pawn（兵）”为单位的数值评估，正值表示红方优势

主要变化线（pv）：引擎预测的后续若干步最佳走法序列

搜索深度（depth）：引擎实际搜索的层数

搜索节点数（nodes）：引擎评估过的局面数量

2.3 双轨知识存储系统

为了提供战略层面的洞察和可追溯的知识引用，系统引入了两类知识库：历史棋局知识图谱和经典棋书向量库。这种“双轨”设计兼顾了结构化数据查询和非结构化文本检索的需求。

2.3.1 知识图谱（GraphRAG）

基于Neo4j构建的中国象棋知识图谱，用于存储历史对局数据、开局定式和胜率统计等信息。该图谱以棋局局面为节点，走法为边，每个局面节点可关联该局面的胜率、出现次数、所属开局类型等属性。

通过图查询，代理可以检索：

相似局面：与当前局面结构相似的历史局面

胜率统计：特定局面在历史上红方/黑方的胜率

常见应对：某局面的最常见后续走法及其频率

开局定式：特定开局序列的标准走法

知识图谱的构建需要导入大量PGN对局数据（如悟空象棋数据集、精英对局数据库等），通过解析PGN提取局面和结果，构建“局面-走法-结果”三元组，从而形成丰富的开局和局面知识网络。

2.3.2 书籍向量库（Books RAG）

利用向量数据库（如FAISS/Chroma）存储经典象棋书籍内容的向量表示。这些书籍包括《橘中秘》《梅花谱》《象棋实用残局》等经典著作，以及《象棋攻防妙法》《象棋中局战法》《象棋布局原理》等现代名著。

RAG（Retrieval-Augmented Generation，检索增强生成）流程如下：

文档处理：使用LangChain的PDFLoader加载棋书PDF

文本切分：使用RecursiveCharacterTextSplitter进行文本切分

向量嵌入：切分后的文本片段通过嵌入模型转换为向量

向量存储：存入FAISS/Chroma向量数据库

相似检索：查询时，将查询文本转为向量，检索最相似的片段

当LLM需要战略解释或经典注解时，可以调用此检索器从向量库中获取相关段落的原文。这些内容将作为LLM的上下文，使其讲解能够引用大师的原文观点，提高权威性和可信度。

2.4 多模态大模型中枢

大语言模型是整个系统的“大脑”，负责统筹各工具、生成讲解和与用户交互。本项目采用DeepSeek API提供的大模型服务，同时引入Qwen2.5-VL视觉模型实现多模态感知。

2.4.1 DeepSeek模型

DeepSeek模型以其在中文理解和复杂推理方面的出色表现，能够胜任棋局讲解中的多步推理和知识融合任务。本项目主要使用以下两个模型：

deepseek-chat：通用对话模型，负责日常交互和简单讲解

deepseek-reasoner：推理增强模型，负责复杂局面分析和多步推理

DeepSeek提供了与OpenAI兼容的API接口，项目通过Python客户端调用DeepSeek API，设置系统提示和用户提示，以获取模型响应。在LangGraph框架中，DeepSeek可作为对话生成模块，根据当前状态（包括引擎结果、知识库检索结果、视觉模型输出）生成自然语言讲解。

2.4.2 Qwen2.5-VL视觉模型

Qwen2.5-VL是阿里通义千问团队推出的开源多模态模型，具备强大的图像理解和文档解析能力。它能处理图像、文本、视频等多种输入，并输出文本或定位框等形式的结果。

在本系统中，Qwen-VL被用于棋盘图像理解：

棋盘识别：识别9×10网格、楚河汉界位置

棋子检测：识别每个交叉点的棋子类型和颜色

FEN生成：将识别结果转换为标准FEN字符串

态势描述：生成对局面的视觉描述，如“三子归边”

2.5 智能代理编排：LangGraph

LangGraph是项目采用的Agent框架，用于构建和管理LLM驱动的智能代理。它是LangChain生态的一部分，提供了一个图结构来定义代理的行为流程。与传统基于链式提示的Agent不同，LangGraph允许开发者以状态机的方式设计代理。

2.5.1 ReAct架构设计

本系统初步采用ReAct（Reason + Act）风格的代理架构。ReAct是一种让LLM通过自我提示（self-prompting）进行思考-行动循环的模式。LangGraph将这一模式具象化为一个图：

节点（Nodes）：图中的节点代表代理的不同状态或功能模块。例如：

输入预处理节点：判断输入类型，图片则调用视觉模型

引擎计算节点：调用Pikafish获取最佳着法和评估

知识检索节点：查询知识图谱和棋书向量库

讲解生成节点：调用DeepSeek生成自然语言讲解

边（Edges）：边定义了节点之间的流转逻辑。边可以是简单的顺序执行，也可以是条件分支。例如：

条件边：判断是否已有引擎评估结果，决定下一步走向

循环边：支持多轮思考-行动循环

汇聚边：多个工具调用结果汇聚到讲解生成节点

2.5.2 状态管理

LangGraph使用一个全局状态对象（通常是一个字典）来存储代理在执行过程中的所有中间结果。状态中可包含以下字段：

state = {
    "input_type": "fen" or "image",  # 输入类型
    "fen": "rnbakabnr/...",           # 当前局面FEN
    "visual_desc": "红方三子归边...",  # 视觉描述
    "engine_result": {                 # 引擎结果
        "bestmove": "炮二平五",
        "score": 65,
        "pv": ["炮二平五", "马8进7", ...]
    },
    "kg_result": {                     # 知识图谱结果
        "win_rate": 0.60,
        "common_moves": [...]
    },
    "book_result": [                   # 棋书检索结果
        {"source": "梅花谱", "text": "..."}
    ],
    "explanation": "红方最佳..."      # 最终讲解
}

各节点通过读写这个状态来协同工作。例如，引擎计算节点将结果写入state["engine_result"]，讲解生成节点读取所有相关结果生成最终输出。

系统核心组件及其技术选型总结如下表：

表2-1：系统核心组件与技术选型

3. 核心功能模块详细设计

系统面向教学场景，落地为三大核心交互模式。每种模式都有明确的用户价值、执行逻辑和技术实现要点。本章将详细阐述每个功能模块的设计细节，为后续开发提供清晰的指导。

3.1 下棋谱模式（核心教学打谱）

3.1.1 功能描述

下棋谱模式是系统的核心教学功能。用户加载经典残局或历史名局的FEN序列，点击“下一步”跟随打谱。系统会在每一步提供详细的讲解，包括：当前局面的战略分析、引擎评估、历史数据统计、经典棋书引用。

该模式的主要使用场景包括：

学习经典残局：如《橘中秘》《梅花谱》中的经典杀法

研究历史名局：如胡荣华、许银川等特级大师的对局

理解开局定式：学习中炮对屏风马等常见开局

打谱练习：跟随大师的思路，培养棋感

3.1.2 执行逻辑

下棋谱模式的完整执行流程如下：

用户输入：用户通过界面加载棋谱文件（PGN格式）或直接输入FEN序列

局面提取：系统提取当前局面特征（FEN字符串）

触发工作流：点击“下一步”触发LangGraph工作流

引擎计算：调用Pikafish工具获取当前数值评估（如胜率65%）

知识检索：从向量库检索相关棋书片段

图谱查询：查询知识图谱获取历史胜率统计

讲解生成：DeepSeek执行知识引用优先原则，输出讲解

3.1.3 讲解示例

假设用户正在学习《梅花谱》中的一个经典局面，系统可能输出如下讲解：

“当前局面，红方最佳着法是炮二平五（当头炮）。此着法历史上红方胜率约60%【知识图谱】。红方底线车马炮三子归边，形成强大攻势【视觉分析】。正如《梅花谱》所言：‘当头炮势如破竹’，红方应抓住时机迅速突破【棋书引用】。黑方若应以马8进7，红方可续走车一平二，保持先手优势【引擎分析】。”

这段讲解融合了多个信息源：引擎提供的最佳着法、知识图谱的历史统计、视觉模型的态势描述、棋书的经典论述。这种多维度的讲解方式，让用户不仅知道“怎么走”，更理解“为什么”。

3.1.4 界面设计要点

下棋谱模式的界面应包含以下元素：

棋盘显示区：动态显示当前局面，支持红方/黑方视角切换

着法列表：显示当前棋谱的所有着法，当前步高亮显示

控制按钮：上一步、下一步、跳转到开头、跳转到结尾

讲解面板：显示系统生成的自然语言讲解

引擎信息：显示当前局面的评估分数、最佳着法

3.2 人机对战模式（实战陪练）

3.2.1 功能描述

人机对战模式让用户与AI（Pikafish引擎）进行对战。不同于传统象棋软件，本系统的AI对手不仅是“对手”，更是“教练”。系统会实时分析用户的走法，在关键时刻给出提示和讲解。

该模式的核心特性包括：

可调节难度：通过限制引擎搜索深度，提供从初学者到大师级别的难度

实时分析：界面侧边栏实时透出AI的“思考过程”（引擎评分波动）

错误提示：当用户走出导致胜率暴跌的“劣着”时，系统主动中断并分析错误原因

正确示范：调出知识图谱中正确的应对定式

3.2.2 执行逻辑

人机对战模式的执行流程如下：

难度选择：用户选择AI难度级别（1-10级）

引擎配置：根据难度设置Pikafish的搜索深度（1级=5层，10级=30层）

开始对局：用户执红先行，或选择执黑由AI先行

用户走子：用户在棋盘上点击走子

局面评估：系统调用Pikafish评估用户走子后的局面

劣着检测：如果胜率变化超过阈值（如下降20%），触发提示

AI回应：Pikafish根据设定难度计算并执行回应着法

3.2.3 难度级别设计

难度级别与引擎搜索深度的对应关系如下表：

表3-1：难度级别与引擎配置

3.2.4 错误提示机制

当用户走出“劣着”时，系统会弹出提示框，分析错误原因。错误检测逻辑如下：

# 劣着检测逻辑
def detect_blunder(current_score, previous_score, threshold=200):
    """
    检测是否走出劣着
    current_score: 当前局面评分（红方视角，单位：百分之一兵）
    previous_score: 走子前局面评分
    threshold: 劣着阈值（默认200 = 2个兵的价值）
    """
    score_drop = previous_score - current_score
    if score_drop > threshold:
        return True, f"此着导致局面恶化{score_drop}分"
    return False, None

系统不仅会指出错误，还会提供改进建议。例如：“这步棋导致红方丢了一个兵，建议改走车二进四，保持子力平衡。历史上类似局面，红方走车二进四的胜率是58%。”

3.3 对弈辅助分析模式

3.3.1 功能描述

对弈辅助分析模式支持两名用户在线对弈，系统作为“金牌旁观教练”提供实时或赛后分析。该模式既可以用于朋友间的对弈辅助，也可以用于比赛裁判和复盘分析。

该模式的核心功能包括：

图片识别：一方上传纸质棋盘照片，Qwen-VL提取当前局面并转为FEN

实时分析：对弈过程中，系统实时分析当前局面，提供建议

赛后复盘：对局结束后，一键生成复盘报告，标出全局“胜负手”

关键局面：自动识别并标注对局中的关键转折点

3.3.2 执行逻辑

对弈辅助分析模式的执行流程如下：

创建对局：一名用户创建对局房间，另一名用户加入

局面输入：支持手动输入FEN、上传图片或在线走子

视觉识别：如果上传图片，调用Qwen-VL识别局面

实时分析：每步结束后，系统自动分析局面变化

关键提示：当出现重大局面变化时，给出提示

生成报告：对局结束后，生成完整复盘报告

3.3.3 复盘报告内容

复盘报告应包含以下内容：

对局概览：双方信息、对局结果、总步数、对局时长

胜率曲线：展示对局过程中双方胜率的变化趋势

关键局面：标注3-5个关键转折点，说明胜负手

失误统计：统计双方的“劣着”数量和类型

改进建议：针对关键失误，给出改进建议

3.3.4 胜负手识别算法

系统通过分析胜率曲线的“突变点”来识别胜负手。算法逻辑如下：

# 胜负手识别算法
def identify_turning_points(scores, threshold=300):
    """
    识别胜率曲线的转折点（胜负手）
    scores: 每步后的局面评分列表
    threshold: 转折点阈值（默认300 = 3个兵的价值）
    """
    turning_points = []
    for i in range(1, len(scores)):
        score_change = abs(scores[i] - scores[i-1])
        if score_change > threshold:
            turning_points.append({
                "move_number": i,
                "score_change": score_change,
                "description": generate_description(i, scores)
            })
    return turning_points

三大功能模块的对比如下表：

表3-2：功能模块对比

4. 落地实现详细指南

本章提供4周敏捷冲刺的详细落地时间表，针对3-4人团队利用Trae/Cursor等AI编程助手进行开发。每个Sprint都有明确的目标、任务分解、交付物和验收标准。团队应严格按照本指南执行，同时灵活调整以应对实际情况。

4.1 Sprint 1（第1周）：MVP核心底座搭建

4.1.1 Sprint目标

实现文本FEN输入、引擎解析与基础UI显示。本周的核心任务是搭建系统的“骨架”，确保Pikafish能够被正确调用，FEN能够被正确解析，棋盘能够被正确显示。本周结束时，团队应该能够演示“输入FEN -> 引擎分析 -> 显示结果”的完整流程。

4.1.2 任务分解

任务1（后端）：Pikafish UCI封装工具

编写Python脚本封装Pikafish为LangGraph的Tool。实现以下功能：

通过subprocess启动Pikafish进程

实现UCI命令的发送和响应解析

封装为LangGraph Tool接口

处理引擎超时和异常情况

# pikafish_tool.py 核心框架
import subprocess
import time
from typing import Dict, Optional

class PikafishTool:
    def __init__(self, engine_path: str):
        self.engine_path = engine_path
        self.process = None
        self._start_engine()
    
    def _start_engine(self):
        # AI生成：启动引擎进程
        pass
    
    def analyze(self, fen: str, depth: int = 20) -> Dict:
        # AI生成：发送position和go命令，解析结果
        pass

任务2（前端）：Gradio基础Web界面

使用Gradio搭建基础Web界面，实现以下功能：

FEN输入文本框

分析按钮

结果显示区域（文本）

与后端API的对接

# app.py Gradio界面框架
import gradio as gr

def analyze_position(fen: str):
    # AI生成：调用后端分析API
    pass

with gr.Blocks() as demo:
    gr.Markdown("# 象棋AI分析系统")
    fen_input = gr.Textbox(label="FEN字符串")
    analyze_btn = gr.Button("分析")
    result_output = gr.Textbox(label="分析结果")
    
    analyze_btn.click(analyze_position, inputs=fen_input, outputs=result_output)

demo.launch()

任务3（渲染）：FEN到棋盘图像生成

使用Pillow库实现从FEN字符串到棋盘图像的动态生成：

解析FEN字符串，提取棋子位置信息

绘制9×10棋盘网格

在正确位置绘制棋子（使用图片或文字）

支持红方/黑方视角切换

# board_renderer.py 框架
from PIL import Image, ImageDraw, ImageFont

class BoardRenderer:
    def __init__(self):
        # AI生成：加载棋盘和棋子资源
        pass
    
    def render(self, fen: str, perspective="red") -> Image:
        # AI生成：解析FEN并渲染棋盘
        pass
    
    def _parse_fen(self, fen: str) -> List[List[str]]:
        # AI生成：解析FEN为二维数组
        pass

4.1.3 交付物与验收标准

本周交付物及验收标准：

表4-1：Sprint 1交付物与验收标准

4.1.4 AI辅助开发提示

本周开发可充分利用AI编程助手。建议的Prompt策略：

提供完整上下文：将本章文档作为上下文喂给AI

分步生成：先生成框架，再逐步填充细节

明确要求：指定函数签名、返回值类型、异常处理

测试驱动：要求AI同时生成单元测试代码

4.2 Sprint 2（第2周）：知识注入与Agent编排

4.2.1 Sprint目标

让AI能够查书并说人话。本周的核心任务是搭建知识库和LangGraph工作流。本周结束时，系统应该能够根据局面检索相关棋书内容，并生成引用经典论述的自然语言讲解。

4.2.2 任务分解

任务1（数据）：棋书PDF向量化

使用LangChain处理棋书PDF，构建FAISS向量库：

使用PDFLoader加载棋书PDF文件

使用RecursiveCharacterTextSplitter进行智能文本切分

使用Embedding模型（如BGE-M3）将文本转为向量

使用FAISS存储向量索引

# book_vectorizer.py 框架
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

class BookVectorizer:
    def __init__(self, embedding_model="BAAI/bge-m3"):
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
    
    def process_pdf(self, pdf_path: str, book_name: str):
        # AI生成：加载PDF、切分文本、生成向量
        pass
    
    def build_index(self, output_path: str):
        # AI生成：构建FAISS索引并保存
        pass

任务2（架构）：LangGraph状态机搭建

搭建LangGraph状态机，定义全局状态和节点：

定义全局状态字典（TypedDict）

实现各节点函数：输入预处理、引擎调用、知识检索、讲解生成

定义边和条件流转逻辑

编译和测试工作流

# agent_graph.py 框架
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    # AI生成：定义状态字段
    fen: str
    engine_result: dict
    book_result: list
    explanation: str

def create_agent_graph():
    workflow = StateGraph(AgentState)
    
    # AI生成：添加节点
    workflow.add_node("analyze_engine", analyze_engine_node)
    workflow.add_node("retrieve_books", retrieve_books_node)
    workflow.add_node("generate", generate_node)
    
    # AI生成：添加边和条件
    workflow.set_entry_point("analyze_engine")
    workflow.add_edge("analyze_engine", "retrieve_books")
    workflow.add_edge("retrieve_books", "generate")
    workflow.add_edge("generate", END)
    
    return workflow.compile()

任务3（提示词）：DeepSeek核心Prompt设计

设计DeepSeek的核心Prompt，强制执行工具优先和引用优先原则：

# prompts.py 讲解生成Prompt
EXPLANATION_PROMPT = """
你是一位象棋大师，正在为初学者讲解棋局。

【重要原则】
1. 工具优先：所有精确数据（胜率、最佳着法）必须来自引擎结果
2. 引用优先：所有战略分析必须引用棋书原文或知识图谱数据
3. 严禁编造：不得自行捏造棋理或历史数据

【输入信息】
当前局面FEN：{fen}
引擎分析结果：{engine_result}
棋书检索结果：{book_result}
知识图谱数据：{kg_result}

【输出格式】
1. 最佳着法（来自引擎）
2. 局面分析（结合引擎评估和视觉描述）
3. 战略讲解（引用棋书原文）
4. 历史参考（引用知识图谱数据）
"""

4.2.3 交付物与验收标准

表4-2：Sprint 2交付物与验收标准

4.3 Sprint 3（第3周）：多模态感知与图谱构建

4.3.1 Sprint目标

让系统“看得见”且能查阅历史大数据。本周的核心任务是接入视觉模型和构建知识图谱。本周结束时，系统应该能够处理用户上传的棋盘图片，并在Neo4j中构建可用的知识图谱。

4.3.2 任务分解

任务1（多模态）：Qwen2.5-VL视觉模型接入

接入Qwen2.5-VL API，实现棋盘图像理解：

调用Qwen-VL API处理用户上传的图片

要求模型输出结构化描述（棋子位置、局面态势）

将视觉描述转换为FEN字符串

集成到LangGraph工作流中

# vision_analyzer.py 框架
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from PIL import Image
import torch

class VisionAnalyzer:
    def __init__(self, model_path="Qwen/Qwen2.5-VL-3B-Instruct"):
        # AI生成：加载模型和处理器
        pass
    
    def analyze(self, image: Image.Image) -> dict:
        """
        分析棋盘图片
        返回：{
            "fen": "rnbakabnr/...",
            "description": "红方三子归边...",
            "pieces": [...]
        }
        """
        # AI生成：调用模型分析图片
        pass

任务2（知识图谱）：Neo4j图谱构建

解析PGN数据集，构建Neo4j知识图谱：

解析PGN格式的开源数据集（如悟空象棋数据集）

提取局面和胜率信息

写入Neo4j构建“局面-走法-结果”三元组

实现Cypher查询接口

# knowledge_graph.py 框架
from neo4j import GraphDatabase

class XiangqiKnowledgeGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def import_pgn(self, pgn_file: str):
        # AI生成：解析PGN并导入图谱
        pass
    
    def query_similar_positions(self, fen: str, limit=5) -> list:
        # AI生成：查询相似局面
        pass
    
    def get_win_rate(self, fen: str) -> dict:
        # AI生成：查询胜率统计
        pass

4.3.3 交付物与验收标准

表4-3：Sprint 3交付物与验收标准

4.4 Sprint 4（第4周）：高阶特征与联调

4.4.1 Sprint目标

开发“杀手锏”功能并优化演示体验。本周的核心任务是实现Transformer特征提取器和系统整体联调。本周结束时，系统应该具备完整的三大模式功能，并能在校赛中进行演示。

4.4.2 任务分解

任务1（特征提取）：Transformer关键特征提取器

实现基于Transformer的棋局特征提取器：

将FEN转换为90×14的one-hot张量

加入位置编码（Positional Encoding）

输入至4-6层的PyTorch TransformerEncoder

输出128-512维的特征向量

# feature_extractor.py 框架
import torch
import torch.nn as nn

class XiangqiFeatureExtractor(nn.Module):
    def __init__(self, d_model=256, nhead=8, num_layers=4):
        super().__init__()
        # AI生成：定义模型结构
        self.embedding = nn.Linear(14, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        self.transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model, nhead),
            num_layers
        )
        self.fc = nn.Linear(d_model * 90, 256)
    
    def forward(self, x):
        # AI生成：前向传播
        pass
    
    def fen_to_tensor(self, fen: str) -> torch.Tensor:
        # AI生成：FEN转one-hot张量
        pass

任务2（语义检索）：相似局面检索

将特征向量存入Neo4j，实现相似局面检索：

将提取的特征向量存入Neo4j作为节点的向量属性

实现基于余弦相似度的相似局面检索

支持“特级大师思路映射”功能

任务3（联调）：系统整体联调

进行系统整体联调，确保各模块协同工作：

统一术语输出（标准红方大写字母K/A/E/R/C/H/P符号体系）

优化响应延迟（目标<3秒）

完善错误处理和用户提示

准备演示脚本和演示数据

4.4.3 交付物与验收标准

表4-4：Sprint 4交付物与验收标准

四周Sprint的时间线和里程碑汇总如下：

表4-5：Sprint时间线与里程碑

4.5 Phase 2：神经符号增强阶段（Sprint 5-7）

基于 UPDATE1 附录E 的神经符号增强方案，在完成基础 MVP（Sprint 1-4）后，进入高级推理能力增强阶段。目标是将系统从"基于证据的讲解"升级为"基于证明的推理"。

4.5.1 Sprint 5（第5-6周）：假设演绎推理引擎

Sprint目标

实现 DeductiveVerifier 核心逻辑，强制系统生成待验证假设并进行符号化演绎证明。

任务分解

任务1：状态Schema扩展
- 扩展 AgentState 支持 reasoning.candidate_hypotheses
- 定义 Hypothesis 数据结构（id/statement/verification_plan/verification_result/proof_chain）
- 定义 ChosenClaim 数据结构（claim_id/statement/confidence/bound_evidence）

任务2：语义提取节点增强
- 在 semantic_extractor 节点中实现假设生成逻辑
- 基于 semantic_state 提炼2-3个核心假设
- 例如：检测到 king_safety_black: fragile → 生成假设H1："黑方王翼存在可利用的结构性弱点"

任务3：演绎验证器实现
- 实现 DeductiveVerifier 类
- 前提提取：从 semantic_state 和 facts 中提取相关前提
- 规则匹配：在棋理概念本体中匹配因果/推断规则
- 证据绑定：每步推导绑定到具体证据（ENGINE/BOOK/KG）
- 结论裁决：VERIFIED / PARTIALLY_VERIFIED / REFUTED / UNCERTAIN

任务4：演示案例准备
- 准备5个典型局面的演绎推理演示案例
- 包含完整的前提-规则-结论证明链

交付物与验收标准

| 交付物 | 验收标准 |
|--------|----------|
| core/reasoning/state.py | 状态Schema支持假设字段 |
| core/reasoning/deductive_verifier.py | DeductiveVerifier类实现 |
| core/agent/nodes/semantic_extractor.py | 假设生成逻辑 |
| tests/test_deductive.py | 演绎推理测试通过 |
| docs/demos/ | 5个演示案例 |

4.5.2 Sprint 6（第3-4周）：思维树规划器 + 对抗验证

Sprint目标

实现 ToT（Tree of Thought）规划器的分支生成与评估逻辑，开发对抗样本生成器。

任务分解

任务1：思维树规划器
- 实现 claim_planner 的多分支生成模式
- 分支评估因子：Engine_Score_Consistency / KG_Support_Rate / Rule_Application_Count
- 最优路径选择逻辑
- 更新 LangGraph 图结构支持 ToT 分支

任务2：对抗样本生成器
- 实现独立 LLM 实例作为"对手"
- 在关键逻辑节点引入错误（偷换概念/伪造证据/忽视反例）
- 构建首批20个对抗样本

任务3：系统自检机制
- evidence_verifier 处理对抗样本
- 记录推理鲁棒性指标
- 错误归因与修复反馈

任务4：评测脚本
- 编写"演绎推理质量"相关评测脚本
- 假设验证完整率 / 证明链可信度

交付物与验收标准

| 交付物 | 验收标准 |
|--------|----------|
| core/reasoning/tot_planner.py | ToT规划器实现 |
| core/reasoning/branch_evaluator.py | 分支评估器 |
| core/reasoning/adversarial_generator.py | 对抗样本生成器 |
| data/adversarial_samples/ | 20个对抗样本 |
| scripts/eval_reasoning.py | 评测脚本 |

4.5.3 Sprint 7（第7-8周）：语义空间映射 + 集成联调

Sprint目标

完整集成 ToT 与对抗验证闭环，完善语义空间映射，建立线上推理质量仪表盘。

任务分解

任务1：特征提取器对齐
- Transformer Key Feature Extractor 输出包含空间坐标/棋子标识
- 输出格式：active_rook_id, weak_pawn_coord 等

任务2：Prompt管线强制绑定
- 更新"中层解释层"和"高层战略层"Prompt
- 强制要求输出抽象判断后注明底层依据
- 示例："红方掌握了主动权优势（依据：ENGINE评分+0.5，且PV显示连续三步先手）"

任务3：完整工作流集成
- 更新 LangGraph 图结构（见附录E.3.2）
- 集成 semantic_extractor + 假设生成
- 集成 ToT 规划 + branch_evaluator
- 集成 evidence_verifier + 演绎证明
- 集成 teaching_rewriter + 空间概念绑定

任务4：推理质量仪表盘
- 建立线上监控仪表盘
- 持续监控新增指标（假设验证完整率/证明链可信度/最优路径命中率等）

任务5：深度/快速模式切换
- 为复杂分析设置开关
- 用户可选择快速模式或深度分析模式

交付物与验收标准

| 交付物 | 验收标准 |
|--------|----------|
| core/reasoning/semantic_mapper.py | 语义空间映射 |
| core/agent/graph_v2.py | 完整工作流集成 |
| prompts/ | 更新后的Prompt模板 |
| scripts/dashboard.py | 推理质量仪表盘 |
| tests/integration/ | 集成测试通过 |

Phase 2 时间线汇总

| Sprint | 时间 | 核心目标 |
|--------|------|----------|
| Sprint 5 | 第5-6周 | 假设演绎推理引擎 |
| Sprint 6 | 第7-8周 | 思维树规划器 + 对抗验证 |
| Sprint 7 | 第9-10周 | 语义空间映射 + 集成联调 |

5. 团队AI赋能开发协议

为了在30天内完成项目，全员必须遵守以下AI开发协议。本协议规定了团队在使用AI编程助手时的工作原则、开发流程和质量保障措施。严格遵守本协议，可以最大化AI辅助开发的效率，同时保证代码质量。

5.1 开发原则与规范

5.1.1 拒绝手写样板代码

所有的界面组件、UCI协议正则解析、LangGraph骨架，全部通过喂给Trae/Cursor这个文档的上下文来自动生成。团队应充分利用AI的能力，将精力集中在业务逻辑和创新功能上。

以下代码应优先使用AI生成：

Gradio/Streamlit界面组件

UCI协议的正则解析代码

LangGraph的节点和边定义

数据库连接和CRUD操作

单元测试和集成测试

API接口的定义和文档

5.1.2 测试驱动（TDD）

AI每写完一个工具函数（如query_neo4j），团队成员必须立刻运行独立脚本进行验证，确保不将Bug带入Agent状态机。测试驱动开发的原则是：先写测试，再写实现，最后重构。

TDD工作流程：

编写测试：根据需求编写测试用例

运行测试：确认测试失败（红色）

编写实现：用AI生成最小实现代码

运行测试：确认测试通过（绿色）

重构优化：改进代码质量，保持测试通过

# test_pikafish_tool.py 示例
import pytest
from pikafish_tool import PikafishTool

def test_analyze_starting_position():
    """测试初始局面分析"""
    tool = PikafishTool("./pikafish")
    fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    result = tool.analyze(fen, depth=10)
    
    assert "bestmove" in result
    assert "score" in result
    assert result["score"] == 0  # 初始局面均势

5.1.3 Prompt即代码

将给DeepSeek的提示词版本化管理（存入GitHub），将其视为核心业务逻辑代码对待。提示词的变更应经过代码审查，确保质量和一致性。

Prompt管理规范：

所有Prompt统一存放在prompts/目录下

Prompt文件使用版本控制，变更需提交commit

Prompt变更需经过团队成员review

记录Prompt版本与系统版本的对应关系

5.2 AI辅助开发工作流

5.2.1 使用Trae/Cursor的最佳实践

以下是使用AI编程助手的最佳实践：

提供完整上下文：将相关文档、需求说明作为上下文喂给AI

分步骤生成：复杂任务拆分为多个小步骤，逐步生成

明确要求格式：指定输出格式（函数签名、返回值类型等）

要求注释和文档：要求AI生成详细的代码注释

迭代优化：根据生成结果，提出修改要求，迭代优化

5.2.2 推荐的Prompt模板

以下是几个常用的Prompt模板：

模板1：生成工具函数

请帮我实现一个Python函数，用于[功能描述]。

要求：
- 函数名：[函数名]
- 输入参数：[参数列表及类型]
- 返回值：[返回值类型及格式]
- 异常处理：[需要处理的异常情况]
- 注释：包含函数docstring和关键步骤注释

上下文：
[相关代码或文档]

模板2：生成Gradio界面

请帮我用Gradio创建一个Web界面，实现[功能描述]。

界面要求：
- 包含[组件列表]
- 布局要求[布局描述]
- 交互逻辑[交互描述]

后端API：
[API接口说明]

模板3：调试和优化

我遇到了以下问题，请帮我调试：

问题描述：[问题描述]
错误信息：[错误信息]

相关代码：
```python
[代码]
```

预期行为：[预期行为]
实际行为：[实际行为]

5.3 代码审查与测试策略

5.3.1 代码审查清单

每次提交代码前，应进行以下检查：

功能正确性：代码是否实现了预期的功能

边界处理：是否处理了异常情况（空输入、超时等）

代码风格：是否符合PEP 8规范

注释完整性：关键逻辑是否有注释说明

测试覆盖：是否编写了相应的单元测试

5.3.2 自动化测试策略

项目应建立以下自动化测试：

单元测试：每个工具函数都有对应的单元测试

集成测试：测试LangGraph工作流的完整流程

端到端测试：测试从用户输入到结果输出的完整链路

# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.10
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run tests
      run: pytest tests/ -v

团队成员角色分工建议如下：

表5-1：团队角色分工建议

6. 代码实现参考

本章提供核心模块的完整代码实现参考。这些代码经过精心设计，可以直接用于项目开发，也可以作为AI生成代码的参考模板。代码遵循Python最佳实践，包含详细的注释和文档字符串。

6.1 Pikafish UCI封装工具

以下是Pikafish UCI封装工具的完整实现：

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pikafish UCI 封装工具
提供与Pikafish象棋引擎的交互接口
"""

import subprocess
import time
import re
from typing import Dict, Optional, List
from dataclasses import dataclass

@dataclass
class EngineResult:
    """引擎分析结果"""
    bestmove: str
    score: int  # 红方视角，单位：百分之一兵
    pv: List[str]  # 预测的主要变化线
    depth: int
    nodes: int
    time_ms: int

class PikafishTool:
    """
    Pikafish UCI 工具类
    
    Usage:
        tool = PikafishTool("/path/to/pikafish")
        result = tool.analyze(fen, depth=20)
        print(result.bestmove, result.score)
    """
    
    def __init__(self, engine_path: str, timeout: int = 30):
        """
        初始化Pikafish工具
        
        Args:
            engine_path: Pikafish可执行文件路径
            timeout: 引擎响应超时时间（秒）
        """
        self.engine_path = engine_path
        self.timeout = timeout
        self.process = None
        self._start_engine()
    
    def _start_engine(self):
        """启动引擎进程"""
        self.process = subprocess.Popen(
            [self.engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        # 初始化UCI
        self._send_command("uci")
        self._wait_for("uciok")
        # 准备就绪
        self._send_command("isready")
        self._wait_for("readyok")
    
    def _send_command(self, cmd: str):
        """发送命令到引擎"""
        self.process.stdin.write(cmd + "\n")
        self.process.stdin.flush()
    
    def _wait_for(self, target: str) -> List[str]:
        """等待引擎返回特定响应"""
        lines = []
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            line = self.process.stdout.readline().strip()
            if line:
                lines.append(line)
                if target in line:
                    return lines
        raise TimeoutError(f"等待{target}超时")
    
    def analyze(self, fen: str, depth: int = 20) -> EngineResult:
        """
        分析指定局面
        
        Args:
            fen: 局面FEN字符串
            depth: 搜索深度
            
        Returns:
            EngineResult: 分析结果
        """
        # 设置局面
        self._send_command(f"position fen {fen}")
        # 开始搜索
        self._send_command(f"go depth {depth}")
        
        # 解析输出
        bestmove = None
        score = 0
        pv = []
        max_depth = 0
        nodes = 0
        
        while True:
            line = self.process.stdout.readline().strip()
            if not line:
                continue
                
            if line.startswith("info"):
                # 解析info信息
                info = self._parse_info(line)
                if "depth" in info:
                    max_depth = info["depth"]
                if "score" in info:
                    score = info["score"]
                if "pv" in info:
                    pv = info["pv"]
                if "nodes" in info:
                    nodes = info["nodes"]
                    
            elif line.startswith("bestmove"):
                bestmove = line.split()[1]
                break
        
        return EngineResult(
            bestmove=bestmove,
            score=score,
            pv=pv,
            depth=max_depth,
            nodes=nodes,
            time_ms=0
        )
    
    def _parse_info(self, line: str) -> Dict:
        """解析info行"""
        info = {}
        parts = line.split()
        i = 1  # 跳过"info"
        while i < len(parts):
            key = parts[i]
            if key == "depth":
                info["depth"] = int(parts[i+1])
                i += 2
            elif key == "score":
                # 格式: score cp 123 或 score mate 5
                score_type = parts[i+1]
                if score_type == "cp":
                    info["score"] = int(parts[i+2])
                elif score_type == "mate":
                    mate_in = int(parts[i+2])
                    info["score"] = 10000 if mate_in > 0 else -10000
                i += 3
            elif key == "pv":
                # 主要变化线
                pv = []
                j = i + 1
                while j < len(parts) and not parts[j] in ["depth", "score", "nodes"]:
                    pv.append(parts[j])
                    j += 1
                info["pv"] = pv
                i = j
            elif key == "nodes":
                info["nodes"] = int(parts[i+1])
                i += 2
            else:
                i += 1
        return info
    
    def close(self):
        """关闭引擎进程"""
        if self.process:
            self._send_command("quit")
            self.process.wait(timeout=5)
    
    def __del__(self):
        self.close()

# 使用示例
if __name__ == "__main__":
    tool = PikafishTool("./pikafish")
    fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    result = tool.analyze(fen, depth=15)
    print(f"最佳着法: {result.bestmove}")
    print(f"局面评分: {result.score}")
    print(f"预测变化: {' '.join(result.pv[:5])}")
    tool.close()

6.2 LangGraph Agent编排

以下是LangGraph Agent编排的完整实现：

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph Agent 编排
定义象棋分析代理的状态机工作流
"""

from typing import TypedDict, Annotated, List, Dict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import operator

# 导入工具
from pikafish_tool import PikafishTool
from book_retriever import BookRetriever
from knowledge_graph import XiangqiKnowledgeGraph

# 定义状态
class AgentState(TypedDict):
    """
    代理状态
    包含工作流执行过程中的所有中间结果
    """
    # 输入
    input_type: str  # "fen" 或 "image"
    fen: str  # 当前局面FEN
    image_path: str  # 图片路径（如果是图片输入）
    
    # 中间结果
    visual_desc: str  # 视觉描述
    engine_result: Dict  # 引擎分析结果
    book_result: List[Dict]  # 棋书检索结果
    kg_result: Dict  # 知识图谱结果
    
    # 输出
    explanation: str  # 最终讲解
    error: str  # 错误信息

class XiangqiAgent:
    """
    象棋分析代理
    
    使用LangGraph编排多工具协同工作流
    """
    
    def __init__(
        self,
        pikafish_path: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        deepseek_api_key: str,
        faiss_index_path: str
    ):
        """初始化代理"""
        # 初始化工具
        self.pikafish = PikafishTool(pikafish_path)
        self.book_retriever = BookRetriever(faiss_index_path)
        self.kg = XiangqiKnowledgeGraph(neo4j_uri, neo4j_user, neo4j_password)
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=deepseek_api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        # 构建工作流
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        """构建LangGraph工作流"""
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("preprocess", self._preprocess_node)
        workflow.add_node("analyze_engine", self._analyze_engine_node)
        workflow.add_node("retrieve_books", self._retrieve_books_node)
        workflow.add_node("query_kg", self._query_kg_node)
        workflow.add_node("generate", self._generate_node)
        
        # 设置入口点
        workflow.set_entry_point("preprocess")
        
        # 添加边
        workflow.add_edge("preprocess", "analyze_engine")
        workflow.add_edge("analyze_engine", "retrieve_books")
        workflow.add_edge("retrieve_books", "query_kg")
        workflow.add_edge("query_kg", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()
    
    def _preprocess_node(self, state: AgentState) -> AgentState:
        """预处理节点"""
        if state["input_type"] == "image":
            # TODO: 调用视觉模型提取FEN
            pass
        return state
    
    def _analyze_engine_node(self, state: AgentState) -> AgentState:
        """引擎分析节点"""
        result = self.pikafish.analyze(state["fen"], depth=20)
        state["engine_result"] = {
            "bestmove": result.bestmove,
            "score": result.score,
            "pv": result.pv,
            "depth": result.depth
        }
        return state
    
    def _retrieve_books_node(self, state: AgentState) -> AgentState:
        """棋书检索节点"""
        # 使用引擎推荐的最佳着法作为查询
        query = state["engine_result"]["bestmove"]
        results = self.book_retriever.retrieve(query, k=3)
        state["book_result"] = results
        return state
    
    def _query_kg_node(self, state: AgentState) -> AgentState:
        """知识图谱查询节点"""
        win_rate = self.kg.get_win_rate(state["fen"])
        similar = self.kg.query_similar_positions(state["fen"], limit=3)
        state["kg_result"] = {
            "win_rate": win_rate,
            "similar_positions": similar
        }
        return state
    
    def _generate_node(self, state: AgentState) -> AgentState:
        """讲解生成节点"""
        # 构建提示词
        prompt = self._build_explanation_prompt(state)
        
        # 调用LLM生成讲解
        response = self.llm.invoke([HumanMessage(content=prompt)])
        state["explanation"] = response.content
        return state
    
    def _build_explanation_prompt(self, state: AgentState) -> str:
        """构建讲解生成提示词"""
        prompt = f"""
你是一位象棋大师，正在为初学者讲解棋局。

【重要原则】
1. 工具优先：所有精确数据必须来自引擎结果
2. 引用优先：战略分析必须引用棋书原文或知识图谱数据
3. 严禁编造：不得自行捏造棋理或历史数据

【当前局面】
FEN: {state['fen']}

【引擎分析结果】
最佳着法: {state['engine_result']['bestmove']}
局面评分: {state['engine_result']['score']}（红方视角，正值为红优）
预测变化线: {' '.join(state['engine_result']['pv'][:5])}

【棋书检索结果】
"""
        for i, book in enumerate(state['book_result'], 1):
            prompt += f"{i}. [{book['source']}] {book['text'][:100]}...\n"
        
        prompt += f"""

【知识图谱数据】
历史胜率: 红方 {state['kg_result']['win_rate'].get('red', 'N/A')}%

【输出要求】
1. 首先给出最佳着法（来自引擎）
2. 分析当前局面的战略态势
3. 引用棋书原文解释该着法的战略意义
4. 提及历史胜率数据（如有）
5. 语言生动易懂，适合初学者理解
"""
        return prompt
    
    def analyze(self, fen: str) -> Dict:
        """
        分析指定局面
        
        Args:
            fen: 局面FEN字符串
            
        Returns:
            Dict: 包含讲解和各项分析结果
        """
        # 初始化状态
        initial_state = AgentState(
            input_type="fen",
            fen=fen,
            image_path="",
            visual_desc="",
            engine_result={},
            book_result=[],
            kg_result={},
            explanation="",
            error=""
        )
        
        # 执行工作流
        final_state = self.workflow.invoke(initial_state)
        
        return {
            "fen": final_state["fen"],
            "explanation": final_state["explanation"],
            "engine_result": final_state["engine_result"],
            "book_result": final_state["book_result"],
            "kg_result": final_state["kg_result"]
        }

6.3 棋书PDF向量化脚本

以下是棋书PDF向量化的完整实现：

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
棋书PDF向量化工具
将象棋书籍PDF转换为向量索引
"""

import os
from pathlib import Path
from typing import List, Dict
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from tqdm import tqdm

class BookVectorizer:
    """
    棋书向量化工具
    
    Usage:
        vectorizer = BookVectorizer()
        vectorizer.process_pdf("./books/梅花谱.pdf", "梅花谱")
        vectorizer.process_pdf("./books/橘中秘.pdf", "橘中秘")
        vectorizer.build_index("./faiss_index")
    """
    
    def __init__(
        self,
        embedding_model: str = "BAAI/bge-m3",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        初始化向量化工具
        
        Args:
            embedding_model: 嵌入模型名称
            chunk_size: 文本切分块大小
            chunk_overlap: 切分重叠大小
        """
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"}
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", " ", ""],
            length_function=len
        )
        self.documents = []
    
    def process_pdf(self, pdf_path: str, book_name: str) -> int:
        """
        处理单个PDF文件
        
        Args:
            pdf_path: PDF文件路径
            book_name: 书名（用于元数据）
            
        Returns:
            int: 处理的文档块数量
        """
        print(f"正在处理: {book_name}")
        
        # 加载PDF
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        
        # 添加元数据
        for page in pages:
            page.metadata["source"] = book_name
            page.metadata["page"] = page.metadata.get("page", 0)
        
        # 文本切分
        chunks = self.text_splitter.split_documents(pages)
        
        # 添加到文档集合
        self.documents.extend(chunks)
        
        print(f"  生成 {len(chunks)} 个文本块")
        return len(chunks)
    
    def process_directory(self, directory: str) -> int:
        """
        批量处理目录中的所有PDF
        
        Args:
            directory: PDF文件所在目录
            
        Returns:
            int: 处理的总文档块数量
        """
        total_chunks = 0
        pdf_files = list(Path(directory).glob("*.pdf"))
        
        print(f"发现 {len(pdf_files)} 个PDF文件")
        
        for pdf_file in tqdm(pdf_files, desc="处理PDF"):
            book_name = pdf_file.stem  # 使用文件名（不含扩展名）作为书名
            chunks = self.process_pdf(str(pdf_file), book_name)
            total_chunks += chunks
        
        print(f"\n总计: {total_chunks} 个文本块")
        return total_chunks
    
    def build_index(self, output_path: str):
        """
        构建FAISS索引并保存
        
        Args:
            output_path: 索引保存路径
        """
        if not self.documents:
            raise ValueError("没有文档可以索引，请先调用process_pdf")
        
        print(f"\n正在构建FAISS索引...")
        print(f"文档数量: {len(self.documents)}")
        
        # 构建向量索引
        vectorstore = FAISS.from_documents(
            self.documents,
            self.embeddings
        )
        
        # 保存索引
        vectorstore.save_local(output_path)
        print(f"索引已保存到: {output_path}")
        
        return vectorstore

# 使用示例
if __name__ == "__main__":
    import torch
    
    # 初始化向量化工具
    vectorizer = BookVectorizer(
        embedding_model="BAAI/bge-m3",
        chunk_size=500,
        chunk_overlap=50
    )
    
    # 处理单个PDF
    # vectorizer.process_pdf("./books/梅花谱.pdf", "梅花谱")
    
    # 批量处理目录
    vectorizer.process_directory("./books")
    
    # 构建并保存索引
    vectorizer.build_index("./faiss_index")

6.4 Gradio前端界面

以下是Gradio前端界面的完整实现：

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gradio前端界面
象棋AI分析系统的Web界面
"""

import gradio as gr
from PIL import Image
import tempfile
import os

# 导入后端模块
from xiangqi_agent import XiangqiAgent
from board_renderer import BoardRenderer

# 初始化组件
agent = XiangqiAgent(...)  # 配置参数
renderer = BoardRenderer()

def analyze_fen(fen: str):
    """分析FEN局面"""
    # 调用Agent分析
    result = agent.analyze(fen)
    
    # 渲染棋盘
    board_image = renderer.render(fen)
    
    # 格式化输出
    explanation = result["explanation"]
    engine_info = format_engine_result(result["engine_result"])
    
    return board_image, explanation, engine_info

def format_engine_result(engine_result: dict) -> str:
    """格式化引擎结果"""
    return f"""
**引擎分析**\n- 最佳着法: {engine_result.get('bestmove', 'N/A')}\n- 局面评分: {engine_result.get('score', 'N/A')}\n- 搜索深度: {engine_result.get('depth', 'N/A')}\n- 预测变化: {' '.join(engine_result.get('pv', [])[:5])}"""

# 创建Gradio界面
with gr.Blocks(title="象棋AI分析系统", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 象棋AI混合代理教学与对弈系统
    基于Pikafish引擎 + DeepSeek LLM + LangGraph Agent的智能象棋分析平台
    """)
    
    with gr.Tab("局面分析"):
        with gr.Row():
            with gr.Column(scale=1):
                fen_input = gr.Textbox(
                    label="FEN字符串",
                    placeholder="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
                    lines=2
                )
                analyze_btn = gr.Button("分析局面", variant="primary")
                
            with gr.Column(scale=2):
                board_output = gr.Image(label="棋盘")
        
        explanation_output = gr.Markdown(label="AI讲解")
        engine_output = gr.Markdown(label="引擎信息")
        
        analyze_btn.click(
            analyze_fen,
            inputs=fen_input,
            outputs=[board_output, explanation_output, engine_output]
        )
    
    with gr.Tab("图片识别"):
        with gr.Row():
            with gr.Column(scale=1):
                image_input = gr.Image(label="上传棋盘图片", type="pil")
                recognize_btn = gr.Button("识别局面", variant="primary")
            
            with gr.Column(scale=2):
                recognized_board = gr.Image(label="识别结果")
                recognized_fen = gr.Textbox(label="识别的FEN")
    
    with gr.Tab("人机对战"):
        gr.Markdown("人机对战功能开发中...")
    
    with gr.Tab("使用说明"):
        gr.Markdown("""
        ## 使用说明\n\n        ### 局面分析\n        1. 在FEN输入框中粘贴局面FEN字符串\n        2. 点击"分析局面"按钮\n        3. 系统将显示棋盘图像、AI讲解和引擎分析\n\n        ### 图片识别\n        1. 上传棋盘照片或截图\n        2. 点击"识别局面"按钮\n        3. 系统将自动识别棋子位置并生成FEN\n\n        ### FEN格式说明\n        FEN（Forsyth-Edwards Notation）是描述象棋局面的标准格式。\n        示例：`rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1`\n        """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)

7. 迭代演进与维护

本项目采用敏捷迭代模式，将整体路线划分为若干阶段（Phase），每个阶段又细分为若干Sprint（迭代周期，约2-4周）。每个Sprint都有明确的迭代目标和可交付成果。本章阐述项目的迭代演进机制和维护策略。

7.1 迭代演进机制

7.1.1 活文档（Living Constitution）

本规划文档作为“活文档”，会随着项目进展不断演进。所有参与者（包括AI助手）都必须严格遵循本规划，并在实践中不断完善它，确保项目沿着正确的方向演进。

文档版本管理规范：

版本号格式：主版本.次版本（如v1.0, v1.1, v2.0）

主版本变更：重大架构调整或功能变更

次版本变更：小功能增加、bug修复、文档完善

每次迭代后输出完整的新版规划文档

所有变更通过GitHub进行版本控制

7.1.2 反馈驱动优化

根据测试反馈，识别系统的不足之处，进入下一个迭代进行优化。反馈来源包括：

内部测试：项目团队的自测和交叉测试

用户测试：邀请目标用户（象棋爱好者）试用

专家评审：请象棋教练或高手评估讲解质量

性能监控：系统响应时间、资源占用等指标

7.1.3 并行小迭代

不同模块可以并行迭代优化。例如，在优化讲解质量的同时，可以小步迭代视觉模型调用来提高棋盘识别准确率。这种并行迭代确保各组件齐头并进。

7.2 维护策略

7.2.1 版本控制与演进

所有代码和文档变更都通过GitHub进行版本控制。Git工作流建议：

主分支（main）：稳定版本，随时可以部署

开发分支（dev）：日常开发，功能集成

功能分支（feature/*）：单个功能开发

修复分支（hotfix/*）：紧急bug修复

7.2.2 回滚与扩展

如果某个迭代失败或效果不佳，系统设计支持安全回滚到上一稳定状态。同时，新功能可以作为独立子迭代加入现有阶段，而不影响已有功能的稳定性。

7.2.3 社区迭代

项目开源后，鼓励社区通过Issues和PR提出修改建议或贡献代码，实现长期维护和演进。规划文档也会根据社区反馈进行必要的修订，保持其作为项目“宪法”的权威性和时效性。

7.3 总结与展望

Xiangqi Hybrid LLM-Agent Analysis System通过精心设计的架构和严谨的迭代规划，正朝着其核心目标稳步迈进。当前阶段（Phase 1）已实现了基础的FEN解析、引擎调用和LLM讲解集成，正在进行视觉感知模块的集成和Prompt工程，以进一步提高讲解的生动度和准确度。

展望未来，系统将在以下方向持续演进：

知识图谱丰富：导入更多历史对局数据，提升检索准确性

棋书库扩展：支持更多经典和现代棋书

视觉模型升级：提高棋盘识别准确率，支持更多输入形式

个性化学习：根据用户水平定制讲解深度

社区功能：支持用户分享和讨论

更长远地看，本项目有望成为Neuro-Symbolic AI在复杂博弈领域的一个标杆案例。它将证明，通过将符号系统的严谨性与深度学习的灵活性相结合，可以创造出既“聪明”又“可靠”的智能系统。这不仅对棋类爱好者有实用价值，也对人工智能研究具有启示意义——展示了一条实现更高级AI智能的可行路径。

附录A：术语表

本附录列出文档中使用的专业术语及其解释。

表A-1：术语表

附录B：参考资源

B.1 开源项目

Pikafish：https://github.com/official-pikafish/Pikafish

LangGraph：https://github.com/langchain-ai/langgraph

LangChain：https://github.com/langchain-ai/langchain

Qwen-VL：https://github.com/QwenLM/Qwen2.5-VL

B.2 数据集

悟空象棋数据集：包含大量历史对局

CCRL象棋引擎排名：引擎测试数据

B.3 经典棋书

《橘中秘》：明代象棋经典

《梅花谱》：清代象棋名著

《象棋实用残局》：残局学习必备

《象棋布局原理》：现代开局理论

B.4 技术文档

UCI协议规范：http://wbec-ridderkerk.nl/html/UCIProtocol.html

FEN格式说明：https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation

Neo4j文档：https://neo4j.com/docs/

DeepSeek API：https://platform.deepseek.com/

附录E：神经符号增强与演绎推理能力升级方案

E.1 背景与目标

本附录旨在将当前前沿的神经符号AI研究成果，系统性地集成至现有"中高层解释器"架构中。核心目标是解决纯LLM在复杂棋局分析中存在的"推理黑箱"与"幻觉"问题，通过引入显式的假设演绎、多路径规划与对抗验证机制，将系统从一个"优秀的讲解员"升级为一个"严谨的分析师"，从而构建可验证、可追溯的高可信推理闭环。

本次升级紧密围绕文档v2.0中识别的缺口（如缺乏假设验证机制、单一线性推理路径），并遵循"工具优先、证据优先"的核心原则。

E.2 核心技术增强方案

E.2.1 假设演绎推理引擎

原理：将LLM擅长的"假设验证"能力制度化。不再让系统直接输出最终解释，而是强制其生成若干待验证的假设，并利用引擎、知识库等外部工具进行严格的符号化演绎证明。

系统实现：
1. 节点增强：在 semantic_extractor 节点中，不仅生成语义标签，还需基于当前 semantic_state 提炼出2-3个核心假设，存入 reasoning.candidate_hypotheses。例如，若检测到 king_safety_black: fragile，则生成假设H1："黑方王翼存在可利用的结构性弱点"。
2. 验证流程：在 evidence_verifier 节点中实现 DeductiveVerifier 类。对于每个假设，制定并执行一个结构化的验证计划（Plan）：
   - 前提提取：从 semantic_state 和 facts 中提取相关前提。例如，为H1提取前提：P1："黑方中卒挺起，王城开线"（来自视觉或引擎PV），P2："红方车炮可集结至底线"（来自引擎搜索结果）。
   - 规则匹配：在棋理概念本体中匹配相应的因果或推断规则。例如，规则R：王城开线 + 重子集结 -> 高概率战术威胁。
   - 证据绑定：要求每一步推导都必须绑定到具体证据（如 ENGINE: PV显示车八平六， BOOK: 引用《橘中秘》'破象局'）。
   - 结论裁决：综合证据与规则，对假设进行裁决。结果可标记为 VERIFIED, PARTIALLY_VERIFIED, REFUTED 或 UNCERTAIN，并存入 reasoning.chosen_claims。

预期效果：解释输出将包含一个可追溯的"证明"路径，而非单一结论，极大提升分析的说服力和可信度。

E.2.2 思维树（Tree of Thought）规划器

原理：为解决线性推理易"一条道走到黑"的问题，引入树形搜索策略。系统可探索多种不同的战略解释路径，并利用客观工具（引擎评分、知识图谱统计）作为评估函数，剪枝掉逻辑薄弱的分支。

系统实现：
1. 分支生成：claim_planner 根据不同的核心矛盾识别结果，生成多条解释主线（例如：路径A侧重"中路控制"，路径B侧重"侧翼突破"）。
2. 分支评估：每个分支都作为一个临时的 AgentState 副本，继续执行 evidence_verifier。评估分数由以下因子加权计算：
   - Engine_Score_Consistency：解释与引擎评分方向的一致性
   - KG_Support_Rate：解释中关键论断在知识图谱中的历史支持率
   - Rule_Application_Count：成功应用的棋理规则数量
3. 最优路径选择：选择评估分数最高的分支进入最终的 teaching_rewriter 节点。

预期效果：系统能够比较不同的战略视角，避免因单一视角偏差导致的错误，输出更全面、更经得起推敲的分析。

E.2.3 面向推理的对抗验证闭环

原理：借鉴对抗生成思想，自动化地发现和修复系统推理中的逻辑漏洞。通过一个生成器故意产生带有细微逻辑错误的解释，训练系统的验证器更敏锐地识别证据与结论之间的矛盾。

系统实现：
1. 对抗样本生成：使用一个独立的LLM实例作为"对手"。给定一个正确解释，对手负责在关键逻辑节点引入错误，例如：偷换概念（将"子力活跃"混淆为"物质优势"）、伪造证据引用、忽视反例数据等。
2. 系统自检：让系统的 evidence_verifier 节点处理这些对抗样本。记录其成功检测出逻辑谬误的比率，作为"推理鲁棒性指标"。
3. 错误归因与修复：对于未被检测出的谬误，进行人工或自动化的错误归因，并反馈修复。修复对象可能是：Prompt模板、棋理本体规则定义、或验证器的检查逻辑。

预期效果：系统具备自我"逻辑免疫"能力，在持续对抗中不断提升推理的严密性，形成自我进化的飞轮。

E.2.4 语义空间映射与思维链绑定

原理：强化高层战略概念与底层具体事实（空间位置、棋子动态）的绑定关系。确保每一个抽象的战略判断（如"红方主动权优势"）都能向下追溯到引擎计算的精确线路或视觉模型识别的棋子部署。

系统实现：
1. 特征提取器对齐：Transformer Key Feature Extractor 的输出除语义向量外，还应包含关键特征的空间坐标或棋子标识（如 active_rook_id, weak_pawn_coord）。
2. Prompt管线强制绑定：在"中层解释层"和"高层战略层"Prompt中，强制要求LLM在输出每个抽象判断后，必须用括号注明其底层依据。

示例输出："红方掌握了主动权优势（依据：ENGINE评分+0.5，且PV显示连续三步先手；VISION识别红方双车炮已占开放线）。"

预期效果：彻底杜绝"无根之木"式的空泛战略说辞，确保每一句高层分析都"脚踏实地"。

E.3 状态Schema与工作流更新

E.3.1 状态Schema扩展

```python
state = {
    ...,
    "reasoning": {
        "core_contradiction": "",
        "candidate_hypotheses": [
            {
                "id": "h1",
                "statement": "假设陈述",
                "verification_plan": [{"tool": "ENGINE", "query": "..."}],
                "verification_result": "VERIFIED | REFUTED | UNCERTAIN",
                "proof_chain": []
            }
        ],
        "chosen_claims": [
            {
                "claim_id": "c1",
                "statement": "最终结论",
                "confidence": 0.85,
                "bound_evidence": ["ENGINE:p2", "BOOK:p3"]
            }
        ],
        "uncertainties": [],
        "tot_branches": [
            {
                "branch_id": "b1",
                "core_theme": "中路突破",
                "evaluation_score": 0.92,
                "claims": [...]
            }
        ],
        "adversarial_test": {
            "last_errors_found": 3,
            "total_tests": 100
        }
    },
    "semantic": {
        ...,
        "spatial_features": [
            {"feature": "red_rook_activity", "bound_to": "piece_id_Ra", "coord": "9,0"}
        ]
    }
}
```

E.3.2 升级后的LangGraph图结构

```
flowchart LR
    START --> A[problem_classifier]
    A --> B[preprocess]
    B --> C[analyze_engine]
    C --> D[retrieve_books]
    D --> E[query_kg]
    E --> F[semantic_extractor + 假设生成]
    F --> G{启用ToT规划?}
    G -- 是 --> H[claim_planner + 多分支生成]
    G -- 否 --> I[claim_planner + 单分支]
    H --> J[branch_evaluator]
    J --> K[evidence_verifier + 演绎证明]
    I --> K
    K --> L[teaching_rewriter + 空间概念绑定]
    L --> END
```

E.4 评测指标体系扩展

在原有指标基础上，新增以下维度以衡量推理能力：

| 指标类别 | 指标名称 | 定义与测量方法 |
|---------|---------|---------------|
| 演绎推理质量 | 假设验证完整率 | 对专家标注的假设，系统验证步骤（前提-规则-结论）的完备性 |
| 演绎推理质量 | 证明链可信度 | 证明链中每一步推理与绑定证据的吻合度，由专家抽检打分 |
| 思维规划能力 | 最优路径命中率 | ToT模式下，系统选择的最优解释分支与专家选择的一致率 |
| 鲁棒性 | 对抗样本误拒率 | 系统错误地将一个正确解释判定为含有逻辑谬误的比例 |
| 鲁棒性 | 对抗样本漏检率 | 系统未能检测出对抗样本中人工植入的逻辑谬误的比例 |
| 可解释性 | 概念绑定追溯成功率 | 用户能否通过系统提供的证据标签，成功定位到支撑某抽象概念的具体事实 |

E.5 实施路线图与风险控制

E.5.1 分阶段实施计划

| 阶段 | 时间 | 目标 |
|-----|------|-----|
| MVP增强版 | 第1-2周 | 实现 DeductiveVerifier 核心逻辑，集成到 evidence_verifier 节点。更新状态Schema，支持假设字段。准备包含5个典型局面的演绎推理演示案例。 |
| 稳定版 | 第3-4周 | 实现ToT规划器的分支生成与评估逻辑。开发对抗样本生成器的基础模块，构建首批20个对抗样本。完成评测指标中"演绎推理质量"相关脚本的编写。 |
| 专业版 | 第5-8周 | 完整集成ToT与对抗验证闭环到评测流程中。完善语义空间映射，更新特征提取器输出格式。建立线上推理质量仪表盘，持续监控新增指标。 |

E.5.2 风险与应对

| 风险类型 | 描述 | 应对策略 |
|---------|------|---------|
| 技术复杂度风险 | 演绎推理和ToT的实现可能增加系统延迟 | 为复杂分析设置开关，用户可选择快速模式或深度分析模式 |
| LLM能力依赖风险 | 假设生成质量受模型能力影响 | 通过精细的Prompt工程和棋理本体约束，引导模型生成符合逻辑的假设 |
| 评测成本风险 | 专家标注证明链成本高 | 采用"模型生成-专家校验"的模式，先由系统生成证明链草案，专家仅进行审核和纠正 |

E.6 总结

本方案通过引入假设演绎、思维树、对抗验证和语义绑定等神经符号AI的关键技术，对现有混合代理系统进行了深度增强。它标志着系统从"基于证据的讲解"向"基于证明的推理"的关键演进。升级后的系统不仅能给出更精准、更深刻的棋局分析，其透明的推理过程更能满足专业教学、竞技分析等场景的高可信要求，为项目的实际应用与学术价值奠定了坚实基础。

---

象棋AI混合代理教学与对弈系统

Xiangqi Hybrid LLM-Agent Analysis System

Version 1.1  |  2025年3月

© 2025 开源项目