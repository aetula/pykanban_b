from pathlib import Path
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
# 3. 格式化函数
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


# =========================================================
# 4. 读取原始数据（一次性读取多个 sheet）
# =========================================================
@st.cache_data(show_spinner=False)
def load_raw_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"未找到数据文件: {DATA_FILE}")

    sheets = pd.read_excel(
        DATA_FILE,
        sheet_name=[
            "merge_data",
            "target_shop_month_output_wide",
            "target_频次信息_data"
        ]
    )

    merge_data = sheets["merge_data"].copy()
    income_wide = sheets["target_shop_month_output_wide"].copy()
    freq_wide = sheets["target_频次信息_data"].copy()

    # 统一店铺字段类型，避免后续反复 astype(str)
    for df in [merge_data, income_wide, freq_wide]:
        if "店铺" in df.columns:
            df["店铺"] = df["店铺"].astype(str).str.strip()

    return merge_data, income_wide, freq_wide


# =========================================================
# 5. 预处理：基础信息表
# =========================================================
@st.cache_data(show_spinner=False)
def prepare_shop_base(merge_data: pd.DataFrame):
    if "店铺" not in merge_data.columns:
        raise ValueError("merge_data 中缺少列：店铺")

    df = merge_data.copy()
    df["店铺"] = df["店铺"].astype(str).str.strip()

    df = df.dropna(subset=["店铺"])
    df = df[df["店铺"] != ""]

    # 每个店铺只保留第一条记录
    shop_base = (
        df.drop_duplicates(subset=["店铺"], keep="first")
        .set_index("店铺", drop=False)
        .sort_index()
    )

    store_list = shop_base["店铺"].tolist()

    return shop_base, store_list


# =========================================================
# 6. 预处理：收入分层宽表 -> 长表
# =========================================================
@st.cache_data(show_spinner=False)
def prepare_income_long(income_wide: pd.DataFrame):
    if "店铺" not in income_wide.columns:
        return pd.DataFrame()

    df = income_wide.copy()
    df["店铺"] = df["店铺"].astype(str).str.strip()

    value_cols = [c for c in df.columns if c != "店铺"]
    if not value_cols:
        return pd.DataFrame()

    df = df.melt(
        id_vars=["店铺"],
        var_name="name",
        value_name="数值"
    )

    name_series = df["name"].astype(str)

    df["月份"] = name_series.str.extract(r"^(\d+月)", expand=False)
    df["分层"] = (
        name_series
        .str.replace(r"^\d+月", "", regex=True)
        .str.strip()
    )

    df["月份数值"] = pd.to_numeric(
        df["月份"].str.extract(r"(\d+)", expand=False),
        errors="coerce"
    )
    df["数值"] = pd.to_numeric(df["数值"], errors="coerce").round(2)

    layer_order = [
        "0-25%的机器",
        "25%-50%的机器",
        "50%-75%的机器",
        "75%-100%的机器"
    ]
    month_order = [f"{i}月" for i in range(12, 0, -1)]

    df = df.dropna(subset=["店铺", "月份", "月份数值", "数值"])
    df = df[df["分层"].isin(layer_order)]

    df["月份"] = pd.Categorical(df["月份"], categories=month_order, ordered=True)
    df["分层"] = pd.Categorical(df["分层"], categories=layer_order, ordered=True)

    df = df.sort_values(
        ["店铺", "月份数值", "分层"],
        ascending=[True, False, True]
    ).reset_index(drop=True)

    return df


