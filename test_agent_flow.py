#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试两阶段Agent流程 - 流式输出"""

import requests
import sys
import io
import json
import time
from dotenv import load_dotenv
import os

load_dotenv()

# 强制行缓冲，实时输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdout.reconfigure(line_buffering=True)

api_key = os.getenv('ALIYUN_API_KEY')
FEN = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR w - - 0 3'

print('【系统启动】')
print(f'局面: {FEN}')
print()

# ========== 基础Prompt ==========
BASE_PROMPT = '''你是中国象棋教练AI。

## 你的局限性
你是瞎子: 看不到棋盘，不懂象棋规则(马走日象走田、炮隔山打)。
你不懂棋理: 不知道开局为什么要出动车马炮。
你会编造: 需要工具数据约束自己。

注意: 局限性认知是内部的，对用户输出时是自信的教练。

## 可用工具
- get_piece_attacks: 查棋子能攻击什么
- get_piece_defenders: 查谁在保护某棋子
- get_threats_to_piece: 查谁在威胁某棋子
- get_piece_relations: 综合攻防关系
- analyze_move: 分析某步棋效果
- engine_deep_analysis: 引擎深度分析
- engine_alternatives: 候选走法对比
- analyze_position_strategy: 战略分析

## 当前局面
FEN: ''' + FEN + '''
红方: 帅(5,1) 仕(4,1)(6,1) 相(3,1)(7,1) 马(2,1)(8,1) 车(1,1)(9,1) 炮(2,3)(8,3) 兵(1,4)(3,4)(6,3)(7,4)(9,4)
黑方: 将(5,10) 士(4,10)(6,10) 象(3,10)(7,10) 马(2,10)(8,10) 车(1,10)(9,10) 炮(3,8)(7,8) 卒(1,7)(3,7)(5,7)(7,7)(9,7)
引擎评估: cp=123, bestmove=g3g4'''

# ========== 阶段1: 规划 ==========
print('=' * 60)
print('【阶段1: 规划】 Qwen-Max决定怎么分析')
print('=' * 60)

resp = requests.post(
    'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
    json={
        'model': 'qwen-max',
        'messages': [
            {'role': 'system', 'content': BASE_PROMPT},
            {'role': 'user', 'content': '你打算怎么分析? 列出想调用的工具、目的。(只规划，不执行)'}
        ],
        'temperature': 0.7,
        'max_tokens': 800
    },
    timeout=60
)

plan = resp.json()['choices'][0]['message']['content']
print(plan)
print()

# ========== 阶段2: 执行循环 ==========
print('=' * 60)
print('【阶段2: 执行】 Qwen-Max调用工具并思考')
print('=' * 60)

def execute_tool(tool_name, args=None):
    from core.llm.agent_tools import AgentTools
    tools = AgentTools()
    args = args or {}
    args['fen'] = FEN

    func_map = {
        'get_piece_attacks': tools.get_piece_attacks,
        'get_piece_defenders': tools.get_piece_defenders,
        'get_threats_to_piece': tools.get_threats_to_piece,
        'get_piece_relations': tools.get_piece_relations,
        'analyze_move': tools.analyze_move,
        'engine_deep_analysis': tools.engine_deep_analysis,
        'engine_alternatives': tools.engine_alternatives,
        'analyze_position_strategy': tools.analyze_position_strategy,
    }

    func = func_map.get(tool_name)
    if not func:
        return {'error': f'Unknown: {tool_name}'}

    result = func(**args)
    if hasattr(result, 'data'):
        return {'success': result.success, 'data': result.data, 'message': result.message}
    return result

TOOLS_SCHEMA = [
    {'type': 'function', 'function': {'name': 'get_piece_attacks', 'parameters': {'type': 'object', 'properties': {'piece': {'type': 'string'}}}}},
    {'type': 'function', 'function': {'name': 'get_piece_defenders', 'parameters': {'type': 'object', 'properties': {'piece': {'type': 'string'}}}}},
    {'type': 'function', 'function': {'name': 'get_threats_to_piece', 'parameters': {'type': 'object', 'properties': {'piece': {'type': 'string'}}}}},
    {'type': 'function', 'function': {'name': 'get_piece_relations', 'parameters': {'type': 'object', 'properties': {'piece': {'type': 'string'}}}}},
    {'type': 'function', 'function': {'name': 'analyze_move', 'parameters': {'type': 'object', 'properties': {'move': {'type': 'string'}}}}},
    {'type': 'function', 'function': {'name': 'engine_deep_analysis', 'parameters': {'type': 'object', 'properties': {'depth': {'type': 'integer', 'default': 20}}}}},
    {'type': 'function', 'function': {'name': 'engine_alternatives', 'parameters': {'type': 'object', 'properties': {'top_n': {'type': 'integer', 'default': 3}}}}},
    {'type': 'function', 'function': {'name': 'analyze_position_strategy', 'parameters': {'type': 'object', 'properties': {}}}},
]

messages = [
    {'role': 'system', 'content': BASE_PROMPT + '\n\n现在你有权限调用工具。 执行分析，根据结果决定是否继续调用。'},
    {'role': 'user', 'content': '请开始执行你的分析计划。'}
]

for round_num in range(3):
    print(f'\n--- 第{round_num+1}轮 ---')

    resp = requests.post(
        'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={
            'model': 'qwen-max',
            'messages': messages,
            'tools': TOOLS_SCHEMA,
            'tool_choice': 'auto',
            'temperature': 0.7,
            'max_tokens': 1000
        },
        timeout=60
    )

    choice = resp.json()['choices'][0]
    msg = choice['message']

    if 'tool_calls' in msg and msg['tool_calls']:
        tool_names = [tc['function']['name'] for tc in msg['tool_calls']]
        print(f'[Qwen决定调用] {tool_names}')

        assistant_msg = {'role': 'assistant', 'content': msg.get('content', ''), 'tool_calls': []}

        for tc in msg['tool_calls']:
            tool_name = tc['function']['name']
            args = json.loads(tc['function']['arguments']) if tc['function']['arguments'] else {}

            print(f'[执行工具] {tool_name}({args})...')

            result = execute_tool(tool_name, args)
            result_preview = str(result)[:180]
            print(f'[工具返回] {result_preview}...')

            assistant_msg['tool_calls'].append({
                'id': tc['id'],
                'type': 'function',
                'function': {'name': tool_name, 'arguments': tc['function']['arguments']}
            })

            messages.append(assistant_msg)
            messages.append({
                'role': 'tool',
                'tool_call_id': tc['id'],
                'content': json.dumps(result, ensure_ascii=False)
            })

        print('[Qwen思考中...]')
    else:
        print('[Qwen思考完成]')
        print()
        print('=' * 60)
        print('【最终分析】')
        print('=' * 60)
        print(msg.get('content', ''))
        break

print()
print('【流程结束】')
