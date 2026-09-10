import os
import re

import gspread
import pandas as pd

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# =========================================================
# 기본 설정
# =========================================================

SPREADSHEET_ID = "17VJGFNqK-5k2GMqFXBTjPE_vNSor9SpH7dVx_A7WnDE"
WORKSHEET_GID = 741616426

MASTER_FILE = "상품_MASTER_브랜드보완.csv"

PV_START_DATE = pd.Timestamp("2026-04-13")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]


# =========================================================
# Google 로그인
# =========================================================

def get_credentials():

    creds = None

    if os.path.exists("token.json"):

        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    if not creds or not creds.valid:

        if (
            creds
            and creds.expired
            and creds.refresh_token
        ):

            creds.refresh(
                Request()
            )

        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(
                port=0
            )

        with open(
            "token.json",
            "w",
            encoding="utf-8"
        ) as token:

            token.write(
                creds.to_json()
            )

    return creds


# =========================================================
# Google Sheet 읽기
# =========================================================

def load_sheet_values():

    creds = get_credentials()

    client = gspread.authorize(
        creds
    )

    spreadsheet = client.open_by_key(
        SPREADSHEET_ID
    )

    worksheet = (
        spreadsheet
        .get_worksheet_by_id(
            WORKSHEET_GID
        )
    )

    return worksheet.get_all_values()


# =========================================================
# 실제 데이터 헤더 찾기
# =========================================================

def find_header_row(values):

    for i, row in enumerate(values):

        cleaned = [
            str(x).strip()
            for x in row
        ]

        if (
            "연도" in cleaned
            and "온라인상품코드" in cleaned
            and "결제수량" in cleaned
            and "결제금액(포인트포함)" in cleaned
        ):
            return i

    raise ValueError(
        "실제 데이터 헤더를 찾지 못했습니다."
    )


# =========================================================
# 값이 실제로 입력되어 있었는지 확인
# =========================================================

def is_input_present(value):

    if value is None:
        return False

    text = str(value).strip()

    return text != ""


# =========================================================
# 상품코드 추출
#
# 숫자 10자리뿐 아니라
# 01P0000116716 같은 영문 포함 코드도 허용
# =========================================================

def extract_product_codes(value):

    text = str(value).strip()

    if text == "":
        return []

    # 공백 / 줄바꿈 / | / , 등으로 섞여 있는 코드 탐색
    candidates = re.findall(
        r"[A-Za-z0-9]{10,}",
        text
    )

    result = []

    for code in candidates:

        code = (
            str(code)
            .strip()
            .upper()
        )

        if (
            code != ""
            and code not in result
        ):
            result.append(
                code
            )

    return result


# =========================================================
# 가격대 분류
# =========================================================

def classify_price(price):

    if pd.isna(price):
        return "가격정보없음"

    if price < 50000:
        return "5만원 미만"

    elif price < 100000:
        return "5~10만원"

    elif price < 200000:
        return "10~20만원"

    elif price < 300000:
        return "20~30만원"

    elif price < 500000:
        return "30~50만원"

    else:
        return "50만원 이상"


# =========================================================
# 숫자형 변환
# =========================================================

def to_numeric_clean(series):

    cleaned = (
        series
        .astype(str)
        .str.replace(
            ",",
            "",
            regex=False
        )
        .str.replace(
            "원",
            "",
            regex=False
        )
        .str.strip()
    )

    return pd.to_numeric(
        cleaned,
        errors="coerce"
    )


# =========================================================
# RAW 정제
# =========================================================

