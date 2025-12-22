import os
import re
import base64
import httpx
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ET BASE ---
try:
    import somfy_database as db
    BASE_TECHNIQUE = str(db.SOMFY_PRODUCTS)
    NOM_PROJET = "Somfy Expert AI"
except:
    BASE_TECHNIQUE = "{}"
    NOM_PROJET = "Diagnostic Pro"

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- ROUTES PWA ---
@app.get("/manifest.json")
async def get_manifest():
    return FileResponse("manifest.json")

@app.get("/sw.js")
async def get_sw():
    return FileResponse("sw.js", media_type="application/javascript")

# --- MOTEUR PERPLEXITY ---
async def search_perplexity(query: str):
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key: return ""
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Expert technique Somfy. Réponse courte, aérée, gras sur les points clés."},
            {"role": "user", "content": query}
        ]
    }
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=data, headers=headers, timeout=20.0)
            return res.json()['choices'][0]['message']['content']
        except: return ""

# --- FORMATAGE ---
def format_web_content(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'<span class="web-bold">\1</span>', text)
    lines = text.split('\n')
    html = ""
    for line in lines:
        line = line.strip()
        if not line: continue
        if re.match(r'^(\d+\.|-|\*)', line):
            clean = re.sub(r'^(\d+\.|-|\*)\s*', '', line)
            html += f"<div class='web-list-item'>{clean}</div>"
        else:
            html += f"<div class='web-para'>{line}</div>"
    return html

def format_html_output(text: str, web_info: str = "") -> str:
    clean = text.replace("**", "").replace("###", "##")
    sections = re.split(r'##', clean)
    html_res = ""
    for s in sections:
        c = s.strip()
        if not c: continue
        lines = c.split('\n')
        title, body = lines[0].strip(), "<br>".join(lines[1:]).strip()
        css = "diag-section"
        if "Analyse" in title: css += " s-analyse"
        elif "Correction" in title: css += " s-fix"
        elif "Base" in title: css += " s-data"
        html_res += f"<div class='{css}'><div class='section-header'>{title}</div><div class='section-body'>{body}</div></div>"
    if web_info:
        html_res += f"<div class='diag-section s-web'><div class='section-header'>🌐 Recherche Complémentaire</div><div class='section-body'>{format_web_content(web_info)}</div></div>"
    return html_res

# --- ROUTES PRINCIPALES ---
@app.post("/diagnostic")
async def diagnostic(image: UploadFile = File(None), panne_description: str = Form("")):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    sys_prompt = f"Expert {NOM_PROJET}. Base: {BASE_TECHNIQUE}. Format: ## Identification ## Analyse Technique ## Correction Experte ## Enrichissement Base"
    content = [{"type": "text", "text": sys_prompt}, {"type": "text", "text": f"Input: {panne_description}"}]
    if image and image.filename:
        img_b64 = base64.b64encode(await image.read()).decode('utf-8')
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
    
    try:
        chat = client.chat.completions.create(messages=[{"role": "user", "content": content}], model="meta-llama/llama-4-scout-17b-16e-instruct")
        analysis = chat.choices[0].message.content
    except: analysis = "## Erreur ## Analyse vision impossible."

    web_info = await search_perplexity(f"Solution Somfy pour : {panne_description} sur {analysis[:50]}")
    return HTMLResponse(content=format_html_output(analysis, web_info))

