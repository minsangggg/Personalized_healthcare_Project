
#!/usr/bin/env python3
"""Weekly automation for ingredient cleansing and master sync."""
from __future__ import annotations

import argparse
import ast
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import quote_plus

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_FILE_DEFAULT = Path(__file__).with_name('state.json')
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

REMOVE_KEYWORDS: Set[str] = {
    'PN멀티팟','가루소스','간장','거름망','계량',
    '고운','고추가루','고추장','고춧','고춧가루',
    '고춧기름','국간장','국물','국자','굴소스','그릇',
    '기름','까나리','깨','깨소금','꼬지','나무꼬지',
    '냄비','냉수','노른자','녹말','뉴 슈거',
    '뉴슈가','다시다','도마','된장','드레싱',
    '들기름','라면스톡','라면스프','랩','랩으로','럼',
    '마가린','마요네즈',
    '맛간장',
    '맛술',
    '매실액',
    '맥주',
    '머스타드',
    '머스터드',
    '면수',
    '물',
    '물엿',
    '미림',
    '발사믹',
    '버너',
    '버터',
    '베이스',
    '베이킹',
    '볼',
    '비닐',
    '비닐팩',
    '빨대',
    '사리곰탕스프',
    '사이다',
    '새우젓',
    '생수',
    '설탕',
    '소금',
    '소스',
    '소주',
    '숟가락',
    '숟가락으로',
    '스톡',
    '스프가루',
    '시럽',
    '시즈닝',
    '시판용',
    '식기',
    '식용유',
    '식초',
    '쌈장',
    '액젓',
    '양념',
    '양념간장',
    '양념장',
    '에센스',
    '엑기스',
    '엑스',
    '오븐',
    '오일',
    '올리고',
    '올리고 당',
    '올리고당',
    '올리브 오일',
    '올리브유',
    '와사비',
    '와인',
    '요리 당',
    '요리당',
    '용기',
    '용량',
    '월계수',
    '위스키',
    '유',
    '육수',
    '은박컵',
    '인스턴트',
    '장국',
    '전분',
    '전자렌지',
    '젓가락',
    '젓갈',
    '젓개',
    '조미',
    '종이컵',
    '즉석',
    '즙',
    '진간장',
    '집게',
    '찜기',
    '찜솥',
    '참기름',
    '참치액',
    '천일염',
    '청',
    '청국장',
    '청주',
    '초고추장',
    '카놀라유',
    '캐첩',
    '컵',
    '케첩',
    '콜라',
    '토마토케첩',
    '틀',
    '페스토',
    '펩시',
    '포도씨유',
    '포장',
    '프라이팬',
    '허브',
    '허브 솔트',
    '허브맛 솔트',
    '허브맛솔트',
    '허브솔트',
    '호일',
    '후추',
    '후춧가루',
    '흰자',
}


def normalize_common_name(name: str) -> str:
    """Collapse variants of commonly grouped ingredients."""
    name = name.strip()
    if '마늘' in name:
        return '마늘'
    return name

