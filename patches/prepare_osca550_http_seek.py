#!/usr/bin/env python3
"""Keep D decoding and use a single HTTP session with MiniDLNA 1.2 servers."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from prepare_osca550_diag import STRINGS, replace_once
from prepare_osca550_range_probe import main as prepare_range_probe

CURL = 'xbmc/filesystem/CurlFile.cpp'
MARKER = '// OSCA550-HTTP-SEEK v1: retire old transfers before MiniDLNA seeks.'


def patch_http(text: str) -> str:
    if MARKER in text:
        return text
    anchor = '  if(StringUtils::EqualsNoCase(m_state->m_httpheader.GetValue("Transfer-Encoding"), "chunked"))\n'
    addition = '''  // OSCA550-HTTP-SEEK v1: retire old transfers before MiniDLNA seeks.
  // MiniDLNA 1.2.1 reproduced a stalled new Range request while earlier
  // open-ended responses remained unread. The existing single-session Seek
  // path calls Disconnect() before opening the next Range request.
  const std::string osca550Server = m_state->m_httpheader.GetValue("Server");
  if ((url2.IsProtocol("http") || url2.IsProtocol("https")) &&
      osca550Server.find("MiniDLNA/1.2.") != std::string::npos)
  {
    m_multisession = false;
    CLog::Log(LOGINFO, "OSCA550-HTTP-SEEK v1 mode=single server={}", osca550Server);
  }

'''
    text = replace_once(text, anchor, addition + anchor, 'MiniDLNA session policy')
    # Observe errors that Connect currently reports as response=0. Keep its
    # existing return semantics so this experiment changes only session policy.
    failed = '''    if (CURLE_OK == g_curlInterface.easy_getinfo(m_easyHandle, CURLINFO_RESPONSE_CODE, &response))
      return response;
    else
      return -1;
'''
    logged = '''    if (CURLE_OK == g_curlInterface.easy_getinfo(m_easyHandle, CURLINFO_RESPONSE_CODE, &response))
    {
      CLog::Log(LOGINFO, "OSCA550-HTTP-SEEK connect_failed pos={} response={} fileSize={} "
                "bufferBytes={}", m_filePos, response, m_fileSize, m_buffer.getMaxReadSize());
      return response;
    }
    else
      return -1;
'''
    return replace_once(text, failed, logged, 'failed Connect observation')


def main() -> int:
    # The Range Probe parser accepts the same one source_root argument.
    prepare_range_probe()
    root = Path(sys.argv[1]).resolve()
    path = root / CURL
    path.write_text(patch_http(path.read_text(encoding='utf-8')), encoding='utf-8')
    strings = root / STRINGS
    strings.write_text(replace_once(strings.read_text(encoding='utf-8'),
                       'Kodi OSCA550 Diag D', 'Kodi OSCA550 Diag E', 'launcher E'), encoding='utf-8')
    manifest_path = root / 'osca550-diagnostic-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.update(diagnostic_version=4, variant='E-minidlna-single-session',
                    launcher_label='Kodi OSCA550 Diag E',
                    http_seek_policy='single session only for MiniDLNA/1.2.x servers')
    manifest['files_sha256'] = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in manifest['files_sha256']
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

