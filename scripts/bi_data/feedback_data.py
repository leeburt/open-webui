from sqlalchemy import create_engine
import pandas as pd
import logging
from pathlib import Path
import json
import datetime

from db_utils import get_db_engine, query_db

# 只获取logger实例，不进行配置
logger = logging.getLogger(__name__)

def _fetch_raw_feedback_data(engine) -> pd.DataFrame:
    """
    从数据库获取原始反馈数据。
    """
    query = """
        SELECT a.*, b.name
        FROM feedback a
        LEFT JOIN user b ON a.user_id = b.id;
    """
    df = query_db(query, engine)
    logger.info(f"成功读取feedback表数据，共 {len(df)} 条记录")
    return df

def _parse_feedback_entries(feedback_df: pd.DataFrame) -> pd.DataFrame:
    """
    解析原始反馈DataFrame，提取有用的字段。
    """
    feedback_data = []

    def timestamp_to_datetime(timestamp):
        if timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(timestamp)

    for _, r in feedback_df.iterrows():
        feedback_id = r['id']
        try:
            snapshot = json.loads(r['snapshot'])
            data = json.loads(r['data'])
            meta = json.loads(r['meta'])
            
            rating = data.get("rating")
            if rating == -1:
                rating_str = "bad"
            elif rating == 1:
                rating_str = "good"
            else:
                rating_str = "unknown"

            name = r.get('name')
            if name in ['dali', 'cz', ' cz']:
                continue

            message_id = meta.get("message_id")
            history_messages = snapshot.get('chat', {}).get('chat', {}).get('history', {}).get('messages', {})
            
            if not all([message_id, history_messages]):
                logger.warning(f"跳过 feedback_id: {feedback_id}，缺少 message_id 或 history_messages。")
                continue

            answer_info = history_messages.get(message_id)
            if not answer_info:
                logger.warning(f"跳过 feedback_id: {feedback_id}，在 history 中找不到 message_id: {message_id}。")
                continue
            
            parentId = answer_info.get('parentId')
            query_info = history_messages.get(parentId) if parentId else None
            
            feedback_data.append({
                "feedback_id": feedback_id,
                "user_id": r['user_id'],
                "user_name": name,
                "good_or_bad": rating_str,
                "rating_score": data.get("details", {}).get("rating", -99),
                "rating_comment": data.get("comment", ""),
                "query": query_info.get('content') if query_info else None,
                "answer": answer_info.get('content'),
                "model": answer_info.get('model'),
                "message_id": message_id,
                "parentId": parentId,
                "created_at": timestamp_to_datetime(answer_info.get("timestamp")),
            })

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"解析 feedback_id: {feedback_id} 时出错: {e}", exc_info=True)
            continue

    return pd.DataFrame(feedback_data)

def get_feedback_data(db_path: str) -> pd.DataFrame:
    """
    获取、解析并处理用户反馈数据。

    Args:
        db_path (str): 数据库文件的路径。

    Returns:
        pd.DataFrame: 包含已解析反馈数据的DataFrame。
    """
    try:
        engine = get_db_engine(db_path)
        raw_df = _fetch_raw_feedback_data(engine)
        parsed_df = _parse_feedback_entries(raw_df)
        return parsed_df
    except Exception as e:
        logger.error(f"获取反馈数据时出错: {e}")
        return pd.DataFrame()
