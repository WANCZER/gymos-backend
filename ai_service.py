import os
import json
import requests
from typing import List, Dict, Any, Optional

class AIService:
    def __init__(self):
        self.provider = os.environ.get("AI_PROVIDER", "fallback").lower()
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "llama3")
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.openai_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def _call_llm(self, prompt: str, system_prompt: str = "You are a professional AI fitness coach.") -> str:
        """Call configured LLM or fallback if call fails or keys are missing."""
        if self.provider == "openai" and self.openai_key:
            try:
                headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
                payload = {
                    "model": self.openai_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.5
                }
                r = requests.post(f"{self.openai_url}/chat/completions", headers=headers, json=payload, timeout=15)
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"OpenAI error, falling back: {e}")
                
        elif self.provider == "gemini" and self.gemini_key:
            try:
                # Using Gemini 1.5 Flash API format
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{
                        "parts": [{"text": f"System: {system_prompt}\n\nUser: {prompt}"}]
                    }]
                }
                r = requests.post(url, headers=headers, json=payload, timeout=15)
                if r.status_code == 200:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                print(f"Gemini error, falling back: {e}")
                
        elif self.provider == "ollama":
            try:
                payload = {
                    "model": self.ollama_model,
                    "prompt": f"System Instruction: {system_prompt}\n\nUser Prompt: {prompt}",
                    "stream": False
                }
                r = requests.post(self.ollama_url, json=payload, timeout=15)
                if r.status_code == 200:
                    return r.json()["response"]
            except Exception as e:
                print(f"Ollama error, falling back: {e}")

        # If provider is "fallback" or another model fails, return an empty string to trigger local rule-based system
        return ""

    def generate_workout(self, user_profile: Dict[str, Any], day_name: str, muscles: List[str], available_exercises: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates a daily workout split using LLM or rule-based fallback."""
        prompt = f"""
        User Profile:
        - Age: {user_profile.get('age')}
        - Goal: {user_profile.get('primary_goal')}
        - Experience: {user_profile.get('experience_level')}
        - Equipment: {user_profile.get('available_equipment')}
        - Injuries/Limitations: {user_profile.get('injuries')}
        
        Generate a workout for {day_name} focusing on: {', '.join(muscles)}.
        Choose from these available exercises: {[e['name'] for e in available_exercises]}.
        
        Respond ONLY with a valid JSON block of the format:
        {{
          "workout_name": "Workout Name",
          "exercises": [
            {{
              "exercise_name": "Exercise Name",
              "sets": 3,
              "reps": "8-12",
              "reasoning": "Why this exercise fits their goals/limitations"
            }}
          ]
        }}
        Do not output any markdown code blocks, just raw JSON.
        """
        
        system = "You are a professional strength coach. You only return raw JSON, no explanations."
        response_text = self._call_llm(prompt, system)
        
        if response_text:
            try:
                # Clean markdown wrapper if present
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)
                return data
            except Exception:
                pass # Proceed to fallback if parsing fails

        # --- Rule-Based Fallback ---
        # Filters: equipment, injury avoidance
        filtered_exercises = []
        user_equip = [eq.strip().lower() for eq in user_profile.get('available_equipment', 'bodyweight only').split(',')]
        user_injuries = [inj.strip().lower() for inj in user_profile.get('injuries', 'none').split(',')]
        
        for ex in available_exercises:
            # Check if user has required equipment
            req_equip = ex['equipment'].lower()
            equip_matches = False
            if 'full commercial gym' in user_equip:
                equip_matches = True
            elif req_equip == 'bodyweight' or req_equip in user_equip:
                equip_matches = True
            elif 'dumbbells only' in user_equip and req_equip in ['dumbbell', 'bodyweight']:
                equip_matches = True
            elif 'resistance bands' in user_equip and req_equip in ['bands', 'bodyweight']:
                equip_matches = True
                
            # Check injuries. If shoulder injury, avoid heavy overhead presses/upright rows.
            # If knee injury, avoid squats/lunges. If lower back, avoid deadlifts.
            injury_conflict = False
            for injury in user_injuries:
                if 'shoulder' in injury and any(x in ex['name'].lower() for x in ['overhead press', 'shoulder press', 'upright row']):
                    injury_conflict = True
                if 'knee' in injury and any(x in ex['name'].lower() for x in ['squat', 'lunge', 'leg press']):
                    injury_conflict = True
                if 'back' in injury and any(x in ex['name'].lower() for x in ['deadlift', 'barbell row']):
                    injury_conflict = True
            
            # Match target muscle group
            ex_muscle = ex['target_muscle'].lower()
            muscle_matches = any(m.lower() in ex_muscle for m in muscles)
            
            if equip_matches and not injury_conflict and muscle_matches:
                filtered_exercises.append(ex)

        # Build workout lists
        selected = filtered_exercises[:5] # pick top 5
        # If nothing matches, fallback to bodyweight exercises
        if not selected:
            selected = [ex for ex in available_exercises if ex['equipment'].lower() == 'bodyweight'][:3]

        exercises_list = []
        for ex in selected:
            rep_range = "12-15" if user_profile.get('primary_goal') == "Endurance" else "8-12"
            if user_profile.get('experience_level') == "Beginner":
                sets = 3
            else:
                sets = 4
                
            exercises_list.append({
                "exercise_name": ex['name'],
                "sets": sets,
                "reps": rep_range,
                "reasoning": f"Targeting the {ex['target_muscle']} using {ex['equipment']} is safe for your joints."
            })
            
        return {
            "workout_name": f"{day_name} ({', '.join(muscles)})",
            "exercises": exercises_list
        }

    def generate_diet(self, user_profile: Dict[str, Any], budget_val: float, available_foods: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates a calorie-calculated, budget-optimized daily meal plan."""
        # Calculate BMR and TDEE (Mifflin-St Jeor)
        weight = user_profile.get('weight', 70)
        height = user_profile.get('height', 170)
        age = user_profile.get('age', 25)
        gender = user_profile.get('gender', 'Male').lower()
        
        # Base BMR
        if gender == 'female':
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
            
        # Activity Multiplier (default 1.375 for active 3 days/wk)
        tdee = bmr * 1.375
        
        # Goal adjustment
        goal = user_profile.get('primary_goal', 'Maintenance')
        if goal == 'Muscle Gain':
            target_calories = tdee + 300
        elif goal == 'Fat Loss':
            target_calories = tdee - 500
        else:
            target_calories = tdee
            
        # Macronutrients
        # Protein: 2.0g per kg for muscle gain/loss
        protein_g = weight * 2.0
        # Fat: 25% of calories
        fat_g = (target_calories * 0.25) / 9
        # Carbs: remainder
        carbs_g = (target_calories - (protein_g * 4 + fat_g * 9)) / 4
        
        # Safety bounds
        protein_g = max(50.0, protein_g)
        fat_g = max(30.0, fat_g)
        carbs_g = max(50.0, carbs_g)
        
        # Prompt LLM
        prompt = f"""
        User Goal: {goal}
        Target Calories: {target_calories:.0f} kcal
        Target Protein: {protein_g:.0f}g, Carbs: {carbs_g:.0f}g, Fat: {fat_g:.0f}g
        Diet Preference: {user_profile.get('diet_preference')}
        Budget: {user_profile.get('diet_budget')} (Daily target cost limit: {budget_val})
        
        Create a 4-meal plan (Breakfast, Lunch, Snack, Dinner) using these local ingredients:
        {[{'name': f['name'], 'cost_100g': f['cost_per_100g'], 'is_veg': f['is_veg']} for f in available_foods]}
        
        Return ONLY a raw JSON block:
        {{
          "calories": {target_calories:.0f},
          "protein": {protein_g:.0f},
          "carbs": {carbs_g:.0f},
          "fat": {fat_g:.0f},
          "meals": [
            {{
              "name": "Breakfast",
              "cost": 50,
              "items": [
                {{
                  "food_name": "Eggs",
                  "amount": "3 large",
                  "calories": 210,
                  "protein": 18,
                  "carbs": 2,
                  "fat": 15,
                  "cost": 18
                }}
              ]
            }}
          ]
        }}
        """
        
        system = "You are a professional sports nutritionist. You only return valid raw JSON."
        response_text = self._call_llm(prompt, system)
        
        if response_text:
            try:
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)
                return data
            except Exception:
                pass

        # --- Fallback Optimizer (Rule-Based) ---
        is_veg = user_profile.get('diet_preference', 'Non-vegetarian') == 'Vegetarian' or user_profile.get('diet_preference') == 'Vegan'
        
        # Filter food items
        protein_sources = []
        carbs_sources = []
        fats_sources = []
        
        for f in available_foods:
            if is_veg and not f['is_veg']:
                continue
            
            p = f['protein_per_100g']
            c = f['carbs_per_100g']
            fa = f['fat_per_100g']
            
            # Simple sorting
            if p > 15:
                protein_sources.append(f)
            elif c > 30:
                carbs_sources.append(f)
            elif fa > 20:
                fats_sources.append(f)

        # Defaults if list is empty
        if not protein_sources:
            protein_sources = [f for f in available_foods if f['is_veg']]
        if not carbs_sources:
            carbs_sources = [f for f in available_foods if f['is_veg']]

        # Select items based on budget (sort by cost per protein/calorie)
        budget_level = user_profile.get('diet_budget', 'Medium').lower()
        if budget_level == 'low':
            protein_sources.sort(key=lambda x: x['cost_per_100g'])
            carbs_sources.sort(key=lambda x: x['cost_per_100g'])
        else:
            # Sort by protein concentration
            protein_sources.sort(key=lambda x: x['protein_per_100g'], reverse=True)

        # Compile meals
        p_item = protein_sources[0] if protein_sources else {'name': 'Oats', 'calories_per_100g': 389, 'protein_per_100g': 16.9, 'carbs_per_100g': 66, 'fat_per_100g': 6.9, 'cost_per_100g': 10}
        c_item = carbs_sources[0] if carbs_sources else {'name': 'Rice', 'calories_per_100g': 130, 'protein_per_100g': 2.7, 'carbs_per_100g': 28, 'fat_per_100g': 0.3, 'cost_per_100g': 5}
        
        meals_structure = [
            {
                "name": "Breakfast",
                "cost": p_item['cost_per_100g'] * 1.5,
                "items": [
                    {
                        "food_name": p_item['name'],
                        "amount": "150g",
                        "calories": p_item['calories_per_100g'] * 1.5,
                        "protein": p_item['protein_per_100g'] * 1.5,
                        "carbs": p_item['carbs_per_100g'] * 1.5,
                        "fat": p_item['fat_per_100g'] * 1.5,
                        "cost": p_item['cost_per_100g'] * 1.5
                    }
                ]
            },
            {
                "name": "Lunch",
                "cost": (p_item['cost_per_100g'] * 2) + c_item['cost_per_100g'] * 2,
                "items": [
                    {
                        "food_name": p_item['name'],
                        "amount": "200g",
                        "calories": p_item['calories_per_100g'] * 2,
                        "protein": p_item['protein_per_100g'] * 2,
                        "carbs": p_item['carbs_per_100g'] * 2,
                        "fat": p_item['fat_per_100g'] * 2,
                        "cost": p_item['cost_per_100g'] * 2
                    },
                    {
                        "food_name": c_item['name'],
                        "amount": "200g",
                        "calories": c_item['calories_per_100g'] * 2,
                        "protein": c_item['protein_per_100g'] * 2,
                        "carbs": c_item['carbs_per_100g'] * 2,
                        "fat": c_item['fat_per_100g'] * 2,
                        "cost": c_item['cost_per_100g'] * 2
                    }
                ]
            },
            {
                "name": "Snack",
                "cost": 15.0,
                "items": [
                    {
                        "food_name": "Banana",
                        "amount": "1 medium",
                        "calories": 105,
                        "protein": 1.3,
                        "carbs": 27,
                        "fat": 0.3,
                        "cost": 10
                    }
                ]
            },
            {
                "name": "Dinner",
                "cost": (p_item['cost_per_100g'] * 1.5) + c_item['cost_per_100g'] * 1.5,
                "items": [
                    {
                        "food_name": p_item['name'],
                        "amount": "150g",
                        "calories": p_item['calories_per_100g'] * 1.5,
                        "protein": p_item['protein_per_100g'] * 1.5,
                        "carbs": p_item['carbs_per_100g'] * 1.5,
                        "fat": p_item['fat_per_100g'] * 1.5,
                        "cost": p_item['cost_per_100g'] * 1.5
                    },
                    {
                        "food_name": c_item['name'],
                        "amount": "150g",
                        "calories": c_item['calories_per_100g'] * 1.5,
                        "protein": c_item['protein_per_100g'] * 1.5,
                        "carbs": c_item['carbs_per_100g'] * 1.5,
                        "fat": c_item['fat_per_100g'] * 1.5,
                        "cost": c_item['cost_per_100g'] * 1.5
                    }
                ]
            }
        ]
        
        # Compute exact totals
        tot_cal = sum(sum(item['calories'] for item in meal['items']) for meal in meals_structure)
        tot_pro = sum(sum(item['protein'] for item in meal['items']) for meal in meals_structure)
        tot_carb = sum(sum(item['carbs'] for item in meal['items']) for meal in meals_structure)
        tot_fat = sum(sum(item['fat'] for item in meal['items']) for meal in meals_structure)
        
        return {
            "calories": round(tot_cal),
            "protein": round(tot_pro),
            "carbs": round(tot_carb),
            "fat": round(tot_fat),
            "meals": meals_structure
        }

    def chat_coach(self, user_profile: Dict[str, Any], message: str, memory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Provides AI coach responses with simple local intent parsing as fallback."""
        prompt = f"""
        User Profile: {user_profile}
        Previous Coach memory: {memory}
        User says: "{message}"
        
        Provide a coaching reply. Also, if they mention an injury, liking/disliking an exercise, or modifying their budget/schedule, output a system action you want to take.
        Format reply in JSON:
        {{
          "response": "Coach response content...",
          "actions": ["save_pref:key:value", "modify_workout:exercise"]
        }}
        """
        
        system = "You are GymOS AI Coach, a supportive, scientifically accurate, and motivating coach."
        response_text = self._call_llm(prompt, system)
        
        if response_text:
            try:
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_text)
            except Exception:
                pass

        # --- Fallback Rule-Based Chat Coach ---
        msg = message.lower()
        response = "I hear you! Consistency is the number one driver of progress. Keep logging your sets, and let's make today count."
        actions = []
        
        if "hurt" in msg or "pain" in msg or "injury" in msg:
            response = "Safety first. If you're experiencing pain or joint discomfort, let's substitute that exercise immediately. What exercise or body part is bothering you?"
            actions.append("avoid_exercise")
        elif "time" in msg or "minutes" in msg or "busy" in msg:
            response = "Understood. I can condense today's workout into a high-density, superset-based routine so you can finish in 30 minutes. Should we generate a quick version?"
            actions.append("shorten_workout")
        elif "budget" in msg or "price" in msg or "expensive" in msg:
            response = "Healthy eating doesn't need to be expensive. Let's adjust your meal plan budget to 'Low' and optimize for high-yield, cheap local protein like eggs, soy, and lentils. Shall we update?"
            actions.append("set_low_budget")
        elif "creatine" in msg or "supplement" in msg:
            response = "Creatine Monohydrate is one of the most thoroughly researched supplements in existence. It is highly evidence-backed (Level A) for increasing strength, power output, and muscle cell hydration. Take 3-5g daily at any time."
            
        return {
            "response": response,
            "actions": actions
        }

    def research_science(self, query: str) -> Dict[str, Any]:
        """Science Research Engine: answers questions with level of evidence."""
        prompt = f"""
        Research Query: "{query}"
        Answer scientifically. Detail the evidence level (Strong, Moderate, Weak), detect myths, and suggest references.
        Format reply in JSON:
        {{
          "query": "{query}",
          "summary": "Plain-language summary of research findings...",
          "evidence_level": "Strong/Moderate/Weak",
          "myths_detected": ["Myth 1"],
          "references": ["Study 1"]
        }}
        """
        
        system = "You are a scientific fitness researcher. You cite peer-reviewed literature."
        response_text = self._call_llm(prompt, system)
        
        if response_text:
            try:
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_text)
            except Exception:
                pass
                
        # --- Fallback Science Engine ---
        q = query.lower()
        summary = "Based on current sports medicine literature, progressive overload combined with adequate protein intake (1.6 - 2.2g/kg) represents the primary physiological driver of hypertrophy."
        evidence = "Strong"
        myths = []
        refs = ["Morton et al. (2018) - British Journal of Sports Medicine"]
        
        if "creatine" in q:
            summary = "Creatine monohydrate is a highly evidence-backed supplement that increases phosphocreatine stores in muscles, facilitating faster ATP regeneration during short, explosive exercise. It is safe for long-term use."
            myths = ["Creatine causes kidney damage in healthy individuals", "Creatine causes hair loss"]
            refs = ["Buford et al. (2007) - Journal of the International Society of Sports Nutrition"]
        elif "cardio" in q or "fat loss" in q:
            summary = "Fat loss requires a sustained net calorie deficit. While cardio increases daily energy expenditure, resistance training is critical during a deficit to preserve lean contractile tissue."
            myths = ["Spot-reducing fat from specific areas", "Cardio is mandatory for weight loss"]
            refs = ["Helms et al. (2014) - Journal of the International Society of Sports Nutrition"]
        elif "protein" in q:
            summary = "For active individuals, a protein intake of 1.6 to 2.2 grams per kilogram of body weight is optimal for supporting muscle protein synthesis and recovery."
            myths = ["The body can only absorb 30g of protein per meal", "High protein diets damage healthy kidneys"]
            refs = ["Schoenfeld & Aragon (2018) - Journal of the International Society of Sports Nutrition"]

        return {
            "query": query,
            "summary": summary,
            "evidence_level": evidence,
            "myths_detected": myths,
            "references": refs
        }
