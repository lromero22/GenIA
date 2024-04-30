import tensorflow as tf
import os
import numpy as np
import shutil
from tensorflow import keras
from pathlib import Path
from Ipython.display import Audio, display
import subprocess
import librosa

base = Path(__file__).resolve().parent
data = base.joinpath('data')

## PATHS

data_dir = "data"
audio_folder = "audio"
noise_folder = "noise"

# Path to the audio file
audio_path = data / audio_folder
noise_path = data / noise_folder


validation_split = 0.2
shuffle_speed = 43
sample_rate = 16000
scale = 0.5
batch_size = 128
epoch = 15

noise_paths = list(noise_path.glob("*.wav"))

ns_audio, sr = librosa.load(noise_paths[0], sr=None, mono=True)

# Split the noise audio into chunks
def load_noise_sample(path):
    sample, sampling_rate = tf.audio.decode_wav(tf.io.read_file(path), desired_channels=1)

    if sampling_rate == sample_rate:
        slices = int(sample.shape[0] / sample_rate)
        sample = tf.split(sample[:slices * sample_rate], slices)
        return sample
    else:
        raise ValueError(f"Sampling rate for {path} is not {sample_rate}")
    
noise_samples = [load_noise_sample(path) for path in noise_paths]

noise_samples = tf.stack(noise_samples)

# Dataset generation
def path_to_audio(path):
    audio = tf.io.read_file(path)
    audio, _ = tf.audio.decode_wav(audio, 1, sample_rate)
    return audio

def paths_labels(audio_paths, labels):
    path_ds = tf.data.Dataset.from_tensor_slices(audio_paths)
    audio_ds = path_ds.map(lambda x: path_to_audio(x))
    label_ds = tf.data.Dataset.from_tensor_slices(labels)
    return tf.data.Dataset.zip((audio_ds, label_ds))

# Add noise to dataset
def add_noise(audio, noises, scale=0.5):
    if noises is not None:
        tf_rnd = tf.random.uniform((tf.shape(audio)[0]), 0, noises.shape[0], dtype=tf.int32)
        noise = tf.gather(noises, tf_rnd, axis=0)

        prop = tf.math.reduce_max(audio, axis=1) / tf.math.reduce_max(noise, axis=1)
        prop = tf.repeat(tf.expand_dims(prop, axis=1), tf.shape(audio)[1], axis=1)

        audio = audio + noise * prop * scale
    return audio

def audio_to_tff(audio):
    audio = tf.squeeze(audio, axis=-1)
    fft = tf.signal.fft(tf.cast(tf.complex(real=audio, imag=tf.zeros_like(audio)), tf.complex64))

    fft = tf.expand_dims(fft, axis=-1)

    return tf.math.abs(fft[:, :(audio.shape[1] // 2), :])



