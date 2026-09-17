from fastapi import FastAPI

app = FastAPI(title="Python backend")


@app.get("/api/hello")
def hello() -> dict[str, str]:
    return {"message": "hello"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

