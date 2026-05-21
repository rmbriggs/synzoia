"""Vercel entrypoint. The real FastAPI app lives in backend/app/main.py;
this shim only exists so Vercel's @vercel/python builder finds an ASGI
`app` object at the conventional location."""

from backend.app.main import app  # noqa: F401
