"""Bundle identical runtime tools; leave subject teaching instructions independent."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
for name in ['sentence-lesson','grammar-lesson','text-lesson']:
    for folder in ['scripts','assets']:
        shutil.copytree(ROOT/'skills/vocabulary-lesson'/folder,ROOT/'skills'/name/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
