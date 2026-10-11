#!/usr/bin/env python3
"""Publish verified CI assets, including a release that was prepared as a draft."""
import argparse,json,pathlib,subprocess


def publish(repository, tag, assets):
    files=sorted(assets.iterdir())
    if not files or any(not file.is_file() or file.is_symlink() for file in files):
        raise RuntimeError('Release assets must be a nonempty flat directory of regular files')
    if not (assets/'SHA256SUMS').is_file():
        raise RuntimeError('Release checksums are missing')
    view=subprocess.run(['gh','release','view',tag,'--repo',repository,'--json','isDraft,assets'],capture_output=True,text=True)
    prerelease='-' in tag
    if view.returncode == 0:
        existing=json.loads(view.stdout)
        if not existing.get('isDraft'):
            raise RuntimeError('Refusing to replace an already published release')
        expected={file.name for file in files}
        if any(asset['name'] not in expected for asset in existing.get('assets',[])):
            raise RuntimeError('Draft contains assets outside the verified delivery')
        subprocess.run(['gh','release','upload',tag,*map(str,files),'--repo',repository,'--clobber'],check=True)
        # Prepared drafts may be untagged. Verify the pushed tag immediately before publication.
        subprocess.run(['gh','api',f'repos/{repository}/git/ref/tags/{tag}'],check=True,stdout=subprocess.DEVNULL)
        subprocess.run(['gh','release','edit',tag,'--repo',repository,'--draft=false','--prerelease='+str(prerelease).lower()],check=True)
    else:
        # Creation itself verifies the pushed tag; a transient lookup failure cannot replace a release.
        command=['gh','release','create',tag,*map(str,files),'--repo',repository,'--verify-tag','--generate-notes']
        if prerelease: command.append('--prerelease')
        subprocess.run(command,check=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True)
    parser.add_argument('--tag',required=True)
    parser.add_argument('--assets',required=True,type=pathlib.Path)
    arguments=parser.parse_args()
    publish(arguments.repo,arguments.tag,arguments.assets)
