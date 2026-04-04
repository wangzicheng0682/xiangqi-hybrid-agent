"""
真实 RAG 实现 — ChromaDB 向量检索

替代 MockRAG，提供对棋理原则、开局知识、经典棋谱的语义检索。
使用 text2vec-base-chinese 做中文嵌入，ChromaDB 做向量存储。

数据源:
  1. knowledge_retriever.py 中 80+ 条棋理原则（自动索引）
  2. data/init_data/ 中 14 万局棋谱的开局摘要（按需构建）
"""

import re
import threading
from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from core.engine.base import BaseRAG, RAGResult

# 项目根目录
_PROJECT_ROOT = Path(__file__).parent.parent.parent

# ChromaDB 持久化路径
_CHROMA_DIR = _PROJECT_ROOT / "data" / "vector_db" / "chroma"

# 单例
_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None
_init_lock = threading.Lock()


def _get_collection() -> chromadb.Collection:
    """懒加载 ChromaDB collection（线程安全双重检查锁定）"""
    global _client, _collection
    if _collection is not None:
        return _collection

    with _init_lock:
        if _collection is not None:
            return _collection

        _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
        _collection = _client.get_or_create_collection(
            name="xiangqi_knowledge",
            metadata={"hnsw:space": "cosine"},
        )

        _ensure_collection_seeded(_collection)

    return _collection


def _ensure_collection_seeded(collection: chromadb.Collection) -> None:
    if collection.count() == 0:
        _index_principles(collection)
        _index_opening_knowledge(collection)
        return

    principle_probe = collection.get(where={"type": "principle"}, limit=1)
    if not principle_probe or not principle_probe.get("ids"):
        _index_principles(collection)

    opening_probe = collection.get(where={"type": "opening_principle"}, limit=1)
    if not opening_probe or not opening_probe.get("ids"):
        _index_opening_knowledge(collection)


def _index_principles(collection: chromadb.Collection) -> None:
    """将 knowledge_retriever 中的棋理原则索引到 ChromaDB"""
    from core.llm.knowledge_retriever import ChessKnowledgeBase

    kb = ChessKnowledgeBase()
    documents = []
    metadatas = []
    ids = []

    idx = 0
    for tension_type, principles in kb.TENSION_PRINCIPLES.items():
        for p in principles:
            # 构建检索文本：原则 + 适用条件 + 反例
            doc = f"{p.content}"
            if p.applies_when:
                doc += f"。适用条件：{p.applies_when}"
            if p.counter_case:
                doc += f"。例外：{p.counter_case}"

            documents.append(doc)
            metadatas.append({
                "source": p.source or "经典棋理",
                "type": "principle",
                "tension": tension_type,
                "phase": p.phase or "all",
                "tags": ",".join(p.tags) if p.tags else "",
            })
            ids.append(f"principle_{idx}")
            idx += 1

    if documents:
        # ChromaDB 批量上限 ~5000，这里 80+ 条不会超
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )


def _index_opening_knowledge(collection: chromadb.Collection) -> None:
    from core.llm.opening_knowledge import OPENING_PRINCIPLES, OPENING_SYSTEMS

    documents = []
    metadatas = []
    ids = []

    for item in OPENING_PRINCIPLES:
        doc = f"开局原则：{item['name']}。{item['description']}。要点：{'；'.join(item.get('tips', []))}。常见错误：{'；'.join(item.get('common_mistakes', []))}"
        documents.append(doc)
        metadatas.append({
            "source": "开局知识库",
            "type": "opening_principle",
            "phase": "opening",
            "tags": item["name"],
        })
        ids.append(f"opening_principle_{item['id']}")

    for index, system in enumerate(OPENING_SYSTEMS.values()):
        doc = (
            f"开局体系：{system.name}。首步：{system.first_move}。{system.description}。"
            f"特点：{'；'.join(system.characteristics)}。"
            f"主要变例：{'；'.join(system.variations[:5]) if system.variations else '无'}。"
            f"适合：{system.suitable_for or '通用'}"
        )
        documents.append(doc)
        metadatas.append({
            "source": "开局体系库",
            "type": "opening_system",
            "phase": "opening",
            "tags": system.name,
        })
        ids.append(f"opening_system_{index}")

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)


