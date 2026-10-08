"""Open the dashboard only once the local server is ready."""
import json
from pathlib import Path
import sys
import threading
import time
import urllib.request
import webbrowser
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
URL='http://127.0.0.1:8000'

def ready():
    try:
        with urllib.request.urlopen(URL+'/api/health',timeout=1) as response:
            status=json.load(response)
            return status.get('status')=='ok' and status.get('analysis_ready') is True
    except (OSError,ValueError):
        return False

def open_when_ready():
    for _ in range(80):
        if ready():
            webbrowser.open(URL)
            return
        time.sleep(.25)

if __name__=='__main__':
    if ready():
        print('An existing Association Lab server is ready. Opening the dashboard.')
        webbrowser.open(URL)
    else:
        import uvicorn
        threading.Thread(target=open_when_ready,daemon=True).start()
        uvicorn.run('backend.app.main:app',host='127.0.0.1',port=8000)
