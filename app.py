import os
import re
import base64
import httpx
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

try:
    import somfy_database
    BASE_TECHNIQUE = str(somfy_database.SOMFY_PRODUCTS)
except Exception:
    BASE_TECHNIQUE = "{}"

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

async def search_perplexity(query: str):
    """Recherche d'informations techniques via Perplexity API."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        return "Recherche Web non disponible (Clé manquante)."
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "sonar-pro", # Modèle optimisé pour la recherche
        "messages": [
            {"role": "system", "content": "Tu es un documentaliste technique Somfy. Trouve les branchements exacts ou codes erreurs."},
            {"role": "user", "content": query}
        ]
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers=headers, timeout=20.0)
            return response.json()['choices'][0]['message']['content']
        except:
            return "Erreur lors de la recherche en ligne."

def format_html_output(text: str, web_info: str = "") -> str:
    clean = text.replace("**", "").replace("###", "##")
    sections = re.split(r'##', clean)
    html_res = ""
    for s in sections:
        content = s.strip()
        if not content: continue
        lines = content.split('\n')
        title, body = lines[0].strip(), "<br>".join(lines[1:]).strip()
        
        css, icon, tag = "diag-section", "⚙️", "INFO"
        if "Identification" in title: icon, tag = "🆔", "ID"
        elif "Analyse" in title: icon, tag, css = "🔍", "ANALYSE", "diag-section s-analyse"
        elif "Correction" in title: icon, tag, css = "🛠️", "RECO", "diag-section s-fix"
        elif "Base" in title: icon, tag, css = "💾", "DATA", "diag-section s-data"
        
        html_res += f"<div class='{css}'><div class='section-header'><span class='tag'>{tag}</span> {icon} {title}</div><div class='section-body'>{body}</div></div>"
    
    if web_info:
        html_res += f"<div class='diag-section s-web'><div class='section-header'><span class='tag'>WEB</span> 🌐 Recherche Perplexity AI</div><div class='section-body'>{web_info}</div></div>"
    
    return html_res

@app.post("/diagnostic")
async def diagnostic(image: UploadFile = File(None), panne_description: str = Form("")):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    # 1. Analyse Vision via Groq
    system_prompt = f"Expert Somfy. Base : {BASE_TECHNIQUE}. Analyse la photo. Format: ## Identification ## Analyse Technique ## Correction Experte ## Enrichissement Base"
    content = [{"type": "text", "text": system_prompt}, {"type": "text", "text": f"Panne: {panne_description}"}]
    
    if image and image.filename:
        img_b64 = base64.b64encode(await image.read()).decode('utf-8')
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})

    chat_completion = client.chat.completions.create(messages=[{"role": "user", "content": content}], model="meta-llama/llama-4-scout-17b-16e-instruct")
    analysis = chat_completion.choices[0].message.content

    # 2. Recherche Web via Perplexity (si nécessaire)
    web_info = await search_perplexity(f"Solution technique Somfy pour : {panne_description} sur matériel identifié comme {analysis[:100]}")
    
    return HTMLResponse(content=format_html_output(analysis, web_info))

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Somfy Pro - Multi-IA</title>
    <style>
        body { font-family: sans-serif; background: #0f172a; color: white; padding: 15px; }
        .card { background: #1e293b; max-width: 600px; margin: auto; padding: 20px; border-radius: 20px; }
        .diag-section { background: #334155; border-radius: 12px; margin-top: 15px; border-left: 4px solid #38bdf8; }
        .s-analyse { border-left-color: #fbbf24; } .s-fix { border-left-color: #22c55e; } .s-web { border-left-color: #f472b6; }
        .section-header { padding: 10px; font-weight: bold; display: flex; align-items: center; gap: 8px; background: rgba(0,0,0,0.1); }
        .section-body { padding: 15px; font-size: 0.9rem; }
        .tag { font-size: 0.6rem; background: #38bdf8; color: #0f172a; padding: 2px 6px; border-radius: 4px; }
        .btn { width: 100%; padding: 15px; border-radius: 12px; border: none; font-weight: bold; cursor: pointer; margin-top: 10px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .btn-main { background: #38bdf8; color: #0f172a; }
        .btn-reset { background: #ef4444; color: white; display: none; }
        .input-box { position: relative; margin: 15px 0; }
        textarea { width: 100%; height: 80px; background: #0f172a; color: white; border-radius: 12px; padding: 10px; border: 1px solid #334155; }
        .mic { position: absolute; right: 10px; bottom: 10px; background: #334155; border: none; color: white; border-radius: 50%; padding: 8px; cursor: pointer; }
        #preview { width: 100%; border-radius: 12px; display: none; margin-bottom: 15px; }
    </style>
</head>
<body>
<div class="card">
    <h1>Somfy Expert Multi-IA</h1>
    <img id="preview">
    <button class="btn" style="background:#334155; color:white" onclick="document.getElementById('in').click()">📷 Photo de l'équipement</button>
    <input type="file" id="in" accept="image/*" capture="environment" hidden onchange="pv(this)">
    <div class="input-box">
        <textarea id="desc" placeholder="Décrivez la panne..."></textarea>
        <button id="m" class="mic" onclick="tk()">🎙️</button>
    </div>
    <button id="go" class="btn btn-main" onclick="run()">⚡ Diagnostiquer</button>
    <button id="rs" class="btn btn-reset" onclick="reset()">🔄 Nouveau Diagnostic</button>
    <div id="result"></div>
</div>
<script>
    // Chargement au démarrage
    window.onload = () => {
        const saved = localStorage.getItem('lastDiag');
        if(saved) {
            document.getElementById('result').innerHTML = saved;
            document.getElementById('rs').style.display = 'flex';
        }
    };

    let file = null;
    function pv(i) {
        file = i.files[0];
        const r = new FileReader();
        r.onload = (e) => { const p = document.getElementById('preview'); p.src = e.target.result; p.style.display = 'block'; };
        r.readAsDataURL(file);
    }

    async function run() {
        const res = document.getElementById('result');
        const go = document.getElementById('go');
        go.disabled = true; go.innerText = "⏳ Analyse en cours...";
        const fd = new FormData();
        if(file) fd.append('image', file);
        fd.append('panne_description', document.getElementById('desc').value);
        try {
            const r = await fetch('/diagnostic', { method: 'POST', body: fd });
            const html = await r.text();
            res.innerHTML = html;
            localStorage.setItem('lastDiag', html); // Sauvegarde
            document.getElementById('rs').style.display = 'flex';
        } catch(e) { alert("Erreur"); }
        finally { go.disabled = false; go.innerText = "⚡ Diagnostiquer"; }
    }

    function reset() {
        localStorage.removeItem('lastDiag');
        location.reload();
    }
    
    function tk() { /* Code SpeechRecognition identique */ }
</script>
</body>
</html>"""