@app.get("/", response_class=HTMLResponse)
def home():
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#38bdf8">
    <script src="https://unpkg.com/html5-qrcode"></script>
    <title>{NOM_PROJET}</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; padding: 15px; margin: 0; }}
        .card {{ background: #1e293b; max-width: 550px; margin: auto; padding: 20px; border-radius: 20px; border: 1px solid #334155; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        h1 {{ color: #38bdf8; text-align: center; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; }}
        
        /* BOUTONS */
        .btn {{ width: 100%; padding: 15px; border-radius: 12px; border: none; font-weight: bold; cursor: pointer; margin-top: 10px; display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 0.9rem; transition: 0.2s; }}
        .btn-main {{ background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%); color: white; }}
        .btn-scan {{ background: #475569; color: white; }}
        .btn-photo {{ background: #334155; color: white; border: 1px dashed #64748b; }}
        .btn-share {{ background: #10b981; color: white; display: none; }}
        
        /* INPUT & MICRO */
        .input-box {{ position: relative; margin-top: 15px; }}
        textarea {{ width: 100%; height: 90px; background: #0f172a; color: white; border: 1px solid #334155; border-radius: 12px; padding: 12px; box-sizing: border-box; font-family: inherit; resize: none; }}
        .mic {{ position: absolute; right: 10px; bottom: 10px; background: #1e293b; border: 1px solid #334155; color: #38bdf8; border-radius: 50%; width: 38px; height: 38px; cursor: pointer; display: flex; align-items: center; justify-content: center; }}
        .mic-on {{ background: #ef4444; color: white; animation: pulse 1.5s infinite; border: none; }}
        
        /* DIAGNOSTIC */
        .diag-section {{ background: #334155; border-radius: 12px; margin-top: 15px; border-left: 4px solid #38bdf8; overflow: hidden; }}
        .s-analyse {{ border-left-color: #fbbf24; }} .s-fix {{ border-left-color: #22c55e; }} .s-web {{ border-left-color: #f472b6; }}
        .section-header {{ padding: 12px 15px; font-weight: bold; background: rgba(0,0,0,0.2); font-size: 0.9rem; }}
        .section-body {{ padding: 15px; font-size: 0.9rem; line-height: 1.6; color: #cbd5e1; }}
        .web-bold {{ color: #f472b6; font-weight: bold; }}
        .web-list-item:before {{ content: "🔹"; margin-right: 8px; }}
        
        #reader {{ width: 100%; border-radius: 12px; overflow: hidden; display: none; margin-top: 10px; }}
        #preview {{ width: 100%; border-radius: 12px; display: none; margin-top: 10px; border: 2px solid #38bdf8; }}
        #loading {{ display: none; text-align: center; color: #38bdf8; padding: 20px; font-weight: bold; }}
        
        @keyframes pulse {{ 0% {{box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);}} 70% {{box-shadow: 0 0 0 10px rgba(239, 68, 68, 0);}} 100% {{box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);}} }}
    </style>
</head>
<body>
<div class="card">
    <h1>{NOM_PROJET}</h1>
    
    <div id="reader"></div>
    <button id="scanBtn" class="btn btn-scan" onclick="startScan()">🔍 SCANNER CODE-BARRES</button>
    
    <img id="preview">
    <button class="btn btn-photo" onclick="document.getElementById('in').click()">📷 PHOTO DU PROBLÈME</button>
    <input type="file" id="in" accept="image/*" capture="environment" hidden onchange="pv(this)">
    
    <div class="input-box">
        <textarea id="desc" placeholder="Décrivez la panne ou scannez un code..."></textarea>
        <button id="m" class="mic" onclick="tk()">🎙️</button>
    </div>
    
    <button id="go" class="btn btn-main" onclick="run()">⚡ LANCER DIAGNOSTIC</button>
    <button id="sh" class="btn btn-share" onclick="share()">📤 PARTAGER LE RAPPORT</button>
    <button id="rs" class="btn" style="background:#475569; color:white; display:none" onclick="reset()">🔄 NOUVEAU DIAGNOSTIC</button>
    
    <div id="loading">📡 Analyse IA & Recherche Web...</div>
    <div id="result"></div>
</div>

<script>
    if ('serviceWorker' in navigator) {{ navigator.serviceWorker.register('/sw.js'); }}

    window.onload = () => {{
        const saved = localStorage.getItem('lastDiag');
        if(saved) {{
            document.getElementById('result').innerHTML = saved;
            document.getElementById('rs').style.display = 'flex';
            document.getElementById('sh').style.display = 'flex';
        }}
    }};

    // --- SCANNER ---
    let html5QrCode;
    function startScan() {{
        const r = document.getElementById('reader');
        r.style.display = 'block';
        document.getElementById('scanBtn').style.display = 'none';
        html5QrCode = new Html5Qrcode("reader");
        html5QrCode.start({{ facingMode: "environment" }}, {{ fps: 10, qrbox: 250 }}, (txt) => {{
            document.getElementById('desc').value = "Référence : " + txt;
            stopScan();
            run();
        }}).catch(err => alert("Erreur Caméra"));
    }}
    function stopScan() {{
        if (html5QrCode) {{ html5QrCode.stop().then(() => {{ 
            document.getElementById('reader').style.display = 'none'; 
            document.getElementById('scanBtn').style.display = 'flex';
        }}); }}
    }}

    // --- MICRO (VOICE) ---
    let rec = null;
    function tk() {{
        const S = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!S) return alert("Micro non supporté");
        if (!rec) {{
            rec = new S(); rec.lang = 'fr-FR';
            rec.onresult = (e) => {{ document.getElementById('desc').value += " " + e.results[0][0].transcript; }};
            rec.onstart = () => document.getElementById('m').classList.add('mic-on');
            rec.onend = () => document.getElementById('m').classList.remove('mic-on');
        }}
        try {{ rec.start(); }} catch(e) {{ rec.stop(); }}
    }}

    // --- IMAGE ---
    let file = null;
    function pv(i) {{
        file = i.files[0];
        const r = new FileReader();
        r.onload = (e) => {{ const p = document.getElementById('preview'); p.src = e.target.result; p.style.display = 'block'; }};
        r.readAsDataURL(file);
    }}

    // --- ACTIONS ---
    async function run() {{
        const res = document.getElementById('result');
        const load = document.getElementById('loading');
        const go = document.getElementById('go');
        go.disabled = true; load.style.display = 'block'; res.innerHTML = "";
        const fd = new FormData();
        if (file) fd.append('image', file);
        fd.append('panne_description', document.getElementById('desc').value);
        try {{
            const r = await fetch('/diagnostic', {{ method: 'POST', body: fd }});
            const html = await r.text();
            res.innerHTML = html;
            localStorage.setItem('lastDiag', html);
            document.getElementById('rs').style.display = 'flex';
            document.getElementById('sh').style.display = 'flex';
        }} catch (e) {{ alert("Erreur reseau"); }} 
        finally {{ load.style.display = 'none'; go.disabled = false; }}
    }}

    function share() {{
        const t = document.getElementById('result').innerText;
        if (navigator.share) {{ navigator.share({{ title: 'Rapport Somfy', text: t }}); }}
        else {{ navigator.clipboard.writeText(t); alert("Copié !"); }}
    }}

    function reset() {{
        localStorage.removeItem('lastDiag');
        location.reload();
    }}
</script>
</body>
</html>"""
