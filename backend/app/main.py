from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="Baze University Exam Scheduler API",
    description="Adaptive Exam Timetabling System for Baze University",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Baze University Exam Scheduler API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "backend"}

@app.get("/api/v1/test")
async def test_endpoint():
    return {
        "message": "Backend is running successfully!",
        "test": "passed"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)