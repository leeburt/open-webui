from sqlalchemy import create_engine
import pandas as pd
import logging
from pathlib import Path

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
            select b.name,a.*
                from (
                SELECT * from chat  
                where meta!='{}') a 
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
    chat_data=[]
    import json
    import datetime 
    ## s时间戳转时间
    def timestamp_to_datetime(timestamp):
        return datetime.datetime.fromtimestamp(timestamp)

    for i,r in chat_df.iterrows():
        chat_=json.loads(r['chat'])
        user_id=r['user_id']
        user_name = r['name']
        chat_created_at=timestamp_to_datetime(r['created_at'])
        chat_updated_at=timestamp_to_datetime(r['updated_at'])
    
        if user_name in ['dali','cz',' cz','xuchengba']:
            continue

        chat_model=chat_.get("models",[])
        chat_title = chat_.get("title",None)
        chat_id= chat_.get("id",None)

        for history in chat_.get("history",{}).items():
            if history=={}:
                continue
            if history[0]=="messages":
                for id,hist in history[1].items():
                    chat_data.append({
                        "chat_id":chat_id,
                        "chat_user_id":user_id,
                        "chat_title":chat_title,
                        "chat_model":chat_model,
                        "last_chat_model":chat_model[-1],
                        "chat_created_at":chat_created_at,
                        "chat_updated_at":chat_updated_at,
                        "user_name":user_name,
                        "role":hist.get("role"),
                        "model":hist.get("model"),
                        "models":hist.get("models"),
                        "message_id":id,
                        "parentId":hist.get("parentId"),
                        "last_child_id":hist.get("childrenIds",[])[-1] if hist.get("childrenIds",[]) else 0,
                        "childrenIds": hist.get("childrenIds"),
                        "created_at": timestamp_to_datetime(hist.get("timestamp")) if hist.get("timestamp") else -1,
                        "content":hist.get("content")
                    })
                
        # chat_data.append(r['chat'])

    chat_data_pd=pd.DataFrame(chat_data)
    return chat_data_pd

def get_show_data(chat_data_pd):
    """
    获取展示数据
    """
    ## 获取所有的query
    chat_data_pd_query=chat_data_pd[chat_data_pd.role=="user"]

    ## 获取所有的回答
    chat_data_pd_respond=chat_data_pd[chat_data_pd.role=="assistant"]
    chat_data_pd_respond.info()


    show_respond_data = chat_data_pd_respond.drop(columns=['message_id'])
    show_respond_data.rename(columns={"content":"respond_content","parentId":"message_id"},inplace=True)

    chat_show_data=chat_data_pd_query.merge(show_respond_data[["message_id","respond_content"]],on = 'message_id')
    chat_show_data.reset_index(drop=True,inplace=True)
    # chat_show_data.info(verbose=False)

    return chat_show_data

    

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
    chat_show_data.to_csv("chat_show_data.csv",index=False,encoding="utf-8-sig")


