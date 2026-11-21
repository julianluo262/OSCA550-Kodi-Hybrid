#!/usr/bin/env python3
"""Prepare two reproducible diagnostic variants; no decoder fix is applied."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SOURCE_COMMIT = "1c2da8772de76760e63cd4c30f2ea7143c660e80"
APP_PACKAGE = "com.osca550.kodi.diag"
CPP = "xbmc/cores/VideoPlayer/DVDCodecs/Video/DVDVideoCodecAndroidMediaCodec.cpp"
HEADER = "xbmc/cores/VideoPlayer/DVDCodecs/Video/DVDVideoCodecAndroidMediaCodec.h"
VIEW = "tools/android/packaging/xbmc/src/XBMCVideoView.java.in"
STRINGS = "tools/android/packaging/xbmc/strings.xml.in"
SETTINGS = "system/settings/settings.xml"
BLOBS = {
    CPP: "a1d0c78af0c750d37d82fabbf50a38560d57f44b",
    HEADER: "e049d94218c0a97f09c56528ddcce827717e490d",
    VIEW: "ad131e90c5d2cc4477ef21f87464ed579fa5038f",
    STRINGS: "141a1a3fe1f372e80a504e573eba7b6731de20b4",
    SETTINGS: "b226ebcc77caf313ecdd424c424181d4ca3de009",
    "version.txt": "8b70ad0084e3ecf448e850071c7b4ef7e46ba6c9",
}

DIAGNOSTICS = r'''
// OSCA550-DIAG v1: observation only. Do not suppress or skip stale-buffer calls.
namespace
{
constexpr const char* OSCA550_VARIANT = "@VARIANT@";
std::atomic<unsigned int> g_osca550FlushSerial{0};
std::atomic<unsigned int> g_osca550OutputLogs{0};
std::atomic<unsigned int> g_osca550ReleaseLogs{0};

void LogOSCA550JniException(JNIEnv* env, const char* where)
{
  jthrowable exception = env->ExceptionOccurred();
  if (!exception)
    return;

  // Retain the original Android exception report, and also put the stack in kodi.log.
  env->ExceptionDescribe();
  env->ExceptionClear();
  std::string detail = "Java exception (stack unavailable)";
  jclass logClass = env->FindClass("android/util/Log");
  if (env->ExceptionCheck())
    env->ExceptionClear();
  if (logClass)
  {
    jmethodID getStack = env->GetStaticMethodID(
        logClass, "getStackTraceString", "(Ljava/lang/Throwable;)Ljava/lang/String;");
    if (env->ExceptionCheck())
      env->ExceptionClear();
    if (getStack)
    {
      jstring stack = static_cast<jstring>(env->CallStaticObjectMethod(logClass, getStack, exception));
      if (env->ExceptionCheck())
        env->ExceptionClear();
      else if (stack)
      {
        const char* text = env->GetStringUTFChars(stack, nullptr);
        if (env->ExceptionCheck())
          env->ExceptionClear();
        else if (text)
        {
          detail = text;
          env->ReleaseStringUTFChars(stack, text);
        }
      }
      if (stack)
        env->DeleteLocalRef(stack);
    }
    env->DeleteLocalRef(logClass);
  }
  env->DeleteLocalRef(exception);
  CLog::Log(LOGERROR, "OSCA550-DIAG v1 {} JNI exception in {}: {}", OSCA550_VARIANT, where,
            detail);
}
} // namespace
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def set_default(text: str, setting_id: str, value: str) -> str:
    pattern = re.compile(
        r'(<setting\b[^>]*\bid="' + re.escape(setting_id) + r'"[^>]*>)(.*?)(</setting>)',
        re.DOTALL,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(f"setting {setting_id}: expected exactly one definition")
    match = matches[0]
    block, count = re.subn(r"<default>.*?</default>", f"<default>{value}</default>",
                           match.group(2), flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"setting {setting_id}: expected exactly one default")
    return text[:match.start(2)] + block + text[match.end(2):]


def instrument_cpp(text: str, variant: str) -> str:
    # Replace only the pinned source's existing exception handlers, before adding the helper.
    pattern = re.compile(
        r"(?P<indent>[ \t]*)xbmc_jnienv\(\)->ExceptionDescribe\(\);\n"
        r"(?P=indent)xbmc_jnienv\(\)->ExceptionClear\(\);"
    )
    text, count = pattern.subn(
        lambda m: m["indent"] + "LogOSCA550JniException(xbmc_jnienv(), __func__);", text)
    if count != 21:
        raise RuntimeError(f"expected 21 pinned JNI exception handlers, found {count}")
    text = replace_once(text, "using namespace KODI::MESSAGING;\n",
                        "using namespace KODI::MESSAGING;\n" +
                        DIAGNOSTICS.replace("@VARIANT@", variant), "diagnostic helper")
    text = replace_once(text, "  m_bufferId = bufferId;\n",
                        "  m_bufferId = bufferId;\n"
                        "  m_osca550FlushSerial = g_osca550FlushSerial.load();\n"
                        "  if (g_osca550OutputLogs.fetch_add(1) < 64)\n"
                        "    CLog::Log(LOGINFO, \"OSCA550-DIAG output index={} serial={}\",\n"
                        "              bufferId, m_osca550FlushSerial);\n", "output generation")
    text = replace_once(text, "  if (!render || displayTime == 0)\n",
                        "  const int diagnosticIndex = m_bufferId;\n"
                        "  const unsigned int diagnosticSerial = g_osca550FlushSerial.load();\n"
                        "  if (g_osca550ReleaseLogs.fetch_add(1) < 64 ||\n"
                        "      m_osca550FlushSerial != diagnosticSerial)\n"
                        "    CLog::Log(LOGINFO,\n"
                        "              \"OSCA550-DIAG release index={} render={} assignedSerial={} \"\n"
                        "              \"currentSerial={} displayTime={}\",\n"
                        "              diagnosticIndex, render, m_osca550FlushSerial, diagnosticSerial,\n"
                        "              displayTime);\n\n"
                        "  if (!render || displayTime == 0)\n", "release observation")
    text = replace_once(text,
                        '    CLog::Log(LOGERROR, "CMediaCodecVideoBuffer::ReleaseOutputBuffer error in render({})", render);',
                        '    CLog::Log(LOGERROR, "CMediaCodecVideoBuffer::ReleaseOutputBuffer error in render({})", render);\n'
                        '    CLog::Log(LOGERROR, "OSCA550-DIAG failed release index={} assignedSerial={} "\n'
                        '              "currentSerial={}", diagnosticIndex, m_osca550FlushSerial,\n'
                        '              diagnosticSerial);', "failed release context")
    text = replace_once(text, "  m_hints = hints;\n\n  // On Quest devices",
                        "  m_hints = hints;\n"
                        "  g_osca550FlushSerial.store(0);\n"
                        "  g_osca550OutputLogs.store(0);\n"
                        "  g_osca550ReleaseLogs.store(0);\n"
                        '  CLog::Log(LOGINFO, "OSCA550-DIAG v1 {} Open surface={} hybrid={} "\n'
                        '            "profile={} level={} {}x{}", OSCA550_VARIANT, m_render_surface,\n'
                        "            m_render_hybrid, hints.profile, hints.level, hints.width, hints.height);\n\n"
                        "  // On Quest devices",
                        "Open marker")
    text = replace_once(text, "    m_codec->flush();\n",
                        "    const unsigned int diagnosticSerial = g_osca550FlushSerial.fetch_add(1) + 1;\n"
                        '    CLog::Log(LOGINFO, "OSCA550-DIAG flush begin serial={} state={}",\n'
                        "              diagnosticSerial, m_state);\n"
                        "    m_codec->flush();\n"
                        '    CLog::Log(LOGINFO, "OSCA550-DIAG flush returned serial={} exception={}",\n'
                        "              diagnosticSerial, xbmc_jnienv()->ExceptionCheck() == JNI_TRUE);\n",
                        "flush observation")
    text = replace_once(text, "  m_codec->configure(mediaformat, m_jnivideosurface,\n",
                        '  CLog::Log(LOGINFO, "OSCA550-DIAG v1 {} configure codec={} surface={} hybrid={} "\n'
                        '            "format={}", OSCA550_VARIANT, m_codecname, m_render_surface,\n'
                        "            m_render_hybrid, mediaformat.toString());\n"
                        "  m_codec->configure(mediaformat, m_jnivideosurface,\n", "configure observation")
    text = replace_once(text,
                        "void CDVDVideoCodecAndroidMediaCodec::surfaceChanged(CJNISurfaceHolder holder, int format, int width, int height)\n{\n}",
                        "void CDVDVideoCodecAndroidMediaCodec::surfaceChanged(CJNISurfaceHolder holder, int format, int width, int height)\n{\n"
                        '  CLog::Log(LOGINFO, "OSCA550-DIAG v1 {} surfaceChanged format={} {}x{}",\n'
                        "            OSCA550_VARIANT, format, width, height);\n}", "surface format observation")
    return text


def blob_hash(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def prepare(root: Path, variant: str, *, check_git: bool = True) -> dict:
    root = root.resolve()
    if variant not in ("A", "B"):
        raise ValueError("variant must be A or B")
    if check_git:
        actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                         text=True).strip()
        if actual != SOURCE_COMMIT:
            raise RuntimeError(f"source commit mismatch: expected {SOURCE_COMMIT}, got {actual}")

    backups = root / ".osca550-diag-originals"
    originals = {}
    for name, expected in BLOBS.items():
        backup = backups / name
        data = (backup if backup.is_file() else root / name).read_bytes()
        if blob_hash(data) != expected:
            raise RuntimeError(f"source content mismatch: {name}; use the pinned checkout")
        originals[name] = data

    label = "A-transparent" if variant == "A" else "B-opaque"
    planned = {name: data.decode("utf-8") for name, data in originals.items()}
    planned[CPP] = instrument_cpp(planned[CPP], label)
    planned[HEADER] = replace_once(planned[HEADER], "  int m_bufferId = -1;\n",
                                  "  int m_bufferId = -1;\n"
                                  "  unsigned int m_osca550FlushSerial = 0;\n", "buffer diagnostic field")
    planned["version.txt"] = replace_once(planned["version.txt"], "APP_PACKAGE org.xbmc.kodi\n",
                                         f"APP_PACKAGE {APP_PACKAGE}\n", "package identity")
    planned[STRINGS] = replace_once(planned[STRINGS], '<string name="app_name">@APP_NAME@</string>',
                                   f'<string name="app_name">Kodi OSCA550 Diag {variant}</string>',
                                   "launcher label")
    for setting_id, value in {
        "videoplayer.usemediacodec": "true",
        "videoplayer.usemediacodecsurface": "true",
        "videoplayer.usemediacodechybridsurface": "false",
        "debug.showloginfo": "true",
    }.items():
        planned[SETTINGS] = set_default(planned[SETTINGS], setting_id, value)
    if variant == "B":
        planned[VIEW] = replace_once(planned[VIEW], "setFormat(PixelFormat.TRANSPARENT)",
                                    "setFormat(PixelFormat.OPAQUE)", "opaque Surface experiment")

    # Do not write anything until all source hashes and replacement anchors passed.
    for name, data in originals.items():
        backup = backups / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(data)
    for name, text in planned.items():
        path = root / name
        data = text.encode("utf-8")
        if path.read_bytes() != data:
            path.write_bytes(data)
    manifest = {
        "diagnostic_version": 1, "variant": label, "source_commit": SOURCE_COMMIT,
        "package": APP_PACKAGE, "launcher_label": f"Kodi OSCA550 Diag {variant}",
        "surface_format": "TRANSPARENT" if variant == "A" else "OPAQUE",
        "decoder_behaviour": "unchanged; logging and observation only",
        "jni_exception_handlers_instrumented": 21,
        "files_sha256": {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
                         for name, text in planned.items()},
    }
    (root / "osca550-diagnostic-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--variant", choices=("A", "B"), required=True)
    args = parser.parse_args()
    manifest = prepare(args.source_root, args.variant)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