def make_dataframe(values):

    header_index = find_header_row(
        values
    )

    header = [
        str(x).strip()
        for x in values[
            header_index
        ]
    ]

    data_rows = values[
        header_index + 1:
    ]

    df = pd.DataFrame(
        data_rows,
        columns=header
    )

    # -----------------------------------------------------
    # 신규 시트명 → 기존 코드에서 쓰던 이름으로 통일
    # -----------------------------------------------------

    rename_map = {}

    if (
        "전시요일" in df.columns
        and "요일" not in df.columns
    ):
        rename_map[
            "전시요일"
        ] = "요일"

    if (
        "전시순서" in df.columns
        and "순서" not in df.columns
    ):
        rename_map[
            "전시순서"
        ] = "순서"

    df = df.rename(
        columns=rename_map
    )

    wanted_columns = [
        "연도",
        "월",
        "일정",
        "요일",
        "순서",
        "온라인상품코드",
        "상품명",
        "브랜드명",
        "정상가",
        "최종혜택가",
        "할인율",
        "결제수량",
        "결제금액(포인트포함)",
        "PV",
    ]

    # 빠진 열이 있으면 빈 열 생성
    for column in wanted_columns:

        if column not in df.columns:
            df[column] = ""

    df = df[
        wanted_columns
    ].copy()

    # =====================================================
    # 성과완료 판단용
    # 숫자 변환 전에 "값이 입력돼 있었는지" 저장
    #
    # 0도 입력된 값이므로 성과완료로 처리해야 함
    # =====================================================

    df[
        "_결제수량입력"
    ] = (
        df["결제수량"]
        .apply(
            is_input_present
        )
    )

    df[
        "_결제금액입력"
    ] = (
        df[
            "결제금액(포인트포함)"
        ]
        .apply(
            is_input_present
        )
    )

    # =====================================================
    # 상품코드 처리
    # =====================================================

    df["상품코드목록"] = (
        df[
            "온라인상품코드"
        ]
        .apply(
            extract_product_codes
        )
    )

    # 상품코드 없는 요약행 제거
    df = df[
        df[
            "상품코드목록"
        ]
        .apply(len)
        > 0
    ].copy()

    df[
        "대표상품코드"
    ] = (
        df[
            "상품코드목록"
        ]
        .apply(
            lambda x: x[0]
        )
    )

    df[
        "전체옵션코드"
    ] = (
        df[
            "상품코드목록"
        ]
        .apply(
            lambda x:
            "|".join(x)
        )
    )

    df[
        "옵션개수"
    ] = (
        df[
            "상품코드목록"
        ]
        .apply(len)
    )

    df[
        "복수옵션여부"
    ] = (
        df[
            "옵션개수"
        ]
        > 1
    )

    # =====================================================
    # 텍스트 정리
    # =====================================================

    for column in [
        "상품명",
        "브랜드명",
        "요일",
    ]:

        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # =====================================================
    # 숫자형 정제
    # =====================================================

    numeric_columns = [
        "정상가",
        "최종혜택가",
        "결제수량",
        "결제금액(포인트포함)",
        "PV",
    ]

    for column in numeric_columns:

        df[column] = (
            to_numeric_clean(
                df[column]
            )
        )

    df["할인율"] = (
        df["할인율"]
        .astype(str)
        .str.replace(
            "%",
            "",
            regex=False
        )
        .str.strip()
    )

    df["할인율"] = (
        pd.to_numeric(
            df["할인율"],
            errors="coerce"
        )
    )

    df["순서"] = (
        pd.to_numeric(
            df["순서"],
            errors="coerce"
        )
    )

    # =====================================================
    # 날짜
    # =====================================================

    year_text = (
        df["연도"]
        .astype(str)
        .str.replace(
            ".0",
            "",
            regex=False
        )
        .str.strip()
    )

    schedule_text = (
        df["일정"]
        .astype(str)
        .str.strip()
    )

    df["날짜"] = (
        pd.to_datetime(
            year_text
            + "/"
            + schedule_text,
            errors="coerce"
        )
    )

    # =====================================================
    # 성과 상태
    #
    # 결제수량 또는 결제금액 칸에 값이 입력돼 있으면 성과완료
    # 둘 다 빈칸일 때만 예정편성
    #
    # 0도 실제 입력된 값이므로 성과완료
    # =====================================================

    completed_mask = (
        df[
            "_결제수량입력"
        ]
        |
        df[
            "_결제금액입력"
        ]
    )

    df["성과상태"] = (
        "예정편성"
    )

    df.loc[
        completed_mask,
        "성과상태"
    ] = "성과완료"

    # =====================================================
    # PV 분석 가능 여부
    #
    # 회사에서 PV 수집을 시작한 2026-04-13 이후이며
    # 실제 PV가 0보다 큰 경우에만 분석
    # =====================================================

    df[
        "PV분석가능"
    ] = (
        (df["날짜"] >= PV_START_DATE)
        &
        df["PV"].notna()
        &
        (df["PV"] > 0)
    )

    # =====================================================
    # KPI
    # =====================================================

    df["CVR"] = pd.NA
    df["PV당매출"] = pd.NA

    pv_mask = (
        df["PV분석가능"]
    )

    df.loc[
        pv_mask,
        "CVR"
    ] = (
        df.loc[
            pv_mask,
            "결제수량"
        ]
        /
        df.loc[
            pv_mask,
            "PV"
        ]
    )

    df.loc[
        pv_mask,
        "PV당매출"
    ] = (
        df.loc[
            pv_mask,
            "결제금액(포인트포함)"
        ]
        /
        df.loc[
            pv_mask,
            "PV"
        ]
    )

    df["CVR"] = pd.to_numeric(
        df["CVR"],
        errors="coerce"
    )

    df["PV당매출"] = (
        pd.to_numeric(
            df["PV당매출"],
            errors="coerce"
        )
    )

    # -----------------------------------------------------
    # 건당 결제금액
    # -----------------------------------------------------

    df[
        "건당결제금액"
    ] = (
        df[
            "결제금액(포인트포함)"
        ]
        /
        df[
            "결제수량"
        ]
    )

    df.loc[
        (
            df["결제수량"].isna()
            |
            (df["결제수량"] <= 0)
        ),
        "건당결제금액"
    ] = pd.NA

    # -----------------------------------------------------
    # 실질 할인율
    # -----------------------------------------------------

    df[
        "실질할인율"
    ] = (
        1
        -
        (
            df["최종혜택가"]
            /
            df["정상가"]
        )
    ) * 100

    df.loc[
        (
            df["정상가"].isna()
            |
            (df["정상가"] <= 0)
        ),
        "실질할인율"
    ] = pd.NA

    # =====================================================
    # 혜택가 가격대
    # =====================================================

    df[
        "혜택가가격대"
    ] = (
        df[
            "최종혜택가"
        ]
        .apply(
            classify_price
        )
    )

    # 내부 확인용 열 제거
    df = df.drop(
        columns=[
            "_결제수량입력",
            "_결제금액입력",
        ]
    )

    return df


