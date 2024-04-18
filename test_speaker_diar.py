import torch
import speechbrain
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding

#TODO: BUSCA MANERA DE SOLUCIONAR ESTE PROBLEMA
model = PretrainedSpeakerEmbedding(
    "speechbrain/spkrec-ecapa-voxceleb",
    device=torch.device("cuda"),
    use_auth_token='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')


from pyannote.audio import Audio
from pyannote.core import Segment


# test

audio = Audio(sample_rate=16000, mono="downmix")

# extract embedding for a speaker speaking between t=3s and t=6s
speaker1 = Segment(3., 6.)
waveform1, sample_rate = audio.crop('data/test.wav', speaker1)
embedding1 = model(waveform1[None])

# extract embedding for a speaker speaking between t=7s and t=12s
speaker2 = Segment(7., 12.)
waveform2, sample_rate = audio.crop('data/test.wav', speaker2)
embedding2 = model(waveform2[None])

# compare embeddings using "cosine" distance
from scipy.spatial.distance import cdist
distance = cdist(embedding1, embedding2, metric="cosine")