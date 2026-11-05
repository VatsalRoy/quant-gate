"""List every LFM3-1.7B GGUF from the 4 uploaders -> results/inventory.csv"""
import csv
import re
from pathlib import Path

from huggingface_hub import HfApi
from huggingface_hub.utils import RepositoryNotFoundError

REPOS = {
    "LiquidAI/LFM3-1.7B-GGUF": "official",
    "bartowski/LFM3-1.7B-GGUF": "bartowski",
    "prithivMLmods/LFM3-1.7B-GGUF": "prithivMLmods",
    "AtomicChat/LFM3-1.7B-GGUF": "AtomicChat",
}

# Fill these in after READING each model card. Don't guess.
# Values: "yes", "no", or "unknown"
IMATRIX_PER_CARD = {
    "official": "unknown",
    "bartowski": "yes",
    "prithivMLmods": "unknown",
    "AtomicChat": "yes (tag)",
}

N_PARAMS = 1.73e9  # from the model card; used for approximate bits per weight

QUANT_RE = re.compile(
    r"(IQ\d_[A-Z]+|Q\d_K(?:_[A-Z]+)?|Q\d_\d|BF16|F16|F32|NVFP4|MXFP4)", re.I
)


def parse_quant(name: str) -> tuple[str, str]:
    """Return (quant_type, variant), e.g. ('Q4_K_M', 'AD')."""
    m = QUANT_RE.search(name)
    quant = m.group(1).upper() if m else "UNKNOWN"
    if "QAD" in name.upper():
        variant = "QAD"
    elif re.search(r"(^|[-_.])AD-", name):
        variant = "AD"
    else:
        variant = ""
    return quant, variant


def sha_of(lfs) -> str:
    if lfs is None:
        return ""
    if isinstance(lfs, dict):
        return lfs.get("sha256", "")
    return getattr(lfs, "sha256", "") or ""


def main():
    api = HfApi()
    rows, other_files = [], []

    for repo, uploader in REPOS.items():
        try:
            info = api.model_info(repo, files_metadata=True)
        except RepositoryNotFoundError:
            print(f"!! not found: {repo}")
            continue

        for s in info.siblings:
            name = s.rfilename
            if "imatrix" in name.lower() or name.endswith(".dat"):
                other_files.append((repo, name))
                continue
            if not name.endswith(".gguf"):
                continue
            quant, variant = parse_quant(name)
            size = s.size or 0
            rows.append({
                "repo": repo,
                "uploader": uploader,
                "filename": name,
                "quant": quant,
                "variant": variant,
                "size_bytes": size,
                "size_gb": round(size / 1e9, 3),
                "approx_bpw": round(size * 8 / N_PARAMS, 2),
                "sha256": sha_of(s.lfs),
                "imatrix_per_card": IMATRIX_PER_CARD[uploader],
                "revision": info.sha,  # exact repo commit you inventoried
            })

    rows.sort(key=lambda r: (r["uploader"], r["approx_bpw"]))
    out = Path("results/inventory.csv")
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} files to {out}\n")
    for up in REPOS.values():
        sub = [r for r in rows if r["uploader"] == up]
        gb = sum(r["size_gb"] for r in sub)
        print(f"  {up:14s} {len(sub):3d} files  {gb:6.1f} GB")
    unknown = [r["filename"] for r in rows if r["quant"] == "UNKNOWN"]
    if unknown:
        print("\nCould not parse quant type for:", *unknown, sep="\n  ")
    if other_files:
        print("\nNon-GGUF imatrix/calibration files (not tested, but note them):")
        for repo, name in other_files:
            print(f"  {repo}: {name}")


if __name__ == "__main__":
    main()