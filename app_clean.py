import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="清洁照片筛选查看器",
    layout="wide"
)

# =========================
# 列名配置
# =========================
COL_TIME = "任务创建时间"
COL_APARTMENT = "公寓楼"
COL_ADDRESS = "洗衣房地址"
COL_MACHINE_ID = "机器编号"
COL_STAFF = "工作人员"
COL_BUCKET = "桶身照片"
COL_MACHINE = "机身照片"

REQUIRED_COLS = [
    COL_TIME,
    COL_APARTMENT,
    COL_ADDRESS,
    COL_MACHINE_ID,
    COL_STAFF,
    COL_BUCKET,
    COL_MACHINE
]


# =========================
# 工具函数
# =========================
def clean_text(x):
    if pd.isna(x):
        return pd.NA
    x = str(x).strip()
    if x == "" or x.lower() in ["nan", "none", "null"]:
        return pd.NA
    return x


def clean_url(x):
    x = clean_text(x)
    if pd.isna(x):
        return pd.NA
    if str(x).startswith("http://") or str(x).startswith("https://"):
        return x
    return pd.NA


def format_time(x):
    if pd.isna(x):
        return "-"
    try:
        return pd.to_datetime(x).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(x)


@st.cache_data(show_spinner=False)
def read_excel_file(uploaded_file):
    return pd.read_excel(uploaded_file)


def apply_filters(df, date_range, selected_apartments, selected_addresses, selected_staff):
    result = df.copy()

    # 时间筛选：选了开始和结束日期才生效
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

        result = result[
            (result[COL_TIME] >= start_date) &
            (result[COL_TIME] <= end_date)
        ]

    # 公寓楼
    if selected_apartments:
        result = result[result[COL_APARTMENT].astype(str).isin(selected_apartments)]

    # 洗衣房地址
    if selected_addresses:
        result = result[result[COL_ADDRESS].astype(str).isin(selected_addresses)]

    # 工作人员
    if selected_staff:
        result = result[result[COL_STAFF].astype(str).isin(selected_staff)]

    return result


def render_image_by_url(url: str, title: str):
    if pd.isna(url) or str(url).strip() == "":
        st.warning(f"{title}为空")
        return

    st.markdown(
        f"""
        <div style="margin-bottom: 8px; font-size: 14px; font-weight: 600;">
            {title}
        </div>
        <div style="
            width: 100%;
            aspect-ratio: 3 / 4;
            background: #f7f7f7;
            border: 1px solid #eaeaea;
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 8px;
        ">
            <img
                src="{url}"
                style="
                    width: 100%;
                    height: 100%;
                    object-fit: contain;
                    display: block;
                    background: white;
                "
            />
        </div>
        """,
        unsafe_allow_html=True
    )


def render_photo_pair(record):
    staff_text = record[COL_STAFF] if pd.notna(record[COL_STAFF]) else "-"
    time_text = format_time(record[COL_TIME])
    apartment_text = record[COL_APARTMENT] if pd.notna(record[COL_APARTMENT]) else "-"
    address_text = record[COL_ADDRESS] if pd.notna(record[COL_ADDRESS]) else "-"
    machine_id_text = record[COL_MACHINE_ID] if pd.notna(record[COL_MACHINE_ID]) else "-"

    with st.container(border=True):
        st.markdown(
            f"""
            <div style="
                display: flex;
                align-items: center;
                gap: 10px;
                flex-wrap: wrap;
                margin-bottom: 8px;
                font-size: 14px;
            ">
                <span style="
                    display: inline-block;
                    padding: 4px 10px;
                    border-radius: 999px;
                    background: #eef2ff;
                    color: #3730a3;
                    font-weight: 600;
                    font-size: 13px;
                ">
                    {staff_text}
                </span>
                <span style="color: #4b5563;">{time_text}</span>
            </div>

            <div style="
                font-size: 14px;
                color: #374151;
                line-height: 1.6;
                margin-bottom: 14px;
                word-break: break-word;
            ">
                {apartment_text} - {address_text} - {machine_id_text}
            </div>
            """,
            unsafe_allow_html=True
        )

        img_col1, img_col2 = st.columns(2, gap="medium")

        with img_col1:
            render_image_by_url(record[COL_BUCKET], "桶身照片")

        with img_col2:
            render_image_by_url(record[COL_MACHINE], "机身照片")


