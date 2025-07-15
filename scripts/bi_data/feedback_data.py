from sqlalchemy import create_engine
import pandas as pd
import logging
from pathlib import Path
import json
import datetime 

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_chat_data(db_path):
    """
    获取chat表的所有数据并转换为DataFrame
    
    Args:
        db_path (str): 数据库文件路径
    
    Returns:
        pd.DataFrame: 包含chat表数据的DataFrame
    """
    try:
        # 创建数据库连接
        engine = create_engine(f'sqlite:///{db_path}')
        
        # 读取chat表数据
        query = """
            select a.*,b.name
            from (
            SELECT * from feedback) a 
            left join (
            select id,name from user 
            ) b
            on a.user_id=b.id;
        """
        df = pd.read_sql_query(query, engine)
        
        logger.info(f"成功读取chat表数据，共 {len(df)} 条记录")
        return df
        
    except Exception as e:
        logger.error(f"读取chat表数据时出错: {str(e)}")
        raise

def parse_chat_data(chat_df):
    """
    解析chat表数据
    """


    ## s时间戳转时间
    def timestamp_to_datetime(timestamp):
        return datetime.datetime.fromtimestamp(timestamp)

    import traceback
    feedback_data=[]
    import json
    for i,r in chat_df.iterrows():
        feedback_id = r['id']
        snapshot = json.loads(r['snapshot'])
        data=json.loads(r['data'])
        rating = data.get("rating",-99)
        rating_score = data.get("details",{}).get("rating",-99)
        rating_comment = data.get("comment","")
        
        if rating == -1:
            rating = "bad"
        elif rating == 1:
            rating = "good"
        else:
            rating = "unknown"

        name= r['name']
        user_id=r['user_id']
        meta=json.loads(r['meta'])
        message_id = meta.get("message_id")
        
        history = snapshot['chat']['chat']['history']
        try:
            history_messages = history['messages']
            query_info = history_messages[message_id]
            parentId = query_info['parentId']
            query = history_messages[parentId]
        except:
            print(traceback.format_exc())
            print(parentId)
            print(message_id)
            print(history)
            with open(f"bad_data/tmp_feedback_meta_{feedback_id}.json","w") as f:
                bad_data={
                    "traceback":str(traceback.format_exc()),
                    "message_id":message_id,
                    "parentId":parentId,
                    "snapshot":snapshot
                }
                json.dump(bad_data,f,ensure_ascii=False,indent=4)
            continue

        if name in ['dali','cz',' cz']:
            continue
        # history = snapshot.get("history",{})
        feedback_data.append({
            "feedback_id":feedback_id,
            "user_id":user_id,
            "user_name":name,
            "goog_or_bad":rating,
            "rating_score":rating_score,
            "rating_comment":rating_comment,
            
            "query":query,
            "answer":query_info['content'],
            "model":query_info['model'],

            "role":query_info.get("role"),
            "message_id":message_id,
            "parentId":query_info.get("parentId"),
            "last_child_id":query_info.get("childrenIds",[])[-1] if history.get("childrenIds",[]) else 0,
            "childrenIds":query_info.get("childrenIds"),
            "created_at":timestamp_to_datetime(query_info.get("timestamp")) if query_info.get("timestamp") else -1,

            "meta":meta,
            "data":data,
            "snapshot":snapshot
        })


    chat_data_pd=pd.DataFrame(feedback_data)
    return chat_data_pd

def get_show_data(chat_data_pd):
    """
    获取展示数据
    """
    ## 获取所有的query
    chat_data_score=chat_data_pd[chat_data_pd.rating_score>0]
    chat_data_score.reset_index(drop=True,inplace=True)

    return chat_data_score

    

if __name__ == "__main__":
    # 数据库文件路径
    db_path = "../../backend/data/webui.db"
    # 获取数据
    chat_df = get_chat_data(db_path)
    # 解析数据
    chat_data_pd = parse_chat_data(chat_df)
    chat_show_data = get_show_data(chat_data_pd)

    chat_show_data.info()
    # 保存数据
    chat_show_data.to_csv("feedback_data.csv",index=False,encoding="utf-8-sig")
    print(chat_show_data.head())
