from fastapi import FastAPI, UploadFile, Form, File, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import base64
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
from pyzbar.pyzbar import decode as decode_qr
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

class DiagnosticMobileRequest(BaseModel):
    image: Optional[str] = None
    panne_description: str
    timestamp: str

class DiagnosticResponse(BaseModel):
    status: str
    timestamp: str
    result: str

def call_perplexity(prompt: str) -> str:
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

def read_qr_from_image(image_bytes: bytes) -> str:
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        codes = decode_qr(img)
        if not codes:
            return ""
        data = codes[0].data.decode("utf-8", errors="ignore").strip()
        return data
    except Exception as e:
        return f"[QR_ERROR] {str(e)}"

def analyze_image_vision(image_bytes: bytes) -> str:
    prompt = """Analyse cette photo d'equipement electrique Somfy en detail:
    
1. TYPE DE MATERIEL: identifie le type (boitier commande, moteur, controleur, etc.)
2. REFERENCES VISIBLES: lis tous les numeros, codes produit, references affichees
3. ETAT PHYSIQUE: couleur, dommages visibles, LED (allumees/eteintes), connecteurs
4. RACCORDEMENTS: identifie les fils, bornes, connecteurs visibles
5. SPECIFICATIONS: 16V DC, alimentation, indicateurs d'etat visibles

Reponse structuree et claire, sans commentaires superflus."""
    
    result = call_perplexity_with_image(prompt, image_bytes)
    return result

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Somfy Diagnostic</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Arial; background: #f5f5f5; padding: 20px; }
.container { max-width: 900px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
h1 { color: #667eea; margin-bottom: 10px; }
.subtitle { color: #999; margin-bottom: 25px; }
.form-group { margin-bottom: 20px; }
label { display: block; font-weight: bold; margin-bottom: 8px; }
.photo-section { display: flex; gap: 10px; margin-bottom: 20px; }
.photo-btn {
  flex: 1;
  padding: 15px;
  border: 2px solid #667eea;
  background: white;
  color: #667eea;
  border-radius: 5px;
  font-weight: bold;
  cursor: pointer;
  font-size: 14px;
}
.photo-btn:hover { background: #667eea; color: white; }
.photo-btn.active { background: #667eea; color: white; }
input[type="file"] { display: none; }
textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 5px;
  min-height: 80px;
  resize: vertical;
  font-family: Arial;
  font-size: 14px;
}
textarea:focus { outline: none; border-color: #667eea; }
.button-submit {
  padding: 12px 30px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: bold;
  font-size: 14px;
}
.button-submit:hover { background: #5568d3; }
#loading {
  display: none;
  text-align: center;
  padding: 30px;
  color: #667eea;
}
.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 10px;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
#result {
  display: none;
  margin-top: 30px;
  padding: 20px;
  background: #f9f9f9;
  border-left: 4px solid #667eea;
  border-radius: 5px;
  white-space: normal;
  line-height: 1.6;
  font-size: 14px;
  max-height: 600px;
  overflow-y: auto;
}
#result h2 {
  color: #667eea;
  margin-top: 25px;
  margin-bottom: 15px;
  font-size: 1.3em;
  border-bottom: 2px solid #667eea;
  padding-bottom: 8px;
}
#result h2:first-child { margin-top: 0; }
#result h3 {
  color: #555;
  margin-top: 15px;
  margin-bottom: 10px;
}
#result p {
  margin-bottom: 12px;
}
#result ul {
  margin-left: 25px;
  margin-bottom: 12px;
}
#result li {
  margin-bottom: 8px;
}
#result strong {
  color: #667eea;
}
#result hr {
  border: none;
  border-top: 2px solid #ddd;
  margin: 25px 0;
}
</style>
</head>
<body>
<div class="container">
  <h1>SOMFY Diagnostic AI</h1>
  <p class="subtitle">Diagnostic électrique avec analyse photo + QR code</p>

  <div class="form-group">
    <label>Photo (optionnel mais recommandé)</label>
    <div class="photo-section">
      <button type="button" class="photo-btn" id="camera-btn">Prendre une photo</button>
      <button type="button" class="photo-btn" id="upload-btn">Uploader une photo</button>
    </div>
    <input type="file" id="camera-input" accept="image/*" capture="environment" />
    <input type="file" id="upload-input" accept="image/*" />
    <div id="photo-status" style="margin-top:10px;color:#999;"></div>
  </div>

  <div class="form-group">
    <label>Description panne (optionnel)</label>
    <textarea id="panne" placeholder="Ex: Aucun mouvement, LED éteinte..."></textarea>
  </div>

  <button type="button" class="button-submit" id="submit-btn">Lancer diagnostic</button>

  <div id="loading">
    <div class="spinner"></div>
    <p>Diagnostic en cours (analyse photo + traitement)...</p>
  </div>

  <div id="result"></div>
