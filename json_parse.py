import json
import re

# --- Safe JSON Parsing ---
def safe_json_parse(response_text):
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        # Attempt to fix unescaped backslashes
        fixed = re.sub(r'(?<!\\)\\(?![\\nrt"])', r'\\\\', response_text)
        try:
            return json.loads(fixed)
        except Exception as e2:
            print("Failed JSON:", fixed[:500])
            raise e2  # Re-raise if still failing
 