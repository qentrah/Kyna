#!/usr/bin/env python3
"""Stage portable CLI/native payloads and verify relocated applications before archiving."""
import argparse, json, os, pathlib, platform, shutil, subprocess, sys
from portable_runtime import stage

def run(*args, env=None):
    subprocess.run([str(x) for x in args], check=True, env=env)

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
    suffix='.exe' if os.name=='nt' else ''
    searches=[p for p in (build/'vcpkg_installed').glob('*/bin') if p.is_dir()]
    stage(cli,[pathlib.Path('bin/ky'+suffix),pathlib.Path('bin/kyna'+suffix)],searches)
    notices(root,build,cli)
    # Relocation is verified in a second directory with SDK environment variables removed.
    moved=output/'relocated-cli'; shutil.copytree(cli,moved)
    environment=dict(os.environ,QT_QPA_PLATFORM='offscreen',QT_PLUGIN_PATH='/nonexistent',QML_IMPORT_PATH='/nonexistent')
    for key in ('DYLD_LIBRARY_PATH','DYLD_FRAMEWORK_PATH','LD_LIBRARY_PATH'): environment.pop(key,None)
    ky=moved/'bin'/('ky'+suffix)
    run(ky,'--version',env=environment)
    run(sys.executable,root/'tests/tooling/verify_installed_cli.py',ky,root,env=environment)
    libraries=[]
    if args.native:
        qtroot=pathlib.Path(os.environ.get('QT_ROOT_DIR',''))
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
            libraries.append(library)
        run(sys.executable,root/'tests/native/verify_optional_packages.py',ky,root,*libraries,env=environment)
    shutil.rmtree(moved)
    (output/'VERIFICATION.json').write_text(json.dumps({'schema':'kyna.delivery/v1','target':platform.system()+'-'+platform.machine(),'relocated_cli':True,'native_application_smoke':bool(args.native)},indent=2)+'\n')
if __name__=='__main__': main()
