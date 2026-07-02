from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/")
def root():
    return FileResponse("landing.html")
