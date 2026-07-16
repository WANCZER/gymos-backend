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
    prefix="/coach",
    tags=["AI Coach"]
)

ai_service = AIService()

@router.post("/chat", response_model=schemas.ChatResponse)
def coach_chat(chat_req: schemas.ChatRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Fetch user memories
    db_memories = db.query(models.AICoachMemory).filter(models.AICoachMemory.user_id == current_user.id).all()
    memory_list = [{"key": m.key, "value": m.value} for m in db_memories]
    
    user_dict = {
        "email": current_user.email,
        "name": current_user.name,
        "age": current_user.age,
        "goal": current_user.primary_goal,
        "equipment": current_user.available_equipment,
        "injuries": current_user.injuries,
        "budget": current_user.diet_budget,
        "diet": current_user.diet_preference
    }
    
    # 2. Get coach response
    coach_data = ai_service.chat_coach(user_dict, chat_req.message, memory_list)
    
    # 3. Parse actions (e.g. save preference to memory)
    actions = coach_data.get("actions", [])
    for action in actions:
        if action.startswith("save_pref:"):
            parts = action.split(":", 2)
            if len(parts) == 3:
                key, value = parts[1], parts[2]
                # Check if memory already exists
                existing = db.query(models.AICoachMemory).filter(
                    models.AICoachMemory.user_id == current_user.id,
                    models.AICoachMemory.key == key
                ).first()
                if existing:
                    existing.value = value
                else:
                    new_mem = models.AICoachMemory(user_id=current_user.id, key=key, value=value)
                    db.add(new_mem)
                db.commit()
                
    return schemas.ChatResponse(
        response=coach_data["response"],
        actions=actions
    )


@router.get("/memory", response_model=List[schemas.AICoachMemoryOut])
def get_coach_memories(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.AICoachMemory).filter(models.AICoachMemory.user_id == current_user.id).all()


@router.delete("/memory/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coach_memory(memory_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    mem = db.query(models.AICoachMemory).filter(
        models.AICoachMemory.id == memory_id,
        models.AICoachMemory.user_id == current_user.id
    ).first()
    
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    db.delete(mem)
    db.commit()
    return


@router.post("/research", response_model=schemas.ResearchResponse)
def research_query(req: schemas.ResearchRequest):
    data = ai_service.research_science(req.query)
    return schemas.ResearchResponse(
        query=data["query"],
        summary=data["summary"],
        evidence_level=data["evidence_level"],
        myths_detected=data["myths_detected"],
        references=data["references"]
    )
