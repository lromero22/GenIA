import librosa
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from pathlib import Path
import soundfile as sf
import numpy as np
from ffmpeg import FFmpeg

from audio_preprocess import audio_conver, speaker_path


# Caracterizador de la campaña
# caracterizador = "Con NombrePersona de Sura/Suramericana"

# Load the audio file and extract the MFCC features
audio, sr = librosa.load(audio_conver, sr=None, mono=True)
mfccs = librosa.feature.mfcc(y=audio, sr=sr)
scaler = StandardScaler()
mfccs_scaled = scaler.fit_transform(mfccs.T)
kmeans = KMeans(n_clusters=2)
speaker_labels = kmeans.fit_predict(mfccs_scaled)

# Get the time segments for each speaker in the real duration of the audio
segments = librosa.frames_to_time(np.arange(len(speaker_labels)), sr=sr)

timestamps = []
current_label = speaker_labels[0]
start_time = segments[0]
for i, label in enumerate(speaker_labels[1:], start=1):
    if label != current_label:
        end_time = segments[i-1]
        timestamps.append((start_time, end_time, current_label))
        start_time = segments[i]
        current_label = label
end_time = segments[-1]
timestamps.append((start_time, end_time, current_label))

# Merge segments that are too close to each other
def merge_segments(timestamps, max_gap=0.5):
    sorted_timestamps = sorted(timestamps, key=lambda x: (x[2], x[0]))
    merged_timestamps = []
    
    current_start, current_end, current_speaker = sorted_timestamps[0]
    
    for start, end, speaker in sorted_timestamps[1:]:
        if speaker == current_speaker and start - current_end <= max_gap:
            current_end = end
        else:
            merged_timestamps.append((current_start, current_end, current_speaker))
            current_start, current_end, current_speaker = start, end, speaker
    
    merged_timestamps.append((current_start, current_end, current_speaker))
    
    return merged_timestamps

merged_timestamps = merge_segments(timestamps)

# Using the timestamps, we can transcript the audio in one file for each speaker
for i, (start, end, speaker) in enumerate(merged_timestamps):
    speaker_audio = audio[int(start * sr):int(end * sr)]
    speaker_file = speaker_path / f"speaker_{speaker}_{i}.wav"
    sf.write(speaker_file, speaker_audio, sr)

