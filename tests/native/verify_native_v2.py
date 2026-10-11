#!/usr/bin/env python3
"""Exercise retained closures, GC, wrong-thread calls, tree/VM execution and stale resources."""
import json,pathlib,subprocess,sys,tempfile
ky,library=map(lambda p:str(pathlib.Path(p).resolve()),sys.argv[1:])
with tempfile.TemporaryDirectory() as directory:
    root=pathlib.Path(directory)
    code='fn closure(seed: int) { var n=seed; fn next(): int { n=n+1; return n; } return next; } var callback=closure(40); retainTestCallback(callback); collectGarbage(); console.log(fireTestCallback()); console.log(wrongThreadTest()); var r=createTestResource(); collectGarbage(); console.log(readTestResource(r));'
    for tree in (False,True):
        (root/'dep.ky').write_text('export var marker=1;')
        (root/'main.ky').write_text(('import { marker } from "./dep.ky";' if tree else '')+code)
        r=subprocess.run([ky,'--native-library',library,'run',str(root/'main.ky')],capture_output=True,text=True,timeout=15)
        assert r.returncode==0 and r.stdout=='41\ntrue\n42\n',(r.stdout,r.stderr)
    callback = 'fn fail(): int {\nvar broken: any = 1;\nreturn broken();\n}\n'
    for imported in (False, True):
        if imported:
            (root/'dep.ky').write_text('export '+callback)
            source = 'import { fail } from "./dep.ky";\n'
        else:
            source = callback
        (root/'main.ky').write_text(source+'retainTestCallback(fail);\nfireTestCallback();\n')
        result = subprocess.run([ky, '--native-library', library, '--diagnostic-format', 'json', 'run', str(root/'main.ky')], capture_output=True, text=True)
        assert result.returncode == 1, result.stderr
        diagnostic = json.loads(result.stderr)['diagnostics'][0]
        assert pathlib.Path(diagnostic['file']).name == ('dep.ky' if imported else 'main.ky'), diagnostic
        assert diagnostic['range']['start']['line'] == 3, diagnostic
        assert any(frame['function'] == 'fail' for frame in diagnostic['callFrames']), diagnostic
    for imported in (False, True):
        callback = 'fn fail(): int {\n\nthrow "boom";\n}\n'
        if imported:
            (root/'dep.ky').write_text('export '+callback)
            source = 'import { fail } from "./dep.ky";\n'
        else:
            source = callback
        (root/'main.ky').write_text(source+'retainTestCallback(fail);\nfireTestCallback();\n')
        result = subprocess.run([ky, '--native-library', library, '--diagnostic-format', 'json', 'run', str(root/'main.ky')], capture_output=True, text=True)
        diagnostic = json.loads(result.stderr)['diagnostics'][0]
        assert result.returncode == 1 and diagnostic['code'] == ('KRT2301' if imported else 'KVM2301'), diagnostic
        assert pathlib.Path(diagnostic['file']).name == ('dep.ky' if imported else 'main.ky'), diagnostic
        assert diagnostic['range']['start']['line'] == 3, diagnostic
        assert any(frame['function'] == 'fail' for frame in diagnostic['callFrames']), diagnostic
    (root/'main.ky').write_text('var r=createTestResource(); disposeTestResource(r); readTestResource(r);')
    r=subprocess.run([ky,'--native-library',library,'run',str(root/'main.ky')],capture_output=True,text=True)
    assert r.returncode!=0 and 'KNATIVE1006' in r.stderr,r.stderr
print('ABI 2 callback/resource tests passed')