# =========================================================
# MASTER 읽기
# =========================================================

def load_master():

    if not os.path.exists(
        MASTER_FILE
    ):

        raise FileNotFoundError(
            f"{MASTER_FILE} 파일을 찾을 수 없습니다."
        )

    master = pd.read_csv(
        MASTER_FILE,
        dtype=str,
        encoding="utf-8-sig"
    )

    required_columns = [
        "대표상품코드",
        "대카테고리",
        "중카테고리",
        "분류방식",
        "비고",
    ]

    for column in required_columns:

        if column not in master.columns:
            master[column] = ""

    master[
        "대표상품코드"
    ] = (
        master[
            "대표상품코드"
        ]
        .fillna("")
        .astype(str)
        .str.replace(
            ".0",
            "",
            regex=False
        )
        .str.strip()
        .str.upper()
    )

    master = (
        master
        .drop_duplicates(
            subset=[
                "대표상품코드"
            ],
            keep="last"
        )
        .copy()
    )

    master = master[
        required_columns
    ].copy()

    master = (
        master.rename(
            columns={
                "대카테고리":
                    "MASTER_대카테고리",

                "중카테고리":
                    "MASTER_중카테고리",

                "분류방식":
                    "MASTER_분류방식",

                "비고":
                    "MASTER_비고",
            }
        )
    )

    return master


# =========================================================
# RAW + MASTER 결합
# =========================================================

