import json

PREFIXES_FILE = 'prefixes.json'

def load_prefixes():
    """Return a dict {guild_id_str: prefix_str} from a JSON file."""
    try:
        with open(PREFIXES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("prefixes", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_prefixes(prefixes):
    """Save the dict {guild_id_str: prefix_str} to the JSON file."""
    try:
        with open(PREFIXES_FILE, 'w', encoding='utf-8') as f:
            json.dump({"prefixes": prefixes}, f, indent=2)
    except Exception as e:
        print(f"Error saving prefixes: {e}")