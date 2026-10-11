#!/usr/bin/env python3
"""Exercise type contracts through the public CLI, imports, and warm caches."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    binary = str(Path(sys.argv[1]).resolve())
    def check(source, code=None, name=None):
        if name:
            Path(name).write_text(source)
        arguments = [binary, 'check', str(name) if name else '-', '--no-color', '--diagnostic-format', 'json']
        result = subprocess.run(arguments, input=None if name else source, text=True, capture_output=True, timeout=20)
        diagnostics = json.loads(result.stderr)['diagnostics'] if result.stderr else []
        if code:
            assert result.returncode == 1, (source, result.stderr)
            assert code in {d['code'] for d in diagnostics}, (source, diagnostics)
        else:
            assert result.returncode == 0, (source, result.stderr)
        return diagnostics

    cases = [
        ('var x: int = null;', 'KSEM1505'),
        ('var x: int? = 1; var y: int = x;', 'KSEM1505'),
        ('fn consume(cb: fn(int): int): int { return cb(1); } fn wrong(x: str): int { return 1; } consume(wrong);', 'KSEM1202'),
        ('intf Box<T> {value:T;} var x: Box<int,str> = {value:1};', 'KSEM1502'),
        ('var x=1; var x=2;', 'KSEM1102'),
        ('switch(1){default:{} default:{}}', 'KSYN1301'),
        ('switch(1){default:{} case 1:{}}', 'KSYN1302'),
        ('switch(1){case "1":{}}', 'KSEM1307'),
        ('fn f(): int { return null; }', 'KSEM1507'),
        ('fn f(x: int?): int { return x; }', 'KSEM1507'),
        ('var big = 9223372036854775808;', 'KSEM1604'),
        ('switch(0){case 0:{} case -0.0:{}}', 'KSEM1306'),
        ('fn f(x: int): int { return x; } var g = f; g("bad");', 'KSEM1202'),
        ('fn f(x: int) { return x; } var g = f; g();', 'KSEM1201'),
        ('fn f(x: int) { return x; } var result: str = f(1);', 'KSEM1505'),
        ('fn f(x: int) { return f(x); }', 'KSEM1503'),
        ('type A = B; type B = A;', 'KSEM1501'),
        ('type A = int; print(A);', 'KSEM1504'),
        ('loop { fn f(): void { break; } break; }', 'KSEM1301'),
        ('loop { fn f(): void { continue; } break; }', 'KSEM1301'),
        ('switch (1) { case 1: {} case 1: {} }', 'KSEM1306'),
        ('switch (1) { case 1: {} case 1.0: {} }', 'KSEM1306'),
        ('var x = 1; switch (1) { case x: {} }', 'KSEM1305'),
        ('var wrong: int = 1 / 2;', 'KSEM1505'),
        ('var wrong = 1 && true;', 'KSEM1601'),
        ('var wrong = !1;', 'KSEM1601'),
        ('var wrong = "a" < "b";', 'KSEM1602'),
        ('var wrong = 1.5 % 2;', 'KSEM1603'),
        ('console.missing("hello");', 'KSEM2404'),
    ]
    for source, code in cases: check(source, code)
    for source in [
        'var x: int? = null; var y: int? = 1;',
        'var minimum:int = -9223372036854775808;',
        'switch(9223372036854775807){case 9223372036854775806:{} case 9223372036854775807:{}}',
        'switch(9007199254740992.0){case 9007199254740993:{} case 9007199254740992.0:{}}',
        'type Count = int; fn f(x: Count) { return x + 1; } var g = f; var result: Count = g(1);',
        'fn f(x: int): int { return x; } var g: fn(int): int = f; var result: int = g(1);',
        'var result: float = 1 / 2;',
        'switch (1.0) { case 1.000001: {} case 1.000002: {} }',
    ]: check(source)

    with tempfile.TemporaryDirectory(prefix='kyna-contracts-') as directory:
        root = Path(directory)
        cache_root = root / "host-cache"
        os.environ["KYNA_EXPORT_CACHE_DIR"] = str(cache_root)
        types = root / 't.ky'
        types.write_text('export type Count = int; export intf Person { name: str; } export intf Box<T> { value: T; } print("must not run");')
        library = root / 'library.ky'
        library.write_text('export fn add(value: int) { return value + 1; } export var count = 42;')
        entry = root / 'main.ky'
        source = 'import { add as plus, count } from "./library.ky"; var x: int = plus(count);'
        for _ in range(2): check(source, name=entry)
        # Foreign compiler/checker cache versions are misses, never trusted contracts.
        cache = next(cache_root.glob('library.ky.*.kyc'))
        assert not Path(str(library) + '.kyc').exists()
        old_cache = cache.read_text()
        cache.write_text('KYC3-contracts-foreign-compiler\n' + old_cache.split('\n', 1)[1])
        check(source, name=entry)
        assert cache.read_text().splitlines()[0] != 'KYC3-contracts-foreign-compiler'
        for _ in range(2):
            check('import { add as plus } from "./library.ky"; plus("bad");', 'KSEM1202', entry)
            check('import * as lib from "./library.ky"; lib.add();', 'KSEM1201', entry)
            check('import { count } from "./library.ky"; var bad: str = count;', 'KSEM1505', entry)
            check('import { hidden } from "./library.ky";', 'K4004', entry)
        check('import type { Count } from "./t.ky"; var count: Count = 42;', name=entry)
        check('import type { Count as Total } from "./t.ky"; var count: Total = 42;', name=entry)
        check('import type { Person } from "./t.ky"; var person: Person = {name:"A"};', name=entry)
        check('import type { Box } from "./t.ky"; var box: Box<int> = {value:1};', name=entry)
        check('import type { Box } from "./t.ky"; var box: Box<int> = {value:"bad"};', 'KSEM1506', entry)
        check('import type { Box } from "./t.ky"; var box: Box = {value:1};', 'KSEM1502', entry)
        check('import * as types from "./t.ky"; print(types.Person);', 'KSEM1504', entry)
        check('var count = 1; export type { count };', 'KSEM1504', entry)
        (root / 'reexport.ky').write_text('import type { Person } from "./t.ky"; export type { Person };')
        check('import type { Person } from "./reexport.ky"; var person: Person = {name:"A"};', name=entry)
        check('import type * as types from "./t.ky"; var count: types.Count = 42;', name=entry)
        check('import type { Count } from "./t.ky"; print(Count);', 'KSEM1504', entry)
        entry.write_text('import type { Count } from "./t.ky"; var count: Count = 42; print(count);')
        result = subprocess.run([binary, 'run', str(entry), '--no-color'], capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and result.stdout == '42\n', result
        private_types = root / 'private.ky'
        private_types.write_text('type Internal = int; type T = str; '
                                 'export type Count = Internal; '
                                 'export intf Box<T> { value: Internal; other: T; } '
                                 'export intf Wrapper { child: Hidden; } '
                                 'intf Hidden { number: Internal; }')
        (root / 'private_reexport.ky').write_text('import type { Box, Wrapper } from "./private.ky"; export type { Box, Wrapper };')
        private_stamp = None
        for _ in range(2):
            check('import type { Count, Box } from "./private.ky"; var count: Count = 1; '
                  'var box: Box<int> = {value:1, other:2};', name=entry)
            check('import type { Box } from "./private_reexport.ky"; '
                  'var box: Box<str> = {value:1, other:"ok"};', name=entry)
            check('import type { Box } from "./private_reexport.ky"; '
                  'var box: Box<str> = {value:"bad", other:"ok"};', 'KSEM1506', entry)
            check('import type { Internal } from "./private.ky";', 'K4004', entry)
            check('import type { Hidden } from "./private.ky";', 'K4004', entry)
            check('import type * as types from "./private.ky"; '
                  'var hidden: types.Hidden = {number:1};', 'KSEM1505', entry)
            stamp = next(cache_root.glob('private.ky.*.kyc')).stat().st_mtime_ns
            if private_stamp is not None:
                assert stamp == private_stamp, "checked private contracts must reuse the warm cache"
            private_stamp = stamp
        check('import type { Box } from "./private.ky"; '
              'var box: Box<int?> = {value:1, other:null};', name=entry)
        check('import type { Box } from "./private.ky"; '
              'var box: Box<int?> = {value:1, other:"bad"};', 'KSEM1506', entry)
        # Retain private interface dependencies, including references declared later.
        check('import type { Wrapper } from "./private.ky"; '
              'var wrapper: Wrapper = {child:{number:1}};', name=entry)
        check('import type { Wrapper } from "./private_reexport.ky"; '
              'var wrapper: Wrapper = {child:{number:"bad"}};', 'KSEM1506', entry)
        # Exact bytes, not file metadata alone, determine cache validity.
        original = library.stat()
        library.write_text('export fn add(value: str) { return value; } export var count = 42;')
        os.utime(library, ns=(original.st_atime_ns, original.st_mtime_ns))
        check(source, 'KSEM1202', entry)
    print('type contract verification passed')

if __name__ == '__main__': main()
