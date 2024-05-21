from ffmpeg import FFmpeg
from pathlib import Path


base = Path(__file__).resolve().parent

## PATHS

def conversor(input: Path):
    output = input.resolve().parent
    
    audio_conver = output / "output" / "converted"
    # Audio conversion to PCM using FFPMEG
    ffmpeg = FFmpeg().option("y").input(url=input).output(url=audio_conver, format='s16le', acodec='pcm_s16le', ac=1, ar='16k')
    ffmpeg.execute()

    return True