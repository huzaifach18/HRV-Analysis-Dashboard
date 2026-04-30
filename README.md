# CardioVision - Clinical ECG & HRV Analysis Dashboard

![Dashboard Preview](https://img.shields.io/badge/Status-Active-success) ![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688)

CardioVision is a professional, modern web dashboard for physiological signal analysis, specializing in Electrocardiogram (ECG) processing and Heart Rate Variability (HRV) metrics extraction. It features a custom backend built with Python (FastAPI) and a sleek, glassmorphic frontend utilizing vanilla JavaScript and Chart.js.

## Features

- **Pan-Tompkins Algorithm Pipeline**: Step-by-step visualization of ECG signal processing, including bandpass filtering, derivative calculation, squaring, and moving window integration.
- **Comprehensive HRV Metrics**:
  - *Time Domain*: Mean RR, SDNN, RMSSD, pNN50.
  - *Frequency Domain*: LF Power, HF Power, LF/HF Ratio via Power Spectral Density (PSD).
  - *Non-Linear*: Poincaré plot geometry (SD1, SD2) and Sample Entropy (SampEn).
- **Autonomic Nervous System Assessment**: Real-time evaluation of the sympathovagal balance.
- **Interactive Visualizations**: Dynamic charts with zooming and panning capabilities using Chart.js.
- **Dataset Flexibility**: 
  - Direct integration with the PhysioNet MIT-BIH Arrhythmia Database.
  - Support for local custom dataset uploads (`.mat`, `.csv`, `.txt`, `.dat`).
- **Medical Report Generation**: Export detailed clinical reports in PDF format.
- **Adjustable Signal Processing**: Configurable filter order and cutoff frequencies.

## Project Structure

```
BSP OEL 1/
│
├── backend/
│   ├── main.py            # FastAPI application and route definitions
│   └── hrv_analyzer.py    # Core signal processing and HRV extraction logic
│
├── frontend/
│   ├── index.html         # Main dashboard interface
│   ├── style.css          # Glassmorphic and modern UI styling
│   └── app.js             # Client-side logic, API calls, and Chart.js rendering
│
└── README.md              # Project documentation
```

## Technologies Used

- **Backend**: Python, FastAPI, NumPy, SciPy, WFDB (PhysioNet data).
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla), Chart.js (with zoom plugin), html2pdf.js.

## Installation

1. **Clone or download the repository.**

2. **Set up a Python virtual environment (Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the required Python dependencies:**
   ```bash
   pip install fastapi uvicorn numpy scipy wfdb python-multipart
   ```

## Running the Application

1. **Start the FastAPI server:**
   From the root directory of the project, run:
   ```bash
   uvicorn backend.main:app --reload
   ```

2. **Access the Dashboard:**
   Open your web browser and navigate to:
   ```
   http://127.0.0.1:8000
   ```

## Usage

- **Built-in Records**: Select an MIT-BIH dataset from the dropdown and click "Analyze Signal".
- **Custom Uploads**: Use the file upload input to process your own ECG data. Supported formats are `.mat` (must contain a 1D signal array), `.csv`, `.txt`, or `.dat`.
- **Exporting**: Fill out the patient information and click "Export PDF" to generate and download a comprehensive clinical report.

## License
MIT License
