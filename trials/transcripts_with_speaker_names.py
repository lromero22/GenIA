
import datetime
from pathlib import Path
import wave
import contextlib

import whisper
from ffmpeg import FFmpeg
import torch
import torchaudio
import pyannote.audio


# from speechbrain.inference.speaker import EncoderClassifier
# from speechbrain.inference.speaker import SpeakerRecognition

from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
from pyannote.audio import Audio
from pyannote.core import Segment
from sklearn.cluster import AgglomerativeClustering
import numpy as np

# TODO: Try https://github.com/Mastering-Python-GT/Transcription-diarization-whisper-pyannote/tree/main


# PATHS
# Path to the audio file
base = Path(__file__).resolve().parent
audio_path = base / "data" / 'test.wav'
audio_conver = base / "data" / "conversion" / 'test.wav'
speaker_path = base / "data" / "speakers"

# PARAMETERS
num_speakers = 2 
language = 'es'
model_size = 'large-v3'  

#PREPROCESSING

# Get the duration of the audio
with contextlib.closing(wave.open(str(audio_path))) as f:
    frames = f.getnframes()
    rate = f.getframerate()
    duration = frames / float(rate)

# Audio conversion to PCM using FFPMEG
ffmpeg = FFmpeg().option("y").input(url=str(audio_path)).output(
    url=audio_conver, format='s16le', acodec='pcm_s16le', ac=1, ar='16k')
ffmpeg.execute()

# FUNCTION DEFINITIONS
# Get the Word embeddings for each segment

# Create an Audio object
audio = Audio()
def segment_embedding(segment):
    start = segment["start"]
    # Whisper overshoots the end timestamp in the last segment
    end = min(duration, segment["end"])
    clip = Segment(start, end)
    waveform, _ = audio.crop(audio_path, clip)
    return embedding_model(waveform[None])

# Get the time in seconds
def time(secs):
    return datetime.timedelta(seconds=round(secs))


# PRETRAINED MODEL
# load the pretrained speaker embedding model
# classifier = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")
# signal, fs = torchaudio.load('tests/samples/ASR/spk1_snt1.wav')
# embedding_model = classifier.encode_batch(signal)

# TRANSCRIPTION WITH WHISPER
model = whisper.load_model(model_size)
result = whisper.transcribe(model, audio= audio_path, language="es")

# Get the segments from the transcription
segments = result["segments"]


# Get the embeddings for each segment
embeddings = np.zeros(shape=(len(segments), 192))
for i, segment in enumerate(segments):
    embeddings[i] = segment_embedding(segment)
# Replace NaN values with 0
embeddings = np.nan_to_num(embeddings)

# Clustering the embeddings to get the speakers
clustering = AgglomerativeClustering(num_speakers).fit(embeddings)
labels = clustering.labels_
for i in range(len(segments)):
    segments[i]["speaker"] = 'SPEAKER ' + str(labels[i] + 1)

# Write the transcript to a file
with open("transcript.txt", "w") as f:
  for (i, segment) in enumerate(segments):
    if i == 0 or segments[i - 1]["speaker"] != segment["speaker"]:
      f.write("\n" + segment["speaker"] + ' ' +
          str(time(segment["start"])) + '\n')
    f.write(segment["text"][1:] + ' ')
