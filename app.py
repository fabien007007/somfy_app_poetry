from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def call_perplexity(prompt: str) -> str:
    if not PERPLEXITY_API_KEY:
        return "❌ PERPLEXITY_API_KEY manquante"
    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}"},
            json={"model": "sonar", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 2000},
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"❌ HTTP {resp.status_code}"
    except Exception as e:
        return f"❌ {str(e)}"

def call_perplexity_with_image(prompt: str, image_base64: str) -> str:
    if not PERPLEXITY_API_KEY:
        return "❌ PERPLEXITY_API_KEY manquante"
    try:
        clean_image = image_base64.split(',')[1] if ',' in image_base64 else image_base64
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}"},
            json={
                "model": "sonar",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "image": f"data:image/jpeg;base64,{clean_image}"}
                    ]
                }],
                "temperature": 0.7,
                "max_tokens": 2000
            },
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"❌ HTTP {resp.status_code}"
    except Exception as e:
        return f"❌ {str(e)}"

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SOMFY Diagnostic AI</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <script src="https://cdn.jsdelivr.net/npm/jsqr/dist/jsQR.js"></script>
    <style>
        body { background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%); padding: 20px; min-height: 100vh; }
        .navbar-custom { background: linear-gradient(90deg, #3b82f6 0%, #1e40af 100%); }
        .card-diagnostic { border: none; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
        .btn-photo { border: 2px solid #3b82f6; color: #3b82f6; background: white; padding: 1rem; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .btn-photo:hover { background: #3b82f6; color: white; }
        .btn-diagnostic { background: linear-gradient(90deg, #3b82f6 0%, #1e40af 100%); color: white; padding: 0.75rem 2rem; border: none; border-radius: 8px; font-weight: 600; width: 100%; }
        .result-box { background: #f9fafb; border-left: 4px solid #3b82f6; padding: 1.5rem; border-radius: 8px; white-space: pre-wrap; word-wrap: break-word; font-family: monospace; font-size: 0.9rem; max-height: 600px; overflow-y: auto; }
        .preview-image { max-width: 100%; max-height: 250px; border-radius: 8px; margin-top: 1rem; }
        .btn-group-custom { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; }
        @media (max-width: 576px) { .btn-group-custom { grid-template-columns: 1fr; } }
        input[type="file"] { display: none; }
    </style>
</head>
<body>
    <nav class="navbar navbar-custom navbar-expand-lg sticky-top">
        <div class="container"><span class="navbar-brand text-white"><i class="bi bi-lightning-fill"></i> SOMFY Diagnostic AI</span></div>
    </nav>

    <div class="container" style="max-width: 900px; margin-top: 30px;">
        <div class="card card-diagnostic">
            <div class="card-header" style="background: linear-gradient(90deg, #3b82f6 0%, #1e40af 100%); color: white; padding: 1.5rem;">
                <h3 style="margin: 0;"><i class="bi bi-tools"></i> Diagnostic électrique Somfy</h3>
                <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">Analyse photo + QR code + description</p>
            </div>
            
            <div class="card-body" style="padding: 2rem;">
                <form id="diagnosticForm">
                    <div class="mb-3">
                        <label class="form-label"><i class="bi bi-camera"></i> Photo</label>
                        <div class="btn-group-custom">
                            <button type="button" class="btn-photo" onclick="document.getElementById('cameraInput').click()">
                                <i class="bi bi-camera"></i> Prendre une photo
                            </button>
                            <button type="button" class="btn-photo" onclick="document.getElementById('uploadInput').click()">
                                <i class="bi bi-upload"></i> Uploader une photo
                            </button>
                        </div>
                        <input type="file" id="cameraInput" accept="image/*" capture="environment" onchange="handleImageCapture(event)">
                        <input type="file" id="uploadInput" accept="image/*" onchange="handleImageUpload(event)">
                        <div id="imagePreviewContainer"></div>
                    </div>

                    <div class="mb-3">
                        <label class="form-label"><i class="bi bi-qr-code"></i> QR code</label>
                        <button type="button" class="btn-photo w-100" onclick="toggleQRScanner()" id="qrButton">
                            <i class="bi bi-qr-code"></i> Démarrer scanner QR
                        </button>
                        <video id="qrVideo" style="max-width: 100%; max-height: 300px; border-radius: 8px; margin-top: 1rem; display: none;"></video>
                        <div id="qrResultContainer"></div>
                    </div>

                    <div class="mb-3">
                        <label for="description" class="form-label"><i class="bi bi-pencil-square"></i> Description panne</label>
                        <textarea class="form-control" id="description" rows="4" placeholder="Décrivez le problème observé..." maxlength="500"></textarea>
                        <small class="text-muted d-block mt-2"><span id="charCount">0</span>/500</small>
                    </div>

                    <button type="submit" class="btn btn-diagnostic"><i class="bi bi-play-circle"></i> Lancer diagnostic</button>
                </form>
                <div id="resultContainer"></div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let currentImageBase64 = null;
        let qrScanning = false;

        document.getElementById('description').addEventListener('input', function() {
            document.getElementById('charCount').textContent = this.value.length;
        });

        function handleImageCapture(event) {
            const file = event.target.files[0];
            if (file) readAndPreviewImage(file);
            event.target.value = '';
        }

        function handleImageUpload(event) {
            const file = event.target.files[0];
            if (file) readAndPreviewImage(file);
            event.target.value = '';
        }

        function readAndPreviewImage(file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                currentImageBase64 = e.target.result;
                const container = document.getElementById('imagePreviewContainer');
                container.innerHTML = '<img src="' + currentImageBase64 + '" class="preview-image"><div class="alert alert-success mt-2"><i class="bi bi-check-circle"></i> Photo prête</div>';
            };
            reader.readAsDataURL(file);
        }

        function toggleQRScanner() {
            qrScanning = !qrScanning;
            const video = document.getElementById('qrVideo');
            const button = document.getElementById('qrButton');
            
            if (qrScanning) {
                video.style.display = 'block';
                button.innerHTML = '<i class="bi bi-stop-circle"></i> Arrêter scanner';
                navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
                    .then(stream => {
                        video.srcObject = stream;
                        video.play();
                        scanQRCode(video);
                    })
                    .catch(err => {
                        document.getElementById('qrResultContainer').innerHTML = '<div class="alert alert-danger mt-2">Erreur caméra: ' + err.message + '</div>';
                        stopQRScanner();
                    });
            } else {
                stopQRScanner();
            }
        }

        function stopQRScanner() {
            qrScanning = false;
            const video = document.getElementById('qrVideo');
            const button = document.getElementById('qrButton');
            video.style.display = 'none';
            button.innerHTML = '<i class="bi bi-qr-code"></i> Démarrer scanner QR';
            if (video.srcObject) {
                video.srcObject.getTracks().forEach(track => track.stop());
            }
        }

        function scanQRCode(video) {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            function scan() {
                if (!qrScanning) return;
                if (video.videoWidth === 0) {
                    setTimeout(scan, 100);
                    return;
                }
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                ctx.drawImage(video, 0, 0);
                try {
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    const code = jsQR(imageData.data, canvas.width, canvas.height);
                    if (code) {
                        document.getElementById('description').value = code.data;
                        document.getElementById('charCount').textContent = code.data.length;
                        document.getElementById('qrResultContainer').innerHTML = '<div class="alert alert-success mt-2"><i class="bi bi-check-circle"></i> QR: <strong>' + code.data + '</strong></div>';
                        stopQRScanner();
                        return;
                    }
                } catch (e) {}
                setTimeout(scan, 100);
            }
            scan();
        }

        document.getElementById('diagnosticForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const description = document.getElementById('description').value.trim();
            const resultContainer = document.getElementById('resultContainer');

            if (!currentImageBase64 && !description) {
                resultContainer.innerHTML = '<div class="alert alert-warning mt-3">Veuillez fournir une photo ou une description</div>';
                return;
            }

            const btn = this.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Analyse...';

            try {
                const formData = new FormData();
                if (currentImageBase64) formData.append('image', currentImageBase64);
                formData.append('description', description);
                formData.append('timestamp', new Date().toISOString());

                const response = await fetch('/diagnose', { method: 'POST', body: formData });
                const data = await response.json();
                
                if (data.status === 'success') {
                    resultContainer.innerHTML = '<div class="alert alert-success mt-3"><i class="bi bi-check-circle"></i> Diagnostic complété</div><div class="result-box">' + escapeHtml(data.result) + '</div>';
                } else {
                    resultContainer.innerHTML = '<div class="alert alert-danger mt-3">❌ ' + escapeHtml(data.result) + '</div>';
                }
            } catch (error) {
                resultContainer.innerHTML = '<div class="alert alert-danger mt-3">❌ Erreur: ' + escapeHtml(error.message) + '</div>';
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-play-circle"></i> Lancer diagnostic';
            }
        });

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""

@app.post("/diagnose")
async def diagnose(description: str = Form(""), image: str = Form(None), timestamp: str = Form("")):
    try:
        if not description.strip() and not image:
            return JSONResponse({"status": "error", "result": "Description ou image requise"}, status_code=400)

        prompt_parts = [
            "=== DIAGNOSTIC TECHNIQUE SOMFY ===",
            f"Timestamp: {timestamp}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "[DESCRIPTION UTILISATEUR]",
            description if description.strip() else "Aucune description fournie",
            "",
        ]

        image_analysis = ""
        if image:
            image_analysis = call_perplexity_with_image(
                "Analyse cette photo d'équipement Somfy:\n1) TYPE: boîtier/moteur/contrôleur?\n2) RÉFÉRENCES: numéros visibles\n3) ÉTAT: dommages/LED/connecteurs\n4) RACCORDEMENTS: fils/bornes\n5) ALIMENTATION: 16V DC ou autre",
                image
            )
            prompt_parts.append("[ANALYSE IMAGE]")
            prompt_parts.append(image_analysis)
            prompt_parts.append("")

        diagnostic_prompt = "\n".join(prompt_parts) + """

DIAGNOSTIC TECHNIQUE COMPLET avec:
1. IDENTIFICATION: Type équipement, modèle, références
2. ANALYSE: État électrique, connexions, alimentation
3. PROBLÈMES: Liste défauts détectés
4. CAUSES: Analyse causes possibles
5. SOLUTIONS: Actions correctives détaillées
6. VÉRIFICATIONS: Tests à effectuer
7. ESCALADE: Si besoin support Somfy

Réponse structurée, professionnelle."""

        diagnosis = call_perplexity(diagnostic_prompt)

        return JSONResponse({
            "status": "success",
            "result": diagnosis,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return JSONResponse({"status": "error", "result": f"Erreur: {str(e)}"}, status_code=500)

@app.get("/health")
async def health():
    return {"status": "ok", "perplexity": "✅" if PERPLEXITY_API_KEY else "❌"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
