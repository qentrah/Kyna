#!/usr/bin/env python3
"""Stage portable CLI/native payloads and verify relocated applications before archiving."""
import argparse, json, os, pathlib, platform, shutil, subprocess, sys
from portable_runtime import stage

def run(*args, env=None):
    subprocess.run([str(x) for x in args], check=True, env=env)

def isolated_environment(runtime_bins, environment=None, windows=None):
    """Keep build tools available while preventing SDK runtime lookup fallbacks."""
    result=dict(os.environ if environment is None else environment)
    for key in ('DYLD_LIBRARY_PATH','DYLD_FRAMEWORK_PATH','LD_LIBRARY_PATH',
                'QML2_IMPORT_PATH','QT_ROOT_DIR','CMAKE_PREFIX_PATH'):
        result.pop(key,None)
    result.update(QT_QPA_PLATFORM='offscreen',QT_PLUGIN_PATH='/nonexistent',QML_IMPORT_PATH='/nonexistent')
    is_windows = os.name=='nt' if windows is None else windows
    if is_windows:
        # Windows searches PATH for DLLs. Retain compiler/CMake directories,
        # but remove the original Qt, vcpkg and unrelocated application bins.
        normalize=lambda path: str(path).replace('\\','/').rstrip('/').lower()
        excluded={normalize(path) for path in runtime_bins}
        result['PATH']=';'.join(path for path in result.get('PATH','').split(';') if normalize(path) not in excluded)
    return result

def notices(root, build, destination):
    licenses = destination / 'licenses'
    licenses.mkdir(exist_ok=True)
    shutil.copy2(root / 'LICENSE', licenses / 'Kyna-LICENSE.txt')
    # vcpkg copyright files include the license notices for the actual resolved ports.
    for copyright in sorted((build / 'vcpkg_installed').glob('*/share/*/copyright')):
        shutil.copy2(copyright, licenses / (copyright.parent.name + '-copyright.txt'))
    shutil.copy2(root / 'docs/native-dependencies.md', licenses / 'DEPENDENCIES.md')
    for file in (root / 'docs/licenses/native').iterdir():
        if file.is_file(): shutil.copy2(file, licenses / file.name)
    if sys.platform.startswith('linux'):
        inventory=json.loads((destination/'runtime-inventory.json').read_text())
        packages={}
        for binary in inventory['binaries']:
            owner=subprocess.run(['dpkg-query','-S',binary['source']],capture_output=True,text=True)
            if owner.returncode:continue
            for line in owner.stdout.splitlines():
                package=line.split(': ',1)[0].split(':')[0]
                copyright=pathlib.Path('/usr/share/doc')/package/'copyright'
                if not copyright.is_file():continue
                shutil.copy2(copyright,licenses/(package+'-copyright.txt'))
                version=subprocess.check_output(['dpkg-query','-W','-f=${Version}',package],text=True)
                packages[package]={'version':version,'notice':package+'-copyright.txt'}
        (licenses/'distribution-packages.json').write_text(json.dumps(packages,indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=pathlib.Path)
    parser.add_argument('--output', required=True, type=pathlib.Path)
    parser.add_argument('--native', action='store_true')
    args=parser.parse_args()
    root=pathlib.Path(__file__).resolve().parents[2]; build=args.build.resolve(); output=args.output.resolve()
    if output.exists(): raise RuntimeError('Choose a fresh delivery staging directory')
    output.mkdir(parents=True)
    cli=output/'cli'
    run('cmake','--install',build,'--config','Release','--prefix',cli)
    # Optional adapters are distributed with their own verified dependency closure.
    # CMake's development installation must not leak unrelocated copies into CLI archives.
    shutil.rmtree(cli/'lib/kyna/native',ignore_errors=True)
    suffix='.exe' if os.name=='nt' else ''
    searches=[p for p in (build/'vcpkg_installed').glob('*/bin') if p.is_dir()]
    stage(cli,[pathlib.Path('bin/ky'+suffix),pathlib.Path('bin/kyna'+suffix)],searches)
    notices(root,build,cli)
    # Relocation is verified in a second directory with SDK environment variables removed.
    moved=output/'relocated-cli'; shutil.copytree(cli,moved)
    qtroot=pathlib.Path(os.environ.get('QT_ROOT_DIR',''))
    environment=isolated_environment(searches+[qtroot/'bin',build/'bin',build/'bin/Release',build/'native',build/'native/Release'])
    ky=moved/'bin'/('ky'+suffix)
    run(ky,'--version',env=environment)
    run(sys.executable,root/'tests/tooling/verify_installed_cli.py',ky,root,env=environment)
    libraries=[]
    if args.native:
        qtpaths=next((p for name in ('qtpaths','qtpaths6','qtpaths.exe','qtpaths6.exe') if (p:=qtroot/'bin'/name).is_file()),None)
        if not qtpaths:
            executable=shutil.which('qtpaths6') or shutil.which('qtpaths')
            qtpaths=pathlib.Path(executable) if executable else None
        if not qtpaths: raise RuntimeError('Qt qtpaths executable is required')
        for name in ('gui','geometry','ml'):
            candidates=list((build/'native').rglob('*kyna_'+name+('.dll' if os.name=='nt' else '.so')))
            if len(candidates)!=1: raise RuntimeError('Expected exactly one native adapter: '+name)
            package=output/name;package.mkdir();library=package/candidates[0].name;shutil.copy2(candidates[0],library)
            stage(package,[pathlib.Path(library.name)],searches+[candidates[0].parent],qtpaths if name=='gui' else None)
            notices(root,build,package)
            if name=='gui':
                qt_version=json.loads((package/'runtime-inventory.json').read_text())['qt_version']
                run(sys.executable,root/'build_tools/packaging/qt_source_notices.py','--version',qt_version,'--payload',package,'--cache',build/'qt-source-material')
            libraries.append(library)
        run(sys.executable,root/'tests/native/verify_optional_packages.py',ky,root,*libraries,env=environment)
    shutil.rmtree(moved)
    (output/'VERIFICATION.json').write_text(json.dumps({'schema':'kyna.delivery/v1','target':platform.system()+'-'+platform.machine(),'relocated_cli':True,'native_application_smoke':bool(args.native)},indent=2)+'\n')
if __name__=='__main__': main()
