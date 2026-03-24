from pathlib import Path
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# 0. 页面配置
# =========================================================
st.set_page_config(
    page_title="店铺经营表现分析",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# 1. 全局 CSS（Apple 风）
# =========================================================
APPLE_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI",
                 Roboto, Helvetica, Arial, sans-serif;
    color: #1D1D1F;
}

.stApp {
    background-color: #F5F5F7;
}

/* 顶部整体区域 */
.top-shell {
    position: sticky;
    top: 0;
    z-index: 999;
    background: rgba(245,245,247,0.88);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    padding-top: 0.35rem;
    padding-bottom: 0.35rem;
}

/* 顶部毛玻璃栏 */
.apple-top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    padding: 14px 24px;
    background: rgba(255, 255, 255, 0.78);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(0,0,0,0.06);
    border-radius: 22px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.04);
    margin-bottom: 18px;
}

.brand-title {
    font-weight: 600;
    font-size: 1.25rem;
    color: #1D1D1F;
    letter-spacing: -0.01em;
    white-space: nowrap;
}

/* 主体区域 */
.block-container {
    padding-top: 1.0rem;
    padding-bottom: 2.5rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
    max-width: none !important;
}

/* 卡片 */
.apple-card {
    background: #FFFFFF;
    border: none;
    border-radius: 22px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.04);
    padding: 20px 22px 22px 22px;
    margin-bottom: 22px;
    overflow: hidden;
}

.apple-card-title {
    font-weight: 600;
    font-size: 1.08rem;
    color: #1D1D1F;
    margin-bottom: 14px;
}

/* 规格区 */
.spec-section {
    padding-top: 2px;
}

.spec-section-title {
    font-size: 0.96rem;
    font-weight: 600;
    color: #1D1D1F;
    margin-top: 16px;
    margin-bottom: 12px;
    border-left: 3px solid #0071E3;
    padding-left: 8px;
}

.spec-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 18px;
}

.spec-item {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: flex-start;
    border-bottom: 1px solid #E5E5EA;
    padding-bottom: 12px;
    min-height: 60px;
}

.spec-label {
    font-size: 0.76rem;
    color: #86868B;
    letter-spacing: 0.02em;
    margin-bottom: 6px;
}

.spec-value {
    font-size: 1.05rem;
    font-weight: 500;
    color: #1D1D1F;
    line-height: 1.3;
}

/* Streamlit 输入控件细节 */
div[data-baseweb="select"] > div {
    border-radius: 14px !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    min-height: 48px !important;
    background: #FFFFFF !important;
    box-shadow: none !important;
}

div[data-testid="stSelectbox"] label {
    display: none !important;
}

/* 图表容器内边距更紧凑 */
.chart-wrap {
    padding-top: 4px;
}

