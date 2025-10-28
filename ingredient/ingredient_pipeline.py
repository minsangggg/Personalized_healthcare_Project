"""
Ingredient Pipeline - Data Insertion Module

재료명을 정제하여 ingredient 테이블에 INSERT하는 통합 파이프라인
"""

import pandas as pd
from sqlalchemy import create_engine
from typing import List, Set
import logging
from ingredient_etl import IngredientETL

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IngredientPipeline:
    """재료명 정제 및 DB 적재 파이프라인"""
    
    def __init__(self, db_connection_string: str = None):
        """
        Args:
            db_connection_string: 데이터베이스 연결 문자열
                                  예: 'mysql+pymysql://user:pass%40word@host:port/dbname'
        """
        self.etl = IngredientETL()
        
        if db_connection_string:
            self.engine = create_engine(db_connection_string)
        else:
            # 기본 연결 문자열 (config.py에서 가져옴)
            try:
                from config import DB_CONNECTION_STRING
                self.engine = create_engine(DB_CONNECTION_STRING)
            except ImportError:
                # Fallback
                self.engine = create_engine(
                    'mysql+pymysql://lgup3:lgup3P%40ssw0rd@211.51.163.232:19306/lgup3'
                )
    
    def extract_ingredients_from_recipe_dict(self, ingredient_dict: dict) -> List[str]:
        """
        레시피의 ingredient_full (딕셔너리 형태)에서 재료명만 추출
        
        Args:
            ingredient_dict: {'재료명': '용량', ...} 형태의 딕셔너리
            
        Returns:
            재료명 리스트
        """
        return list(ingredient_dict.keys()) if ingredient_dict else []
    
    def transform(self, ingredients: List[str]) -> Set[str]:
        """
        재료명 정제 (ETL의 Transform 단계)
        
        Args:
            ingredients: 원본 재료명 리스트
            
        Returns:
            정제된 재료명 Set
        """
        return self.etl.process_ingredients_to_set(ingredients)
    
    def load(self, ingredients: Set[str], table_name: str = 'ingredient'):
        """
        정제된 재료명을 ingredient 테이블에 INSERT
        
        Args:
            ingredients: 정제된 재료명 Set
            table_name: 테이블명 (기본값: 'ingredient')
        """
        if not ingredients:
            logger.warning("No ingredients to insert")
            return
        
        # DataFrame 생성
        df = pd.DataFrame({'ingredient_name': list(ingredients)})
        
        # 기존 테이블 읽기
        try:
            existing_df = pd.read_sql(f"SELECT ingredient_name FROM {table_name}", self.engine)
            existing_set = set(existing_df['ingredient_name'].tolist())
            
            # 새로운 재료만 필터링
            new_ingredients = ingredients - existing_set
            if not new_ingredients:
                logger.info("All ingredients already exist in database")
                return
            
            df_new = pd.DataFrame({'ingredient_name': list(new_ingredients)})
            
        except Exception as e:
            # 테이블이 없거나 조회 실패 시 전체 삽입
            logger.warning(f"Could not read existing table: {e}")
            df_new = df
        
        # INSERT
        df_new.to_sql(
            table_name,
            con=self.engine,
            if_exists='append',
            index=False
        )
        
        logger.info(f"Inserted {len(df_new)} new ingredients into {table_name}")
    
    def process_user_input(self, ingredients: List[str]):
        """
        사용자가 직접 입력한 재료명 처리
        
        Args:
            ingredients: 사용자 입력 재료명 리스트
        """
        logger.info("Processing user input ingredients...")
        
        # Transform
        cleaned_ingredients = self.transform(ingredients)
        
        logger.info(f"Cleaned {len(ingredients)} ingredients -> {len(cleaned_ingredients)} unique ingredients")
        
        # Load
        if cleaned_ingredients:
            self.load(cleaned_ingredients)
        else:
            logger.warning("No valid ingredients after cleaning")
    
    def process_recipe(self, ingredient_full: dict):
        """
        Recipe DB에서 새로운 레시피를 처리
        
        Args:
            ingredient_full: 레시피의 ingredient_full 딕셔너리
        """
        logger.info("Processing new recipe ingredients...")
        
        # Extract
        ingredients = self.extract_ingredients_from_recipe_dict(ingredient_full)
        
        # Transform & Load
        self.process_user_input(ingredients)
    
    def process_csv(self, csv_path: str, ingredient_column: str = 'IRDNT_NM'):
        """
        CSV 파일에서 재료명을 추출하여 처리
        
        Args:
            csv_path: CSV 파일 경로
            ingredient_column: 재료명이 있는 컬럼명
        """
        logger.info(f"Processing ingredients from CSV: {csv_path}")
        
        # CSV 읽기
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # 재료명 추출
        ingredients = df[ingredient_column].dropna().unique().tolist()
        
        logger.info(f"Extracted {len(ingredients)} unique ingredients from CSV")
        
        # Transform & Load
        self.process_user_input(ingredients)
    
    def process_recipe_csv(self, recipe_csv_path: str):
        """
        Recipe CSV에서 ingredient_full 컬럼을 파싱하여 재료 처리
        
        Args:
            recipe_csv_path: Recipe CSV 파일 경로
        """
        import ast
        logger.info(f"Processing recipe CSV: {recipe_csv_path}")
        
        # CSV 읽기
        df = pd.read_csv(recipe_csv_path, encoding='utf-8-sig')
        
        all_ingredients = []
        
        # ingredient_full 컬럼에서 재료명 추출
        for idx, row in df.iterrows():
            ingredient_full = row.get('INGREDIENT_FULL', '{}')
            
            try:
                # 문자열을 딕셔너리로 변환
                if isinstance(ingredient_full, str):
                    ingredient_dict = ast.literal_eval(ingredient_full)
                else:
                    ingredient_dict = ingredient_full
                
                # 재료명만 추출
                ingredients = list(ingredient_dict.keys())
                all_ingredients.extend(ingredients)
                
            except Exception as e:
                logger.warning(f"Error processing row {idx}: {e}")
                continue
        
        # 중복 제거
        unique_ingredients = list(set(all_ingredients))
        
        logger.info(f"Extracted {len(unique_ingredients)} unique ingredients from recipes")
        
        # Transform & Load
        self.process_user_input(unique_ingredients)


def main():
    """예제 실행 코드"""
    pipeline = IngredientPipeline()
    
    # 테스트: 사용자 입력 처리
    print("\n" + "=" * 60)
    print("Test 1: User Input Processing")
    print("=" * 60)
    user_ingredients = [
        "소고기_양지 300g",
        "계란 3개",
        "빨강 파프리카 1개",
        "소금",
        "간장 1큰술"
    ]
    pipeline.process_user_input(user_ingredients)
    
    # 테스트: Recipe 딕셔너리 처리
    print("\n" + "=" * 60)
    print("Test 2: Recipe Dictionary Processing")
    print("=" * 60)
    recipe_ingredients = {
        '쌀': '2컵',
        '돼지고기': '200g',
        '표고버섯': '3개',
        '소금': '1큰술',
        '간장': '2큰술'
    }
    pipeline.process_recipe(recipe_ingredients)
    
    # CSV 파일 처리 (옵션)
    # print("\n" + "=" * 60)
    # print("Test 3: CSV Processing")
    # print("=" * 60)
    # pipeline.process_csv('path/to/ingredient.csv', 'INGREDIENT_NAME')


if __name__ == "__main__":
    main()

