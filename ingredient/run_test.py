"""
Ingredient ETL Pipeline - Test Runner

테스트 실행을 위한 스크립트
"""

from ingredient_etl import IngredientETL
from ingredient_pipeline import IngredientPipeline

def test_etl_cleaning():
    """ETL 정제 로직 테스트"""
    print("\n" + "=" * 60)
    print("Test: ETL Cleaning Logic")
    print("=" * 60)
    
    etl = IngredientETL()
    
    test_cases = [
        # 양념류 제거 테스트
        ("소금 1큰술", ""),
        ("간장 2큰술", ""),
        ("다진마늘 1T", ""),
        ("고춧가루 1큰술", ""),
        ("참기름 1큰술", ""),
        
        # 고기류 표준화 테스트
        ("소고기_양지 300g", "소고기_양지"),
        ("양지머리 300g", "소고기_양지"),
        ("돼지고기_다짐육 200g", "돼지고기_다짐육"),
        ("다짐육(돼지고기) 200g", "돼지고기_다짐육"),
        ("소고기 국거리 200g", "소고기_국거리"),
        ("닭가슴살 300g", "닭고기_가슴살"),
        
        # 상세 설명 제거 테스트
        ("계란 흰자 2개", "계란"),
        ("계란 노른자 1개", "계란"),
        ("달걀 3개", "계란"),
        ("빨강 파프리카 1개", "파프리카"),
        ("노랑 파프리카 1개", "파프리카"),
        ("청 피망 1개", "피망"),
        ("홍 피망 1개", "피망"),
        ("멥쌀 2컵", "쌀"),
        ("찹쌀 1컵", "쌀"),
    ]
    
    print("\nTesting individual ingredient cleaning...\n")
    passed = 0
    failed = 0
    
    for input_ingredient, expected in test_cases:
        result = etl.clean_ingredient(input_ingredient)
        
        # 예상 결과와 비교
        if result == expected:
            print(f"✓ {input_ingredient:35} -> {result}")
            passed += 1
        else:
            print(f"✗ {input_ingredient:35} -> {result:20} (expected: {expected})")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)


def test_pipeline_processing():
    """파이프라인 전체 처리 테스트"""
    print("\n" + "=" * 60)
    print("Test: Pipeline Processing")
    print("=" * 60)
    
    # DB 연결 없이 테스트
    print("\nProcessing sample ingredients (without DB insert)...")
    
    ingredients = [
        "소고기_양지 300g",
        "계란 흰자 2개",
        "빨강 파프리카 1개",
        "청 피망 1개",
        "소금 1큰술",
        "간장 1큰술",
        "다진마늘 1T",
        "돼지고기 다짐육 200g",
        "닭가슴살 300g"
    ]
    
    etl = IngredientETL()
    cleaned = etl.process_ingredients(ingredients)
    
    print("\nInput ingredients:")
    for ing in ingredients:
        print(f"  - {ing}")
    
    print(f"\nCleaned ingredients ({len(cleaned)}):")
    for ing in sorted(cleaned):
        print(f"  - {ing}")
    
    print(f"\nFiltered out: {len(ingredients) - len(cleaned)} items")


def test_recipe_dict():
    """Recipe 딕셔너리 처리 테스트"""
    print("\n" + "=" * 60)
    print("Test: Recipe Dictionary Processing")
    print("=" * 60)
    
    etl = IngredientETL()
    
    recipe = {
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
    
    print("\nOriginal recipe ingredients:")
    for item, amount in recipe.items():
        print(f"  - {item}: {amount}")
    
    ingredients = list(recipe.keys())
    cleaned = etl.process_ingredients_to_set(ingredients)
    
    print(f"\nCleaned ingredients ({len(cleaned)}):")
    for ing in sorted(cleaned):
        print(f"  - {ing}")
    
    print(f"\nFiltered out: {len(ingredients) - len(cleaned)} items")


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("Ingredient ETL Pipeline - Test Suite")
    print("=" * 60)
    
    try:
        test_etl_cleaning()
        test_pipeline_processing()
        test_recipe_dict()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