/* 移动端 */
@media (max-width: 768px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .apple-top-bar {
        padding: 12px 16px;
    }

    .brand-title {
        font-size: 1.10rem;
    }

    .spec-grid {
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    }
}
</style>
"""

st.markdown(APPLE_CSS, unsafe_allow_html=True)


# =========================================================
# 2. 数据读取
# =========================================================
DATA_FILE = Path(__file__).parent / "data" / "shiny_data.xlsx"


@st.cache_data(show_spinner=False)
def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"未找到数据文件: {DATA_FILE}")

    merge_df = pd.read_excel(DATA_FILE, sheet_name="merge_data")
    income_df = pd.read_excel(DATA_FILE, sheet_name="target_shop_month_output_wide")
    freq_df = pd.read_excel(DATA_FILE, sheet_name="target_频次信息_data")

    return merge_df, income_df, freq_df


# =========================================================
# 3. 工具函数
# =========================================================
def is_missing(x) -> bool:
    return pd.isna(x)


def fmt_num(x, digits=2):
    if is_missing(x):
        return "-"
    return f"{float(x):.{digits}f}"


def fmt_pct(x, digits=2):
    if is_missing(x):
        return "-"
    return f"{float(x) * 100:.{digits}f}%"


def fmt_yuan(x, digits=2):
    if is_missing(x):
        return "-"
    return f"¥{float(x):.{digits}f}"


def fmt_text(x):
    if is_missing(x):
        return "-"
    value = str(x).strip()
    return value if value else "-"


def make_spec_item(label, value):
    return f"""
    <div class="spec-item">
        <span class="spec-label">{label}</span>
        <span class="spec-value">{value}</span>
    </div>
    """


def month_num_from_name(text):
    match = re.search(r"(\d+)月", str(text))
    return int(match.group(1)) if match else None


def build_specs_html(row: pd.Series) -> str:
    html = f"""
    <div class="spec-section">

        <div class="spec-section-title">基础信息</div>
        <div class="spec-grid">
            {make_spec_item("城市", fmt_text(row.get("城市")))}
            {make_spec_item("办学层次", fmt_text(row.get("办学层次")))}
            {make_spec_item("定价", fmt_text(row.get("定价")))}
            {make_spec_item("万化收入", fmt_yuan(row.get("万化收入"), 2))}
        </div>

        <div class="spec-section-title" style="margin-top:26px;">用户信息</div>
        <div class="spec-grid">
            {make_spec_item("服务人数", fmt_num(row.get("服务人数"), 0))}
            {make_spec_item("稳定月活跃用户", fmt_num(row.get("稳定月活跃用户"), 0))}
            {make_spec_item("月活跃率", fmt_pct(row.get("月活跃率"), 0))}
        </div>

        <div class="spec-section-title" style="margin-top:26px;">机器信息</div>
        <div class="spec-grid">
            {make_spec_item("机器数量", fmt_num(row.get("机器数量"), 0))}
            {make_spec_item("机器月收入均值", fmt_yuan(row.get("机器月收入均值"), 2))}
            {make_spec_item("机器月均频次", fmt_num(row.get("机器月均频次"), 2))}
            {make_spec_item("Top25%机器月收入", fmt_yuan(row.get("top25%机器月收入"), 2))}
            {make_spec_item("TOP25%机器频次均值", fmt_num(row.get("TOP25%机器频次均值"), 2))}
        </div>

    </div>
    """
    return html


# =========================================================
# 4. 图表函数
# =========================================================
def make_income_layer_plot(df_income_wide: pd.DataFrame, selected_store: str):
    plot_df = df_income_wide[df_income_wide["店铺"] == selected_store].copy()

    if plot_df.empty:
        return None

    plot_df = plot_df.melt(
        id_vars=["店铺"],
        var_name="name",
        value_name="数值"
    )

    plot_df["月份"] = plot_df["name"].astype(str).str.extract(r"^(\d+月)")
    plot_df["分层"] = (
        plot_df["name"]
        .astype(str)
        .str.replace(r"^\d+月", "", regex=True)
        .str.strip()
    )
    plot_df["月份数值"] = plot_df["月份"].apply(month_num_from_name)
    plot_df["数值"] = pd.to_numeric(plot_df["数值"], errors="coerce").round(2)

    plot_df = plot_df.dropna(subset=["月份数值", "数值"])

    layer_order = [
        "0-25%的机器",
        "25%-50%的机器",
        "50%-75%的机器",
        "75%-100%的机器",
    ]
    month_order = [f"{i}月" for i in range(12, 0, -1)]

    plot_df["分层"] = pd.Categorical(plot_df["分层"], categories=layer_order, ordered=True)
    plot_df["月份"] = pd.Categorical(plot_df["月份"], categories=month_order, ordered=True)
    plot_df = plot_df.sort_values(["月份数值", "分层"], ascending=[False, True])

    if plot_df.empty:
        return None

    color_map = {
        "0-25%的机器": "#6395a5",
        "25%-50%的机器": "#00a8ed",
        "50%-75%的机器": "#153ded",
        "75%-100%的机器": "#051c2c",
    }

    fig = go.Figure()

    for layer in layer_order:
        sub = plot_df[plot_df["分层"] == layer].copy()
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
                cliponaxis=False,
                hovertemplate=(
                    "月份: %{y}<br>"
                    "分层: %{fullData.name}<br>"
                    "数值: %{x:.2f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        barmode="group",
        height=980,
        xaxis=dict(
            title="数值",
            showgrid=True,
            gridcolor="#E5E5EA",
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            categoryorder="array",
            categoryarray=month_order,
            tickfont=dict(size=13),
        ),
        legend=dict(
            orientation="h",
            x=0.5,
            y=1.10,
            xanchor="center",
            font=dict(size=12),
        ),
        margin=dict(t=45, b=40, l=5, r=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def make_freq_plot(df_freq_wide: pd.DataFrame, selected_store: str):
    plot_df = df_freq_wide[df_freq_wide["店铺"] == selected_store].copy()

    if plot_df.empty:
        return None

    plot_df = plot_df.melt(
        id_vars=["店铺"],
        var_name="name",
        value_name="数值"
    )

    plot_df["月份"] = plot_df["name"].astype(str).str.extract(r"^(\d+月)")
    plot_df["月份数值"] = plot_df["月份"].apply(month_num_from_name)

    def parse_metric(name):
        text = str(name)
        if "TOP25%机器频次均值" in text:
            return "TOP25%机器频次均值"
        if "频次均值" in text:
            return "全店频次均值"
        return None

    plot_df["指标"] = plot_df["name"].apply(parse_metric)
    plot_df["数值"] = pd.to_numeric(plot_df["数值"], errors="coerce").round(2)

    plot_df = plot_df.dropna(subset=["月份数值", "指标", "数值"])

    metric_order = ["TOP25%机器频次均值", "全店频次均值"]
    month_order = [f"{i}月" for i in range(12, 0, -1)]

    plot_df["指标"] = pd.Categorical(plot_df["指标"], categories=metric_order, ordered=True)
    plot_df["月份"] = pd.Categorical(plot_df["月份"], categories=month_order, ordered=True)
    plot_df = plot_df.sort_values(["月份数值", "指标"], ascending=[False, True])

    if plot_df.empty:
        return None

    color_map = {
        "TOP25%机器频次均值": "#051c2c",
        "全店频次均值": "#00a8ed",
    }

    fig = go.Figure()

    for metric in metric_order:
        sub = plot_df[plot_df["指标"] == metric].copy()
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
                cliponaxis=False,
                hovertemplate=(
                    "月份: %{y}<br>"
                    "指标: %{fullData.name}<br>"
                    "数值: %{x:.2f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        barmode="group",
        height=640,
        xaxis=dict(
            title="频次",
            showgrid=True,
            gridcolor="#E5E5EA",
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            categoryorder="array",
            categoryarray=month_order,
            tickfont=dict(size=13),
        ),
        legend=dict(
            orientation="h",
            x=0.5,
            y=1.08,
            xanchor="center",
            font=dict(size=12),
        ),
        margin=dict(t=35, b=40, l=5, r=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


# =========================================================
# 5. 主逻辑
# =========================================================
try:
    merge_data, target_shop_month_output_wide, target_freq_data = load_data()
except Exception as e:
    st.error(f"数据加载失败：{e}")
    st.stop()

if "店铺" not in merge_data.columns:
    st.error("merge_data 中缺少列：店铺")
    st.stop()

store_options = (
    merge_data["店铺"]
    .dropna()
    .astype(str)
    .drop_duplicates()
    .tolist()
)

if not store_options:
    st.error("没有可选店铺，请检查数据。")
    st.stop()

# 顶部栏
st.markdown('<div class="top-shell">', unsafe_allow_html=True)
col1, col2 = st.columns([2.2, 1.2], vertical_alignment="center")

with col1:
    st.markdown(
        """
        <div class="apple-top-bar" style="margin-bottom:0;">
            <div class="brand-title">店铺经营表现分析</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    selected_store = st.selectbox(
        "请选择店铺",
        options=store_options,
        index=0,
        help="请输入或选择店铺",
        label_visibility="collapsed",
    )

