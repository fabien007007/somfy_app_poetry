import os
import re
import base64
from io import BytesIO
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# Importation de ta base de données Somfy
try:
    import somfy_database
    # On s'assure que la base est chargée en texte brut pour l'IA
    BASE_TECHNIQUE = str(somfy_database.SOMFY_PRODUCTS)
except Exception:
    BASE_TECHNIQUE = "Base de données non accessible."

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_html_output(text: str) -> str:
    """Structure la réponse en blocs visuels propres."""
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

@app.post("/diagnostic")
async def diagnostic(image: UploadFile = File(None), panne_description: str = Form("")):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return HTMLResponse(content="Erreur : Configuration API manquante.")
    
    client = Groq(api_key=api_key)
    
    # SYSTEM PROMPT : On définit ici l'expertise
    system_instruction = f"""Tu es l'Expert Technique Somfy n°1. 
    TA SOURCE DE VÉRITÉ EST CETTE BASE : {BASE_TECHNIQUE}
    
    RÈGLES STRICTES :
    1. Regarde la photo pour identifier le modèle (ex: Centralis, Soliris, Animeo).
    2. Cherche TOUJOURS les procédures de test et câblage exacts dans la BASE fournie.
    3. Si tu vois '1810392' ou '1822039', utilise les données spécifiques à ces références.
    4. Réponds UNIQUEMENT avec ce format : ## Identification ## Sécurité ## Tests ## Correction"""

    content = [{"type": "text", "text": system_instruction}]
    content.append({"type": "text", "text": f"Panne décrite par le technicien : {panne_description}"})

    if image and image.filename:
        img_data = await image.read()
        img_b64 = base64.b64encode(img_data).decode('utf-8')
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
        })

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": content}],
            model="meta-llama/llama-4-scout-17b-16e-instruct", # Modèle Production Stable
            temperature=0.2 # On baisse la température pour plus de précision technique
        )
        raw_text = chat_completion.choices[0].message.content
    except Exception as e:
        raw_text = f"## Identification ## Erreur \n{str(e)}"
    
    return HTMLResponse(content=format_html_output(raw_text))

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Somfy Expert - Vision & Micro</title>
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
        .input-box { position: relative; margin-top: 10px; }
        textarea { width: 100%; height: 100px; border-radius: 12px; border: 1px solid #ddd; padding: 12px; font-size: 1rem; box-sizing: border-box; resize: none; }
        .mic { position: absolute; right: 10px; bottom: 12px; border: none; background: #e2e8f0; padding: 10px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; }
        .mic-on { background: #ff4d4d; color: white; animation: pulse 1s infinite; }
        @keyframes pulse { 0% {opacity: 1} 50% {opacity: 0.6} 100% {opacity: 1} }
        #preview { width: 100%; border-radius: 12px; display: none; margin-bottom: 15px; max-height: 200px; object-fit: cover; }
        #loading { display: none; text-align: center; margin: 15px; color: #667eea; font-weight: bold; }
    </style>
</head>
<body>
<div class="card">
    <h1>Expert Technique Somfy</h1>
    <img id="preview">
    <button class="btn btn-photo" onclick="document.getElementById('in').click()">📸 Photo du boîtier / schéma</button>
    <input type="file" id="in" accept="image/*" capture="environment" hidden onchange="pv(this)">
    <div class="input-box">
        <textarea id="desc" placeholder="Décrivez le symptôme ou la panne..."></textarea>
        <button id="m" class="mic" onclick="tk()">🎙️</button>
    </div>
    <button id="go" class="btn btn-main" onclick="run()">⚡ Analyser & Diagnostiquer</button>
    <div id="loading">⏳ Consultation de la base technique Somfy...</div>
    <div id="result"></div>
</div>
<script>
let file = null; let rec = null;
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
        res.innerHTML = await r.text();
    } catch (e) { alert("Erreur réseau"); } 
    finally { load.style.display = 'none'; go.disabled = false; }
}
</script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
