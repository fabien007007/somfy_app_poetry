from fastapi import FastAPI, UploadFile, Form, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import base64
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import cv2
import numpy as np
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════

class DiagnosticMobileRequest(BaseModel):
    image: Optional[str] = None
    panne_description: str
    timestamp: str

class DiagnosticResponse(BaseModel):
    status: str
    timestamp: str
    result: str

class HealthResponse(BaseModel):
    status: str
    version: str
    api_key_present: bool
    timestamp: str

# ═══════════════════════════════════════════════════════════════════
# PERPLEXITY API CALLS
# ═══════════════════════════════════════════════════════════════════

def call_perplexity(prompt: str) -> str:
    """Appel à l'API Perplexity pour diagnostic texte"""
    if not PERPLEXITY_API_KEY:
        return "Erreur: PERPLEXITY_API_KEY manquante"
    
    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}"},
            json={
                "model": "sonar",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 2000
            },
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"Erreur: HTTP {resp.status_code}"
    except Exception as e:
        return f"Erreur: {str(e)}"

def call_perplexity_with_image(prompt: str, image_bytes: bytes) -> str:
    """Appel à l'API Perplexity avec analyse d'image"""
    if not PERPLEXITY_API_KEY:
        return "Erreur: PERPLEXITY_API_KEY manquante"
    
    try:
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}"},
            json={
                "model": "sonar",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image",
                                "image": f"data:image/jpeg;base64,{image_base64}"
                            }
                        ]
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            },
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"Erreur: HTTP {resp.status_code}"
    except Exception as e:
        return f"Erreur analyse image: {str(e)}"

# ═══════════════════════════════════════════════════════════════════
# IMAGE PROCESSING
# ═══════════════════════════════════════════════════════════════════

def read_qr_from_image(image_bytes: bytes) -> str:
    """
    Décode un QR code via OpenCV (compatible Render sans libzbar).
    Remplace pyzbar qui nécessitait une dépendance système indisponible.
    """
    try:
        # Conversion bytes -> numpy array pour OpenCV
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return ""

        # Détection QR Code via OpenCV
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img)
        
        if data:
            return data.strip()
            
        return ""
    except Exception as e:
        return f"[QR_ERROR] {str(e)}"

def analyze_image_vision(image_bytes: bytes) -> str:
    """Analyse détaillée d'une photo d'équipement Somfy via Perplexity"""
    prompt = """Analyse cette photo d'equipement electrique Somfy en detail:
    1. TYPE DE MATERIEL: identifie le type (boitier commande, moteur, controleur, capteur, etc.)
    2. REFERENCES VISIBLES: lis tous les numeros, codes produit, references affichees sur l'equipement
    3. ETAT PHYSIQUE: couleur, dommages visibles, LED (allumees/eteintes), connecteurs
    4. RACCORDEMENTS: identifie les fils, bornes, connecteurs visibles et leur couleur
    5. SPECIFICATIONS: tension (16V DC), alimentation, indicateurs d'etat visibles
    6. SIGNES DE DEFAUT: traces de surchauffe, fils brules, corrosion, oxydation
    
    Reponse structuree et precise, sans commentaires superflus."""
    
    result = call_perplexity_with_image(prompt, image_bytes)
    return result

