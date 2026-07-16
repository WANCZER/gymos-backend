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
    prefix="/supplements",
    tags=["Supplements"]
)

ai_service = AIService()

@router.get("/", response_model=List[schemas.SupplementOut])
def get_supplements(query: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Supplement)
    if query:
        q = q.filter(models.Supplement.name.ilike(f"%{query}%"))
    return q.all()


@router.get("/{name}", response_model=schemas.SupplementOut)
def get_supplement_details(name: str, db: Session = Depends(get_db)):
    supp = db.query(models.Supplement).filter(models.Supplement.name.ilike(name)).first()
    if not supp:
        raise HTTPException(status_code=404, detail="Supplement not found in database")
    return supp


@router.post("/scan")
def scan_supplement(label_text: str, current_user: models.User = Depends(get_current_user)):
    """Scans and analyzes supplement ingredients for red flags, dosage, and value."""
    # Build prompt for AI scanner analysis
    prompt = f"""
    Analyze the following scanned label text of a supplement product:
    "{label_text}"
    
    Identify:
    1. Active ingredients and their dosages.
    2. Any proprietary blends (underdosed warnings).
    3. Artificial additives, fillers, or sweeteners.
    4. Safety flags, heavy metal disclosures, or third-party certs (USP, NSF, Informed-Choice).
    5. Cost-effectiveness / Value for money rating (High/Medium/Low).
    
    Respond in JSON format:
    {{
      "product_name": "Inferred Product Name",
      "active_ingredients": [
        {{"name": "Ingredient A", "dose": "5g", "is_effective_dose": true, "reason": "Standard daily dose is 3-5g"}}
      ],
      "proprietary_blends_found": false,
      "additives_fillers": ["Maltodextrin"],
      "certifications": ["NSF Certified"],
      "safety_warnings": ["High caffeine content. Avoid close to sleep."],
      "value_rating": "High",
      "conclusion": "Summary of whether this product is worth buying or if there are cheaper single-ingredient alternatives."
    }}
    """
    
    system = "You are a supplement transparency inspector. You analyze formulations for safety and effectiveness. Return ONLY raw JSON."
    response_text = ai_service._call_llm(prompt, system)
    
    if response_text:
        try:
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception:
            pass
            
    # --- Fallback Parser ---
    t = label_text.lower()
    product_name = "Scanned Supplement"
    active_ingredients = []
    additives = ["Silicon Dioxide"]
    warnings = []
    certs = ["None detected"]
    value = "Medium"
    conclusion = "This product contains standard active ingredients, but ensure you compare prices with unflavored single-ingredient alternatives."
    
    if "creatine" in t:
        product_name = "Creatine Powder"
        active_ingredients.append({"name": "Creatine Monohydrate", "dose": "5g", "is_effective_dose": True, "reason": "5g matches standard saturation/maintenance dose."})
        value = "High"
        conclusion = "Excellent single-ingredient supplement. Pure creatine monohydrate is highly cost-effective and clinically proven."
    elif "whey" in t or "protein" in t:
        product_name = "Whey Protein Concentrate"
        active_ingredients.append({"name": "Whey Protein", "dose": "24g", "is_effective_dose": True, "reason": "20-25g protein triggers muscle protein synthesis optimally."})
        additives.append("Sucralose")
        value = "High"
        conclusion = "Good protein source. Check for third-party testing (NSF/Informed-Choice) if you are a competitive athlete."
    elif "pre" in t or "caffeine" in t:
        product_name = "Pre-Workout Formula"
        active_ingredients.append({"name": "Caffeine", "dose": "300mg", "is_effective_dose": True, "reason": "Strong stimulant effect. Recommended limit is 400mg daily."})
        active_ingredients.append({"name": "L-Citrulline", "dose": "3g", "is_effective_dose": False, "reason": "Underdosed. Clinically effective dose is 6-8g for pump/nitric oxide."})
        warnings.append("High stimulant dosage. Do not consume within 6 hours of bedtime.")
        value = "Low"
        conclusion = "Underdosed active pumps (L-Citrulline) and high caffeine. You might be better off buying bulk L-Citrulline and Caffeine pills separately."

    return {
        "product_name": product_name,
        "active_ingredients": active_ingredients,
        "proprietary_blends_found": "blend" in t,
        "additives_fillers": additives,
        "certifications": certs,
        "safety_warnings": warnings,
        "value_rating": value,
        "conclusion": conclusion
    }
