# -*- coding: utf-8 -*-
"""Training_model.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1qP05PQ1PRXyURMsq2sh1ZBa-nsMim28R

#Reconocimiento de Emociones

######Comenzamos descargando y descomprimiendo el modelo. Esto nos dará dos archivos, un archivo ONNX binario que contiene los pesos del modelo y un archivo YAML con metainformación sobre el modelo. Primero descargamos las herramientas necesarias.
"""

!pip install audonnx
 !pip install audinterface
 !pip install audb
 !pip install audmetric
 !pip install opensmile
 !pip install audplot

"""###Cargando el modelo

######Comenzamos descargando y descomprimiendo el modelo. Esto nos dará dos archivos, un archivo ONNX binario que contiene los pesos del modelo y un archivo YAML con metainformación sobre el modelo.
"""

import os

import audeer


model_root = 'model'
cache_root = 'cache'


audeer.mkdir(cache_root)
def cache_path(file):
    return os.path.join(cache_root, file)


url = 'https://zenodo.org/record/6221127/files/w2v2-L-robust-12.6bc4a7fd-1.1.0.zip'
dst_path = cache_path('model.zip')

if not os.path.exists(dst_path):
    audeer.download_url(
        url,
        dst_path,
        verbose=True,
    )

if not os.path.exists(model_root):
    audeer.extract_archive(
        dst_path,
        model_root,
        verbose=True,
    )

"""######Al imprimir el modelo se enumeran los nodos de entrada y salida. Dado que el modelo opera con el flujo de audio sin procesar, tenemos un único nodo de entrada llamado "señal", que espera una señal mono con una frecuencia de muestreo de 16000 Hz. También vemos que el modelo tiene dos nodos de salida: 'hidden_states', que nos da acceso a los estados agrupados de la última capa del transformador y 'logits', que proporciona puntuaciones de excitación, dominancia y valencia en un rango de aproximadamente 0. .1."""

import audonnx

model = audonnx.load(model_root)
model

"""### Prueba de la librería

######Como prueba, llamamos al modelo con algo de ruido blanco. Tenga en cuenta que tenemos que forzar el tipo de datos de la señal a una precisión de punto flotante de 32 bits. Como resultado obtenemos un diccionario con predicciones para cada nodo de salida.
"""

import numpy as np


np.random.seed(0)

sampling_rate = 16000
signal = np.random.normal(
    size=sampling_rate,
).astype(np.float32)

model(signal, sampling_rate)

"""###Predecir excitación, dominancia y valencia

###### Audinterface ofrece una forma más avanzada de interconectar el modelo. Especialmente, la clase Característica resulta útil, ya que tiene la opción de asignar nombres a las dimensiones de salida. Dado que solo estamos interesados en las puntuaciones de excitación, dominancia y valencia, pasamos 'logits' como argumento de palabra clave adicional para nombres_salida. Y habilitamos el remuestreo automático en caso de que la frecuencia de muestreo esperada del modelo no coincida.
"""

import audinterface


interface = audinterface.Feature(
    model.labels('logits'),
    process_func=model,
    process_func_args={
        'outputs': 'logits',
    },
    sampling_rate=sampling_rate,
    resample=True,
    verbose=True,
)

interface.process_signal(signal, sampling_rate)

"""###Usando embeddings para entrenar el *modelo*

######La Base de datos de Berlín sobre el habla emocional (Emo-DB) es una conocida base de datos de habla con expresiones emocionales de diferentes actores. Para obtener la base de datos utilizamos audb, un paquete para gestionar archivos multimedia anotados. Cuando cargamos los datos, audb se encarga de almacenar en caché y convertir los archivos al formato deseado. Las anotaciones están organizadas como tablas en formato aud.
"""

import audb
import audformat


db = audb.load(
    'emodb',
    version='1.1.1',
    format='wav',
    mixdown=True,
    sampling_rate=16000,
    full_path=False,
    cache_root=cache_root,
    verbose=True,
)
speaker = db['files']['speaker'].get()
emotion = db['emotion']['emotion'].get()

audformat.utils.concat([emotion, speaker])

"""######Dado que el modelo se ajustó en puntuaciones dimensionales y no en etiquetas categóricas, se requiere un ajuste fino para los nuevos objetivos. Por lo tanto utilizamos la salida de 'hidden_states' para acceder al espacio latente del modelo, también llamado embedding."""

import pandas as pd


hidden_states = audinterface.Feature(
    model.labels('hidden_states'),
    process_func=model,
    process_func_args={
        'outputs': 'hidden_states',
    },
    sampling_rate=16000,
    resample=True,
    num_workers=5,
    verbose=True,
)

