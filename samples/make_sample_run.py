"""Regenerate the committed sample run in samples/outputs/ (and samples/exercise_pack_sample.json).

The pipeline lives in ttx/demo.py; `ttx demo` runs the same thing into out/demo
without touching committed files. No network, no keys, no model.

Run from the repo root:  python samples/make_sample_run.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ttx.demo import run_sample  # noqa: E402


def main() -> None:
    result = run_sample(REPO / "samples" / "outputs", sample_pack_path=REPO / "samples" / "exercise_pack_sample.json")
    for name, path in result["files"].items():
        print(f"built {name:<28} {Path(path).relative_to(REPO)}")
    print("headline:", result["headline"])


if __name__ == "__main__":
    main()
