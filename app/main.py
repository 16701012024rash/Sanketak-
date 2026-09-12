from fastapi import FastAPI
from app.routers import reports, risk_radar, patterns, precedents, actions, auth, analyse

app = FastAPI(
    title="Sanketak API",
    description="Backend for Sanketak — an anonymous, multilingual worker safety reporting "
                "system with AI-powered risk analysis, historical disaster precedent matching, "
                "and pattern detection. Built for OIL's HSE team, fully self-hosted with no "
                "external cloud AI dependencies.",
    version="1.0.0",
)
app.include_router(reports.router)
app.include_router(risk_radar.router)
app.include_router(patterns.router)
app.include_router(precedents.router)
app.include_router(actions.router)
app.include_router(auth.router)
app.include_router(analyse.router)

@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Simple liveness check to confirm the API is running.",
)
def health():
    return {"status": "ok"}