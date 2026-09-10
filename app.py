import streamlit as st
import pandas as pd

from load_and_clean import (
    load_sheet_values,
    make_dataframe,
    merge_with_master,
    search_product,
    calculate_product_average,
    calculate_benchmark,
)

from sync_master import (
    load_master,
    find_new_products,
    make_brand_large_map,
    make_brand_middle_map,
    classify_new_products,
    save_master,
    normalize_brand,
)


# =========================================================
# 페이지 설정
# =========================================================

st.set_page_config(
    page_title="딜특가 의사결정 지원",
    page_icon="📊",
    layout="wide",
)


# =========================================================
# 표시 함수
# =========================================================

def format_number(value):
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.1f}"


def format_money(value):
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.0f}원"


def format_percent(value):
    if value is None or pd.isna(value):
        return "-"
    return f"{value * 100:.2f}%"


def format_discount(value):
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.1f}%"


def format_diff(product_value, benchmark_value, kind):
    if (
        product_value is None
        or benchmark_value is None
        or pd.isna(product_value)
        or pd.isna(benchmark_value)
    ):
        return "-"

    diff = product_value - benchmark_value

    if kind == "number":
        return f"{diff:+,.1f}"
    elif kind == "money":
        return f"{diff:+,.0f}원"
    elif kind == "cvr":
        return f"{diff * 100:+.2f}%p"
    elif kind == "percent":
        return f"{diff:+.1f}%p"

    return "-"


# =========================================================
# 할인율 구간
# =========================================================

def add_discount_band(df):
    result = df.copy()

    result["할인율구간"] = pd.cut(
        result["할인율"],
        bins=[
            -1,
            10,
            20,
            30,
            40,
            50,
            60,
            1000,
        ],
        labels=[
            "10% 이하",
            "10~20%",
            "20~30%",
            "30~40%",
            "40~50%",
            "50~60%",
            "60% 초과",
        ],
        include_lowest=True,
        right=True,
    )

    return result

# =========================================================
# 포트폴리오용 DEMO CSV 로드
# =========================================================

@st.cache_data(ttl=300)
def load_raw_data():

    demo_path = "demo_data.csv"

    demo_df = pd.read_csv(
        demo_path,
        dtype=str
    ).fillna("")

    values = [
        demo_df.columns.tolist()
    ] + demo_df.values.tolist()

    df = make_dataframe(
        values
    )

    return df

# =========================================================
# MASTER 신규 상품 자동 동기화
# =========================================================

