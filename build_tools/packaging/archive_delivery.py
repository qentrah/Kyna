#!/usr/bin/env python3
"""Archive only verified delivery directories, with matching native metadata and hashes."""
import argparse,hashlib,json,pathlib,re,subprocess,sys,tarfile,zipfile
from portable_runtime import digest as sha256_file, native_file

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery',required=True,type=pathlib.Path)
    parser.add_argument('--target',required=True,choices=('linux-x86_64','linux-arm64','darwin-x86_64','darwin-arm64','windows-x86_64'))
    parser.add_argument('--output',required=True,type=pathlib.Path)
    parser.add_argument('--native-only',action='store_true')
    args=parser.parse_args();root=pathlib.Path(__file__).resolve().parents[2]
    version=re.search(r'project\(kyna VERSION ([0-9.]+)',(root/'CMakeLists.txt').read_text())[1]
    verification=json.loads((args.delivery/'VERIFICATION.json').read_text())
    if not verification.get('relocated_cli'):raise RuntimeError('Delivery has not passed relocation checks')
    for package in ('cli','gui','geometry','ml'):
        directory=args.delivery/package
        if not directory.exists():continue
        inventory=json.loads((directory/'runtime-inventory.json').read_text())
        for binary in inventory['binaries']:
            path=(directory/binary['path']).resolve()
            if not path.is_relative_to(directory.resolve()):raise RuntimeError('Inventory path escapes package')
            digest=sha256_file(path)
            if digest!=binary['sha256']:raise RuntimeError('Binary changed after inventory: '+binary['path'])
        if any(path.is_symlink() for path in directory.rglob('*')):raise RuntimeError('Package contains links')
        listed={binary['path'] for binary in inventory['binaries']}
        for path in directory.rglob('*'):
            if path.is_file() and native_file(path) and path.relative_to(directory).as_posix() not in listed:
                raise RuntimeError('Untracked native binary in payload: '+path.name)
    args.output.mkdir(parents=True,exist_ok=True)
    if args.native_only and not verification.get('native_application_smoke'):raise RuntimeError('Native delivery has not passed application checks')
    if not args.native_only and not args.target.startswith('windows'):
        archive=args.output/f'kyna-{args.target}.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            for file in sorted((args.delivery/'cli').iterdir()):tar.add(file,arcname=file.name)
    elif not args.native_only:
        archive=args.output/f'kyna-{args.target}.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zip:
            for file in sorted((args.delivery/'cli').rglob('*')):
                if file.is_file():zip.write(file,file.relative_to(args.delivery/'cli'))
    if verification.get('native_application_smoke'):
        for name in ('gui','geometry','ml'):
            package=args.delivery/name
            library=next(package.glob('*kyna_'+name+('.dll' if args.target.startswith('windows') else '.so')))
            subprocess.run([sys.executable,str(root/'tools/native-packager/package.py'),'--package',name,'--version',version,'--target',args.target,'--library',str(library),'--runtime-files',str(package),'--output',str(args.output)],check=True)
    entries=[]
    for file in sorted(args.output.iterdir()):
        if file.is_file() and file.name!='SHA256SUMS':
            digest=sha256_file(file)
            entries.append(digest+'  '+file.name+'\n')
    (args.output/'SHA256SUMS').write_text(''.join(entries))
    print('Archived verified delivery:',args.target)
if __name__=='__main__':main()
