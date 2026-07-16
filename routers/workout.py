from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from database import get_db
from routers.auth import get_current_user
import models
import schemas
from ai_service import AIService

router = APIRouter(
    prefix="/workouts",
    tags=["Workouts"]
)

ai_service = AIService()

# --- Splits ---
@router.get("/split", response_model=List[schemas.WorkoutSplitOut])
def get_user_split(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    splits = db.query(models.WorkoutSplit).filter(models.WorkoutSplit.user_id == current_user.id).all()
    # Sort by day order
    day_order = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    splits.sort(key=lambda s: day_order.get(s.day_of_week, 7))
    return splits


@router.put("/split", response_model=List[schemas.WorkoutSplitOut])
def update_user_split(split_data: schemas.WorkoutSplitCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Delete old splits
    db.query(models.WorkoutSplit).filter(models.WorkoutSplit.user_id == current_user.id).delete()
    
    new_splits = []
    for split in split_data.splits:
        db_split = models.WorkoutSplit(
            user_id=current_user.id,
            day_of_week=split.day_of_week,
            muscle_groups=split.muscle_groups
        )
        db.add(db_split)
        new_splits.append(db_split)
        
    db.commit()
    for s in new_splits:
        db.refresh(s)
    return new_splits


# --- Exercises / Encyclopedia ---
@router.get("/exercises", response_model=List[schemas.ExerciseOut])
def get_exercises(
    target_muscle: Optional[str] = None,
    equipment: Optional[str] = None,
    difficulty: Optional[str] = None,
    query: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.Exercise)
    if target_muscle:
        q = q.filter(models.Exercise.target_muscle.ilike(f"%{target_muscle}%"))
    if equipment:
        q = q.filter(models.Exercise.equipment.ilike(f"%{equipment}%"))
    if difficulty:
        q = q.filter(models.Exercise.difficulty == difficulty)
    if query:
        q = q.filter(models.Exercise.name.ilike(f"%{query}%") | models.Exercise.instructions.ilike(f"%{query}%"))
    return q.all()


@router.get("/exercises/{exercise_id}", response_model=schemas.ExerciseOut)
def get_exercise_details(exercise_id: int, db: Session = Depends(get_db)):
    exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise


# --- AI Workout Generation ---
@router.post("/generate-daily")
def generate_daily_workout(day_name: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Find split for this day
    split = db.query(models.WorkoutSplit).filter(
        models.WorkoutSplit.user_id == current_user.id,
        models.WorkoutSplit.day_of_week == day_name
    ).first()
    
    if not split or split.muscle_groups.lower() == "rest":
        return {"workout_name": "Rest Day", "exercises": [], "message": "Enjoy your rest day! Focus on recovery."}
        
    muscles = [m.strip() for m in split.muscle_groups.split(",")]
    
    # Load all exercises to pass to the generator
    all_ex = db.query(models.Exercise).all()
    # If database is empty, return empty list
    if not all_ex:
        return {"workout_name": f"{day_name} Workout", "exercises": [], "message": "Exercise database is empty."}
        
    ex_dicts = []
    for ex in all_ex:
        ex_dicts.append({
            "id": ex.id,
            "name": ex.name,
            "target_muscle": ex.target_muscle,
            "equipment": ex.equipment,
            "difficulty": ex.difficulty
        })
        
    user_dict = {
        "age": current_user.age,
        "primary_goal": current_user.primary_goal,
        "experience_level": current_user.experience_level,
        "available_equipment": current_user.available_equipment,
        "injuries": current_user.injuries
    }
    
    workout = ai_service.generate_workout(user_dict, day_name, muscles, ex_dicts)
    return workout


@router.post("/rotation")
def suggest_rotation(exercise_name: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ex = db.query(models.Exercise).filter(models.Exercise.name == exercise_name).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")
        
    # Get alternative list
    alternatives = []
    if ex.alternatives:
        alt_names = [a.strip() for a in ex.alternatives.split(",")]
        alternatives = db.query(models.Exercise).filter(models.Exercise.name.in_(alt_names)).all()
        
    # If no designated alternatives, search matching target muscle and equipment
    if not alternatives:
        alternatives = db.query(models.Exercise).filter(
            models.Exercise.target_muscle == ex.target_muscle,
            models.Exercise.equipment == ex.equipment,
            models.Exercise.name != ex.name
        ).limit(3).all()
        
    # Format response
    results = []
    for alt in alternatives:
        results.append({
            "name": alt.name,
            "target_muscle": alt.target_muscle,
            "equipment": alt.equipment,
            "difficulty": alt.difficulty,
            "rep_range": alt.rep_range,
            "reasoning": f"Great alternative for {ex.name} using {alt.equipment} to target the {alt.target_muscle}."
        })
    return results


# --- Logging ---
@router.post("/logs", response_model=schemas.WorkoutLogOut)
def log_workout(log_data: schemas.WorkoutLogCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Increment streak logic
    today = datetime.date.today()
    # Check if logged today or yesterday
    last_log = db.query(models.WorkoutLog).filter(
        models.WorkoutLog.user_id == current_user.id
    ).order_by(models.WorkoutLog.date.desc()).first()
    
    if last_log:
        days_diff = (today - last_log.date).days
        if days_diff == 1:
            current_user.streak += 1
        elif days_diff > 1:
            current_user.streak = 1 # Reset to 1
    else:
        current_user.streak = 1 # Initial workout
        
    current_user.streak_updated_at = datetime.datetime.utcnow()
    
    # Save log
    db_log = models.WorkoutLog(
        user_id=current_user.id,
        date=log_data.date or today,
        workout_name=log_data.workout_name,
        completed=log_data.completed
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    
    for ex_log in log_data.exercise_logs:
        # Resolve exercise_id if possible
        ex = db.query(models.Exercise).filter(models.Exercise.name == ex_log.exercise_name).first()
        ex_id = ex.id if ex else None
        
        # Serialize sets_data to JSON string
        sets_json = json.dumps([{"set": s.set_number, "weight": s.weight, "reps": s.reps} for s in ex_log.sets_data])
        
        db_ex_log = models.ExerciseLog(
            workout_log_id=db_log.id,
            exercise_id=ex_id,
            exercise_name=ex_log.exercise_name,
            sets_data=sets_json
        )
        db.add(db_ex_log)
        
    db.commit()
    db.refresh(db_log)
    return db_log


@router.get("/logs", response_model=List[schemas.WorkoutLogOut])
def get_workout_logs(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(models.WorkoutLog).filter(models.WorkoutLog.user_id == current_user.id).order_by(models.WorkoutLog.date.desc()).all()
    # Unpack JSON sets_data for output validation
    for log in logs:
        for ex_log in log.exercise_logs:
            try:
                # Convert serialized JSON string back to list of dicts for schemas.WorkoutLogOut
                parsed_sets = json.loads(ex_log.sets_data)
                # Map keys from "set" to "set_number" for schemas compatibility
                ex_log.sets_data = [
                    schemas.SetLog(set_number=s.get("set", 1), weight=s.get("weight", 0.0), reps=s.get("reps", 0))
                    for s in parsed_sets
                ]
            except Exception:
                ex_log.sets_data = []
    return logs
import datetime