@st.cache_data(ttl=300)
def sync_master_from_dataframe(raw_df):

    master = load_master()

    products = (
        raw_df
        .sort_values("날짜")
        .drop_duplicates(
            subset=["대표상품코드"],
            keep="last"
        )
        [
            [
                "대표상품코드",
                "전체옵션코드",
                "상품명",
                "브랜드명",
            ]
        ]
        .copy()
    )

    products["대표상품코드"] = (
        products["대표상품코드"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    products["브랜드정규화"] = (
        products["브랜드명"]
        .apply(normalize_brand)
    )

    new_products = find_new_products(
        products,
        master
    )

    new_count = len(new_products)

    if new_products.empty:
        return {
            "new_count": 0,
            "unclassified_count": 0,
            "saved": False,
        }

    large_map = make_brand_large_map(
        master
    )

    middle_map = make_brand_middle_map(
        master
    )

    new_rows = classify_new_products(
        new_products,
        large_map,
        middle_map
    )

    unclassified_count = int(
        (
            new_rows["대카테고리"]
            == "미분류"
        ).sum()
    )

    save_master(
        master,
        new_rows
    )

    return {
        "new_count": new_count,
        "unclassified_count": unclassified_count,
        "saved": True,
    }


# =========================================================
# 최종 분석 데이터
# =========================================================

def load_final_data():

    raw_df = load_raw_data()

    sync_result = (
        sync_master_from_dataframe(
            raw_df
        )
    )

    final_df = merge_with_master(
        raw_df
    )

    return final_df, sync_result

# =========================================================
# 벤치마크 표
# =========================================================

def make_benchmark_table(
    benchmark,
    product_average
):

    if benchmark is None:
        return pd.DataFrame(
            {
                "지표": [
                    "비교 가능한 과거 성과 없음"
                ]
            }
        )

    rows = []

    metrics = [
        (
            "편성당 평균 매출",
            "평균결제금액",
            "money",
            format_money
        ),
        (
            "평균 결제수량",
            "평균결제수량",
            "number",
            format_number
        ),
        (
            "평균 할인율",
            "평균할인율",
            "percent",
            format_discount
        ),
    ]

    for label, key, kind, formatter in metrics:

        benchmark_value = benchmark.get(
            key
        )

        if product_average is None:
            product_value = None
        else:
            product_value = product_average.get(
                key
            )

        rows.append(
            {
                "지표": label,
                "상품 평균": (
                    formatter(product_value)
                    if product_value is not None
                    else "-"
                ),
                "비교군 평균": (
                    formatter(benchmark_value)
                    if benchmark_value is not None
                    else "-"
                ),
                "상품 - 비교군": (
                    format_diff(
                        product_value,
                        benchmark_value,
                        kind
                    )
                    if (
                        product_value is not None
                        and benchmark_value is not None
                    )
                    else "-"
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


# =========================================================
# 상품 목록
# =========================================================

def make_product_list(df):

    return (
        df
        .sort_values("날짜")
        .drop_duplicates(
            subset=["대표상품코드"],
            keep="last"
        )
        .copy()
    )


# =========================================================
# 상품 키워드 검색
# =========================================================

def search_products_by_keyword(
    products,
    keyword
):

    keyword = (
        str(keyword)
        .strip()
        .lower()
    )

    if keyword == "":
        return products.iloc[0:0]

    mask = (
        products["상품명"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(
            keyword,
            regex=False
        )
        |
        products["브랜드명"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(
            keyword,
            regex=False
        )
        |
        products["전체옵션코드"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(
            keyword,
            regex=False
        )
        |
        products["대표상품코드"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(
            keyword,
            regex=False
        )
    )

    return products[
        mask
    ].copy()


# =========================================================
# 표본 수준
# =========================================================

def get_sample_level(count):

    if count <= 2:
        return "표본 적음"
    elif count <= 9:
        return "참고"
    else:
        return "충분"


# =========================================================
# 카테고리 비교 요약
# =========================================================

def make_category_summary(
    performance_df,
    group_columns
):

    if performance_df.empty:
        return pd.DataFrame()

    summary = (
        performance_df
        .groupby(
            group_columns,
            dropna=False
        )
        .agg(
            편성완료수=(
                "대표상품코드",
                "size"
            ),

            상품수=(
                "대표상품코드",
                "nunique"
            ),

            평균PV=(
                "PV",
                "mean"
            ),

            평균결제수량=(
                "결제수량",
                "mean"
            ),

            평균CVR=(
                "CVR",
                "mean"
            ),

            평균결제금액=(
                "결제금액(포인트포함)",
                "mean"
            ),

            평균PV당매출=(
                "PV당매출",
                "mean"
            ),

            평균할인율=(
                "할인율",
                "mean"
            ),
        )
        .reset_index()
    )

    summary["표본수준"] = (
        summary["편성완료수"]
        .apply(get_sample_level)
    )

    return summary


# =========================================================
# 상품별 성과 요약
# =========================================================

def make_product_summary(
    performance_df
):

    if performance_df.empty:
        return pd.DataFrame()

    summary = (
        performance_df
        .groupby(
            [
                "대표상품코드",
                "상품명",
                "브랜드명",
                "대카테고리",
                "중카테고리",
            ],
            dropna=False
        )
        .agg(
            편성횟수=(
                "대표상품코드",
                "size"
            ),

            평균PV=(
                "PV",
                "mean"
            ),

            평균결제수량=(
                "결제수량",
                "mean"
            ),

            평균CVR=(
                "CVR",
                "mean"
            ),

            평균결제금액=(
                "결제금액(포인트포함)",
                "mean"
            ),

            평균PV당매출=(
                "PV당매출",
                "mean"
            ),

            평균할인율=(
                "할인율",
                "mean"
            ),
        )
        .reset_index()
    )

    return summary


# =========================================================
# 가격대별 성과
# =========================================================

def make_price_summary(
    performance_df
):

    summary = (
        performance_df
        .groupby(
            "혜택가가격대",
            observed=True
        )
        .agg(
            편성수=(
                "대표상품코드",
                "size"
            ),

            평균PV=(
                "PV",
                "mean"
            ),

            평균결제수량=(
                "결제수량",
                "mean"
            ),

            평균CVR=(
                "CVR",
                "mean"
            ),

            평균결제금액=(
                "결제금액(포인트포함)",
                "mean"
            ),

            평균PV당매출=(
                "PV당매출",
                "mean"
            ),

            평균할인율=(
                "할인율",
                "mean"
            ),
        )
        .reset_index()
    )

    price_order_map = {
        "<5만원": 0,
        "5만원 미만": 0,
        "5~10만원": 1,
        "10~20만원": 2,
        "20~30만원": 3,
        "30~50만원": 4,
        "50만원 이상": 5,
    }

    summary["정렬순서"] = (
        summary["혜택가가격대"]
        .astype(str)
        .map(price_order_map)
        .fillna(999)
    )

    summary = (
        summary
        .sort_values("정렬순서")
        .drop(columns=["정렬순서"])
    )

    return summary


# =========================================================
# 할인율별 성과
# =========================================================

def make_discount_summary(
    performance_df
):

    discount_order = [
        "10% 이하",
        "10~20%",
        "20~30%",
        "30~40%",
        "40~50%",
        "50~60%",
        "60% 초과",
    ]

    temp = add_discount_band(
        performance_df
    )

    summary = (
        temp
        .groupby(
            "할인율구간",
            observed=True
        )
        .agg(
            편성수=(
                "대표상품코드",
                "size"
            ),

            평균PV=(
                "PV",
                "mean"
            ),

            평균결제수량=(
                "결제수량",
                "mean"
            ),

            평균CVR=(
                "CVR",
                "mean"
            ),

            평균결제금액=(
                "결제금액(포인트포함)",
                "mean"
            ),

            평균PV당매출=(
                "PV당매출",
                "mean"
            ),

            평균혜택가=(
                "최종혜택가",
                "mean"
            ),
        )
        .reset_index()
    )

    summary["할인율구간"] = (
        summary["할인율구간"]
        .astype(str)
    )

    summary["정렬순서"] = (
        summary["할인율구간"]
        .map(
            {
                value: index
                for index, value
                in enumerate(
                    discount_order
                )
            }
        )
    )

    summary = (
        summary
        .sort_values("정렬순서")
        .drop(columns=["정렬순서"])
    )

    return summary


# =========================================================
# 혜택가 가격대 × 할인율 조합 분석
# =========================================================

def make_price_discount_matrix(
    performance_df
):

    price_order = [
        "<5만원",
        "5만원 미만",
        "5~10만원",
        "10~20만원",
        "20~30만원",
        "30~50만원",
        "50만원 이상",
    ]

    discount_order = [
        "10% 이하",
        "10~20%",
        "20~30%",
        "30~40%",
        "40~50%",
        "50~60%",
        "60% 초과",
    ]

    temp = add_discount_band(
        performance_df
    ).copy()

    temp = temp[
        temp["혜택가가격대"].notna()
        &
        temp["할인율구간"].notna()
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    summary = (
        temp
        .groupby(
            [
                "혜택가가격대",
                "할인율구간",
            ],
            observed=True
        )
        .agg(
            편성수=(
                "대표상품코드",
                "size"
            ),

            평균결제금액=(
                "결제금액(포인트포함)",
                "mean"
            ),
        )
        .reset_index()
    )

    summary["혜택가가격대"] = (
        summary["혜택가가격대"]
        .astype(str)
    )

    summary["할인율구간"] = (
        summary["할인율구간"]
        .astype(str)
    )

    summary["표시값"] = summary.apply(
        lambda row:
            (
                f"{row['평균결제금액']:,.0f}원 "
                f"(n={int(row['편성수'])})"
            ),
        axis=1
    )

    matrix = (
        summary
        .pivot(
            index="혜택가가격대",
            columns="할인율구간",
            values="표시값"
        )
    )

    existing_prices = (
        matrix.index
        .astype(str)
        .tolist()
    )

    ordered_prices = [
        value
        for value in price_order
        if value in existing_prices
    ]

    ordered_prices += [
        value
        for value in existing_prices
        if value not in ordered_prices
    ]

    existing_discounts = (
        matrix.columns
        .astype(str)
        .tolist()
    )

    ordered_discounts = [
        value
        for value in discount_order
        if value in existing_discounts
    ]

    matrix = matrix.reindex(
        index=ordered_prices,
        columns=ordered_discounts
    )

    matrix = (
        matrix
        .fillna("-")
        .reset_index()
        .rename(
            columns={
                "혜택가가격대":
                    "혜택가 가격대"
            }
        )
    )

    return matrix


# =========================================================
# 카테고리 표 표시용
# =========================================================

def prepare_category_table(
    summary_df
):

    table = summary_df.copy()

    table["평균PV"] = (
        table["평균PV"]
        .round(1)
    )

    table["평균결제수량"] = (
        table["평균결제수량"]
        .round(1)
    )

    table["평균CVR"] = (
        table["평균CVR"]
        * 100
    ).round(2)

    table["평균결제금액"] = (
        table["평균결제금액"]
        .round(0)
    )

    table["평균PV당매출"] = (
        table["평균PV당매출"]
        .round(0)
    )

    table["평균할인율"] = (
        table["평균할인율"]
        .round(1)
    )

    return table.rename(
        columns={
            "편성완료수":
                "편성완료 수",

            "상품수":
                "상품 수",

            "평균PV":
                "평균 PV",

            "평균결제수량":
                "평균 결제수량",

            "평균CVR":
                "평균 CVR(%)",

            "평균결제금액":
                "편성당 평균 매출",

            "평균PV당매출":
                "평균 PV당 매출",

            "평균할인율":
                "평균 할인율(%)",

            "표본수준":
                "표본 수준",
        }
    )


# =========================================================
# 상품 상세
# =========================================================

def show_product_detail(
    df,
    product_code
):

    # =====================================================
    # 전체 상품 이력
    # =====================================================

    history = search_product(
        df,
        product_code
    )

    if history.empty:
        st.warning(
            "해당 상품의 편성 이력을 찾지 못했습니다."
        )
        return

    history = (
        history
        .sort_values("날짜")
    )

    latest = history.iloc[-1]

    target_code = latest["대표상품코드"]

    # =====================================================
    # 상품 기본 정보
    # =====================================================

    st.divider()

    st.subheader(
        "상품 기본 정보"
    )

    st.markdown(
        f"### {latest['상품명']}"
    )

    info1, info2, info3, info4 = st.columns(4)

    with info1:
        st.write("**브랜드**")
        st.write(
            latest["브랜드명"]
        )

    with info2:
        st.write("**대카테고리**")
        st.write(
            latest["대카테고리"]
        )

    with info3:
        st.write("**중카테고리**")
        st.write(
            latest["중카테고리"]
        )

    with info4:
        st.write("**혜택가 가격대**")
        st.write(
            latest["혜택가가격대"]
        )

    st.caption(
        f"대표상품코드: {latest['대표상품코드']} "
        f"| 전체옵션코드: {latest['전체옵션코드']}"
    )

    # =====================================================
    # 성과 분석 기간
    # =====================================================

    st.markdown(
        "#### 성과 분석 기간"
    )

    product_period_option = (
        st.selectbox(
            "KPI와 비교군에 적용할 기간",
            [
                "전체",
                "최근 6개월",
                "최근 1년",
                "직접 선택",
            ],
            key=f"product_period_{target_code}"
        )
    )

    period_df = df.copy()

    today = (
        pd.Timestamp.today()
        .normalize()
    )

    if product_period_option == "최근 6개월":

        start_date = (
            today
            - pd.DateOffset(months=6)
        )

        period_df = (
            period_df[
                (
                    period_df["날짜"]
                    >= start_date
                )
                &
                (
                    period_df["날짜"]
                    <= today
                )
            ]
            .copy()
        )

    elif product_period_option == "최근 1년":

        start_date = (
            today
            - pd.DateOffset(years=1)
        )

        period_df = (
            period_df[
                (
                    period_df["날짜"]
                    >= start_date
                )
                &
                (
                    period_df["날짜"]
                    <= today
                )
            ]
            .copy()
        )

    elif product_period_option == "직접 선택":

        valid_dates = (
            df["날짜"]
            .dropna()
        )

        if not valid_dates.empty:

            min_date = (
                valid_dates
                .min()
                .date()
            )

            max_date = (
                valid_dates
                .max()
                .date()
            )

            product_date_range = (
                st.date_input(
                    "조회 기간 선택",
                    value=(
                        min_date,
                        max_date
                    ),
                    min_value=min_date,
                    max_value=max_date,
                    key=f"product_date_range_{target_code}"
                )
            )

            if (
                isinstance(
                    product_date_range,
                    (list, tuple)
                )
                and len(product_date_range) == 2
            ):

                start_date = pd.Timestamp(
                    product_date_range[0]
                )

                end_date = pd.Timestamp(
                    product_date_range[1]
                )

                period_df = (
                    period_df[
                        (
                            period_df["날짜"]
                            >= start_date
                        )
                        &
                        (
                            period_df["날짜"]
                            <= end_date
                        )
                    ]
                    .copy()
                )

    # =====================================================
    # 선택 기간의 검색 상품 성과
    # =====================================================

    period_history = search_product(
        period_df,
        product_code
    )

    period_completed = (
        period_history[
            period_history["성과상태"]
            == "성과완료"
        ]
        .copy()
    )

    # =====================================================
    # 전체 과거 / 예정 이력
    # =====================================================

    completed = (
        history[
            history["성과상태"]
            == "성과완료"
        ]
        .copy()
    )

    scheduled = (
        history[
            history["성과상태"]
            == "예정편성"
        ]
        .copy()
    )

    # =====================================================
    # 과거 편성 성과
    # =====================================================

    st.divider()

    st.subheader(
        "과거 편성 성과"
    )

    st.caption(
        "아래 KPI는 선택한 분석 기간의 편성완료 데이터만 반영합니다."
    )

    if period_completed.empty:

        product_average = None

        st.info(
            "선택한 기간에 해당 상품의 편성완료 이력이 없습니다."
        )

    else:

        product_average = (
            calculate_product_average(
                period_completed
            )
        )

        average_quantity = (
            period_completed[
                "결제수량"
            ]
            .dropna()
            .mean()
        )

        k1, k2, k3, k4 = (
            st.columns(4)
        )

        with k1:
            st.metric(
                "편성 횟수",
                f"{len(period_completed):,}회"
            )

        with k2:
            st.metric(
                "편성당 평균 매출",
                format_money(
                    product_average[
                        "평균결제금액"
                    ]
                )
            )

        with k3:
            st.metric(
                "평균 결제수량",
                format_number(
                    average_quantity
                )
            )

        with k4:
            st.metric(
                "평균 할인율",
                format_discount(
                    product_average[
                        "평균할인율"
                    ]
                )
            )

    # =====================================================
    # 전체 과거 편성 이력
    # =====================================================

    st.markdown(
        "#### 과거 편성 이력"
    )

    st.caption(
        "편성 이력 표는 분석 기간과 관계없이 전체 과거 이력을 보여줍니다."
    )

    if completed.empty:

        st.write(
            "과거 편성 이력 없음"
        )

    else:

        completed_view = (
            completed[
                [
                    "날짜",
                    "요일",
                    "순서",
                    "정상가",
                    "최종혜택가",
                    "할인율",
                    "결제수량",
                    "결제금액(포인트포함)",
                ]
            ]
            .sort_values(
                "날짜",
                ascending=False
            )
            .copy()
        )

        completed_view["날짜"] = (
            completed_view["날짜"]
            .dt.strftime(
                "%Y-%m-%d"
            )
        )

        st.dataframe(
            completed_view,
            use_container_width=True,
            hide_index=True
        )

    # =====================================================
    # 예정 편성
    # =====================================================

    st.divider()

    st.subheader(
        "예정 편성"
    )

    if scheduled.empty:

        st.write(
            "예정 편성 없음"
        )

    else:

        scheduled_view = (
            scheduled[
                [
                    "날짜",
                    "요일",
                    "순서",
                    "정상가",
                    "최종혜택가",
                    "할인율",
                ]
            ]
            .sort_values(
                "날짜",
                ascending=True
            )
            .copy()
        )

        scheduled_view["날짜"] = (
            scheduled_view["날짜"]
            .dt.strftime(
                "%Y-%m-%d"
            )
        )

        st.dataframe(
            scheduled_view,
            use_container_width=True,
            hide_index=True
        )

    # =====================================================
    # 비교군 벤치마크
    # =====================================================

    completed_all = (
        period_df[
            period_df["성과상태"]
            == "성과완료"
        ]
        .copy()
    )

    brand_benchmark = (
        calculate_benchmark(
            completed_all,
            "브랜드명",
            latest["브랜드명"],
            target_code
        )
    )

    category_benchmark = (
        calculate_benchmark(
            completed_all,
            "중카테고리",
            latest["중카테고리"],
            target_code
        )
    )

    price_benchmark = (
        calculate_benchmark(
            completed_all,
            "혜택가가격대",
            latest["혜택가가격대"],
            target_code
        )
    )

    st.divider()

    st.subheader(
        "비교군 벤치마크"
    )

    st.caption(
        "선택한 분석 기간의 편성완료 데이터를 기준으로 비교합니다. "
        "검색 상품 자체의 성과는 비교군 평균에서 제외합니다."
    )

    for title, benchmark in [
        (
            f"동일 브랜드 · {latest['브랜드명']}",
            brand_benchmark
        ),
        (
            f"동일 중카테고리 · {latest['중카테고리']}",
            category_benchmark
        ),
        (
            f"동일 혜택가 가격대 · {latest['혜택가가격대']}",
            price_benchmark
        ),
    ]:

        st.markdown(
            f"### {title}"
        )

        if benchmark is None:

            st.info(
                "비교 가능한 과거 성과가 없습니다."
            )

        else:

            b1, b2 = (
                st.columns(2)
            )

            with b1:

                st.metric(
                    "비교 편성 수",
                    f"{benchmark['건수']}건"
                )

            with b2:

                st.metric(
                    "표본 수준",
                    benchmark[
                        "표본수준"
                    ]
                )

            st.dataframe(
                make_benchmark_table(
                    benchmark,
                    product_average
                ),
                use_container_width=True,
                hide_index=True
            )


# =========================================================
# 앱 시작
# =========================================================


st.title(
    "딜특가 의사결정 지원 대시보드"
)

st.caption(
    "Google Sheet 최신 데이터를 기반으로 유사 상품군의 과거 성과를 비교합니다."
)


# =========================================================
# 데이터 로드 + MASTER 동기화
# =========================================================

try:

    with st.spinner(
        "Google Sheet와 상품 MASTER를 확인하는 중..."
    ):

        df, sync_result = (
            load_final_data()
        )

except PermissionError:

    st.error(
        "상품 MASTER CSV가 다른 프로그램에서 열려 있어 저장할 수 없습니다."
    )

    st.write(
        "Excel에서 `상품_MASTER_브랜드보완.csv`를 닫은 뒤 브라우저를 새로고침해주세요."
    )

    st.stop()

except Exception as e:

    st.error(
        "데이터를 불러오는 중 오류가 발생했습니다."
    )

    st.exception(e)

    st.stop()


# =========================================================
# 자동 동기화 결과 안내
# =========================================================

if sync_result["new_count"] > 0:

    st.success(
        f"신규 상품 {sync_result['new_count']:,}개를 "
        f"MASTER에 자동 추가했습니다."
    )

    if (
        sync_result[
            "unclassified_count"
        ]
        > 0
    ):

        st.warning(
            f"신규 상품 중 "
            f"{sync_result['unclassified_count']:,}개는 "
            f"카테고리 확인이 필요합니다."
        )


# =========================================================
# 전체 현황
# =========================================================

completed_count = (
    df["성과상태"]
    .eq("성과완료")
    .sum()
)

scheduled_count = (
    df["성과상태"]
    .eq("예정편성")
    .sum()
)

top1, top2, top3 = (
    st.columns(3)
)

with top1:
    st.metric(
        "전체 편성",
        f"{len(df):,}건"
    )

with top2:
    st.metric(
        "편성 완료",
        f"{completed_count:,}건"
    )

with top3:
    st.metric(
        "예정 편성",
        f"{scheduled_count:,}건"
    )

st.divider()

# =========================================================
# 탭
# =========================================================

overview_tab, operation_tab, category_tab, price_tab, search_tab = (
    st.tabs(
        [
            "📈 Overview",
            "📅 운영·추이 분석",
            "📊 카테고리 성과 분석",
            "💰 가격·혜택 분석",
            "🔎 상품 검색",
        ]
    )
)


# =========================================================
# 0. Overview
# =========================================================

with overview_tab:

    st.subheader(
        "딜특가 전체 성과"
    )

    st.caption(
        "선택한 기간의 편성완료 데이터를 기준으로 전체 성과를 확인합니다."
    )

    # =====================================================
    # 기간 필터
    # =====================================================

    overview_period = st.selectbox(
        "분석 기간",
        [
            "최근 30일",
            "최근 3개월",
            "최근 6개월",
            "최근 1년",
            "전체",
            "직접 선택",
        ],
        key="overview_period"
    )

    overview_df = df[
        df["성과상태"]
        == "성과완료"
    ].copy()

    today = (
        pd.Timestamp.today()
        .normalize()
    )

    if overview_period == "최근 30일":

        start_date = (
            today
            - pd.DateOffset(days=30)
        )

        overview_df = overview_df[
            (
                overview_df["날짜"]
                >= start_date
            )
            &
            (
                overview_df["날짜"]
                <= today
            )
        ].copy()

    elif overview_period == "최근 3개월":

        start_date = (
            today
            - pd.DateOffset(months=3)
        )

        overview_df = overview_df[
            (
                overview_df["날짜"]
                >= start_date
            )
            &
            (
                overview_df["날짜"]
                <= today
            )
        ].copy()

    elif overview_period == "최근 6개월":

        start_date = (
            today
            - pd.DateOffset(months=6)
        )

        overview_df = overview_df[
            (
                overview_df["날짜"]
                >= start_date
            )
            &
            (
                overview_df["날짜"]
                <= today
            )
        ].copy()

    elif overview_period == "최근 1년":

        start_date = (
            today
            - pd.DateOffset(years=1)
        )

        overview_df = overview_df[
            (
                overview_df["날짜"]
                >= start_date
            )
            &
            (
                overview_df["날짜"]
                <= today
            )
        ].copy()

    elif overview_period == "직접 선택":

        valid_dates = (
            df["날짜"]
            .dropna()
        )

        if not valid_dates.empty:

            min_date = (
                valid_dates
                .min()
                .date()
            )

            max_date = (
                valid_dates
                .max()
                .date()
            )

            overview_date_range = st.date_input(
                "조회 기간 선택",
                value=(
                    min_date,
                    max_date
                ),
                min_value=min_date,
                max_value=max_date,
                key="overview_date_range"
            )

            if (
                isinstance(
                    overview_date_range,
                    (list, tuple)
                )
                and len(overview_date_range) == 2
            ):

                start_date = pd.Timestamp(
                    overview_date_range[0]
                )

                end_date = pd.Timestamp(
                    overview_date_range[1]
                )

                overview_df = overview_df[
                    (
                        overview_df["날짜"]
                        >= start_date
                    )
                    &
                    (
                        overview_df["날짜"]
                        <= end_date
                    )
                ].copy()

    # =====================================================
    # KPI
    # =====================================================

    if overview_df.empty:

        st.info(
            "선택한 기간에 해당하는 편성완료 데이터가 없습니다."
        )

    else:

        total_revenue = (
            overview_df[
                "결제금액(포인트포함)"
            ]
            .sum()
        )

        total_placements = (
            len(
                overview_df
            )
        )

        avg_revenue = (
            overview_df[
                "결제금액(포인트포함)"
            ]
            .mean()
        )

        active_days = (
            overview_df["날짜"]
            .dt.normalize()
            .nunique()
        )

        avg_daily_revenue = (
            total_revenue
            / active_days
            if active_days > 0
            else 0
        )

        o1, o2, o3, o4 = (
            st.columns(4)
        )

        with o1:
            st.metric(
                "기간 총 매출",
                format_money(
                    total_revenue
                )
            )

        with o2:
            st.metric(
                "일평균 매출",
                format_money(
                    avg_daily_revenue
                )
            )

        with o3:
            st.metric(
                "편성당 평균 매출",
                format_money(
                    avg_revenue
                )
            )

        with o4:
            st.metric(
                "편성 수",
                f"{total_placements:,}건"
            )

       
        # =================================================
        # 월별 편성 효율 추이
        # =================================================

        st.divider()

        st.markdown(
            "### 월별 편성 효율 추이"
        )

        st.caption(
            "월별 편성 수 차이를 고려해 편성당 평균 매출을 기준으로 비교합니다."
        )

        monthly_temp = (
            overview_df
            .copy()
        )

        monthly_temp[
            "연월"
        ] = (
            monthly_temp[
                "날짜"
            ]
            .dt.to_period("M")
            .astype(str)
        )

        monthly_summary = (
            monthly_temp
            .groupby(
                "연월"
            )
            .agg(
                총매출=(
                    "결제금액(포인트포함)",
                    "sum"
                ),

                편성수=(
                    "대표상품코드",
                    "size"
                ),

                편성당평균매출=(
                    "결제금액(포인트포함)",
                    "mean"
                ),

                총결제수량=(
                    "결제수량",
                    "sum"
                ),
            )
            .reset_index()
            .sort_values(
                "연월"
            )
        )

        # -------------------------------------------------
        # 그래프
        # -------------------------------------------------

        monthly_chart = (
            monthly_summary[
                [
                    "연월",
                    "편성당평균매출",
                ]
            ]
            .copy()
            .set_index(
                "연월"
            )
        )

        st.line_chart(
            monthly_chart
        )

        # -------------------------------------------------
        # 표
        # -------------------------------------------------

        monthly_table = (
            monthly_summary
            .copy()
        )

        monthly_table[
            "총매출"
        ] = (
            monthly_table[
                "총매출"
            ]
            .round(0)
            .astype("Int64")
        )

        monthly_table[
            "편성당평균매출"
        ] = (
            monthly_table[
                "편성당평균매출"
            ]
            .round(0)
            .astype("Int64")
        )

        monthly_table[
            "총결제수량"
        ] = (
            monthly_table[
                "총결제수량"
            ]
            .round(0)
            .astype("Int64")
        )

        monthly_table = (
            monthly_table
            .rename(
                columns={
                    "연월":
                        "월",

                    "총매출":
                        "총 매출",

                    "편성수":
                        "편성 수",

                    "편성당평균매출":
                        "편성당 평균 매출",

                    "총결제수량":
                        "총 결제수량",
                }
            )
        )

        st.dataframe(
            monthly_table,
            use_container_width=True,
            hide_index=True
        )

        # =================================================
        # 카테고리 매출 기여도
        # =================================================

        st.divider()

        st.markdown(
            "### 카테고리 매출 기여도"
        )

        st.caption(
            "선택 기간 내 대카테고리별 편성 비중과 매출 기여도를 비교합니다."
        )

        category_contribution = (
            overview_df
            .groupby(
                "대카테고리"
            )
            .agg(
                편성수=(
                    "대표상품코드",
                    "size"
                ),

                총매출=(
                    "결제금액(포인트포함)",
                    "sum"
                ),

                편성당평균매출=(
                    "결제금액(포인트포함)",
                    "mean"
                ),
            )
            .reset_index()
        )

        category_contribution = (
            category_contribution[
                category_contribution[
                    "대카테고리"
                ]
                .fillna("")
                != "미분류"
            ]
            .copy()
        )

        total_category_placements = (
            category_contribution[
                "편성수"
            ]
            .sum()
        )

        total_category_revenue = (
            category_contribution[
                "총매출"
            ]
            .sum()
        )

        category_contribution[
            "편성비중"
        ] = (
            category_contribution[
                "편성수"
            ]
            / total_category_placements
            * 100
        )

        category_contribution[
            "매출비중"
        ] = (
            category_contribution[
                "총매출"
            ]
            / total_category_revenue
            * 100
        )

        category_contribution[
            "기여도차이"
        ] = (
            category_contribution[
                "매출비중"
            ]
            - category_contribution[
                "편성비중"
            ]
        )

        category_contribution = (
            category_contribution
            .sort_values(
                "매출비중",
                ascending=False
            )
        )

        contribution_chart = (
            category_contribution[
                [
                    "대카테고리",
                    "편성비중",
                    "매출비중",
                ]
            ]
            .copy()
            .set_index(
                "대카테고리"
            )
        )

        st.bar_chart(
            contribution_chart
        )

        contribution_table = (
            category_contribution
            .copy()
        )

        contribution_table[
            "총매출"
        ] = (
            contribution_table[
                "총매출"
            ]
            .round(0)
            .astype("Int64")
        )

        contribution_table[
            "편성당평균매출"
        ] = (
            contribution_table[
                "편성당평균매출"
            ]
            .round(0)
            .astype("Int64")
        )

        contribution_table[
            "편성비중"
        ] = (
            contribution_table[
                "편성비중"
            ]
            .round(1)
        )

        contribution_table[
            "매출비중"
        ] = (
            contribution_table[
                "매출비중"
            ]
            .round(1)
        )

        contribution_table[
            "기여도차이"
        ] = (
            contribution_table[
                "기여도차이"
            ]
            .round(1)
        )

        contribution_table = (
            contribution_table
            .rename(
                columns={
                    "대카테고리":
                        "카테고리",

                    "편성수":
                        "편성 수",

                    "총매출":
                        "총 매출",

                    "편성당평균매출":
                        "편성당 평균 매출",

                    "편성비중":
                        "편성 비중(%)",

                    "매출비중":
                        "매출 비중(%)",

                    "기여도차이":
                        "매출 비중 - 편성 비중(%p)",
                }
            )
        )

        st.dataframe(
            contribution_table,
            use_container_width=True,
            hide_index=True
        )
        # =================================================
        # 브랜드 성과 TOP 10
        # =================================================

        st.divider()

        st.markdown(
            "### 브랜드 성과 TOP 10"
        )

        st.caption(
            "선택 기간 내 브랜드별 총 매출과 편성 효율을 함께 확인합니다."
        )

        brand_summary = (
            overview_df
            .groupby(
                "브랜드명"
            )
            .agg(
                편성수=(
                    "대표상품코드",
                    "size"
                ),

                총매출=(
                    "결제금액(포인트포함)",
                    "sum"
                ),

                편성당평균매출=(
                    "결제금액(포인트포함)",
                    "mean"
                ),

                평균결제수량=(
                    "결제수량",
                    "mean"
                ),
            )
            .reset_index()
        )

        brand_summary = (
            brand_summary[
                brand_summary[
                    "브랜드명"
                ]
                .fillna("")
                .str.strip()
                != ""
            ]
            .copy()
        )

        brand_top10 = (
            brand_summary
            .sort_values(
                "총매출",
                ascending=False
            )
            .head(10)
            .copy()
        )

        brand_chart = (
            brand_top10[
                [
                    "브랜드명",
                    "총매출",
                ]
            ]
            .copy()
            .set_index(
                "브랜드명"
            )
        )

        st.bar_chart(
            brand_chart
        )

        brand_table = (
            brand_top10
            .copy()
        )

        brand_table[
            "총매출"
        ] = (
            brand_table[
                "총매출"
            ]
            .round(0)
            .astype("Int64")
        )

        brand_table[
            "편성당평균매출"
        ] = (
            brand_table[
                "편성당평균매출"
            ]
            .round(0)
            .astype("Int64")
        )

        brand_table[
            "평균결제수량"
        ] = (
            brand_table[
                "평균결제수량"
            ]
            .round(1)
        )

        brand_table = (
            brand_table
            .rename(
                columns={
                    "브랜드명":
                        "브랜드",

                    "편성수":
                        "편성 수",

                    "총매출":
                        "총 매출",

                    "편성당평균매출":
                        "편성당 평균 매출",

                    "평균결제수량":
                        "평균 결제수량",
                }
            )
        )

        st.dataframe(
            brand_table,
            use_container_width=True,
            hide_index=True
        )

        # =================================================
        # 브랜드 효율 TOP 10
        # =================================================

        st.divider()

        st.markdown(
            "### 브랜드 효율 TOP 10"
        )

        st.caption(
            "편성 3회 이상 브랜드 중 편성당 평균 매출이 높은 브랜드를 비교합니다."
        )

        efficient_brand_top10 = (
            brand_summary[
                brand_summary[
                    "편성수"
                ]
                >= 3
            ]
            .sort_values(
                "편성당평균매출",
                ascending=False
            )
            .head(10)
            .copy()
        )

        efficient_brand_chart = (
            efficient_brand_top10[
                [
                    "브랜드명",
                    "편성당평균매출",
                ]
            ]
            .copy()
            .set_index(
                "브랜드명"
            )
        )

        st.bar_chart(
            efficient_brand_chart
        )

        efficient_brand_table = (
            efficient_brand_top10
            .copy()
        )

        efficient_brand_table[
            "총매출"
        ] = (
            efficient_brand_table[
                "총매출"
            ]
            .round(0)
            .astype("Int64")
        )

        efficient_brand_table[
            "편성당평균매출"
        ] = (
            efficient_brand_table[
                "편성당평균매출"
            ]
            .round(0)
            .astype("Int64")
        )

        efficient_brand_table[
            "평균결제수량"
        ] = (
            efficient_brand_table[
                "평균결제수량"
            ]
            .round(1)
        )

        efficient_brand_table = (
            efficient_brand_table
            .rename(
                columns={
                    "브랜드명":
                        "브랜드",

                    "편성수":
                        "편성 수",

                    "총매출":
                        "총 매출",

                    "편성당평균매출":
                        "편성당 평균 매출",

                    "평균결제수량":
                        "평균 결제수량",
                }
            )
        )

        st.dataframe(
            efficient_brand_table,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# 운영·추이 분석
# =========================================================

with operation_tab:

    st.subheader(
        "운영·추이 분석"
    )

    st.caption(
        "일별·요일별 편성 성과와 운영 패턴을 확인합니다."
    )

    # =====================================================
    # 일별 매출 추이
    # =====================================================

    st.divider()

    st.markdown(
        "### 일별 매출 추이"
    )

    daily_summary = (
        overview_df
        .groupby(
            overview_df["날짜"]
            .dt.normalize()
        )
        .agg(
            일매출=(
                "결제금액(포인트포함)",
                "sum"
            ),

            편성수=(
                "대표상품코드",
                "size"
            ),
        )
        .reset_index()
    )

    daily_summary = (
        daily_summary
        .sort_values(
            "날짜"
        )
    )

    daily_chart = (
        daily_summary[
            [
                "날짜",
                "일매출",
            ]
        ]
        .copy()
        .set_index(
            "날짜"
        )
    )

    st.line_chart(
        daily_chart
    )

    daily_table = (
        daily_summary
        .copy()
    )

    daily_table[
        "날짜"
    ] = (
        daily_table[
            "날짜"
        ]
        .dt.strftime(
            "%Y-%m-%d"
        )
    )

    daily_table[
        "일매출"
    ] = (
        daily_table[
            "일매출"
        ]
        .round(0)
        .astype("Int64")
    )

    daily_table = (
        daily_table
        .rename(
            columns={
                "일매출":
                    "총 매출",

                "편성수":
                    "편성 수",
            }
        )
    )

    st.dataframe(
        daily_table,
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # 요일별 편성 효율
    # =====================================================

    st.divider()

    st.markdown(
        "### 요일별 편성 효율"
    )

    st.caption(
        "요일별 편성 수 차이를 고려해 편성당 평균 매출을 중심으로 비교합니다."
    )

    weekday_order = [
        "월",
        "화",
        "수",
        "목",
        "금",
        "토",
        "일",
    ]

    weekday_temp = (
        overview_df
        .copy()
    )

    weekday_temp[
        "요일명"
    ] = (
        weekday_temp[
            "날짜"
        ]
        .dt.dayofweek
        .map(
            {
                0: "월",
                1: "화",
                2: "수",
                3: "목",
                4: "금",
                5: "토",
                6: "일",
            }
        )
    )

    # -------------------------------------------------
    # 날짜 단위 성과
    # -------------------------------------------------

    weekday_daily = (
        weekday_temp
        .groupby(
            [
                weekday_temp[
                    "날짜"
                ]
                .dt.normalize(),
                "요일명",
            ]
        )
        .agg(
            일매출=(
                "결제금액(포인트포함)",
                "sum"
            ),

            일편성수=(
                "대표상품코드",
                "size"
            ),
        )
        .reset_index()
    )

    # -------------------------------------------------
    # 요일별 요약
    # -------------------------------------------------

    weekday_summary = (
        weekday_temp
        .groupby(
            "요일명"
        )
        .agg(
            편성당평균매출=(
                "결제금액(포인트포함)",
                "mean"
            ),

            편성당평균결제수량=(
                "결제수량",
                "mean"
            ),
        )
        .reset_index()
    )

    weekday_daily_summary = (
        weekday_daily
        .groupby(
            "요일명"
        )
        .agg(
            평균일매출=(
                "일매출",
                "mean"
            ),

            평균편성수=(
                "일편성수",
                "mean"
            ),
        )
        .reset_index()
    )

    weekday_summary = (
        weekday_summary
        .merge(
            weekday_daily_summary,
            on="요일명",
            how="left"
        )
    )

    weekday_summary[
        "정렬순서"
    ] = (
        weekday_summary[
            "요일명"
        ]
        .map(
            {
                day: index
                for index, day
                in enumerate(
                    weekday_order
                )
            }
        )
    )

    weekday_summary = (
        weekday_summary
        .sort_values(
            "정렬순서"
        )
        .drop(
            columns=[
                "정렬순서"
            ]
        )
    )

    # -------------------------------------------------
    # 그래프
    # -------------------------------------------------

    weekday_chart = (
        weekday_summary[
            [
                "요일명",
                "편성당평균매출",
            ]
        ]
        .copy()
        .set_index(
            "요일명"
        )
    )

    st.bar_chart(
        weekday_chart
    )

    # -------------------------------------------------
    # 표
    # -------------------------------------------------

    weekday_table = (
        weekday_summary
        .copy()
    )

    weekday_table[
        "평균일매출"
    ] = (
        weekday_table[
            "평균일매출"
        ]
        .round(0)
        .astype("Int64")
    )

    weekday_table[
        "편성당평균매출"
    ] = (
        weekday_table[
            "편성당평균매출"
        ]
        .round(0)
        .astype("Int64")
    )

    weekday_table[
        "평균편성수"
    ] = (
        weekday_table[
            "평균편성수"
        ]
        .round(1)
    )

    weekday_table[
        "편성당평균결제수량"
    ] = (
        weekday_table[
            "편성당평균결제수량"
        ]
        .round(1)
    )

    weekday_table = (
        weekday_table
        .rename(
            columns={
                "요일명":
                    "요일",

                "편성당평균매출":
                    "편성당 평균 매출",

                "편성당평균결제수량":
                    "편성당 평균 결제수량",

                "평균일매출":
                    "평균 일 매출",

                "평균편성수":
                    "평균 편성 수",
            }
        )
    )

    st.dataframe(
        weekday_table,
        use_container_width=True,
        hide_index=True
    )
    # =====================================================
    # 전시순서별 편성 효율
    # =====================================================

    st.divider()

    st.markdown(
        "### 전시순서별 편성 효율"
    )

    st.caption(
        "전시순서별 편성당 평균 매출과 결제수량을 비교합니다. "
        "전시 위치와 성과의 관계를 참고용으로 확인할 수 있습니다."
    )

    order_temp = (
        overview_df[
            overview_df["순서"].notna()
        ]
        .copy()
    )

    if order_temp.empty:

        st.info(
            "전시순서 분석이 가능한 데이터가 없습니다."
        )

    else:

        order_temp[
            "순서정렬"
        ] = pd.to_numeric(
            order_temp["순서"],
            errors="coerce"
        )

        order_summary = (
            order_temp
            .groupby(
                [
                    "순서",
                    "순서정렬",
                ],
                dropna=False
            )
            .agg(
                편성수=(
                    "대표상품코드",
                    "size"
                ),

                편성당평균매출=(
                    "결제금액(포인트포함)",
                    "mean"
                ),

                평균결제수량=(
                    "결제수량",
                    "mean"
                ),
            )
            .reset_index()
            .sort_values(
                [
                    "순서정렬",
                    "순서",
                ]
            )
        )

        # -------------------------------------------------
        # 그래프
        # -------------------------------------------------

        order_chart = (
            order_summary[
                [
                    "순서",
                    "편성당평균매출",
                ]
            ]
            .copy()
        )

        order_chart[
            "순서"
        ] = (
            order_chart[
                "순서"
            ]
            .astype(str)
        )

        order_chart = (
            order_chart
            .set_index(
                "순서"
            )
        )

        st.bar_chart(
            order_chart
        )

        # -------------------------------------------------
        # 표
        # -------------------------------------------------

        order_table = (
            order_summary[
                [
                    "순서",
                    "편성수",
                    "편성당평균매출",
                    "평균결제수량",
                ]
            ]
            .copy()
        )

        order_table[
            "편성당평균매출"
        ] = (
            order_table[
                "편성당평균매출"
            ]
            .round(0)
            .astype("Int64")
        )

        order_table[
            "평균결제수량"
        ] = (
            order_table[
                "평균결제수량"
            ]
            .round(1)
        )

        order_table = (
            order_table
            .rename(
                columns={
                    "순서":
                        "전시순서",

                    "편성수":
                        "편성 수",

                    "편성당평균매출":
                        "편성당 평균 매출",

                    "평균결제수량":
                        "평균 결제수량",
                }
            )
        )

        st.dataframe(
            order_table,
            use_container_width=True,
            hide_index=True
        )
    # =====================================================
    # 브랜드 기간별 성과 변화
    # =====================================================

    st.divider()

    st.markdown(
        "### 브랜드 기간별 성과 변화"
    )

    st.caption(
        "선택한 기간과 바로 이전 동일 기간을 비교하고, 원하는 기준으로 브랜드를 정렬합니다."
    )

    # -----------------------------------------------------
    # 비교 기간 선택
    # -----------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:
        growth_period_label = st.selectbox(
            "비교 기간",
            [
                "1개월",
                "3개월",
                "6개월",
                "12개월",
            ],
            index=1,
            key="brand_growth_period"
        )

    with col2:
        growth_sort_option = st.selectbox(
            "정렬 기준",
            [
                "증감률 높은 순",
                "증감률 낮은 순",
                "최근 편성당 평균 매출 높은 순",
                "최근 총매출 높은 순",
                "최근 편성 수 많은 순",
                "매출 증가액 큰 순",
            ],
            index=0,
            key="brand_growth_sort"
        )

    growth_period_map = {
        "1개월": 1,
        "3개월": 3,
        "6개월": 6,
        "12개월": 12,
    }

    growth_months = (
        growth_period_map[
            growth_period_label
        ]
    )

    # -----------------------------------------------------
    # 성과 완료 데이터
    # -----------------------------------------------------

    growth_base = (
        df[
            df["성과상태"]
            == "성과완료"
        ]
        .copy()
    )

    if growth_base.empty:

        st.info(
            "브랜드 기간 비교가 가능한 데이터가 없습니다."
        )

    else:

        # -------------------------------------------------
        # 데이터의 가장 최근 날짜를 기준일로 사용
        # -------------------------------------------------

        growth_end = (
            growth_base[
                "날짜"
            ]
            .max()
            .normalize()
        )

        recent_start = (
            growth_end
            - pd.DateOffset(
                months=growth_months
            )
        )

        previous_start = (
            recent_start
            - pd.DateOffset(
                months=growth_months
            )
        )

        # -------------------------------------------------
        # 최근 기간
        # -------------------------------------------------

        recent_brand_df = (
            growth_base[
                (
                    growth_base[
                        "날짜"
                    ]
                    >= recent_start
                )
                &
                (
                    growth_base[
                        "날짜"
                    ]
                    <= growth_end
                )
            ]
            .copy()
        )

        # -------------------------------------------------
        # 이전 동일 기간
        # -------------------------------------------------

        previous_brand_df = (
            growth_base[
                (
                    growth_base[
                        "날짜"
                    ]
                    >= previous_start
                )
                &
                (
                    growth_base[
                        "날짜"
                    ]
                    < recent_start
                )
            ]
            .copy()
        )

        st.caption(
            f"최근 {growth_period_label}: "
            f"{recent_start.strftime('%Y-%m-%d')} ~ "
            f"{growth_end.strftime('%Y-%m-%d')}  |  "
            f"이전 {growth_period_label}: "
            f"{previous_start.strftime('%Y-%m-%d')} ~ "
            f"{(recent_start - pd.Timedelta(days=1)).strftime('%Y-%m-%d')}"
        )

        # -------------------------------------------------
        # 최근 기간 브랜드 요약
        # -------------------------------------------------

        recent_brand_summary = (
            recent_brand_df
            .groupby(
                "브랜드명"
            )
            .agg(
                최근편성수=(
                    "대표상품코드",
                    "size"
                ),

                최근총매출=(
                    "결제금액(포인트포함)",
                    "sum"
                ),

                최근편성당평균매출=(
                    "결제금액(포인트포함)",
                    "mean"
                ),

                최근평균결제수량=(
                    "결제수량",
                    "mean"
                ),
            )
            .reset_index()
        )

        # -------------------------------------------------
        # 이전 기간 브랜드 요약
        # -------------------------------------------------

        previous_brand_summary = (
            previous_brand_df
            .groupby(
                "브랜드명"
            )
            .agg(
                이전편성수=(
                    "대표상품코드",
                    "size"
                ),

                이전총매출=(
                    "결제금액(포인트포함)",
                    "sum"
                ),

                이전편성당평균매출=(
                    "결제금액(포인트포함)",
                    "mean"
                ),

                이전평균결제수량=(
                    "결제수량",
                    "mean"
                ),
            )
            .reset_index()
        )

        # -------------------------------------------------
        # 두 기간 결합
        # -------------------------------------------------

        brand_growth = (
            recent_brand_summary
            .merge(
                previous_brand_summary,
                on="브랜드명",
                how="inner"
            )
        )

        # -------------------------------------------------
        # 최소 표본 기준
        # -------------------------------------------------

        brand_growth = (
            brand_growth[
                (
                    brand_growth[
                        "최근편성수"
                    ]
                    >= 3
                )
                &
                (
                    brand_growth[
                        "이전편성수"
                    ]
                    >= 3
                )
            ]
            .copy()
        )

        if brand_growth.empty:

            st.info(
                "선택한 두 기간 모두 3회 이상 편성된 브랜드가 없습니다."
            )

        else:

            # ---------------------------------------------
            # 변화 지표 계산
            # ---------------------------------------------

            brand_growth[
                "매출증가액"
            ] = (
                brand_growth[
                    "최근편성당평균매출"
                ]
                -
                brand_growth[
                    "이전편성당평균매출"
                ]
            )

            brand_growth[
                "증감률"
            ] = (
                brand_growth[
                    "매출증가액"
                ]
                /
                brand_growth[
                    "이전편성당평균매출"
                ]
                * 100
            )

            brand_growth = (
                brand_growth
                .replace(
                    [
                        float("inf"),
                        float("-inf"),
                    ],
                    pd.NA
                )
                .dropna(
                    subset=[
                        "증감률"
                    ]
                )
            )

            # ---------------------------------------------
            # 정렬 기준 적용
            # ---------------------------------------------

            sort_map = {

                "증감률 높은 순":
                    (
                        "증감률",
                        False
                    ),

                "증감률 낮은 순":
                    (
                        "증감률",
                        True
                    ),

                "최근 편성당 평균 매출 높은 순":
                    (
                        "최근편성당평균매출",
                        False
                    ),

                "최근 총매출 높은 순":
                    (
                        "최근총매출",
                        False
                    ),

                "최근 편성 수 많은 순":
                    (
                        "최근편성수",
                        False
                    ),

                "매출 증가액 큰 순":
                    (
                        "매출증가액",
                        False
                    ),
            }

            sort_column, sort_ascending = (
                sort_map[
                    growth_sort_option
                ]
            )

            brand_growth_top = (
                brand_growth
                .sort_values(
                    sort_column,
                    ascending=sort_ascending
                )
                .head(10)
                .copy()
            )

            # ---------------------------------------------
            # 그래프
            # ---------------------------------------------

            if growth_sort_option in [
                "증감률 높은 순",
                "증감률 낮은 순",
            ]:

                chart_value = "증감률"

            elif growth_sort_option == "최근 편성당 평균 매출 높은 순":

                chart_value = "최근편성당평균매출"

            elif growth_sort_option == "최근 총매출 높은 순":

                chart_value = "최근총매출"

            elif growth_sort_option == "최근 편성 수 많은 순":

                chart_value = "최근편성수"

            else:

                chart_value = "매출증가액"

            growth_chart = (
                brand_growth_top[
                    [
                        "브랜드명",
                        chart_value,
                    ]
                ]
                .copy()
                .set_index(
                    "브랜드명"
                )
            )

            st.bar_chart(
                growth_chart
            )

            # ---------------------------------------------
            # 표
            # ---------------------------------------------

            growth_table = (
                brand_growth_top
                .copy()
            )

            money_columns = [
                "최근총매출",
                "이전총매출",
                "최근편성당평균매출",
                "이전편성당평균매출",
                "매출증가액",
            ]

            for column in money_columns:

                growth_table[
                    column
                ] = (
                    growth_table[
                        column
                    ]
                    .round(0)
                    .astype("Int64")
                )

            growth_table[
                "최근평균결제수량"
            ] = (
                growth_table[
                    "최근평균결제수량"
                ]
                .round(1)
            )

            growth_table[
                "이전평균결제수량"
            ] = (
                growth_table[
                    "이전평균결제수량"
                ]
                .round(1)
            )

            growth_table[
                "증감률"
            ] = (
                growth_table[
                    "증감률"
                ]
                .round(1)
            )

            growth_table = (
                growth_table[
                    [
                        "브랜드명",
                        "최근편성수",
                        "이전편성수",
                        "최근총매출",
                        "이전총매출",
                        "최근편성당평균매출",
                        "이전편성당평균매출",
                        "매출증가액",
                        "증감률",
                        "최근평균결제수량",
                        "이전평균결제수량",
                    ]
                ]
                .rename(
                    columns={
                        "브랜드명":
                            "브랜드",

                        "최근편성수":
                            f"최근 {growth_period_label} 편성 수",

                        "이전편성수":
                            f"이전 {growth_period_label} 편성 수",

                        "최근총매출":
                            f"최근 {growth_period_label} 총매출",

                        "이전총매출":
                            f"이전 {growth_period_label} 총매출",

                        "최근편성당평균매출":
                            f"최근 {growth_period_label} 편성당 평균 매출",

                        "이전편성당평균매출":
                            f"이전 {growth_period_label} 편성당 평균 매출",

                        "매출증가액":
                            "편성당 평균 매출 증감액",

                        "증감률":
                            "증감률(%)",

                        "최근평균결제수량":
                            f"최근 {growth_period_label} 평균 결제수량",

                        "이전평균결제수량":
                            f"이전 {growth_period_label} 평균 결제수량",
                    }
                )
            )

            st.dataframe(
                growth_table,
                use_container_width=True,
                hide_index=True
            )
# =========================================================
# 1. 카테고리 성과 분석
# =========================================================

with category_tab:

    st.subheader(
        "카테고리 성과 분석"
    )

    st.caption(
        "조건을 선택하면 유사 상품군의 과거 편성 성과를 확인할 수 있습니다."
    )

    # =====================================================
    # 기간 필터
    # =====================================================

    period_option = st.selectbox(
        "분석 기간",
        [
            "전체",
            "최근 6개월",
            "최근 1년",
            "직접 선택",
        ],
        key="category_period"
    )

    period_df = df.copy()

    today = pd.Timestamp.today().normalize()

    if period_option == "최근 6개월":

        start_date = (
            today
            - pd.DateOffset(months=6)
        )

        period_df = period_df[
            (
                period_df["날짜"]
                >= start_date
            )
            &
            (
                period_df["날짜"]
                <= today
            )
        ].copy()

    elif period_option == "최근 1년":

        start_date = (
            today
            - pd.DateOffset(years=1)
        )

        period_df = period_df[
            (
                period_df["날짜"]
                >= start_date
            )
            &
            (
                period_df["날짜"]
                <= today
            )
        ].copy()

    elif period_option == "직접 선택":

        valid_dates = (
            df["날짜"]
            .dropna()
        )

        if not valid_dates.empty:

            min_date = (
                valid_dates
                .min()
                .date()
            )

            max_date = (
                valid_dates
                .max()
                .date()
            )

            date_range = st.date_input(
                "조회 기간 선택",
                value=(
                    min_date,
                    max_date
                ),
                min_value=min_date,
                max_value=max_date,
                key="category_date_range"
            )

            if (
                isinstance(
                    date_range,
                    (list, tuple)
                )
                and len(date_range) == 2
            ):

                start_date = pd.Timestamp(
                    date_range[0]
                )

                end_date = pd.Timestamp(
                    date_range[1]
                )

                period_df = period_df[
                    (
                        period_df["날짜"]
                        >= start_date
                    )
                    &
                    (
                        period_df["날짜"]
                        <= end_date
                    )
                ].copy()

    # =====================================================
    # 카테고리 / 가격 / 상태 필터
    # =====================================================

    f1, f2, f3, f4 = (
        st.columns(4)
    )

    large_categories = (
        ["전체"]
        +
        sorted(
            period_df["대카테고리"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
    )

    with f1:

        selected_large = (
            st.selectbox(
                "대카테고리",
                large_categories,
                key="category_large"
            )
        )

    filtered_df = period_df.copy()

    if selected_large != "전체":

        filtered_df = filtered_df[
            filtered_df[
                "대카테고리"
            ]
            == selected_large
        ]

    middle_categories = (
        ["전체"]
        +
        sorted(
            filtered_df[
                "중카테고리"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
    )

    with f2:

        selected_middle = (
            st.selectbox(
                "중카테고리",
                middle_categories,
                key="category_middle"
            )
        )

    if selected_middle != "전체":

        filtered_df = filtered_df[
            filtered_df[
                "중카테고리"
            ]
            == selected_middle
        ]

    existing_price_bands = (
        filtered_df[
            "혜택가가격대"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    preferred_price_order = [
        "<5만원",
        "5만원 미만",
        "5~10만원",
        "10~20만원",
        "20~30만원",
        "30~50만원",
        "50만원 이상",
    ]

    price_bands = (
        ["전체"]
        +
        [
            x
            for x in preferred_price_order
            if x in existing_price_bands
        ]
        +
        [
            x
            for x in sorted(
                existing_price_bands
            )
            if x not in preferred_price_order
        ]
    )

    with f3:

        selected_price = (
            st.selectbox(
                "혜택가 가격대",
                price_bands,
                key="category_price"
            )
        )

    if selected_price != "전체":

        filtered_df = filtered_df[
            filtered_df[
                "혜택가가격대"
            ]
            == selected_price
        ]

    with f4:

        selected_status_label = (
            st.selectbox(
                "데이터 상태",
                [
                    "전체",
                    "편성완료",
                    "예정편성",
                ],
                key="category_status"
            )
        )

    status_map = {
        "전체": "전체",
        "편성완료": "성과완료",
        "예정편성": "예정편성",
    }

    selected_status = (
        status_map[
            selected_status_label
        ]
    )

    if selected_status != "전체":

        filtered_df = filtered_df[
            filtered_df[
                "성과상태"
            ]
            == selected_status
        ]

    # =====================================================
    # 브랜드 / 상품명 검색
    # =====================================================

    f5, f6 = st.columns(2)

    with f5:

        brand_keyword = (
            st.text_input(
                "브랜드 검색",
                placeholder="예: 설화수 / Tenui",
                key="category_brand"
            )
        )

    if brand_keyword:

        filtered_df = filtered_df[
            filtered_df[
                "브랜드명"
            ]
            .fillna("")
            .astype(str)
            .str.contains(
                brand_keyword,
                case=False,
                regex=False
            )
        ]

    with f6:

        product_keyword = (
            st.text_input(
                "상품명 검색",
                placeholder="예: 니트 / 향수 / 트리트먼트",
                key="category_product"
            )
        )

    if product_keyword:

        filtered_df = filtered_df[
            filtered_df[
                "상품명"
            ]
            .fillna("")
            .astype(str)
            .str.contains(
                product_keyword,
                case=False,
                regex=False
            )
        ]

    # =====================================================
    # 성과완료 데이터
    # =====================================================

    performance_df = filtered_df[
        filtered_df[
            "성과상태"
        ]
        == "성과완료"
    ].copy()


    # =====================================================
    # 선택 조건 성과
    # =====================================================

    st.divider()

    st.markdown(
        "### 선택 조건의 과거 성과"
    )

    st.caption(
        "성과완료 데이터를 기준으로 매출·결제수량·할인율을 계산합니다."
    )

    if performance_df.empty:

        st.info(
            "현재 조건에 해당하는 과거 편성 성과가 없습니다."
        )

    else:

        avg_quantity = (
            performance_df["결제수량"]
            .mean()
        )

        avg_payment = (
            performance_df[
                "결제금액(포인트포함)"
            ]
            .mean()
        )

        avg_discount = (
            performance_df[
                "할인율"
            ]
            .mean()
        )

        k1, k2, k3, k4 = (
            st.columns(4)
        )

        with k1:
            st.metric(
                "편성완료 수",
                f"{len(performance_df):,}건"
            )

        with k2:
            st.metric(
                "편성당 평균 매출",
                format_money(
                    avg_payment
                )
            )

        with k3:
            st.metric(
                "평균 결제수량",
                format_number(
                    avg_quantity
                )
            )

        with k4:
            st.metric(
                "평균 할인율",
                format_discount(
                    avg_discount
                )
            )

    # =====================================================
    # 카테고리 비교
    # =====================================================

    st.divider()

    st.markdown(
        "### 카테고리 비교"
    )

    st.caption(
        "편성완료 데이터를 기준으로 카테고리별 평균 성과를 비교합니다. "
        "표본이 적은 카테고리는 참고용으로 확인해주세요."
    )

    category_metric_options = {
        "편성당 평균 매출":
            "평균결제금액",

        "평균 결제수량":
            "평균결제수량",

        "평균 할인율":
            "평균할인율",

        "편성완료 수":
            "편성완료수",
    }

    selected_category_metric = (
        st.selectbox(
            "카테고리 비교 지표",
            list(
                category_metric_options.keys()
            ),
            key="category_compare_metric"
        )
    )

    category_metric_column = (
        category_metric_options[
            selected_category_metric
        ]
    )

    all_completed = df[
        df[
            "성과상태"
        ]
        == "성과완료"
    ].copy()


    # -------------------------------------------------
    # 대카테고리 비교
    # -------------------------------------------------

    st.markdown(
        "#### 대카테고리별"
    )

    large_summary = (
        make_category_summary(
            all_completed,
            ["대카테고리"]
        )
    )

    if not large_summary.empty:

        large_summary = (
            large_summary[
                large_summary[
                    "대카테고리"
                ]
                .fillna("")
                != "미분류"
            ]
            .copy()
        )

    if large_summary.empty:

        st.info(
            "대카테고리 비교 데이터가 없습니다."
        )

    else:

        large_chart = (
            large_summary[
                [
                    "대카테고리",
                    category_metric_column
                ]
            ]
            .copy()
        )

        large_chart = (
            large_chart
            .sort_values(
                category_metric_column,
                ascending=False
            )
            .set_index(
                "대카테고리"
            )
        )

        st.bar_chart(
            large_chart
        )

        large_table = (
            large_summary[
                [
                    "대카테고리",
                    "편성완료수",
                    "상품수",
                    "평균결제금액",
                    "평균결제수량",
                    "평균할인율",
                ]
            ]
            .sort_values(
                "평균결제금액",
                ascending=False
            )
            .copy()
        )

        large_table[
            "평균결제금액"
        ] = (
            large_table[
                "평균결제금액"
            ]
            .round(0)
            .astype("Int64")
        )

        large_table[
            "평균결제수량"
        ] = (
            large_table[
                "평균결제수량"
            ]
            .round(1)
        )

        large_table[
            "평균할인율"
        ] = (
            large_table[
                "평균할인율"
            ]
            .round(1)
        )

        large_table = (
            large_table
            .rename(
                columns={
                    "편성완료수":
                        "편성완료 수",

                    "상품수":
                        "상품 수",

                    "평균결제금액":
                        "편성당 평균 매출",

                    "평균결제수량":
                        "평균 결제수량",

                    "평균할인율":
                        "평균 할인율(%)",
                }
            )
        )

        st.dataframe(
            large_table,
            use_container_width=True,
            hide_index=True
        )


    # -------------------------------------------------
    # 중카테고리 비교
    # -------------------------------------------------

    st.markdown(
        "#### 중카테고리별"
    )

    if selected_large == "전체":

        st.caption(
            "위에서 대카테고리를 선택하면 해당 대카테고리 안의 "
            "중카테고리 성과를 비교할 수 있습니다."
        )

    else:

        middle_compare_df = (
            all_completed[
                all_completed[
                    "대카테고리"
                ]
                == selected_large
            ]
            .copy()
        )

        middle_summary = (
            make_category_summary(
                middle_compare_df,
                [
                    "대카테고리",
                    "중카테고리"
                ]
            )
        )

        if not middle_summary.empty:

            middle_summary = (
                middle_summary[
                    middle_summary[
                        "중카테고리"
                    ]
                    .fillna("")
                    != "미분류"
                ]
                .copy()
            )

        if middle_summary.empty:

            st.info(
                "비교할 중카테고리 데이터가 없습니다."
            )

        else:

            middle_chart = (
                middle_summary[
                    [
                        "중카테고리",
                        category_metric_column
                    ]
                ]
                .copy()
            )

            middle_chart = (
                middle_chart
                .sort_values(
                    category_metric_column,
                    ascending=False
                )
                .set_index(
                    "중카테고리"
                )
            )

            st.bar_chart(
                middle_chart
            )

            middle_table = (
                middle_summary[
                    [
                        "대카테고리",
                        "중카테고리",
                        "편성완료수",
                        "상품수",
                        "평균결제금액",
                        "평균결제수량",
                        "평균할인율",
                    ]
                ]
                .sort_values(
                    "평균결제금액",
                    ascending=False
                )
                .copy()
            )

            middle_table[
                "평균결제금액"
            ] = (
                middle_table[
                    "평균결제금액"
                ]
                .round(0)
                .astype("Int64")
            )

            middle_table[
                "평균결제수량"
            ] = (
                middle_table[
                    "평균결제수량"
                ]
                .round(1)
            )

            middle_table[
                "평균할인율"
            ] = (
                middle_table[
                    "평균할인율"
                ]
                .round(1)
            )

            middle_table = (
                middle_table
                .rename(
                    columns={
                        "편성완료수":
                            "편성완료 수",

                        "상품수":
                            "상품 수",

                        "평균결제금액":
                            "편성당 평균 매출",

                        "평균결제수량":
                            "평균 결제수량",

                        "평균할인율":
                            "평균 할인율(%)",
                    }
                )
            )

            st.dataframe(
                middle_table,
                use_container_width=True,
                hide_index=True
            )


    # =====================================================
    # TOP 10
    # =====================================================
    st.divider()

    st.markdown(
        "### 성과 좋은 상품 TOP 10"
    )

    product_summary = (
        make_product_summary(
            performance_df
        )
    )

    if product_summary.empty:

        st.info(
            "TOP 10을 계산할 과거 편성 데이터가 없습니다."
        )

    else:

        ranking_options = {
            "편성당 평균 매출":
                "평균결제금액",

            "평균 결제수량":
                "평균결제수량",

            "평균 할인율":
                "평균할인율",

            "편성완료 횟수":
                "편성횟수",
        }

        selected_ranking = (
            st.selectbox(
                "TOP 10 기준",
                list(
                    ranking_options.keys()
                ),
                key="top10_metric"
            )
        )

        ranking_column = (
            ranking_options[
                selected_ranking
            ]
        )

        top10 = (
            product_summary
            .sort_values(
                ranking_column,
                ascending=False
            )
            .head(10)
            .copy()
        )

        chart_df = (
            top10[
                [
                    "상품명",
                    ranking_column
                ]
            ]
            .copy()
            .set_index(
                "상품명"
            )
        )

        st.bar_chart(
            chart_df
        )

        top10_view = top10[
            [
                "대표상품코드",
                "상품명",
                "브랜드명",
                "편성횟수",
                "평균결제금액",
                "평균결제수량",
                "평균할인율",
            ]
        ].copy()

        top10_view[
            "평균결제수량"
        ] = (
            top10_view[
                "평균결제수량"
            ]
            .round(1)
        )

        top10_view[
            "평균할인율"
        ] = (
            top10_view[
                "평균할인율"
            ]
            .round(1)
        )

        top10_view = (
            top10_view
            .rename(
                columns={
                    "편성횟수":
                        "편성완료 횟수",

                    "평균결제금액":
                        "편성당 평균 매출",

                    "평균결제수량":
                        "평균 결제수량",

                    "평균할인율":
                        "평균 할인율(%)",
                }
            )
        )

        st.dataframe(
            top10_view,
            use_container_width=True,
            hide_index=True
        )


    # =====================================================
    # 상세 데이터
    # =====================================================

    st.divider()

    st.markdown(
        "### 상세 편성 데이터"
    )

    display_columns = [
        "날짜",
        "요일",
        "순서",
        "대표상품코드",
        "상품명",
        "브랜드명",
        "대카테고리",
        "중카테고리",
        "정상가",
        "최종혜택가",
        "할인율",
        "PV",
        "결제수량",
        "결제금액(포인트포함)",
        "CVR",
        "PV당매출",
        "혜택가가격대",
        "성과상태",
    ]

    view_df = (
        filtered_df[
            display_columns
        ]
        .copy()
        .sort_values(
            "날짜",
            ascending=False
        )
    )

    view_df["날짜"] = (
        view_df["날짜"]
        .dt.strftime(
            "%Y-%m-%d"
        )
    )

    view_df["CVR"] = (
        view_df["CVR"]
        * 100
    ).round(2)

    view_df["성과상태"] = (
        view_df["성과상태"]
        .replace(
            {
                "성과완료":
                    "편성완료"
            }
        )
    )

    view_df = (
        view_df
        .rename(
            columns={
                "결제금액(포인트포함)":
                    "결제금액",

                "CVR":
                    "CVR(%)",

                "PV당매출":
                    "PV당 매출",

                "성과상태":
                    "편성상태",
            }
        )
    )

    st.dataframe(
        view_df,
        use_container_width=True,
        hide_index=True,
        height=600
    )


# =========================================================
# 2. 가격·혜택 분석
# =========================================================

with price_tab:

    st.subheader(
        "가격·혜택 분석"
    )

    st.caption(
        "동일 카테고리 안에서 혜택가와 할인 수준에 따른 과거 성과를 비교합니다."
    )

    # =====================================================
    # 기간 필터
    # =====================================================

    price_period_option = st.selectbox(
        "분석 기간",
        [
            "전체",
            "최근 6개월",
            "최근 1년",
            "직접 선택",
        ],
        key="price_period"
    )

    price_period_df = df.copy()

    today = pd.Timestamp.today().normalize()

    if price_period_option == "최근 6개월":

        start_date = (
            today
            - pd.DateOffset(months=6)
        )

        price_period_df = price_period_df[
            (
                price_period_df["날짜"]
                >= start_date
            )
            &
            (
                price_period_df["날짜"]
                <= today
            )
        ].copy()

    elif price_period_option == "최근 1년":

        start_date = (
            today
            - pd.DateOffset(years=1)
        )

        price_period_df = price_period_df[
            (
                price_period_df["날짜"]
                >= start_date
            )
            &
            (
                price_period_df["날짜"]
                <= today
            )
        ].copy()

    elif price_period_option == "직접 선택":

        valid_dates = (
            df["날짜"]
            .dropna()
        )

        if not valid_dates.empty:

            min_date = (
                valid_dates
                .min()
                .date()
            )

            max_date = (
                valid_dates
                .max()
                .date()
            )

            date_range = st.date_input(
                "조회 기간 선택",
                value=(
                    min_date,
                    max_date
                ),
                min_value=min_date,
                max_value=max_date,
                key="price_date_range"
            )

            if (
                isinstance(
                    date_range,
                    (list, tuple)
                )
                and len(date_range) == 2
            ):

                start_date = pd.Timestamp(
                    date_range[0]
                )

                end_date = pd.Timestamp(
                    date_range[1]
                )

                price_period_df = price_period_df[
                    (
                        price_period_df["날짜"]
                        >= start_date
                    )
                    &
                    (
                        price_period_df["날짜"]
                        <= end_date
                    )
                ].copy()

    # =====================================================
    # 카테고리 필터
    # =====================================================

    pf1, pf2 = st.columns(2)

    price_large_categories = (
        ["전체"]
        +
        sorted(
            price_period_df[
                "대카테고리"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
    )

    with pf1:

        price_large = (
            st.selectbox(
                "대카테고리",
                price_large_categories,
                key="price_large"
            )
        )

    price_filtered = price_period_df[
        price_period_df[
            "성과상태"
        ]
        == "성과완료"
    ].copy()

    if price_large != "전체":

        price_filtered = (
            price_filtered[
                price_filtered[
                    "대카테고리"
                ]
                == price_large
            ]
        )

    price_middle_categories = (
        ["전체"]
        +
        sorted(
            price_filtered[
                "중카테고리"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
    )

    with pf2:

        price_middle = (
            st.selectbox(
                "중카테고리",
                price_middle_categories,
                key="price_middle"
            )
        )

    if price_middle != "전체":

        price_filtered = (
            price_filtered[
                price_filtered[
                    "중카테고리"
                ]
                == price_middle
            ]
        )

    st.write(
        f"현재 분석 대상: "
        f"**{len(price_filtered):,}건의 편성완료 데이터**"
    )

    if price_filtered.empty:

        st.warning(
            "현재 조건에 해당하는 편성완료 데이터가 없습니다."
        )

    else:

        # =================================================
        # 혜택가 분석
        # =================================================

        st.divider()

        st.markdown(
            "### 혜택가 가격대별 성과"
        )

        price_summary = (
            make_price_summary(
                price_filtered
            )
        )

        metric_options = {
            "편성당 평균 매출":
                "평균결제금액",

            "평균 결제수량":
                "평균결제수량",

            "평균 할인율":
                "평균할인율",

            "편성완료 수":
                "편성수",
        }

        selected_price_metric = (
            st.selectbox(
                "그래프로 비교할 지표",
                list(
                    metric_options.keys()
                ),
                key="price_metric"
            )
        )

        price_metric_column = (
            metric_options[
                selected_price_metric
            ]
        )

        price_chart = (
            price_summary[
                [
                    "혜택가가격대",
                    price_metric_column
                ]
            ]
            .copy()
            .set_index(
                "혜택가가격대"
            )
        )

        st.bar_chart(
            price_chart
        )

        price_table = (
            price_summary[
                [
                    "혜택가가격대",
                    "편성수",
                    "평균결제금액",
                    "평균결제수량",
                    "평균할인율",
                ]
            ]
            .copy()
        )

        price_table[
            "평균결제금액"
        ] = (
            price_table[
                "평균결제금액"
            ]
            .round(0)
            .astype("Int64")
        )

        price_table[
            "평균결제수량"
        ] = (
            price_table[
                "평균결제수량"
            ]
            .round(1)
        )

        price_table[
            "평균할인율"
        ] = (
            price_table[
                "평균할인율"
            ]
            .round(1)
        )

        price_table = (
            price_table
            .rename(
                columns={
                    "혜택가가격대":
                        "혜택가 가격대",

                    "편성수":
                        "편성완료 수",

                    "평균결제금액":
                        "편성당 평균 매출",

                    "평균결제수량":
                        "평균 결제수량",

                    "평균할인율":
                        "평균 할인율(%)",
                }
            )
        )

        st.dataframe(
            price_table,
            use_container_width=True,
            hide_index=True
        )


        # =================================================
        # 할인율 분석
        # =================================================

        st.divider()

        st.markdown(
            "### 할인율 구간별 성과"
        )

        discount_summary = (
            make_discount_summary(
                price_filtered
            )
        )

        discount_metric_options = {
            "편성당 평균 매출":
                "평균결제금액",

            "평균 결제수량":
                "평균결제수량",

            "평균 혜택가":
                "평균혜택가",

            "편성완료 수":
                "편성수",
        }

        selected_discount_metric = (
            st.selectbox(
                "그래프로 비교할 지표",
                list(
                    discount_metric_options.keys()
                ),
                key="discount_metric"
            )
        )

        discount_metric_column = (
            discount_metric_options[
                selected_discount_metric
            ]
        )

        discount_chart = (
            discount_summary[
                [
                    "할인율구간",
                    discount_metric_column
                ]
            ]
            .copy()
            .set_index(
                "할인율구간"
            )
        )

        st.bar_chart(
            discount_chart
        )

        discount_table = (
            discount_summary[
                [
                    "할인율구간",
                    "편성수",
                    "평균결제금액",
                    "평균결제수량",
                    "평균혜택가",
                ]
            ]
            .copy()
        )

        discount_table[
            "평균결제금액"
        ] = (
            discount_table[
                "평균결제금액"
            ]
            .round(0)
            .astype("Int64")
        )

        discount_table[
            "평균결제수량"
        ] = (
            discount_table[
                "평균결제수량"
            ]
            .round(1)
        )

        discount_table[
            "평균혜택가"
        ] = (
            discount_table[
                "평균혜택가"
            ]
            .round(0)
            .astype("Int64")
        )

        discount_table = (
            discount_table
            .rename(
                columns={
                    "할인율구간":
                        "할인율 구간",

                    "편성수":
                        "편성완료 수",

                    "평균결제금액":
                        "편성당 평균 매출",

                    "평균결제수량":
                        "평균 결제수량",

                    "평균혜택가":
                        "평균 혜택가",
                }
            )
        )

        st.dataframe(
            discount_table,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        st.markdown(
            "### 혜택가 가격대 × 할인율 조합"
        )

        price_discount_matrix = (
            make_price_discount_matrix(
                price_filtered
            )
        )
        st.dataframe(
            price_discount_matrix,
            use_container_width=True,
            hide_index=True
        )
# =========================================================
# 3. 상품 검색
# =========================================================

with search_tab:

    st.subheader(
        "상품 검색"
    )

    st.caption(
        "상품코드, 상품명 일부, 브랜드명으로 검색할 수 있습니다."
    )

    keyword = (
        st.text_input(
            "검색어",
            placeholder=(
                "상품코드 / 상품명 일부 / 브랜드명"
            ),
            key="product_search_keyword"
        )
    )

    products = make_product_list(df)

    if keyword:

        search_result = (
            search_products_by_keyword(
                products,
                keyword
            )
        )

        if search_result.empty:

            st.warning(
                "검색 결과가 없습니다."
            )

        else:

            result_view = (
                search_result[
                    [
                        "대표상품코드",
                        "상품명",
                        "브랜드명",
                        "대카테고리",
                        "중카테고리",
                        "혜택가가격대",
                    ]
                ]
                .copy()
            )

            st.dataframe(
                result_view,
                use_container_width=True,
                hide_index=True
            )

            search_result = (
                search_result
                .reset_index(
                    drop=True
                )
            )

            labels = []

            for _, row in (
                search_result
                .iterrows()
            ):

                labels.append(
                    f"{row['상품명']} "
                    f"| {row['브랜드명']} "
                    f"| {row['대표상품코드']}"
                )

            selected_label = (
                st.selectbox(
                    "상세 확인할 상품 선택",
                    labels,
                    key="product_detail_select"
                )
            )

            if selected_label:

                selected_index = (
                    labels.index(
                        selected_label
                    )
                )

                selected_code = (
                    search_result
                    .iloc[
                        selected_index
                    ][
                        "대표상품코드"
                    ]
                )

                show_product_detail(
                    df,
                    selected_code
                )
