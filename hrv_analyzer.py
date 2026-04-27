import numpy as np
import scipy.signal as signal
import scipy.io

class HRVAnalyzer:
    def __init__(self, mat_path):
        self.mat_path = mat_path
        mat = scipy.io.loadmat(self.mat_path, squeeze_me=False)
        data = mat['ECGData']
        self.ecg_data = data['Data'][0,0]
        self.ecg_labels = [str(x[0]) for x in data['Labels'][0,0]]
        self.num_signals = self.ecg_data.shape[0]

    def get_signal_list(self):
        return [{"id": i, "label": self.ecg_labels[i]} for i in range(self.num_signals)]

    def estimate_fs(self, sig):
        peaks, _ = signal.find_peaks(sig, distance=30, prominence=0.2)
        if len(peaks) < 10:
            return 128.0
        med_rr_samples = np.median(np.diff(peaks))
        # Assuming average resting RR interval is ~0.75 to 0.85 seconds
        estimated_fs = med_rr_samples / 0.8 
        standard_fs = [100, 125, 128, 200, 250, 300, 360, 500, 1000]
        return float(min(standard_fs, key=lambda x: abs(x - estimated_fs)))

    def sample_entropy(self, U, m=2, r=None):
        if len(U) < m + 1:
            return 0.0
        if r is None:
            r = 0.2 * np.std(U, ddof=1)
        
        def _phi(m_len):
            x = np.array([U[i:i+m_len] for i in range(len(U) - m_len + 1)])
            # Vectorized Chebyshev distance
            dist = np.max(np.abs(x[:, None, :] - x[None, :, :]), axis=2)
            # Count matches, subtract 1 for self-match
            counts = np.sum(dist <= r, axis=0) - 1
            return np.sum(counts)
        
        B = _phi(m)
        A = _phi(m+1)
        
        if A == 0 or B == 0:
            return 0.0
        return -np.log(A / B)

    def analyze_raw(self, sig, label):
        fs = self.estimate_fs(sig)
        
        # For visualization, keep raw signal
        raw_sig = np.copy(sig)
        
        # Step 0: Normalization
        sig = sig - np.mean(sig)
        sig_std = np.std(sig)
        if sig_std > 0:
            sig = sig / sig_std
            
        # Step 1: Pan-Tompkins Bandpass Filter (5 - 15 Hz)
        # Isolates QRS complex
        nyq = 0.5 * fs
        b, a = signal.butter(3, [5.0 / nyq, 15.0 / nyq], btype='band')
        filtered_sig = signal.filtfilt(b, a, sig)
        
        # Step 2: Derivative
        derivative_sig = np.gradient(filtered_sig)
        
        # Step 3: Squaring
        squared_sig = derivative_sig ** 2
        
        # Step 4: Moving Window Integration (MWI) (150ms)
        mwi_window = max(1, int(0.15 * fs))
        from scipy.ndimage import uniform_filter1d
        mwi_sig = uniform_filter1d(squared_sig, size=mwi_window) * mwi_window
        
        # Step 5: Peak Detection on MWI
        # Prominence set to 50% of the mean to catch varying beats
        peaks_mwi, _ = signal.find_peaks(mwi_sig, distance=int(0.4*fs), prominence=0.5 * np.mean(mwi_sig))
        
        # Refine peaks: Map back to the exact R-peak on the filtered signal
        peaks = []
        search_window = int(0.1 * fs)
        for p in peaks_mwi:
            start = max(0, p - search_window)
            end = min(len(filtered_sig), p + search_window)
            if start < end:
                # Find maximum in the original filtered signal
                local_peak = start + np.argmax(filtered_sig[start:end])
                peaks.append(local_peak)
                
        peaks = np.array(peaks)
        
        if len(peaks) < 2:
            return {"error": "Not enough peaks found"}
            
        rr_intervals = np.diff(peaks) / fs # in seconds
        rr_intervals_ms = rr_intervals * 1000 # in ms
        
        # ECTOPIC BEAT REMOVAL (Interpolation / Extrapolation)
        if len(rr_intervals_ms) > 5:
            valid_mask = np.ones(len(rr_intervals_ms), dtype=bool)
            # Use a median filter of size 5 to find local baseline
            med_rr = signal.medfilt(rr_intervals_ms, kernel_size=5)
            
            # An RR interval varying > 20% from local median is considered ectopic/artifact
            diff_ratio = np.abs(rr_intervals_ms - med_rr) / med_rr
            ectopic_indices = np.where(diff_ratio > 0.20)[0]
            valid_mask[ectopic_indices] = False
            
            # If ectopic beats are found but not all beats are ectopic
            if np.any(valid_mask) and not np.all(valid_mask):
                valid_idx = np.where(valid_mask)[0]
                all_idx = np.arange(len(rr_intervals_ms))
                # np.interp natively interpolates between points and extrapolates flat values at the edges
                rr_intervals_ms = np.interp(all_idx, valid_idx, rr_intervals_ms[valid_mask])
                # Back-calculate rr_intervals in seconds for cumulative sum (t array) in PSD
                rr_intervals = rr_intervals_ms / 1000.0
        
        # TIME DOMAIN
        mean_rr = np.mean(rr_intervals_ms)
        sdnn = np.std(rr_intervals_ms, ddof=1)
        # RMSSD and pNN50
        diff_rr = np.diff(rr_intervals_ms)
        rmssd = np.sqrt(np.mean(diff_rr ** 2))
        nn50 = np.sum(np.abs(diff_rr) > 50)
        pnn50 = (nn50 / len(rr_intervals_ms)) * 100.0
        
        # FREQUENCY DOMAIN
        # We'll interpolate RR intervals to get a consistent sampling rate for PSD
        # Typical resampling frequency for HRV PSD is 4 Hz
        t = np.cumsum(rr_intervals)
        t = t - t[0] # start at 0
        fs_interp = 4.0 
        
        if len(t) > 10:
            t_interp = np.arange(0, t[-1], 1.0/fs_interp)
            rr_interp = np.interp(t_interp, t, rr_intervals_ms)
            
            # Welch's method
            nperseg = min(256, len(rr_interp))
            f, pxx = signal.welch(rr_interp, fs=fs_interp, nperseg=nperseg)
            
            # Bands
            lf_band = np.logical_and(f >= 0.04, f <= 0.15)
            hf_band = np.logical_and(f > 0.15, f <= 0.4)
            
            lf_power = np.trapezoid(pxx[lf_band], f[lf_band]) if np.any(lf_band) else 0.0
            hf_power = np.trapezoid(pxx[hf_band], f[hf_band]) if np.any(hf_band) else 0.0
            lf_hf = lf_power / hf_power if hf_power > 0 else 0.0
            
            psd_f = f.tolist()
            psd_p = pxx.tolist()
        else:
            lf_power, hf_power, lf_hf = 0, 0, 0
            psd_f, psd_p = [], []
            
        # NON-LINEAR
        # Poincaré Plot
        # SD1, SD2
        sd1 = np.sqrt(0.5) * np.std(diff_rr, ddof=1)
        sd2 = np.sqrt(2 * np.std(rr_intervals_ms, ddof=1)**2 - 0.5 * np.std(diff_rr, ddof=1)**2)
        
        # Sample Entropy
        sampen = self.sample_entropy(rr_intervals_ms, m=2)
        
        # Downsample signals to reduce JSON payload size for frontend plotting
        # Typical 65536 is too large for UI. We send a downsampled version and only a 5-second segment for pipeline
        plot_len = min(int(fs * 5), len(sig)) # plot 5 seconds for step-by-step
        
        raw_plot = [float(x) for x in raw_sig[:plot_len]]
        filtered_plot = [float(x) for x in filtered_sig[:plot_len]]
        squared_plot = [float(x) for x in squared_sig[:plot_len]]
        mwi_plot = [float(x) for x in mwi_sig[:plot_len]]
        
        peaks_plot = [int(p) for p in peaks if p < plot_len]
        peaks_mwi_plot = [int(p) for p in peaks_mwi if p < plot_len]
        
        # RR plot points
        rr_plot = [float(x) for x in rr_intervals_ms]
        
        return {
            "label": label,
            "fs": float(fs),
            "time_domain": {
                "mean_nni": float(mean_rr),
                "sdnn": float(sdnn),
                "rmssd": float(rmssd),
                "pnn50": float(pnn50)
            },
            "frequency_domain": {
                "lf": float(lf_power),
                "hf": float(hf_power),
                "lf_hf_ratio": float(lf_hf),
                "psd_f": [float(x) for x in psd_f],
                "psd_p": [float(x) for x in psd_p]
            },
            "non_linear": {
                "sd1": float(sd1),
                "sd2": float(sd2),
                "sampen": float(sampen)
            },
            "plots": {
                "raw_ecg": raw_plot,
                "filtered_ecg": filtered_plot,
                "squared_ecg": squared_plot,
                "mwi_ecg": mwi_plot,
                "peaks": peaks_plot,
                "peaks_mwi": peaks_mwi_plot,
                "rr": rr_plot
            }
        }
        
    def analyze(self, index):
        if index < 0 or index >= self.num_signals:
            raise ValueError("Invalid signal index")
        sig = self.ecg_data[index]
        label = self.ecg_labels[index]
        return self.analyze_raw(sig, label)
