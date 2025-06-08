from sqlalchemy import inspect
from sqlalchemy import create_engine
import pandas as pd
import os
from pathlib import Path
from tqdm import tqdm
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def export_tables_to_csv(db_path, output_dir='db_exports'):
    """
    将SQLite数据库中的所有表导出为CSV文件
    
    Args:
        db_path (str): 数据库文件路径
        output_dir (str): 输出目录名称
    """
    try:
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 创建数据库连接
        engine = create_engine(f'sqlite:///{db_path}')
        inspector = inspect(engine)
        
        # 获取所有表名
        tables = inspector.get_table_names()
        logger.info(f"找到 {len(tables)} 个表")
        
        # 使用tqdm显示进度
        for table in tqdm(tables, desc="导出表"):
            try:
                # 读取表数据
                df = pd.read_sql_table(table, engine)
                
                # 生成带时间戳的文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = output_path / f"{table}_{timestamp}.csv"
                
                # 导出到CSV
                df.to_csv(output_file, index=False, encoding='utf-8')
                logger.info(f"成功导出表 {table} 到 {output_file}")
                
            except Exception as e:
                logger.error(f"导出表 {table} 时出错: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"处理数据库时出错: {str(e)}")
        raise

if __name__ == "__main__":
    db_path = "../backend/data/webui.db"
    export_tables_to_csv(db_path) 