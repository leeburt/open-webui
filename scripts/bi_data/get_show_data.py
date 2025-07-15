## 该函数功能
# 1. 获取chat表的所有数据
# 2. 获取feedback表的所有数据
# 3. 汇总数据：1）汇总所有数据的使用量和反馈量，不同模型的调用量和反馈量，汇总不同user使用量和反馈量，
#          2）然后按天进行汇总使用量和反馈量，按天进行汇总不同user使用量和反馈量
# 4. 保存数据为json格式
import pandas as pd
import json
import datetime
import logging
from pathlib import Path

# 从重构后的模块中导入函数
from chat_data import get_chat_data
from feedback_data import get_feedback_data

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s- %(funcName)s - %(lineno)d - %(levelname)s - %(message)s' # 统一为详细日志格式
)
logger = logging.getLogger(__name__)

def generate_summary_stats(chat_df: pd.DataFrame, feedback_df: pd.DataFrame) -> dict:
    """
    根据聊天和反馈数据生成汇总统计信息。

    Args:
        chat_df: 包含聊天数据的DataFrame。
        feedback_df: 包含反馈数据的DataFrame。

    Returns:
        dict: 包含所有汇总统计信息的多层字典。
    """
    summary = {}

    # 确保日期列是datetime类型，以便进行时间序列分析
    chat_df['chat_created_at'] = pd.to_datetime(chat_df['chat_created_at'], errors='coerce')
    feedback_df['created_at'] = pd.to_datetime(feedback_df['created_at'], errors='coerce')

    # 删除缺少关键信息的行
    chat_df.dropna(subset=['chat_created_at', 'user_name', 'last_chat_model'], inplace=True)
    feedback_df.dropna(subset=['created_at', 'user_name', 'model'], inplace=True)

    # 替换模型名称
    chat_df['last_chat_model'].replace('星伴V1.1', '聆镜 1.1', inplace=True)
    feedback_df['model'].replace('星伴V1.1', '聆镜 1.1', inplace=True)

    # 1. 总体统计
    summary['overall_stats'] = {
        'total_chats': int(chat_df['chat_id'].nunique()),
        'total_user_queries': len(chat_df),
        'total_feedbacks': len(feedback_df),
        'feedback_ratio': len(feedback_df) / len(chat_df) if len(chat_df) > 0 else 0,
    }

    # 2. 按模型统计
    model_usage = chat_df['last_chat_model'].value_counts().to_dict()
    model_feedback = feedback_df['model'].value_counts().to_dict()
    model_stats = {
        model: {
            'usage_count': model_usage.get(model, 0),
            'feedback_count': model_feedback.get(model, 0)
        } for model in set(model_usage) | set(model_feedback)
    }
    summary['model_stats'] = model_stats

    # 3. 按用户统计
    user_usage = chat_df['user_name'].value_counts().to_dict()
    user_feedback = feedback_df['user_name'].value_counts().to_dict()
    user_stats = {
        user: {
            'usage_count': user_usage.get(user, 0),
            'feedback_count': user_feedback.get(user, 0)
        } for user in set(user_usage) | set(user_feedback)
    }
    summary['user_stats'] = user_stats

    # 4. 按天统计
    daily_usage = chat_df.set_index('chat_created_at').resample('D').size().to_frame('count')
    daily_feedback = feedback_df.set_index('created_at').resample('D').size().to_frame('count')
    daily_stats = pd.merge(daily_usage, daily_feedback, left_index=True, right_index=True, how='outer').fillna(0)
    daily_stats.rename(columns={'count_x': 'usage_count', 'count_y': 'feedback_count'}, inplace=True)

    # 将浮点计数值转换为整数
    daily_stats = daily_stats.astype(int)

    # 将DatetimeIndex转换为字符串，以确保JSON序列化兼容性
    daily_stats.index = daily_stats.index.strftime('%Y-%m-%d')
    summary['daily_stats'] = daily_stats.to_dict('index')

    # 5. 按天和用户统计
    daily_user_usage = chat_df.groupby([pd.Grouper(key='chat_created_at', freq='D'), 'user_name']).size()
    daily_user_feedback = feedback_df.groupby([pd.Grouper(key='created_at', freq='D'), 'user_name']).size()
    
    daily_user_stats = {}
    for (date, user), count in daily_user_usage.items():
        date_str = date.strftime('%Y-%m-%d')
        if date_str not in daily_user_stats:
            daily_user_stats[date_str] = {}
        if user not in daily_user_stats[date_str]:
            daily_user_stats[date_str][user] = {'usage_count': 0, 'feedback_count': 0}
        daily_user_stats[date_str][user]['usage_count'] = int(count)

    for (date, user), count in daily_user_feedback.items():
        date_str = date.strftime('%Y-%m-%d')
        if date_str not in daily_user_stats:
            daily_user_stats[date_str] = {}
        if user not in daily_user_stats[date_str]:
            daily_user_stats[date_str][user] = {'usage_count': 0, 'feedback_count': 0}
        daily_user_stats[date_str][user]['feedback_count'] = int(count)
        
    summary['daily_user_stats'] = daily_user_stats
    
    return summary

def default_json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def save_all_data(chat_df,feedback_df):
    """
    保存所有数据
    """
    output_dir = Path(__file__).parent / "df_data"
    output_dir.mkdir(exist_ok=True)
    time_now=datetime.datetime.now().strftime("%Y-%m-%d")
    chat_df.to_csv(output_dir / f"{time_now}_chat_data.csv",index=False,encoding="utf-8-sig")
    feedback_df.to_csv(output_dir / f"{time_now}_feedback_data.csv",index=False,encoding="utf-8-sig")
    logger.info(f"明细数据成功保存到: {output_dir}")

if __name__ == "__main__":
    # 定义数据库路径
    db_path = "../../backend/data/webui.db"
    
    logger.info("开始获取和处理数据...")
    
    # 1. 获取聊天和反馈数据
    chat_df = get_chat_data(db_path)
    feedback_df = get_feedback_data(db_path)


    if chat_df.empty:
        logger.warning("聊天数据为空，无法生成统计信息。")
    else:
        # 2. 生成汇总统计
        logger.info("数据获取成功，开始生成汇总统计...")
        summary_data = generate_summary_stats(chat_df, feedback_df)
        
        # 可选：保存详细的DataFrame数据
        save_all_data(chat_df, feedback_df)

        # 3. 保存数据为JSON文件
        output_dir = Path(__file__).parent
        # 将统计文件也保存到 df_data 目录中
        output_data_dir = output_dir / "df_data"
        output_data_dir.mkdir(exist_ok=True)
        time_now = datetime.datetime.now().strftime("%Y-%m-%d")
        output_path = output_data_dir / f"{time_now}_summary_stats.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_json_serializer)
            logger.info(f"统计数据成功保存到: {output_path}")
        except Exception as e:
            logger.error(f"保存JSON文件时出错: {e}")