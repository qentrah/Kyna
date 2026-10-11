#!/usr/bin/env python3
"""Release gates reject modified payloads and unaccepted notarization responses."""
import hashlib, importlib.util, json, os, pathlib, subprocess, sys, tempfile, unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build_tools/packaging'))
import notarize_payload, sign_payload

class ReleasePackagingTests(unittest.TestCase):
    def test_archive_rejects_modified_binary(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=pathlib.Path(temporary);delivery=directory/'delivery';cli=delivery/'cli';cli.mkdir(parents=True)
            (delivery/'VERIFICATION.json').write_text(json.dumps({'relocated_cli':True}))
            (cli/'ky').write_bytes(b'modified')
            (cli/'runtime-inventory.json').write_text(json.dumps({'binaries':[{'path':'ky','sha256':hashlib.sha256(b'original').hexdigest()}]}))
            result=subprocess.run([sys.executable,str(ROOT/'build_tools/packaging/archive_delivery.py'),'--delivery',str(delivery),'--target','darwin-arm64','--output',str(directory/'archives')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Binary changed after inventory',result.stderr)
            self.assertFalse((directory/'archives').exists())

    def test_archive_rejects_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=pathlib.Path(temporary);delivery=directory/'delivery';cli=delivery/'cli';cli.mkdir(parents=True)
            (delivery/'VERIFICATION.json').write_text(json.dumps({'relocated_cli':True}))
            (cli/'runtime-inventory.json').write_text(json.dumps({'binaries':[{'path':'../../outside','sha256':'unused'}]}))
            result=subprocess.run([sys.executable,str(ROOT/'build_tools/packaging/archive_delivery.py'),'--delivery',str(delivery),'--target','darwin-arm64','--output',str(directory/'archives')],capture_output=True,text=True)
            self.assertIn('Inventory path escapes',result.stderr)

    def test_signing_error_does_not_disclose_tool_output(self):
        with patch.object(sign_payload.subprocess,'run',return_value=subprocess.CompletedProcess([],1,stdout=b'private-password',stderr=b'private-certificate')):
            with self.assertRaisesRegex(RuntimeError,'Release signing tool failed: codesign') as error:
                sign_payload.run('codesign','private-password')
            self.assertNotIn('private',str(error.exception))

    def test_notarization_requires_accepted_status(self):
        credentials={'APPLE_ID':'private','APPLE_TEAM_ID':'private','APPLE_APP_PASSWORD':'private'}
        with patch.dict(os.environ,credentials),patch.object(sys,'argv',['notarize','payload']),patch.object(notarize_payload.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0),subprocess.CompletedProcess([],0,stdout=json.dumps({'status':'Invalid'}))]):
            with self.assertRaisesRegex(RuntimeError,'did not accept'):
                notarize_payload.main()

    def test_notarization_accepts_valid_response(self):
        credentials={'APPLE_ID':'private','APPLE_TEAM_ID':'private','APPLE_APP_PASSWORD':'private'}
        with patch.dict(os.environ,credentials),patch.object(sys,'argv',['notarize','payload']),patch.object(notarize_payload.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0),subprocess.CompletedProcess([],0,stdout=json.dumps({'status':'Accepted','id':'fixture'}))]):
            notarize_payload.main()

if __name__=='__main__':unittest.main()