</div>

<script>
  let photoFile = null;

  document.getElementById('camera-btn').addEventListener('click', function(e) {
    e.preventDefault();
    document.getElementById('camera-input').click();
  });

  document.getElementById('upload-btn').addEventListener('click', function(e) {
    e.preventDefault();
    document.getElementById('upload-input').click();
  });

  document.getElementById('camera-input').addEventListener('change', function(e) {
    photoFile = this.files[0];
    document.getElementById('photo-status').textContent = 'Photo: ' + photoFile.name;
    document.getElementById('camera-btn').classList.add('active');
    document.getElementById('upload-btn').classList.remove('active');
  });

  document.getElementById('upload-input').addEventListener('change', function(e) {
    photoFile = this.files[0];
    document.getElementById('photo-status').textContent = 'Photo: ' + photoFile.name;
    document.getElementById('upload-btn').classList.add('active');
    document.getElementById('camera-btn').classList.remove('active');
  });

  document.getElementById('submit-btn').addEventListener('click', function(e) {
    e.preventDefault();

    let panne = document.getElementById('panne').value;
    let loading = document.getElementById('loading');
    let result = document.getElementById('result');

    loading.style.display = 'block';
    result.style.display = 'none';

    let formData = new FormData();
    if (photoFile) {
      formData.append('image', photoFile);
    }
    formData.append('panne_description', panne);

    fetch('/diagnostic', {method: 'POST', body: formData})
      .then(response => {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.text();
      })
      .then(data => {
        let html = data
          .replace(/### (.*?)\\n?/g, '<h3>$1</h3>')
          .replace(/## (.*?)\\n?/g, '<h2>$1</h2>')
          .replace(/\\n---\\n/g, '<hr>')
          .replace(/\\n- (.*?)(?=\\n|$)/g, '<li>$1</li>')
          .replace(/\\n\\n+/g, '</p><p>')
          .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');

        html = '<p>' + html.replace(/(<h[23]>|<hr>|<ul>|<ol>|<li>)/g,'</p>$1').replace(/<\\/li>/g,'</li><p>') + '</p>';
        html = html.replace(/(<p>\\s*)+(?=<(h[23]|ul|ol|li|hr)>)/g, '');
        html = html.replace(/<p>\\s*<\\/p>/g, '');
        html = html.replace(/<\\/li><p>/g, '</li>');
        html = html.replace(/<hr><p>/g, '<hr>');
        html = html.replace(/<p><ul>/g,'<ul>').replace(/<\\/ul><\\/p>/g,'</ul>');

        result.innerHTML = html;
        result.style.display = 'block';
        loading.style.display = 'none';
      })
      .catch(err => {
        alert('Erreur: ' + err.message);
        loading.style.display = 'none';
      });
  });
</script>

</body>
</html>"""

@app.post("/diagnostic")
async def diagnostic(request: Request):
    form = await request.form()
    image_file = form.get('image')
    panne_description = form.get('panne_description', '')

    image_info = "Pas de photo fournie"
    vision_analysis = ""
    qr_info = ""
    qr_text = ""
    image_bytes = None

    if image_file and image_file.filename:
        image_bytes = await image_file.read()
        image_info = f"Photo fournie: {image_file.filename}"
        
        vision_analysis = analyze_image_vision(image_bytes)
        
        qr_text = read_qr_from_image(image_bytes)
        if qr_text:
            if qr_text.startswith("[QR_ERROR]"):
                qr_info = f"Lecture QR code: ERREUR"
            else:
                qr_info = f"QR code detecte: {qr_text}"
        else:
            qr_info = "QR code: non present"

    prompt = f"""Tu es electricien Somfy expert specialise en diagnostic electrique.

{image_info}

ANALYSE VISUELLE DE L'IMAGE FOURNIE:
{vision_analysis if vision_analysis else "Pas d'image"}

{qr_info}

DESCRIPTION PANNE CLIENT:
{panne_description if panne_description else "Non decrite"}

BASES DU DIAGNOSTIC:
- Type d'equipement Somfy identifie
- References produit, numeros de serie
- Etat physique observe
- Raccordements visibles

Fournis un diagnostic complet STRUCTURE avec:

## 1. IDENTIFICATION EQUIPEMENT
Confirm le type, modele, reference (d'apres la photo si fournie)

## 2. OBSERVATIONS VISUELLES
État physique, LED, indicateurs

## 3. VERIFICATIONS SECURITE OBLIGATOIRES
- Couper alimentation 230V AC
- Verifier absence de tension (testeur VDE)
- EPI et mise a la terre
- Ne pas intervenir sous tension

## 4. TESTS DIAGNOSTIC
- Tension 16V DC bus IB/IB+ (14-18V nominal)
- Continuite fils bus et commandes
- Presence alimentation 24V DC si capteurs

## 5. LOCALISATION PANNE PROBABLE
D'apres observations visuelles et description

## 6. ACTIONS CORRECTIVES
Etapes precises pour regler

## 7. AVERTISSEMENTS IMPORTANTS
Risques et interdictions.

IMPORTANT: Diagnostic pratique et precis, pour technicien Somfy."""
    
    result = call_perplexity(prompt)
    return result

@app.post("/api/diagnostic-mobile", response_model=DiagnosticResponse)
async def diagnostic_mobile(req: DiagnosticMobileRequest):
    image_bytes = None
    
    if req.image:
        try:
            image_bytes = base64.b64decode(req.image)
        except Exception as e:
            return DiagnosticResponse(
                status="error",
                timestamp=req.timestamp,
                result=f"Erreur decodage image: {str(e)}"
            )
    
    image_info = "Pas de photo fournie"
    vision_analysis = ""
    qr_info = ""
    qr_text = ""

    if image_bytes:
        image_info = "Photo fournie"
        vision_analysis = analyze_image_vision(image_bytes)
        qr_text = read_qr_from_image(image_bytes)
        
        if qr_text:
            if qr_text.startswith("[QR_ERROR]"):
                qr_info = f"QR: ERREUR"
            else:
                qr_info = f"QR detecte: {qr_text}"
        else:
            qr_info = "QR: absent"

    prompt = f"""Tu es electricien Somfy expert specialise en diagnostic electrique.

{image_info}
{qr_info if qr_info else ""}

ANALYSE VISUELLE:
{vision_analysis if vision_analysis else "Pas d'image"}

DESCRIPTION PANNE:
{req.panne_description if req.panne_description else "Non decrite"}

Fournis un diagnostic complet STRUCTURE avec:
1. IDENTIFICATION EQUIPEMENT
2. OBSERVATIONS VISUELLES
3. VERIFICATIONS SECURITE OBLIGATOIRES
4. TESTS DIAGNOSTIC
5. LOCALISATION PANNE PROBABLE
6. ACTIONS CORRECTIVES
7. AVERTISSEMENTS IMPORTANTS

IMPORTANT: Diagnostic pratique et precis."""
    
    result = call_perplexity(prompt)
    
    return DiagnosticResponse(
        status="success",
        timestamp=req.timestamp,
        result=result
    )

@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
