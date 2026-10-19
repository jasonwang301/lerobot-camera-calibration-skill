"""Compare pip's downloaded archive hashes with official PyPI release records."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from urllib.request import urlopen


def verify(item):
    meta = item["metadata"]
    download = item["download_info"]
    name, version = meta["name"], meta["version"]
    filename = unquote(Path(urlsplit(download["url"]).path).name)
    actual = download.get("archive_info", {}).get("hashes", {}).get("sha256")
    result = {"name": name, "version": version, "filename": filename, "sha256": actual}
    try:
        if not actual:
            raise ValueError("pip report contains no SHA256")
        url = f"https://pypi.org/pypi/{quote(name, safe='')}/{quote(version, safe='')}/json"
        with urlopen(url, timeout=25) as response:
            release = json.load(response)
        expected = next(row["digests"]["sha256"] for row in release["urls"] if row["filename"] == filename)
        if actual != expected:
            raise ValueError("archive SHA256 differs from official PyPI")
        result["verified"] = True
    except Exception as exc:
        result.update(verified=False, error=str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", nargs="?", default="install-report.json")
    parser.add_argument("--out", default="artifacts/pypi-verification.json")
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text())
    archives = [row for row in report["install"] if "archive_info" in row["download_info"]]
    if not archives:
        raise SystemExit("No downloaded archives found in pip report")
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(verify, archives))
    payload = {"verified_at_utc": datetime.now(timezone.utc).isoformat(), "packages": results}
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    failures = [row for row in results if not row["verified"]]
    print(f"Official PyPI SHA256 verified: {len(results) - len(failures)}/{len(results)} archives")
    for row in failures:
        print(f"  {row['name']}=={row['version']}: {row['error']}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
