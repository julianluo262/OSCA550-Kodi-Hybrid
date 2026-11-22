#!/usr/bin/env python3
"""Export E only after checking identity, D baseline, native markers and signer."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

SIGNER = '6cc81ed76d8d4e8637c487b5835950eeb805934e14993eb3ba1ae5fba7fb188f'
PACKAGE = 'com.osca550.kodi.diag'


def capture(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def main():
    parser = argparse.ArgumentParser()
    for name in ('source_root', 'build_root', 'output', 'build_tools'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    manifest_path = args.source_root / 'osca550-diagnostic-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if (manifest.get('diagnostic_version') != 4 or
            manifest.get('variant') != 'E-minidlna-single-session' or
            manifest.get('surface_format') != 'TRANSPARENT' or
            manifest.get('minimal_format_for_target') is not True):
        raise RuntimeError('Wrong E manifest or D decoder configuration')
    for name, expected in manifest['files_sha256'].items():
        if hashlib.sha256((args.source_root / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Source changed after patching: ' + name)
    view = args.build_root / 'tools/android/packaging/xbmc/src/XBMCVideoView.java'
    if 'setFormat(PixelFormat.TRANSPARENT)' not in view.read_text(encoding='utf-8'):
        raise RuntimeError('Wrong generated Surface')
    apk = args.source_root / 'kodiapp-arm64-v8a-release.apk'
    badging = capture(str(args.build_tools / 'aapt'), 'dump', 'badging', str(apk))
    print(badging, flush=True)
    if (f"package: name='{PACKAGE}'" not in badging or
            "application-label:'Kodi OSCA550 Diag E'" not in badging or
            not re.search(r"^native-code:.*'arm64-v8a'", badging, re.MULTILINE)):
        raise RuntimeError('Wrong E APK identity or architecture')
    with zipfile.ZipFile(apk) as package:
        native = package.read('lib/arm64-v8a/libkodi.so')
    for marker in (b'OSCA550-HTTP-SEEK v1', b'OSCA550-RANGE v1', b'D-minimal-format'):
        if marker not in native:
            raise RuntimeError('Missing native marker: ' + repr(marker))
    cert = capture(str(args.build_tools / 'apksigner'), 'verify', '--print-certs', str(apk))
    match = re.search(r'Signer #1 certificate SHA-256 digest: (\S+)', cert)
    if not match or match[1] != SIGNER:
        raise RuntimeError('Signer differs from installed D; do not uninstall the working app')
    args.output.mkdir(parents=True, exist_ok=True)
    dest = args.output / 'OSCA550-Diag-E-HTTP-seek-arm64.apk'
    shutil.copy2(apk, dest)
    shutil.copy2(manifest_path, args.output / 'manifest-E.json')
    (args.output / 'apk-badging-E.txt').write_text(badging, encoding='utf-8')
    (args.output / 'apk-signature-E.txt').write_text(cert, encoding='utf-8')
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    (args.output / (dest.name + '.sha256')).write_text(digest + '  ' + dest.name + '\n', encoding='utf-8')
    print(json.dumps({'apk': dest.name, 'sha256': digest, 'signer': match[1]}, indent=2))


if __name__ == '__main__':
    main()

