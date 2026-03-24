from pathlib import Path
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# 1. 页面基础设置
# =========================================================
st.set_page_config(
    page_title="店铺经营表现分析",
    layout="wide"
)

st.title("店铺经营表现分析")


# =========================================================
# 2. 数据文件路径
# =========================================================
DATA_FILE = Path(__file__).parent / "data" / "shiny_data.xlsx"


# =========================================================
# 3. 读取数据
# =========================================================
@st.cache_data
def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"未找到数据文件: {DATA_FILE}")

    merge_data = pd.read_excel(DATA_FILE, sheet_name="merge_data")
    target_shop_month_output_wide = pd.read_excel(
        DATA_FILE,
        sheet_name="target_shop_month_output_wide"
    )
    target_freq_data = pd.read_excel(
        DATA_FILE,
        sheet_name="target_频次信息_data"
    )

    return merge_data, target_shop_month_output_wide, target_freq_data


# =========================================================
# 4. 格式化函数
# =========================================================
def fmt_num(x, digits=2):
    if pd.isna(x):
        return "-"
    return f"{float(x):.{digits}f}"


def fmt_pct(x, digits=2):
    if pd.isna(x):
        return "-"
    return f"{float(x) * 100:.{digits}f}%"


def fmt_yuan(x, digits=2):
    if pd.isna(x):
        return "-"
    return f"¥{float(x):.{digits}f}"


def fmt_text(x):
    if pd.isna(x):
        return "-"
    value = str(x).strip()
    return value if value else "-"


def extract_month_num(text):
    match = re.search(r"(\d+)月", str(text))
    if match:
        return int(match.group(1))
    return None


# =========================================================
# 5. 图表函数：收入分层
# =========================================================
def make_income_layer_plot(df_income_wide: pd.DataFrame, selected_store: str):
    df = df_income_wide[df_income_wide["店铺"].astype(str) == str(selected_store)].copy()

    if df.empty:
        return None

    df = df.melt(
        id_vars=["店铺"],
        var_name="name",
        value_name="数值"
    )

    df["月份"] = df["name"].astype(str).str.extract(r"^(\d+月)")
    df["分层"] = (
        df["name"]
        .astype(str)
        .str.replace(r"^\d+月", "", regex=True)
        .str.strip()
    )
    df["月份数值"] = df["月份"].apply(extract_month_num)
    df["数值"] = pd.to_numeric(df["数值"], errors="coerce").round(2)

    df = df.dropna(subset=["月份数值", "数值"])

    if df.empty:
        return None

    month_order = [f"{i}月" for i in range(12, 0, -1)]
    layer_order = [
        "0-25%的机器",
        "25%-50%的机器",
        "50%-75%的机器",
        "75%-100%的机器"
    ]

    df["月份"] = pd.Categorical(df["月份"], categories=month_order, ordered=True)
    df["分层"] = pd.Categorical(df["分层"], categories=layer_order, ordered=True)
    df = df.sort_values(["月份数值", "分层"], ascending=[False, True])

    color_map = {
        "0-25%的机器": "#6395a5",
        "25%-50%的机器": "#00a8ed",
        "50%-75%的机器": "#153ded",
        "75%-100%的机器": "#051c2c"
    }

    fig = go.Figure()

    for layer in layer_order:
        sub = df[df["分层"] == layer].copy()
        if sub.empty:
            continue

        fig.add_trace(
            go.Bar(
                x=sub["数值"],
                y=sub["月份"],
                name=layer,
                orientation="h",
                marker=dict(color=color_map[layer]),
                text=[f"{v:.2f}" for v in sub["数值"]],
                textposition="outside",
                hovertemplate=(
                    "月份: %{y}<br>"
                    "分层: %{fullData.name}<br>"
                    "数值: %{x:.2f}<extra></extra>"
                )
            )
        )

    fig.update_layout(
        barmode="group",
        height=900,
        xaxis=dict(
            title="数值",
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            title="",
            categoryorder="array",
            categoryarray=month_order
        ),
        margin=dict(t=40, b=40, l=10, r=30),
        legend=dict(
            orientation="h",
            x=0.5,
            y=1.10,
            xanchor="center"
        )
    )

    return fig


