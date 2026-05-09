import urllib.request
import json

url = "https://multiagent-9rqt.onrender.com/api/analyze"
data = json.dumps({"query": "I was involved in a car crash while drunk."}).encode('utf-8')
headers = {'Content-Type': 'application/json'}
req = urllib.request.Request(url, data=data, headers=headers)

try:
    with urllib.request.urlopen(req, timeout=120) as response:
        print(response.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
