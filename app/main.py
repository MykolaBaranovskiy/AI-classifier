import json
import io
import os
import pandas as pd
 
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
 
from .classifier import classify_all
from .reporter import generate_report
from .schemas import RequestResult
 
OUTPUT_JSON_PATH = "output.json"
REPORT_MD_PATH = "report.md"

app = FastAPI()

@app.get("/health")
async def health():
    return {"health": "ok"}

@app.post("/classify", response_model=list[RequestResult])
async def classify(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")
 
    contents = await file.read()
 
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")
 
    required_columns = {"id", "channel", "timestamp", "raw_text"}
    missing = required_columns - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns: {missing}",
        )
 
    rows = df.to_dict(orient="records")
    results: list[RequestResult] = await classify_all(rows)
 
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(
            [r.model_dump() for r in results],
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
 
    report_md = generate_report(results)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)
 
    return results
 
 
@app.get("/results")
async def get_results():
    if not os.path.exists(OUTPUT_JSON_PATH):
        raise HTTPException(
            status_code=404,
            detail="No results yet. Please POST a CSV to /classify first.",
        )
    return FileResponse(OUTPUT_JSON_PATH, media_type="application/json", filename="output.json")
 
 
@app.get("/report")
async def get_report():
    if not os.path.exists(REPORT_MD_PATH):
        raise HTTPException(
            status_code=404,
            detail="No report yet. Please POST a CSV to /classify first.",
        )
    return FileResponse(REPORT_MD_PATH, media_type="text/markdown", filename="report.md")