import re
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os

# ---------------------------------
# 1️⃣ 저장 경로
# ---------------------------------
save_recipe_fname = './data/recipe_by_type.csv'
progress_file = './data/progress.json'
os.makedirs(os.path.dirname(save_recipe_fname), exist_ok=True)

# ---------------------------------
# 2️⃣ 종류별 카테고리 설정
# ---------------------------------
by_type = {
    '밑반찬': '63', '메인반찬': '56', '국/탕': '54', '찌개': '55',
    '디저트': '60', '면/만두': '53', '밥/죽/떡': '52', '퓨전': '61',
    '양식': '65', '샐러드': '64', '빵': '66', '기타': '62'
}

max_pages_per_category = 50  # ✅ 카테고리당 최대 페이지 제한

# ---------------------------------
# 3️⃣ 진행 상태 복원
# ---------------------------------
start_category = None
start_page = 1

if os.path.exists(progress_file):
    with open(progress_file, 'r', encoding='utf-8') as f:
        progress = json.load(f)
        start_category = progress.get('category')
        start_page = progress.get('page', 1)
        print(f"🔁 진행 복원: {start_category} → {start_page}페이지부터 재시작")
else:
    print("🚀 새 크롤링 시작")

# ---------------------------------
# 4️⃣ 유틸 함수 - step_text 정제
# ---------------------------------
def clean_step_text(step_list):
    """자음/모음만 있는 문장 제거 + ㅎㅎ, ㅋ, ㅠㅠ, ㅜㅜ 제거"""
    cleaned = []
    for step in step_list:
        if re.match(r'^[ㄱ-ㅎㅏ-ㅣ]+$', step.strip()):
            continue
        step = re.sub(r'[ㅋㅎㅠㅜ]+', '', step).strip()
        if step:
            cleaned.append(step)
    return cleaned

# ---------------------------------
# 5️⃣ 크롤링 시작
# ---------------------------------
recipe_idx = 1
list4df = []
visited_urls = set()
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# ✅ 기존 CSV 불러와 중복 방지
if os.path.exists(save_recipe_fname):
    old_df = pd.read_csv(save_recipe_fname)
    print(f"✅ 기존 데이터 {len(old_df)}개 불러옴 (중복 방지)")

try:
    start_flag = start_category is None
    for type_key, type_value in by_type.items():
        if not start_flag:
            if type_key == start_category:
                start_flag = True
            else:
                continue

        main_url = f"https://www.10000recipe.com/recipe/list.html?cat4={type_value}&order=reco"
        page = start_page

        while True:
            if page > max_pages_per_category:
                print(f"⚡ {type_key} 카테고리 {max_pages_per_category}페이지까지 완료, 다음으로 이동")
                break

            print(f"🔍 {type_key} → {page}페이지 처리 중...")

            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump({'category': type_key, 'page': page}, f, ensure_ascii=False, indent=2)

            try:
                response = session.get(f"{main_url}&page={page}", timeout=8)
                if response.status_code != 200:
                    print(f"⚠️ 페이지 요청 실패 ({response.status_code}) - {type_key} {page}p")
                    break
            except Exception as e:
                print(f"⚠️ 페이지 요청 오류: {e}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            sources = soup.select('#contents_area_full > ul > ul > li > div.common_sp_thumb > a')

            if not sources:
                print(f"✅ {type_key} 카테고리 종료 ({page-1}페이지까지)")
                break

            for source in sources:
                recipe_url = 'https://www.10000recipe.com' + str(source).split('href')[1].split('"')[1]

                try:
                    response_r = session.get(recipe_url, timeout=8)
                    if response_r.status_code != 200:
                        continue
                    soup_r = BeautifulSoup(response_r.text, 'html.parser')
                except Exception:
                    continue

                try:
                    # 제목
                    title_tag = soup_r.select_one('div.view2_summary h3, h3.recipe_title, h3')
                    title = title_tag.text.strip() if title_tag else None

                    # ✅ 조회수 필터링만 적용
                    views_tag = soup_r.select_one("div.view_cate_num > span.hit.font_num")
                    views = views_tag.text.strip().replace(",", "") if views_tag else None
                    if not views or not views.isdigit() or int(views) < 100000:
                        continue  # 🔥 10만 미만 조회수는 제외

                    # 인분 / 조리시간 / 난이도
                    info_tags = soup_r.select('span.view2_summary_info1, span.view2_summary_info2, span.view2_summary_info3')
                    servings = re.sub(r'[^0-9]', '', info_tags[0].text) if len(info_tags) > 0 else None
                    cooking_time = re.sub(r'[^0-9]', '', info_tags[1].text) if len(info_tags) > 1 else None
                    difficulty = info_tags[2].text.strip() if len(info_tags) > 2 else None

                    # 재료
                    ingredients = [
                        f"{li.select_one('.ingre_list_name').text.strip()} {li.select_one('.ingre_list_ea').text.strip()}"
                        for li in soup_r.select("#divConfirmedMaterialArea li") if li.select_one(".ingre_list_name")
                    ]

                    # 조리순서 (정제 + 번호 부여)
                    cooking_order = clean_step_text([step.text.strip() for step in soup_r.select('div.view_step_cont')])
                    cooking_order = [f"{i+1}. {text}" for i, text in enumerate(cooking_order)]

                    # 해시태그
                    hashtags = [a.text.strip().replace("#", "") for a in soup_r.select("div.view_tag a")]

                    # 관련상품명
                    related_tag = soup_r.select_one("div#relationGoods div.best_tit b")
                    related_title = related_tag.text.strip() if related_tag else None

                    # ✅ 변경된 컬럼 순서/이름으로 저장
                    list4df.append([
                        recipe_idx, related_title, servings, type_key, cooking_time,
                        difficulty, ingredients, cooking_order, hashtags
                    ])
                    print(f"✅ [{recipe_idx}] {title}")
                    recipe_idx += 1

                except Exception:
                    continue

            page += 1
            time.sleep(0.5)

        start_page = 1

except KeyboardInterrupt:
    print("\n🟡 수동 중단됨 — progress.json에 마지막 상태 저장 완료.")
except Exception as e:
    print(f"❌ 전체 오류: {e}")

# ---------------------------------
# 6️⃣ CSV 저장 (컬럼명/순서 변경 적용)
# ---------------------------------
recipe_df = pd.DataFrame(list4df, columns=[
    'recipe_id', 'recipe_nm_ko', 'servings', 'ty_nm', 'cooking_time',
    'level_nm', 'ingredient_full', 'step_text', 'tag'
])

if os.path.exists(save_recipe_fname):
    old_df = pd.read_csv(save_recipe_fname)
    recipe_df = pd.concat([old_df, recipe_df], ignore_index=True).drop_duplicates(subset=['recipe_id'])

recipe_df.to_csv(save_recipe_fname, encoding='utf-8-sig', index=False)
print(f"\n💾 CSV 누적 저장 완료 → {save_recipe_fname}")
print("⚡ 크롤링 완료 (컬럼 순서/이름 변경 + step 번호 부여 + 감탄사 제거 + resume + 중복 방지)")
