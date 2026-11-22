#!/usr/bin/env python3
"""Patch full Kodi source with bounded Range/FileCache EOF diagnostics."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "outputs/OSCA550_Kodi_Main10_Diagnostic_v2"
sys.path.insert(0, str(BUNDLE / "patches"))
from prepare_osca550_main10 import CPP, prepare as prepare_main10

MARK = "// OSCA550-RANGE v1: bounded HTTP Range/FileCache EOF diagnostics."


def patch_filecache(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if MARK in text:
        return
    anchor = "    if (iRead <= 0)\n    {\n"
    if text.count(anchor) != 1:
        raise RuntimeError("FileCache read anchor changed")
    insert = """    if (iRead <= 0)
    {
      CLog::Log(LOGINFO,
                "OSCA550-RANGE FileCache read_nonpositive writePos={} readPos={} seekPos={} "
                "sourceLength={} cacheFileSize={} chunkSize={} returned={}",
                m_writePos, m_readPos, m_seekPos, m_source.GetLength(), m_fileSize,
                m_chunkSize, iRead);
"""
    text = text.replace(anchor, insert, 1)
    if "using namespace XFILE;" not in text:
        raise RuntimeError("FileCache namespace anchor missing")
    text = text.replace("\nusing namespace XFILE;", "\n" + MARK + "\n\nusing namespace XFILE;", 1)
    path.write_text(text, encoding="utf-8")


def patch_curl(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if MARK in text:
        return
    anchor = """  m_bufferSize = size;
  m_buffer.Destroy();
  m_buffer.Create(size * 3);
  m_httpheader.Clear();
"""
    if text.count(anchor) != 1:
        raise RuntimeError("Curl Connect anchor changed")
    replacement = """  m_bufferSize = size;
  m_buffer.Destroy();
  m_buffer.Create(size * 3);
  m_httpheader.Clear();
  CLog::Log(LOGINFO, "OSCA550-RANGE connect_begin resumePos={} sendRange={} bufferSize={}",
            m_filePos, m_sendRange, size);
"""
    text = text.replace(anchor, replacement, 1)
    text = text.replace("  curl_off_t length;", "  curl_off_t length = 0;")
    text = text.replace("  double length;", "  double length = 0;")

    # length is declared in the preceding SDK conditional and remains in scope.
    anchor2 = """  long response;
  if (CURLE_OK == g_curlInterface.easy_getinfo(m_easyHandle, CURLINFO_RESPONSE_CODE, &response))
    return response;

  return -1;
}
"""
    if text.count(anchor2) != 1:
        raise RuntimeError("Curl response anchor changed")
    replacement2 = """  long response;
  if (CURLE_OK == g_curlInterface.easy_getinfo(m_easyHandle, CURLINFO_RESPONSE_CODE, &response))
  {
    CLog::Log(LOGINFO, "OSCA550-RANGE connect_end resumePos={} response={} contentLength={} "
              "fileSize={} sendRange={} stillRunning={}",
              m_filePos, response, length, m_fileSize, m_sendRange, m_stillRunning);
    return response;
  }

  CLog::Log(LOGINFO, "OSCA550-RANGE connect_end resumePos={} response=unknown contentLength={} "
            "fileSize={} sendRange={} stillRunning={}",
            m_filePos, length, m_fileSize, m_sendRange, m_stillRunning);
  return -1;
}
"""
    text = text.replace(anchor2, replacement2, 1)

    anchor3 = """  if (!m_stillRunning && (m_fileSize == 0 || m_filePos != m_fileSize))
  {
    CLog::Log(LOGWARNING,
"""
    if text.count(anchor3) != 1:
        raise RuntimeError("Curl premature-read anchor changed")
    replacement3 = """  if (!m_stillRunning && (m_fileSize == 0 || m_filePos != m_fileSize))
  {
    CLog::Log(LOGINFO, "OSCA550-RANGE premature_read pos={} fileSize={} bufferBytes={} stillRunning={}",
              m_filePos, m_fileSize, m_buffer.getMaxReadSize(), m_stillRunning);
    CLog::Log(LOGWARNING,
"""
    text = text.replace(anchor3, replacement3, 1)
    if "using namespace XFILE;" not in text:
        raise RuntimeError("Curl namespace anchor missing")
    text = text.replace("\nusing namespace XFILE;", "\n" + MARK + "\n\nusing namespace XFILE;", 1)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    manifest = prepare_main10(root, "D", check_git=False)
    patch_filecache(root / "xbmc/filesystem/FileCache.cpp")
    patch_curl(root / "xbmc/filesystem/CurlFile.cpp")
    cpp = root / CPP
    text = cpp.read_text(encoding="utf-8")
    anchor = '  CLog::Log(LOGINFO, "OSCA550-DIAG v2 {} Open surface={} hybrid={} "'
    if text.count(anchor) != 1:
        raise RuntimeError("codec open anchor changed")
    text = text.replace(anchor, '  CLog::Log(LOGINFO, "OSCA550-RANGE v1 probe active source=FileCache/CurlFile");\n\n' + anchor, 1)
    cpp.write_text(text, encoding="utf-8")
    manifest.update({
        "diagnostic_version": 3,
        "variant": "D-range-probe",
        "launcher_label": "Kodi OSCA550 Range Probe D",
        "range_probe": True,
        "probe_scope": "FileCache and CurlFile HTTP Range/EOF diagnostics",
    })
    manifest["files_sha256"] = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in manifest["files_sha256"]
    }
    for companion in ("xbmc/filesystem/FileCache.cpp", "xbmc/filesystem/CurlFile.cpp"):
        manifest["files_sha256"][companion] = hashlib.sha256((root / companion).read_bytes()).hexdigest()
    (root / "osca550-diagnostic-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



