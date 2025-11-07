import re

TEXT_COLS = {
    "name": "PRDLST_NM",
    "func": "PRIMARY_FNCLTY",
    "raw":  "RAWMTRL_NM",
}

OPTIONAL_COLS = [
    "IFTKN_ATNT_MATR_CN",
    "PRDT_SHAP_CD_NM",
    "NTK_MTHD",
    "LAST_UPDT_DTM",
]

CATEGORY_PATTERNS = {
    "Vitamin A":        [r"비타민\s*a\b", r"\bvitamin\s*a\b", r"레티놀|retinol"],
    "Vitamin B-Complex":[r"비타민\s*b\s*콤플렉스|b\s*군|b군", r"b-?complex", r"\bvitamin\s*b(?!\s*12)\b"],
    "Vitamin B1":       [r"비타민\s*b\s*1\b|티아민|thiamin[e]?"],
    "Vitamin B2":       [r"비타민\s*b\s*2\b|리보플라빈|riboflavin"],
    "Vitamin B6":       [r"비타민\s*b\s*6\b|피리독신|pyridoxine"],
    "Vitamin B12":      [r"비타민\s*b\s*12\b|코발라민|cobalamin|메틸코발라민"],
    "Vitamin C":        [r"비타민\s*c\b|ascorbic|아스코르빈"],
    "Vitamin D":        [r"비타민\s*d\b|\bvitamin\s*d\b|\bd3\b|콜레칼시페롤"],
    "Vitamin E":        [r"비타민\s*e\b|tocopherol|토코페롤"],
    "Vitamin K":        [r"비타민\s*k\b|\bvitamin\s*k\b|메나퀴논|menaquinone"],
    "Calcium":          [r"칼슘|\bcalcium\b|\bca\b"],
    "Magnesium":        [r"마그네슘|\bmagnesium\b|\bmg\b"],
    "Iron":             [r"철분|철\b|\biron\b|페리틴|ferr|헴철|헤믹"],
    "Zinc":             [r"아연|\bzinc\b|\bzn\b"],
    "Selenium":         [r"셀레늄|\bselenium\b|\bse\b"],
    "Iodine":           [r"요오드|요오드화|\biodine\b"],
    "Omega-3":          [r"오메가\s*[- ]?3|\bomega[- ]?3\b|\bdha\b|\bepa\b|알갈|조류\s*오일|algal"],
    "Krill Oil":        [r"크릴\s*오일|\bkrill\b"],
    "Lutein/Zeaxanthin":[r"루테인|제아잔틴|zeaxanthin|마리골드|marigold"],
    "Bilberry":         [r"빌베리|bilberry"],
    "CoQ10":            [r"코엔자임\s*q?\s*10|coq10|유비퀴논|ubiquinone"],
    "Alpha-Lipoic Acid":[r"알파\s*리포산|lipoic|\bala\b"],
    "Resveratrol":      [r"레스베라트롤|resveratrol"],
    "Taurine":          [r"타우린|\btaurine\b"],
    "Probiotics":       [r"프로바이오틱|유산균|lactobacillus|bifidobacter|비피도|바이오틱스"],
    "Prebiotics":       [r"프리바이오틱|이눌린|\bfos\b|프락토올리고당|\bgos\b|갈락토올리고당|난소화성"],
    "Synbiotics":       [r"신바이오틱|synbiot"],
    "Glucosamine/Chondroitin":[r"글루코사민|콘드로이틴|chondroitin|\bmsm\b"],
    "MSM":              [r"\bmsm\b|메틸설포닐메탄"],
    "Milk Thistle":     [r"밀크\s*씨슬|실리마린|silymarin|silybum"],
    "Collagen":         [r"콜라겐|collagen|펩타이드\s*콜라겐"],
    "Hyaluronic Acid":  [r"히알루론|hyaluronic"],
    "Biotin":           [r"비오틴|biotin"],
    "Berberine":        [r"베르베린|berberine"],
    "Inositol":         [r"이노시톨|inositol"],
    "Ginseng/Red Ginseng":[r"홍삼|인삼|ginseng|진세노사이드|ginsenoside"],
    "Folate":           [r"엽산|folate|folic"],
    "Multivitamin":     [r"멀티\s*비타민|종합\s*비타민|multivit(amin|)"],
    "Chlorella":        [r"클로렐라|chlorella"],
}

NEGATIVE_PATTERNS = [r"철갑", r"철근", r"철도", r"철제", r"철관", r"철학", r"철학자"]
SOURCE_WEIGHT = {"func": 3.0, "name": 2.0, "raw": 1.0}

