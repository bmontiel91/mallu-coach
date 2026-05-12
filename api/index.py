"""
Mallu Coach - Vercel Serverless API
Replaces server.py for Vercel deployment
"""
import json, os, sys, re, base64, tempfile
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from openai import OpenAI

app = Flask(__name__)

# --- Config from environment ---
SHEET_ID = os.environ.get("SHEET_ID", "1Z0_A6t5o6Nrt9BqVbNiujUAWTpG7Q55mcpR9B_CTQlw")
OPENCODE_KEY = os.environ.get("OPENCODE_KEY", "sk-NLrMQCgHfHEp9m1baJrs7j34yhXgxkg58FLEfZ1pTeEKENMMcu0kDs6zO9XPNLTG")
VISION_MODEL = os.environ.get("VISION_MODEL", "qwen3.5-plus")
GOOGLE_CREDS_B64 = os.environ.get("GOOGLE_CREDS_B64", "")

def get_sheets():
    """Get Google Sheets service. Reads credentials from env var or file."""
    if GOOGLE_CREDS_B64:
        creds_json = base64.b64decode(GOOGLE_CREDS_B64).decode()
        creds = Credentials.from_authorized_user_info(json.loads(creds_json))
    else:
        # Fallback: local file (for development)
        path = "/home/bmont/.hermes/google_token.json"
        if os.path.exists(path):
            with open(path) as f:
                creds = Credentials.from_authorized_user_info(json.load(f))
        else:
            raise Exception("No Google credentials available")
    return build("sheets", "v4", credentials=creds)

