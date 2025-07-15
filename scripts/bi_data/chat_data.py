from sqlalchemy import create_engine
import pandas as pd
import logging
from pathlib import Path
import json
import datetime

from db_utils import get_db_engine, query_db

# 只获取logger实例，不进行配置
logger = logging.getLogger(__name__)

def _fetch_raw_chat_data(engine) -> pd.DataFrame:
    """
    从数据库中获取原始聊天数据。
    """
    query = """
        SELECT b.name, a.*
        FROM (
            SELECT * FROM chat WHERE meta != '{}'
        ) a
        LEFT JOIN (
            SELECT id, name FROM user
        ) b ON a.user_id = b.id;
    """
    df = query_db(query, engine)
    logger.info(f"成功读取chat表数据，共 {len(df)} 条记录")
    return df

def _parse_chat_messages(chat_df: pd.DataFrame) -> pd.DataFrame:
    """
    解析原始聊天DataFrame，提取消息级别的数据。
    """
    chat_data = []
    
    def timestamp_to_datetime(timestamp):
        if timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(timestamp)

    for _, r in chat_df.iterrows():
        try:
            chat_ = json.loads(r['chat'])
            user_id = r['user_id']
            user_name = r.get('name')
            
            if user_name in ['dali', 'cz', ' cz', 'xuchengba']:
                continue

            chat_model = chat_.get("models", [])
            chat_title = chat_.get("title")
            chat_id = chat_.get("id")

            for msg_id, hist in chat_.get("history", {}).get("messages", {}).items():
                chat_data.append({
                    "chat_id": chat_id,
                    "chat_user_id": user_id,
                    "chat_title": chat_title,
                    "chat_model": chat_model,
                    "last_chat_model": chat_model[-1] if chat_model else None,
                    "chat_created_at": timestamp_to_datetime(r['created_at']),
                    "chat_updated_at": timestamp_to_datetime(r['updated_at']),
                    "user_name": user_name,
                    "role": hist.get("role"),
                    "model": hist.get("model"),
                    "models": hist.get("models"),
                    "message_id": msg_id,
                    "parentId": hist.get("parentId"),
                    "last_child_id": hist.get("childrenIds", [])[-1] if hist.get("childrenIds") else None,
                    "childrenIds": hist.get("childrenIds"),
                    "created_at": timestamp_to_datetime(hist.get("timestamp")),
                    "content": hist.get("content")
                })
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"解析chat记录时出错 (ID: {r.get('id', 'N/A')}): {e}")
            continue

    return pd.DataFrame(chat_data)

def _create_chat_view(chat_data_pd: pd.DataFrame) -> pd.DataFrame:
    """
    将用户问题和助手回答配对，创建用于展示的DataFrame。
    """
    if chat_data_pd.empty:
        return pd.DataFrame()

    queries = chat_data_pd[chat_data_pd.role == "user"].copy()
    responses = chat_data_pd[chat_data_pd.role == "assistant"].copy()
    
    # 准备用于合并的回答数据。我们只需要 parentId（作为连接键）和 content。
    # 我们还包括 created_at 时间戳，以便在有多个回答时选择最新的一个。
    responses_to_merge = responses[['parentId', 'content', 'created_at']].copy()
    responses_to_merge.rename(columns={
        'parentId': 'message_id', 
        'content': 'respond_content'
    }, inplace=True)

    # 如果一个问题有多个回答，只保留最新的一个。
    # 按时间降序排序，然后根据 message_id 删除重复项，保留第一个（即最新的）。
    responses_to_merge.sort_values('created_at', ascending=False, inplace=True)
    responses_to_merge.drop_duplicates(subset=['message_id'], keep='first', inplace=True)
    
    # on='message_id' 将会连接 queries.message_id 和 responses_to_merge.message_id (原 parentId)
    chat_show_data = queries.merge(
        responses_to_merge[['message_id', 'respond_content']], 
        on='message_id',
        how='left' # 使用left join保留所有问题，即使没有回答
    )
    
    chat_show_data.reset_index(drop=True, inplace=True)
    return chat_show_data

def get_chat_data(db_path: str) -> pd.DataFrame:
    """
    获取、解析并处理聊天数据，返回一个包含问答对的DataFrame。

    Args:
        db_path (str): 数据库文件的路径。

    Returns:
        pd.DataFrame: 处理后的聊天数据。
    """
    try:
        engine = get_db_engine(db_path)
        raw_df = _fetch_raw_chat_data(engine)
        parsed_df = _parse_chat_messages(raw_df)
        chat_view_df = _create_chat_view(parsed_df)
        return chat_view_df
    except Exception as e:
        logger.error(f"获取聊天数据时出错: {e}")
        # 在高级别函数中捕获异常，可以返回一个空的DataFrame或重新引发异常
        # 这里选择返回空DataFrame，使调用方代码更健壮
        return pd.DataFrame()
