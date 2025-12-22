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
except Exception as e:
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

# --- MOTEUR DE RECHERCHE WEB (Perplexity) ---
async def search_perplexity(query: str):
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key: return ""
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Expert technique Somfy. Donne des solutions précises, schémas ou codes erreurs. Sois concis et utilise le gras."},
            {"role": "user", "content": query}
        ]
    }
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=data, headers=headers, timeout=25.0)
            return res.json()['choices'][0]['message']['content']
        except: return "Recherche web indisponible."

# --- FORMATAGE HTML ---
def format_html_output(text: str, web_info: str = "") -> str:
    clean = text.replace("**", "").replace("###", "##")
    sections = re.split(r'##', clean)
    html_res = ""
    for s in sections:
        c = s.strip()
        if not c: continue
        lines = c.split('\n')
        title = lines[0].strip()
        body = "<br>".join(lines[1:]).strip()
        css = "diag-section"
        icon = "⚙️"
        if "Identification" in title: icon, css = "🆔", "diag-section"
        elif "Analyse" in title: icon, css = "🔍", "diag-section s-analyse"
        elif "Correction" in title: icon, css = "🛠️", "diag-section s-fix"
        elif "Base" in title or "Enrichissement" in title: icon, css = "💾", "diag-section s-data"
        html_res += f"<div class='{css}'><div class='section-header'>{icon} {title}</div><div class='section-body'>{body}</div></div>"
    if web_info:
        web_body = web_info.replace("**", "<b>").replace("\n", "<br>")
        html_res += f"<div class='diag-section s-web'><div class='section-header'>🌐 SOLUTIONS WEB TEMPS RÉEL</div><div class='section-body'>{web_body}</div></div>"
    return html_res

# --- LOGIQUE DE DIAGNOSTIC (Modèle Stable Llama 4 Scout) ---
@app.post("/diagnostic")
async def diagnostic(image: UploadFile = File(None), panne_description: str = Form("")):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    prompt_systeme = f"""Tu es l'Expert Technique Somfy Ultime.
    Tu as accès à cette BASE DE DONNÉES PRIVÉE : {BASE_TECHNIQUE}.
    
    TA MISSION :
    1. Si une image est fournie : ANALYSE-LA visuellement avec une précision extrême (borniers, câblage, état des LEDs, références).
    2. Identifie le produit exact et compare-le à la BASE DE DONNÉES fournie.
    3. Ne sois jamais générique. Ta réponse doit être unique et correspondre à la photo.
    
    STRUCTURE OBLIGATOIRE (utilise ##) :
    ## 🆔 Identification précise
    ## 🔍 Analyse visuelle et technique
    ## 🛠️ Correction étape par étape
    ## 💾 Enrichissement Base & Docs"""

    messages = [{"role": "system", "content": prompt_systeme}]
    user_content = [{"type": "text", "text": f"PROBLÈME DÉCRIT : {panne_description}"}]
    
    if image and image.filename:
        img_b64 = base64.b64encode(await image.read()).decode('utf-8')
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
        })
    
    messages.append({"role": "user", "content": user_content})

    try:
        # UTILISATION DU MODÈLE DE PRODUCTION STABLE LLAMA 4 SCOUT
        response = client.chat.completions.create(
            messages=messages,
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=0.1
        )
        analysis = response.choices[0].message.content
    except Exception as e:
        analysis = f"## ⚠️ Erreur ## Problème avec le modèle Llama 4 Scout : {str(e)}"

    web_query = f"Solution technique Somfy précise pour : {panne_description}. Matériel : {analysis[:100]}"
    web_info = await search_perplexity(web_query)
    
    return HTMLResponse(content=format_html_output(analysis, web_info))