# ====== ROUTINES ======
ROUTINES = {
    "espalda_biceps": {
        "nombre": "🐺 Espalda + Bíceps",
        "ejercicios": [
            {"nombre":"Dominadas","sets":2,"opcional":True,"pesos":["BW","+5","+10","+15"]},
            {"nombre":"Remo barra profunda","sets":2,"pesos":["50","60","70","80"]},
            {"nombre":"Remo en T","sets":3,"pesos":["50","60","70","80"]},
            {"nombre":"Remo gironda unilateral","sets":2,"pesos":["15","20","25","30"]},
            {"nombre":"Jalón al pecho","sets":3,"pesos":["40","50","60","70"]},
            {"nombre":"Pull over","sets":2,"pesos":["30","35","40"]},
            {"nombre":"Posterior con cable","sets":3,"pesos":["5","7","10","12"]},
            {"nombre":"Curl bayesiano poleas","sets":3,"pesos":["10","12","15"]},
            {"nombre":"Curl predicador biserie","sets":2,"pesos":["25","30","35"]},
            {"nombre":"Curl Martillo","sets":3,"pesos":["12","15","18","20"]},
            {"nombre":"Antebrazos","sets":2,"opcional":True,"pesos":["20","25","30"]}
        ]
    },
    "piernas1": {
        "nombre": "🦵 Piernas 1",
        "ejercicios": [
            {"nombre":"Aductores","sets":2,"pesos":["30","40","50"]},{"nombre":"Abductores","sets":2,"pesos":["30","40","50"]},
            {"nombre":"Peso muerto rumano mancuernas","sets":2,"pesos":["20","25","30","35"]},
            {"nombre":"Hiperextensiones","sets":2,"pesos":["0","5","10","15"]},{"nombre":"Búlgaras","sets":2,"pesos":["15","20","25","30"]},
            {"nombre":"Hip thrust","sets":2,"pesos":["40","50","60","70"]},{"nombre":"Pantorrillas (x2)","sets":2,"pesos":["40","50","60","70"]},
            {"nombre":"Curl femoral","sets":2,"pesos":["25","30","35","40"]},{"nombre":"Extensión cuádriceps","sets":2,"pesos":["30","40","50"]}
        ]
    },
    "espalda_hombros_brazos": {
        "nombre": "💪 Torso",
        "ejercicios": [
            {"nombre":"Dominadas","sets":2,"pesos":["BW","+5","+10"]},{"nombre":"Remo en T","sets":3,"pesos":["50","60","70"]},
            {"nombre":"Press hammer","sets":3,"pesos":["25","30","35","40"]},{"nombre":"Aperturas máquina","sets":2,"pesos":["20","25","30"]},
            {"nombre":"Remo gironda","sets":1,"pesos":["15","20","25"]},{"nombre":"Jalón al pecho","sets":2,"pesos":["40","50","60"]},
            {"nombre":"Press militar","sets":2,"pesos":["25","30","35"]},{"nombre":"Elevaciones laterales poleas","sets":3,"pesos":["5","7","10"]},
            {"nombre":"Posterior cable","sets":3,"pesos":["5","7","10"]},{"nombre":"Fondos paralelas","sets":1,"pesos":["BW","+5","+10"]},
            {"nombre":"Curl bayesiano/predicador","sets":2,"pesos":["10","12","15"]},{"nombre":"Curl martillo","sets":2,"pesos":["12","15","18"]},
            {"nombre":"Ext. tríceps polea","sets":2,"pesos":["15","20","25"]},{"nombre":"Ext. tríceps tras nuca","sets":2,"pesos":["15","20","25"]},
            {"nombre":"Encogimiento hombros","sets":3,"pesos":["20","25","30","35"]}
        ]
    },
    "piernas2": {
        "nombre": "🦵 Piernas 2",
        "ejercicios": [
            {"nombre":"Aductores","sets":2,"pesos":["30","40","50"]},{"nombre":"Abductores","sets":2,"pesos":["30","40","50"]},
            {"nombre":"Peso muerto rumano","sets":2,"pesos":["40","50","60","70"]},{"nombre":"Sentadilla","sets":3,"pesos":["60","70","80","90"]},
            {"nombre":"Búlgaras/estocadas","sets":2,"pesos":["15","20","25","30"]},{"nombre":"Pantorrillas (x2)","sets":2,"pesos":["40","50","60"]},
            {"nombre":"Curl femoral","sets":2,"pesos":["25","30","35","40"]},{"nombre":"Extensión cuádriceps","sets":2,"pesos":["30","40","50"]}
        ]
    },
    "pecho_hombros_triceps": {
        "nombre": "💪 Pecho+Homb+Tríceps",
        "ejercicios": [
            {"nombre":"Press plano","sets":3,"pesos":["60","70","80","90"]},{"nombre":"Press inclinado Smith","sets":2,"pesos":["50","60","70"]},
            {"nombre":"Aperturas máquina","sets":2,"pesos":["20","25","30"]},{"nombre":"Press militar","sets":2,"pesos":["25","30","35"]},
            {"nombre":"Elevaciones laterales poleas","sets":3,"pesos":["5","7","10"]},{"nombre":"Press cerrado Smith","sets":2,"pesos":["40","50","60"]},
            {"nombre":"Ext. tríceps polea","sets":2,"pesos":["15","20","25"]},{"nombre":"Ext. tríceps tras nuca","sets":2,"pesos":["15","20","25"]},
            {"nombre":"Fondos paralelas","sets":2,"pesos":["BW","+5","+10"]},{"nombre":"Encogimiento hombros","sets":3,"pesos":["20","25","30"]}
        ]
    }
}

# ====== API Routes ======
@app.route("/api/routines")
def api_routines():
    return jsonify(ROUTINES)

@app.route("/api/health")
def api_health():
    try:
        sheets = get_sheets()
        r = sheets.spreadsheets().values().get(spreadsheetId=SHEET_ID, range="Hoja 1!A:F").execute()
        rows = r.get("values", [])
        data = []
        for row in rows[1:]:
            if len(row) >= 2:
                data.append({"date": row[0], "steps": row[1] if len(row)>1 else "0",
                    "sleep": row[2] if len(row)>2 else "0", "hr_avg": row[3] if len(row)>3 else "0",
                    "hr_min": row[4] if len(row)>4 else "0", "hr_max": row[5] if len(row)>5 else "0"})
        return jsonify(data)
    except Exception as e:
        return jsonify([])

@app.route("/api/food")
def api_food():
    try:
        sheets = get_sheets()
        r = sheets.spreadsheets().values().get(spreadsheetId=SHEET_ID, range="Food!A:E").execute()
        rows = r.get("values", [])
        return jsonify(rows[1:] if len(rows) > 1 else [])
    except:
        return jsonify([])

