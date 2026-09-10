import os
import re
import shutil
from collections import Counter
from datetime import datetime

import pandas as pd

from load_and_clean import load_sheet_values

from make_brand_master import (
    clean_text,
    standardize_brand,
    determine_category,
)


# =========================================================
# 설정
# =========================================================

MASTER_FILE = "상품_MASTER_브랜드보완.csv"

BACKUP_FOLDER = "master_backup"


# =========================================================
# 상품코드 처리
# =========================================================

def extract_product_codes(value):

    if pd.isna(value):
        return []

    text = str(value).strip()

    if text == "":
        return []

    # 숫자 10자리뿐 아니라
    # 01P0000116716 같은 영문+숫자 코드도 허용
    codes = re.findall(
        r"[A-Za-z0-9]{10,}",
        text
    )

    cleaned = []

    for code in codes:

        code = (
            str(code)
            .strip()
            .upper()
        )

        if (
            code != ""
            and code not in cleaned
        ):
            cleaned.append(
                code
            )

    return cleaned


def join_codes(codes):

    return "|".join(
        codes
    )


# =========================================================
# 헤더 찾기
# =========================================================

def find_header_index(values):

    for i, row in enumerate(values):

        cleaned = [
            clean_text(x)
            for x in row
        ]

        if (
            "온라인상품코드" in cleaned
            and "상품명" in cleaned
            and "브랜드명" in cleaned
        ):
            return i

    raise ValueError(
        "온라인상품코드 / 상품명 / 브랜드명 "
        "헤더를 찾지 못했습니다."
    )


# =========================================================
# 구글시트 → 상품 단위 데이터 만들기
# =========================================================

def load_product_dataframe():

    print()
    print(
        "구글시트에서 상품 데이터를 불러오는 중..."
    )

    values = load_sheet_values()

    header_index = find_header_index(
        values
    )

    header = [
        clean_text(x)
        for x in values[
            header_index
        ]
    ]

    data = values[
        header_index + 1:
    ]

    df = pd.DataFrame(
        data,
        columns=header
    )

    required = [
        "온라인상품코드",
        "상품명",
        "브랜드명",
    ]

    for column in required:

        if column not in df.columns:
            raise ValueError(
                f"{column} 열을 찾지 못했습니다."
            )

    df["상품명"] = (
        df["상품명"]
        .apply(
            clean_text
        )
    )

    df["브랜드명"] = (
        df["브랜드명"]
        .apply(
            clean_text
        )
    )

    df["상품코드목록"] = (
        df["온라인상품코드"]
        .apply(
            extract_product_codes
        )
    )

    # 상품코드가 없는 행 제외
    df = df[
        df["상품코드목록"]
        .apply(
            len
        )
        > 0
    ].copy()

    df["대표상품코드"] = (
        df["상품코드목록"]
        .apply(
            lambda x: (
                x[0]
                if len(x) > 0
                else ""
            )
        )
    )

    df["전체옵션코드"] = (
        df["상품코드목록"]
        .apply(
            join_codes
        )
    )

    # -----------------------------------------------------
    # 같은 대표상품코드가 여러 편성에 있을 수 있으므로
    # 가장 최근에 보인 비어있지 않은 값 위주로 상품 단위 통합
    # -----------------------------------------------------

    product_rows = []

    for (
        representative_code,
        group
    ) in df.groupby(
        "대표상품코드",
        sort=False
    ):

        # 전체 옵션코드 합치기
        all_codes = []

        for codes in group[
            "상품코드목록"
        ]:

            for code in codes:

                if code not in all_codes:
                    all_codes.append(
                        code
                    )

        # 상품명
        product_names = [
            clean_text(x)
            for x in group[
                "상품명"
            ].tolist()
            if clean_text(x) != ""
        ]

        product_name = (
            product_names[-1]
            if product_names
            else ""
        )

        # 브랜드명
        brand_names = [
            clean_text(x)
            for x in group[
                "브랜드명"
            ].tolist()
            if clean_text(x) != ""
        ]

        raw_brand = (
            brand_names[-1]
            if brand_names
            else ""
        )

        standard_brand = (
            standardize_brand(
                raw_brand
            )
        )

        # -------------------------------------------------
        # 상품 하나 기준으로 카테고리 판단
        # -------------------------------------------------

        (
            large_category,
            middle_category,
            method,
        ) = determine_category(
            standard_brand,
            [product_name],
        )

        product_rows.append(
            {
                "대표상품코드":
                    representative_code,

                "전체옵션코드":
                    join_codes(
                        all_codes
                    ),

                "상품명":
                    product_name,

                "브랜드명":
                    standard_brand,

                "대카테고리":
                    large_category,

                "중카테고리":
                    middle_category,

                "분류방식":
                    method,

                "비고":
                    "",
            }
        )

    product_df = pd.DataFrame(
        product_rows
    )

    return product_df


