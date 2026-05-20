from fastapi import FastAPI

app = FastAPI(title="synzoia")


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}
