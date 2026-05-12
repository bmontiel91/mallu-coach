#!/usr/bin/env python3
"""
Mallu Coach - Backend Server
Production version for Render + GitHub Pages
"""
import json, os, sys, re, base64, urllib.parse, socketserver
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from openai import OpenAI

TOKEN_PATH = "/home/bmont/.hermes/google_token.json"
SHEET_ID = "1Z0_A6t5o6Nrt9BqVbNiujUAWTpG7Q55mcpR9B_CTQlw"
SHEET_NAME = "Hoja 1"
OPENCODE_KEY = "sk-NLrMQCgHfHEp9m1baJrs7j34yhXgxkg58FLEfZ1pTeEKENMMcu0kDs6zO9XPNLTG"
VISION_MODEL = "qwen3.5-plus"
FRONTEND_PATH = Path(__file__).parent / "index.html"

# CORS: allow GitHub Pages frontend
ALLOWED_ORIGINS = [
    "https://bmontiel91.github.io",
    "http://localhost:8080",
    "http://localhost:3000",
]

def get_sheets():
    with open(TOKEN_PATH) as f:
        creds = Credentials.from_authorized_user_info(json.load(f))
    return build("sheets", "v4", credentials=creds)

class CoachHandler(BaseHTTPRequestHandler):
    def set_cors(self):
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS or not origin:
            self.send_header("Access-Control-Allow-Origin", origin or "*")
        else:
            self.send_header("Access-Control-Allow-Origin", "https://bmontiel91.github.io")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self.set_cors()
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            self.serve_frontend()
        elif path == "/api/health":
            self.serve_health_data()
        elif path == "/api/routines":
            self.serve_routines()
        elif path == "/api/workouts":
            self.serve_workouts()
        elif path == "/api/food":
            self.serve_food()
        else:
            self.send_error(404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        cl = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(cl)) if cl else {}
        if path == "/api/workout/save":
            self.save_workout(body)
        elif path == "/api/food/save":
            self.save_food(body)
        elif path == "/api/health/save":
            self.save_health(body)
        elif path == "/api/analyze-image":
            self.analyze_image(body)
        else:
            self.send_error(404)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.set_cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def serve_frontend(self):
        if FRONTEND_PATH.exists():
            self.send_response(200)
            self.set_cors()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(FRONTEND_PATH.read_bytes())
        else:
            self.send_json({"error": "Frontend not found"}, 500)

    def serve_routines(self):
        routines = {
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
        self.send_json(routines)

    def serve_workouts(self):
        try:
            sheets = get_sheets()
            r = sheets.spreadsheets().values().get(spreadsheetId=SHEET_ID, range="Workouts!A:G").execute()
            rows = r.get("values", [])
            workouts = []
            for row in rows[1:]:
                if len(row) >= 4:
                    workouts.append({"date": row[0], "routine": row[1], "exercise": row[2],
                        "sets": json.loads(row[3]) if len(row)>3 and row[3] else []})
            self.send_json(workouts)
        except:
            self.send_json([])

    def save_workout(self, data):
        try:
            sheets = get_sheets()
            date = data.get("date", datetime.now().strftime("%d/%m/%Y"))
            self.send_json({"status": "ok"})
        except Exception as e:
            self.send_json({"status": "error", "message": str(e)}, 500)

    def serve_health_data(self):
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
            self.send_json(data)
        except:
            self.send_json([])

    def save_health(self, data):
        try:
            sheets = get_sheets()
            date = data.get("date", datetime.now().strftime("%d/%m/%Y"))
            row = [[date, str(data.get("steps",0)), str(data.get("sleep",0)),
                str(data.get("hr_avg",0)), str(data.get("hr_min",0)), str(data.get("hr_max",0)), "0"]]
            sheets.spreadsheets().values().append(spreadsheetId=SHEET_ID, range="Hoja 1!A:G",
                valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                body={"values": row}).execute()
            self.send_json({"status": "ok"})
        except Exception as e:
            self.send_json({"status": "error", "message": str(e)}, 500)

    def serve_food(self):
        try:
            sheets = get_sheets()
            r = sheets.spreadsheets().values().get(spreadsheetId=SHEET_ID, range="Food!A:E").execute()
            rows = r.get("values", [])
            self.send_json(rows[1:] if len(rows) > 1 else [])
        except:
            self.send_json([])

    def save_food(self, data):
        try:
            sheets = get_sheets()
            date = data.get("date", datetime.now().strftime("%d/%m/%Y"))
            sheets.spreadsheets().values().append(spreadsheetId=SHEET_ID, range="Food!A:E",
                valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                body={"values": [[date, data.get("meal",""), data.get("food",""),
                    str(data.get("calories",0)), str(data.get("protein",0))]]}).execute()
            self.send_json({"status": "ok"})
        except Exception as e:
            self.send_json({"status": "error", "message": str(e)}, 500)

    def analyze_image(self, body):
        try:
            img_b64 = body.get("image", "")
            atype = body.get("type", "food")
            date = body.get("date", datetime.now().strftime("%d/%m/%Y"))
            if not img_b64:
                self.send_json({"status":"error","message":"No image"}, 400)
                return
            client = OpenAI(api_key=OPENCODE_KEY, base_url="https://opencode.ai/zen/go/v1")
            if atype == "health":
                prompt = """Analyze this health screenshot. Return ONLY JSON: {"steps":0,"sleep":0,"hr_avg":0,"hr_min":0,"hr_max":0}."""
            else:
                prompt = """Analyze this food photo. Return ONLY JSON: {"food":"name","calories":0,"protein":0,"carbs":0,"fat":0,"meal":"desayuno/almuerzo/snack/cena"}. Be realistic."""
            resp = client.chat.completions.create(model=VISION_MODEL,
                messages=[{"role":"system","content":"You extract data from images. Return ONLY valid JSON."},
                    {"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{img_b64}","detail":"high"}}]}],
                max_tokens=600, temperature=0.1)
            text = resp.choices[0].message.content
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if not m:
                self.send_json({"status":"error","message":"Could not parse vision result"}, 500)
                return
            result = json.loads(m.group())
            sheets = get_sheets()
            if atype == "health":
                sheets.spreadsheets().values().append(spreadsheetId=SHEET_ID, range="Hoja 1!A:G",
                    valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                    body={"values":[[date,str(result.get("steps",0)),str(result.get("sleep",0)),
                        str(result.get("hr_avg",0)),str(result.get("hr_min",0)),str(result.get("hr_max",0)),"0"]]}).execute()
                self.send_json({"status":"ok","type":"health","data":result,
                    "message":f"✅ Pasos: {result.get('steps','?')} | Sueño: {result.get('sleep','?')}h | FC: {result.get('hr_avg','?')}"})
            else:
                sheets.spreadsheets().values().append(spreadsheetId=SHEET_ID, range="Food!A:E",
                    valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                    body={"values":[[date,result.get("meal","snack"),result.get("food","Comida"),
                        str(result.get("calories",0)),str(result.get("protein",0))]]}).execute()
                self.send_json({"status":"ok","type":"food","data":result,
                    "message":f"✅ {result.get('food','?')} — {result.get('calories','?')} kcal | {result.get('protein','?')}g prot"})
        except Exception as e:
            self.send_json({"status":"error","message":str(e)}, 500)

    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

class ThreadedServer(socketserver.ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadedServer(("0.0.0.0", port), CoachHandler)
    print(f"🚀 Mallu Coach on http://0.0.0.0:{port}")
    print(f"   Vision: {VISION_MODEL} | Sheets: {SHEET_ID[:12]}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
