import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import WorkInstruction, Step

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilities to handle ObjectId in responses
class WIResponse(BaseModel):
    id: str
    title: str

class WIDetailResponse(BaseModel):
    id: str
    title: str
    steps: List[Step]

@app.get("/")
def read_root():
    return {"message": "Work Instructions API running"}

@app.get("/api/instructions", response_model=List[WIResponse])
def list_instructions():
    items = get_documents("workinstruction", {})
    result = []
    for it in items:
        result.append(WIResponse(id=str(it.get("_id")), title=it.get("title", "Untitled")))
    return result

@app.post("/api/instructions", response_model=WIResponse)
def create_instruction(payload: WorkInstruction):
    # Ensure steps have sequential order values
    steps_sorted = sorted(payload.steps, key=lambda s: s.order)
    normalized_steps = [Step(title=s.title, description=s.description, order=i) for i, s in enumerate(steps_sorted)]
    doc = {"title": payload.title, "steps": [s.model_dump() for s in normalized_steps]}
    new_id = create_document("workinstruction", doc)
    return WIResponse(id=new_id, title=payload.title)

@app.get("/api/instructions/{wi_id}", response_model=WIDetailResponse)
def get_instruction(wi_id: str):
    try:
        oid = ObjectId(wi_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    docs = get_documents("workinstruction", {"_id": oid}, limit=1)
    if not docs:
        raise HTTPException(status_code=404, detail="Not found")
    doc = docs[0]
    steps = [Step(**s) for s in doc.get("steps", [])]
    return WIDetailResponse(id=str(doc.get("_id")), title=doc.get("title", "Untitled"), steps=steps)

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