# =========================================================
# 기존 카테고리 체계 보정
# =========================================================


def normalize_existing_category(
    large,
    middle,
):

    large = clean_text(large)
    middle = clean_text(middle)

    if large in [
        "",
        "미분류",
        "NAN",
        "NONE",
    ]:
        large = ""

    if middle in [
        "",
        "미분류",
        "NAN",
        "NONE",
    ]:
        middle = ""

    # =====================================================
    # 뷰티
    # =====================================================

    if large == "향수":
        large = "뷰티"

        if middle == "":
            middle = "향수"

    elif large == "스킨케어":
        large = "뷰티"

        if middle == "":
            middle = "스킨케어"

    elif large == "메이크업":
        large = "뷰티"

        if middle == "":
            middle = "메이크업"

    elif large in [
        "헤어",
        "바디",
        "헤어·바디",
    ]:
        large = "뷰티"

        if middle == "":
            middle = "헤어·바디"

    # =====================================================
    # 리빙
    # =====================================================

    elif large == "가전":
        large = "리빙"

        if middle == "":
            middle = "가전"

    elif large == "주방":
        large = "리빙"

        if middle == "":
            middle = "주방"

    elif large in [
        "생활",
        "홈",
        "생활·홈",
    ]:
        large = "리빙"

        if middle == "":
            middle = "생활·홈"

    elif large == "식품":
        large = "리빙"

        if middle == "":
            middle = "식품"

    elif large == "펫":
        large = "리빙"

        if middle in [
            "",
            "펫용품",
        ]:
            middle = "펫"

    elif large == "완구·취미":
        large = "리빙"

        if middle == "":
            middle = "완구·취미"

    # =====================================================
    # 패션
    # =====================================================

    elif large in [
        "여성패션",
        "여성의류",
    ]:
        large = "패션"

        if middle == "":
            middle = "여성의류"

    elif large in [
        "남성패션",
        "남성의류",
    ]:
        large = "패션"

        if middle == "":
            middle = "남성의류"

    elif large == "의류":
        large = "패션"

        if middle == "":
            middle = "의류"

    elif large == "슈즈":
        large = "패션"

        if middle == "":
            middle = "슈즈"

    elif large in [
        "잡화",
        "가방",
        "가방·잡화",
    ]:
        large = "패션"

        if middle == "":
            middle = "가방·잡화"

    elif large == "스포츠":
        large = "패션"

        if middle == "":
            middle = "스포츠"

    elif large == "골프":
        large = "패션"

        if middle == "":
            middle = "골프"

    elif (
        large
        .replace(" ", "")
        .replace("·", "")
        .replace("/", "")
        == "스포츠골프"
    ):
        large = "패션"

        if (
            middle
            .replace(" ", "")
            .replace("·", "")
            .replace("/", "")
            == "스포츠골프"
        ):
            middle = ""

    elif large == "주얼리":
        large = "패션"

        if middle == "":
            middle = "주얼리"

    elif large == "시계":
        large = "패션"

        if middle == "":
            middle = "시계"

    # =====================================================
    # 중카테고리 명칭 통일
    # =====================================================

    if middle == "펫용품":
        middle = "펫"

    if middle == "잡화":
        middle = "가방·잡화"

    return (
        large,
        middle,
    )
    # -----------------------------------------------------
    # 예전 대카테고리 → 새 체계
    # -----------------------------------------------------

    if large == "향수":

        large = "뷰티"

        if middle == "":
            middle = "향수"

    elif large == "펫":

        large = "리빙"

        if middle in [
            "",
            "펫용품",
        ]:
            middle = "펫"

    elif large == "완구·취미":

        large = "리빙"

        if middle == "":
            middle = "완구·취미"

    elif large == "식품":

        large = "리빙"

        if middle == "":
            middle = "식품"

    elif large == "스포츠":

        large = "패션"

        if middle == "":
            middle = "스포츠"

    elif large == "골프":

        large = "패션"

        if middle == "":
            middle = "골프"

    elif large == "주얼리":

        large = "패션"

        if middle == "":
            middle = "주얼리"

    elif large == "시계":

        large = "패션"

        if middle == "":
            middle = "시계"

    elif large in [
        "여성패션",
        "남성패션",
    ]:

        old_large = large

        large = "패션"

        # 과거 중카가 비어있을 때만
        # 성별 정보를 활용
        if middle == "":

            if old_large == "여성패션":
                middle = "여성의류"

            elif old_large == "남성패션":
                middle = "남성의류"

    # 펫용품 명칭 통일
    if middle == "펫용품":
        middle = "펫"

    return (
        large,
        middle,
    )