# ═══════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
def home():
    """Page d'accueil HTML"""
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Somfy Diagnostic API</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
            }
            .container {
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            h1 {
                color: #667eea;
                margin: 0 0 10px 0;
            }
            .status {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 18px;
                margin: 15px 0;
            }
            .status-dot {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #22c55e;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .endpoint {
                background: #f5f5f5;
                border-left: 4px solid #667eea;
                padding: 15px;
                margin: 15px 0;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
            }
            .endpoint strong {
                color: #667eea;
            }
            .info {
                background: #e0f2fe;
                border: 1px solid #0284c7;
                padding: 12px;
                border-radius: 6px;
                margin: 15px 0;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 Somfy Diagnostic API</h1>
            <div class="status">
                <div class="status-dot"></div>
                <span><strong>EN LIGNE</strong> - Service opérationnel</span>
            </div>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            
            <h2>Endpoints disponibles</h2>
            
            <div class="endpoint">
                <strong>POST /analyze</strong><br>
                Analyse d'une panne avec image (QR code + vision)
            </div>
            
            <div class="endpoint">
                <strong>GET /health</strong><br>
                Vérification de l'état du service
            </div>
            
            <div class="info">
                <strong>ℹ️ Version:</strong> OpenCV Edition (Python 3.13, Render-Native)<br>
                <strong>🎯 Fonctionnalités:</strong> Lecture QR Code (OpenCV), Analyse image (Perplexity), Diagnostic IA
            </div>
            
            <h2>Utilisation</h2>
            <p>Envoyez une requête POST à <code>/analyze</code> avec:</p>
            <ul>
                <li><code>image</code> (file): Photo de l'équipement Somfy</li>
                <li><code>panne_description</code> (text): Description du problème</li>
            </ul>
        </div>
    </body>
    </html>
    """

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Vérification de l'état du service"""
    return HealthResponse(
        status="healthy",
        version="1.0.0-opencv",
        api_key_present=bool(PERPLEXITY_API_KEY),
        timestamp=datetime.now().isoformat()
    )

@app.post("/analyze", response_model=DiagnosticResponse)
async def analyze_panne(
    image: Optional[UploadFile] = File(None),
    panne_description: str = Form(...)
):
    """
    Endpoint principal: Diagnostic d'une panne Somfy
    - Lecture du QR code (si présent)
    - Analyse vision de l'équipement
    - Diagnostic IA via Perplexity
    """
    timestamp = datetime.now().isoformat()
    
    vision_result = ""
    qr_result = ""
    
    if image:
        content = await image.read()
        
        # 1. Tenter de lire QR code (via OpenCV)
        qr_result = read_qr_from_image(content)
        
        # 2. Analyse vision
        vision_result = analyze_image_vision(content)
    
    # 3. Construction du prompt final pour diagnostic
    final_prompt = f"""Tu es un expert Somfy en diagnostic de pannes d'équipements électriques.

CONTEXTE: Diagnostic d'une panne Somfy
DESCRIPTION UTILISATEUR: {panne_description}
ANALYSE VISION DE L'EQUIPEMENT: {vision_result if vision_result else "(Pas d'image fournie)"}
CODE / REFERENCE LU: {qr_result if qr_result else "(Pas de QR code détecté)"}

TACHE: 
1. Identifier la cause probable de la panne
2. Proposer des solutions de dépannage étape par étape
3. Lister les pièces/composants potentiellement à remplacer
4. Recommander si un intervention technique est nécessaire

Réponse structurée et actionnable."""
    
    final_response = call_perplexity(final_prompt)
    
    return DiagnosticResponse(
        status="success",
        timestamp=timestamp,
        result=final_response
    )

@app.post("/analyze-text")
async def analyze_text_only(panne_description: str = Form(...)):
    """
    Diagnostic basé sur la description textuelle uniquement
    (pour les cas sans photo)
    """
    timestamp = datetime.now().isoformat()
    
    prompt = f"""Tu es un expert Somfy en diagnostic de pannes.

DESCRIPTION DU PROBLEME: {panne_description}

Propose un diagnostic détaillé avec:
1. Causes probables
2. Solutions de dépannage
3. Pièces à vérifier/remplacer
4. Recommandations"""
    
    result = call_perplexity(prompt)
    
    return DiagnosticResponse(
        status="success",
        timestamp=timestamp,
        result=result
    )

@app.get("/version")
def get_version():
    """Retourne la version et les détails de l'app"""
    return {
        "name": "Somfy Diagnostic API",
        "version": "1.0.0",
        "edition": "OpenCV (No pyzbar/libzbar)",
        "python": "3.13.4",
        "platform": "Render Native",
        "features": [
            "QR Code detection (OpenCV)",
            "Image vision analysis (Perplexity)",
            "AI-powered diagnostics"
        ]
    }

# ═══════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Gestion globale des erreurs"""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

