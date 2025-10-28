# Ingredient ETL Pipeline

재료명을 정제하여 ingredient 테이블에 적재하는 ETL 파이프라인입니다.

## 📋 개요

이 파이프라인은 다음과 같은 상황에서 사용됩니다:

1. **사용자가 직접 입력한 재료명** 처리
2. **Recipe DB에 새로운 레시피가 추가**되었을 때 재료명 처리

## 🔄 처리 과정

```
입력 데이터 (재료명)
    ↓
1. 양념류 제거 (소금, 간장, 후추, 기름 등)
    ↓
2. 고기류 표준화 (소고기_양지, 돼지고기_다짐육 등)
    ↓
3. 상세 설명 제거 (계란 흰자 → 계란, 빨강 파프리카 → 파프리카)
    ↓
최종 INSERT → ingredient 테이블
```

## 📁 파일 구조

```
ingredient/
├── ingredient_etl.py          # 정제 로직 (ETL 클래스)
├── ingredient_pipeline.py    # DB 연결 및 INSERT 로직
├── example_usage.py         # 사용 예제
└── README_ingredient_etl.md  # 이 문서
```

## 🎯 재료 네이밍 규칙

### 1. 양념류 제거
다음 항목은 필터링됩니다:
- 소금, 후추, 설탕, 간장, 고추장, 된장
- 참기름, 식용유, 들기름
- 양념장, 양념
- 고춧가루, 고추가루
- 국간장, 진간장
- 맛술, 액젓
- 다진파, 다진마늘, 다진생강
- 물, 육수, 국물

### 2. 고기류 표준화
**형식:** `고기종류_용도`

**소고기:**
- `소고기_양지` (양지머리, 양지)
- `소고기_국거리` (국거리용)
- `소고기_다짐육` (소고기 다짐육)
- `소고기_안심`
- `소고기_등심`
- `소고기_불고기`
- `소고기_갈비`

**돼지고기:**
- `돼지고기_다짐육` (다짐육)
- `돼지고기_삼겹살`
- `돼지고기_목살`
- `돼지고기_안심`
- `돼지고기_갈비`
- `돼지고기_등심`

**닭고기:**
- `닭고기_가슴살` (닭가슴살)
- `닭고기_다리`
- `닭고기_날개`
- `닭고기_안심`

### 3. 상세 설명 제거

| 원본 | 정제 후 |
|------|---------|
| 계란 흰자 | 계란 |
| 계란 노른자 | 계란 |
| 달걀 | 계란 |
| 빨강 파프리카 | 파프리카 |
| 노랑 파프리카 | 파프리카 |
| 청 피망 | 피망 |
| 홍 피망 | 피망 |
| 멥쌀 | 쌀 |
| 찹쌀 | 쌀 |

## 🚀 사용 방법

### 1. 기본 사용

```python
from ingredient_pipeline import IngredientPipeline

# 파이프라인 초기화
pipeline = IngredientPipeline()

# 사용자 입력 처리
ingredients = ["소고기_양지 300g", "계란 3개", "빨강 파프리카 1개"]
pipeline.process_user_input(ingredients)
```

### 2. Recipe 딕셔너리 처리

```python
# Recipe에서 ingredient_full 딕셔너리
recipe_ingredients = {
    '쌀': '2컵',
    '양지': '300g',
    '무': '1/4개',
    '콩나물': '1줌'
}

pipeline.process_recipe(recipe_ingredients)
```

### 3. CSV 파일 처리

```python
# 재료명만 있는 CSV
pipeline.process_csv('ingredient.csv', 'INGREDIENT_NAME')

# Recipe CSV에서 ingredient_full 컬럼 처리
pipeline.process_recipe_csv('recipe_info.csv')
```

### 4. 대량 처리

```python
# 여러 레시피 일괄 처리
recipes = [
    {'쌀': '2컵', '양지': '300g', '무': '1/4개'},
    {'돼지고기': '200g', '표고버섯': '3개'},
    {'계란': '3개', '대파': '1대'}
]

for recipe in recipes:
    pipeline.process_recipe(recipe)
```

## 📊 데이터베이스 구조

### ingredient 테이블
```sql
CREATE TABLE ingredient (
    ingredient_name VARCHAR(255) PRIMARY KEY
);
```

## 🛠️ 설정

### 데이터베이스 연결
`ingredient_pipeline.py`에서 데이터베이스 연결 문자열을 수정하세요:

```python
pipeline = IngredientPipeline(
    db_connection_string='mysql+pymysql://user:pass%40word@host:port/dbname'
)
```

### 로깅 설정
로깅 레벨을 조정할 수 있습니다:

```python
import logging
logging.basicConfig(level=logging.DEBUG)  # DEBUG, INFO, WARNING, ERROR
```

## 📝 예제 실행

```bash
# ETL 테스트
python ingredient_etl.py

# 파이프라인 테스트
python ingredient_pipeline.py

# 사용 예제
python example_usage.py
```

## 🔍 처리 결과 예시

### 입력
```python
[
    "소고기_양지 300g",
    "계란 흰자 2개",
    "빨강 파프리카 1개",
    "청 피망 1개",
    "소금 1큰술",         # ← 필터링
    "간장 1큰술",         # ← 필터링
    "다진마늘 1T",        # ← 필터링
    "돼지고기 다짐육 200g"
]
```

### 출력 (DB에 INSERT됨)
```
소고기_양지
계란
파프리카
피망
돼지고기_다짐육
```

## 💡 주요 기능

1. **양념류 자동 필터링**: 양념류 키워드를 자동으로 감지하여 제거
2. **고기류 표준화**: 고기명을 `고기종류_용도` 형식으로 통일
3. **상세 설명 제거**: 색상, 부분 등 상세 설명을 제거하여 핵심 재료명만 추출
4. **중복 제거**: Set을 사용하여 자동 중복 제거
5. **기존 데이터 보존**: 이미 존재하는 재료는 다시 INSERT하지 않음

## ⚠️ 주의사항

1. **DB 연결 정보**: 프로덕션 환경에서는 환경변수나 설정 파일 사용 권장
2. **데이터 검증**: 잘못된 재료명이 입력될 경우를 대비해 검증 로직 추가 권장
3. **대량 처리**: 대량 데이터 처리 시 트랜잭션 관리 고려
4. **에러 핸들링**: 네트워크 오류, DB 오류 등에 대한 예외 처리 필요

## 🔧 커스터마이징

### 양념류 키워드 추가
`ingredient_etl.py`의 `__init__` 메서드에서 `self.seasoning_keywords`에 추가:

```python
self.seasoning_keywords = [
    '소금', '후추', ...,
    '새로운양념'  # 추가
]
```

### 고기류 패턴 추가
`self.meat_patterns`에 새로운 패턴 추가:

```python
r'새로운패턴': '표준명',
```

### 상세 설명 패턴 추가
`self.description_patterns`에 새로운 패턴 추가:

```python
(r'패턴정규식', '치환할값'),
```