# =========================================================
# 기존 MASTER 불러오기
# =========================================================

def load_existing_master():

    if not os.path.exists(
        MASTER_FILE
    ):

        return pd.DataFrame(
            columns=[
                "대표상품코드",
                "전체옵션코드",
                "상품명",
                "브랜드명",
                "대카테고리",
                "중카테고리",
                "분류방식",
                "비고",
            ]
        )

    master = pd.read_csv(
        MASTER_FILE,
        dtype=str,
        encoding="utf-8-sig",
    )

    required_columns = [
        "대표상품코드",
        "전체옵션코드",
        "상품명",
        "브랜드명",
        "대카테고리",
        "중카테고리",
        "분류방식",
        "비고",
    ]

    for column in required_columns:

        if column not in master.columns:
            master[
                column
            ] = ""

    master = master[
        required_columns
    ].copy()

    for column in required_columns:

        master[
            column
        ] = (
            master[
                column
            ]
            .fillna("")
            .astype(str)
            .apply(
                clean_text
            )
        )

    master[
        "대표상품코드"
    ] = (
        master[
            "대표상품코드"
        ]
        .str.upper()
    )

    # 기존 브랜드명도 새 표준화 규칙 적용
    master[
        "브랜드명"
    ] = (
        master[
            "브랜드명"
        ]
        .apply(
            standardize_brand
        )
    )

    # 기존 카테고리 체계 보정
    normalized = master.apply(
        lambda row:
            normalize_existing_category(
                row[
                    "대카테고리"
                ],
                row[
                    "중카테고리"
                ],
            ),
        axis=1,
    )

    master[
        "대카테고리"
    ] = [
        x[0]
        for x in normalized
    ]

    master[
        "중카테고리"
    ] = [
        x[1]
        for x in normalized
    ]

    return master


# =========================================================
# MASTER 백업
# =========================================================

