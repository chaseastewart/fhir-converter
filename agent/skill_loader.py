import re
from pathlib import Path

def load_skill(path: str) -> str:
    text = Path(path).read_text(encoding="utf-8")
    return re.sub(r"^---.*?---\s*", "", text, count=1, flags=re.DOTALL)
