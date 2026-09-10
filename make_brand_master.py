import re
from collections import Counter

import pandas as pd

from load_and_clean import load_sheet_values


OUTPUT_FILE = "브랜드_표준화.csv"


# ==========================================================
# 1. 기본 문자열 정리
# ==========================================================

def clean_text(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)

    return text


def upper_if_english(text):
    text = clean_text(text)

    if text == "":
        return ""

    if not re.search(r"[가-힣]", text):
        return text.upper()

    return text


# ==========================================================
# 2. 브랜드 Alias
#
# 원본은 달라도 같은 브랜드이면
# 표준브랜드명 하나로 통합
# ==========================================================

BRAND_ALIAS = {

    # ------------------------------------------------------
    # 뷰티
    # ------------------------------------------------------

    "다비네스": "DAVINES",
    "DAVINES": "DAVINES",

    "비디비치": "VIDIVICI",
    "VIDIVICI": "VIDIVICI",

    "연작": "YUNJAC",
    "YUNJAC": "YUNJAC",

    "설화수": "SULWHASOO",
    "SULWHASOO": "SULWHASOO",

    "헤라": "HERA",
    "HERA": "HERA",

    "에스트라": "AESTURA",
    "AESTURA": "AESTURA",

    "딥티크": "DIPTYQUE",
    "DIPTYQUE": "DIPTYQUE",

    "킬리안": "KILIAN",
    "KILIAN": "KILIAN",

    "크리드": "CREED",
    "CREED": "CREED",

    "메이크업포에버": "MAKE UP FOR EVER",
    "MAKE UP FOR EVER": "MAKE UP FOR EVER",

    "더말로지카": "DERMALOGICA",
    "DERMALOGICA": "DERMALOGICA",

    "에르보리앙": "ERBORIAN",
    "ERBORIAN": "ERBORIAN",

    "딘토": "DINTO",
    "DINTO": "DINTO",

    "힌스": "HINCE",
    "HINCE": "HINCE",

    "오프라": "OFRA",
    "OFRA": "OFRA",

    "브이티코스메틱": "VT COSMETICS",
    "VT 코스메틱": "VT COSMETICS",
    "VT COSMETICS": "VT COSMETICS",

    "코이": "KOY",
    "koy": "KOY",
    "KOY": "KOY",

    "플르부아": "PLEUVOIR",
    "PLEUVOIR": "PLEUVOIR",

    "딸라스파": "THALASPA",
    "THALASPA": "THALASPA",

    "에스쁘아": "ESPOIR",
    "espoir": "ESPOIR",
    "ESPOIR": "ESPOIR",

    "시미헤이즈뷰티": "SIMIHAZE BEAUTY",
    "시미헤이즈 뷰티": "SIMIHAZE BEAUTY",
    "SIMIHAZE BEAUTY": "SIMIHAZE BEAUTY",

    "톤28": "TOUN28",
    "TOUN 28": "TOUN28",
    "TOUN28": "TOUN28",

    "르네휘테르": "RENE FURTERER",
    "RENE FURTERER": "RENE FURTERER",

    "발망헤어": "BALMAIN HAIR",
    "BALMAIN HAIR": "BALMAIN HAIR",

    "구딸": "GOUTAL",
    "GOUTAL": "GOUTAL",

    "조러브스": "JO LOVES",
    "JO LOVES": "JO LOVES",

    "세르즈루텐": "SERGE LUTENS",
    "SERGE LUTENS": "SERGE LUTENS",

    "메모파리": "MEMO PARIS",
    "MEMO PARIS": "MEMO PARIS",

    "아틀리에 코롱": "ATELIER COLOGNE",
    "ATELIER COLOGNE": "ATELIER COLOGNE",

    "메종프란시스커정": "MAISON FRANCIS KURKDJIAN",
    "메종 프란시스 커정": "MAISON FRANCIS KURKDJIAN",
    "MAISON FRANCIS KURKDJIAN": "MAISON FRANCIS KURKDJIAN",

    "톰포드 퍼퓸": "TOM FORD PERFUME",
    "TOMFORD PERFUME": "TOM FORD PERFUME",
    "TOM FORD PERFUME": "TOM FORD PERFUME",

    "프라다 퍼퓸": "PRADA PERFUME",
    "PRADA PERFUME": "PRADA PERFUME",

    "메종 마르지엘라 프래그런스": "MAISON MARGIELA FRAGRANCES",
    "메종마르지엘라 퍼퓸": "MAISON MARGIELA FRAGRANCES",
    "MAISON MARGIELA FRAGRANCE": "MAISON MARGIELA FRAGRANCES",
    "MAISON MARGIELA FRAGRANCES": "MAISON MARGIELA FRAGRANCES",

    "돌체앤가바나뷰티": "DOLCE&GABBANA BEAUTY",
    "DOLCE & GABBANA BEAUTY": "DOLCE&GABBANA BEAUTY",
    "DOLCE&GABBANA BEAUTY": "DOLCE&GABBANA BEAUTY",

    "베스앤바디웍스": "BATH & BODY WORKS",
    "배스앤바디웍스": "BATH & BODY WORKS",
    "BATH&BODY WORKS": "BATH & BODY WORKS",
    "BATH & BODY WORKS": "BATH & BODY WORKS",
    "bath&body works": "BATH & BODY WORKS",
    "BBW": "BATH & BODY WORKS",

    "멜린엔게츠": "MALIN+GOETZ",
    "멜린앤게츠": "MALIN+GOETZ",
    "MALIN+GOETZ": "MALIN+GOETZ",

    "페이스팩토리": "FACE FACTORY",
    "FACE FACTORY": "FACE FACTORY",

    "오리베": "ORIBE",
    "ORIBE": "ORIBE",

    # 라페르바
    "라페르바": "라페르바",
    "LA PERVA": "라페르바",

    # ------------------------------------------------------
    # 패션
    # ------------------------------------------------------

    "STB": "STUDIO TOMBOY",
    "스튜디오 톰보이": "STUDIO TOMBOY",
    "톰보이": "STUDIO TOMBOY",
    "STUDIO TOMBOY": "STUDIO TOMBOY",

    "올세인츠": "ALLSAINTS",
    "ALLSAINTS": "ALLSAINTS",

    "말본골프": "MALBON GOLF",
    "MALBON GOLF": "MALBON GOLF",

    "J.Lindeberg": "J.LINDEBERG",
    "J.LINDEBERG": "J.LINDEBERG",

    "노비스": "NOBIS",
    "노비스 남성": "NOBIS",
    "노비스 여성": "NOBIS",
    "NOBIS": "NOBIS",

    "시프트지": "SHIFT.G",
    "SHIFT.G": "SHIFT.G",

    "휴고": "HUGO",
    "HUGO": "HUGO",

    "보스": "BOSS",
    "BOSS": "BOSS",

    "페트레이": "PEUTEREY",
    "PEUTEREY": "PEUTEREY",

    "피레넥스": "PYRENEX",
    "PYRENEX": "PYRENEX",

    "리바이스": "LEVI'S",
    "리바이스 (여)": "LEVI'S",
    "LEVI`S": "LEVI'S",
    "LEVI'S": "LEVI'S",

    "세인트제임스": "SAINT JAMES",
    "SAINT JAMES": "SAINT JAMES",

    "아니아하이에": "ANIA HAIE",
    "아니아 하이에": "ANIA HAIE",
    "ANIAHAIE": "ANIA HAIE",
    "ANIA HAIE": "ANIA HAIE",

    "스와로브스키": "SWAROVSKI",
    "SWAROVSKI": "SWAROVSKI",

    "디디에두보": "DIDIER DUBOT",
    "DIDIER DUBOT": "DIDIER DUBOT",

    "골든듀": "GOLDEN DEW",
    "GOLDEN DEW": "GOLDEN DEW",

    "스타일러스": "STYLUS",
    "STYLUS": "STYLUS",

    "아뜰리에폴린": "ATELIER PAULIN",
    "아뜰리에 폴린": "ATELIER PAULIN",
    "ATELIER PAULIN": "ATELIER PAULIN",

    "GOLDEN GOOSE KOREA": "GOLDEN GOOSE",
    "GOLDEN GOOSE": "GOLDEN GOOSE",

    # ------------------------------------------------------
    # 리빙
    # ------------------------------------------------------

    "까사미아": "CASAMIA",
    "CASAMIA": "CASAMIA",

    "덴비": "DENBY",
    "DENBY": "DENBY",

    "에밀앙리": "EMILE HENRY",
    "EMILE HENRY": "EMILE HENRY",

    "롬멜스바흐": "ROMMELSBACHER",
    "ROMMELSBACHER": "ROMMELSBACHER",

    "미닉스": "MINIX",
    "MINIX": "MINIX",

    "파나소닉": "PANASONIC",
    "Panasonic": "PANASONIC",
    "panasonic": "PANASONIC",
    "PANASONIC": "PANASONIC",

    "뱅앤올룹슨": "BANG&OLUFSEN",
    "BANG & OLUFSEN": "BANG&OLUFSEN",
    "BANG&OLUFSEN": "BANG&OLUFSEN",
    "B&O": "BANG&OLUFSEN",

    "밀레": "MIELE",
    "Miele": "MIELE",
    "MIELE": "MIELE",

    "알텐바흐": "ALTENBACH",
    "ALTENBACH": "ALTENBACH",

    "나흐트만": "NACHTMANN",
    "NACHTMANN": "NACHTMANN",

    "킨토": "KINTO",
    "KINTO": "KINTO",

    "셀레티": "SELETTI",
    "SELETTI": "SELETTI",

    "포커시스": "FOCUSIS",
    "FOCUSIS": "FOCUSIS",

    "제니퍼룸": "JENNIFEROOM",
    "JENNIFEROOM": "JENNIFEROOM",

    "킨제네라": "KEENGENERA",
    "KEENGENERA": "KEENGENERA",

    "마이크로매트": "MICROMAT",
    "MICROMAT": "MICROMAT",

    "라이젠탈": "REISENTHEL",
    "REISENTHEL": "REISENTHEL",

    "산테코": "SANTECO",
    "SANTECO": "SANTECO",

    "게인스보로": "GAINSBORO.C",
    "GAINSBORO.C": "GAINSBORO.C",

    "리튼": "RITTEN",
    "RITTEN": "RITTEN",

    "리한": "LIHAN",
    "LIHAN": "LIHAN",

    "노몬": "NOMON",
    "NOMON": "NOMON",

    "빌레로이앤보흐": "VILLEROY&BOCH",
    "VILLEROY&BOCH": "VILLEROY&BOCH",

    # ------------------------------------------------------
    # 편집숍 / 셀러
    # ------------------------------------------------------

    "캡슐": "CAPSUL",
    "CAPSUL": "CAPSUL",
    "CAPS:UL": "CAPSUL",
    "CAPS\\:UL": "CAPSUL",

    "두오모": "DUOMO",
    "DUOMO": "DUOMO",

    "LIGHTNOW": "LIGHTNOW",
}


