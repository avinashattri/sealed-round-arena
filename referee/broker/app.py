from fastapi import FastAPI

from contracts.messages import Receipt, Submit

app = FastAPI(title="Sealed Round Arena - Broker")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/submit", response_model=Receipt)
def submit(req: Submit):
    # Minimal schema validation and acknowledgement
    return Receipt(challenge_id=req.challenge_id, status="accepted")
