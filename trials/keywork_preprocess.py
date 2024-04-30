import re
import spacy

with open("transcribe.txt", "r", encoding="UTF-8") as f:
    transcribe = f.readlines()

# Keyword preprocessing
speaker1 = [line for line in transcribe if "SPEAKER_00" in line]
speaker2 = [line for line in transcribe if "SPEAKER_01" in line]

# Join the lines of each speaker
speaker1 = " ".join(speaker1)
speaker2 = " ".join(speaker2)

# Remove the strings that match the pattern 00:00:00 - 0:00:26 [SPEAKER_00]:
pattern = r"\d{1,2}:\d{2}:\d{2} - \d{1,2}:\d{2}:\d{2} \[SPEAKER_\d{2}\]:"

speaker1 = re.sub(pattern, "", speaker1)
speaker2 = re.sub(pattern, "", speaker2)

speaker1 = speaker1.split("\n")
speaker2 = speaker2.split("\n")



nlp = spacy.load("es_core_news_sm")

#use spacy in each item of the speaker list
speaker1 = [nlp(line) for line in speaker1]
speaker2 = [nlp(line) for line in speaker2]

for token in speaker1:
    print(token.ent)