features_w2v2 = hidden_states.process_index(
    emotion.index,
    root=db.root,
    cache_root=audeer.path(cache_root, 'w2v2'),
)
features_w2v2

"""######Como clasificador, utilizamos una clasificación de vectores de soporte de scikit-learn. Dado que Emo-DB no define un conjunto oficial de entrenamiento y prueba, aplicamos dejar a un hablante fuera, es decir, predecimos a cada hablante individualmente después de entrenar con los otros hablantes. Para ello definimos la siguiente función de utilidad."""

from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


# Clasificador y objeto de agrupacion
clf = make_pipeline(
    StandardScaler(),
    SVC(gamma='auto'),
)
logo = LeaveOneGroupOut()

def experiment(
    features,
    targets,
    groups,
):
    truths = []
    preds = []

    # leave-one-speaker loop
    pbar = audeer.progress_bar(
        total=len(groups.unique()),
        desc='Run experiment',
    )
    for train_index, test_index in logo.split(
        features,
        targets,
        groups=groups,
    ):
        train_x = features.iloc[train_index]
        train_y = targets[train_index]
        clf.fit(train_x, train_y)

        truth_x = features.iloc[test_index]
        truth_y = targets[test_index]
        predict_y = clf.predict(truth_x)

        truths.append(truth_y)
        preds.append(predict_y)

        pbar.update()

    # combine speaker folds
    truth = pd.concat(truths)
    truth.name = 'truth'
    pred = pd.Series(
        np.concatenate(preds),
        index=truth.index,
        name='prediction',
    )

    return truth, pred

truth_w2v2, pred_w2v2 = experiment(
    features_w2v2,
    emotion,
    speaker,
)
audformat.utils.concat([truth_w2v2, pred_w2v2])

"""######Medimos el rendimiento mediante el Recordatorio Promedio No Ponderado (UAR), que calculamos con audmetric."""

import audmetric


audmetric.unweighted_average_recall(truth_w2v2, pred_w2v2)

"""###Comparación con características hechas con librerias.

######Repetimos el experimento anterior y utilizamos como entrada el conjunto de funciones ComParE compuesto por más de 6k funcionales. Para extraer el conjunto de funciones utilizamos opensmile.
"""

import opensmile


smile = opensmile.Smile(
    opensmile.FeatureSet.ComParE_2016,
    opensmile.FeatureLevel.Functionals,
    sampling_rate=16000,
    resample=True,
    num_workers=5,
    verbose=True,
)

features_smile = smile.process_index(
    emotion.index,
    root=db.root,
    cache_root=audeer.path(cache_root, 'smile'),
)
features_smile

truth_smile, pred_smile = experiment(
    features_smile,
    emotion,
    speaker,
)
audmetric.unweighted_average_recall(truth_smile, pred_smile)

"""######Para comprender en qué clases perdemos rendimiento, trazamos matrices de confusión para ambos enfoques con audplot."""

import audplot
import matplotlib.pyplot as plt


_, axs = plt.subplots(1, 2, figsize=[15, 5])

axs[0].set_title('smile')
audplot.confusion_matrix(
    truth_smile,
    pred_smile,
    percentage=True,
    ax=axs[0],
)

axs[1].set_title('w2v2')
audplot.confusion_matrix(
    truth_w2v2,
    pred_w2v2,
    percentage=True,
    ax=axs[1],
)

"""##Extraccion de caracteristicas de los audios."""



import opensmile
import audiofile
from pathlib import Path
import os
from glob import glob

def process_features(audio:str):
  # Load the audio file
  signal, sampling_rate = audiofile.read(audio)

  # Initialize the feature extractor with the same configuration as used for the dataset
  smile = opensmile.Smile(
      opensmile.FeatureSet.ComParE_2016,
      opensmile.FeatureLevel.Functionals,
      sampling_rate=16000,
      resample=True,
      num_workers=5,
      verbose=True,
  )

  # Extract features
  features = smile.process_signal(signal, sampling_rate)

  return features


# All files and directories ending with .txt and that don't begin with a dot:
base = os.path.abspath('')
file_paths = glob(f"{base}/*.WAV")
input_files = [os.path.basename(file_path) for file_path in file_paths]


def conversion(input_path):
      base = os.path.abspath('')
      input_file = os.path.basename(input_path)
      output_path = os.path.join(base, 'conversion', input_file)

      # Comando para conversiones con bitrate específico
      command = f"ffmpeg -y -i {input_file} -format s16le -acodec pcm_s16le -ar 44100 {output_path}"
      os.system(command)
      return output_path

for file_path in file_paths:
  converted_path = conversion(file_path)
  features = process_features(converted_path)
  # Store or use the extracted features
  print(features)  # Print the features to the console

predicted_emotion = clf.predict(features)
print("Predicted Emotion:", predicted_emotion)