# ==========================================================
# 3. 브랜드 기준 카테고리
# ==========================================================

BRAND_CATEGORY = {

    # ------------------------------------------------------
    # 방금 최종 검수한 4회 이상 브랜드
    # ------------------------------------------------------

    "JO MALONE": ("뷰티", "향수"),

    "EMPORIO ARMANI UNDERWEAR":
        ("패션", "남성의류"),

    "BUTTERO":
        ("패션", "슈즈"),

    "SAINT JAMES":
        ("패션", "의류"),

    "HENRY BEGUELIN":
        ("패션", "가방·잡화"),

    "JANSPORT":
        ("패션", "가방·잡화"),

    "SONY":
        ("리빙", "가전"),

    "FACE FACTORY":
        ("뷰티", ""),

    "PHILIPS":
        ("리빙", "가전"),

    "ENTIRE STUDIOS":
        ("패션", ""),

    "GOLDEN GOOSE":
        ("패션", "슈즈"),

    "TWG TEA":
        ("리빙", "식품"),

    "CONVERSE":
        ("패션", "슈즈"),

    # RAEL은 의도적으로 미분류

    "KENWOOD":
        ("리빙", "가전"),

    "MALIN+GOETZ":
        ("뷰티", ""),

    "MARSHALL":
        ("리빙", "가전"),

    "ATELIER PAULIN":
        ("패션", "주얼리"),

    # 사용자가 준 표에는 리빙>의류였지만
    # 기존 체계상 패션>의류로 처리
    "DEUS EX MACHINA":
        ("패션", "의류"),

    "FELLOW":
        ("리빙", ""),

    "KNIRPS":
        ("패션", "가방·잡화"),

    "LOGITECH":
        ("리빙", "가전"),

    "MIAOU":
        ("패션", "여성의류"),

    "PARABOOT":
        ("패션", "슈즈"),

    "REPETTO":
        ("패션", "슈즈"),

    "SATISFY":
        ("패션", "스포츠"),

    "TEVA":
        ("패션", "슈즈"),

    "ORIBE":
        ("뷰티", ""),

    # ------------------------------------------------------
    # 기존 뷰티
    # ------------------------------------------------------

    "DAVINES":
        ("뷰티", "헤어·바디"),

    "RENE FURTERER":
        ("뷰티", "헤어·바디"),

    "BALMAIN HAIR":
        ("뷰티", "헤어·바디"),

    "VIDIVICI":
        ("뷰티", "메이크업"),

    "HERA":
        ("뷰티", "메이크업"),

    "DINTO":
        ("뷰티", "메이크업"),

    "HINCE":
        ("뷰티", "메이크업"),

    "OFRA":
        ("뷰티", "메이크업"),

    "MAKE UP FOR EVER":
        ("뷰티", "메이크업"),

    "YUNJAC":
        ("뷰티", "스킨케어"),

    "SULWHASOO":
        ("뷰티", "스킨케어"),

    "AESTURA":
        ("뷰티", "스킨케어"),

    "DERMALOGICA":
        ("뷰티", "스킨케어"),

    "ERBORIAN":
        ("뷰티", "스킨케어"),

    "DIPTYQUE":
        ("뷰티", "향수"),

    "KILIAN":
        ("뷰티", "향수"),

    "CREED":
        ("뷰티", "향수"),

    "SERGE LUTENS":
        ("뷰티", "향수"),

    "MEMO PARIS":
        ("뷰티", "향수"),

    "ATELIER COLOGNE":
        ("뷰티", "향수"),

    "JO LOVES":
        ("뷰티", "향수"),

    "GOUTAL":
        ("뷰티", "향수"),

    "TOM FORD PERFUME":
        ("뷰티", "향수"),

    "PRADA PERFUME":
        ("뷰티", "향수"),

    "MAISON FRANCIS KURKDJIAN":
        ("뷰티", "향수"),

    "MAISON MARGIELA FRAGRANCES":
        ("뷰티", "향수"),

    "VT COSMETICS":
        ("뷰티", ""),

    "THALASPA":
        ("뷰티", ""),

    "PLEUVOIR":
        ("뷰티", ""),

    "KOY":
        ("뷰티", ""),

    "BATH & BODY WORKS":
        ("뷰티", ""),

    "DOLCE&GABBANA BEAUTY":
        ("뷰티", ""),

    "TOUN28":
        ("뷰티", ""),

    "SIMIHAZE BEAUTY":
        ("뷰티", ""),

    "ESPOIR":
        ("뷰티", ""),

    "라페르바":
        ("뷰티", ""),

    # ------------------------------------------------------
    # 기존 패션
    # ------------------------------------------------------

    "STUDIO TOMBOY":
        ("패션", "여성의류"),

    "MALBON GOLF":
        ("패션", "골프"),

    "J.LINDEBERG":
        ("패션", "골프"),

    "ANIA HAIE":
        ("패션", "주얼리"),

    "SWAROVSKI":
        ("패션", "주얼리"),

    "DIDIER DUBOT":
        ("패션", "주얼리"),

    "GOLDEN DEW":
        ("패션", "주얼리"),

    "STYLUS":
        ("패션", "주얼리"),

    "ALLSAINTS":
        ("패션", ""),

    "NOBIS":
        ("패션", ""),

    "SHIFT.G":
        ("패션", ""),

    "HUGO":
        ("패션", ""),

    "BOSS":
        ("패션", ""),

    "PEUTEREY":
        ("패션", ""),

    "PYRENEX":
        ("패션", ""),

    "LEVI'S":
        ("패션", ""),

    # ------------------------------------------------------
    # 기존 리빙
    # ------------------------------------------------------

    "CASAMIA":
        ("리빙", "생활·홈"),

    "DENBY":
        ("리빙", "주방"),

    "EMILE HENRY":
        ("리빙", "주방"),

    "ROMMELSBACHER":
        ("리빙", "가전"),

    "MINIX":
        ("리빙", "가전"),

    "PANASONIC":
        ("리빙", "가전"),

    "BANG&OLUFSEN":
        ("리빙", "가전"),

    "MIELE":
        ("리빙", "가전"),

    "ALTENBACH":
        ("리빙", "주방"),

    "NACHTMANN":
        ("리빙", "주방"),

    "KINTO":
        ("리빙", "주방"),

    "VILLEROY&BOCH":
        ("리빙", "주방"),

    "JENNIFEROOM":
        ("리빙", "가전"),

    "KEENGENERA":
        ("리빙", "생활·홈"),

    "MICROMAT":
        ("리빙", "생활·홈"),

    "RITTEN":
        ("리빙", "생활·홈"),

    "GAINSBORO.C":
        ("리빙", "생활·홈"),

    "NOMON":
        ("리빙", "생활·홈"),

    "REISENTHEL":
        ("패션", "가방·잡화"),

    "SANTECO":
        ("리빙", "주방"),

    "LIHAN":
        ("리빙", "주방"),

    "SELETTI":
        ("리빙", ""),

    "FOCUSIS":
        ("리빙", ""),
}


