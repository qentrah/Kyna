#!/usr/bin/env python3
"""Collect verified Homebrew source provenance and upstream notices for a staged closure.

Source archives remain separate release materials. Nothing is installed or executed.
"""
import argparse, concurrent.futures, hashlib, json, pathlib, re, subprocess, tarfile

def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload',required=True,type=pathlib.Path)
    parser.add_argument('--brew-metadata',required=True,type=pathlib.Path)
    parser.add_argument('--sources',required=True,type=pathlib.Path)
    parser.add_argument('--include',action='append',default=[])
    args=parser.parse_args()
    inventory=json.loads((args.payload/'runtime-inventory.json').read_text())
    metadata={f['name']:f for f in json.loads(args.brew_metadata.read_text())['formulae']}
    versions={}
    for binary in inventory['binaries']:
        match=re.search(r'/Cellar/([^/]+)/([^/]+)/',binary['source'])
        if match: versions[match[1]]=match[2].split('_')[0]
    for name in args.include:
        if name not in metadata: raise RuntimeError('Missing installed source metadata: '+name)
        versions[name]=metadata[name]['installed'][0]['version'].split('_')[0]
    args.sources.mkdir(parents=True,exist_ok=True)
    def collect(pair):
        name,version=pair;formula=metadata[name];stable=formula['urls']['stable']
        if formula['versions']['stable']!=version: raise RuntimeError('Installed/source version disagreement: '+name)
        url,expected=stable['url'],stable['checksum']
        if not url.startswith('https://') or not expected: raise RuntimeError('Unverified source origin: '+name)
        suffix=next((ending for ending in ('.tar.gz','.tar.xz','.tar.bz2','.tgz') if url.split('?')[0].endswith(ending)),'.tar.gz')
        archive=args.sources/(name.replace('@','-')+'-'+version+suffix)
        if not archive.is_file() or sha(archive)!=expected:
            pending=archive.with_suffix(archive.suffix+'.pending')
            subprocess.run(['curl','--fail','--location','--silent','--show-error',
                '--proto','=https','--proto-redir','=https','--retry','2','--max-time','180',
                '--output',str(pending),url],check=True)
            if sha(pending)!=expected: pending.unlink();raise RuntimeError('Source checksum mismatch: '+name)
            pending.replace(archive)
        notices=[]
        with tarfile.open(archive,'r:*') as tar:
            for member in tar:
                if not member.isfile() or member.size>2*1024*1024: continue
                parts=pathlib.PurePosixPath(member.name).parts
                if '..' in parts or member.name.startswith('/'): raise RuntimeError('Unsafe upstream source member')
                filename=parts[-1].lower()
                if not (filename.startswith(('license','licence','copying','copyright','notice')) or 'licenses' in (p.lower() for p in parts) or filename=='qt_attribution.json'): continue
                relative=pathlib.Path(*parts[1:])
                destination=args.payload/'licenses/upstream'/name/relative
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(tar.extractfile(member).read())
                notices.append(destination.relative_to(args.payload).as_posix())
        if not notices: raise RuntimeError('No upstream license notices found: '+name)
        print('Verified source and notices:',name,version,flush=True)
        return {'name':name,'version':version,'license_expression':formula['license'],'source_url':url,'source_archive':archive.name,'source_sha256':expected,'notices':sorted(notices)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records=list(pool.map(collect,sorted(versions.items())))
    (args.payload/'licenses/source-inventory.json').write_text(json.dumps({'schema':'kyna.source-inventory/v1','packages':records},indent=2)+'\n')
if __name__=='__main__': main()
