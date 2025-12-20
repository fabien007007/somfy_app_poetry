import os
import re
import base64
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Chargement de la base pour le contexte de l'IA
try:
    import somfy_database
    BASE_TECHNIQUE = str(somfy_database.SOMFY_PRODUCTS)
except Exception:
    BASE_TECHNIQUE = "{}"

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def format_html_output(text: str) -> str:
    """Structure les sections de diagnostic avec un design pro."""
    clean = text.replace("**", "").replace("###", "##")
    sections = re.split(r'##', clean)
    html_res = ""
    for s in sections:
        content = s.strip()
        if not content: continue
        lines = content.split('\n')
        title = lines[0].strip().replace(':', '')
        body = "<br>".join(lines[1:]).strip()
        
        css = "diag-section"
        icon, tag = "⚙️", "INFO"
        if "Identification" in title: icon, tag = "🆔", "ID"
        elif "Analyse" in title: icon, tag, css = "🔍", "ANALYSE", "diag-section s-analyse"
        elif "Correction" in title: icon, tag, css = "🛠️", "RECO", "diag-section s-fix"
        elif "Base" in title: icon, tag, css = "💾", "UPDATE", "diag-section s-data"
        
        html_res += f"<div class='{css}'><div class='section-header'><span class='tag'>{tag}</span> {icon} {title}</div><div class='section-body'>{body}</div></div>"
    return html_res

@app.post("/diagnostic")
async def diagnostic(image: UploadFile = File(None), panne_description: str = Form("")):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    system_instruction = f"""Tu es l'Expert Support Somfy pour techniciens. 
    Analyse la photo (câblage, LEDs, étiquettes) et les symptômes.
    Utilise cette base : {BASE_TECHNIQUE}. Si absent, utilise tes connaissances expertes (Reset 2/7/2, codes erreurs).
    PROPOSE UN BLOC JSON DANS 'Enrichissement Base' SI L'INFO EST NOUVELLE.
    FORMAT : ## Identification ## Analyse Technique ## Correction Experte ## Enrichissement Base"""

    content = [{"type": "text", "text": system_instruction}]
    content.append({"type": "text", "text": f"Symptôme : {panne_description}"})

    if image and image.filename:
        img_data = await image.read()
        img_b64 = base64.b64encode(img_data).decode('utf-8')
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": content}],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=0.1
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
    <title>Somfy Pro AI</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: white; margin: 0; padding: 15px; }
        .card { background: #1e293b; max-width: 600px; margin: auto; padding: 20px; border-radius: 24px; border: 1px solid #334155; }
        h1 { font-size: 1.1rem; color: #38bdf8; text-align: center; text-transform: uppercase; margin-bottom: 20px; }
        .diag-section { background: #334155; border-radius: 12px; margin-top: 15px; border-left: 4px solid #38bdf8; }
        .s-analyse { border-left-color: #fbbf24; }
        .s-fix { border-left-color: #22c55e; }
        .s-data { border-left-color: #a855f7; font-family: monospace; font-size: 0.8rem; }
        .section-header { padding: 10px 15px; font-weight: bold; background: rgba(0,0,0,0.2); display: flex; align-items: center; gap: 10px; }
        .tag { font-size: 0.6rem; background: #38bdf8; color: #0f172a; padding: 2px 6px; border-radius: 4px; }
        .section-body { padding: 15px; color: #cbd5e1; font-size: 0.95rem; }
        .btn { width: 100%; padding: 16px; border-radius: 12px; border: none; font-weight: bold; cursor: pointer; margin-top: 10px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .btn-main { background: #38bdf8; color: #0f172a; }
        .btn-photo { background: #334155; color: white; border: 1px dashed #64748b; }
        .btn-share { background: #22c55e; color: white; display: none; }
        .btn-reset { background: #475569; color: white; display: none; }
        .input-box { position: relative; margin: 15px 0; }
        textarea { width: 100%; height: 90px; background: #0f172a; border: 1px solid #334155; border-radius: 12px; color: white; padding: 15px; box-sizing: border-box; }
        .mic { position: absolute; right: 10px; bottom: 10px; background: #334155; border: none; padding: 8px; border-radius: 50%; color: white; cursor: pointer; }
        .mic-on { background: #ef4444; animation: pulse 1s infinite; }
        #preview { width: 100%; border-radius: 12px; display: none; margin-bottom: 15px; border: 2px solid #38bdf8; }
        #loading { display: none; text-align: center; color: #38bdf8; padding: 10px; }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
    </style>
</head>
<body>
<div class="card">
    <h1>Somfy Expert AI</h1>
    <img id="preview">
    <button class="btn btn-photo" onclick="document.getElementById('in').click()">📷 Photo de l'équipement</button>
    <input type="file" id="in" accept="image/*" capture="environment" hidden onchange="pv(this)">
    <div class="input-box">
        <textarea id="desc" placeholder="Décrivez le problème technique..."></textarea>
        <button id="m" class="mic" onclick="tk()">🎙️</button>
    </div>
    <button id="go" class="btn btn-main" onclick="run()">⚡ Diagnostiquer</button>
    <button id="sh" class="btn btn-share" onclick="share()">📤 Partager le rapport</button>
    <button id="rs" class="btn btn-reset" onclick="location.reload()">🔄 Nouveau Diagnostic</button>
    <div id="loading">⏳ Analyse technique en cours...</div>
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
        document.getElementById('sh').style.display = 'flex';
        document.getElementById('rs').style.display = 'flex';
    } catch (e) { alert("Erreur réseau"); } 
    finally { load.style.display = 'none'; go.disabled = false; }
}
function share() {
    const t = document.getElementById('result').innerText;
    if (navigator.share) { navigator.share({ title: 'Rapport Somfy', text: t }); }
    else { navigator.clipboard.writeText(t); alert("Copié dans le presse-papier"); }
}
</script>
</body>
</html>"""
