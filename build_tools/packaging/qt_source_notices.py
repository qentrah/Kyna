#!/usr/bin/env python3
"""Collect Qt SDK source notices from vendor archives with vendor SHA-256 sidecars."""
import argparse,json,pathlib,re,subprocess
from source_notices import download_source,extract_notices

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',required=True)
    parser.add_argument('--payload',required=True,type=pathlib.Path)
    parser.add_argument('--cache',required=True,type=pathlib.Path)
    args=parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+',args.version):parser.error('Expected an exact Qt version')
    base='https://download.qt.io/archive/qt/'+'.'.join(args.version.split('.')[:2])+'/'+args.version+'/submodules/'
    args.cache.mkdir(parents=True,exist_ok=True);records=[]
    for name in ('qtbase','qtdeclarative','qtsvg'):
        filename=name+'-everywhere-src-'+args.version+'.tar.xz'
        checksum=subprocess.check_output(['curl','--fail','--location','--silent','--show-error','--proto','=https','--proto-redir','=https','--retry','3',base+filename+'.sha256'],text=True)
        fields=checksum.split()
        if len(fields)!=2 or fields[1].lstrip('*')!=filename or not re.fullmatch('[a-f0-9]{64}',fields[0]):raise RuntimeError('Invalid Qt source checksum sidecar')
        archive=args.cache/filename;download_source(base+filename,fields[0],archive)
        notices=extract_notices(archive,args.payload,name)
        records.append({'name':name,'version':args.version,'source_url':base+filename,'source_sha256':fields[0],'source_archive':filename,'notices':notices})
        print('Verified Qt source and notices:',name,args.version,flush=True)
    (args.payload/'licenses/qt-source-inventory.json').write_text(json.dumps({'schema':'kyna.source-inventory/v1','packages':records},indent=2)+'\n')
if __name__=='__main__':main()
