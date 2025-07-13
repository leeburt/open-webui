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
        query = "SELECT * FROM chat"
        df = pd.read_sql_query(query, engine)
        
        logger.info(f"成功读取chat表数据，共 {len(df)} 条记录")
        return df
        
    except Exception as e:
        logger.error(f"读取chat表数据时出错: {str(e)}")
        raise

if __name__ == "__main__":
    # 数据库文件路径
    db_path = "../backend/data/webui.db"
    
    # 获取数据
    chat_df = get_chat_data(db_path)
    
    # 显示数据基本信息
    print("\n数据基本信息:")
    print(chat_df.info())
    
    # 显示前几行数据
    print("\n数据预览:")
    print(chat_df.head())
    
    # 显示数据统计信息
    print("\n数据统计信息:")
    print(chat_df.describe()) 

    ## 保存为csv文件
    chat_df.to_csv("chat_data.csv", index=False)
