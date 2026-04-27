from fastapi import FastAPI, HTTPException, UploadFile, File
import tempfile
import numpy as np
import scipy.io
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .hrv_analyzer import HRVAnalyzer
import os

app = FastAPI(title="ECG HRV Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mat_file_path = os.path.join("C:\\", "Users", "chhuz", "OneDrive", "Desktop", "BSP OEL 1", "ECGData.mat")
analyzer = None

@app.on_event("startup")
def startup_event():
    global analyzer
    if os.path.exists(mat_file_path):
        analyzer = HRVAnalyzer(mat_file_path)
    else:
        print(f"Dataset not found at {mat_file_path}")

@app.get("/api/signals")
def get_signals():
    if not analyzer:
        raise HTTPException(status_code=500, detail="Data not loaded")
    return analyzer.get_signal_list()

@app.get("/api/analyze/{signal_id}")
def analyze_signal(signal_id: int):
    if not analyzer:
        raise HTTPException(status_code=500, detail="Data not loaded")
    try:
        results = analyzer.analyze(signal_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not analyzer:
        raise HTTPException(status_code=500, detail="Base analyzer not loaded")
    
    try:
        content = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith(".csv") or filename.endswith(".txt") or filename.endswith(".dat"):
            try:
                txt_str = content.decode("utf-8").strip()
                txt_str = txt_str.replace(',', ' ').split()
                sig = np.array([float(x) for x in txt_str])
            except UnicodeDecodeError:
                # If it fails to decode as text, assume it's a raw binary float array
                sig = np.frombuffer(content, dtype=np.float64)
                if len(sig) < 100:
                    sig = np.frombuffer(content, dtype=np.float32)
            label = f"Custom File: {file.filename}"
            
        elif filename.endswith(".mat"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mat") as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            
            mat = scipy.io.loadmat(tmp_path, squeeze_me=False)
            os.unlink(tmp_path)
            
            if 'ECGData' in mat:
                sig = mat['ECGData']['Data'][0,0][0]
            else:
                for key in mat:
                    if not key.startswith('__') and isinstance(mat[key], np.ndarray):
                        candidate = np.squeeze(mat[key])
                        if candidate.ndim == 1 and len(candidate) > 100:
                            sig = candidate
                            break
                else:
                    raise ValueError("Could not find a valid 1D signal array in the .mat file")
            label = f"Custom MAT: {file.filename}"
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload .csv, .txt, .mat, or .dat")
            
        results = analyzer.analyze_raw(sig, label)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload Error: {str(e)}")

# Mount frontend directory for static UI serving
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))
