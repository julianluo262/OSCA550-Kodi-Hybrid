#!/usr/bin/env python3
"""Compare explicit Main10 profile and a minimal HiSilicon MediaFormat."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from prepare_osca550_diag import CPP, STRINGS, prepare as prepare_baseline, replace_once

VARIANTS = {"C": "C-main10-profile", "D": "D-minimal-format"}

PROFILE_BLOCK = '''  // OSCA550-DIAG v2: restrict the experiment to clear HiSilicon HEVC Main10.
  const bool osca550Main10 = m_hints.codec == AV_CODEC_ID_HEVC &&
                            m_hints.profile == FF_PROFILE_HEVC_MAIN_10 &&
                            m_mime == "video/hevc" && !m_hints.cryptoSession &&
                            m_codecname.rfind("OMX.hisi.", 0) == 0;
  if (osca550Main10)
    mediaformat.setInteger("profile", CJNIMediaCodecInfoCodecProfileLevel::HEVCProfileMain10);
  CLog::Log(LOGINFO, "OSCA550-DIAG v2 {} Main10 experiment eligible={} minimal={}",
            OSCA550_VARIANT, osca550Main10, @MINIMAL@);

'''


def prepare(root: Path, variant: str, *, check_git: bool = True) -> dict:
    if variant not in VARIANTS:
        raise ValueError("variant must be C or D")
    # This reconstructs the exact transparent-Surface diagnostic baseline from
    # verified original Git blobs, including when switching from C to D.
    manifest = prepare_baseline(root, "A", check_git=check_git)
    root = root.resolve()
    cpp = (root / CPP).read_text(encoding="utf-8")
    cpp = replace_once(cpp, 'OSCA550_VARIANT = "A-transparent";',
                       f'OSCA550_VARIANT = "{VARIANTS[variant]}";', "variant identity")
    cpp = cpp.replace("OSCA550-DIAG v1", "OSCA550-DIAG v2")

    start_anchor = "  mediaformat.setInteger(CJNIMediaFormat::KEY_MAX_INPUT_SIZE, 0);\n"
    end_anchor = "  // handle codec extradata\n"
    if cpp.count(start_anchor) != 1 or cpp.count(end_anchor) != 1:
        raise RuntimeError("MediaFormat experiment anchors changed")
    start = cpp.index(start_anchor)
    end = cpp.index(end_anchor, start)
    original_options = cpp[start:end]
    profile = PROFILE_BLOCK.replace("@MINIMAL@", "true" if variant == "D" else "false")
    if variant == "C":
        options = profile + original_options
    else:
        indented = "".join("  " + line if line.strip() else line
                           for line in original_options.splitlines(keepends=True))
        options = (profile + "  if (!osca550Main10)\n  {\n" + indented + "  }\n\n")
    cpp = cpp[:start] + options + cpp[end:]
    if cpp.count("  InjectExtraData(mediaformat);") != 1:
        raise RuntimeError("Codec initialization data must remain present")

    strings = (root / STRINGS).read_text(encoding="utf-8")
    strings = replace_once(strings, "Kodi OSCA550 Diag A", f"Kodi OSCA550 Diag {variant}",
                           "launcher label")
    for name, content in ((CPP, cpp), (STRINGS, strings)):
        path = root / name
        data = content.encode("utf-8")
        if path.read_bytes() != data:
            path.write_bytes(data)

    manifest.update({
        "diagnostic_version": 2,
        "variant": VARIANTS[variant],
        "launcher_label": f"Kodi OSCA550 Diag {variant}",
        "surface_format": "TRANSPARENT",
        "decoder_behaviour": "explicit HEVC Main10 profile for clear HiSilicon HEVC Main10",
        "minimal_format_for_target": variant == "D",
        "unchanged": ["HEVC bitstream conversion", "csd-0 injection", "Surface selection",
                      "flush and buffer release", "other decoders and encrypted streams"],
        "omitted_optional_fields_for_target": [] if variant == "C" else [
            "max-input-size", "priority", "operating-rate", "rotation-degrees",
            "feature-tunneled-playback", "color-range", "color-standard", "color-transfer",
            "hdr-static-info"],
    })
    manifest["files_sha256"] = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in manifest["files_sha256"]}
    (root / "osca550-diagnostic-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--variant", choices=tuple(VARIANTS), required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source_root, args.variant), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
