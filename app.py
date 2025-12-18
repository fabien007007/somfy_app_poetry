from fastapi import FastAPI, UploadFile, Form, File, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
import re
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
# Remplace dans ton .env ou directement ici pour tester
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
genai.configure(api_key=GEMINI_API_KEY)

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
    """Prépare l'image pour l'envoi à Gemini"""
    try:
        img = Image.open(BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((800, 800)) # Qualité supérieure pour Gemini
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        return Image.open(buffer) # Gemini accepte directement les objets PIL
    except Exception as e:
        print(f"Erreur image: {e}")
        return None

def call_gemini_vision(prompt: str, pil_image=None) -> str:
    if not GEMINI_API_KEY:
        return "❌ Clé API Gemini manquante."
    
    try:
        # Utilisation du modèle Flash (Gratuit, rapide et voit les images)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        inputs = [prompt]
        if pil_image:
            inputs.append(pil_image)
            
        response = model.generate_content(inputs)
        return response.text
    except Exception as e:
        return f"⚙️ Erreur Gemini: {str(e)}"

def format_html_output(text: str) -> str:
    """Design en cartes comme demandé"""
    # Nettoyage Markdown de Gemini
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
    img_pil = None
    if image and image.filename:
        raw_data = await image.read()
        img_pil = prepare_image_for_gemini(raw_data)
    
    prompt = f"""Tu es l'expert technique Somfy ultime. 
    Analyse cette situation : {panne_description}.
    Si une image est fournie, identifie précisément le modèle Somfy, les branchements et toute anomalie visuelle (fil desserré, brûlure, LED).
    Réponds EXCLUSIVEMENT avec ce format :
    ## Identification
    ## Sécurité
    ## Tests
    ## Correction
    Sois très technique, pas de blabla, pas de sources."""
    
    raw_text = call_gemini_vision(prompt, img_pil)
    return HTMLResponse(content=format_html_output(raw_text))

@app.get("/", response_class=HTMLResponse)
def home():
    # Garder exactement le même HTML que précédemment (avec localStorage et micro)
    # Copie-colle ici le HTML du message précédent
    return """ ... (Le HTML complet avec localStorage du message précédent) ... """
