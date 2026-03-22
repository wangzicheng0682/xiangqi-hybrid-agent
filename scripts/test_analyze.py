import sys
sys.path.insert(0, '.')

from web_gradio.app import analyze_position, PlayState, board_to_fen

print('\n测试分析函数...')
result = analyze_position(state)
print(f'分析结果长度: {len(result)}')
print(f'分析结果:\n{result}')