@app.route("/api/workouts")
def api_workouts():
    try:
        sheets = get_sheets()
        r = sheets.spreadsheets().values().get(spreadsheetId=SHEET_ID, range="Workouts!A:G").execute()
        rows = r.get("values", [])
        workouts = []
        for row in rows[1:]:
            if len(row) >= 4:
                workouts.append({"date": row[0], "routine": row[1], "exercise": row[2],
                    "sets": json.loads(row[3]) if len(row)>3 and row[3] else []})
        return jsonify(workouts)
    except:
        return jsonify([])

@app.route("/api/health/save", methods=["POST"])
def api_save_health():
    try:
        data = request.get_json()
        sheets = get_sheets()
        date = data.get("date", datetime.now().strftime("%d/%m/%Y"))
        row = [[date, str(data.get("steps",0)), str(data.get("sleep",0)),
            str(data.get("hr_avg",0)), str(data.get("hr_min",0)), str(data.get("hr_max",0)), "0"]]
        sheets.spreadsheets().values().append(spreadsheetId=SHEET_ID, range="Hoja 1!A:G",
            valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
            body={"values": row}).execute()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/food/save", methods=["POST"])
def api_save_food():
    try:
        data = request.get_json()
        sheets = get_sheets()
        date = data.get("date", datetime.now().strftime("%d/%m/%Y"))
        sheets.spreadsheets().values().append(spreadsheetId=SHEET_ID, range="Food!A:E",
            valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
            body={"values": [[date, data.get("meal",""), data.get("food",""),
                str(data.get("calories",0)), str(data.get("protein",0))]]}).execute()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/workout/save", methods=["POST"])
def api_save_workout():
    return jsonify({"status": "ok"})

@app.route("/api/analyze-image", methods=["POST"])
def api_analyze_image():
    try:
        body = request.get_json()
        img_b64 = body.get("image", "")
        atype = body.get("type", "food")
        date = body.get("date", datetime.now().strftime("%d/%m/%Y"))
        if not img_b64:
            return jsonify({"status":"error","message":"No image"}), 400
        client = OpenAI(api_key=OPENCODE_KEY, base_url="https://opencode.ai/zen/go/v1")
        prompt_health = """Analyze this health screenshot. Return ONLY JSON: {"steps":0,"sleep":0,"hr_avg":0,"hr_min":0,"hr_max":0}."""
        prompt_food = """Analyze this food photo. Return ONLY JSON: {"food":"name","calories":0,"protein":0,"carbs":0,"fat":0,"meal":"desayuno/almuerzo/snack/cena"}. Be realistic."""
        prompt = prompt_health if atype == "health" else prompt_food
        resp = client.chat.completions.create(model=VISION_MODEL,
            messages=[{"role":"system","content":"You extract data from images. Return ONLY valid JSON."},
                {"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{img_b64}","detail":"high"}}]}],
            max_tokens=600, temperature=0.1)
        text = resp.choices[0].message.content
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if not m:
            return jsonify({"status":"error","message":"Could not parse vision result"}), 500
        result = json.loads(m.group())
        sheets = get_sheets()
        if atype == "health":
            sheets.spreadsheets().values().append(spreadsheetId=SHEET_ID, range="Hoja 1!A:G",
                valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                body={"values":[[date,str(result.get("steps",0)),str(result.get("sleep",0)),
                    str(result.get("hr_avg",0)),str(result.get("hr_min",0)),str(result.get("hr_max",0)),"0"]]}).execute()
            return jsonify({"status":"ok","type":"health","data":result,
                "message":f"✅ Pasos: {result.get('steps','?')} | Sueño: {result.get('sleep','?')}h | FC: {result.get('hr_avg','?')}"})
        else:
            sheets.spreadsheets().values().append(spreadsheetId=SHEET_ID, range="Food!A:E",
                valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                body={"values":[[date,result.get("meal","snack"),result.get("food","Comida"),
                    str(result.get("calories",0)),str(result.get("protein",0))]]}).execute()
            return jsonify({"status":"ok","type":"food","data":result,
                "message":f"✅ {result.get('food','?')} — {result.get('calories','?')} kcal | {result.get('protein','?')}g prot"})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# Serve index.html for root path
@app.route("/")
def serve_index():
    return send_from_directory("..", "index.html")

# ====== Vercel handler ======
# Vercel expects a WSGI app called 'app' - it's already defined above
