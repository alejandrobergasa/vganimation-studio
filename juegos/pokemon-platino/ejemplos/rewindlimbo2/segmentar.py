import numpy as np, soundfile as sf, librosa
S = 'audio/sep/htdemucs/original/'
y = sum(sf.read(S + n + '.wav', dtype='float32')[0].mean(1) for n in ('drums', 'bass', 'other'))
y = librosa.resample(y, orig_sr=44100, target_sr=22050); fs = 22050; hop = 2048
C = librosa.feature.chroma_cqt(y=y, sr=fs, hop_length=hop)
M = librosa.feature.mfcc(y=y, sr=fs, hop_length=hop, n_mfcc=13)
R = librosa.feature.rms(y=y, hop_length=hop)
X = np.vstack([librosa.util.normalize(C, axis=0), M / 50, 20 * np.log10(R + 1e-5) / 20])
b = librosa.segment.agglomerative(X, 40)
t = librosa.frames_to_time(b, sr=fs, hop_length=hop)
print(' '.join('%.1f' % x for x in t))
