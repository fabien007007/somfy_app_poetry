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

# Configuration stable : on force le transport 'rest' pour éviter l'erreur 404/v1beta
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
    if not GEMINI_API_KEY: return "❌ Clé API manquante."
    try:
        # On repasse sur 1.5-flash qui a un quota plus élevé en gratuit
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        content = [prompt]
        if image_data: content.append(image_data)
        
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        # Si le quota est encore bloqué, on affiche un message clair
        if "429" in str(e):
            return "⏳ Limite de requêtes atteinte. Réessayez dans 1 minute."
        return f"⚙️ Erreur : {str(e)}"

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
    
    prompt = f"Tu es l'expert technique Somfy. Analyse : {panne_description}. Format : ## Identification ## Sécurité ## Tests ## Correction"
    
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
        .btn-reset { background: #f8fafc; color: #64748b; border: 1px solid #e2e8f0; display: none; margin-top: 10px; }
        .input-box { position: relative; margin-top: 10px; }
        textarea { width: 100%; height: 100px; border-radius: 12px; border: 1px solid #ddd; padding: 12px; font-size: 1rem; box-sizing: border-box; }
        .mic { position: absolute; right: 10px; bottom: 12px; border: none; background: #f0f2f5; padding: 10px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; }
        .mic-on { background: #ff4d4d; color: white; animation: pulse 1s infinite; }
        @keyframes pulse { 0% {opacity: 1} 50% {opacity: 0.6} 100% {opacity: 1} }
        #preview { width: 100%; border-radius: 12px; display: none; margin-bottom: 15px; }
        #loading { display: none; text-align: center; margin: 15px; color: #667eea; font-weight: bold; }
    </style>
</head>
<body>
<div class="card">
    <h1>Somfy Expert AI</h1>
    <img id="preview">
    <button class="btn btn-photo" onclick="document.getElementById('in').click()">📸 Photo de l'équipement</button>
    <input type="file" id="in" accept="image/*" capture="environment" hidden onchange="pv(this)">
    <div class="input-box">
        <textarea id="desc" placeholder="Décrivez la panne..."></textarea>
        <button id="m" class="mic" onclick="tk()">🎙️</button>
    </div>
    <button id="go" class="btn btn-main" onclick="run()">⚡ Lancer le Diagnostic</button>
    <button id="sh" class="btn btn-share" onclick="share()">📤 Partager le Diagnostic</button>
    <button id="rs" class="btn btn-reset" onclick="resetAll()">🔄 Nouveau Diagnostic</button>
    <div id="loading">⏳ Analyse en cours...</div>
    <div id="result"></div>
</div>
<script>
let file = null; let rec = null;
window.onload = () => {
    const savedResult = localStorage.getItem('lastDiag');
    if (savedResult) {
        document.getElementById('result').innerHTML = savedResult;
        document.getElementById('sh').style.display = 'flex';
        document.getElementById('rs').style.display = 'flex';
    }
};
function pv(i) {
    if (i.files[0]) {
        file = i.files[0];
        const r = new FileReader();
        r.onload = (e) => { const p = document.getElementById('preview'); p.src = e.target.result; p.style.display = 'block'; };
        r.readAsDataURL(file);
    }
}
function tk() {
    const S = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!S) return alert("Micro non supporté");
    if (!rec) {
        rec = new S(); rec.lang = 'fr-FR';
        rec.onresult = (e) => { document.getElementById('desc').value += " " + e.results[0][0].transcript; };
        rec.onstart = () => document.getElementById('m').classList.add('mic-on');
        rec.onend = () => document.getElementById('m').classList.remove('mic-on');
    }
    try { rec.start(); } catch(e) { rec.stop(); }
}
async function run() {
    const res = document.getElementById('result');
    const load = document.getElementById('loading');
    const go = document.getElementById('go');
    go.disabled = true; load.style.display = 'block'; res.innerHTML = "";
    const fd = new FormData();
    if (file) fd.append('image', file);
    fd.append('panne_description', document.getElementById('desc').value);
    try {
        const r = await fetch('/diagnostic', { method: 'POST', body: fd });
        const htmlText = await r.text();
        res.innerHTML = htmlText;
        localStorage.setItem('lastDiag', htmlText);
        document.getElementById('sh').style.display = 'flex';
        document.getElementById('rs').style.display = 'flex';
    } catch (e) { alert("Erreur de connexion"); } 
    finally { load.style.display = 'none'; go.disabled = false; }
}
function resetAll() {
    if(confirm("Effacer pour un nouveau diagnostic ?")) {
        localStorage.removeItem('lastDiag');
        location.reload();
    }
}
function share() {
    const t = document.getElementById('result').innerText;
    if (navigator.share) { navigator.share({ title: 'Diagnostic Somfy', text: t }); }
    else { navigator.clipboard.writeText(t); alert("Copié dans le presse-papier !"); }
}
</script>
</body>
</html>"""