# --- INTERFACE FRONT-END ---
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
        body {{ font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 15px; }}
        .card {{ background: #1e293b; max-width: 600px; margin: auto; padding: 20px; border-radius: 20px; border: 1px solid #334155; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        h1 {{ color: #38bdf8; text-align: center; font-size: 1.2rem; text-transform: uppercase; margin-bottom: 25px; }}
        
        .btn {{ width: 100%; padding: 16px; border-radius: 12px; border: none; font-weight: bold; cursor: pointer; margin-top: 12px; display: flex; align-items: center; justify-content: center; gap: 10px; font-size: 1rem; transition: 0.2s; }}
        .btn-main {{ background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%); color: white; }}
        .btn-scan {{ background: #475569; color: white; }}
        .btn-photo {{ background: #334155; color: white; border: 1px dashed #64748b; }}
        .btn-share {{ background: #10b981; color: white; display: none; }}
        
        .input-box {{ position: relative; margin-top: 20px; }}
        textarea {{ width: 100%; height: 110px; background: #0f172a; border: 1px solid #334155; border-radius: 12px; color: white; padding: 12px; box-sizing: border-box; resize: none; font-size: 1rem; }}
        .mic {{ position: absolute; right: 10px; bottom: 10px; background: #1e293b; border: 1px solid #334155; color: #38bdf8; border-radius: 50%; width: 44px; height: 44px; cursor: pointer; display: flex; align-items: center; justify-content: center; }}
        .mic-on {{ background: #ef4444; color: white; animation: pulse 1.5s infinite; border: none; }}
        
        .diag-section {{ background: #334155; border-radius: 12px; margin-top: 15px; border-left: 4px solid #94a3b8; overflow: hidden; }}
        .s-analyse {{ border-left-color: #fbbf24; }} .s-fix {{ border-left-color: #22c55e; }} .s-data {{ border-left-color: #38bdf8; }}
        .s-web {{ border-left-color: #f472b6; background: #2c2e3e; }}
        .section-header {{ padding: 12px 15px; font-weight: bold; background: rgba(0,0,0,0.2); display: flex; align-items: center; gap: 8px; }}
        .section-body {{ padding: 15px; line-height: 1.6; font-size: 0.95rem; }}
        
        #reader {{ width: 100%; border-radius: 12px; overflow: hidden; display: none; margin-top: 10px; }}
        #preview {{ width: 100%; border-radius: 12px; display: none; margin: 15px 0; border: 2px solid #38bdf8; max-height: 300px; object-fit: cover; }}
        #loading {{ display: none; text-align: center; color: #38bdf8; font-weight: bold; padding: 20px; }}
        @keyframes pulse {{ 0% {{box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);}} 70% {{box-shadow: 0 0 0 10px rgba(239, 68, 68, 0);}} 100% {{box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);}} }}
    </style>
</head>
<body>
<div class="card">
    <h1>{NOM_PROJET}</h1>
    <div id="reader"></div>
    <button id="btnScan" class="btn btn-scan" onclick="startScan()">🔍 SCANNER CODE-BARRES</button>
    <img id="preview">
    <button class="btn btn-photo" onclick="document.getElementById('in').click()">📷 PHOTO DU PRODUIT / PANNE</button>
    <input type="file" id="in" accept="image/*" capture="environment" hidden onchange="pv(this)">
    <div class="input-box">
        <textarea id="desc" placeholder="Décrivez le problème technique ou scannez..."></textarea>
        <button id="m" class="mic" onclick="tk()">🎙️</button>
    </div>
    <button id="go" class="btn btn-main" onclick="run()">⚡ LANCER LE DIAGNOSTIC</button>
    <button id="sh" class="btn btn-share" onclick="share()">📤 PARTAGER LE RAPPORT</button>
    <button id="rs" class="btn" style="background:#ef4444; color:white; display:none" onclick="reset()">🔄 NOUVEAU DIAGNOSTIC</button>
    <div id="loading">📡 Analyse Groq Vision & Recherche Web...</div>
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
    let scanner;
    function startScan() {{
        document.getElementById('reader').style.display = 'block';
        document.getElementById('btnScan').style.display = 'none';
        scanner = new Html5Qrcode("reader");
        scanner.start({{ facingMode: "environment" }}, {{ fps: 10, qrbox: 250 }}, (txt) => {{
            document.getElementById('desc').value = "Référence : " + txt;
            stopScan(); run();
        }}).catch(e => alert("Caméra bloquée"));
    }}
    function stopScan() {{
        if(scanner) {{ scanner.stop().then(() => {{ 
            document.getElementById('reader').style.display = 'none';
            document.getElementById('btnScan').style.display = 'flex';
        }}); }}
    }}
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
    let file = null;
    function pv(i) {{
        file = i.files[0];
        const r = new FileReader();
        r.onload = (e) => {{ const p = document.getElementById('preview'); p.src = e.target.result; p.style.display = 'block'; }};
        r.readAsDataURL(file);
    }}
    async function run() {{
        const res = document.getElementById('result');
        const load = document.getElementById('loading');
        const go = document.getElementById('go');
        go.style.display = 'none'; load.style.display = 'block'; res.innerHTML = "";
        const fd = new FormData();
        if (file) fd.append('image', file);
        fd.append('panne_description', document.getElementById('desc').value);
        try {{
            const r = await fetch('/diagnostic', {{ method: 'POST', body: fd }});
            const html = await r.text();
            res.innerHTML = html;
            localStorage.setItem('lastDiag', html);
            document.getElementById('sh').style.display = 'flex';
            document.getElementById('rs').style.display = 'flex';
        }} catch (e) {{ alert("Erreur serveur"); go.style.display = 'flex'; }} 
        finally {{ load.style.display = 'none'; }}
    }}
    function share() {{
        const t = document.getElementById('result').innerText;
        if (navigator.share) {{ navigator.share({{ title: 'Rapport Somfy', text: t }}); }}
        else {{ navigator.clipboard.writeText(t); alert("Copié !"); }}
    }}
    function reset() {{
        localStorage.removeItem('lastDiag'); location.reload();
    }}
</script>
</body>
</html>"""
