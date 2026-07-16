from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, Base, SessionLocal
import models
from routers import auth, workout, nutrition, supplement, coach, analytics

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GymOS API",
    description="The World's Most Intelligent AI Fitness Ecosystem backend api.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(workout.router)
app.include_router(nutrition.router)
app.include_router(supplement.router)
app.include_router(coach.router)
app.include_router(analytics.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to GymOS - The AI Fitness Operating System API"}


@app.on_event("startup")
def seed_database():
    db = SessionLocal()
    try:
        # 1. Seed Exercises
        if db.query(models.Exercise).count() == 0:
            exercises = [
                models.Exercise(
                    name="Bench Press",
                    target_muscle="Chest",
                    secondary_muscles="Shoulders,Triceps",
                    equipment="Barbell",
                    difficulty="Intermediate",
                    instructions="Lay flat on a bench. Grip the barbell slightly wider than shoulder width. Unrack it, lower to mid-chest, and press back up locking your elbows.",
                    mistakes="Bouncing the bar off your chest, flaring your elbows at a 90-degree angle.",
                    alternatives="Dumbbell Press,Push-ups,Cable Flyes",
                    variations="Incline Bench Press,Decline Bench Press",
                    rep_range="5-8"
                ),
                models.Exercise(
                    name="Dumbbell Press",
                    target_muscle="Chest",
                    secondary_muscles="Shoulders,Triceps",
                    equipment="Dumbbells",
                    difficulty="Beginner",
                    instructions="Lie flat on a bench holding dumbbells at chest level. Press the dumbbells straight up above you until arms are extended. Lower under control.",
                    mistakes="Clashing dumbbells together at the top, shortening range of motion.",
                    alternatives="Bench Press,Push-ups",
                    variations="Incline Dumbbell Press,Single Arm Press",
                    rep_range="8-12"
                ),
                models.Exercise(
                    name="Push-up",
                    target_muscle="Chest",
                    secondary_muscles="Shoulders,Triceps,Core",
                    equipment="Bodyweight",
                    difficulty="Beginner",
                    instructions="Start in plank position. Lower body until chest almost touches the floor, keeping elbows at a 45-degree angle. Press back up.",
                    mistakes="Sagging hips, head craning forward, elbows flared.",
                    alternatives="Bench Press,Dumbbell Press",
                    variations="Decline Push-ups,Diamond Push-ups",
                    rep_range="10-20"
                ),
                models.Exercise(
                    name="Pull-up",
                    target_muscle="Back",
                    secondary_muscles="Biceps,Shoulders,Core",
                    equipment="Bodyweight",
                    difficulty="Intermediate",
                    instructions="Hang from a bar with a wide overhand grip. Pull your chest up to the bar, lead with your elbows. Lower slowly back to dead hang.",
                    mistakes="Using momentum/kicking legs, half reps.",
                    alternatives="Lat Pulldown,Bent Over Row",
                    variations="Chin-ups,Weighted Pull-ups",
                    rep_range="5-10"
                ),
                models.Exercise(
                    name="Lat Pulldown",
                    target_muscle="Back",
                    secondary_muscles="Biceps,Shoulders",
                    equipment="Cable",
                    difficulty="Beginner",
                    instructions="Sit at pulldown station. Pull bar down to collarbone level, squeezing shoulder blades. Return bar slowly to starting position.",
                    mistakes="Leaning back excessively, pulling bar behind neck.",
                    alternatives="Pull-up,Bent Over Row",
                    variations="Close Grip Pulldown,Underhand Pulldown",
                    rep_range="8-12"
                ),
                models.Exercise(
                    name="Bent Over Row",
                    target_muscle="Back",
                    secondary_muscles="Biceps,Shoulders,Hamstrings",
                    equipment="Barbell",
                    difficulty="Intermediate",
                    instructions="Hinge at hips, keep back straight, hold barbell with overhand grip. Pull bar to lower ribs, squeezing shoulder blades. Lower slowly.",
                    mistakes="Rounding lower back, standing too upright, using arms instead of lats.",
                    alternatives="Dumbbell Row,Lat Pulldown",
                    variations="Underhand Barbell Row,Pendlay Row",
                    rep_range="6-10"
                ),
                models.Exercise(
                    name="Dumbbell Row",
                    target_muscle="Back",
                    secondary_muscles="Biceps,Shoulders",
                    equipment="Dumbbells",
                    difficulty="Beginner",
                    instructions="Support one knee and hand on flat bench. With free hand, pull dumbbell up to hip, keeping elbow close to side. Lower under control.",
                    mistakes="Rotating torso, pulling to chest instead of hip.",
                    alternatives="Bent Over Row,Lat Pulldown",
                    variations="Incline Bench Dumbbell Row,Chest Supported Row",
                    rep_range="8-12"
                ),
                models.Exercise(
                    name="Squat",
                    target_muscle="Legs",
                    secondary_muscles="Glutes,Hamstrings,Core",
                    equipment="Barbell",
                    difficulty="Intermediate",
                    instructions="Place barbell across upper back. Stand shoulder-width apart. Sit hips back and down until thighs are parallel to ground. Drive back up.",
                    mistakes="Knees collapsing inward, heels lifting off floor, rounding back.",
                    alternatives="Goblet Squat,Leg Press,Bulgarian Split Squat",
                    variations="Front Squat,Box Squat",
                    rep_range="6-10"
                ),
                models.Exercise(
                    name="Goblet Squat",
                    target_muscle="Legs",
                    secondary_muscles="Glutes,Core",
                    equipment="Dumbbells",
                    difficulty="Beginner",
                    instructions="Hold dumbbell vertically against chest. Lower into squat, keeping chest tall and elbows inside knees. Push through feet to rise.",
                    mistakes="Rounding upper back, leaning forward too far.",
                    alternatives="Squat,Leg Press",
                    variations="Kettlebell Goblet Squat",
                    rep_range="10-15"
                ),
                models.Exercise(
                    name="Bulgarian Split Squat",
                    target_muscle="Legs",
                    secondary_muscles="Glutes,Core",
                    equipment="Dumbbells",
                    difficulty="Intermediate",
                    instructions="Place one foot behind you on a bench. Hold dumbbells at sides. Lower front thigh until parallel to floor. Push up using front leg.",
                    mistakes="Front knee traveling too far past toes, losing balance.",
                    alternatives="Lunge,Goblet Squat",
                    variations="Bodyweight Split Squat",
                    rep_range="8-12"
                ),
                models.Exercise(
                    name="Overhead Press",
                    target_muscle="Shoulders",
                    secondary_muscles="Triceps,Core",
                    equipment="Barbell",
                    difficulty="Intermediate",
                    instructions="Hold barbell at chest height, shoulder width. Stand tall, brace core, press bar straight up overhead, moving face back slightly. Lockout.",
                    mistakes="Arching lower back, using leg drive (which makes it a push press).",
                    alternatives="Dumbbell Lateral Raise,Dumbbell Shoulder Press",
                    variations="Seated Shoulder Press,Dumbbell Shoulder Press",
                    rep_range="6-10"
                ),
                models.Exercise(
                    name="Dumbbell Lateral Raise",
                    target_muscle="Shoulders",
                    secondary_muscles="None",
                    equipment="Dumbbells",
                    difficulty="Beginner",
                    instructions="Stand with dumbbells at sides. Raise arms out to sides, keeping slight bend in elbows, until parallel to floor. Lower slowly.",
                    mistakes="Swinging body, leading with hands instead of elbows, lifting too heavy.",
                    alternatives="Cable Lateral Raise,Overhead Press",
                    variations="Seated Lateral Raise,Incline Lateral Raise",
                    rep_range="12-15"
                ),
                models.Exercise(
                    name="Bicep Curl",
                    target_muscle="Arms",
                    secondary_muscles="Forearms",
                    equipment="Barbell",
                    difficulty="Beginner",
                    instructions="Stand holding barbell with underhand grip. Keep elbows tucked at sides. Curl bar up towards shoulders. Lower under control.",
                    mistakes="Swinging hips, elbows drifting forward, dropping weight fast.",
                    alternatives="Dumbbell Hammer Curl,Cable Curl",
                    variations="Dumbbell Bicep Curl,Preacher Curl",
                    rep_range="10-12"
                ),
                models.Exercise(
                    name="Tricep Pushdown",
                    target_muscle="Arms",
                    secondary_muscles="None",
                    equipment="Cable",
                    difficulty="Beginner",
                    instructions="Grip cable rope/bar at chest level. Squeeze triceps to press bar down until arms are fully locked. Return slowly.",
                    mistakes="Elbows flaring out, leaning entire weight on bar.",
                    alternatives="Skull Crushers,Close Grip Bench Press",
                    variations="Rope Pushdown,Single Arm Pushdown",
                    rep_range="10-15"
                ),
                models.Exercise(
                    name="Plank",
                    target_muscle="Core",
                    secondary_muscles="Shoulders,Glutes",
                    equipment="Bodyweight",
                    difficulty="Beginner",
                    instructions="Hold body in straight line supported by elbows and toes. Brace core and glutes. Hold for time.",
                    mistakes="Hips sagging or hiking too high, head dropping down.",
                    alternatives="Hanging Leg Raise,Russian Twists",
                    variations="Side Plank,Weighted Plank",
                    rep_range="30-60s"
                )
            ]
            db.add_all(exercises)
            db.commit()

        # 2. Seed Foods
        if db.query(models.FoodItem).count() == 0:
            foods = [
                models.FoodItem(name="Chicken Breast", calories_per_100g=165.0, protein_per_100g=31.0, carbs_per_100g=0.0, fat_per_100g=3.6, fiber_per_100g=0.0, cost_per_100g=30.0, category="Proteins", is_veg=False),
                models.FoodItem(name="Whole Eggs", calories_per_100g=155.0, protein_per_100g=13.0, carbs_per_100g=1.1, fat_per_100g=11.0, fiber_per_100g=0.0, cost_per_100g=15.0, category="Proteins", is_veg=False),
                models.FoodItem(name="Rolled Oats", calories_per_100g=389.0, protein_per_100g=16.9, carbs_per_100g=66.0, fat_per_100g=6.9, fiber_per_100g=10.6, cost_per_100g=10.0, category="Grains", is_veg=True),
                models.FoodItem(name="Brown Rice", calories_per_100g=111.0, protein_per_100g=2.6, carbs_per_100g=23.0, fat_per_100g=0.9, fiber_per_100g=1.8, cost_per_100g=6.0, category="Grains", is_veg=True),
                models.FoodItem(name="Paneer (Cottage Cheese)", calories_per_100g=265.0, protein_per_100g=18.3, carbs_per_100g=1.2, fat_per_100g=20.8, fiber_per_100g=0.0, cost_per_100g=40.0, category="Dairy", is_veg=True),
                models.FoodItem(name="Soy Chunks", calories_per_100g=345.0, protein_per_100g=52.0, carbs_per_100g=33.0, fat_per_100g=0.5, fiber_per_100g=13.0, cost_per_100g=12.0, category="Proteins", is_veg=True),
                models.FoodItem(name="Lentils (Dal)", calories_per_100g=116.0, protein_per_100g=9.0, carbs_per_100g=20.0, fat_per_100g=0.4, fiber_per_100g=8.0, cost_per_100g=8.0, category="Proteins", is_veg=True),
                models.FoodItem(name="Peanut Butter", calories_per_100g=588.0, protein_per_100g=25.0, carbs_per_100g=20.0, fat_per_100g=50.0, fiber_per_100g=6.0, cost_per_100g=25.0, category="Fats", is_veg=True),
                models.FoodItem(name="Banana", calories_per_100g=89.0, protein_per_100g=1.1, carbs_per_100g=22.8, fat_per_100g=0.3, fiber_per_100g=2.6, cost_per_100g=5.0, category="Fruits", is_veg=True),
                models.FoodItem(name="Broccoli", calories_per_100g=34.0, protein_per_100g=2.8, carbs_per_100g=6.6, fat_per_100g=0.4, fiber_per_100g=2.6, cost_per_100g=15.0, category="Vegetables", is_veg=True)
            ]
            db.add_all(foods)
            db.commit()

        # 3. Seed Supplements
        if db.query(models.Supplement).count() == 0:
            supplements = [
                models.Supplement(
                    name="Creatine Monohydrate",
                    scientific_evidence="Strong",
                    benefits="Increases muscle phosphocreatine levels, improving short-burst power output, strength, cell hydration, and hypertrophy.",
                    dosage="3-5 grams daily, taken consistently at any time of day. No loading phase strictly necessary.",
                    safety="Extremely safe. May cause minor water weight gain. No evidence of kidney damage in healthy individuals.",
                    cost_effectiveness="High",
                    best_timing="Any time (consistency is key)"
                ),
                models.Supplement(
                    name="Whey Protein",
                    scientific_evidence="Strong",
                    benefits="Highly bioavailable dairy protein rich in leucine. Excellent for hitting daily protein requirements and promoting muscle protein synthesis.",
                    dosage="1-2 scoops (25-50g) post-workout or to supplement protein-deficient meals.",
                    safety="Safe. Individuals with severe lactose intolerance may prefer Whey Isolate or Plant-based alternatives.",
                    cost_effectiveness="High",
                    best_timing="Post-workout or meal gap"
                ),
                models.Supplement(
                    name="Caffeine",
                    scientific_evidence="Strong",
                    benefits="Blocks adenosine receptors to reduce perceived exertion, increase mental focus, and temporarily boost muscle power.",
                    dosage="100-300mg taken 30-45 minutes before training. Avoid exceeding 400mg daily to prevent habituation.",
                    safety="Safe in moderate doses. Can cause insomnia, elevated heart rate, or jitters if under-tolerant.",
                    cost_effectiveness="High",
                    best_timing="30-45 mins pre-workout"
                ),
                models.Supplement(
                    name="Vitamin D3",
                    scientific_evidence="Moderate",
                    benefits="Supports bone density, testosterone production, and immune function, particularly in individuals with minimal sun exposure.",
                    dosage="1000-5000 IU daily taken with a fat-containing meal for absorption.",
                    safety="Extremely safe at standard doses. Mega-doses over 10000 IU daily over months can cause toxicity.",
                    cost_effectiveness="High",
                    best_timing="Morning with breakfast"
                )
            ]
            db.add_all(supplements)
            db.commit()
            
    finally:
        db.close()
