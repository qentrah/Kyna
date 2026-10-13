#!/usr/bin/env python3
"""Require an Accepted notarization result without exposing credential diagnostics."""
import argparse, json, os, pathlib, subprocess, tempfile

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('payload',type=pathlib.Path)
    args=parser.parse_args()
    names=('APPLE_ID','APPLE_TEAM_ID','APPLE_APP_PASSWORD')
    values=[os.environ.get(name) for name in names]
    if not all(values):raise RuntimeError('Apple notarization credentials are required')
    with tempfile.TemporaryDirectory(prefix='kyna-notarization-') as directory:
        archive=pathlib.Path(directory)/'payload.zip'
        subprocess.run(['ditto','-c','-k','--keepParent',str(args.payload),str(archive)],check=True)
        result=subprocess.run(['xcrun','notarytool','submit',str(archive),'--apple-id',values[0],
                               '--team-id',values[1],'--password',values[2],'--wait','--output-format','json'],capture_output=True,text=True)
        if result.returncode:raise RuntimeError('Apple notarization command failed')
        report=json.loads(result.stdout)
        if report.get('status')!='Accepted':raise RuntimeError('Apple did not accept the payload for notarization')
        print('Notarization accepted:',report.get('id',''))
if __name__=='__main__':main()
