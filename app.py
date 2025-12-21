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

# Chargement de la base
try:
    import somfy_database
    BASE_TECHNIQUE = str(somfy_database.SOMFY_PRODUCTS)
except Exception:
    BASE_TECHNIQUE = "{}"

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

async def search_perplexity(query: str):
    """Recherche Web avec instruction de formatage strict."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key: return ""
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # On demande à Perplexity de structurer sa réponse pour la lisibilité
    system_msg = """Tu es un expert technique Somfy.
    Tes réponses doivent être COURTES et AÉRÉES.
    - Utilise des listes à puces pour les étapes.
    - Mets les questions importantes ou les solutions en GRAS (**texte**).
    - Ne fais pas de gros paragraphes."""
    
    data = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query}
        ]
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers=headers, timeout=20.0)
            return response.json()['choices'][0]['message']['content']
        except:
            return ""

def format_web_content(text: str) -> str:
    """Transforme le Markdown de Perplexity en HTML stylisé."""
    if not text: return ""
    
    # 1. Convertir le gras (**texte**) en span coloré
    text = re.sub(r'\*\*(.*?)\*\*', r'<span class="web-bold">\1</span>', text)
    
    # 2. Gérer les listes et les sauts de ligne
    lines = text.split('\n')
    formatted_html = ""
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Si c'est un point de liste (commence par - ou * ou 1.)
        if re.match(r'^(\d+\.|-|\*)', line):
            # On retire le marqueur pour mettre notre propre puce CSS
            clean_line = re.sub(r'^(\d+\.|-|\*)\s*', '', line)
            formatted_html += f"<div class='web-list-item'>{clean_line}</div>"
        else:
            # Paragraphe normal
            formatted_html += f"<div class='web-para'>{line}</div>"
            
    return formatted_html

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
    
    # Intégration propre de Perplexity
    if web_info:
        formatted_web = format_web_content(web_info)
        html_res += f"<div class='diag-section s-web'><div class='section-header'><span class='tag'>WEB</span> 🌐 Recherche Complémentaire</div><div class='section-body'>{formatted_web}</div></div>"
    
    return html_res

@app.post("/diagnostic")
async def diagnostic(image: UploadFile = File(None), panne_description: str = Form("")):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    # 1. Vision GROQ
    system_prompt = f"Expert Somfy. Base: {BASE_TECHNIQUE}. Format: ## Identification ## Analyse Technique ## Correction Experte ## Enrichissement Base"
    content = [{"type": "text", "text": system_prompt}, {"type": "text", "text": f"Panne: {panne_description}"}]
    
    if image and image.filename:
        img_b64 = base64.b64encode(await image.read()).decode('utf-8')
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})

    try:
        chat_completion = client.chat.completions.create(messages=[{"role": "user", "content": content}], model="meta-llama/llama-4-scout-17b-16e-instruct")
        analysis = chat_completion.choices[0].message.content
    except: analysis = "## Erreur ## Analyse vision impossible."

    # 2. Recherche WEB (si nécessaire)
    web_query = f"Problème technique Somfy : {panne_description}. Matériel identifié : {analysis[:50]}."
    web_info = await search_perplexity(web_query)
    
    return HTMLResponse(content=format_html_output(analysis, web_info))

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Somfy Expert Pro</title>
    <style>
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 15px; }
        .card { background: #1e293b; max-width: 600px; margin: auto; padding: 20px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); border: 1px solid #334155; }
        h1 { color: #38bdf8; text-align: center; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 25px; font-size: 1.2rem; }
        
        /* Sections du diagnostic */
        .diag-section { background: #334155; border-radius: 12px; margin-top: 15px; border-left: 4px solid #94a3b8; overflow: hidden; }
        .s-analyse { border-left-color: #fbbf24; } 
        .s-fix { border-left-color: #22c55e; } 
        .s-data { border-left-color: #a855f7; }
        
        /* Section Web spécifique */
        .s-web { border-left-color: #f472b6; background: #2c2e3e; }
        .web-bold { color: #f472b6; font-weight: bold; }
        .web-list-item { padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: flex-start; }
        .web-list-item:before { content: "🔹"; margin-right: 10px; font-size: 0.8rem; }
        .web-para { margin-bottom: 10px; line-height: 1.5; }

        .section-header { padding: 12px 15px; font-weight: bold; background: rgba(0,0,0,0.2); display: flex; align-items: center; gap: 10px; color: #f1f5f9; }
        .section-body { padding: 15px; font-size: 0.95rem; line-height: 1.6; color: #cbd5e1; }
        .tag { font-size: 0.65rem; background: #475569; color: #fff; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; }
        
        /* Contrôles */
        .btn { width: 100%; padding: 16px; border-radius: 12px; border: none; font-weight: bold; cursor: pointer; margin-top: 12px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.1s; font-size: 1rem; }
        .btn:active { transform: scale(0.98); }
        .btn-main { background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%); color: white; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3); }
        .btn-photo { background: #334155; color: white; border: 1px dashed #64748b; }
        .btn-share { background: #10b981; color: white; display: none; }
        .btn-reset { background: #ef4444; color: white; display: none; }
        
        .input-box { position: relative; margin: 15px 0; }
        textarea { width: 100%; height: 90px; background: #0f172a; border: 1px solid #334155; border-radius: 12px; color: white; padding: 12px; box-sizing: border-box; font-family: inherit; resize: none; }
        textarea:focus { outline: none; border-color: #38bdf8; }
        
        .mic { position: absolute; right: 10px; bottom: 10px; background: #1e293b; border: 1px solid #334155; color: #38bdf8; border-radius: 50%; width: 36px; height: 36px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .mic-on { background: #ef4444; color: white; border-color: #ef4444; animation: pulse 1.5s infinite; }
        
        #preview { width: 100%; border-radius: 12px; display: none; margin-bottom: 15px; border: 2px solid #38bdf8; max-height: 250px; object-fit: cover; }
        #loading { display: none; text-align: center; color: #38bdf8; font-weight: bold; padding: 20px; }
        
        @keyframes pulse { 0% {box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);} 70% {box-shadow: 0 0 0 10px rgba(239, 68, 68, 0);} 100% {box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);} }
    </style>
</head>
<body>
<div class="card">
    <h1>Somfy Expert AI</h1>
    <img id="preview">
    <button class="btn btn-photo" onclick="document.getElementById('in').click()">📷 Prendre Photo</button>
    <input type="file" id="in" accept="image/*" capture="environment" hidden onchange="pv(this)">
    
    <div class="input-box">
        <textarea id="desc" placeholder="Décrivez le problème (ex: le portail ne se ferme plus)..."></textarea>
        <button id="m" class="mic" onclick="tk()">🎙️</button>
    </div>
    
    <button id="go" class="btn btn-main" onclick="run()">⚡ Lancer Diagnostic</button>
    <button id="sh" class="btn btn-share" onclick="share()">📤 Partager</button>
    <button id="rs" class="btn btn-reset" onclick="reset()">🔄 Nouveau</button>
    
    <div id="loading">📡 Analyse Matériel & Recherche Web...</div>
    <div id="result"></div>
</div>

<script>
    window.onload = () => {
        const saved = localStorage.getItem('lastDiag');
        if(saved) {
            document.getElementById('result').innerHTML = saved;
            document.getElementById('rs').style.display = 'flex';
            document.getElementById('sh').style.display = 'flex';
        }
    };

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
        if (!S) return alert("Micro non supporté sur ce navigateur");
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
        
        go.style.display = 'none'; 
        load.style.display = 'block'; 
        res.innerHTML = "";
        
        const fd = new FormData();
        if (file) fd.append('image', file);
        fd.append('panne_description', document.getElementById('desc').value);
        
        try {
            const r = await fetch('/diagnostic', { method: 'POST', body: fd });
            const html = await r.text();
            res.innerHTML = html;
            localStorage.setItem('lastDiag', html);
            document.getElementById('sh').style.display = 'flex';
            document.getElementById('rs').style.display = 'flex';
        } catch (e) { 
            alert("Erreur de communication");
            go.style.display = 'flex';
        } finally { 
            load.style.display = 'none'; 
        }
    }

    function share() {
        const t = document.getElementById('result').innerText;
        if (navigator.share) { navigator.share({ title: 'Diag Somfy', text: t }); }
        else { navigator.clipboard.writeText(t); alert("Copié !"); }
    }
    
    function reset() {
        localStorage.removeItem('lastDiag');
        location.reload();
    }
</script>
</body>
</html>"""
