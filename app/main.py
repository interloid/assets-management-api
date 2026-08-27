from fastapi import FastAPI


app = FastAPI()


@app.get("/")
def home():
    return{
        "message":"This is Assets Management System"
    }