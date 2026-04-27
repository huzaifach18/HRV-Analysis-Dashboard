// Chart instances
let rawChartInstance = null;
let filteredChartInstance = null;
let squaredChartInstance = null;
let mwiChartInstance = null;
let rrChartInstance = null;
let poincareChartInstance = null;
let psdChartInstance = null;

const API_BASE = "http://127.0.0.1:8000/api";

// Elements
const selector = document.getElementById("signal-selector");
const analyzeBtn = document.getElementById("analyze-btn");
const loading = document.getElementById("loading");
const badge = document.getElementById("current-badge");
const sympatheticStatus = document.getElementById("sympathetic-status");
const bannerStatus = document.querySelector(".banner-status");
const autonomicBanner = document.getElementById("autonomic-banner");

const fileUpload = document.getElementById("file-upload");
const uploadBtn = document.getElementById("upload-btn");

fileUpload.addEventListener("change", () => {
    uploadBtn.disabled = fileUpload.files.length === 0;
});

// Initialization
async function init() {
    try {
        const res = await fetch(`${API_BASE}/signals`);
        const signals = await res.json();
        
        selector.innerHTML = "";
        signals.forEach(sig => {
            const opt = document.createElement("option");
            opt.value = sig.id;
            opt.textContent = `Record ${sig.id} - ${sig.label}`;
            selector.appendChild(opt);
        });
        
        analyzeBtn.disabled = false;
        
        // Setup Chart defaults
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
    } catch (err) {
        console.error("Failed to load signals", err);
        selector.innerHTML = "<option disabled>Error loading</option>";
    }
}

// Format numbers
const fmt = (num) => typeof num === 'number' ? num.toFixed(2) : '--';

// Main Analyze Flow
analyzeBtn.addEventListener("click", async () => {
    const id = selector.value;
    if (!id) return;
    
    loading.classList.remove("hidden");
    analyzeBtn.disabled = true;
    
    try {
        const res = await fetch(`${API_BASE}/analyze/${id}`);
        const data = await res.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        updateMetrics(data);
        updateStatus(data);
        renderCharts(data);
        
        badge.textContent = data.label;
    } catch(err) {
        console.error(err);
        alert("Error analyzing signal");
    } finally {
        loading.classList.add("hidden");
        analyzeBtn.disabled = false;
    }
});