# ==========================================================
# 4. 브랜드만으로 분류하면 안 되는 브랜드
# ==========================================================

PRODUCT_NAME_REQUIRED = {
    "CAPSUL",
    "DUOMO",
    "LIGHTNOW",
    "GARMIN",

    "GUCCI",
    "PRADA",
    "VALENTINO",
    "LOEWE",
    "SAINT LAURENT",
    "BOTTEGA VENETA",
    "ALAIA",
    "TIFFANY&CO.",
    "TOM FORD",
    "HERMES",
    "CHLOE",
    "FERRAGAMO",
    "MIU MIU",
    "CELINE",
}


# ==========================================================
# 5. 브랜드 표준화
# ==========================================================

def standardize_brand(raw_brand):
    raw = clean_text(raw_brand)

    if raw == "":
        return ""

    if raw in BRAND_ALIAS:
        return BRAND_ALIAS[raw]

    upper_raw = upper_if_english(raw)

    if upper_raw in BRAND_ALIAS:
        return BRAND_ALIAS[upper_raw]

    return upper_raw


# ==========================================================
# 6. 상품명 자동 분류
# ==========================================================

def has_any(text, keywords):
    return any(
        keyword in text
        for keyword in keywords
    )


def classify_product_name(product_name):
    product = clean_text(
        product_name
    ).upper()

    if product == "":
        return None

    # ------------------------------------------------------
    # 골프
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "골프",
            "GOLF",
        ],
    ):
        return "패션", "골프"

    # ------------------------------------------------------
    # 주얼리
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "반지",
            "RING",
            "목걸이",
            "NECKLACE",
            "귀걸이",
            "EARRING",
            "팔찌",
            "BRACELET",
            "피어싱",
            "이어커프",
            "PENDANT",
        ],
    ):
        return "패션", "주얼리"

    # ------------------------------------------------------
    # 시계
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "손목시계",
            "여성시계",
            "남성시계",
            "WATCH",
        ],
    ):
        return "패션", "시계"

    # ------------------------------------------------------
    # 향수
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "오 드 퍼퓸",
            "오드퍼퓸",
            "EAU DE PARFUM",
            " EDP",
            "오 드 뚜왈렛",
            "오드뚜왈렛",
            "EAU DE TOILETTE",
            " EDT",
            "퍼퓸",
            "PERFUME",
            "FRAGRANCE",
            "코롱",
            "COLOGNE",
        ],
    ):
        return "뷰티", "향수"

    # ------------------------------------------------------
    # 메이크업
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "파운데이션",
            "FOUNDATION",
            "쿠션",
            "CUSHION",
            "립스틱",
            "LIPSTICK",
            "틴트",
            "BLUSH",
            "블러셔",
            "하이라이터",
            "HIGHLIGHTER",
            "컨실러",
            "CONCEALER",
            "아이섀도",
            "EYESHADOW",
            "마스카라",
            "MASCARA",
            "아이라이너",
            "EYELINER",
            "브로우",
            "BROW",
            "메이크업",
            "MAKEUP",
        ],
    ):
        return "뷰티", "메이크업"

    # ------------------------------------------------------
    # 헤어·바디
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "샴푸",
            "SHAMPOO",
            "트리트먼트",
            "TREATMENT",
            "컨디셔너",
            "CONDITIONER",
            "헤어오일",
            "HAIR OIL",
            "헤어 미스트",
            "HAIR MIST",
            "바디워시",
            "BODY WASH",
            "바디 워시",
            "바디로션",
            "BODY LOTION",
            "바디 로션",
            "바디오일",
            "BODY OIL",
            "바디 오일",
            "핸드크림",
            "HAND CREAM",
            "핸드 워시",
            "HAND WASH",
            "입욕제",
        ],
    ):
        return "뷰티", "헤어·바디"

    # ------------------------------------------------------
    # 스킨케어
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "세럼",
            "SERUM",
            "앰플",
            "AMPOULE",
            "토너",
            "TONER",
            "에센스",
            "ESSENCE",
            "선크림",
            "SUNSCREEN",
            "선에센스",
            "클렌징",
            "CLEANSING",
            "클렌저",
            "CLEANSER",
            "아이크림",
            "수딩",
            "MOISTUR",
        ],
    ):
        return "뷰티", "스킨케어"

    # ------------------------------------------------------
    # 펫
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "강아지",
            "반려견",
            "반려묘",
            "DOG ",
            "CAT ",
            "아이츄",
            "JOINT츄".upper(),
        ],
    ):
        return "리빙", "펫"

    # ------------------------------------------------------
    # 식품
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "초콜릿",
            "CHOCOLATE",
            "커피 캡슐",
            "캡슐커피",
            "드립백",
            "티백",
            "PROTEIN BAR",
            "프로틴바",
        ],
    ):
        return "리빙", "식품"

    # ------------------------------------------------------
    # 가전
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "청소기",
            "VACUUM",
            "가습기",
            "HUMIDIFIER",
            "선풍기",
            "공기청정기",
            "AIR PURIFIER",
            "커피머신",
            "COFFEE MACHINE",
            "토스터",
            "TOASTER",
            "블렌더",
            "BLENDER",
            "에어프라이어",
            "드라이기",
            "헤어드라이",
            "스피커",
            "SPEAKER",
            "이어폰",
            "EARPHONE",
            "HEADPHONE",
            "헤드폰",
            "턴테이블",
            "TURNTABLE",
            "음식물처리기",
            "전기히터",
            "충전기",
            "CHARGER",
            "카메라",
            "CAMERA",
            "믹서기",
            "푸드프로세서",
            "그라인더",
            "키보드",
        ],
    ):
        return "리빙", "가전"

    # ------------------------------------------------------
    # 주방
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "프라이팬",
            "후라이팬",
            "FRY PAN",
            "냄비",
            "WOK",
            "웍",
            "소스팬",
            "접시",
            "PLATE",
            "머그",
            "MUG",
            "텀블러",
            "TUMBLER",
            "글라스",
            "GLASS",
            "고블렛",
            "수저",
            "젓가락",
            "커트러리",
            "CUTLERY",
            "나이프",
            "KNIFE",
            "도마",
            "BOWL",
            "티포트",
            "TEAPOT",
            "주방",
        ],
    ):
        return "리빙", "주방"

    # ------------------------------------------------------
    # 생활·홈
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "침구",
            "이불",
            "BEDDING",
            "베개",
            "PILLOW",
            "러그",
            "RUG",
            "매트리스",
            "MATTRESS",
            "타월",
            "TOWEL",
            "수건",
            "의자",
            "CHAIR",
            "조명",
            "LAMP",
            "벽시계",
            "CLOCK",
            "디퓨저",
            "DIFFUSER",
            "화병",
            "VASE",
            "가구",
            "FURNITURE",
            "옷걸이",
            "HANGER",
        ],
    ):
        return "리빙", "생활·홈"

    # ------------------------------------------------------
    # 완구·취미
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "레고",
            "LEGO",
            "BEARBRICK",
            "베어브릭",
            "피규어",
        ],
    ):
        return "리빙", "완구·취미"

    # ------------------------------------------------------
    # 슈즈
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "스니커즈",
            "SNEAKER",
            "운동화",
            "로퍼",
            "LOAFER",
            "샌들",
            "SANDAL",
            "슬리퍼",
            "SLIPPER",
            "플립플랍",
            "FLIP FLOP",
            "부츠",
            "BOOT",
            "뮬",
            "MULE",
            "펌프스",
            "PUMPS",
            "플랫슈즈",
            "FLAT SHOES",
            "FLATSHOES",
        ],
    ):
        return "패션", "슈즈"

    # ------------------------------------------------------
    # 가방·잡화
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "백팩",
            "BACKPACK",
            "토트백",
            "TOTE BAG",
            "숄더백",
            "SHOULDER BAG",
            "크로스백",
            "CROSSBODY",
            "메신저백",
            "MESSENGER",
            "버킷백",
            "BUCKET BAG",
            "캐리어",
            "TRAVEL CASE",
            "카드지갑",
            "반지갑",
            "지갑",
            "WALLET",
            "벨트",
            "BELT",
            "스카프",
            "SCARF",
            "머플러",
            "MUFFLER",
            "장갑",
            "GLOVE",
            "모자",
            "HAT",
            "선글라스",
            "SUNGLASSES",
            "안경",
            "EYEWEAR",
            "우산",
        ],
    ):
        return "패션", "가방·잡화"

    # ------------------------------------------------------
    # 스포츠
    # ------------------------------------------------------

    if has_any(
        product,
        [
            "래쉬가드",
            "RASHGUARD",
            "러닝화",
            "RUNNING",
            "요가매트",
            "YOGA MAT",
            "스윔",
            "SWIM",
            "트레일 쇼츠",
        ],
    ):
        return "패션", "스포츠"

    # ------------------------------------------------------
    # 남성의류
    # ------------------------------------------------------

    clothes_keywords = [
        "티셔츠",
        "T-SHIRT",
        "셔츠",
        "SHIRT",
        "니트",
        "KNIT",
        "가디건",
        "CARDIGAN",
        "팬츠",
        "PANTS",
        "TROUSERS",
        "자켓",
        "JACKET",
        "재킷",
        "코트",
        "COAT",
        "패딩",
        "후디",
        "HOODIE",
        "스웨터",
        "SWEATER",
        "베스트",
        "VEST",
        "드로즈",
        "UNDERWEAR",
    ]

    if (
        has_any(
            product,
            [
                "남성 ",
                "[MEN]",
                " MEN ",
                "남자 ",
            ],
        )
        and has_any(
            product,
            clothes_keywords,
        )
    ):
        return "패션", "남성의류"

    # ------------------------------------------------------
    # 여성의류
    # ------------------------------------------------------

    if (
        has_any(
            product,
            [
                "여성 ",
                "[WOMEN]",
                " WOMEN ",
                "여자 ",
            ],
        )
        and has_any(
            product,
            clothes_keywords,
        )
    ):
        return "패션", "여성의류"

    # ------------------------------------------------------
    # 성별 불명 의류
    # ------------------------------------------------------

    if has_any(
        product,
        clothes_keywords
        + [
            "원피스",
            "DRESS",
            "스커트",
            "SKIRT",
            "블라우스",
            "BLOUSE",
            "레깅스",
            "LEGGINGS",
        ],
    ):
        return "패션", "의류"

    return None