st.markdown("</div>", unsafe_allow_html=True)

# 当前店铺数据
store_profile = merge_data[merge_data["店铺"].astype(str) == str(selected_store)].copy()
if store_profile.empty:
    st.warning("当前店铺没有匹配数据。")
    st.stop()

row = store_profile.iloc[0]

# 卡片1：经营画像
st.markdown('<div class="apple-card">', unsafe_allow_html=True)
st.markdown(
    f'<div class="apple-card-title">{selected_store}｜经营画像</div>',
    unsafe_allow_html=True,
)
st.markdown(build_specs_html(row), unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 卡片2：收入分层
st.markdown('<div class="apple-card">', unsafe_allow_html=True)
st.markdown(
    '<div class="apple-card-title">机器收入分层月度表现</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)

income_fig = make_income_layer_plot(target_shop_month_output_wide, selected_store)
if income_fig is None:
    st.info("当前店铺暂无收入分层数据。")
else:
    st.plotly_chart(income_fig, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 卡片3：频次
st.markdown('<div class="apple-card">', unsafe_allow_html=True)
st.markdown(
    '<div class="apple-card-title">机器频次月度表现</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)

freq_fig = make_freq_plot(target_freq_data, selected_store)
if freq_fig is None:
    st.info("当前店铺暂无频次数据。")
else:
    st.plotly_chart(freq_fig, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)