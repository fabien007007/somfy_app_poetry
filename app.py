from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
import re
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# On configure l'API en forçant le transport REST pour éviter l'erreur v1beta/404
genai.configure(api_key=GEMINI_API_KEY, transport='rest')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LOGIQUE GEMINI ---

def prepare_image_for_gemini(image_bytes):
    try:
        img = Image.open(BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((800, 800))
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        return {"mime_type": "image/jpeg", "data": buffer.getvalue()}
    except Exception:
        return None

def call_gemini_vision(prompt: str, image_data=None) -> str:
    if not GEMINI_API_KEY:
        return "❌ Clé API GEMINI_API_KEY manquante dans Render."
    try:
        # Utilisation du nom de modèle le plus stable
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        content = [prompt]
        if image_data:
            content.append(image_data)
            
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        return f"⚙️ Erreur technique : {str(e)}"

def format_html_output(text: str) -> str:
    clean = text.replace("**", "").replace("###", "##")
    sections = re.split(r'##', clean)
    html_res = ""
    for s in sections:
        content = s.strip()
        if not content: continue
        lines = content.split('\n')
        title = lines[0].strip().replace(':', '')
        body = "<br>".join(lines[1:]).strip()
        icon, css, tag = "⚙️", "diag-section", "INFO"
        if "Identification" in title: icon, tag = "🆔", "ID"
        elif "Sécurité" in title: icon, tag, css = "⚠️", "SÉCURITÉ", "diag-section s-secu"
        elif "Test" in title: icon, tag = "🔍", "TEST"
        elif "Correction" in title: icon, tag = "🛠️", "FIX"
        html_res += f"<div class='{css}'><div class='section-header'><span class='tag'>{tag}</span> {icon} {title}</div><div class='section-body'>{body}</div></div>"
    return html_res

# --- ROUTES ---

@app.post("/diagnostic")
async def diagnostic(image: UploadFile = File(None), panne_description: str = Form("")):
    img_payload = None
    if image and image.filename:
        raw_data = await image.read()
        img_payload = prepare_image_for_gemini(raw_data)
    
    prompt = f"Expert Somfy. Analyse : {panne_description}. Si photo : identifie modèle et fils. Format strict : ## Identification ## Sécurité ## Tests ## Correction"
    
    raw_text = call_gemini_vision(prompt, img_payload)
    return HTMLResponse(content=format_html_output(raw_text))

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Somfy Expert AI</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #f4f7f6; padding: 15px; margin: 0; }
        .card { background: white; max-width: 500px; margin: auto; padding: 20px; border-radius: 20px; box-shadow: 0 8px 20px rgba(0,0,0,0.05); }
        h1 { color: #667eea; text-align: center; font-size: 1.4rem; }
        .diag-section { background: #fff; border: 1px solid #eee; border-radius: 12px; margin-top: 15px; overflow: hidden; border-left: 5px solid #667eea; }
        .s-secu { border-left-color: #ff4d4d; }
        .section-header { background: #f9f9f9; padding: 10px 15px; font-weight: bold; display: flex; align-items: center; gap: 8px; }
        .tag { background: #667eea; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; }
        .section-body { padding: 15px; line-height: 1.5; font-size: 0.95rem; color: #444; }
        .btn { width: 100%; padding: 15px; margin: 8px 0; border: none; border-radius: 12px; cursor: pointer; font-weight: bold; font-size: 1rem; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .btn-photo { background: #f0f2f5; color: #555; border: 1px dashed #ccc; }
        .btn-main { background: #667eea; color: white; margin-top: 15px; }
        .btn-share { background: #25d366; color: white; display: none; }
