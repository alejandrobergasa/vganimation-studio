"""Análisis de la música original (stems sin voz): tempo local, tonalidad y energía cada 10 s."""
import numpy as np, soundfile as sf, librosa
S = 'audio/sep/htdemucs/original/'
y = sum(sf.read(S + n + '.wav', dtype='float32')[0].mean(1) for n in ('drums', 'bass', 'other'))
fs = 44100
y = librosa.resample(y, orig_sr=fs, target_sr=22050); fs = 22050
hop = 512
oenv = librosa.onset.onset_strength(y=y, sr=fs, hop_length=hop)
chroma = librosa.feature.chroma_cqt(y=y, sr=fs, hop_length=hop)
KS_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
N = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
w = int(10 * fs / hop)
for i in range(0, len(oenv), w):
    seg = oenv[i:i + w]
    tempo = librosa.feature.tempo(onset_envelope=seg, sr=fs, hop_length=hop)[0] if len(seg) > 50 else 0
    c = chroma[:, i:i + w].mean(1)
    best = max(((np.corrcoef(c, np.roll(K, k))[0, 1], N[k] + m) for K, m in ((KS_MAJ, ''), (KS_MIN, 'm')) for k in range(12)))
    rms = 20 * np.log10(np.sqrt((y[i * hop:(i + w) * hop] ** 2).mean()) + 1e-6)
    print('%5.0f  tempo %5.1f  tono %-4s (%.2f)  %5.1f dB' % (i * hop / fs, tempo, best[1], best[0], rms))
