#!/usr/bin/env python3
"""Enable the fork's Hybrid MediaCodec Surface setting for the first OSCA-550 test.

This changes only Kodi's default setting values. It does not alter codec/rendering
C++ or Java code; those implementation changes come from vkapartzianis/xbmc:Omega.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

SETTING_VALUES = {
    # The hybrid path is selected only when the normal direct-surface option is off.
    "videoplayer.usemediacodecsurface": "false",
    "videoplayer.usemediacodechybridsurface": "true",
}


def set_default(xml: str, setting_id: str, value: str) -> str:
    # Locate one <setting id="..."> ... </setting> block without reformatting
    # the rest of Kodi's settings.xml.
    pat = re.compile(
        r"(<setting\b(?=[^>]*\bid=[\"']" + re.escape(setting_id) +
        r"[\"'])[^>]*>)(.*?)(</setting>)",
        re.DOTALL,
    )
    match = pat.search(xml)
    if not match:
        raise RuntimeError(f"Required setting not found: {setting_id}")
    block = match.group(2)
    default_pat = re.compile(r"(<default\b[^>]*>)(.*?)(</default>)", re.DOTALL)
    if not default_pat.search(block):
        raise RuntimeError(f"<default> not found inside setting: {setting_id}")
    new_block = default_pat.sub(lambda m: m.group(1) + value + m.group(3), block, count=1)
    return xml[:match.start(2)] + new_block + xml[match.end(2):]


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} PATH_TO_SETTINGS_XML", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"Settings file does not exist: {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    for setting_id, value in SETTING_VALUES.items():
        text = set_default(text, setting_id, value)
        print(f"Set {setting_id} default = {value}")
    path.write_text(text, encoding="utf-8")
    print("Hybrid Surface first-test defaults applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
