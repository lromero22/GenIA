from ffmpeg import FFmpeg
from pathlib import Path


base = Path(__file__).resolve().parent

## PATHS

# Path to the audio file
audio_path = base / "data" / 'test.wav'
audio_conver = base / "data" / "conversion" / 'test.wav'
speaker_path = base / "data" / "speakers"


## PREPROCESSING

# Audio conversion to PCM using FFPMEG
ffmpeg = FFmpeg().option("y").input(url=str(audio_path)).output(url=audio_conver, format='s16le', acodec='pcm_s16le', ac=1, ar='16k')
ffmpeg.execute()