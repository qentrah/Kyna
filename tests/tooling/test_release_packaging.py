#!/usr/bin/env python3
"""Release gates reject modified payloads and unaccepted notarization responses."""
import hashlib, io, json, os, pathlib, subprocess, sys, tarfile, tempfile, unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build_tools/packaging'))
import notarize_payload, sign_payload, source_notices, portable_runtime, qt_source_notices

class ReleasePackagingTests(unittest.TestCase):
    def test_android_notice_resources_include_checked_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=pathlib.Path(temporary);payload=root/'payload';licenses=payload/'licenses';licenses.mkdir(parents=True)
            for name in ('qt-source-inventory.json','Kyna-LICENSE.txt','Qt-LICENSE.txt'):(licenses/name).write_text('notice')
            output=root/'notices.qrc';qt_source_notices.write_qrc(payload,output,[{'notices':['licenses/Qt-LICENSE.txt']}])
            document=qt_source_notices.ET.parse(output)
            aliases={file.attrib['alias'] for file in document.findall('./qresource/file')}
            self.assertEqual(aliases,{'licenses/qt-source-inventory.json','licenses/Kyna-LICENSE.txt','licenses/Qt-LICENSE.txt'})
            with self.assertRaisesRegex(RuntimeError,'Invalid Qt notice resource'):
                qt_source_notices.write_qrc(payload,output,[{'notices':['../../outside']}])

    def test_dependency_tool_failure_preserves_diagnostic(self):
        failure=subprocess.CalledProcessError(1,['cmake'],output='unresolved dependency: required.dll')
        with patch.object(portable_runtime.subprocess,'check_output',side_effect=failure):
            with self.assertRaisesRegex(RuntimeError,'unresolved dependency: required.dll'):
                portable_runtime.run('cmake','-P','scan.cmake')

    def test_elf_dependency_preserves_loader_soname(self):
        with patch.object(portable_runtime.sys,'platform','linux'),patch.object(portable_runtime,'run',return_value='libarmadillo.so.15\n'):
            self.assertEqual(portable_runtime.dependency_filename(pathlib.Path('/sdk/libarmadillo.so.15.2.3')),'libarmadillo.so.15')

    def test_elf_soname_cannot_escape_payload(self):
        with patch.object(portable_runtime.sys,'platform','linux'),patch.object(portable_runtime,'run',return_value='../outside.so'):
            with self.assertRaisesRegex(RuntimeError,'Invalid ELF dependency SONAME'):
                portable_runtime.dependency_filename(pathlib.Path('dependency.so'))

    def test_universal_macho_headers_are_not_dependencies(self):
        output='/sdk/plugin (architecture x86_64):\n\t@rpath/QtCore (compatibility version 6.0.0, current version 6.7.3)\n/sdk/plugin (architecture arm64):\n\t@rpath/QtCore (compatibility version 6.0.0, current version 6.7.3)\n'
        with patch.object(portable_runtime,'run',return_value=output):
            self.assertEqual(portable_runtime.macho_dependencies(pathlib.Path('plugin')),['@rpath/QtCore'])

    def test_universal_macho_rpaths_are_deduplicated(self):
        section='cmd LC_RPATH\ncmdsize 32\npath @loader_path/../lib (offset 12)\n'
        with patch.object(portable_runtime,'run',return_value=section+section):
            self.assertEqual(portable_runtime.macho_rpaths(pathlib.Path('plugin')),['@loader_path/../lib'])

    def test_qt_staging_excludes_debug_bundles(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=pathlib.Path(temporary);sdk=directory/'sdk';sdk.mkdir()
            (sdk/'plugin.dylib').write_bytes(b'runtime')
            (sdk/'plugin.pdb').write_bytes(b'debug')
            dwarf=sdk/'plugin.dylib.dSYM/Contents/Resources/DWARF/plugin'
            dwarf.parent.mkdir(parents=True);dwarf.write_bytes(b'debug-mach-o')
            portable_runtime.copy_regular_tree(sdk,directory/'runtime')
            self.assertEqual(sorted(p.name for p in (directory/'runtime').iterdir()),['plugin.dylib'])
            self.assertEqual((directory/'runtime/plugin.dylib').read_bytes(),b'runtime')

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
