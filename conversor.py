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

audio = base / "audios" / "force-44441940-972-20240401-112258-1711988578.150759.WAV"

conversor(audio)

for output_file, codec, bitrate in conversiones:
    if bitrate:
        # Comando para conversiones con bitrate específico
        command = f"ffmpeg -y -i {input_file} -acodec pcm_s16le -ac 1 -ar 16000 {output_file}"
        os.system(command)
        print(f"Archivo {output_file} creado.")