import streamlit as st
import pandas as pd
import json
from pathlib import Path
import plotly.express as px
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(
    page_title="聆镜BI数据看板",
    page_icon="📊",
    layout="wide"
)

# --- 数据加载与处理 ---
def load_data(file_path):
    """
    加载并预处理JSON统计数据。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error(f"错误：找不到数据文件。请确保 '{file_path}' 存在。")
        return None

@st.cache_data
def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    """
    将DataFrame转换为UTF-8编码的CSV字节流，并缓存结果。
    """
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

def process_daily_stats(daily_stats_dict):
    """将每日统计字典转换为格式正确的DataFrame。"""
    if not daily_stats_dict:
        return pd.DataFrame(columns=['date', 'usage_count', 'feedback_count'])
    df = pd.DataFrame.from_dict(daily_stats_dict, orient='index')
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df.reset_index() # 重置索引，使date成为普通列

def process_dict_to_df(data_dict, index_name="name"):
    """通用函数，将字典转换为DataFrame，并将索引重置为列。"""
    if not data_dict:
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(data_dict, orient='index')
    df.index.name = index_name
    return df.reset_index()

# --- 主函数 ---
def main():
    st.title("📊 聆镜数据BI看板")
    st.caption("展示用户聊天、反馈和模型使用情况的交互式仪表盘。")

    # 找到最新的统计文件
    data_dir = Path(__file__).parent / "df_data"
    list_of_files = list(data_dir.glob('*_summary_stats.json'))
    if not list_of_files:
        st.error("在当前目录下找不到任何 `_summary_stats.json` 文件。")
        st.stop()
    
    latest_file = max(list_of_files, key=lambda p: p.stat().st_mtime)
    
    data = load_data(latest_file)
    if not data:
        st.stop()

    # --- 数据预处理 ---
    overall_stats = data.get('overall_stats', {})
    daily_df = process_daily_stats(data.get('daily_stats', {}))
    model_df = process_dict_to_df(data.get('model_stats', {}), "model")
    user_df = process_dict_to_df(data.get('user_stats', {}), "user")

    # --- 页面主体 ---
    
    # 1. 关键指标 (KPIs)
    st.header("整体概览")
    col1, col2= st.columns(2)

    with col1:
        st.metric(label="总提问数", value=f"{overall_stats.get('total_user_queries', 0):,}")
    with col2:
        st.metric(label="总反馈数", value=f"{overall_stats.get('total_feedbacks', 0):,}")


    st.markdown("---")

    # 2. 每日趋势
    st.header("每日使用与反馈趋势")
    
    if not daily_df.empty:
        min_date = daily_df['date'].min().date()
        max_date = daily_df['date'].max().date()
        daily_df.sort_values(by='date', ascending=False, inplace=True)
        date_range = st.date_input(
            "选择日期范围",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="daily_date_range",
            help="选择一个时间段来分析趋势。"
        )
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_daily_df = daily_df[(daily_df['date'].dt.date >= start_date) & (daily_df['date'].dt.date <= end_date)]

            fig_daily = px.line(
                filtered_daily_df, x='date', y=['usage_count', 'feedback_count'],
                labels={'value': '数量', 'date': '日期', 'variable': '指标'},
                template="plotly_white"
            )
            fig_daily.update_layout(legend_title_text='', title_text="每日提问量 vs 反馈量", title_x=0.5)
            st.plotly_chart(fig_daily, use_container_width=True)


            with st.expander("查看每日趋势明细数据"):
                st.dataframe(filtered_daily_df.style.format({'usage_count': '{:,}', 'feedback_count': '{:,}'}))
                csv_daily = convert_df_to_csv(filtered_daily_df)
                st.download_button(
                    label="下载每日趋势数据 (CSV)",
                    data=csv_daily,
                    file_name=f'daily_trend_{start_date}_to_{end_date}.csv',
                    mime='text/csv',
                )
    else:
        st.warning("没有可供分析的每日数据。")

    st.markdown("---")

    # 3. 模型使用情况分析
    st.header("模型使用情况分析")
    if not model_df.empty:
        df_to_plot_model = model_df.sort_values('usage_count', ascending=False)
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            fig_model = px.bar(
                df_to_plot_model,
                x='model',
                y=['usage_count', 'feedback_count'],
                barmode='group',
                labels={'value': '数量', 'model': '模型', 'variable': '指标'},
                template="plotly_white",
                text_auto=True
            )
            fig_model.update_layout(legend_title_text='', xaxis_title=None, title_text="各模型提问量 vs 反馈量", title_x=0.5)
            fig_model.update_traces(textposition='outside')
            st.plotly_chart(fig_model, use_container_width=True)
            
        with col2:
            st.markdown("##### 数据明细")
            st.dataframe(
                df_to_plot_model.style.format({'usage_count': '{:,}', 'feedback_count': '{:,}'}),
                use_container_width=True
            )
            csv_model = convert_df_to_csv(df_to_plot_model)
            time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="下载模型使用反馈数据(CSV)",
                data=csv_model,
                file_name=f'model_stats_data_{time_str}.csv',
                mime='text/csv',
            )
    else:
        st.info("没有模型统计数据。")

    st.markdown("---")

    # 4. 用户使用情况分析
    st.header("用户使用情况分析")
    
    if not user_df.empty:
        user_list = sorted(user_df['user'].unique())
        selected_users = st.multiselect(
            "选择用户 (留空以显示Top 20高频用户)",
            options=user_list, default=None,
            placeholder="选择一个或多个用户进行分析"
        )
        
        if selected_users:
            df_to_plot = user_df[user_df['user'].isin(selected_users)].copy()
            title_text = "所选用户提问量 vs 反馈量"
        else:
            df_to_plot = user_df.sort_values('usage_count', ascending=False).head(20)
            title_text = "Top 20 高频用户提问量 vs 反馈量"

        df_to_plot.sort_values('usage_count', ascending=True, inplace=True)
        
        fig_user = px.bar(
            df_to_plot, y='user', x=['usage_count', 'feedback_count'],
            orientation='h', barmode='group',
            labels={'value': '数量', 'user': '用户', 'variable': '指标'},
            template="plotly_white",
            height=max(400, len(df_to_plot) * 40), text_auto=True
        )
        fig_user.update_layout(legend_title_text='', yaxis_title=None, title_text=title_text, title_x=0.5)
        fig_user.update_traces(textposition='outside')
        st.plotly_chart(fig_user, use_container_width=True)
        
        with st.expander("查看用户统计明细数据"):
            display_df = df_to_plot.sort_values('usage_count', ascending=False)
            st.dataframe(display_df.style.format({'usage_count': '{:,}', 'feedback_count': '{:,}'}))
            
            csv_user = convert_df_to_csv(display_df)
            time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="下载用户使用数据(CSV)",
                data=csv_user,
                file_name=f'user_use_data_{time_str}.csv',
                mime='text/csv',
            )
    else:
        st.info("没有用户统计数据。")

    # # 5. 原始数据
    # with st.expander("查看原始JSON数据"):
    #     st.json(data)

if __name__ == "__main__":
    main()