# ==========================================================
# 7. 여러 상품을 종합해서 분류
# ==========================================================

def classify_from_products(product_names):
    classifications = []

    for product_name in product_names:
        result = classify_product_name(
            product_name
        )

        if result is not None:
            classifications.append(
                result
            )

    if not classifications:
        return "", "", "검수 필요"

    large_values = [
        x[0]
        for x in classifications
    ]

    large_counter = Counter(
        large_values
    )

    if len(large_counter) == 1:
        large = large_values[0]

        middle_values = [
            x[1]
            for x in classifications
            if x[1] != ""
        ]

        if not middle_values:
            return (
                large,
                "",
                "상품명 자동분류",
            )

        middle_counter = Counter(
            middle_values
        )

        if len(middle_counter) == 1:
            return (
                large,
                middle_values[0],
                "상품명 자동분류",
            )

        return (
            large,
            "",
            "상품명 혼합",
        )

    return (
        "",
        "",
        "상품군 혼합",
    )


# ==========================================================
# 8. 최종 분류
# ==========================================================

def determine_category(
    standard_brand,
    product_names,
):

    # RAEL은 일부러 미분류
    if standard_brand == "RAEL":
        return "", "", "검수 필요"

    # 브랜드만으로 위험한 경우
    if standard_brand in PRODUCT_NAME_REQUIRED:
        return classify_from_products(
            product_names
        )

    # 브랜드 기준값
    if standard_brand in BRAND_CATEGORY:
        large, middle = (
            BRAND_CATEGORY[
                standard_brand
            ]
        )

        if middle != "":
            return (
                large,
                middle,
                "브랜드 기준",
            )

        product_result = (
            classify_from_products(
                product_names
            )
        )

        product_large = (
            product_result[0]
        )

        product_middle = (
            product_result[1]
        )

        if (
            product_large == large
            and product_middle != ""
        ):
            return (
                large,
                product_middle,
                "브랜드+상품명",
            )

        return (
            large,
            "",
            "브랜드 기준",
        )

    return classify_from_products(
        product_names
    )


