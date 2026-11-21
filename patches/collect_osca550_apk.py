#!/usr/bin/env python3
"""Verify one exact APK output, its identity and signing certificate before export."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

PACKAGE = "com.osca550.kodi.diag"


def capture(*args: str) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("build_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("build_tools", type=Path)
    parser.add_argument("--variant", choices=("A", "B"), required=True)
    args = parser.parse_args()
    generated_view = args.build_root / "tools/android/packaging/xbmc/src/XBMCVideoView.java"
    expected_format = "TRANSPARENT" if args.variant == "A" else "OPAQUE"
    if f"setFormat(PixelFormat.{expected_format})" not in generated_view.read_text(encoding="utf-8"):
        raise RuntimeError("generated Java source has the wrong Surface variant")
    apk = args.source_root / "kodiapp-arm64-v8a-release.apk"
    if not apk.is_file():
        raise RuntimeError(f"expected final ARM64 APK not found: {apk}")
    badging = capture(str(args.build_tools / "aapt"), "dump", "badging", str(apk))
    if f"package: name='{PACKAGE}'" not in badging:
        raise RuntimeError("APK package identity is wrong; refusing to export an unrelated APK")
    expected_label = f"Kodi OSCA550 Diag {args.variant}"
    if f"application-label:'{expected_label}'" not in badging:
        raise RuntimeError(f"APK launcher label is not {expected_label}; it may be a stale build")
    if not re.search(r"^native-code:.*'arm64-v8a'", badging, re.MULTILINE):
        raise RuntimeError("APK does not contain the ARM64 native library")
    marker = "A-transparent" if args.variant == "A" else "B-opaque"
    with zipfile.ZipFile(apk) as package:
        native = package.read("lib/arm64-v8a/libkodi.so")
        if b"OSCA550-DIAG v1" not in native or marker.encode("ascii") not in native:
            raise RuntimeError("APK native library is missing the expected diagnostic marker")
    certificate = capture(str(args.build_tools / "apksigner"), "verify", "--print-certs", str(apk))
    match = re.search(r"Signer #1 certificate SHA-256 digest: (\S+)", certificate)
    if not match:
        raise RuntimeError("cannot determine APK signing certificate")

    args.output.mkdir(parents=True, exist_ok=True)
    certificate_file = args.output / "signer-sha256.txt"
    if certificate_file.exists() and certificate_file.read_text().strip() != match[1]:
        raise RuntimeError("A and B APK signing certificates differ")
    certificate_file.write_text(match[1] + "\n", encoding="utf-8")
    suffix = "transparent" if args.variant == "A" else "opaque"
    dest = args.output / f"OSCA550-Diag-{args.variant}-{suffix}-arm64.apk"
    shutil.copy2(apk, dest)
    shutil.copy2(args.source_root / "osca550-diagnostic-manifest.json",
                 args.output / f"manifest-{args.variant}.json")
    (args.output / f"apk-badging-{args.variant}.txt").write_text(badging, encoding="utf-8")
    (args.output / f"apk-signature-{args.variant}.txt").write_text(certificate, encoding="utf-8")
    (args.output / f"{dest.name}.sha256").write_text(
        hashlib.sha256(dest.read_bytes()).hexdigest() + "  " + dest.name + "\n", encoding="utf-8")
    print(json.dumps({"apk": str(dest), "package": PACKAGE, "label": expected_label}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
