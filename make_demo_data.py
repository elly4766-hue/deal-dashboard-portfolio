import random
from datetime import date, timedelta

import pandas as pd


# =========================================================
# 기본 설정
# =========================================================

random.seed(42)

OUTPUT_FILE = "demo_data.csv"

START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 9, 9)


# =========================================================
# 가상 브랜드 / 상품
# =========================================================

PRODUCTS = [

    # -----------------------------------------------------
    # 패션
    # -----------------------------------------------------

    {
        "brand": "LUMEN",
        "product": "여성 캐시미어 블렌드 니트",
        "normal_price": 189000,
        "base_sales": 4200000,
    },
    {
        "brand": "LUMEN",
        "product": "여성 울 블렌드 가디건",
        "normal_price": 219000,
        "base_sales": 4800000,
    },
    {
        "brand": "NORDEN",
        "product": "남성 클래식 셔츠",
        "normal_price": 129000,
        "base_sales": 3100000,
    },
    {
        "brand": "NORDEN",
        "product": "남성 테이퍼드 팬츠",
        "normal_price": 159000,
        "base_sales": 3500000,
    },
    {
        "brand": "MOTION LAB",
        "product": "러닝 경량 자켓",
        "normal_price": 149000,
        "base_sales": 3900000,
    },
    {
        "brand": "MOTION LAB",
        "product": "스포츠 트레이닝 팬츠",
        "normal_price": 99000,
        "base_sales": 3000000,
    },
    {
        "brand": "GREEN FAIRWAY",
        "product": "골프 여성 카라 티셔츠",
        "normal_price": 179000,
        "base_sales": 4500000,
    },
    {
        "brand": "GREEN FAIRWAY",
        "product": "골프 남성 기능성 팬츠",
        "normal_price": 209000,
        "base_sales": 4700000,
    },
    {
        "brand": "ATELIER BAG",
        "product": "레더 미니 숄더백",
        "normal_price": 329000,
        "base_sales": 5200000,
    },
    {
        "brand": "ATELIER BAG",
        "product": "데일리 토트백",
        "normal_price": 259000,
        "base_sales": 4600000,
    },

    # -----------------------------------------------------
    # 뷰티
    # -----------------------------------------------------

    {
        "brand": "PURELAB",
        "product": "수분 장벽 크림",
        "normal_price": 68000,
        "base_sales": 5100000,
    },
    {
        "brand": "PURELAB",
        "product": "진정 세럼",
        "normal_price": 59000,
        "base_sales": 4900000,
    },
    {
        "brand": "GLOWMATE",
        "product": "글로우 쿠션 파운데이션",
        "normal_price": 52000,
        "base_sales": 4500000,
    },
    {
        "brand": "GLOWMATE",
        "product": "벨벳 립 틴트",
        "normal_price": 32000,
        "base_sales": 3500000,
    },
    {
        "brand": "SCENT ARCHIVE",
        "product": "오드퍼퓸 50ML",
        "normal_price": 168000,
        "base_sales": 5800000,
    },
    {
        "brand": "SCENT ARCHIVE",
        "product": "퍼퓸 기프트 세트",
        "normal_price": 198000,
        "base_sales": 6200000,
    },
    {
        "brand": "BOTANIC DAY",
        "product": "퍼퓸 바디워시",
        "normal_price": 39000,
        "base_sales": 3200000,
    },
    {
        "brand": "BOTANIC DAY",
        "product": "너리싱 헤어 마스크",
        "normal_price": 45000,
        "base_sales": 3400000,
    },

    # -----------------------------------------------------
    # 리빙
    # -----------------------------------------------------

    {
        "brand": "HOME TABLE",
        "product": "프리미엄 프라이팬 세트",
        "normal_price": 179000,
        "base_sales": 4300000,
    },
    {
        "brand": "HOME TABLE",
        "product": "세라믹 냄비 세트",
        "normal_price": 249000,
        "base_sales": 5100000,
    },
    {
        "brand": "MORNING BREW",
        "product": "드립 커피메이커",
        "normal_price": 159000,
        "base_sales": 4600000,
    },
    {
        "brand": "MORNING BREW",
        "product": "전기 토스터",
        "normal_price": 119000,
        "base_sales": 3700000,
    },
    {
        "brand": "AIRNEST",
        "product": "미니 공기청정기",
        "normal_price": 299000,
        "base_sales": 5400000,
    },
    {
        "brand": "AIRNEST",
        "product": "무선 서큘레이터",
        "normal_price": 189000,
        "base_sales": 4400000,
    },
    {
        "brand": "DAILY PANTRY",
        "product": "프리미엄 견과 선물세트",
        "normal_price": 69000,
        "base_sales": 3900000,
    },
    {
        "brand": "DAILY PANTRY",
        "product": "시그니처 디저트 세트",
        "normal_price": 59000,
        "base_sales": 3600000,
    },
]


# =========================================================
# 브랜드별 최근 성장/하락 패턴
# =========================================================

