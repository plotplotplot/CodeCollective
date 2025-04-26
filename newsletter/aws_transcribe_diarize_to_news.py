import sys
import json

with open("edunx1_diarize.json", "r") as f:
    textdict = json.loads(f.read())

results = textdict["results"]
items = results["items"]

outstr = '<div class="conversation">\n'
lastspeaker = ""
for item in items:
    if item['type'] != 'punctuation':
        outstr += " "
    if item['speaker_label'] != lastspeaker:
        if lastspeaker != "":
            outstr += "\n</div>\n"
            outstr += "\n</div>\n"
        if "0" in lastspeaker:
            outstr += '<div class="message sender">\n'
        else:
            outstr += '<div class="message receiver">\n'
        outstr += '<div class="bubble">\n'
        lastspeaker = item['speaker_label']

    outstr += item['alternatives'][0]['content']
outstr += "\n</div>\n"

with open("edunx1_diarize.html", "w") as f:
    f.write(outstr)
print("Output written to edunx1_diarize.html")