from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# 1. 页面设置
# =========================================================
st.set_page_config(
    page_title="店铺经营表现分析",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DATA_FILE = Path(__file__).parent / "data" / "shiny_data.xlsx"


# =========================================================
# 2. 样式
# =========================================================
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2.00rem;
        max-width: 1380px;
    }

    .page-title {
        font-size: 1.85rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 1.10rem;
        line-height: 1.25;
        letter-spacing: -0.02em;
    }

    .section-title {
        font-size: 1.20rem;
        font-weight: 700;
        color: #111827;
        margin: 1.20rem 0 0.75rem 0;
        letter-spacing: -0.01em;
    }

    .chart-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #111827;
        margin: 0 0 0.70rem 0;
    }

    .toolbar-card {
        background: rgba(255, 255, 255, 0.78);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(229, 231, 235, 0.85);
        border-radius: 18px;
        padding: 14px 16px;
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.05);
        margin-bottom: 16px;
    }

    .info-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 14px 16px 12px 16px;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
        min-height: 82px;
    }

    .info-card-label {
        font-size: 0.84rem;
        color: #6b7280;
        margin-bottom: 8px;
        line-height: 1.20;
    }

    .info-card-value {
        font-size: 0.98rem;
        font-weight: 700;
        color: #111827;
        line-height: 1.25;
        word-break: break-word;
    }

    .panel-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 16px 16px 10px 16px;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
        margin-top: 8px;
        margin-bottom: 12px;
    }

    div[data-baseweb="select"] > div {
        border-radius: 12px !important;
        min-height: 42px;
        border-color: #d1d5db !important;
        box-shadow: none !important;
    }

    hr {
        margin-top: 1.10rem !important;
        margin-bottom: 1.10rem !important;
        border-color: #eceff3 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


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


def info_card(label: str, value: str):
    st.markdown(
        f"""
        <div class="info-card">
            <div class="info-card-label">{label}</div>
            <div class="info-card-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 4. 读取原始数据
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

    for df in [merge_data, income_wide, freq_wide]:
        if "店铺" in df.columns:
            df["店铺"] = df["店铺"].astype(str).str.strip()

    return merge_data, income_wide, freq_wide


# =========================================================
# 5. 预处理：基础信息
# =========================================================
@st.cache_data(show_spinner=False)
def prepare_shop_base(merge_data: pd.DataFrame):
    if "店铺" not in merge_data.columns:
        raise ValueError("merge_data 中缺少列：店铺")

    df = merge_data.copy()
    df["店铺"] = df["店铺"].astype(str).str.strip()
    df = df.dropna(subset=["店铺"])
    df = df[df["店铺"] != ""]

    shop_base = (
        df.drop_duplicates(subset=["店铺"], keep="first")
        .set_index("店铺", drop=False)
        .sort_index()
    )

    store_list = shop_base["店铺"].tolist()
    return shop_base, store_list


# =========================================================
# 6. 预处理：收入分层
# 目标结构：
# y轴 = 1月-12月
# x轴 = 数值
# 颜色 = 类别
# 同月份不同类别并排，不重叠
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
    df["类别"] = (
        name_series
        .str.replace(r"^\d+月", "", regex=True)
        .str.strip()
    )
    df["月份数值"] = pd.to_numeric(
        df["月份"].str.extract(r"(\d+)", expand=False),
        errors="coerce"
    )
    df["数值"] = pd.to_numeric(df["数值"], errors="coerce").round(2)

    category_order = [
        "0-25%的机器",
        "25%-50%的机器",
        "50%-75%的机器",
        "75%-100%的机器"
    ]
    month_order = [f"{i}月" for i in range(1, 13)]

    df = df.dropna(subset=["店铺", "月份", "月份数值", "数值"])
    df = df[df["类别"].isin(category_order)]
    df = df[df["数值"] > 0]

    df["月份"] = pd.Categorical(df["月份"], categories=month_order, ordered=True)
    df["类别"] = pd.Categorical(df["类别"], categories=category_order, ordered=True)

    return df.sort_values(
        ["店铺", "月份数值", "类别"],
        ascending=[True, True, True]
    ).reset_index(drop=True)


# =========================================================
# 7. 预处理：频次
# 目标结构：
# y轴 = 1月-12月
# x轴 = 数值
# 颜色 = 类别
# 同月份不同类别并排，不重叠
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

    df["类别"] = pd.Series(pd.NA, index=df.index, dtype="object")
    df.loc[name_series.str.contains("TOP25%机器频次均值", na=False), "类别"] = "TOP25%机器频次均值"
    df.loc[
        name_series.str.contains("频次均值", na=False)
        & ~name_series.str.contains("TOP25%机器频次均值", na=False),
        "类别"
    ] = "全店频次均值"

    df["数值"] = pd.to_numeric(df["数值"], errors="coerce").round(2)

    category_order = ["TOP25%机器频次均值", "全店频次均值"]
    month_order = [f"{i}月" for i in range(1, 13)]

    df = df.dropna(subset=["店铺", "月份", "月份数值", "类别", "数值"])
    df = df[df["类别"].isin(category_order)]
    df = df[df["数值"] > 0]

    df["月份"] = pd.Categorical(df["月份"], categories=month_order, ordered=True)
    df["类别"] = pd.Categorical(df["类别"], categories=category_order, ordered=True)

    return df.sort_values(
        ["店铺", "月份数值", "类别"],
        ascending=[True, True, True]
    ).reset_index(drop=True)


# =========================================================
# 8. Plotly 图表：分组横向条形图（不重叠）
# y轴 = 月份
# x轴 = 数值
# 颜色 = 类别
# =========================================================
def make_grouped_horizontal_bar(
    df_long: pd.DataFrame,
    selected_store: str,
    category_order: list[str],
    color_map: dict[str, str],
    x_title: str,
    height: int
):
    plot_df = df_long[df_long["店铺"] == selected_store].copy()
    if plot_df.empty:
        return None

    month_order = [f"{i}月" for i in range(1, 13)]

    fig = go.Figure()

    for category in category_order:
        sub = plot_df[plot_df["类别"] == category].copy()
        if sub.empty:
            continue

        fig.add_trace(
            go.Bar(
                x=sub["数值"],
                y=sub["月份"],
                name=category,
                orientation="h",
                marker=dict(color=color_map.get(category, "#4b5563")),
                text=sub["数值"].map(lambda v: f"{v:.2f}"),
                textposition="outside",
                cliponaxis=False,
                offsetgroup=str(category),
                legendgroup=str(category),
                hovertemplate=(
                    "月份: %{y}<br>"
                    "类别: %{fullData.name}<br>"
                    "数值: %{x:.2f}<extra></extra>"
                )
            )
        )

    fig.update_layout(
        barmode="group",   # 关键：并排，不重叠
        bargap=0.28,
        bargroupgap=0.08,
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(t=10, b=30, l=10, r=90),
        legend=dict(
            orientation="h",
            x=0.00,
            y=1.10,
            xanchor="left",
            yanchor="bottom",
            title=None,
            font=dict(size=12)
        ),
        xaxis=dict(
            title=x_title,
            showgrid=True,
            gridcolor="#e5e7eb",
            zeroline=False,
            tickfont=dict(size=12, color="#374151"),
            title_font=dict(size=12, color="#374151")
        ),
        yaxis=dict(
            title="",
            categoryorder="array",
            categoryarray=month_order[::-1],
            tickfont=dict(size=12, color="#374151")
        ),
        font=dict(
            family="Arial, PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif",
            color="#374151",
            size=12
        )
    )

    return fig


# =========================================================
# 9. 加载数据
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
# 10. 顶部筛选
# =========================================================
st.markdown('<div class="toolbar-card">', unsafe_allow_html=True)
selected_store = st.selectbox(
    "请选择店铺",
    options=store_list,
    index=0
)
st.markdown('</div>', unsafe_allow_html=True)

if selected_store not in shop_base.index:
    st.warning("当前店铺没有匹配数据。")
    st.stop()

row = shop_base.loc[selected_store]

st.markdown(
    f'<div class="page-title">{selected_store} ｜ 经营画像</div>',
    unsafe_allow_html=True
)


# =========================================================
# 11. 基础信息
# =========================================================
st.markdown('<div class="section-title">基础信息</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    info_card("城市", fmt_text(row.get("城市")))
with c2:
    info_card("办学层次", fmt_text(row.get("办学层次")))
with c3:
    info_card("定价", fmt_text(row.get("定价")))
with c4:
    info_card("万化收入", fmt_yuan(row.get("万化收入"), 2))

st.markdown('<div class="section-title">用户信息</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    info_card("服务人数", fmt_num(row.get("服务人数"), 0))
with c2:
    info_card("稳定月活跃用户", fmt_num(row.get("稳定月活跃用户"), 0))
with c3:
    info_card("月活跃率", fmt_pct(row.get("月活跃率"), 0))

st.markdown('<div class="section-title">机器信息</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    info_card("机器数量", fmt_num(row.get("机器数量"), 0))
with c2:
    info_card("机器月收入均值", fmt_yuan(row.get("机器月收入均值"), 2))
with c3:
    info_card("机器月均频次", fmt_num(row.get("机器月均频次"), 2))
with c4:
    info_card("Top25%机器月收入", fmt_yuan(row.get("top25%机器月收入"), 2))
with c5:
    info_card("TOP25%机器频次均值", fmt_num(row.get("TOP25%机器频次均值"), 2))


# =========================================================
# 12. 图表分析
# =========================================================
st.markdown('<div class="section-title">图表分析</div>', unsafe_allow_html=True)

income_category_order = [
    "0-25%的机器",
    "25%-50%的机器",
    "50%-75%的机器",
    "75%-100%的机器"
]
income_color_map = {
    "0-25%的机器": "#9bb7c0",
    "25%-50%的机器": "#5fa7c1",
    "50%-75%的机器": "#2f6e8a",
    "75%-100%的机器": "#17384d"
}

freq_category_order = ["TOP25%机器频次均值", "全店频次均值"]
freq_color_map = {
    "TOP25%机器频次均值": "#17384d",
    "全店频次均值": "#5fa7c1"
}

st.markdown('<div class="panel-card">', unsafe_allow_html=True)
st.markdown('<div class="chart-title">机器收入分层月度表现</div>', unsafe_allow_html=True)
income_fig = make_grouped_horizontal_bar(
    df_long=income_long,
    selected_store=selected_store,
    category_order=income_category_order,
    color_map=income_color_map,
    x_title="数值",
    height=1200
)
if income_fig is None:
    st.info("当前店铺暂无收入分层数据。")
else:
    st.plotly_chart(income_fig, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="panel-card">', unsafe_allow_html=True)
st.markdown('<div class="chart-title">机器频次月度表现</div>', unsafe_allow_html=True)
freq_fig = make_grouped_horizontal_bar(
    df_long=freq_long,
    selected_store=selected_store,
    category_order=freq_category_order,
    color_map=freq_color_map,
    x_title="频次",
    height=800
)
if freq_fig is None:
    st.info("当前店铺暂无频次数据。")
else:
    st.plotly_chart(freq_fig, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)