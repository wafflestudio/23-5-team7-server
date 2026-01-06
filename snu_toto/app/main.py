from fastapi import FastAPI

app = FastAPI(
    title="SNU Toto API",
    version="1.0.0",
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Hello World from SNU Toto API"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