BRAND_TREND = {

    "LUMEN": 1.10,
    "NORDEN": 0.92,
    "MOTION LAB": 1.18,
    "GREEN FAIRWAY": 1.12,
    "ATELIER BAG": 0.95,

    "PURELAB": 1.25,
    "GLOWMATE": 1.08,
    "SCENT ARCHIVE": 1.20,
    "BOTANIC DAY": 0.90,

    "HOME TABLE": 1.05,
    "MORNING BREW": 1.15,
    "AIRNEST": 0.88,
    "DAILY PANTRY": 1.10,
}


# =========================================================
# 요일 효과
# =========================================================

WEEKDAY_FACTOR = {
    0: 0.94,   # 월
    1: 0.98,   # 화
    2: 1.03,   # 수
    3: 1.07,   # 목
    4: 1.12,   # 금
    5: 1.05,   # 토
    6: 0.96,   # 일
}

WEEKDAY_NAME = {
    0: "월",
    1: "화",
    2: "수",
    3: "목",
    4: "금",
    5: "토",
    6: "일",
}


# =========================================================
# 전시순서 효과
# =========================================================

ORDER_FACTOR = {
    1: 1.16,
    2: 1.10,
    3: 1.06,
    4: 1.02,
    5: 0.98,
    6: 0.95,
    7: 0.92,
    8: 0.90,
}


# =========================================================
# 할인율별 효과
# =========================================================

def discount_factor(discount_rate):

    if discount_rate < 10:
        return 0.88

    if discount_rate < 20:
        return 0.97

    if discount_rate < 30:
        return 1.05

    if discount_rate < 40:
        return 1.11

    if discount_rate < 50:
        return 1.08

    return 1.02


# =========================================================
# 계절 효과
# =========================================================

def season_factor(month):

    if month in [11, 12]:
        return 1.18

    if month in [5, 6]:
        return 1.08

    if month in [1, 2]:
        return 0.94

    return 1.00


# =========================================================
# 최근 브랜드 변화 반영
# =========================================================

def trend_factor(brand, current_date):

    base = BRAND_TREND.get(
        brand,
        1.0
    )

    # 2026년 4월 이후 변화가 점차 반영되도록 설정
    if current_date < date(2026, 4, 1):
        return 1.0

    return base


# =========================================================
# 가상 데이터 생성
# =========================================================

rows = []

current_date = START_DATE

product_code_map = {}

next_product_code = 9100000001

for product in PRODUCTS:

    product_code_map[
        (
            product["brand"],
            product["product"],
        )
    ] = str(next_product_code)

    next_product_code += 1


while current_date <= END_DATE:

    # 매일 편성하는 대신 약 70%의 날짜에만 편성
    if random.random() < 0.70:

        placement_count = random.randint(
            5,
            8
        )

        selected_products = random.sample(
            PRODUCTS,
            placement_count
        )

        for order, product in enumerate(
            selected_products,
            start=1
        ):

            normal_price = product[
                "normal_price"
            ]

            discount_rate = random.choice(
                [
                    10,
                    15,
                    20,
                    25,
                    30,
                    35,
                    40,
                    45,
                    50,
                ]
            )

            benefit_price = round(
                normal_price
                *
                (
                    1
                    -
                    discount_rate / 100
                ),
                -2
            )

            revenue = (
                product["base_sales"]
                *
                WEEKDAY_FACTOR[
                    current_date.weekday()
                ]
                *
                ORDER_FACTOR.get(
                    order,
                    0.90
                )
                *
                discount_factor(
                    discount_rate
                )
                *
                season_factor(
                    current_date.month
                )
                *
                trend_factor(
                    product["brand"],
                    current_date
                )
                *
                random.uniform(
                    0.65,
                    1.35
                )
            )

            revenue = max(
                revenue,
                0
            )

            revenue = round(
                revenue,
                -3
            )

            if benefit_price > 0:

                quantity = max(
                    0,
                    round(
                        revenue
                        /
                        benefit_price
                        *
                        random.uniform(
                            0.80,
                            1.20
                        )
                    )
                )

            else:

                quantity = 0

            # -------------------------------------------------
            # PV
            # 2026-04-13 이전에는 빈칸
            # -------------------------------------------------

            if current_date >= date(
                2026,
                4,
                13
            ):

                pv = max(
                    quantity * random.randint(
                        5,
                        18
                    ),
                    random.randint(
                        100,
                        500
                    )
                )

            else:

                pv = ""

            code = product_code_map[
                (
                    product["brand"],
                    product["product"],
                )
            ]

            rows.append(
                {
                    "연도":
                        current_date.year,

                    "월":
                        current_date.month,

                    "일정":
                        current_date.strftime(
                            "%m/%d"
                        ),

                    "전시요일":
                        WEEKDAY_NAME[
                            current_date.weekday()
                        ],

                    "전시순서":
                        order,

                    "온라인상품코드":
                        code,

                    "상품명":
                        product["product"],

                    "브랜드명":
                        product["brand"],

                    "정상가":
                        int(
                            normal_price
                        ),

                    "최종혜택가":
                        int(
                            benefit_price
                        ),

                    "할인율":
                        discount_rate,

                    "결제수량":
                        quantity,

                    "결제금액(포인트포함)":
                        int(
                            revenue
                        ),

                    "PV":
                        pv,
                }
            )

    current_date += timedelta(
        days=1
    )


