import json
import subprocess

with open('../../Downloads/equity-alpha-engine-uk-3adcf1c5225d.json', 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

subprocess.run(['gh', 'secret', 'set', 'GCP_SA_KEY'], input=json.dumps(data), text=True)
