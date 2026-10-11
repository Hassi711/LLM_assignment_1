The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
"""Collect Urdu Wikipedia article text through the official MediaWiki API.

Run this yourself to generate collection evidence for the assignment. This is
not a web-page scraper: it uses Wikipedia's public API and a descriptive
User-Agent, sends requests sequentially, and pauses between requests.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API_URL = "https://ur.wikipedia.org/w/api.php"
SOURCE_PAGE = "https://ur.wikipedia.org/"
LICENSE_NOTE = "Wikipedia article text is generally CC BY-SA and GFDL; preserve attribution and verify the current applicable terms before submission."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-mib", type=float, default=80.0,
                        help="Target UTF-8 bytes of extracted article text (default: 80 MiB).")
    parser.add_argument("--out", default="data/raw/urwiki_api.jsonl",
                        help="JSONL output path, relative to current directory by default.")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Pause between API requests in seconds (default: 0.5).")
    parser.add_argument("--max-pages", type=int, default=0,
                        help="Optional safety limit; 0 means no page-count limit.")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    target_bytes = int(args.target_mib * 1024 * 1024)
    start_utc = datetime.now(timezone.utc).isoformat()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "CS417-UrduBPE-coursework/1.0 (educational research; contact: hassanbh711@gmail.com)"
    })
    # Keep the base request immutable. MediaWiki continuation responses may
    # omit continuation keys that were present in the previous response; if we
    # mutate the base params, stale keys can cause the API's badcontinue error.
    base_params: dict[str, object] = {
        "action": "query",
        "generator": "allpages",
        "gapnamespace": 0,
        "gapfilterredir": "nonredirects",
        "gaplimit": 50,
        "prop": "extracts|info",
        "explaintext": 1,
        "exsectionformat": "plain",
        "inprop": "url",
        "format": "json",
        "formatversion": 2,
        "maxlag": 5,
    }

    pages_saved = 0
    text_bytes = 0
    api_calls = 0
    seen_page_ids: set[int] = set()
    last_title = ""
    continuation: dict[str, object] = {}

    try:
        with out_path.open("w", encoding="utf-8", newline="\n") as output:
            while text_bytes < target_bytes:
                # Pass exactly the continuation object from the immediately
                # preceding API response; do not retain stale continuation keys.
                request_params = base_params.copy()
                request_params.update(continuation)
                response = session.get(API_URL, params=request_params, timeout=90)
                api_calls += 1
                if response.status_code in (429, 500, 502, 503, 504):
                    # Back off instead of hammering the public API.
                    wait = min(60, 2 ** min(api_calls, 6))
                    print(f"HTTP {response.status_code}; retrying after {wait}s")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                payload = response.json()

                if "error" in payload:
                    error = payload["error"]
                    if error.get("code") in {"maxlag", "readonly", "ratelimited"}:
                        time.sleep(max(args.delay, 5.0))
                        continue
                    raise RuntimeError(f"MediaWiki API error: {error}")

                pages = payload.get("query", {}).get("pages", [])
                for page in pages:
                    page_id = page.get("pageid")
                    if page_id in seen_page_ids:
                        continue
                    if page_id is not None:
                        seen_page_ids.add(page_id)
                    body = (page.get("extract") or "").strip()
                    # Skip pages with no meaningful article text.
                    if len(body) < 100:
                        continue
                    title = page.get("title", "")
                    url = page.get("fullurl") or f"https://ur.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    record = {
                        "source": "Urdu Wikipedia",
                        "pageid": page_id,
                        "title": title,
                        "url": url,
                        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                        "text": body,
                    }
                    output.write(json.dumps(record, ensure_ascii=False) + "\n")
                    pages_saved += 1
                    text_bytes += len(body.encode("utf-8"))
                    last_title = title
                    if args.max_pages and pages_saved >= args.max_pages:
                        break
                    if text_bytes >= target_bytes:
                        break

                if args.max_pages and pages_saved >= args.max_pages:
                    break
                if text_bytes >= target_bytes:
                    break
                next_continuation = payload.get("continue")
                if not next_continuation:
                    print("API returned no continuation token; reached the end of available article titles.")
                    break
                # Replace, rather than update, the prior continuation state.
                # Some generator/property batches return only a subset of keys.
                continuation = dict(next_continuation)
                time.sleep(max(0.0, args.delay))

    except KeyboardInterrupt:
        print("Interrupted by user; writing a manifest for the pages collected so far.")

    out_bytes = out_path.stat().st_size if out_path.exists() else 0
    manifest = {
        "source_name": "Urdu Wikipedia",
        "source_url": SOURCE_PAGE,
        "api_endpoint": API_URL,
        "license_note": LICENSE_NOTE,
        "collection_start_utc": start_utc,
        "collection_end_utc": datetime.now(timezone.utc).isoformat(),
        "pages_saved": pages_saved,
        "extracted_text_bytes_utf8": text_bytes,
        "jsonl_output_bytes": out_bytes,
        "api_calls": api_calls,
        "delay_seconds": args.delay,
        "last_saved_title": last_title,
        "output_path": str(out_path),
        "user_agent_note": "Replace the example contact email in the script with your own contact before running.",
    }
    manifest_path = out_path.with_name("urwiki_collection_manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"Collection evidence saved to: {manifest_path}")


if __name__ == "__main__":
    main()
