from fastapi import FastAPI


app = FastAPI(title="AI Transition Day 1 Demo")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "day": 1,
        "topic": "positioning-and-environment-setup",
    }