def backup_master():

    if not os.path.exists(
        MASTER_FILE
    ):
        return None

    os.makedirs(
        BACKUP_FOLDER,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_path = os.path.join(
        BACKUP_FOLDER,
        (
            "상품_MASTER_브랜드보완_"
            f"{timestamp}.csv"
        ),
    )

    shutil.copy2(
        MASTER_FILE,
        backup_path,
    )

    return backup_path


# =========================================================
# 값이 유효한지
# =========================================================

def valid_category(value):

    value = clean_text(
        value
    )

    return value not in [
        "",
        "미분류",
        "NAN",
        "NONE",
    ]


# =========================================================
# 기존 MASTER + 신규 자동분류 결합
# =========================================================

def merge_master(
    old_master,
    new_products,
):

    old_map = {}

    for _, row in old_master.iterrows():

        code = clean_text(
            row[
                "대표상품코드"
            ]
        ).upper()

        if code != "":
            old_map[
                code
            ] = row.to_dict()

    result_rows = []

    existing_count = 0
    new_count = 0
    category_updated_count = 0
    brand_updated_count = 0

    # -----------------------------------------------------
    # 현재 구글시트 상품 처리
    # -----------------------------------------------------

    for _, new_row in new_products.iterrows():

        code = clean_text(
            new_row[
                "대표상품코드"
            ]
        ).upper()

        if code in old_map:

            existing_count += 1

            old_row = (
                old_map[
                    code
                ]
            )

            result = (
                old_row.copy()
            )

            # ---------------------------------------------
            # 상품 기본정보는 최신 시트 기준으로 갱신
            # ---------------------------------------------

            result[
                "전체옵션코드"
            ] = clean_text(
                new_row[
                    "전체옵션코드"
                ]
            )

            result[
                "상품명"
            ] = clean_text(
                new_row[
                    "상품명"
                ]
            )

            old_brand = clean_text(
                result[
                    "브랜드명"
                ]
            )

            new_brand = clean_text(
                new_row[
                    "브랜드명"
                ]
            )

            # 브랜드 표준화값 갱신
            if (
                new_brand != ""
                and new_brand != old_brand
            ):

                result[
                    "브랜드명"
                ] = new_brand

                brand_updated_count += 1

            # ---------------------------------------------
            # 카테고리
            #
            # 새 브랜드/상품명 규칙으로 확실한 값이 나오면
            # 새로운 체계를 우선 적용.
            #
            # 새 값이 미분류이면 기존값 보존.
            # ---------------------------------------------

            new_large = clean_text(
                new_row[
                    "대카테고리"
                ]
            )

            new_middle = clean_text(
                new_row[
                    "중카테고리"
                ]
            )

            new_method = clean_text(
                new_row[
                    "분류방식"
                ]
            )

            old_large = clean_text(
                result[
                    "대카테고리"
                ]
            )

            old_middle = clean_text(
                result[
                    "중카테고리"
                ]
            )

            changed = False

            if valid_category(
                new_large
            ):

                if (
                    old_large
                    != new_large
                ):
                    changed = True

                result[
                    "대카테고리"
                ] = new_large

                # 새 중카까지 확실하면 적용
                if valid_category(
                    new_middle
                ):

                    if (
                        old_middle
                        != new_middle
                    ):
                        changed = True

                    result[
                        "중카테고리"
                    ] = new_middle

                else:
                    # 새 분류가 대카만 확실할 경우
                    # 기존 중카가 새로운 체계에서
                    # 너무 세분화된 값이면 제거
                    allowed_middle = {
                        "여성의류",
                        "남성의류",
                        "의류",
                        "슈즈",
                        "가방·잡화",
                        "스포츠",
                        "골프",
                        "주얼리",
                        "시계",

                        "스킨케어",
                        "메이크업",
                        "향수",
                        "헤어·바디",

                        "주방",
                        "생활·홈",
                        "가전",
                        "식품",
                        "펫",
                        "완구·취미",
                    }

                    if (
                        old_middle
                        not in allowed_middle
                    ):
                        result[
                            "중카테고리"
                        ] = ""

                result[
                    "분류방식"
                ] = new_method

            # 새 자동분류가 없으면
            # 기존 분류 유지
            if changed:
                category_updated_count += 1

            result_rows.append(
                result
            )

            # 처리 완료 표시
            del old_map[
                code
            ]

        else:

            # ---------------------------------------------
            # MASTER에 없던 신규상품
            # ---------------------------------------------

            new_count += 1

            result_rows.append(
                {
                    "대표상품코드":
                        code,

                    "전체옵션코드":
                        clean_text(
                            new_row[
                                "전체옵션코드"
                            ]
                        ),

                    "상품명":
                        clean_text(
                            new_row[
                                "상품명"
                            ]
                        ),

                    "브랜드명":
                        clean_text(
                            new_row[
                                "브랜드명"
                            ]
                        ),

                    "대카테고리":
                        clean_text(
                            new_row[
                                "대카테고리"
                            ]
                        ),

                    "중카테고리":
                        clean_text(
                            new_row[
                                "중카테고리"
                            ]
                        ),

                    "분류방식":
                        clean_text(
                            new_row[
                                "분류방식"
                            ]
                        ),

                    "비고":
                        "",
                }
            )

    # -----------------------------------------------------
    # 구글시트에는 지금 없지만 기존 MASTER에는 있던 상품
    # → 삭제하지 않고 그대로 보존
    # -----------------------------------------------------

    preserved_old_count = len(
        old_map
    )

    for row in old_map.values():

        result_rows.append(
            row
        )

    result = pd.DataFrame(
        result_rows
    )

    columns = [
        "대표상품코드",
        "전체옵션코드",
        "상품명",
        "브랜드명",
        "대카테고리",
        "중카테고리",
        "분류방식",
        "비고",
    ]

    for column in columns:

        if column not in result.columns:
            result[
                column
            ] = ""

    result = result[
        columns
    ]

    # -----------------------------------------------------
    # 최종 빈 카테고리 표시
    # -----------------------------------------------------

    result[
        "대카테고리"
    ] = (
        result[
            "대카테고리"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace(
            "",
            "미분류",
        )
    )

    result[
        "중카테고리"
    ] = (
        result[
            "중카테고리"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace(
            "",
            "미분류",
        )
    )

    result[
        "대표상품코드"
    ] = (
        result[
            "대표상품코드"
        ]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # 대표상품코드 중복 제거
    result = (
        result
        .drop_duplicates(
            subset=[
                "대표상품코드"
            ],
            keep="first",
        )
        .reset_index(
            drop=True
        )
    )

    stats = {
        "existing_count":
            existing_count,

        "new_count":
            new_count,

        "preserved_old_count":
            preserved_old_count,

        "category_updated_count":
            category_updated_count,

        "brand_updated_count":
            brand_updated_count,
    }

    return (
        result,
        stats,
    )


# =========================================================
# 실행
# =========================================================

def main():

    print()
    print(
        "=" * 60
    )

    print(
        "상품 MASTER 동기화 시작"
    )

    print(
        "=" * 60
    )

    # -----------------------------------------------------
    # 1. 기존 MASTER
    # -----------------------------------------------------

    old_master = (
        load_existing_master()
    )

    print(
        f"기존 MASTER 상품 수: "
        f"{len(old_master):,}개"
    )

    # -----------------------------------------------------
    # 2. 현재 구글시트 상품
    # -----------------------------------------------------

    new_products = (
        load_product_dataframe()
    )

    print(
        f"현재 시트 상품 수: "
        f"{len(new_products):,}개"
    )

    # -----------------------------------------------------
    # 3. 백업
    # -----------------------------------------------------

    backup_path = (
        backup_master()
    )

    if backup_path:

        print()
        print(
            f"기존 MASTER 백업 완료:"
        )

        print(
            backup_path
        )

    # -----------------------------------------------------
    # 4. 결합
    # -----------------------------------------------------

    (
        result,
        stats,
    ) = merge_master(
        old_master,
        new_products,
    )

    # -----------------------------------------------------
    # 5. 저장
    # -----------------------------------------------------

    result.to_csv(
        MASTER_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # -----------------------------------------------------
    # 6. 결과 통계
    # -----------------------------------------------------

    classified_large = (
        result[
            "대카테고리"
        ]
        .ne(
            "미분류"
        )
        .sum()
    )

    classified_middle = (
        result[
            "중카테고리"
        ]
        .ne(
            "미분류"
        )
        .sum()
    )

    total = len(
        result
    )

    print()
    print(
        "=" * 60
    )

    print(
        "상품 MASTER 동기화 완료"
    )

    print(
        "=" * 60
    )

    print(
        f"기존 상품 매칭: "
        f"{stats['existing_count']:,}개"
    )

    print(
        f"신규 상품 추가: "
        f"{stats['new_count']:,}개"
    )

    print(
        f"기존 MASTER에서만 존재하여 보존: "
        f"{stats['preserved_old_count']:,}개"
    )

    print(
        f"표준 브랜드명 변경: "
        f"{stats['brand_updated_count']:,}개"
    )

    print(
        f"카테고리 변경/보완: "
        f"{stats['category_updated_count']:,}개"
    )

    print()

    print(
        f"최종 MASTER 상품 수: "
        f"{total:,}개"
    )

    print(
        f"대카테고리 분류: "
        f"{classified_large:,} / "
        f"{total:,}"
    )

    if total > 0:

        print(
            f"대카테고리 분류율: "
            f"{classified_large / total * 100:.1f}%"
        )

        print(
            f"중카테고리 분류율: "
            f"{classified_middle / total * 100:.1f}%"
        )

    print()
    print(
        f"저장 파일: "
        f"{MASTER_FILE}"
    )

    print()

# =========================================================
# app.py 호환용 함수
# =========================================================

def load_master():

    return load_existing_master()


def normalize_brand(value):

    return standardize_brand(
        value
    )


def find_new_products(
    products,
    master,
):

    product_codes = set(
        master[
            "대표상품코드"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .tolist()
    )

    result = (
        products[
            ~products[
                "대표상품코드"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .isin(
                product_codes
            )
        ]
        .copy()
    )

    return result


def make_brand_large_map(
    master
):

    temp = master.copy()

    temp[
        "브랜드정규화"
    ] = (
        temp[
            "브랜드명"
        ]
        .apply(
            standardize_brand
        )
    )

    result = {}

    for (
        brand,
        group
    ) in temp.groupby(
        "브랜드정규화"
    ):

        values = [
            clean_text(x)
            for x in group[
                "대카테고리"
            ].tolist()
            if valid_category(x)
        ]

        if not values:
            continue

        counts = Counter(
            values
        )

        category, count = (
            counts.most_common(1)[0]
        )

        total = sum(
            counts.values()
        )

        if (
            total > 0
            and count / total >= 0.8
        ):
            result[
                brand
            ] = category

    return result


def make_brand_middle_map(
    master
):

    temp = master.copy()

    temp[
        "브랜드정규화"
    ] = (
        temp[
            "브랜드명"
        ]
        .apply(
            standardize_brand
        )
    )

    result = {}

    for (
        brand,
        group
    ) in temp.groupby(
        "브랜드정규화"
    ):

        values = [
            clean_text(x)
            for x in group[
                "중카테고리"
            ].tolist()
            if valid_category(x)
        ]

        if len(values) < 2:
            continue

        counts = Counter(
            values
        )

        category, count = (
            counts.most_common(1)[0]
        )

        total = sum(
            counts.values()
        )

        if (
            total > 0
            and count / total >= 0.9
        ):
            result[
                brand
            ] = category

    return result


def classify_new_products(
    new_products,
    large_map,
    middle_map,
):

    result_rows = []

    for _, row in (
        new_products
        .iterrows()
    ):

        product_name = clean_text(
            row[
                "상품명"
            ]
        )

        raw_brand = clean_text(
            row[
                "브랜드명"
            ]
        )

        standard_brand = (
            standardize_brand(
                raw_brand
            )
        )

        (
            large,
            middle,
            method,
        ) = determine_category(
            standard_brand,
            [
                product_name
            ],
        )

        # 새 규칙에서 미분류일 경우
        # 기존 MASTER 브랜드 다수결 활용
        if not valid_category(
            large
        ):

            if standard_brand in (
                large_map
            ):
                large = (
                    large_map[
                        standard_brand
                    ]
                )

                method = (
                    "브랜드 이력"
                )

        if not valid_category(
            middle
        ):

            if standard_brand in (
                middle_map
            ):
                middle = (
                    middle_map[
                        standard_brand
                    ]
                )

                if method == (
                    "브랜드 이력"
                ):
                    method = (
                        "브랜드 이력"
                    )
                else:
                    method = (
                        "브랜드+이력"
                    )

        if not valid_category(
            large
        ):
            large = (
                "미분류"
            )

        if not valid_category(
            middle
        ):
            middle = (
                "미분류"
            )

        result_rows.append(
            {
                "대표상품코드":
                    clean_text(
                        row[
                            "대표상품코드"
                        ]
                    ).upper(),

                "전체옵션코드":
                    clean_text(
                        row[
                            "전체옵션코드"
                        ]
                    ),

                "상품명":
                    product_name,

                "브랜드명":
                    standard_brand,

                "대카테고리":
                    large,

                "중카테고리":
                    middle,

                "분류방식":
                    method,

                "비고":
                    "",
            }
        )

    return pd.DataFrame(
        result_rows
    )


def save_master(
    master,
    new_rows,
):

    combined = pd.concat(
        [
            master,
            new_rows,
        ],
        ignore_index=True,
    )

    combined[
        "대표상품코드"
    ] = (
        combined[
            "대표상품코드"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    combined = (
        combined
        .drop_duplicates(
            subset=[
                "대표상품코드"
            ],
            keep="first",
        )
        .reset_index(
            drop=True
        )
    )

    combined.to_csv(
        MASTER_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    return combined

if __name__ == "__main__":
    main()
