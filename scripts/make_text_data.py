"""WikiText-2: test split -> KL text; train split slice -> imatrix calibration text."""
from pathlib import Path

from datasets import load_dataset

name = ("Salesforce/wikitext", "wikitext-2-raw-v1")
test = "".join(load_dataset(*name, split="test")["text"])
train = "".join(load_dataset(*name, split="train")["text"])

Path("data").mkdir(exist_ok=True)
Path("data/kl_text.txt").write_text(test)
Path("data/calib_text.txt").write_text(train[:600_000])  # used only in the rebuild phase

print(f"KL text (test split):    {len(test):,} chars")
print(f"Calibration (train[:600k]): 600,000 chars")