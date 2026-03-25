from pathlib import Path

import altair as alt
import pandas as pd
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
        padding-top: 1.50rem;
        padding-bottom: 2.00rem;
        max-width: 1400px;
    }

    h1, h2, h3 {
        letter-spacing: -0.02em;
    }

    .page-title {
        font-size: 2.00rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 1.25rem;
        line-height: 1.25;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #111827;
        margin: 1.40rem 0 0.85rem 0;
    }

    .chart-title {
        font-size: 1.20rem;
        font-weight: 700;
        color: #111827;
        margin: 0.20rem 0 0.80rem 0;
    }

    .info-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 16px 18px 14px 18px;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
        min-height: 92px;
    }

    .info-card-label {
        font-size: 0.88rem;
        color: #6b7280;
        margin-bottom: 8px;
        line-height: 1.20;
    }

    .info-card-value {
        font-size: 1.00rem;
        font-weight: 700;
        color: #111827;
        line-height: 1.25;
        word-break: break-word;
    }

    .panel-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 18px 18px 10px 18px;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
        margin-top: 8px;
        margin-bottom: 12px;
    }

    div[data-baseweb="select"] > div {
        border-radius: 12px !important;
        min-height: 44px;
        border-color: #d1d5db !important;
        box-shadow: none !important;
    }

    hr {
        margin-top: 1.25rem !important;
        margin-bottom: 1.25rem !important;
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

    return df.sort_values(
        ["店铺", "月份数值", "分层"],
        ascending=[True, False, True]
    ).reset_index(drop=True)


# =========================================================
# 7. 预处理：频次
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

    df["指标"] = pd.Series(pd.NA, index=df.index, dtype="object")
    df.loc[name_series.str.contains("TOP25%机器频次均值", na=False), "指标"] = "TOP25%机器频次均值"
    df.loc[
        name_series.str.contains("频次均值", na=False)
        & ~name_series.str.contains("TOP25%机器频次均值", na=False),
        "指标"
    ] = "全店频次均值"

    df["数值"] = pd.to_numeric(df["数值"], errors="coerce").round(2)

    metric_order = ["TOP25%机器频次均值", "全店频次均值"]
    month_order = [f"{i}月" for i in range(12, 0, -1)]

    df = df.dropna(subset=["店铺", "月份", "月份数值", "指标", "数值"])
    df = df[df["指标"].isin(metric_order)]

    df["月份"] = pd.Categorical(df["月份"], categories=month_order, ordered=True)
    df["指标"] = pd.Categorical(df["指标"], categories=metric_order, ordered=True)

    return df.sort_values(
        ["店铺", "月份数值", "指标"],
        ascending=[True, False, True]
    ).reset_index(drop=True)


# =========================================================
# 8. Altair 图表：收入分层
# =========================================================
def make_income_layer_chart(df_income_long: pd.DataFrame, selected_store: str):
    plot_df = df_income_long[df_income_long["店铺"] == selected_store].copy()
    if plot_df.empty:
        return None

    layer_order = [
        "0-25%的机器",
        "25%-50%的机器",
        "50%-75%的机器",
        "75%-100%的机器"
    ]
    month_order = [f"{i}月" for i in range(12, 0, -1)]

    plot_df["标签"] = plot_df["数值"].map(lambda x: f"{x:.2f}")

    color_scale = alt.Scale(
        domain=layer_order,
        range=["#9bb7c0", "#5fa7c1", "#2f6e8a", "#17384d"]
    )

    base = alt.Chart(plot_df).encode(
        y=alt.Y(
            "月份:N",
            sort=month_order,
            title=None,
            axis=alt.Axis(labelFontSize=12, title=None, labelColor="#374151")
        ),
        x=alt.X(
            "数值:Q",
            title="数值",
            axis=alt.Axis(
                labelFontSize=11,
                titleFontSize=12,
                grid=True,
                gridColor="#e5e7eb",
                labelColor="#374151",
                titleColor="#374151"
            )
        ),
        color=alt.Color(
            "分层:N",
            sort=layer_order,
            title=None,
            scale=color_scale,
            legend=alt.Legend(
                orient="top",
                direction="horizontal",
                labelFontSize=11
            )
        ),
        yOffset=alt.YOffset("分层:N", sort=layer_order),
        tooltip=[
            alt.Tooltip("月份:N", title="月份"),
            alt.Tooltip("分层:N", title="分层"),
            alt.Tooltip("数值:Q", title="数值", format=".2f")
        ]
    )

    bars = base.mark_bar(size=16, cornerRadiusEnd=3)

    text = base.mark_text(
        align="left",
        baseline="middle",
        dx=4,
        fontSize=11,
        color="#374151"
    ).encode(
        text="标签:N"
    )

    chart = (
        (bars + text)
        .properties(height=520)
        .configure_view(stroke=None)
        .configure_axis(domain=False)
        .configure_legend(
            labelColor="#374151",
            symbolType="square"
        )
    )

    return chart


# =========================================================
# 9. Altair 图表：频次
# =========================================================
def make_freq_chart(df_freq_long: pd.DataFrame, selected_store: str):
    plot_df = df_freq_long[df_freq_long["店铺"] == selected_store].copy()
    if plot_df.empty:
        return None

    metric_order = ["TOP25%机器频次均值", "全店频次均值"]
    month_order = [f"{i}月" for i in range(12, 0, -1)]

    plot_df["标签"] = plot_df["数值"].map(lambda x: f"{x:.2f}")

    color_scale = alt.Scale(
        domain=metric_order,
        range=["#17384d", "#5fa7c1"]
    )

    base = alt.Chart(plot_df).encode(
        y=alt.Y(
            "月份:N",
            sort=month_order,
            title=None,
            axis=alt.Axis(labelFontSize=12, title=None, labelColor="#374151")
        ),
        x=alt.X(
            "数值:Q",
            title="频次",
            axis=alt.Axis(
                labelFontSize=11,
                titleFontSize=12,
                grid=True,
                gridColor="#e5e7eb",
                labelColor="#374151",
                titleColor="#374151"
            )
        ),
        color=alt.Color(
            "指标:N",
            sort=metric_order,
            title=None,
            scale=color_scale,
            legend=alt.Legend(
                orient="top",
                direction="horizontal",
                labelFontSize=11
            )
        ),
        yOffset=alt.YOffset("指标:N", sort=metric_order),
        tooltip=[
            alt.Tooltip("月份:N", title="月份"),
            alt.Tooltip("指标:N", title="指标"),
            alt.Tooltip("数值:Q", title="频次", format=".2f")
        ]
    )

    bars = base.mark_bar(size=18, cornerRadiusEnd=3)

    text = base.mark_text(
        align="left",
        baseline="middle",
        dx=4,
        fontSize=11,
        color="#374151"
    ).encode(
        text="标签:N"
    )

    chart = (
        (bars + text)
        .properties(height=420)
        .configure_view(stroke=None)
        .configure_axis(domain=False)
        .configure_legend(
            labelColor="#374151",
            symbolType="square"
        )
    )

    return chart


# =========================================================
# 10. 加载数据
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
# 11. 顶部
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

st.markdown(
    f'<div class="page-title">{selected_store} ｜ 经营画像</div>',
    unsafe_allow_html=True
)


# =========================================================
# 12. 基础信息
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
# 13. 图表区域
# =========================================================
st.markdown('<div class="section-title">图表分析</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">机器收入分层月度表现</div>', unsafe_allow_html=True)
    income_chart = make_income_layer_chart(income_long, selected_store)
    if income_chart is None:
        st.info("当前店铺暂无收入分层数据。")
    else:
        st.altair_chart(income_chart, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">机器频次月度表现</div>', unsafe_allow_html=True)
    freq_chart = make_freq_chart(freq_long, selected_store)
    if freq_chart is None:
        st.info("当前店铺暂无频次数据。")
    else:
        st.altair_chart(freq_chart, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)