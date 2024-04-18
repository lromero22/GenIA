from pathlib import Path


from pydub import AudioSegment
import ffmpeg
import speech_recognition as sr

base = Path(__file__).resolve().parent


def replace_extension(file_name, extension):
    # Find the last occurrence of "."
    index = file_name.rfind('.')
    if index != -1:
        # Replace everything after "." with ".pcm"
        new_file_name = file_name[:index] + "." + extension
        return new_file_name
    else:
        # If there's no ".", just add ".pcm" at the end
        return file_name + "." + extension

# Convert audio file to wav format
def convert_to_wav(audio_file: Path):
    sound = AudioSegment.from_file(audio_file)
    # sound.export('myfile.pcm', format='s16le', bitrate='16k')
    sound.export(replace_extension(audio_file, "wav"), format='wav')
    return sound


# Convert audio file to mono channel for processing
def convert_to_mono(audio_file):
    sound = AudioSegment.from_file(audio_file)
    sound = sound.set_channels(1)
    return sound


# TODO: Guardar cada trozo en un BytesIO

# Split audio file into chunks
def split_audio(audio_file, chunk_size=10):
    chunks = []
    for i in range(0, len(audio_file), chunk_size * 1000):
        chunks.append(audio_file[i:i + chunk_size * 1000])
    return chunks

def transcribe_audio(audio_file, output_file: Path):

    # Convert audio file to wav format
    # audio_file = convert_to_wav(audio_file)

    # Initialize recognizer class
    r = sr.Recognizer()
    # CMU Sphinx | Offline
    #recognize_sphinx()

    # Capture data from file
    with sr.AudioFile(audio_file) as source:
        audio = r.record(source)

    text = r.recognize_google(audio, language="es-ES")
    # TODO: Split audio in chunks
    # TODO: Optimize transcription and fix errors
    # audio_chunks = split_audio(audio)
    # text = []
    # for i, chunk in enumerate(audio_chunks):
    #     text.append(r.recognize_google(chunk, language="es-ES"))

    with open(output_file, 'w') as f:
        # f.write('\n'.join(text))
        f.write(text)

audio = '1014249230_3.wav'
output_file = base / 'data' / 'transcription.txt'
transcribe_audio(audio, output_file)

