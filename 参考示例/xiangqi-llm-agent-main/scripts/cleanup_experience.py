"""
清理经验池脚本
删除低质量或过时的经验数据
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.store import ExperienceStore

logger = logging.getLogger(__name__)


def main(args):
    """主函数"""
    logger.info("=" * 60)
    logger.info("清理经验池")
    logger.info("=" * 60)
    
    store = ExperienceStore()
    
    # 查询需要删除的经验
    conditions = []
    params = []
    
    if args.min_visits:
        conditions.append("visit_count < ?")
        params.append(args.min_visits)
    
    if args.min_win_rate is not None:
        conditions.append("win_rate < ?")
        params.append(args.min_win_rate)
    
    if not conditions:
        logger.warning("未指定清理条件，请使用 --min-visits 或 --min-win-rate")
        return
    
    where_clause = " AND ".join(conditions)
    
    # 查询
    cursor = store.db.conn.cursor()
    sql = f"SELECT COUNT(*) FROM experiences WHERE {where_clause}"
    cursor.execute(sql, params)
    count = cursor.fetchone()[0]
    
    logger.info(f"找到 {count} 条需要删除的经验")
    
    if args.dry_run:
        logger.info("（仅显示，不删除）")
        # 显示一些示例
        sql = f"SELECT * FROM experiences WHERE {where_clause} LIMIT 10"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        for row in rows:
            logger.info(f"  - ID: {row['id']}, 访问: {row['visit_count']}, 胜率: {row['win_rate']:.2f}")
        return
    
    # 确认
    response = input(f"确认删除 {count} 条经验? (yes/no): ")
    if response.lower() != 'yes':
        logger.info("已取消")
        return
    
    # 删除
    sql = f"DELETE FROM experiences WHERE {where_clause}"
    cursor.execute(sql, params)
    store.db.conn.commit()
    
    deleted = cursor.rowcount
    logger.info(f"已删除 {deleted} 条经验")
    
    # 优化数据库
    logger.info("优化数据库...")
    store.db.vacuum()
    logger.info("完成")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="清理经验池")
    parser.add_argument('--min-visits', type=int, help='最小访问次数')
    parser.add_argument('--min-win-rate', type=float, help='最小胜率')
    parser.add_argument('--dry-run', action='store_true', help='仅显示，不删除')
    
    args = parser.parse_args()
    main(args)

