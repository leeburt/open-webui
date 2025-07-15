from sqlalchemy import create_engine, text
import pandas as pd
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_engine(db_path: str):
    """
    创建并返回一个SQLAlchemy引擎。

    Args:
        db_path (str): SQLite数据库文件的路径。

    Returns:
        sqlalchemy.engine.Engine: 数据库引擎。
    
    Raises:
        Exception: 如果创建引擎失败。
    """
    try:
        if not Path(db_path).exists():
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
        engine = create_engine(f'sqlite:///{db_path}')
        logger.info("数据库引擎创建成功。")
        return engine
    except Exception as e:
        logger.error(f"为 {db_path} 创建数据库引擎失败: {e}")
        raise

def query_db(query: str, engine) -> pd.DataFrame:
    """
    执行SQL查询并以pandas DataFrame的形式返回结果。

    Args:
        query (str): 要执行的SQL查询。
        engine: 要使用的SQLAlchemy引擎。

    Returns:
        pd.DataFrame: 包含查询结果的DataFrame。
        
    Raises:
        Exception: 如果查询执行失败。
    """
    try:
        df = pd.read_sql_query(sql=text(query), con=engine)
        logger.info(f"查询成功执行，返回 {len(df)} 行。")
        return df
    except Exception as e:
        logger.error(f"查询执行失败: {e}")
        raise
