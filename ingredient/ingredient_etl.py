"""
Ingredient ETL Pipeline

재료명을 정제하여 ingredient 테이블에 적재하는 ETL 파이프라인
1. 양념류 제거
2. 고기류 표준화
3. 상세 설명 제거
"""

import re
from typing import List, Set
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IngredientETL:
    """재료명 정제를 위한 ETL 클래스"""
    
    def __init__(self):
        # 양념류 키워드 (제거 대상)
        self.seasoning_keywords = [
            '소금', '후추', '설탕', '간장', '고추장', '된장', '청국장', '고춧가루', '고추가루',
            '참기름', '들기름', '식용유', '양념장', '양념', '국간장', '진간장', '맛술', '액젓',
            '멸치액젓', '물엿', '올리고당', '초고추장', '새우젓', '젓국', '젓갈', '액젓',
            '깨소금', '후춧가루', '통후추', '굵은소금', '꽃소금', '맛소금', '고운소금',
            '고춧기름', '참기름', '들깨가루', '고춧가루', '고춧가루가루', '들깨',
            '케첩', '토마토케첩', '토마토케찹', '와사비', '머스타드', '마요네즈',
            '굴소스', '토마토페이스트', '토마토페스트', '페스토소스',
            '다진파', '다진마늘', '다진생강', '다진', '갈은',
            '국물', '육수', '멸치육수', '다시마육수', '닭육수', '사골육수',
            '물', '뜨거운물', '찬물', '얼음물', '생수'
        ]
        
        # 고기류 정규화 매핑
        self.meat_patterns = {
            # 소고기
            r'소고기.*양지|양지머리|소고기양지|양지\s*먹히': '소고기_양지',
            r'소고기.*국거리|국거리용.*소고기|소고기.*국거리용': '소고기_국거리',
            r'소고기.*다짐육|소고기.*다짐|다짐육.*소고기|다짐육\(소고기\)': '소고기_다짐육',
            r'소고기.*안심|안심.*소고기': '소고기_안심',
            r'소고기.*등심|등심.*소고기': '소고기_등심',
            r'소고기.*불고기|불고기용.*소고기': '소고기_불고기',
            r'소고기.*갈비|갈비용.*소고기': '소고기_갈비',
            r'쇠고기.*양지|쇠고기.*안심|쇠고기.*등심|쇠고기.*갈비': '소고기_양지',  # 쇠고기를 소고기로 통일
            
            # 돼지고기
            r'돼지고기.*다짐육|돼지고기.*다짐|다짐육.*돼지|다짐육\(돼지고기\)': '돼지고기_다짐육',
            r'돼지고기.*삼겹살|삼겹살.*돼지': '돼지고기_삼겹살',
            r'돼지고기.*목살|목살.*돼지': '돼지고기_목살',
            r'돼지고기.*안심|안심.*돼지': '돼지고기_안심',
            r'돼지고기.*갈비|돼지갈비|갈비.*돼지': '돼지고기_갈비',
            r'돼지고기.*등심|등심.*돼지': '돼지고기_등심',
            r'돼지고기.*앞다리|앞다리.*돼지': '돼지고기_앞다리',
            r'대패.*돼지|대패돼지고기': '돼지고기_대패',
            
            # 닭고기
            r'닭.*가슴살|닭가슴살|가슴살.*닭': '닭고기_가슴살',
            r'닭.*다리|닭다리살|닭.*허벅지': '닭고기_다리',
            r'닭.*날개|닭날개': '닭고기_날개',
            r'닭.*안심|닭안심': '닭고기_안심',
            r'닭.*볶음탕용|볶음탕용.*닭': '닭고기_볶음탕',
            
            # 기타
            r'오리훈제': '오리_훈제',
            r'훈제오리': '오리_훈제',
            r'베이컨': '베이컨',
        }
        
        # 상세 설명 제거 패턴
        self.description_patterns = [
            # 계란 관련
            (r'계란.*흰자|계란흰자|달걀.*흰자|흰자', '계란'),
            (r'계란.*노른자|계란노른자|달걀.*노른자', '계란'),
            (r'달걀|계란', '계란'),  # 달걀을 계란으로 통일
            
            # 파프리카/피망 관련
            (r'빨강.*파프리카|빨강파프리카|빨간.*파프리카', '파프리카'),
            (r'노랑.*파프리카|노랑파프리카|노란.*파프리카', '파프리카'),
            (r'적.*파프리카|적파프리카', '파프리카'),
            (r'황.*파프리카|황파프리카', '파프리카'),
            (r'청.*피망|청피망', '피망'),
            (r'홍.*피망|홍피망', '피망'),
            (r'녹색.*피망|녹색피망', '피망'),
            (r'빨강.*피망|빨강피망', '피망'),
            (r'노랑.*피망|노랑피망', '피망'),
            
            # 기타 상세 설명 제거
            (r'소.*잡뼈|잡뼈|뼈', ''),
            (r'멥쌀', '쌀'),
            (r'찹쌀', '쌀'),
            
            # 불필요한 설명 제거
            (r'다진', ''),
            (r'썬', ''),
            (r'깐', ''),
            (r'갈은', ''),
            (r'가루', ''),
            (r'곱게', ''),
            (r'굵게', ''),
            (r'가늘게', ''),
            (r'큼직하게', ''),
            (r'먹기.*좋게', ''),
            (r'한입.*크기', ''),
            
            # 용량/처리상태 제거
            (r'\([^)]*\)', ''),  # 괄호 안의 내용 제거
            (r'\[[^\]]*\]', ''),  # 대괄호 안의 내용 제거
        ]
    
    def is_seasoning(self, ingredient: str) -> bool:
        """
        양념류인지 확인
        
        Args:
            ingredient: 재료명
            
        Returns:
            True if seasoning, False otherwise
        """
        ingredient_lower = ingredient.lower()
        
        for keyword in self.seasoning_keywords:
            if keyword in ingredient:
                return True
        
        return False
    
    def normalize_meat(self, ingredient: str) -> str:
        """
        고기류를 표준화된 형식으로 변환
        
        Args:
            ingredient: 재료명
            
        Returns:
            정규화된 재료명 (고기류가 아니면 원본 반환)
        """
        for pattern, standard in self.meat_patterns.items():
            if re.search(pattern, ingredient, re.IGNORECASE):
                logger.debug(f"Meat normalized: {ingredient} -> {standard}")
                return standard
        
        return ingredient
    
    def remove_description(self, ingredient: str) -> str:
        """
        상세 설명 제거
        
        Args:
            ingredient: 재료명
            
        Returns:
            상세 설명이 제거된 재료명
        """
        result = ingredient
        
        for pattern, replacement in self.description_patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # 연속된 공백 제거
        result = ' '.join(result.split())
        result = result.strip()
        
        return result
    
    def clean_ingredient(self, ingredient: str) -> str:
        """
        재료명을 정제하는 메인 함수
        
        Args:
            ingredient: 원본 재료명
            
        Returns:
            정제된 재료명 (Empty string if should be filtered out)
        """
        if not ingredient or not ingredient.strip():
            return ""
        
        # 1단계: 상세 설명 제거
        cleaned = self.remove_description(ingredient)
        
        if not cleaned:
            return ""
        
        # 2단계: 양념류 제거
        if self.is_seasoning(cleaned):
            logger.debug(f"Filtered out seasoning: {ingredient}")
            return ""
        
        # 3단계: 고기류 표준화
        cleaned = self.normalize_meat(cleaned)
        
        return cleaned
    
    def process_ingredients(self, ingredients: List[str]) -> List[str]:
        """
        여러 재료명을 일괄 처리
        
        Args:
            ingredients: 원본 재료명 리스트
            
        Returns:
            정제된 재료명 리스트 (중복 제거)
        """
        processed = []
        
        for ingredient in ingredients:
            cleaned = self.clean_ingredient(ingredient)
            if cleaned and cleaned not in processed:
                processed.append(cleaned)
        
        return processed
    
    def process_ingredients_to_set(self, ingredients: List[str]) -> Set[str]:
        """
        여러 재료명을 일괄 처리하여 Set으로 반환 (중복 자동 제거)
        
        Args:
            ingredients: 원본 재료명 리스트
            
        Returns:
            정제된 재료명 Set (중복 제거)
        """
        processed = set()
        
        for ingredient in ingredients:
            cleaned = self.clean_ingredient(ingredient)
            if cleaned:
                processed.add(cleaned)
        
        return processed


def main():
    """테스트 및 예제 코드"""
    etl = IngredientETL()
    
    # 테스트 케이스
    test_ingredients = [
        "소고기_양지 300g",
        "돼지고기_다짐육 200g",
        "계란 흰자 3개",
        "빨강 파프리카 1개",
        "청피망 1개",
        "소금",
        "간장 1큰술",
        "다진마늘 1T",
        "닭가슴살 300g",
        "쇠고기_양지 300g",
        "[쇠고기양념] 간장",
        "깐 밤 100g",
        "멥쌀 2컵",
        "소고기 국거리용 200g"
    ]
    
    print("=" * 60)
    print("Ingredient ETL Pipeline Test")
    print("=" * 60)
    
    for ingredient in test_ingredients:
        cleaned = etl.clean_ingredient(ingredient)
        if cleaned:
            print(f"{ingredient:30} -> {cleaned}")
        else:
            print(f"{ingredient:30} -> [필터링됨]")


if __name__ == "__main__":
    main()

