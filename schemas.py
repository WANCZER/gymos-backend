from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import date, datetime

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


# --- User Schemas ---
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[str] = None
    experience_level: Optional[str] = None
    primary_goal: Optional[str] = None
    duration_preference: Optional[int] = None
    available_equipment: Optional[str] = None
    injuries: Optional[str] = None
    diet_preference: Optional[str] = None
    diet_budget: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[str] = None
    experience_level: Optional[str] = None
    primary_goal: Optional[str] = None
    duration_preference: int
    available_equipment: str
    injuries: str
    diet_preference: str
    diet_budget: str
    streak: int
    
    class Config:
        from_attributes = True


# --- Workout Split Schemas ---
class WorkoutSplitDay(BaseModel):
    day_of_week: str
    muscle_groups: str

class WorkoutSplitCreate(BaseModel):
    splits: List[WorkoutSplitDay]

class WorkoutSplitOut(BaseModel):
    id: int
    user_id: int
    day_of_week: str
    muscle_groups: str

    class Config:
        from_attributes = True


# --- Exercise Schemas ---
class ExerciseOut(BaseModel):
    id: int
    name: str
    target_muscle: str
    secondary_muscles: Optional[str] = None
    equipment: str
    difficulty: str
    instructions: Optional[str] = None
    mistakes: Optional[str] = None
    alternatives: Optional[str] = None
    variations: Optional[str] = None
    rep_range: str

    class Config:
        from_attributes = True


# --- Set Log Schema ---
class SetLog(BaseModel):
    set_number: int = Field(alias="set")
    weight: float
    reps: int

    class Config:
        populate_by_name = True


# --- Exercise Log Schemas ---
class ExerciseLogCreate(BaseModel):
    exercise_id: Optional[int] = None
    exercise_name: str
    sets_data: List[SetLog]

class ExerciseLogOut(BaseModel):
    id: int
    exercise_id: Optional[int] = None
    exercise_name: str
    sets_data: List[SetLog]

    class Config:
        from_attributes = True


# --- Workout Log Schemas ---
class WorkoutLogCreate(BaseModel):
    workout_name: str
    date: Optional[date] = None
    completed: Optional[bool] = False
    exercise_logs: List[ExerciseLogCreate]

class WorkoutLogOut(BaseModel):
    id: int
    user_id: int
    date: date
    workout_name: str
    completed: bool
    exercise_logs: List[ExerciseLogOut]

    class Config:
        from_attributes = True


# --- Food Item Schemas ---
class FoodItemOut(BaseModel):
    id: int
    name: str
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    fiber_per_100g: float
    cost_per_100g: float
    category: Optional[str] = None
    is_veg: bool

    class Config:
        from_attributes = True


# --- Meal Item Schemas ---
class MealItemCreate(BaseModel):
    food_name: str
    amount: str
    calories: float
    protein: float
    carbs: float
    fat: float
    cost: float

class MealItemOut(BaseModel):
    id: int
    food_name: str
    amount: str
    calories: float
    protein: float
    carbs: float
    fat: float
    cost: float

    class Config:
        from_attributes = True


# --- Meal Schemas ---
class MealCreate(BaseModel):
    name: str
    cost: float
    items: List[MealItemCreate]

class MealOut(BaseModel):
    id: int
    name: str
    cost: float
    items: List[MealItemOut]

    class Config:
        from_attributes = True


# --- Meal Plan Schemas ---
class MealPlanCreate(BaseModel):
    date: Optional[date] = None
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    budget: Optional[float] = None
    meals: List[MealCreate]

class MealPlanOut(BaseModel):
    id: int
    date: date
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    budget: Optional[float] = None
    meals: List[MealOut]

    class Config:
        from_attributes = True


# --- Supplement Schemas ---
class SupplementOut(BaseModel):
    id: int
    name: str
    scientific_evidence: Optional[str] = None
    benefits: Optional[str] = None
    dosage: Optional[str] = None
    safety: Optional[str] = None
    cost_effectiveness: Optional[str] = None
    best_timing: Optional[str] = None

    class Config:
        from_attributes = True


# --- AI Coach Memory Schemas ---
class AICoachMemoryCreate(BaseModel):
    key: str
    value: str

class AICoachMemoryOut(BaseModel):
    id: int
    key: str
    value: str

    class Config:
        from_attributes = True


# --- Progress Metric Schemas ---
class ProgressMetricCreate(BaseModel):
    date: Optional[date] = None
    weight: Optional[float] = None
    body_fat: Optional[float] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    arms: Optional[float] = None
    thighs: Optional[float] = None
    photo_url: Optional[str] = None

class ProgressMetricOut(BaseModel):
    id: int
    user_id: int
    date: date
    weight: Optional[float] = None
    body_fat: Optional[float] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    arms: Optional[float] = None
    thighs: Optional[float] = None
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True


# --- Coach Chat / Research Schemas ---
class ChatRequest(BaseModel):
    message: str
    context_workout_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    actions: Optional[List[str]] = None # e.g. ["modify_workout", "suggest_meal"]

class ResearchRequest(BaseModel):
    query: str

class ResearchResponse(BaseModel):
    query: str
    summary: str
    evidence_level: str
    myths_detected: List[str]
    references: List[str]
