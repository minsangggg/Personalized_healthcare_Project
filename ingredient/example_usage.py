"""
Ingredient Pipeline - Usage Examples

실제 사용 예제 모음
"""

from ingredient_pipeline import IngredientPipeline
import ast

def example_1_user_input():
    """예제 1: 사용자가 직접 입력한 재료 처리"""
    print("\n" + "=" * 60)
    print("Example 1: User Input")
    print("=" * 60)
    
    pipeline = IngredientPipeline()
    
    # 사용자가 입력한 재료 리스트
    user_ingredients = [
        "소고기_양지 300g",
        "계란 흰자 2개",
        "빨강 파프리카 1개",
        "청피망 1개",
        "소금 1큰술",      # 필터링됨
        "간장 1큰술",      # 필터링됨
        "다진마늘 1T",     # 필터링됨
        "돼지고기 다짐육 200g"
    ]
    
    pipeline.process_user_input(user_ingredients)


def example_2_recipe_dict():
    """예제 2: Recipe 딕셔너리 처리"""
    print("\n" + "=" * 60)
    print("Example 2: Recipe Dictionary")
    print("=" * 60)
    
    pipeline = IngredientPipeline()
    
    # 레시피의 ingredient_full (딕셔너리 형태)
    recipe_dict = {
        '쌀': '2컵',
        '양지': '300g',
        '무': '1/4개',
        '콩나물': '1줌',
        '대파': '1대',
        '국간장': '4T',
        '진간장': '1T',
        '참기름': '1T',
        '고추가루': '3T',
        '다진마늘': '1T',
        '소금': '약간',
        '후추': '약간'
    }
    
    pipeline.process_recipe(recipe_dict)


def example_3_recipe_string():
    """예제 3: Recipe 문자열 (CSV에서 읽어온 경우) 처리"""
    print("\n" + "=" * 60)
    print("Example 3: Recipe String from CSV")
    print("=" * 60)
    
    pipeline = IngredientPipeline()
    
    # CSV에서 읽어온 ingredient_full (문자열 형태)
    ingredient_full_str = "{'쌀': '2컵', '안심': '200g', '콩나물': '20g', '청포묵': '50g'}"
    
    # 문자열을 딕셔너리로 변환
    try:
        ingredient_dict = ast.literal_eval(ingredient_full_str)
        pipeline.process_recipe(ingredient_dict)
    except Exception as e:
        print(f"Error parsing recipe: {e}")


def example_4_csv_file():
    """예제 4: CSV 파일에서 재료명 추출"""
    print("\n" + "=" * 60)
    print("Example 4: CSV File Processing")
    print("=" * 60)
    
    pipeline = IngredientPipeline()
    
    # ingredient_keys_filtered.csv 처리
    try:
        pipeline.process_csv('ingredient_keys_filtered.csv', 'INGREDIENT_NAME')
    except FileNotFoundError:
        print("File not found. Make sure ingredient_keys_filtered.csv exists.")


def example_5_recipe_csv():
    """예제 5: Recipe CSV에서 ingredient_full 처리"""
    print("\n" + "=" * 60)
    print("Example 5: Recipe CSV Processing")
    print("=" * 60)
    
    pipeline = IngredientPipeline()
    
    # recipe_info.csv 처리 (INGREDIENT_FULL 컬럼이 있는 경우)
    try:
        pipeline.process_recipe_csv('recipe_info.csv')
    except FileNotFoundError:
        print("File not found. Make sure recipe_info.csv exists.")
    except Exception as e:
        print(f"Error processing recipe CSV: {e}")


def example_6_batch_processing():
    """예제 6: 대량 레시피 일괄 처리"""
    print("\n" + "=" * 60)
    print("Example 6: Batch Recipe Processing")
    print("=" * 60)
    
    pipeline = IngredientPipeline()
    
    # 여러 레시피의 ingredient_full 딕셔너리 리스트
    recipes = [
        {'쌀': '2컵', '양지': '300g', '무': '1/4개'},
        {'돼지고기': '200g', '표고버섯': '3개', '부추': '1줌'},
        {'계란': '3개', '대파': '1대', '소금': '약간'}
    ]
    
    all_ingredients = []
    for recipe in recipes:
        all_ingredients.extend(list(recipe.keys()))
    
    # 중복 제거하여 일괄 처리
    pipeline.process_user_input(all_ingredients)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Ingredient Pipeline - Example Usage")
    print("=" * 60)
    
    # 각 예제 실행 (DB 연결 없이 테스트하려면 주석 처리)
    # example_1_user_input()
    # example_2_recipe_dict()
    # example_3_recipe_string()
    # example_4_csv_file()
    # example_5_recipe_csv()
    # example_6_batch_processing()
    
    print("\nNote: Uncomment examples above to run them.")
    print("Make sure database connection is properly configured.")

