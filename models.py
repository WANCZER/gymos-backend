from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=True)
    
    # Profile information
    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)  # in cm
    weight = Column(Float, nullable=True)  # in kg
    gender = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)  # beginner, intermediate, advanced
    primary_goal = Column(String, nullable=True)      # Muscle Gain, Fat Loss, Recomposition, Strength, Endurance
    duration_preference = Column(Integer, default=60) # in minutes
    
    # JSON strings or serialized lists
    available_equipment = Column(String, default="Bodyweight only") # comma-separated list
    injuries = Column(String, default="None")                       # comma-separated list
    diet_preference = Column(String, default="Non-vegetarian")     # Vegetarian, Vegan, Non-vegetarian
    diet_budget = Column(String, default="Medium")                 # Low, Medium, High
    
    # Consistency & Tracking
    streak = Column(Integer, default=0)
    streak_updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    splits = relationship("WorkoutSplit", back_populates="user", cascade="all, delete-orphan")
    workout_logs = relationship("WorkoutLog", back_populates="user", cascade="all, delete-orphan")
    meal_plans = relationship("MealPlan", back_populates="user", cascade="all, delete-orphan")
    coach_memories = relationship("AICoachMemory", back_populates="user", cascade="all, delete-orphan")
    progress_metrics = relationship("ProgressMetric", back_populates="user", cascade="all, delete-orphan")


class WorkoutSplit(Base):
    __tablename__ = "workout_splits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day_of_week = Column(String, nullable=False)  # Monday, Tuesday, etc.
    muscle_groups = Column(String, nullable=False) # comma-separated, e.g., "Chest,Triceps"
    
    user = relationship("User", back_populates="splits")


class Exercise(Base):
    __tablename__ = "exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    target_muscle = Column(String, index=True, nullable=False)
    secondary_muscles = Column(String, nullable=True) # comma-separated
    equipment = Column(String, index=True, nullable=False)
    difficulty = Column(String, nullable=False) # Beginner, Intermediate, Advanced
    
    instructions = Column(Text, nullable=True) # step-by-step
    mistakes = Column(Text, nullable=True)     # common mistakes
    alternatives = Column(String, nullable=True) # comma-separated names
    variations = Column(Text, nullable=True)
    rep_range = Column(String, default="8-12")


class WorkoutLog(Base):
    __tablename__ = "workout_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date = Column(Date, default=datetime.date.today, index=True)
    workout_name = Column(String, nullable=False) # e.g. "Push Day"
    completed = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="workout_logs")
    exercise_logs = relationship("ExerciseLog", back_populates="workout_log", cascade="all, delete-orphan")


class ExerciseLog(Base):
    __tablename__ = "exercise_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    workout_log_id = Column(Integer, ForeignKey("workout_logs.id", ondelete="CASCADE"), index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="SET NULL"), nullable=True)
    exercise_name = Column(String, nullable=False)
    sets_data = Column(Text, nullable=False) # JSON list: [{"set": 1, "weight": 60, "reps": 10}, ...]
    
    workout_log = relationship("WorkoutLog", back_populates="exercise_logs")


class MealPlan(Base):
    __tablename__ = "meal_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date = Column(Date, default=datetime.date.today, index=True)
    calories = Column(Float, nullable=False)
    protein = Column(Float, nullable=False)
    carbs = Column(Float, nullable=False)
    fat = Column(Float, nullable=False)
    fiber = Column(Float, default=25.0)
    budget = Column(Float, nullable=True) # daily estimated cost limit
    
    user = relationship("User", back_populates="meal_plans")
    meals = relationship("Meal", back_populates="meal_plan", cascade="all, delete-orphan")


class Meal(Base):
    __tablename__ = "meals"
    
    id = Column(Integer, primary_key=True, index=True)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id", ondelete="CASCADE"), index=True)
    name = Column(String, nullable=False) # Breakfast, Lunch, Snack, Dinner, Pre-workout, Post-workout
    cost = Column(Float, default=0.0)
    
    meal_plan = relationship("MealPlan", back_populates="meals")
    items = relationship("MealItem", back_populates="meal", cascade="all, delete-orphan")


class MealItem(Base):
    __tablename__ = "meal_items"
    
    id = Column(Integer, primary_key=True, index=True)
    meal_id = Column(Integer, ForeignKey("meals.id", ondelete="CASCADE"), index=True)
    food_name = Column(String, nullable=False)
    amount = Column(String, nullable=False) # e.g. "100g", "2 large"
    calories = Column(Float, nullable=False)
    protein = Column(Float, nullable=False)
    carbs = Column(Float, nullable=False)
    fat = Column(Float, nullable=False)
    cost = Column(Float, default=0.0)
    
    meal = relationship("Meal", back_populates="items")


class FoodItem(Base):
    __tablename__ = "food_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    calories_per_100g = Column(Float, nullable=False)
    protein_per_100g = Column(Float, nullable=False)
    carbs_per_100g = Column(Float, nullable=False)
    fat_per_100g = Column(Float, nullable=False)
    fiber_per_100g = Column(Float, default=0.0)
    cost_per_100g = Column(Float, default=0.0) # Local cost proxy (e.g. in INR or USD)
    category = Column(String, nullable=True) # Proteins, Grains, Vegetables, Dairy, Fats, Fruits
    is_veg = Column(Boolean, default=True)


class Supplement(Base):
    __tablename__ = "supplements"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    scientific_evidence = Column(Text, nullable=True) # "Strong", "Moderate", "Weak"
    benefits = Column(Text, nullable=True)
    dosage = Column(Text, nullable=True)
    safety = Column(Text, nullable=True)
    cost_effectiveness = Column(Text, nullable=True)
    best_timing = Column(String, nullable=True)


class AICoachMemory(Base):
    __tablename__ = "ai_coach_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    key = Column(String, nullable=False, index=True) # e.g. "preferred_workout_duration"
    value = Column(Text, nullable=False)
    
    user = relationship("User", back_populates="coach_memories")


class ProgressMetric(Base):
    __tablename__ = "progress_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date = Column(Date, default=datetime.date.today, index=True)
    weight = Column(Float, nullable=True)       # in kg
    body_fat = Column(Float, nullable=True)     # in %
    chest = Column(Float, nullable=True)        # in cm
    waist = Column(Float, nullable=True)        # in cm
    arms = Column(Float, nullable=True)         # in cm
    thighs = Column(Float, nullable=True)       # in cm
    photo_url = Column(String, nullable=True)
    
    user = relationship("User", back_populates="progress_metrics")