# =========================
# 页面主体
# =========================
st.title("清洁照片筛选查看器")
st.caption("上传 Excel 后，可按时间 / 公寓楼 / 洗衣房地址 / 工作人员筛选，仅展示桶身照片和机身照片。")

uploaded_file = st.file_uploader(
    "上传 Excel 文件",
    type=["xlsx", "xls"]
)

if uploaded_file is not None:
    try:
        df = read_excel_file(uploaded_file)

        missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
        if missing_cols:
            st.error(f"Excel 缺少以下字段：{', '.join(missing_cols)}")
            st.stop()

        # 仅保留需要字段
        df = df[REQUIRED_COLS].copy()

        # 清洗字段
        df[COL_APARTMENT] = df[COL_APARTMENT].apply(clean_text)
        df[COL_ADDRESS] = df[COL_ADDRESS].apply(clean_text)
        df[COL_MACHINE_ID] = df[COL_MACHINE_ID].apply(clean_text)
        df[COL_STAFF] = df[COL_STAFF].apply(clean_text)
        df[COL_BUCKET] = df[COL_BUCKET].apply(clean_url)
        df[COL_MACHINE] = df[COL_MACHINE].apply(clean_url)

        # 时间格式
        df[COL_TIME] = pd.to_datetime(df[COL_TIME], errors="coerce")

        # 过滤：两张图都必须存在
        df = df[
            df[COL_BUCKET].notna() &
            df[COL_MACHINE].notna()
        ].copy()

        # 时间为空的去掉
        df = df[df[COL_TIME].notna()].copy()

        if df.empty:
            st.warning("没有可展示的数据。")
            st.stop()

        # =========================
        # 顶部筛选区
        # =========================
        st.markdown("## 筛选条件")

        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.2, 1, 1.2, 1])

        with filter_col1:
            min_date = df[COL_TIME].min().date()
            max_date = df[COL_TIME].max().date()

            date_range = st.date_input(
                "任务创建时间范围",
                value=(),
                min_value=min_date,
                max_value=max_date
            )

        with filter_col2:
            apartment_options = sorted(
                df[COL_APARTMENT].dropna().astype(str).unique().tolist()
            )
            selected_apartments = st.multiselect(
                "公寓楼",
                options=apartment_options,
                default=[],
                placeholder="默认不选"
            )

        with filter_col3:
            address_options = sorted(
                df[COL_ADDRESS].dropna().astype(str).unique().tolist()
            )
            selected_addresses = st.multiselect(
                "洗衣房地址",
                options=address_options,
                default=[],
                placeholder="默认不选"
            )

        with filter_col4:
            staff_options = sorted(
                df[COL_STAFF].dropna().astype(str).unique().tolist()
            )
            selected_staff = st.multiselect(
                "工作人员",
                options=staff_options,
                default=[],
                placeholder="默认不选"
            )

        filtered_df = apply_filters(
            df=df,
            date_range=date_range,
            selected_apartments=selected_apartments,
            selected_addresses=selected_addresses,
            selected_staff=selected_staff
        )

        st.markdown("---")
        st.subheader(f"结果数量：{len(filtered_df)}")

        if filtered_df.empty:
            st.info("当前筛选条件下没有数据。")
            st.stop()

        # 排序后展示
        records = filtered_df.sort_values(COL_TIME, ascending=False).reset_index(drop=True)

        # 一行两组
        for i in range(0, len(records), 2):
            row_cols = st.columns(2, gap="large")

            with row_cols[0]:
                render_photo_pair(records.iloc[i])

            if i + 1 < len(records):
                with row_cols[1]:
                    render_photo_pair(records.iloc[i + 1])

    except Exception as e:
        st.error(f"读取或处理文件失败：{e}")

        # streamlit run app_clean.py