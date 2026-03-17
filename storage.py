import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def _get_path(filename:str):
    return os.path.join(DATA_DIR, filename)

def load_json(filename:str, defualt):
    path = _get_path(filename)

    if not  os.path.exists(path):
        return defualt
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return defualt
    

def save_json(filename: str, data):
    path = _get_path(filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)