# =========================================================
# 예정 편성 데이터 추가
# =========================================================

future_start = END_DATE + timedelta(
    days=1
)

for day_offset in range(
    1,
    8
):

    future_date = (
        future_start
        +
        timedelta(
            days=day_offset
        )
    )

    selected_products = random.sample(
        PRODUCTS,
        5
    )

    for order, product in enumerate(
        selected_products,
        start=1
    ):

        discount_rate = random.choice(
            [
                15,
                20,
                25,
                30,
                35,
                40,
            ]
        )

        normal_price = product[
            "normal_price"
        ]

        benefit_price = round(
            normal_price
            *
            (
                1
                -
                discount_rate / 100
            ),
            -2
        )

        code = product_code_map[
            (
                product["brand"],
                product["product"],
            )
        ]

        rows.append(
            {
                "연도":
                    future_date.year,

                "월":
                    future_date.month,

                "일정":
                    future_date.strftime(
                        "%m/%d"
                    ),

                "전시요일":
                    WEEKDAY_NAME[
                        future_date.weekday()
                    ],

                "전시순서":
                    order,

                "온라인상품코드":
                    code,

                "상품명":
                    product["product"],

                "브랜드명":
                    product["brand"],

                "정상가":
                    int(
                        normal_price
                    ),

                "최종혜택가":
                    int(
                        benefit_price
                    ),

                "할인율":
                    discount_rate,

                "결제수량":
                    "",

                "결제금액(포인트포함)":
                    "",

                "PV":
                    "",
            }
        )


# =========================================================
# 저장
# =========================================================

demo_df = pd.DataFrame(
    rows
)

demo_df = demo_df.sort_values(
    [
        "연도",
        "월",
        "일정",
        "전시순서",
    ]
).reset_index(
    drop=True
)

demo_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# 결과 확인
# =========================================================

print(
    "========================================="
)

print(
    "포트폴리오용 DEMO 데이터 생성 완료"
)

print(
    "파일:",
    OUTPUT_FILE
)

print(
    "총 행 수:",
    len(
        demo_df
    )
)

print(
    "브랜드 수:",
    demo_df[
        "브랜드명"
    ].nunique()
)

print(
    "상품 수:",
    demo_df[
        "온라인상품코드"
    ].nunique()
)

print(
    "기간:",
    demo_df[
        "연도"
    ].astype(str)
    .min(),
    "~",
    demo_df[
        "연도"
    ].astype(str)
    .max()
)

print(
    "========================================="
)
# =========================================================
# 포트폴리오용 상품 MASTER 생성
# =========================================================

CATEGORY_MAP = {

    # 패션
    "LUMEN": (
        "패션",
        "여성의류"
    ),

    "NORDEN": (
        "패션",
        "남성의류"
    ),

    "MOTION LAB": (
        "패션",
        "스포츠"
    ),

    "GREEN FAIRWAY": (
        "패션",
        "골프"
    ),

    "ATELIER BAG": (
        "패션",
        "가방·잡화"
    ),

    # 뷰티
    "PURELAB": (
        "뷰티",
        "스킨케어"
    ),

    "GLOWMATE": (
        "뷰티",
        "메이크업"
    ),

    "SCENT ARCHIVE": (
        "뷰티",
        "향수"
    ),

    "BOTANIC DAY": (
        "뷰티",
        "헤어·바디"
    ),

    # 리빙
    "HOME TABLE": (
        "리빙",
        "주방"
    ),

    "MORNING BREW": (
        "리빙",
        "가전"
    ),

    "AIRNEST": (
        "리빙",
        "가전"
    ),

    "DAILY PANTRY": (
        "리빙",
        "식품"
    ),
}


master_rows = []

for product in PRODUCTS:

    brand = product[
        "brand"
    ]

    product_name = product[
        "product"
    ]

    code = product_code_map[
        (
            brand,
            product_name,
        )
    ]

    large_category, middle_category = (
        CATEGORY_MAP.get(
            brand,
            (
                "미분류",
                "미분류"
            )
        )
    )

    master_rows.append(
        {
            "대표상품코드":
                code,

            "전체옵션코드":
                code,

            "상품명":
                product_name,

            "브랜드명":
                brand,

            "대카테고리":
                large_category,

            "중카테고리":
                middle_category,

            "브랜드군":
                brand,

            "비고":
                "PORTFOLIO DEMO",
        }
    )


demo_master = pd.DataFrame(
    master_rows
)


demo_master.to_csv(
    "상품_MASTER_브랜드보완.csv",
    index=False,
    encoding="utf-8-sig"
)


print()
print(
    "포트폴리오용 상품 MASTER 생성 완료"
)

print(
    "파일: 상품_MASTER_브랜드보완.csv"
)

print(
    "MASTER 상품 수:",
    len(
        demo_master
    )
)

print(
    "========================================="
)
