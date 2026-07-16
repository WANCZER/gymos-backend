from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime

from database import get_db
from routers.auth import get_current_user
import models
import schemas
from ai_service import AIService

router = APIRouter(
    prefix="/nutrition",
    tags=["Nutrition"]
)

ai_service = AIService()

# --- Food Database ---
@router.get("/foods", response_model=List[schemas.FoodItemOut])
def get_foods(
    query: Optional[str] = None,
    category: Optional[str] = None,
    high_protein: Optional[bool] = False,
    budget_friendly: Optional[bool] = False,
    is_veg: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.FoodItem)
    if query:
        q = q.filter(models.FoodItem.name.ilike(f"%{query}%"))
    if category:
        q = q.filter(models.FoodItem.category == category)
    if is_veg is not None:
        q = q.filter(models.FoodItem.is_veg == is_veg)
    
    results = q.all()
    
    if high_protein:
        results = [f for f in results if (f.protein_per_100g / (f.calories_per_100g + 1)) * 100 > 8]
    if budget_friendly:
        results = [f for f in results if f.cost_per_100g < 30] # local currency unit cap
        
    return results


@router.get("/foods/compare")
def compare_foods(food_a: str, food_b: str, db: Session = Depends(get_db)):
    fa = db.query(models.FoodItem).filter(models.FoodItem.name.ilike(food_a)).first()
    fb = db.query(models.FoodItem).filter(models.FoodItem.name.ilike(food_b)).first()
    
    if not fa or not fb:
        raise HTTPException(status_code=404, detail="One or both foods not found in database")
        
    return {
        "food_a": schemas.FoodItemOut.from_orm(fa),
        "food_b": schemas.FoodItemOut.from_orm(fb),
        "comparison_analysis": f"{fa.name} contains {fa.protein_per_100g}g protein per 100g vs {fb.name}'s {fb.protein_per_100g}g. "
                               f"Cost ratio is {fa.name} ({fa.cost_per_100g}/100g) vs {fb.name} ({fb.cost_per_100g}/100g)."
    }


# --- Diet Planner ---
@router.post("/generate-diet", response_model=schemas.MealPlanOut)
def generate_meal_plan(target_date: Optional[datetime.date] = None, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    date_val = target_date or datetime.date.today()
    
    # Check if a meal plan already exists for today
    existing_plan = db.query(models.MealPlan).filter(
        models.MealPlan.user_id == current_user.id,
        models.MealPlan.date == date_val
    ).first()
    
    if existing_plan:
        return existing_plan
        
    # Get all database foods
    all_foods = db.query(models.FoodItem).all()
    if not all_foods:
        raise HTTPException(status_code=400, detail="Food items database is empty. Please run seeds.")
        
    food_dicts = []
    for f in all_foods:
        food_dicts.append({
            "name": f.name,
            "calories_per_100g": f.calories_per_100g,
            "protein_per_100g": f.protein_per_100g,
            "carbs_per_100g": f.carbs_per_100g,
            "fat_per_100g": f.fat_per_100g,
            "fiber_per_100g": f.fiber_per_100g,
            "cost_per_100g": f.cost_per_100g,
            "is_veg": f.is_veg
        })
        
    user_dict = {
        "age": current_user.age,
        "height": current_user.height,
        "weight": current_user.weight,
        "gender": current_user.gender or "Male",
        "primary_goal": current_user.primary_goal,
        "diet_preference": current_user.diet_preference,
        "diet_budget": current_user.diet_budget
    }
    
    budget_limit = 150.0 if current_user.diet_budget.lower() == "low" else 350.0
    
    # Generate daily meal plan via AI / Fallback optimizer
    diet_data = ai_service.generate_diet(user_dict, budget_limit, food_dicts)
    
    db_plan = models.MealPlan(
        user_id=current_user.id,
        date=date_val,
        calories=diet_data["calories"],
        protein=diet_data["protein"],
        carbs=diet_data["carbs"],
        fat=diet_data["fat"],
        fiber=diet_data.get("fiber", 25.0),
        budget=budget_limit
    )
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    
    for meal in diet_data["meals"]:
        db_meal = models.Meal(
            meal_plan_id=db_plan.id,
            name=meal["name"],
            cost=meal.get("cost", 0.0)
        )
        db.add(db_meal)
        db.commit()
        db.refresh(db_meal)
        
        for item in meal["items"]:
            db_item = models.MealItem(
                meal_id=db_meal.id,
                food_name=item["food_name"],
                amount=item["amount"],
                calories=item["calories"],
                protein=item["protein"],
                carbs=item["carbs"],
                fat=item["fat"],
                cost=item.get("cost", 0.0)
            )
            db.add(db_item)
            
    db.commit()
    db.refresh(db_plan)
    return db_plan


@router.get("/meal-plan", response_model=List[schemas.MealPlanOut])
def get_meal_plans(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.MealPlan).filter(models.MealPlan.user_id == current_user.id).order_by(models.MealPlan.date.desc()).all()


# --- Grocery Planner ---
@router.get("/grocery-list")
def get_grocery_list(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Find all meal plans in the last 7 days
    today = datetime.date.today()
    seven_days_ago = today - datetime.timedelta(days=7)
    
    plans = db.query(models.MealPlan).filter(
        models.MealPlan.user_id == current_user.id,
        models.MealPlan.date >= seven_days_ago
    ).all()
    
    if not plans:
        return {"items": [], "total_estimated_cost": 0.0, "message": "No active meal plans found to generate a grocery list. Generate a meal plan first!"}
        
    raw_list = {}
    total_cost = 0.0
    
    for plan in plans:
        for meal in plan.meals:
            for item in meal.items:
                # Accumulate quantities. Simple text accumulation or weight extraction.
                food_name = item.food_name
                amount_str = item.amount
                
                # Check cost
                total_cost += item.cost
                
                # Extract weight in grams if format is "Xg"
                weight_g = 0
                if amount_str.lower().endswith("g"):
                    try:
                        weight_g = int(amount_str[:-1].strip())
                    except ValueError:
                        pass
                
                if food_name not in raw_list:
                    raw_list[food_name] = {
                        "name": food_name,
                        "total_weight_g": weight_g,
                        "non_g_amounts": [amount_str] if weight_g == 0 else [],
                        "estimated_cost": item.cost
                    }
                else:
                    raw_list[food_name]["total_weight_g"] += weight_g
                    raw_list[food_name]["estimated_cost"] += item.cost
                    if weight_g == 0:
                        raw_list[food_name]["non_g_amounts"].append(amount_str)

    # Format result
    items = []
    for food_name, details in raw_list.items():
        # Match food category from DB
        db_food = db.query(models.FoodItem).filter(models.FoodItem.name == food_name).first()
        category = db_food.category if db_food else "Other"
        
        qty_str = ""
        if details["total_weight_g"] > 0:
            weight = details["total_weight_g"]
            if weight >= 1000:
                qty_str = f"{weight/1000:.2f} kg"
            else:
                qty_str = f"{weight} g"
        else:
            # Count occurances of non-g quantities
            counts = {}
            for item in details["non_g_amounts"]:
                counts[item] = counts.get(item, 0) + 1
            qty_str = ", ".join(f"{v}x {k}" for k, v in counts.items())
            
        items.append({
            "name": food_name,
            "quantity": qty_str,
            "category": category,
            "estimated_cost": round(details["estimated_cost"], 2),
            "in_pantry": False # Frontend sets this
        })
        
    return {
        "items": items,
        "total_estimated_cost": round(total_cost, 2),
        "days_covered": len(plans)
    }
