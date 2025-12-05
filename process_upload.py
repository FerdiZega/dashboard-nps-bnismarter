import polars as pl
from fastapi import FastAPI, File, UploadFile
from sqlalchemy import create_engine
import pandas as pd

DB_URL = "postgresql://postgres:password@host:5432/postgres"
engine = create_engine(DB_URL)

app = FastAPI()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    df = pl.read_csv(file.file) if file.filename.endswith(".csv") else pl.read_excel(file.file)

    df = df.rename({
        "person_id": "person_id",
        "nama": "nama",
        "kategori": "kategori",
        "skor_nps": "skor_nps"
    })

    for i in range(0, len(df), 200000):  # chunk saving
        df[i:i+200000].to_pandas().to_sql("nps_data", engine, index=False, if_exists="append")

    return {"status": "success", "rows_uploaded": len(df)}