GOAL_TO_CATS = {
    "수면/이완": ["Magnesium"],
    "에너지/피로": ["Vitamin B-Complex", "CoQ10"],
    "집중/인지": ["Omega-3", "Vitamin B12"],
    "관절/뼈": ["Calcium", "Glucosamine/Chondroitin", "MSM", "Vitamin D"],
    "피부/모발": ["Collagen", "Biotin", "Hyaluronic Acid"],
    "눈 건강": ["Lutein/Zeaxanthin", "Bilberry"],
    "간 건강": ["Milk Thistle"],
    "혈당/대사": ["Berberine", "Inositol"],
    "면역/항산화": ["Vitamin C", "Vitamin D", "Zinc", "Resveratrol"],
}

AGE_BASE_CATS = {
    "10대": ["Multivitamin","Vitamin A","Vitamin B-Complex","Vitamin C","Vitamin D","Zinc","Calcium"],
    "20대": ["Vitamin B-Complex"],
    "30대": ["Vitamin B-Complex"],
    "40대": ["Vitamin C","Omega-3","CoQ10","Calcium","Magnesium"],
    "50대 이상": ["Vitamin C","Omega-3","CoQ10","Calcium","Magnesium","Vitamin B12"],
}

AGE_EXTRA_60PLUS = ["Omega-3","Lutein/Zeaxanthin","Selenium","Chlorella"]

INTAKE_TIPS = {
    "Multivitamin": "식후 권장(미네랄 포함 시 위장 편함)",
    "Vitamin B-Complex": "아침 공복 권장(속 불편하면 식후)",
    "Vitamin C": "식후 권장(흡수/위장 편의)",
    "Vitamin D": "식사 후(지용성, 지방과 함께)",
    "Calcium": "식후 권장(흡수/위장 편의)",
    "Magnesium": "저녁 식후 자주 권장(이완)",
    "Zinc": "식후 권장(빈속은 메스꺼움)",
    "Omega-3": "식후 0~15분(지용성, 지방과 함께)",
    "CoQ10": "식후 권장(지용성, Omega-3와 궁합)",
    "Lutein/Zeaxanthin": "식후 권장(지용성)",
    "Selenium": "식후 권장",
    "Chlorella": "식사와 함께 또는 식후",
    "Folate": "식사와 무관(산모용은 전문의 상담)",
}

FRIENDLY_KO = {
    "Multivitamin": "종합영양제",
    "Vitamin A": "비타민 A",
    "Vitamin B-Complex": "비타민 B군",
    "Vitamin C": "비타민 C",
    "Vitamin D": "비타민 D",
    "Vitamin B12": "비타민 B12",
    "Vitamin E": "비타민 E",
    "Vitamin K": "비타민 K",
    "Calcium": "칼슘",
    "Magnesium": "마그네슘",
    "Zinc": "아연",
    "Iron": "철",
    "Omega-3": "오메가-3",
    "Probiotics": "프로바이오틱스(유산균)",
    "Lutein/Zeaxanthin": "루테인/지아잔틴",
    "Selenium": "셀레늄",
    "Chlorella": "클로렐라",
    "CoQ10": "코엔자임 Q10",
}

REASONS = {
    "Multivitamin": "성장·활동에 필요한 비타민/미네랄을 골고루 보충",
    "Vitamin A": "시각세포 성장·시력 건강",
    "Vitamin B-Complex": "에너지 대사 지원(스트레스/활동량↑ 시)",
    "Vitamin C": "콜라겐 형성·항산화",
    "Vitamin D": "칼슘 흡수·근력·면역",
    "Vitamin B12": "고령층에서 흡수 저하 보완",
    "Calcium": "골격 형성·골다공증 예방",
    "Magnesium": "근육 이완·수면 보조·칼슘 균형",
    "Zinc": "조직 성장·면역·피부",
    "Omega-3": "혈행·중성지방·심혈관 건강",
    "Probiotics": "장내균형·소화·면역",
    "Lutein/Zeaxanthin": "노년층 눈 건강(황반/백내장) 보조",
    "Selenium": "강력 항산화",
    "Chlorella": "단백질·미량영양소 보충",
    "CoQ10": "항산화·에너지(오메가-3와 궁합)",
}

FRIENDLY_ORDER = [
    "Multivitamin", "Vitamin B-Complex", "Vitamin C", "Vitamin D",
    "Calcium", "Magnesium", "Zinc", "Iron",
    "Omega-3", "Probiotics",
    "CoQ10", "Lutein/Zeaxanthin", "Selenium", "Chlorella",
    "Vitamin A", "Vitamin B12", "Vitamin E", "Vitamin K",
]

# Exclude kid-targeted products for non-teen age bands
KID_EXCLUDE_PATTERNS = [
    r"키즈",
    r"우리\s*아이",
    r"\b아이\b",
    r"어린이",
    r"유아|베이비",
    r"\bkids?\b|children|child",
]