# ==========================================================
# 9. Google Sheet 헤더 찾기
# ==========================================================

def find_header_index(values):
    for i, row in enumerate(
        values
    ):
        cleaned = [
            clean_text(x)
            for x in row
        ]

        if (
            "상품명" in cleaned
            and "브랜드명" in cleaned
        ):
            return i

    raise ValueError(
        "상품명 / 브랜드명 헤더를 찾지 못했습니다."
    )


# ==========================================================
# 10. 실행
#
# 이번 버전 핵심:
# 원본 브랜드별이 아니라 표준브랜드별로 GROUP BY
# → 중복 브랜드 CSV에서 제거
# ==========================================================

def main():

    print()
    print(
        "구글시트에서 브랜드 데이터를 불러오는 중..."
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

    if "브랜드명" not in df.columns:
        raise ValueError(
            "브랜드명 열을 찾지 못했습니다."
        )

    if "상품명" not in df.columns:
        raise ValueError(
            "상품명 열을 찾지 못했습니다."
        )

    df["브랜드명"] = (
        df["브랜드명"]
        .apply(
            clean_text
        )
    )

    df["상품명"] = (
        df["상품명"]
        .apply(
            clean_text
        )
    )

    df = df[
        df["브랜드명"] != ""
    ].copy()

    df[
        "표준브랜드명"
    ] = (
        df["브랜드명"]
        .apply(
            standardize_brand
        )
    )

    result_rows = []

    # ======================================================
    # ★ 표준브랜드명 기준으로 묶음
    # ======================================================

    for (
        standard_brand,
        group
    ) in df.groupby(
        "표준브랜드명",
        dropna=False,
    ):

        # 원본 브랜드명 목록
        raw_brands = (
            group[
                "브랜드명"
            ]
            .dropna()
            .astype(str)
            .map(
                clean_text
            )
            .unique()
            .tolist()
        )

        raw_brands = [
            x
            for x in raw_brands
            if x != ""
        ]

        raw_brand_text = (
            " / ".join(
                raw_brands
            )
        )

        # 총 등장횟수
        count = len(
            group
        )

        # 전체 상품명
        all_products = (
            group[
                "상품명"
            ]
            .dropna()
            .astype(str)
            .map(
                clean_text
            )
        )

        all_products = [
            x
            for x in all_products
            if x != ""
        ]

        unique_products = list(
            dict.fromkeys(
                all_products
            )
        )

        product_examples = (
            unique_products[:3]
        )

        (
            large,
            middle,
            method,
        ) = determine_category(
            standard_brand,
            unique_products,
        )

        result_rows.append(
            {
                "원본브랜드명":
                    raw_brand_text,

                "표준브랜드명":
                    standard_brand,

                "등장횟수":
                    count,

                "대카테고리":
                    large,

                "중카테고리":
                    middle,

                "처리방식":
                    method,

                "상품예시1":
                    (
                        product_examples[0]
                        if len(product_examples) >= 1
                        else ""
                    ),

                "상품예시2":
                    (
                        product_examples[1]
                        if len(product_examples) >= 2
                        else ""
                    ),

                "상품예시3":
                    (
                        product_examples[2]
                        if len(product_examples) >= 3
                        else ""
                    ),

                "비고":
                    "",
            }
        )

    result = pd.DataFrame(
        result_rows
    )

    # ======================================================
    # 검수 필요한 것 먼저 보이도록 정렬
    # ======================================================

    method_order = {
        "상품군 혼합": 1,
        "검수 필요": 2,
        "상품명 혼합": 3,
        "상품명 자동분류": 4,
        "브랜드+상품명": 5,
        "브랜드 기준": 6,
    }

    result[
        "_처리순서"
    ] = (
        result[
            "처리방식"
        ]
        .map(
            method_order
        )
        .fillna(99)
    )

    result = (
        result
        .sort_values(
            by=[
                "_처리순서",
                "등장횟수",
                "표준브랜드명",
            ],
            ascending=[
                True,
                False,
                True,
            ],
        )
        .drop(
            columns=[
                "_처리순서"
            ]
        )
        .reset_index(
            drop=True
        )
    )

    # ======================================================
    # 저장
    # ======================================================

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ======================================================
    # 결과 통계
    # ======================================================

    total_raw = (
        df[
            "브랜드명"
        ]
        .nunique()
    )

    total_standard = (
        result[
            "표준브랜드명"
        ]
        .nunique()
    )

    categorized_count = (
        result[
            "대카테고리"
        ]
        .astype(str)
        .str.strip()
        .ne("")
        .sum()
    )

    review_count = (
        result[
            "처리방식"
        ]
        .eq(
            "검수 필요"
        )
        .sum()
    )

    mixed_count = (
        result[
            "처리방식"
        ]
        .eq(
            "상품군 혼합"
        )
        .sum()
    )

    print()
    print(
        "=" * 60
    )

    print(
        "브랜드 표준화 + 중복 통합 + 카테고리 분류 완료"
    )

    print(
        "=" * 60
    )

    print(
        f"원본 브랜드 종류: "
        f"{total_raw:,}개"
    )

    print(
        f"표준 브랜드 종류: "
        f"{total_standard:,}개"
    )

    print(
        f"중복 통합된 브랜드 수: "
        f"{total_raw - total_standard:,}개"
    )

    print()

    print(
        f"대카테고리 분류 완료: "
        f"{categorized_count:,} / "
        f"{total_standard:,}"
    )

    if total_standard > 0:
        rate = (
            categorized_count
            / total_standard
            * 100
        )

        print(
            f"대카테고리 분류율: "
            f"{rate:.1f}%"
        )

    print(
        f"검수 필요: "
        f"{review_count:,}개"
    )

    print(
        f"상품군 혼합: "
        f"{mixed_count:,}개"
    )

    print()

    print(
        f"생성 파일: "
        f"{OUTPUT_FILE}"
    )

    print()

    print(
        "※ 동일 브랜드의 한글/영문 표기는 "
        "표준브랜드명 한 줄로 합쳐집니다."
    )

    print(
        "※ 아직 상품 MASTER에는 반영하지 않았습니다."
    )

    print()


if __name__ == "__main__":
    main()
