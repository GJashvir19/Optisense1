from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib, pandas as pd
import io
import os
import numpy as np
import tensorflow as tf
from PIL import Image
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="OptiSense API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

model = joblib.load("../models/risk_model.pkl")
COLS = joblib.load("../models/feature_columns.pkl")
damage_model = tf.keras.models.load_model("../models/damage_model_v2.keras")

class RiskInput(BaseModel):
    rainfall: float
    river_discharge: float
    water_level: float
    elevation: float
    historical_floods: int

def level(score: float) -> str:
    if score < 33: return "LOW"
    if score < 66: return "MEDIUM"
    return "HIGH"

@app.get("/health")
def root():
    return {"status": "OptiSense API running"}

@app.post("/predict-risk")
def predict_risk(d: RiskInput):
    row = pd.DataFrame([[d.rainfall, d.river_discharge, d.water_level,
                         d.elevation, d.historical_floods]], columns=COLS)
    score = float(model.predict(row)[0])
    return {"risk_score": round(score, 1), "risk_level": level(score)}

class Reading(BaseModel):
    rainfall: float
    river_discharge: float
    water_level: float

class WarningInput(BaseModel):
    readings: list[Reading]
    elevation: float
    historical_floods: int

@app.post("/early-warning")
def early_warning(d: WarningInput):
    rows = [[r.rainfall, r.river_discharge, r.water_level,
             d.elevation, d.historical_floods] for r in d.readings]
    scores = [float(s) for s in model.predict(pd.DataFrame(rows, columns=COLS))]

    recent = scores[-3:]
    slope = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
    forecast = max(0.0, min(100.0, scores[-1] + slope * 3))
    trend = "RISING" if slope > 2 else "FALLING" if slope < -2 else "STEADY"
    flevel = level(forecast)

    if flevel == "HIGH" and trend == "RISING":
        alert, msg = "🚨 FLOOD WARNING", "Risk is climbing and is forecast to reach HIGH within 3 hours. Prepare response now."
    elif flevel == "HIGH":
        alert, msg = "⚠️ HIGH RISK", "Risk is high but no longer rising. Keep monitoring."
    elif trend == "RISING":
        alert, msg = "⚠️ WATCH", "Risk is rising. Keep a close eye on rainfall and river levels."
    else:
        alert, msg = "✅ ALL CLEAR", "No significant flood risk expected in the next 3 hours."

    return {"scores": [round(s, 1) for s in scores], "forecast": round(forecast, 1),
            "forecast_level": flevel, "trend": trend, "alert": alert, "message": msg}

@app.post("/predict-damage")
async def predict_damage(file: UploadFile = File(...)):
    img = Image.open(io.BytesIO(await file.read())).convert("RGB").resize((128, 128))
    x = np.array(img, dtype="float32")[None, ...]   # no /255, the model rescales itself
    p_no_damage = float(damage_model.predict(x, verbose=0)[0][0])
    return {
        "label": "no_damage" if p_no_damage > 0.5 else "damage",
        "damage": round(1 - p_no_damage, 4),
        "no_damage": round(p_no_damage, 4),
    }

# Serve the website from the same server. Keep this at the very end of the file.
FRONT = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=FRONT, html=True), name="frontend")