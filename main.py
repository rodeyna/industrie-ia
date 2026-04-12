from fastapi import FastAPI

app = FastAPI(title="INDUSTRIE IA")

@app.get("/")
def home():
    return {"status": "INDUSTRIE IA is running"}