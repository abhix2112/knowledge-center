from fastapi import FastAPI

app = FastAPI(title="Knowledge Center")


@app.get("/health")
def health_check()-> dict[str, str]:
    return {"status": "ok"}

