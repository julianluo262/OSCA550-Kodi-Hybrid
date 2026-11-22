#!/usr/bin/env python3
"""Verify the range probe APK and diagnostics are present."""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, subprocess, zipfile
from pathlib import Path
PACKAGE='com.osca550.kodi.diag'
def capture(*args): return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT)
def main():
 p=argparse.ArgumentParser();p.add_argument('source_root',type=Path);p.add_argument('build_root',type=Path);p.add_argument('output',type=Path);p.add_argument('build_tools',type=Path);p.add_argument('--variant',choices=('D',),required=True);a=p.parse_args()
 view=a.build_root/'tools/android/packaging/xbmc/src/XBMCVideoView.java'
 if 'setFormat(PixelFormat.TRANSPARENT)' not in view.read_text(encoding='utf-8'): raise RuntimeError('wrong Surface')
 manifest=json.loads((a.source_root/'osca550-diagnostic-manifest.json').read_text(encoding='utf-8'))
 if manifest.get('diagnostic_version')!=3 or manifest.get('variant')!='D-range-probe': raise RuntimeError('wrong manifest')
 apk=a.source_root/'kodiapp-arm64-v8a-release.apk'
 if not apk.is_file(): raise RuntimeError('missing APK')
 badging=capture(str(a.build_tools/'aapt'),'dump','badging',str(apk))
 if f"package: name='{PACKAGE}'" not in badging or "application-label:'Kodi OSCA550 Range Probe D'" not in badging: raise RuntimeError('wrong APK identity')
 if "native-code: 'arm64-v8a'" not in badging and "native-code: 'arm64-v8a'" not in badging.replace('\n',' '): raise RuntimeError('missing ARM64')
 with zipfile.ZipFile(apk) as z:
  native=z.read('lib/arm64-v8a/libkodi.so')
  for marker in (b'OSCA550-RANGE v1',b'D-minimal-format'): 
   if marker not in native: raise RuntimeError('missing native marker '+repr(marker))
 cert=capture(str(a.build_tools/'apksigner'),'verify','--print-certs',str(apk)); m=re.search(r'Signer #1 certificate SHA-256 digest: (\S+)',cert)
 if not m: raise RuntimeError('missing certificate')
 a.output.mkdir(parents=True,exist_ok=True); dest=a.output/'OSCA550-Range-Probe-D-arm64.apk';shutil.copy2(apk,dest);shutil.copy2(a.source_root/'osca550-diagnostic-manifest.json',a.output/'manifest-D-range-probe.json');(a.output/'apk-badging-D.txt').write_text(badging,encoding='utf-8');(a.output/'apk-signature-D.txt').write_text(cert,encoding='utf-8');(a.output/'signer-sha256.txt').write_text(m[1]+'\n',encoding='utf-8');(a.output/(dest.name+'.sha256')).write_text(hashlib.sha256(dest.read_bytes()).hexdigest()+'  '+dest.name+'\n',encoding='utf-8'); print(json.dumps({'apk':str(dest),'package':PACKAGE,'label':'Kodi OSCA550 Range Probe D'},indent=2))
if __name__=='__main__': main()

