import os
import audeer
import audonnx
import numpy as np
import audb
import pandas as pd
import audformat
import audmetric
import opensmile
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

# Function to download and extract the model
def download_and_extract_model(model_url, dst_path, model_root, cache_root):

    if not os.path.exists(dst_path):
        # Create cache_root folder if it doesn't exist
        os.makedirs(cache_root, exist_ok=True)

        audeer.download_url(
            model_url,
            dst_path,
            verbose=True,
        )

    if not os.path.exists(model_root):
        # Create model_root folder if it doesn't exist
        os.makedirs(model_root, exist_ok=True)

        audeer.extract_archive(
            dst_path,
            model_root,
            verbose=True,
        )

# Function to load the model
def load_model(model_root):
    model = audonnx.load(model_root)
    return model

# Function to load the Emo-DB database
def load_emodb_database(cache_root):
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
    return db

def smile_pretrain(emotion, db, cache_root):

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

    return features_smile

# Function to perform leave-one-speaker-out cross-validation experiment
def leave_one_speaker_out_experiment(features, targets, groups, clf):
    truths = []
    preds = []

    logo = LeaveOneGroupOut()

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

    truth = pd.concat(truths)
    truth.name = 'truth'
    pred = pd.Series(
        np.concatenate(preds),
        index=truth.index,
        name='prediction',
    )

    return truth, pred

def main():
    def cache_path(file):
        return os.path.join(cache_root, file)
    
    model_root = 'model'
    cache_root = 'cache'
    
    dst_path = cache_path('model.zip')
    model_url = 'https://zenodo.org/record/6221127/files/w2v2-L-robust-12.6bc4a7fd-1.1.0.zip'

    download_and_extract_model(model_url, dst_path, model_root, cache_root)
    model = load_model(model_root)
    db = load_emodb_database(cache_root)

    speaker = db['files']['speaker'].get()
    emotion = db['emotion']['emotion'].get()

    audformat.utils.concat([emotion, speaker])

    clf = make_pipeline(
        StandardScaler(),
        SVC(gamma='auto'),
    )
    
    features_smile = smile_pretrain(emotion, db, cache_root)

    truth_smile, pred_smile = leave_one_speaker_out_experiment(
        features_smile,
        emotion,
        speaker,
        clf
    )

    audmetric.unweighted_average_recall(truth_smile, pred_smile)

if __name__ == "__main__":
    main()
    print("End pretraining")