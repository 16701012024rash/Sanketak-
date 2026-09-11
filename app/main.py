from fastapi import FastAPI
from app.routers import reports

app = FastAPI(title="Sanketak API")
app.include_router(reports.router)

@app.get("/health")
def health():
    return {"status": "ok"}