def index_game_openings(max_games: int = 5000) -> int:
    """
    解析棋谱文件，提取开局信息并索引。

    只索引前 max_games 局避免首次启动太慢。
    返回索引的对局数。
    """
    collection = _get_collection()

    # 检查是否已索引过对局
    existing = collection.get(where={"type": "game_opening"}, limit=1)
    if existing and existing["ids"]:
        return 0  # 已索引过

    pgn_files = [
        _PROJECT_ROOT / "data" / "init_data" / "dpxq-99813games.pgns",
        _PROJECT_ROOT / "data" / "init_data" / "WXF-41743games.pgns",
    ]

    documents = []
    metadatas = []
    ids = []
    game_count = 0

    for pgn_path in pgn_files:
        if not pgn_path.exists():
            continue

        with open(pgn_path, "r", encoding="utf-8", errors="replace") as f:
            current_headers = {}
            moves_lines = []
            in_moves = False

            for line in f:
                line = line.strip()
                if not line:
                    if in_moves and moves_lines:
                        # 完成一局
                        doc, meta = _build_game_doc(current_headers, moves_lines)
                        if doc:
                            documents.append(doc)
                            metadatas.append(meta)
                            ids.append(f"game_{game_count}")
                            game_count += 1

                            if game_count >= max_games:
                                break

                        current_headers = {}
                        moves_lines = []
                        in_moves = False
                    continue

                if line.startswith("["):
                    match = re.match(r'\[(\w+)\s+"(.*)"\]', line)
                    if match:
                        current_headers[match.group(1)] = match.group(2)
                else:
                    in_moves = True
                    moves_lines.append(line)

            # 最后一局
            if moves_lines and game_count < max_games:
                doc, meta = _build_game_doc(current_headers, moves_lines)
                if doc:
                    documents.append(doc)
                    metadatas.append(meta)
                    ids.append(f"game_{game_count}")
                    game_count += 1

        if game_count >= max_games:
            break

    if documents:
        # 分批插入（ChromaDB 单次限制）
        batch_size = 2000
        for i in range(0, len(documents), batch_size):
            end = min(i + batch_size, len(documents))
            collection.add(
                documents=documents[i:end],
                metadatas=metadatas[i:end],
                ids=ids[i:end],
            )

    return game_count


def _build_game_doc(headers: dict, moves_lines: list):
    """从对局 headers 和走法构建检索文档，只取前 8 步（开局）"""
    event = headers.get("Event", "未知赛事")
    red = headers.get("Red", "未知")
    black = headers.get("Black", "未知")
    result = headers.get("Result", "*")
    date = headers.get("Date", "")

    # 只取前8步（16半步）作为开局摘要
    all_moves = " ".join(moves_lines)
    # 提取前 8 回合
    move_tokens = all_moves.split()[:24]  # 足够包含 8 回合
    opening_moves = " ".join(move_tokens[:16])

    if not opening_moves:
        return None, None

    # 构建检索文档
    result_text = {"1-0": "红胜", "0-1": "黑胜", "1/2-1/2": "和棋"}.get(result, result)
    doc = f"{event} {red}(红) vs {black}(黑) {result_text} 开局：{opening_moves}"

    meta = {
        "type": "game_opening",
        "source": f"{event}",
        "red": red,
        "black": black,
        "result": result,
        "date": date,
        "opening_moves": opening_moves[:200],
    }

    return doc, meta


class ChromaRAG(BaseRAG):
    """
    基于 ChromaDB 的真实 RAG 检索

    自动索引 80+ 棋理原则；可选索引 14 万局棋谱开局。
    """

    def __init__(self):
        self._collection = _get_collection()

    def retrieve(self, query: str, top_k: int = 5) -> List[RAGResult]:
        """
        语义检索：根据查询返回最相关的棋理/棋谱片段。

        Args:
            query: 自然语言查询（如"中炮开局攻势"、"马后炮杀法"）
            top_k: 返回数量

        Returns:
            List[RAGResult]: 按相关性排序的检索结果
        """
        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        rag_results = []
        if results and results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            dists = results["distances"][0] if results["distances"] else [0.5] * len(docs)

            for doc, meta, dist in zip(docs, metas, dists):
                # ChromaDB cosine distance → relevance score
                relevance = max(0.0, 1.0 - dist)
                source = meta.get("source", "象棋知识库")
                rag_results.append(RAGResult(
                    book_name=source,
                    content=doc,
                    relevance=round(relevance, 3),
                ))

        return rag_results

    def retrieve_by_phase(self, query: str, phase: str, top_k: int = 5) -> List[RAGResult]:
        """按阶段过滤检索"""
        where_filter = {"phase": phase} if phase in ("opening", "middlegame", "endgame") else None

        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
        )

        rag_results = []
        if results and results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            dists = results["distances"][0] if results["distances"] else [0.5] * len(docs)

            for doc, meta, dist in zip(docs, metas, dists):
                relevance = max(0.0, 1.0 - dist)
                source = meta.get("source", "象棋知识库")
                rag_results.append(RAGResult(
                    book_name=source,
                    content=doc,
                    relevance=round(relevance, 3),
                ))

        return rag_results

    def retrieve_by_type(self, query: str, doc_type: str, top_k: int = 5) -> List[RAGResult]:
        """按文档类型过滤检索（principle / game_opening）"""
        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"type": doc_type},
        )

        rag_results = []
        if results and results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            dists = results["distances"][0] if results["distances"] else [0.5] * len(docs)

            for doc, meta, dist in zip(docs, metas, dists):
                relevance = max(0.0, 1.0 - dist)
                source = meta.get("source", "象棋知识库")
                rag_results.append(RAGResult(
                    book_name=source,
                    content=doc,
                    relevance=round(relevance, 3),
                ))

        return rag_results


__all__ = ["ChromaRAG", "index_game_openings"]
