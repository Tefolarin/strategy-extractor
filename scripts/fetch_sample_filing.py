"""
fetch_sample_filing.py

Downloads a real, public 10-K so you can try the app against an actual
company filing instead of a synthetic one. Defaults to Alphabet's most
recent 10-K from its own investor relations site.

This talks to the open internet, so it won't run inside a locked-down
sandbox — run it on your own machine.

Usage:
    python scripts/fetch_sample_filing.py
    python scripts/fetch_sample_filing.py --url <some-other-10-K-pdf-url>
"""

import argparse
import sys
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://s206.q4cdn.com/479360582/files/doc_financials/2025/q4/GOOG-10-K-2025.pdf"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "sample_filing.pdf"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="Direct URL to a 10-K PDF")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Where to save it")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {args.url}")
    try:
        req = urllib.request.Request(args.url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            out_path.write_bytes(response.read())
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        print(
            "If this URL has gone stale, grab any public 10-K PDF yourself "
            "(SEC EDGAR, or any public company's investor relations page) "
            "and pass it with --url, or just drop the file straight into "
            "the app's uploader.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