def merge_with_master(df):

    master = load_master()

    result = df.copy()

    result[
        "대표상품코드"
    ] = (
        result[
            "대표상품코드"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    merged = result.merge(
        master,
        how="left",
        on="대표상품코드"
    )

    merged[
        "대카테고리"
    ] = (
        merged[
            "MASTER_대카테고리"
        ]
        .fillna("미분류")
        .replace(
            "",
            "미분류"
        )
    )

    merged[
        "중카테고리"
    ] = (
        merged[
            "MASTER_중카테고리"
        ]
        .fillna("미분류")
        .replace(
            "",
            "미분류"
        )
    )

    merged[
        "카테고리출처"
    ] = (
        merged[
            "MASTER_대카테고리"
        ]
        .notna()
        .map(
            {
                True: "MASTER",
                False: "MASTER 미등록",
            }
        )
    )

    merged.loc[
        merged[
            "대카테고리"
        ]
        == "미분류",
        "카테고리출처"
    ] = "미분류"

    return merged


# =========================================================
# 상품 검색
# =========================================================

def search_product(
    df,
    product_code
):

    product_code = (
        str(product_code)
        .strip()
        .replace(
            ".0",
            ""
        )
        .upper()
    )

    mask = (
        df[
            "상품코드목록"
        ]
        .apply(
            lambda codes:
            product_code
            in [
                str(x).upper()
                for x in codes
            ]
        )
    )

    return df[
        mask
    ].copy()


# =========================================================
# 표본 수준
# =========================================================

def sample_level(count):

    if count <= 2:
        return "표본 적음"

    elif count <= 9:
        return "참고"

    else:
        return "충분"


# =========================================================
# 상품 자체 평균 계산
# =========================================================

def calculate_product_average(
    completed
):

    if completed.empty:
        return None

    pv_available = (
        completed[
            completed[
                "PV분석가능"
            ]
        ]
        .copy()
    )

    return {
        "건수":
            len(completed),

        "PV표본수":
            len(pv_available),

        "평균PV":
            pv_available[
                "PV"
            ].mean(),

        "평균CVR":
            pv_available[
                "CVR"
            ].mean(),

        "평균결제금액":
            completed[
                "결제금액(포인트포함)"
            ].mean(),

        "평균PV당매출":
            pv_available[
                "PV당매출"
            ].mean(),

        "평균할인율":
            completed[
                "할인율"
            ].mean(),

        "평균결제수량":
            completed[
                "결제수량"
            ].mean(),
    }


# =========================================================
# 벤치마크 계산
# =========================================================

def calculate_benchmark(
    completed_df,
    column,
    value,
    target_code
):

    if pd.isna(value):
        return None

    value = str(
        value
    ).strip()

    if (
        value == ""
        or value == "미분류"
        or value == "가격정보없음"
    ):
        return None

    target_code = (
        str(target_code)
        .strip()
        .upper()
    )

    benchmark_base = (
        completed_df[
            completed_df[
                "대표상품코드"
            ]
            .astype(str)
            .str.upper()
            != target_code
        ]
        .copy()
    )

    benchmark = (
        benchmark_base[
            benchmark_base[
                column
            ]
            .astype(str)
            .str.strip()
            == value
        ]
        .copy()
    )

    if benchmark.empty:
        return None

    count = len(
        benchmark
    )

    pv_benchmark = (
        benchmark[
            benchmark[
                "PV분석가능"
            ]
        ]
        .copy()
    )

    return {
        "건수":
            count,

        "PV표본수":
            len(
                pv_benchmark
            ),

        "표본수준":
            sample_level(
                count
            ),

        "평균PV":
            pv_benchmark[
                "PV"
            ].mean(),

        "평균CVR":
            pv_benchmark[
                "CVR"
            ].mean(),

        "평균결제금액":
            benchmark[
                "결제금액(포인트포함)"
            ].mean(),

        "평균PV당매출":
            pv_benchmark[
                "PV당매출"
            ].mean(),

        "평균할인율":
            benchmark[
                "할인율"
            ].mean(),

        "평균결제수량":
            benchmark[
                "결제수량"
            ].mean(),
    }


# =========================================================
# 값 출력용
# =========================================================

def format_value(
    value,
    kind
):

    if (
        value is None
        or pd.isna(value)
    ):
        return "-"

    if kind == "number":
        return f"{value:,.1f}"

    if kind == "money":
        return f"{value:,.0f}원"

    if kind == "cvr":
        return f"{value * 100:.2f}%"

    if kind == "percent":
        return f"{value:.1f}%"

    return str(value)


# =========================================================
# 차이 포맷
# =========================================================

def format_difference(
    product_value,
    benchmark_value,
    kind
):

    if (
        product_value is None
        or benchmark_value is None
        or pd.isna(product_value)
        or pd.isna(benchmark_value)
    ):
        return "-"

    difference = (
        product_value
        - benchmark_value
    )

    if kind == "cvr":

        return (
            f"{difference * 100:+.2f}%p"
        )

    elif kind == "percent":

        return (
            f"{difference:+.1f}%p"
        )

    elif kind == "money":

        return (
            f"{difference:+,.0f}원"
        )

    elif kind == "number":

        return (
            f"{difference:+,.1f}"
        )

    return str(
        difference
    )


# =========================================================
# 벤치마크 출력
# =========================================================

def print_benchmark(
    title,
    benchmark,
    product_average
):

    print()
    print(
        "----------------------------------------"
    )
    print(
        title
    )
    print(
        "----------------------------------------"
    )

    if benchmark is None:

        print(
            "비교 가능한 과거 성과 없음"
        )

        return

    print(
        "비교 편성 건수:",
        benchmark["건수"]
    )

    print(
        "PV 분석 가능 편성:",
        benchmark["PV표본수"]
    )

    print(
        "표본 수준:",
        benchmark["표본수준"]
    )

    print()

    metrics = [
        (
            "평균 PV",
            "평균PV",
            "number"
        ),
        (
            "평균 CVR",
            "평균CVR",
            "cvr"
        ),
        (
            "편성당 평균 매출",
            "평균결제금액",
            "money"
        ),
        (
            "평균 PV당 매출",
            "평균PV당매출",
            "money"
        ),
        (
            "평균 할인율",
            "평균할인율",
            "percent"
        ),
    ]

    for (
        label,
        key,
        kind
    ) in metrics:

        benchmark_value = (
            benchmark[
                key
            ]
        )

        product_value = (
            product_average[
                key
            ]
            if product_average
            else None
        )

        print(
            f"{label}:",
            format_value(
                benchmark_value,
                kind
            ),
            "| 상품 대비",
            format_difference(
                product_value,
                benchmark_value,
                kind
            )
        )


# =========================================================
# 상품 검색 결과 출력
# =========================================================

def print_product_summary(
    df,
    history
):

    if history.empty:

        print()
        print(
            "========================================"
        )
        print(
            "해당 상품의 편성 이력이 없습니다."
        )
        print(
            "========================================"
        )
        print()

        return

    history = (
        history
        .sort_values(
            "날짜"
        )
    )

    latest = (
        history.iloc[-1]
    )

    target_code = (
        latest[
            "대표상품코드"
        ]
    )

    # =====================================================
    # 기본 정보
    # =====================================================

    print()
    print(
        "========================================"
    )
    print(
        "상품 기본 정보"
    )
    print(
        "========================================"
    )
    print()

    print(
        "대표상품코드:",
        latest[
            "대표상품코드"
        ]
    )

    print(
        "상품명:",
        latest[
            "상품명"
        ]
    )

    print(
        "브랜드:",
        latest[
            "브랜드명"
        ]
    )

    print(
        "대카테고리:",
        latest[
            "대카테고리"
        ]
    )

    print(
        "중카테고리:",
        latest[
            "중카테고리"
        ]
    )

    print(
        "혜택가 가격대:",
        latest[
            "혜택가가격대"
        ]
    )

    print(
        "전체옵션코드:",
        latest[
            "전체옵션코드"
        ]
    )

    completed = (
        history[
            history[
                "성과상태"
            ]
            == "성과완료"
        ]
        .copy()
    )

    scheduled = (
        history[
            history[
                "성과상태"
            ]
            == "예정편성"
        ]
        .copy()
    )

    # =====================================================
    # 과거 성과
    # =====================================================

    print()
    print(
        "========================================"
    )
    print(
        "과거 성과"
    )
    print(
        "========================================"
    )
    print()

    if completed.empty:

        print(
            "과거 편성 이력 없음"
        )

        product_average = None

    else:

        product_average = (
            calculate_product_average(
                completed
            )
        )

        print(
            "성과 편성 횟수:",
            len(
                completed
            )
        )

        print(
            "PV 분석 가능 편성:",
            product_average[
                "PV표본수"
            ]
        )

        print(
            "평균 PV:",
            format_value(
                product_average[
                    "평균PV"
                ],
                "number"
            )
        )

        print(
            "평균 CVR:",
            format_value(
                product_average[
                    "평균CVR"
                ],
                "cvr"
            )
        )

        print(
            "편성당 평균 매출:",
            format_value(
                product_average[
                    "평균결제금액"
                ],
                "money"
            )
        )

        print(
            "평균 PV당 매출:",
            format_value(
                product_average[
                    "평균PV당매출"
                ],
                "money"
            )
        )

        print(
            "평균 할인율:",
            format_value(
                product_average[
                    "평균할인율"
                ],
                "percent"
            )
        )

    # =====================================================
    # 예정 편성
    # =====================================================

    print()
    print(
        "========================================"
    )
    print(
        "예정 편성"
    )
    print(
        "========================================"
    )
    print()

    if scheduled.empty:

        print(
            "예정 편성 없음"
        )

    else:

        scheduled_columns = [
            "날짜",
            "요일",
            "순서",
            "정상가",
            "최종혜택가",
            "할인율",
        ]

        print(
            scheduled[
                scheduled_columns
            ]
            .to_string(
                index=False
            )
        )

    # =====================================================
    # 비교군
    # =====================================================

    completed_all = (
        df[
            df[
                "성과상태"
            ]
            == "성과완료"
        ]
        .copy()
    )

    brand_benchmark = (
        calculate_benchmark(
            completed_all,
            "브랜드명",
            latest[
                "브랜드명"
            ],
            target_code
        )
    )

    category_benchmark = (
        calculate_benchmark(
            completed_all,
            "중카테고리",
            latest[
                "중카테고리"
            ],
            target_code
        )
    )

    price_benchmark = (
        calculate_benchmark(
            completed_all,
            "혜택가가격대",
            latest[
                "혜택가가격대"
            ],
            target_code
        )
    )

    print()
    print(
        "========================================"
    )
    print(
        "비교군 벤치마크"
    )
    print(
        "========================================"
    )

    print_benchmark(
        f"동일 브랜드: "
        f"{latest['브랜드명']}",
        brand_benchmark,
        product_average
    )

    print_benchmark(
        f"동일 중카테고리: "
        f"{latest['중카테고리']}",
        category_benchmark,
        product_average
    )

    print_benchmark(
        f"동일 혜택가 가격대: "
        f"{latest['혜택가가격대']}",
        price_benchmark,
        product_average
    )

    print()


# =========================================================
# 실행
# =========================================================

def main():

    print()
    print(
        "========================================"
    )
    print(
        "딜특가 분석 데이터 준비 중..."
    )
    print(
        "========================================"
    )
    print()

    values = (
        load_sheet_values()
    )

    df = (
        make_dataframe(
            values
        )
    )

    df = (
        merge_with_master(
            df
        )
    )

    print(
        "성과 데이터 + MASTER 결합 성공"
    )

    print()

    print(
        "전체 편성 데이터:",
        f"{len(df):,}건"
    )

    print(
        "성과 완료 편성:",
        f"{df['성과상태'].eq('성과완료').sum():,}건"
    )

    print(
        "예정 편성:",
        f"{df['성과상태'].eq('예정편성').sum():,}건"
    )

    print(
        "PV 분석 가능 편성:",
        f"{df['PV분석가능'].sum():,}건"
    )

    print()

    print(
        "========================================"
    )
    print(
        "상품 검색"
    )
    print(
        "========================================"
    )
    print()

    product_code = input(
        "상품코드: "
    )

    history = (
        search_product(
            df,
            product_code
        )
    )

    print_product_summary(
        df,
        history
    )

    input(
        "엔터를 누르면 종료합니다."
    )


if __name__ == "__main__":
    main()