class IngredientETL:
    def __init__(self):
        # ✅ 고기류 표준화
        self.meat_patterns = {
            #소고기
            r'소고기.*양지|양지머리|소고기양지': '소고기_양지',
            r'소고기.*국거리|국거리용 소고기': '소고기_국거리',
            r'소고기.*갈비찜': '소고기_갈비찜',
            r'소고기.*등심': '소고기_등심',
            r'꽃등심': '소고기_꽃등심',
            r'불고기용 소고기': '소고기',
            r'갈비탕용[ ]*소고기': '소고기_갈비탕',
            r'갈비찜고기': '소고기_갈비찜',
            r'간[ ]*소고기|소고기[ ]*간|소고기[ ]*다짐|갈은[ ]*소고기|소고기[ ]*갈은': '소고기_다짐육',
            r'쇠고기': '소고기_양지',

            # 🐖 돼지고기
            r'돼지고기.*다짐육|돼지고기간|돼지고기[ ]*갈은|돼지고기[ ]*간|간[ ]*돼지고기': '돼지고기_다짐육',
            r'돼지고기.*삼겹살|대패삼겹살|대패돼지고기|대패 삼겹살': '돼지고기_삼겹살',
            r'돼지고기.*등심|돼지등심': '돼지고기_등심',
            r'돼지고기.*목살|돼지목살|돼지고기목심': '돼지고기_목살',
            r'돼지고기.*안심': '돼지고기_안심',
            r'돼지고기.*사태': '돼지고기_사태',
            r'돼지고기.*오겹살': '돼지고기_오겹살',
            r'돼지고기.*불고기': '돼지고기_불고기',
            r'돼지고기.*전지|돼지고기앞다리살|돼지고기앞다리|불고기용 돼지고기 앞다리살|국거리 돼지고기|돼지앞다리살|돼지고기 수육꺼리앞다리살': '돼지고기_앞다리살',
            r'돼지고기.*찌개': '돼지고기_찌개',
            r'돼지등갈비': '돼지고기_등갈비',
            r'돼지등뼈|감자탕용 돼지등뼈': '돼지고기_등뼈',
            r'돼지껍데기': '돼지고기_껍데기',
            r'돼지갈비': '돼지고기_갈비',
            r'보쌈용 돼지고기|두툼한 돼지고기': '돼지고기',
            
            # 🐔 닭고기
            r'닭.*가슴살': '닭고기_가슴살',
            r'닭.*닭봉': '닭고기_닭봉',
            r'닭.*다리': '닭고기_다리',
            r'닭.*날개': '닭고기_날개',
            r'닭.*안심': '닭고기_안심',
            r'닭.*모래집': '닭고기_모래집',
            r'닭.*볶음탕|볶음용': '닭고기_닭볶음탕',
            r'닭 한마리|닭고기': '닭고기',

            # 기타
            r'베이컨': '베이컨',
        }

        # ----------------------------------
        # ✂️ 불필요한 단어·형용사 제거 및 통합 규칙
        # ----------------------------------
        self.description_patterns = [
            # 신규·보강 규칙
            (r'.*김치.*', '김치'),
            (r'^(?=.*김)(?!.*튀김가루)(?!.*김치).*$', '김'),
            (r'.*베이컨.*', '베이컨'),
            (r'.*이태리[ ]*파슬리.*', '파슬리'),
            (r'.*(핫케이크[ ]*가루|핫케이크가루|핫케익가루|핫케잌가루).*', '핫케이크가루'),
            (r'.*크랜베리.*', '건크랜베리'),
            (r'.*(고추가루|고춧가루).*', '고추가루'),
            (r'.*고추[ ]*가루.*', '고추가루'),
            (r'.*국간장.*', '국간장'),
            (r'.*만두.*', '만두'),
            (r'.*만두피.*', '만두피'),  # ⚠️ 예외 규칙은 위 만두보다 먼저 위치해야 함
            (r'.*맛술.*', '맛술'),
            (r'.*(머스타드|머스터드).*', '머스타드'),
            (r'.*명란.*', '명란'),
            (r'.*무우.*', '무'),
            (r'.*새송이.*', '새송이버섯'),
            (r'.*(밀가루|중력분|박력분).*', '밀가루'),
            (r'.*배추.*', '배추'),
            (r'.*부대찌개용[ ]*콩.*', '콩'),
            (r'.*봄동.*', '봄동'),
            (r'.*비엔나.*', '햄/소시지'),
            (r'.*생닭.*', '닭고기'),
            (r'.*(샤부샤부용|샤브샤브용)[ ]*소고기.*', '소고기_샤브샤브'),
            (r'.*알배기.*', '알배추'),
            (r'.*(얼갈이[ ]*배추|얼갈이).*', '얼갈이배추'),
            (r'.*와사비.*', '와사비'),
            (r'.*청주.*', '청주'),
            (r'.*후리가케.*', '후리카케'),
            (r'.*알배추.*', '알배추'),             
            (r'.*볶음탕.*', '닭고기_닭볶음탕'), 
            (r'.*소고기.*목심.*', '소고기_목심'),   
            (r'.*골뱅이.*', '골뱅이'),   
            (r'.*(청양고추|꽈리고추).*', '꽈리고추'),
            (r'.*마늘.*', '다진마늘'),
            (r'.*굴.*', '굴'),
            (r'.*설탕.*', '설탕'),
            (r'.*고등어.*', '고등어'),
            (r'.*가자미.*', '가자미'),
            (r'.*낙지.*', '낙지'),
            (r'.*콘.*', '옥수수'),
            (r'.*스파게티.*', '스파게티면'),
            (r'.*양상추.*', '양상추'),
            (r'.*미역.*', '미역'),
            (r'.*호박.*', '호박'),
            (r'.*쪽파.*', '파'),
            (r'.*고구마.*', '고구마'),
            (r'.*차돌박이.*', '차돌박이'),
            (r'.*당근.*', '당근'),
            (r'.*표고.*', '표고버섯'),
            (r'.*크래미.*|.*크레미.*', '맛살'),
            (r'.*파인애플.*', '파인애플'),
            (r'.*페퍼론치노.*|.*페페로치노.*|.*페페론치노.*|.*페페론치니.*', '건고추'),
            (r'.*페투치니면.*', '파스타면'),
            (r'.*플레인.*', '플레인요거트'),
            (r'.*앞다리살.*', '돼지고기_앞다리살'),
            (r'.*바지락.*', '바지락'),
            (r'.*해산.*', '해물'),
            (r'.*양파.*', '양파'),
            (r'.*감자.*', '감자'),
            (r'.*황태.*', '황태'),
            (r'.*우유.*', '우유'),
            (r'.*삼겹.*', '돼지고기_삼겹살'),
            (r'.*대파.*', '파'),
            (r'.*채[ ]*무.*', '무'),                  
            (r'.*무우.*', '무'),
            (r'.*무.*', '무'),
            (r'.*알배추.*', '알배추'),               
            (r'.*알배기.*', '알배추'),
            (r'.*(얼갈이[ ]*배추|얼갈이).*', '얼갈이배추'),
            (r'.*미니토마토.*', '방울토마토'),          
            (r'.*완숙토마토.*', '토마토'),                
            
            # 닭고기류
            (r'.*뼈[ ]*제거.*닭.*한마리.*', '닭'),       
            (r'.*(백숙용|영계).*닭.*', '닭고기_삼계탕'),    
            (r'.*(영계닭|영계).*', '닭고기_삼계탕'),        
            (r'.*삼계탕용.*', '닭고기_삼계탕'),             
            (r'.*볶음탕.*', '닭고기_닭볶음탕'),             
            (r'.*생닭.*', '닭고기'),           
            (r'.*절단[ ]*닭.*', '닭고기'),
                       
            # 새우/게류
            (r'.*건새우.*', '건새우'),
            (r'(?<!건).*새우.*', '새우'),
            (r'(?=.*게)(?!.*스파게티).*', '게'),

            # 소고기 세부 부위
            (r'.*소고기불고기.*|.*한우.*소고기불고기.*', '소고기_불고기'),
            (r'.*소고기샤브샤브.*', '소고기_샤브샤브'),
            (r'.*소고기차돌박이.*', '소고기_차돌박이'),
            (r'.*소고기척아이롤.*', '소고기_척아이롤'),
            (r'.*한우.*소고기.*살치살.*', '소고기_살치살'),
            (r'.*한우.*양지.*', '소고기_양지'),
            (r'.*스테이크용고기.*', '소고기'),
            (r'.*(아롱사태.*소고기|소고기.*아롱사태|아롱사태).*', '소고기_아롱사태'),
            (r'.*업진살[ ]*소고기.*', '소고기_업진살'),
            (r'.*소고기.*목심.*', '소고기_목심'),
            (r'.*(샤부샤부용|샤브샤브용)[ ]*소고기.*', '소고기_샤브샤브'),

            # 돼지고기 세부 부위
            (r'.*수육용[ ]*(삼겹살|통삼겹).*', '돼지고기_삼겹살'),
            (r'.*항정살.*', '돼지고기_항정살'),

            # 면류
            (r'.*소면.*', '소면'),
            (r'.*떡볶이.*', '떡볶이 떡'),
            (r'.*우동.*', '우동사리'),
            (r'.*칼국수.*', '칼국수면'),
            (r'.*스파게티[ ]*면.*', '파스타면'),

            # 해산물·일반 재료
            (r'.*해물.*', '해물'),
            (r'.*오징어.*', '오징어'),
            (r'.*문어.*', '문어'),
            (r'.*바지락.*', '바지락'),
            (r'.*꼬막.*', '꼬막'),
            (r'.*꽁치.*', '꽁치'),
            (r'.*가다랭이포.*|.*가쓰오부시.*|.*가츠오부시.*', '가쓰오부시'),

            # 기본 재료·조미료
            (r'.*돈까스.*', '돈가스'),
            (r'.*된장.*', '된장'),
            (r'.*설탕.*', '설탕'),
            (r'.*생강.*', '다진생강'),

            # 기타 통합
            (r'.*양상추.*', '양상추'),
            (r'.*어묵.*', '어묵'),
            (r'.*불고기.*', '불고기'),
            (r'.*맛살.*', '맛살'),
            (r'.*치킨너겟.*|.*너겟.*', '치킨너겟'),
            (r'.*카레.*', '카레'),
            (r'.*김.*', '김'),
            (r'.*깨.*', '깨'),
            (r'.*멸치.*', '멸치'),
            (r'.*옥수수.*', '옥수수'),
            (r'.*(햄|소세지|소시지|스팸).*', '햄/소시지'),
            (r'.*오리.*', '훈제오리'),
            (r'.*시판[ ]*콩비지.*', '콩비지'),
            (r'.*부대찌개용[ ]*콩.*', '콩'),
            
            # 유제품 / 디저트
            (r'.*액티비아.*', '플레인요거트'),

            # 곡류 / 밀가루 / 가루류
            (r'.*(밀가루|중력분|박력분).*', '밀가루'),

            # 떡류
            (r'.*떡볶이.*', '떡볶이떡'),
            (r'.*(떡국[ ]*떡|떡국용[ ]*떡|떡국용떡).*', '떡국떡'),

            # 기타 재료
            (r'.*모둠전.*|.*모듬전.*', '모둠전'),
            (r'.*새송이.*', '새송이버섯'),
            (r'.*파[ ]*뿌리.*', '파뿌리'),
            (r'.*파[ ]*흰부분.*', '파'),
            (r'^닭$', '닭고기'),
            (r'.*(커피[ ]*믹스|커피가루|커피).*', '커피가루'),
            (r'.*(코코아[ ]*가루|코코아[ ]*분말).*', '코코아 가루'),
            (r'.*(홍[ ]*고추|홍고추).*', '고추'),

        ]

        # ----------------------------------
        # 품목 통합 (마지막 레이어)
        # ----------------------------------
        self.name_unify_patterns = {
            r'^감자.*': '감자',
            r'^고구마.*': '고구마',
            r'^양파.*': '양파',
            r'^대파.*|파$': '파',
            r'.*버섯.*': '버섯',
            r'휘핑크림.*|생크림.*': '휘핑크림',
            r'파프리카.*': '파프리카',
            r'피망.*': '피망',
            r'오이.*': '오이',
            r'달걀.*|계란.*': '계란',
            r'김치.*': '김치',
            r'^당근.*': '당근',
            r'브로콜리.*|브로컬리.*': '브로콜리',
            r'두부.*': '두부',
            r'.*치즈.*': '치즈',
            r'참치.*': '참치',
            r'양배추.*': '양배추',
            r'쌀.*|밥.*': '쌀/밥',
            r'채소.*|야채.*': '채소',
        }

        # ----------------------------------
        # 수식어/불필요한 단어 제거
        # ----------------------------------
        self.redundant_modifiers = [
            "다진", "썬", "잘게", "채썬", "볶은", "삶은", "데친",
            "익힌", "말린", "껍질벗긴", "씨뺀", "통째로", "조각낸",
            "조각", "슬라이스", "얇게썬", "잘게썬", "큰", "작은",
            "적당히", "조금", "사이즈", "냉동", "중간", "것",
            "먹을만큼", "파리", "조그만", "한입"
        ]
    # --------------------------
    # 불필요 단어 제거
    # --------------------------
    def remove_description(self, ingredient: str) -> str:
        result = ingredient
        for pattern, replacement in self.description_patterns:
            result = re.sub(pattern, replacement, result)
        return ' '.join(result.split()).strip()

    # --------------------------
    # 고기류 표준화
    # --------------------------
    def normalize_meat(self, ingredient: str) -> str:
        for pattern, standard in self.meat_patterns.items():
            if re.search(pattern, ingredient):
                return standard
        return ingredient.strip()

    # --------------------------
    # 재료명 통합
    # --------------------------
    def unify_name(self, ingredient: str) -> str:
        name = ingredient
        for word in self.redundant_modifiers:
            name = re.sub(word, '', name)
        for pattern, unified in self.name_unify_patterns.items():
            if re.search(pattern, name):
                name = unified
                break
        return name.strip()


