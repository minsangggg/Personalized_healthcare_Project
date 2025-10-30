from pydantic import BaseModel
from datetime import date
from typing import List

# 공통
class DBTestResponse(BaseModel):
    db_time: str

class DistItem(BaseModel):
    label: str
    count: int
    ratio: float

class DistributionResponse(BaseModel):
    user_id: str
    period_start: date
    period_end: date
    total: int
    items: List[DistItem]

# progress
class TimePoint(BaseModel):
    date: date
    count: int

class WeekPoint(BaseModel):
    week_start: date
    count: int
    attainment: float

class ProgressResponse(BaseModel):
    user_id: str
    target_per_week: int
    period_start: date
    period_end: date
    total_cooks: int
    goal_attainment: float
    timeseries: List[TimePoint]
    weekly: List[WeekPoint]

# segments
class SegmentWeek(BaseModel):
    week_start: date
    count: int
    attainment: float

class SegmentResponse(BaseModel):
    user_id: str
    goal: int
    segment_label: str
    weekly: List[SegmentWeek]

# routine
class HourCount(BaseModel):
    hour: int
    count: int

class WeekdayCount(BaseModel):
    weekday: int  # 1=월 ... 7=일
    count: int

class RoutineResponse(BaseModel):
    user_id: str
    period_start: date
    period_end: date
    by_hour: List[HourCount]
    by_weekday: List[WeekdayCount]
    best_notify_hour: int | None
    best_notify_weekdays: List[int]

# usage diff/time
class TimeBinItem(BaseModel):
    label: str
    count: int
    ratio: float

class UsageDiffTimeResponse(BaseModel):
    user_id: str
    period_start: date
    period_end: date
    level_dist: List[DistItem]
    time_bins: List[TimeBinItem]
    avg_cooking_time: float

# repeat/variety
class TopRepeatItem(BaseModel):
    recipe_id: int
    recipe_nm_ko: str
    count: int

class RepeatVarietyResponse(BaseModel):
    user_id: str
    period_start: date
    period_end: date
    total: int
    unique_recipes: int
    repeat_rate: float
    new_ratio: float
    top_repeats: List[TopRepeatItem]

# ingredients (보류용 스텁)
class IngredientsStatsResponse(BaseModel):
    message: str

# write APIs
class SetGoalRequest(BaseModel):
    user_id: str
    goal: int

class SetGoalResponse(BaseModel):
    user_id: str
    goal: int

class SelectRecipeRequest(BaseModel):
    user_id: str
    recipe_id: int
    selected_date: date | None = None

class SelectRecipeResponse(BaseModel):
    user_id: str
    recipe_id: int
    selected_date: date