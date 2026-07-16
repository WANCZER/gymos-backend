from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
import json

from database import get_db
from routers.auth import get_current_user
import models
import schemas

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)

@router.get("/metrics", response_model=List[schemas.ProgressMetricOut])
def get_metrics_history(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.ProgressMetric).filter(
        models.ProgressMetric.user_id == current_user.id
    ).order_by(models.ProgressMetric.date.asc()).all()


@router.post("/metrics", response_model=schemas.ProgressMetricOut)
def log_progress_metrics(metrics: schemas.ProgressMetricCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = datetime.date.today()
    log_date = metrics.date or today
    
    # Check if entry already exists for this date
    existing = db.query(models.ProgressMetric).filter(
        models.ProgressMetric.user_id == current_user.id,
        models.ProgressMetric.date == log_date
    ).first()
    
    # If logging weight, update current user's weight
    if metrics.weight is not None:
        current_user.weight = metrics.weight
        
    if existing:
        for key, value in metrics.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
        
    db_metrics = models.ProgressMetric(
        user_id=current_user.id,
        date=log_date,
        weight=metrics.weight,
        body_fat=metrics.body_fat,
        chest=metrics.chest,
        waist=metrics.waist,
        arms=metrics.arms,
        thighs=metrics.thighs,
        photo_url=metrics.photo_url
    )
    db.add(db_metrics)
    db.commit()
    db.refresh(db_metrics)
    return db_metrics


@router.get("/overview")
def get_analytics_overview(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Workout stats
    total_workouts = db.query(models.WorkoutLog).filter(
        models.WorkoutLog.user_id == current_user.id,
        models.WorkoutLog.completed == True
    ).count()
    
    # Calculate weekly training volume (sets * reps * weight)
    logs = db.query(models.WorkoutLog).filter(
        models.WorkoutLog.user_id == current_user.id,
        models.WorkoutLog.completed == True
    ).all()
    
    weekly_volume = 0.0
    today = datetime.date.today()
    one_week_ago = today - datetime.timedelta(days=7)
    
    recent_logs = [log for log in logs if log.date >= one_week_ago]
    
    # Muscle group frequency
    muscle_frequency = {}
    
    for log in logs:
        for ex_log in log.exercise_logs:
            # Accumulate volume if in last 7 days
            if log.date >= one_week_ago:
                try:
                    sets = json.loads(ex_log.sets_data)
                    for s in sets:
                        weekly_volume += s.get("weight", 0.0) * s.get("reps", 0)
                except Exception:
                    pass
            
            # Resolve target muscle
            ex = db.query(models.Exercise).filter(models.Exercise.name == ex_log.exercise_name).first()
            if ex:
                muscle_frequency[ex.target_muscle] = muscle_frequency.get(ex.target_muscle, 0) + 1

    # 2. Nutrition average vs targets (last 7 days)
    diet_plans = db.query(models.MealPlan).filter(
        models.MealPlan.user_id == current_user.id,
        models.MealPlan.date >= one_week_ago
    ).all()
    
    avg_protein = 0.0
    avg_calories = 0.0
    if diet_plans:
        avg_protein = sum(p.protein for p in diet_plans) / len(diet_plans)
        avg_calories = sum(p.calories for p in diet_plans) / len(diet_plans)

    # 3. Recovery estimation
    # Simple logic: muscles trained yesterday are resting (20% recovered). Trained 2 days ago are 60%.
    # Otherwise 100% recovered.
    recovery_status = {}
    all_muscles = ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core"]
    for m in all_muscles:
        recovery_status[m] = 100
        
    for log in logs:
        days_ago = (today - log.date).days
        if days_ago == 1: # Trained yesterday
            for ex_log in log.exercise_logs:
                ex = db.query(models.Exercise).filter(models.Exercise.name == ex_log.exercise_name).first()
                if ex:
                    recovery_status[ex.target_muscle] = 30 # Sore/Resting
        elif days_ago == 2: # Trained 2 days ago
            for ex_log in log.exercise_logs:
                ex = db.query(models.Exercise).filter(models.Exercise.name == ex_log.exercise_name).first()
                if ex:
                    # Don't overwrite yesterday's lower recovery
                    recovery_status[ex.target_muscle] = min(recovery_status.get(ex.target_muscle, 100), 70)

    # 4. Generate AI Insights list
    insights = []
    if current_user.streak >= 3:
        insights.append(f"Your consistency is excellent! You are on a {current_user.streak}-workout streak.")
    else:
        insights.append("Log your next workout to build up your streak.")
        
    if avg_protein > 0:
        target_pro = current_user.weight * 2.0 if current_user.weight else 140
        diff_pct = ((avg_protein - target_pro) / target_pro) * 100
        if diff_pct < -15:
            insights.append(f"Your protein intake has averaged {abs(diff_pct):.0f}% below your target this week. Consider adding more eggs or soy chunks.")
        elif abs(diff_pct) <= 15:
            insights.append("Protein intake consistency is looking solid. Keep hitting those daily targets.")
            
    # Muscle balance check
    legs_trained = muscle_frequency.get("Legs", 0)
    upper_trained = muscle_frequency.get("Chest", 0) + muscle_frequency.get("Back", 0)
    if upper_trained > 3 * legs_trained:
        insights.append("Warning: You may be undertraining lower body relative to upper body. Add leg days to balance volume.")
        
    if not insights:
        insights.append("Great start! Log a few more workouts and meals to generate personalized AI performance insights.")

    return {
        "completed_workouts": total_workouts,
        "streak": current_user.streak,
        "weekly_volume_kg": round(weekly_volume, 1),
        "average_calories_consumed": round(avg_calories),
        "average_protein_consumed_g": round(avg_protein),
        "muscle_frequency": muscle_frequency,
        "recovery_status": recovery_status,
        "ai_insights": insights
    }