# ========================================
# 2. 재료명/단위 분리 함수
# ========================================

def make_ingredient_dict(ingredient_list):
    """
    재료 리스트를 {'재료명': '양/단위'} 형태로 변환
    """
    ingredient_dict = {}

    # 단위/표현 키워드 목록
    amount_keywords = [
        '약간', '적당히', '조금', '큼직하게', '솔솔', '톡톡', '적당량', '한줌',
        '보통사이즈', '작은거', '큰캔', '선택사항', '생략가능', '크게', '깍아서',
        '중간크기', '중간사이즈', '또는', '손가락길이', '손가락 길이', '정도', '소량',
        '듬뿍', '넉넉히', '취향껏', '원하는만큼', '기호에맞게', '필요한만큼', '탈탈탈', '살짝',
        '인분', '개', '큰술', '작은술', '숟가락', '컵', 't', 'T', 'ml', 'g', '줌'
    ]

    # 수량 / 단위 패턴 (숫자 + 단위 or 키워드)
    amount_pattern = re.compile(
        r'('
        r'(?:\d[\d\/\.\~]*\s*[가-힣A-Za-z%]*)'
        + '|' + '|'.join(amount_keywords) +
        r')'
    )

    for item in ingredient_list:
        if not item or not isinstance(item, str):
            continue

        item = item.strip()
        name, raw_amount = "", ""

        # ------------------------------------
        # 1️⃣ 숫자 또는 키워드 기준 분리 (우선)
        # ------------------------------------
        parts = re.split(r'\s*(?=\d|' + '|'.join(amount_keywords) + r')', item)
        name = parts[0].strip()
        matches = amount_pattern.findall(item)
        raw_amount = ' '.join(matches).strip() if matches else ""

        # ------------------------------------
        # 2️⃣ 숫자/단위가 없으면 공백 기준 보조 분리
        # ------------------------------------
        if not raw_amount:
            parts = re.split(r'\s{2,}', item)
            if len(parts) == 2:
                name, raw_amount = parts[0].strip(), parts[1].strip()

        # ------------------------------------
        # 3️⃣ 텍스트 정제
        # ------------------------------------
        name = re.sub(r'[^가-힣A-Za-z0-9\s]', '', name).strip()
        raw_amount = re.sub(r'\s+', ' ', raw_amount).strip()

        # ------------------------------------
        # 4️⃣ 결과 저장
        # ------------------------------------
        if name:
            ingredient_dict[name] = raw_amount or None

    return ingredient_dict


