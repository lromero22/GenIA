# @title Divide the audios using the speaker timestamps, to analize specific fragments of audio

import re
import os
from glob import glob
from pathlib import Path
from scipy.io import wavfile # to read and write audio files
from io import BytesIO
import numpy as np
import opensmile
import audiofile

from pretrain_model import pretrain_model

# OS BASED PATH


# All files and directories ending with .txt and that don't begin with a dot:
# base = os.path.abspath('')
base = os.path.dirname(__file__)

audio_path = os.path.join(base, 'audios')
transcribe_path = os.path.join(base, 'transcriptions')

file_paths = glob(f"{transcribe_path}/*.txt")
input_files = [os.path.basename(file_path) for file_path in file_paths]
# print(input_files)

nombre_salida = "transcribe"

# Load / Run the pretrained model
clf = pretrain_model()

# Preprocess input transcription files
# Speaker dicts
speakers0_times = {}
speakers1_times = {}
speakers0_dict = {}
speakers1_dict = {}

for numero_diar, input_file in enumerate(input_files):
  input_file = os.path.join(transcribe_path, input_file)
  with open(input_file, "r", encoding="UTF-8") as f:
      transcribe = f.readlines()

  # Extract the last 6 digits from the file name
  if len(input_file.split('.')) > 2:
    id_file = input_file.split('.')[1]
  else:
    id_file = input_file.split('.')[-2][-6:]

  # Keyword preprocessing
  speaker0 = [line for line in transcribe if "SPEAKER_00" in line]
  speaker1 = [line for line in transcribe if "SPEAKER_01" in line]

  # Join the lines of each speaker
  speaker0 = " ".join(speaker0)
  speaker1 = " ".join(speaker1)

  # Save the timestamps of talking of each speaker
  pattern = r"\d{1,2}:\d{2}:\d{2} - \d{1,2}:\d{2}:\d{2} \[SPEAKER_00]:"
  speaker0_tmp = re.findall(pattern, speaker0)
  speaker0_tmp = [timestamp.replace(" [SPEAKER_00]:", "") for timestamp in speaker0_tmp]
  speakers0_times[id_file] = speaker0_tmp

  pattern = r"\d{1,2}:\d{2}:\d{2} - \d{1,2}:\d{2}:\d{2} \[SPEAKER_01]:"
  speaker1_tmp = re.findall(pattern, speaker1)
  speaker1_tmp = [timestamp.replace(" [SPEAKER_01]:", "") for timestamp in speaker1_tmp]
  speakers1_times[id_file] = speaker1_tmp

  # Remove the strings that match the pattern 00:00:00 - 0:00:26 [SPEAKER_00]:
  pattern = r"\d{1,2}:\d{2}:\d{2} - \d{1,2}:\d{2}:\d{2} \[SPEAKER_\d{2}\]:"
  # Save the lines without timestamp
  speaker0 = re.sub(pattern, "", speaker0)
  speaker1 = re.sub(pattern, "", speaker1)

  speaker0 = speaker0.split("\n")
  speaker1 = speaker1.split("\n")
  speakers0_dict[id_file] = speaker0
  speakers1_dict[id_file] = speaker1





# Function to process audio features using OpenSMILE
def process_features(audio_array, sample_rate):

    smile = opensmile.Smile(
        opensmile.FeatureSet.ComParE_2016,
        opensmile.FeatureLevel.Functionals,
        sampling_rate=16000,
        resample=True,
        num_workers=5,
        verbose=True,
    )

    features = smile.process_signal(audio_array, sample_rate)

    return features

# Function to predict emotion from audio features
def predict_emotion(features, clf):
    predicted_emotion = clf.predict(features)
    return predicted_emotion

# Function to convert time string to seconds
def time_to_seconds(time_str):
    parts = list(map(int, re.split('[:]', time_str)))
    return parts[0] * 3600 + parts[1] * 60 + parts[2]

correct = []
def emotions_per_speaker(speaker_times:dict):
  # All the wavs present in the audio_path
  file_paths_wav = glob(f"{audio_path}/*.WAV")

  audio_paths_dict = {file_path.split('.')[1] if len(file_path.split('.')) > 2 else file_path.split('.')[-2][-6:]: file_path for file_path in file_paths_wav}

  audios_emotions = {}
  for audio_id, timestamps in speaker_times.items():
    # Check if the audio_id exists in the dictionary
    if audio_id in audio_paths_dict:
        # Get the path corresponding to the audio_id
        wav_path = audio_paths_dict[audio_id]

        #160933, 151309, 161467

        # Iterate over each interval string
        emotions = {}
        for interval_str in timestamps:
            # Split the interval string into start and end times
            start, end = map(time_to_seconds, interval_str.split(' - '))

            # Split the audio using start end times
            # get sample rate and audio data
            audio_data, sample_rate = audiofile.read(wav_path)

            ## splice the audio with prefered start and end times
            # spliced_audio = audio_data[start * sample_rate : end * sample_rate, :]
            spliced_audio = audio_data[int(start * sample_rate) : int(end * sample_rate)]

            features = process_features(spliced_audio, sample_rate)

            # TODO: '160933' revisar audio ID tal que paso que da UserWarning: Segment too short, filling with NaN. Corre bien 5
            # ValueError: Input X contains NaN. SVC does not accept missing values encoded as NaN natively
            predicted_emotion = predict_emotion(features, clf)

            predicted_emotions = ', '.join(predicted_emotion)

            
            emotions[interval_str] = predicted_emotions

        audios_emotions[audio_id] = emotions
        correct.append(audio_id)

  return audios_emotions


audios_emotions = emotions_per_speaker(speakers0_times)

print(audios_emotions)

 