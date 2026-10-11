#!/usr/bin/env python3
"""Release gates reject modified payloads and unaccepted notarization responses."""
import hashlib, io, json, os, pathlib, subprocess, sys, tarfile, tempfile, unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build_tools/packaging'))
import notarize_payload, sign_payload, source_notices, portable_runtime

class ReleasePackagingTests(unittest.TestCase):
    def test_hashing_does_not_require_python_311(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=pathlib.Path(temporary)/'binary';path.write_bytes(b'release-payload')
            with patch.object(hashlib,'file_digest',None,create=True):
                self.assertEqual(portable_runtime.digest(path),hashlib.sha256(path.read_bytes()).hexdigest())

    def test_source_notice_rejects_windows_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=pathlib.Path(temporary);archive=directory/'source.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:
                entry=tarfile.TarInfo('source/C:\\outside/LICENSE');entry.size=1;tar.addfile(entry,io.BytesIO(b'x'))
            with self.assertRaisesRegex(RuntimeError,'Unsafe upstream'):
                source_notices.extract_notices(archive,directory/'payload','fixture')

    def test_source_notice_handles_root_license(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=pathlib.Path(temporary);archive=directory/'source.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:
                entry=tarfile.TarInfo('LICENSE');entry.size=1;tar.addfile(entry,io.BytesIO(b'x'))
            names=source_notices.extract_notices(archive,directory/'payload','fixture')
            self.assertEqual(names,['licenses/upstream/fixture/LICENSE'])
            self.assertEqual((directory/'payload'/names[0]).read_bytes(),b'x')

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