# =========================================================
# 6. 图表函数：频次
# =========================================================
def make_freq_plot(df_freq_wide: pd.DataFrame, selected_store: str):
    df = df_freq_wide[df_freq_wide["店铺"].astype(str) == str(selected_store)].copy()

    if df.empty:
        return None

    df = df.melt(
        id_vars=["店铺"],
        var_name="name",
        value_name="数值"
    )

    df["月份"] = df["name"].astype(str).str.extract(r"^(\d+月)")
    df["月份数值"] = df["月份"].apply(extract_month_num)

    def parse_metric(name):
        text = str(name)
        if "TOP25%机器频次均值" in text:
            return "TOP25%机器频次均值"
        if "频次均值" in text:
            return "全店频次均值"
        return None

    df["指标"] = df["name"].apply(parse_metric)
    df["数值"] = pd.to_numeric(df["数值"], errors="coerce").round(2)

    df = df.dropna(subset=["月份数值", "指标", "数值"])

    if df.empty:
        return None

    month_order = [f"{i}月" for i in range(12, 0, -1)]
    metric_order = ["TOP25%机器频次均值", "全店频次均值"]

    df["月份"] = pd.Categorical(df["月份"], categories=month_order, ordered=True)
    df["指标"] = pd.Categorical(df["指标"], categories=metric_order, ordered=True)
    df = df.sort_values(["月份数值", "指标"], ascending=[False, True])

    color_map = {
        "TOP25%机器频次均值": "#051c2c",
        "全店频次均值": "#00a8ed"
    }

    fig = go.Figure()

    for metric in metric_order:
        sub = df[df["指标"] == metric].copy()
        if sub.empty:
            continue

        fig.add_trace(
            go.Bar(
                x=sub["数值"],
                y=sub["月份"],
                name=metric,
                orientation="h",
                marker=dict(color=color_map[metric]),
                text=[f"{v:.2f}" for v in sub["数值"]],
                textposition="outside",
                hovertemplate=(
                    "月份: %{y}<br>"
                    "指标: %{fullData.name}<br>"
                    "数值: %{x:.2f}<extra></extra>"
                )
            )
        )

    fig.update_layout(
        barmode="group",
        height=620,
        xaxis=dict(
            title="频次",
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            title="",
            categoryorder="array",
            categoryarray=month_order
        ),
        margin=dict(t=40, b=40, l=10, r=30),
        legend=dict(
            orientation="h",
            x=0.5,
            y=1.10,
            xanchor="center"
        )
    )

    return fig


# =========================================================
# 7. 主程序
# =========================================================
try:
    merge_data, income_data, freq_data = load_data()
except Exception as e:
    st.error(f"数据加载失败：{e}")
    st.stop()

if "店铺" not in merge_data.columns:
    st.error("merge_data 中缺少列：店铺")
    st.stop()

store_list = (
    merge_data["店铺"]
    .dropna()
    .astype(str)
    .drop_duplicates()
    .tolist()
)

if len(store_list) == 0:
    st.error("没有可选店铺，请检查数据。")
    st.stop()

selected_store = st.selectbox(
    "请选择店铺",
    options=store_list,
    index=0
)

shop_df = merge_data[merge_data["店铺"].astype(str) == str(selected_store)].copy()

if shop_df.empty:
    st.warning("当前店铺没有匹配数据。")
    st.stop()

row = shop_df.iloc[0]


# =========================================================
# 8. 基础信息展示
# =========================================================
st.subheader(f"{selected_store}｜经营画像")

st.markdown("### 基础信息")
col1, col2, col3, col4 = st.columns(4)
col1.metric("城市", fmt_text(row.get("城市")))
col2.metric("办学层次", fmt_text(row.get("办学层次")))
col3.metric("定价", fmt_text(row.get("定价")))
col4.metric("万化收入", fmt_yuan(row.get("万化收入"), 2))

st.markdown("### 用户信息")
col1, col2, col3 = st.columns(3)
col1.metric("服务人数", fmt_num(row.get("服务人数"), 0))
col2.metric("稳定月活跃用户", fmt_num(row.get("稳定月活跃用户"), 0))
col3.metric("月活跃率", fmt_pct(row.get("月活跃率"), 0))

st.markdown("### 机器信息")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("机器数量", fmt_num(row.get("机器数量"), 0))
col2.metric("机器月收入均值", fmt_yuan(row.get("机器月收入均值"), 2))
col3.metric("机器月均频次", fmt_num(row.get("机器月均频次"), 2))
col4.metric("Top25%机器月收入", fmt_yuan(row.get("top25%机器月收入"), 2))
col5.metric("TOP25%机器频次均值", fmt_num(row.get("TOP25%机器频次均值"), 2))

st.divider()


# =========================================================
# 9. 图表展示
# =========================================================
st.subheader("机器收入分层月度表现")
income_fig = make_income_layer_plot(income_data, selected_store)
if income_fig is None:
    st.info("当前店铺暂无收入分层数据。")
else:
    st.plotly_chart(income_fig, use_container_width=True)

st.divider()

st.subheader("机器频次月度表现")
freq_fig = make_freq_plot(freq_data, selected_store)
if freq_fig is None:
    st.info("当前店铺暂无频次数据。")
else:
    st.plotly_chart(freq_fig, use_container_width=True)