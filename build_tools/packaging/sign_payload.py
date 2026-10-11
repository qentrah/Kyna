#!/usr/bin/env python3
"""Sign release payloads, validate signatures, and refresh their byte inventories."""
import argparse, base64, hashlib, json, os, pathlib, plistlib, shutil, subprocess, sys, tempfile
from portable_runtime import native_file


def run(*args):
    # Signing passwords must never appear in command diagnostics or process output.
    result = subprocess.run([str(value) for value in args], capture_output=True)
    if result.returncode:
        raise RuntimeError('Release signing tool failed: ' + pathlib.Path(str(args[0])).name)


def required(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError('Missing release credential: ' + name)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('payloads', nargs='+', type=pathlib.Path)
    args = parser.parse_args()
    inventories = []
    for root in args.payloads:
        file = root / 'runtime-inventory.json'
        inventory = json.loads(file.read_text())
        binaries = [root / binary['path'] for binary in inventory['binaries']]
        if any(not path.resolve().is_relative_to(root.resolve()) for path in binaries):
            raise RuntimeError('Binary inventory escapes payload')
        inventories.append((root, file, inventory, binaries))
    with tempfile.TemporaryDirectory(prefix='kyna-signing-') as temporary:
        directory = pathlib.Path(temporary)
        certificate = directory / 'certificate.p12'
        certificate.write_bytes(base64.b64decode(required('CERTIFICATE_BASE64'), validate=True))
        certificate.chmod(0o600)
        password = required('CERTIFICATE_PASSWORD')
        if sys.platform == 'darwin':
            identity = required('SIGNING_IDENTITY')
            keychain = directory / 'release.keychain'
            key_password = os.urandom(24).hex()
            run('security', 'create-keychain', '-p', key_password, keychain)
            try:
                run('security', 'unlock-keychain', '-p', key_password, keychain)
                run('security', 'import', certificate, '-k', keychain, '-P', password, '-T', '/usr/bin/codesign')
                run('security', 'set-key-partition-list', '-S', 'apple-tool:,apple:', '-s', '-k', key_password, keychain)
                entitlements = directory / 'runtime.plist'
                # Native packages are explicitly trusted plug-ins. Qt's QML engine uses JIT.
                entitlements.write_bytes(plistlib.dumps({'com.apple.security.cs.disable-library-validation': True,
                                                         'com.apple.security.cs.allow-jit': True}))
                for root, file, inventory, binaries in inventories:
                    for path in binaries:
                        run('codesign', '--force', '--options', 'runtime', '--timestamp', '--keychain', keychain,
                            '--entitlements', entitlements, '--sign', identity, path)
                        run('codesign', '--verify', '--strict', path)
            finally:
                run('security', 'delete-keychain', keychain)
        elif os.name == 'nt':
            tools = sorted(pathlib.Path('C:/Program Files (x86)/Windows Kits/10/bin').glob('*/x64/signtool.exe'))
            if not tools:
                raise RuntimeError('Windows SDK signing tool is missing')
            for root, file, inventory, binaries in inventories:
                for path in binaries:
                    if path.name.lower() not in ('ky.exe', 'kyna.exe') and not path.name.lower().startswith('kyna_'):
                        continue  # Keep third-party publisher signatures intact.
                    run(tools[-1], 'sign', '/fd', 'SHA256', '/tr', 'http://timestamp.digicert.com', '/td', 'SHA256',
                        '/f', certificate, '/p', password, path)
                    run(tools[-1], 'verify', '/pa', path)
        else:
            raise RuntimeError('Signing is supported only on macOS and Windows')
    for root, file, inventory, binaries in inventories:
        for binary, path in zip(inventory['binaries'], binaries):
            with path.open('rb') as stream:
                binary['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        inventory['release_signed'] = True
        file.write_text(json.dumps(inventory, indent=2) + '\n')

if __name__ == '__main__':
    main()
