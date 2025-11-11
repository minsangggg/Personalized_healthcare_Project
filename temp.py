from pathlib import Path
text = Path("backend/app/services/llm_client.py").read_text(encoding="utf-8")
start = text.index("        text = re.sub(r\"^(?:\\d+[")
