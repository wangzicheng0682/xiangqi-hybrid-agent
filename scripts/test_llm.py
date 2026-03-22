import sys
sys.path.insert(0, '.')

print('=== LLM测试 ===')
from core.llm import LLMClient, LLMConfig
llm = LLMClient(LLMConfig(
    api_key='715cf7368e134716a8a032dd5e7fcbd2.7zAqa1crDYHcbiWx',
    base_url='https://open.bigmodel.cn/api/paas/v4',
    model='glm-4-flash'
))
response = llm.chat([{'role': 'user', 'content': '你好'}], max_tokens=20)
print(f'LLM响应: {response}')

print()
print('=== Neo4j KG测试 ===')
from core.kg.neo4j_kg import Neo4jKG
kg = Neo4jKG()
kg.connect()
stats = kg.get_statistics()
print(f"数据: {stats['games']:,}局, {stats['positions']:,}局面")
