import os
import audeer
import audonnx
import numpy as np
import audinterface
import audb
import audformat
import audmetric
import pandas as pd
import opensmile
import audiofile
from pathlib import Path
from glob import glob
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
import pretrain_model as ptm

# Function to process audio features using OpenSMILE
def process_features(audio:str):
    signal, sampling_rate = audiofile.read(audio)

    smile = opensmile.Smile(
        opensmile.FeatureSet.ComParE_2016,
        opensmile.FeatureLevel.Functionals,
        sampling_rate=16000,
        resample=True,
        num_workers=5,
        verbose=True,
    )

    features = smile.process_signal(signal, sampling_rate)

    return features

# Function to predict emotion from audio features
def predict_emotion(features, clf):
    predicted_emotion = clf.predict(features)
    return predicted_emotion

def main():
    ptm.main()
    # Base path for Colab
    # base = os.path.abspath('')
    base = os.path.dirname(__file__)

    file_paths = glob(f"{base}/*.WAV")

    for file_path in file_paths:
        # Batch conversion using CMD
        # for %i in (*.WAV) do ffmpeg -y -i "%i" -acodec pcm_s16le -ac 1 -ar 16000 "converted/%~ni.WAV"
        command = f"ffmpeg -y -i {file_path} -acodec pcm_s16le -ac 1 -ar 16000 {file_path}"
        os.system(command)
        print(f"Archivo {file_path} creado.")
        features = process_features(file_path)
        predicted_emotion = predict_emotion(features, ptm.clf)
        print("Predicted Emotion:", predicted_emotion)

if __name__ == "__main__":
    main()
    print("End")