def load_env_file(env_path: Path) -> None:
    """Populate os.environ from a .env file if present."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if '=' not in stripped:
            continue
        key, value = stripped.split('=', 1)
        key, value = key.strip(), value.strip()
        if value.startswith(('"', "'")) and value.endswith(('"', "'")):
            value = value[1:-1]
        os.environ.setdefault(key, value)


@dataclass
class DatabaseConfig:
    url: str

    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        url = os.getenv('DATABASE_URL') or os.getenv('DB_URL')
        if url:
            return cls(url=url)
        user = os.getenv('DB_USER', 'lgup3')
        password = os.getenv('DB_PASSWORD', 'lgup3P@ssw0rd')
        host = os.getenv('DB_HOST', '211.51.163.232')
        port = os.getenv('DB_PORT', '19306')
        name = os.getenv('DB_NAME', 'lgup3')
        charset = os.getenv('DB_CHARSET', 'utf8mb4')
        password_quoted = quote_plus(password)
        return cls(url=f'mysql+pymysql://{user}:{password_quoted}@{host}:{port}/{name}?charset={charset}')


def create_db_engine(config: DatabaseConfig) -> Engine:
    return create_engine(config.url, future=True, pool_pre_ping=True)


def ensure_sql_identifier(name: str) -> str:
    if not IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def load_state(path: Path) -> Dict[str, int]:
    if not path.exists():
        return {'last_processed_recipe_id': 0}
    try:
        data = json.loads(path.read_text(encoding='utf-8') or '{}')
    except json.JSONDecodeError:
        logging.warning('State file is corrupt, resetting state: %s', path)
        return {'last_processed_recipe_id': 0}
    state = {'last_processed_recipe_id': 0}
    state.update({k: int(v) for k, v in data.items() if k == 'last_processed_recipe_id'})
    return state


def save_state(path: Path, state: Dict[str, int]) -> None:
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')


def fetch_recipe_rows(engine: Engine, table: str, last_id: int, full_refresh: bool) -> pd.DataFrame:
    ensure_sql_identifier(table)
    if full_refresh:
        query = text(f'SELECT recipe_id, ingredient_full FROM {table} ORDER BY recipe_id')
        return pd.read_sql_query(query, engine)
    query = text(f'SELECT recipe_id, ingredient_full FROM {table} WHERE recipe_id > :last_id ORDER BY recipe_id')
    return pd.read_sql_query(query, engine, params={'last_id': last_id})


def parse_ingredient_payload(payload) -> Dict[str, Optional[str]]:
    if payload is None or (isinstance(payload, float) and pd.isna(payload)):
        return {}
    if isinstance(payload, dict):
        return {str(k).strip(): _coerce_amount(v) for k, v in payload.items() if str(k).strip()}
    if isinstance(payload, list):
        merged: Dict[str, Optional[str]] = {}
        for item in payload:
            if isinstance(item, dict):
                merged.update(parse_ingredient_payload(item))
        return merged
    if isinstance(payload, str):
        stripped = payload.strip()
        if not stripped:
            return {}
        for loader in (json.loads, ast.literal_eval):
            try:
                parsed = loader(stripped)
                return parse_ingredient_payload(parsed)
            except Exception:
                continue
        logging.warning('Failed to parse ingredient payload: %s', stripped[:80])
        return {}
    logging.warning('Unsupported payload type %s', type(payload).__name__)
    return {}


def _coerce_amount(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value)


def apply_etl(raw: Dict[str, Optional[str]], etl: 'IngredientETL') -> Dict[str, Optional[str]]:
    cleaned: Dict[str, Optional[str]] = {}
    for name, amount in raw.items():
        base_name = normalize_common_name(name)
        transformed = etl.unify_name(etl.normalize_meat(etl.remove_description(base_name)))
        transformed = normalize_common_name(transformed)
        cleaned[transformed] = amount
    return cleaned


def should_index(name: str) -> bool:
    return name and not any(keyword in name for keyword in REMOVE_KEYWORDS)


def gather_unique_names(records: Sequence[Tuple[int, Dict[str, Optional[str]]]]) -> Set[str]:
    names: Set[str] = set()
    for _, payload in records:
        for key in payload:
            if should_index(key):
                names.add(key)
    return names


def update_recipe_table(engine: Engine, table: str, records: Sequence[Tuple[int, Dict[str, Optional[str]]]], dry_run: bool) -> int:
    if not records:
        return 0
    ensure_sql_identifier(table)
    if dry_run:
        return len(records)
    updated = 0
    with engine.begin() as conn:
        stmt = text(f'UPDATE {table} SET ingredient_full = :payload WHERE recipe_id = :recipe_id')
        for recipe_id, payload in records:
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            conn.execute(stmt, {'payload': serialized, 'recipe_id': recipe_id})
            updated += 1
    return updated


def fetch_existing_ingredients(engine: Engine, table: str) -> Set[str]:
    ensure_sql_identifier(table)
    query = text(f'SELECT ingredient_name FROM {table}')
    df = pd.read_sql_query(query, engine)
    return set(df['ingredient_name'].dropna().astype(str))


def insert_new_ingredients(engine: Engine, table: str, names: Iterable[str], dry_run: bool) -> int:
    names = [name for name in names if name]
    if not names:
        return 0
    ensure_sql_identifier(table)
    if dry_run:
        return len(names)
    with engine.begin() as conn:
        stmt = text(f'INSERT INTO {table} (ingredient_name) VALUES (:name)')
        conn.execute(stmt, [{'name': name} for name in names])
    return len(names)


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level.upper(), format='[%(asctime)s] %(levelname)s - %(message)s')


def run_pipeline(args: argparse.Namespace) -> None:
    configure_logging(args.log_level)
    load_env_file(args.env_file)
    config = DatabaseConfig.from_env()
    engine = create_db_engine(config)

    state = load_state(args.state_file)
    last_id = 0 if args.full_refresh else state.get('last_processed_recipe_id', 0)

    logging.info('Fetching recipes from %s (full_refresh=%s, last_id=%s)', args.recipe_table, args.full_refresh, last_id)
    df = fetch_recipe_rows(engine, args.recipe_table, last_id, args.full_refresh)
    if df.empty:
        logging.info('No new recipes to process. Exiting.')
        return

    etl = IngredientETL()
    records: List[Tuple[int, Dict[str, Optional[str]]]] = []
    for row in df.itertuples(index=False):
        raw_payload = parse_ingredient_payload(row.ingredient_full)
        cleaned_payload = apply_etl(raw_payload, etl)
        records.append((row.recipe_id, cleaned_payload))

    updated_count = update_recipe_table(engine, args.recipe_table, records, args.dry_run)
    logging.info('Prepared %s recipe updates%s.', updated_count, ' (dry run)' if args.dry_run else '')

    unique_names = gather_unique_names(records)
    existing_names = fetch_existing_ingredients(engine, args.ingredient_table)
    to_insert = sorted(unique_names - existing_names)
    inserted_count = insert_new_ingredients(engine, args.ingredient_table, to_insert, args.dry_run)
    logging.info('Prepared %s ingredient inserts%s.', inserted_count, ' (dry run)' if args.dry_run else '')

    if args.dry_run:
        logging.info('Dry run mode enabled. No state persisted.')
        return

    new_last_id = int(df['recipe_id'].max())
    save_state(args.state_file, {'last_processed_recipe_id': new_last_id})
    logging.info('State updated. last_processed_recipe_id=%s', new_last_id)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Clean recipe ingredients and sync ingredient master.')
    parser.add_argument('--recipe-table', default=os.getenv('RECIPE_TABLE', 'recipe_backup'), help='Source table with recipe data')
    parser.add_argument('--ingredient-table', default=os.getenv('INGREDIENT_TABLE', 'ingredient'), help='Ingredient master table name')
    parser.add_argument('--state-file', type=Path, default=STATE_FILE_DEFAULT, help='Path to the incremental state file')
    parser.add_argument('--env-file', type=Path, default=PROJECT_ROOT / '.env', help='Path to .env with DB credentials')
    parser.add_argument('--full-refresh', action='store_true', help='Process all recipes regardless of state')
    parser.add_argument('--dry-run', action='store_true', help='Run without writing to the database or state file')
    parser.add_argument('--log-level', default='INFO', help='Logging level (DEBUG, INFO, etc.)')
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        run_pipeline(args)
    except SQLAlchemyError as exc:
        logging.error('Database error: %s', exc)
        raise


if __name__ == '__main__':
    main()