uploadBtn.addEventListener("click", async () => {
    const file = fileUpload.files[0];
    if (!file) return;

    loading.classList.remove("hidden");
    uploadBtn.disabled = true;
    
    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_BASE}/upload`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        
        if (!res.ok || data.error) {
            alert(data.error || data.detail || "Upload error");
            return;
        }
        
        updateMetrics(data);
        updateStatus(data);
        renderCharts(data);
        
        badge.textContent = data.label;
    } catch(err) {
        console.error(err);
        alert("Error analyzing uploaded file");
    } finally {
        loading.classList.add("hidden");
        uploadBtn.disabled = false;
    }
});

function updateMetrics(data) {
    document.getElementById("mean-rr").textContent = fmt(data.time_domain.mean_nni);
    document.getElementById("sdnn").textContent = fmt(data.time_domain.sdnn);
    document.getElementById("rmssd").textContent = fmt(data.time_domain.rmssd);
    document.getElementById("pnn50").textContent = fmt(data.time_domain.pnn50);
    
    document.getElementById("lf-power").textContent = fmt(data.frequency_domain.lf);
    document.getElementById("hf-power").textContent = fmt(data.frequency_domain.hf);
    document.getElementById("lf-hf").textContent = fmt(data.frequency_domain.lf_hf_ratio);
    
    document.getElementById("poincare-stats").innerHTML = `
        <div style="margin-bottom: 3px;">SD1: ${fmt(data.non_linear.sd1)} ms</div>
        <div style="margin-bottom: 3px;">SD2: ${fmt(data.non_linear.sd2)} ms</div>
        <div>SampEn: ${fmt(data.non_linear.sampen)}</div>
    `;
}

function updateStatus(data) {
    const lfhf = data.frequency_domain.lf_hf_ratio;
    const rmssd = data.time_domain.rmssd;
    let statusText = "";
    let className = "";
    
    if (lfhf > 2.0) {
        statusText = `<b>Sympathetic Dominance</b><br>High LF/HF ratio (${fmt(lfhf)}) indicates stress, exertion, or sympathetic activation.`;
        className = "sympathetic";
    } else if (rmssd > 50 || lfhf < 1.0) {
        statusText = `<b>Parasympathetic Dominance</b><br>High RMSSD and low LF/HF indicate strong vagal tone, rest, and recovery.`;
        className = "parasympathetic";
    } else {
        statusText = `<b>Balanced State</b><br>Normal sympathovagal balance.`;
        className = "parasympathetic"; // normal styling
    }
    
    // Update sidebar
    sympatheticStatus.innerHTML = statusText;
    sympatheticStatus.className = `status-indicator ${className}`;
    
    // Update banner
    autonomicBanner.classList.remove("hidden");
    bannerStatus.innerHTML = statusText.toUpperCase();
    bannerStatus.className = `status-indicator banner-status ${className}`;
}

function renderCharts(data) {
    // 1. Pipeline Charts
    const fs = data.fs;
    
    // Helper function to create a pipeline chart
    const createPipelineChart = (canvasId, instance, label, yData, color, peakIndices = null) => {
        const timeAxis = yData.map((_, i) => (i / fs).toFixed(2));
        if (instance) instance.destroy();
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        const datasets = [{
            label: label,
            data: yData,
            borderColor: color,
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.1
        }];
        
        if (peakIndices) {
            const peakData = yData.map((val, i) => peakIndices.includes(i) ? val : null);
            datasets.push({
                label: 'Detected Peaks',
                data: peakData,
                borderColor: '#ef4444',
                backgroundColor: '#ef4444',
                pointRadius: 5,
                pointStyle: 'crossRot',
                showLine: false
            });
        }

        return new Chart(ctx, {
            type: 'line',
            data: { labels: timeAxis, datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false, // disable animation for pipeline so it renders instantly
                scales: {
                    x: { display: false }, // hide x-axis for compactness
                    y: { display: true, grid: { color: 'rgba(255,255,255,0.05)' }}
                },
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                layout: { padding: 0 }
            }
        });
    };

    rawChartInstance = createPipelineChart('rawChart', rawChartInstance, 'Raw Signal', data.plots.raw_ecg, '#94a3b8');
    filteredChartInstance = createPipelineChart('filteredChart', filteredChartInstance, 'Bandpass Filtered', data.plots.filtered_ecg, '#3b82f6');
    squaredChartInstance = createPipelineChart('squaredChart', squaredChartInstance, 'Squared Derivative', data.plots.squared_ecg, '#f59e0b');
    mwiChartInstance = createPipelineChart('mwiChart', mwiChartInstance, 'MWI + Peaks', data.plots.mwi_ecg, '#10b981', data.plots.peaks_mwi);

    // 2. RR Intervals Chart
    const rr = data.plots.rr;
    if (rrChartInstance) rrChartInstance.destroy();
    const ctxRr = document.getElementById('rrChart').getContext('2d');
    rrChartInstance = new Chart(ctxRr, {
        type: 'line',
        data: {
            labels: rr.map((_, i) => i + 1),
            datasets: [{
                label: 'RR Interval (ms)',
                data: rr,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                pointRadius: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Beat Number' }, grid: { color: 'rgba(255,255,255,0.05)' }},
                y: { title: { display: true, text: 'RR (ms)' }, grid: { color: 'rgba(255,255,255,0.05)' }}
            },
            plugins: { legend: { display: false } }
        }
    });

    // 3. Poincare Plot
    const poincareData = [];
    for(let i=0; i<rr.length-1; i++) {
        poincareData.push({ x: rr[i], y: rr[i+1] });
    }
    
    // Calculate SD1 and SD2 lines (Perpendicular cross)
    const meanRR = data.time_domain.mean_nni;
    const sd1 = data.non_linear.sd1;
    const sd2 = data.non_linear.sd2;
    const s2 = 1.0 / Math.sqrt(2.0);
    
    // SD2 axis (along y = x)
    const sd2Line = [
        { x: meanRR - sd2 * s2, y: meanRR - sd2 * s2 },
        { x: meanRR + sd2 * s2, y: meanRR + sd2 * s2 }
    ];
    
    // SD1 axis (perpendicular, along y = -x + 2*meanRR)
    const sd1Line = [
        { x: meanRR + sd1 * s2, y: meanRR - sd1 * s2 },
        { x: meanRR - sd1 * s2, y: meanRR + sd1 * s2 }
    ];
    
    if (poincareChartInstance) poincareChartInstance.destroy();
    const ctxPoincare = document.getElementById('poincareChart').getContext('2d');
    poincareChartInstance = new Chart(ctxPoincare, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'RR(n) vs RR(n+1)',
                    data: poincareData,
                    backgroundColor: 'rgba(245, 158, 11, 0.8)',
                    pointRadius: 4
                },
                {
                    label: 'SD2 Axis (Long)',
                    data: sd2Line,
                    borderColor: '#3b82f6',
                    borderWidth: 3,
                    pointRadius: 0,
                    showLine: true
                },
                {
                    label: 'SD1 Axis (Short)',
                    data: sd1Line,
                    borderColor: '#ef4444',
                    borderWidth: 3,
                    pointRadius: 0,
                    showLine: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'RR(n) (ms)' }, grid: { color: 'rgba(255,255,255,0.05)' }},
                y: { title: { display: true, text: 'RR(n+1) (ms)' }, grid: { color: 'rgba(255,255,255,0.05)' }}
            },
            plugins: { legend: { display: false } }
        }
    });

    // 4. PSD Chart
    const f = data.frequency_domain.psd_f;
    const pxx = data.frequency_domain.psd_p;
    
    if (psdChartInstance) psdChartInstance.destroy();
    const ctxPsd = document.getElementById('psdChart').getContext('2d');
    
    // We can highlight LF and HF bands by using chart backgrounds, but simplest is linear line plot
    psdChartInstance = new Chart(ctxPsd, {
        type: 'line',
        data: {
            labels: f.map(val => val.toFixed(3)),
            datasets: [{
                label: 'Power Spectral Density',
                data: pxx,
                borderColor: '#a855f7',
                backgroundColor: 'rgba(168, 85, 247, 0.2)',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { 
                    title: { display: true, text: 'Frequency (Hz)' }, 
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    min: 0,
                    max: 0.5 // usually interested in 0 to 0.4 / 0.5 Hz
                },
                y: { title: { display: true, text: 'Power (ms²/Hz)' }, grid: { color: 'rgba(255,255,255,0.05)' }}
            },
            plugins: { legend: { display: false } }
        }
    });
}

// Start
init();