# =========================================================
# 7. 预处理：频次宽表 -> 长表
# =========================================================
@st.cache_data(show_spinner=False)
def prepare_freq_long(freq_wide: pd.DataFrame):
    if "店铺" not in freq_wide.columns:
        return pd.DataFrame()

    df = freq_wide.copy()
    df["店铺"] = df["店铺"].astype(str).str.strip()

    value_cols = [c for c in df.columns if c != "店铺"]
    if not value_cols:
        return pd.DataFrame()

    df = df.melt(
        id_vars=["店铺"],
        var_name="name",
        value_name="数值"
    )

    name_series = df["name"].astype(str)

    df["月份"] = name_series.str.extract(r"^(\d+月)", expand=False)
    df["月份数值"] = pd.to_numeric(
        df["月份"].str.extract(r"(\d+)", expand=False),
        errors="coerce"
    )

    # 注意顺序：先判断 TOP25%，避免被“频次均值”提前匹配
    df["指标"] = pd.Series(pd.NA, index=df.index, dtype="object")
    df.loc[name_series.str.contains("TOP25%机器频次均值", na=False), "指标"] = "TOP25%机器频次均值"
    df.loc[
        name_series.str.contains("频次均值", na=False) &
        ~name_series.str.contains("TOP25%机器频次均值", na=False),
        "指标"
    ] = "全店频次均值"

    df["数值"] = pd.to_numeric(df["数值"], errors="coerce").round(2)

    month_order = [f"{i}月" for i in range(12, 0, -1)]
    metric_order = ["TOP25%机器频次均值", "全店频次均值"]

    df = df.dropna(subset=["店铺", "月份", "月份数值", "指标", "数值"])
    df = df[df["指标"].isin(metric_order)]

    df["月份"] = pd.Categorical(df["月份"], categories=month_order, ordered=True)
    df["指标"] = pd.Categorical(df["指标"], categories=metric_order, ordered=True)

    df = df.sort_values(
        ["店铺", "月份数值", "指标"],
        ascending=[True, False, True]
    ).reset_index(drop=True)

    return df


# =========================================================
# 8. 图表函数：收入分层
# =========================================================
def make_income_layer_plot(df_income_long: pd.DataFrame, selected_store: str):
    df = df_income_long[df_income_long["店铺"] == selected_store]

    if df.empty:
        return None

    layer_order = [
        "0-25%的机器",
        "25%-50%的机器",
        "50%-75%的机器",
        "75%-100%的机器"
    ]
    month_order = [f"{i}月" for i in range(12, 0, -1)]

    color_map = {
        "0-25%的机器": "#6395a5",
        "25%-50%的机器": "#00a8ed",
        "50%-75%的机器": "#153ded",
        "75%-100%的机器": "#051c2c"
    }

    fig = go.Figure()

    for layer in layer_order:
        sub = df[df["分层"] == layer]
        if sub.empty:
            continue

        fig.add_trace(
            go.Bar(
                x=sub["数值"],
                y=sub["月份"],
                name=layer,
                orientation="h",
                marker=dict(color=color_map[layer]),
                text=sub["数值"].map(lambda v: f"{v:.2f}"),
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
# 9. 图表函数：频次
# =========================================================
def make_freq_plot(df_freq_long: pd.DataFrame, selected_store: str):
    df = df_freq_long[df_freq_long["店铺"] == selected_store]

    if df.empty:
        return None

    metric_order = ["TOP25%机器频次均值", "全店频次均值"]
    month_order = [f"{i}月" for i in range(12, 0, -1)]

    color_map = {
        "TOP25%机器频次均值": "#051c2c",
        "全店频次均值": "#00a8ed"
    }

    fig = go.Figure()

    for metric in metric_order:
        sub = df[df["指标"] == metric]
        if sub.empty:
            continue

        fig.add_trace(
            go.Bar(
                x=sub["数值"],
                y=sub["月份"],
                name=metric,
                orientation="h",
                marker=dict(color=color_map[metric]),
                text=sub["数值"].map(lambda v: f"{v:.2f}"),
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
# 10. 加载与预处理
# =========================================================
try:
    merge_data, income_wide, freq_wide = load_raw_data()
    shop_base, store_list = prepare_shop_base(merge_data)
    income_long = prepare_income_long(income_wide)
    freq_long = prepare_freq_long(freq_wide)
except Exception as e:
    st.error(f"数据加载失败：{e}")
    st.stop()

if len(store_list) == 0:
    st.error("没有可选店铺，请检查数据。")
    st.stop()


# =========================================================
# 11. 店铺选择
# =========================================================
selected_store = st.selectbox(
    "请选择店铺",
    options=store_list,
    index=0
)

if selected_store not in shop_base.index:
    st.warning("当前店铺没有匹配数据。")
    st.stop()

row = shop_base.loc[selected_store]


# =========================================================
# 12. 基础信息展示
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
# 13. 图表展示
# =========================================================
st.subheader("机器收入分层月度表现")
income_fig = make_income_layer_plot(income_long, selected_store)
if income_fig is None:
    st.info("当前店铺暂无收入分层数据。")
else:
    st.plotly_chart(income_fig, use_container_width=True)

st.divider()

st.subheader("机器频次月度表现")
freq_fig = make_freq_plot(freq_long, selected_store)
if freq_fig is None:
    st.info("当前店铺暂无频次数据。")
else:
    st.plotly_chart(freq_fig, use_container_width=True)