from fastapi import FastAPI
from app.routers import reports, risk_radar, patterns, precedents, actions, auth

app = FastAPI(title="Sanketak API")
app.include_router(reports.router)
app.include_router(risk_radar.router)
app.include_router(patterns.router)
app.include_router(precedents.router)
app.include_router(actions.router)
app.include_router(auth.router)

@app.get("/health")
def health():
    return {"status": "ok"}