#!/usr/bin/env python3
"""Stage and relocate an explicit binary closure; emit a hashed dependency inventory."""
import argparse, hashlib, json, os, pathlib, re, shutil, subprocess, sys, tempfile

def run(*arguments):
    try:
        return subprocess.check_output([str(x) for x in arguments], text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(str(arguments[0]) + ' failed:\n' + (error.output or '')[-12000:]) from error

def digest(path):
    with path.open('rb') as stream:
        checksum = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
        return checksum.hexdigest()

def macho_dependencies(path):
    # Universal binaries have one unindented section header per architecture.
    names = [line.strip().split(' (compatibility', 1)[0]
             for line in run('otool', '-L', path).splitlines()
             if line[:1].isspace()]
    return list(dict.fromkeys(names))

def macho_rpaths(path):
    return list(dict.fromkeys(re.findall(r'cmd LC_RPATH\s+cmdsize \d+\s+path (.*?) \(offset', run('otool', '-l', path))))

def system_macho(name):
    return name.startswith(('/usr/lib/', '/System/Library/'))

def expand_macho(name, source, executable):
    return name.replace('@loader_path', str(source.parent)).replace('@executable_path', str(executable.parent))

def resolve_macho(name, source, executable, searches):
    if name.startswith('@rpath/'):
        suffix = name[len('@rpath/'):]
        paths = [pathlib.Path(expand_macho(p, source, executable)) / suffix for p in macho_rpaths(source)]
        paths += [p / suffix for p in searches]
    else:
        paths = [pathlib.Path(expand_macho(name, source, executable))]
    for path in paths:
        if path.is_file(): return path.resolve()
    raise RuntimeError(f'unresolved dependency {name} of {source}')

def copy_regular_tree(source, destination, recursive=True):
    for path in sorted(source.rglob('*') if recursive else source.iterdir()):
        relative = path.relative_to(source)
        if any(part.lower().endswith('.dsym') for part in relative.parts) or path.suffix.lower() in ('.pdb', '.debug', '.ilk', '.exp', '.lib', '.a', '.o'):
            continue
        if path.is_file():
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists(): target.chmod(target.stat().st_mode | 0o200)
            shutil.copy2(path.resolve(), target)

def stage_qt(root, location, qt):
    queries = dict(line.split(':', 1) for line in run(qt, '--query').splitlines() if ':' in line)
    qml = pathlib.Path(queries['QT_INSTALL_QML'])
    plugins = pathlib.Path(queries['QT_INSTALL_PLUGINS'])
    for group in ('platforms', 'imageformats', 'tls', 'networkinformation'):
        if (plugins / group).is_dir(): copy_regular_tree(plugins / group, root / location / 'plugins' / group)
    for module in ('QtQml', 'QtQuick'):
        if not (qml / module).is_dir(): raise RuntimeError(f'missing QML module {module}')
        # QtQuick's Controls, Dialogs and Shapes are not imported by the adapter.
        copy_regular_tree(qml / module, root / location / 'qml' / module, module == 'QtQml')
    return queries

def windows_system_filters():
    # Stop recursion at OS DLLs, preserving redistributable MSVC runtimes even
    # when CMake resolves those from System32. Match mixed separators/casing
    # emitted by Windows CMake versions without excluding sibling directories.
    root = os.environ.get('SystemRoot', 'C:/Windows').replace('\\', '/').rstrip('/')
    def pattern(path):
        return ''.join(r'[/\\]' if c == '/' else '['+c.lower()+c.upper()+']' if c.isalpha() else re.escape(c) for c in path)
    directories = '|'.join(pattern(name) for name in ('system32', 'syswow64', 'winsxs'))
    exclude = '^' + pattern(root) + r'[/\\]([^/\\]+[.]dll$|(' + directories + r')[/\\])'
    include = r'[/\\](vcruntime|msvcp|concrt)[^/\\]*[.]dll$'
    return include, exclude

def cmake_dependencies(seeds, searches):
    def quote(path): return '[==[' + str(path).replace('\\', '/') + ']==]'
    script = 'cmake_minimum_required(VERSION 3.25)\n'
    if sys.platform == 'win32':
        tool = shutil.which('dumpbin')
        if not tool:
            candidates = list(pathlib.Path('C:/Program Files/Microsoft Visual Studio').rglob('dumpbin.exe'))
            candidates = [p for p in candidates if 'Hostx64/x64' in p.as_posix()]
            if candidates: tool = str(sorted(candidates)[-1])
        if not tool: raise RuntimeError('MSVC dumpbin is required for Windows dependency auditing')
        script += 'set(CMAKE_GET_RUNTIME_DEPENDENCIES_TOOL dumpbin)\nset(CMAKE_GET_RUNTIME_DEPENDENCIES_COMMAND ' + quote(tool) + ')\n'
    with tempfile.TemporaryDirectory(prefix='kyna-dependency-scan-') as directory:
        output = pathlib.Path(directory) / 'dependencies.txt'
        script += 'file(GET_RUNTIME_DEPENDENCIES RESOLVED_DEPENDENCIES_VAR found UNRESOLVED_DEPENDENCIES_VAR missing CONFLICTING_DEPENDENCIES_PREFIX conflicts\n'
        if sys.platform == 'win32':
            # API-set names are OS loader contracts, not redistributable DLL files.
            script += 'PRE_EXCLUDE_REGEXES "[Aa][Pp][Ii]-[Mm][Ss]-.*" "[Ee][Xx][Tt]-[Mm][Ss]-.*"\n'
            include, exclude = windows_system_filters()
            script += 'POST_INCLUDE_REGEXES [==[' + include + ']==]\nPOST_EXCLUDE_REGEXES [==[' + exclude + ']==]\n'
        executables = [p for p in seeds if p.suffix.lower() == '.exe' or p.name in ('ky', 'kyna')]
        libraries = [p for p in seeds if p not in executables]
        if executables: script += 'EXECUTABLES ' + ' '.join(map(quote, executables)) + '\n'
        if libraries: script += 'LIBRARIES ' + ' '.join(map(quote, libraries)) + '\n'
        if searches: script += 'DIRECTORIES ' + ' '.join(map(quote, searches)) + '\n'
        script += 'PRE_EXCLUDE_REGEXES "^api-ms-" "^ext-ms-"\n)\n'
        script += 'if(missing OR conflicts_FILENAMES)\nmessage(FATAL_ERROR "Unresolved/conflicting dependencies: ${missing};${conflicts_FILENAMES}")\nendif()\n'
        script += 'string(REPLACE ";" "\\n" result "${found}")\nfile(WRITE ' + quote(output) + ' "${result}")\n'
        file = pathlib.Path(directory) / 'scan.cmake'; file.write_text(script)
        run('cmake', '-P', file)
        return [pathlib.Path(line) for line in output.read_text().splitlines() if line]

def native_file(path):
    with path.open('rb') as stream: magic = stream.read(4)
    return magic in (b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'\x7fELF') or magic[:2] == b'MZ'

def dependency_filename(source):
    if sys.platform.startswith('linux'):
        soname = run('patchelf', '--print-soname', source).strip()
        if soname:
            if pathlib.PurePosixPath(soname).name != soname or '\\' in soname or soname in ('.', '..'):
                raise RuntimeError('Invalid ELF dependency SONAME')
            return soname
        return source.name
    return source.resolve().name

def stage(root, binary_paths, search_paths, qt=None, qt_location=pathlib.Path('qt')):
    root = root.resolve()
    seeds = [root / p for p in binary_paths]
    for seed in seeds:
        if not seed.is_file() or not seed.resolve().is_relative_to(root): raise RuntimeError(f'invalid staged binary {seed}')
    queries = stage_qt(root, qt_location, qt) if qt else {}
    seeds += [p for p in (root / qt_location).rglob('*') if p.is_file() and native_file(p)]
    searches = [p.resolve() for p in search_paths]
    if queries:
        searches.extend(pathlib.Path(queries[key]) for key in ('QT_INSTALL_LIBS', 'QT_INSTALL_BINS') if key in queries)
    library_dir = seeds[0].parent if sys.platform == 'win32' else root / 'lib/runtime'
    library_dir.mkdir(parents=True, exist_ok=True)
    copies, origins, system = {}, {}, set()
    def copy_dependency(source):
        filename = dependency_filename(source)
        source = source.resolve()
        if source in copies: return copies[source]
        destination = library_dir / filename
        if sys.platform == 'darwin':
            framework = next((parent for parent in source.parents if parent.name.endswith('.framework')), None)
            if framework:
                destination = library_dir / framework.name / source.relative_to(framework)
                # QLibraryInfo uses the framework's CFBundle, not just its Mach-O.
                # Preserve bundle resources as regular files (native archives forbid links).
                resources = framework / 'Resources'
                if resources.is_dir():
                    copy_regular_tree(resources.resolve(), library_dir / framework.name / 'Resources')
                    copy_regular_tree(resources.resolve(), destination.parent / 'Resources')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source in copies: return copies[source]
        if destination.exists() and digest(destination) != digest(source): raise RuntimeError(f'conflicting dependency basename {source.name}')
        shutil.copy2(source, destination); copies[source] = destination; origins[destination] = source
        return destination
    if sys.platform == 'darwin':
        executable = next((p for p in seeds if p.name in ('ky', 'kyna')), seeds[0])
        pending = [(p, p) for p in seeds]; mappings = {}
        while pending:
            source, destination = pending.pop()
            if destination in mappings: continue
            dependencies = {}
            for name in macho_dependencies(source):
                if system_macho(name): system.add(name); continue
                resolved = resolve_macho(name, source, executable, searches)
                # Dylib LC_ID_DYLIB is included by otool -L, but is not a dependency.
                if resolved == source.resolve(): continue
                copied = copy_dependency(resolved); dependencies[name] = copied
                pending.append((resolved, copied))
            mappings[destination] = dependencies
        for destination, dependencies in mappings.items():
            for name, copied in dependencies.items():
                relative = os.path.relpath(copied, destination.parent)
                run('install_name_tool', '-change', name, '@loader_path/' + relative, destination)
            for rpath in macho_rpaths(destination): run('install_name_tool', '-delete_rpath', rpath, destination)
            # Dylib IDs must no longer advertise a build-machine framework path.
            if destination.name not in ('ky', 'kyna'):
                run('install_name_tool', '-id', '@loader_path/' + destination.name, destination)
            run('codesign', '--force', '--sign', '-', '--timestamp=none', destination)
            for name in macho_dependencies(destination):
                if not system_macho(name) and not name.startswith('@loader_path/'):
                    raise RuntimeError(f'nonportable dependency left in {destination}: {name}')
    else:
        for dependency in cmake_dependencies(seeds, searches):
            name = dependency.name.lower()
            if sys.platform == 'win32':
                # UCRT and Windows APIs belong to the supported OS; C++ CRT does not.
                if 'windows/system32/' in dependency.as_posix().lower() and not name.startswith(('vcruntime', 'msvcp', 'concrt')):
                    system.add(str(dependency)); continue
            elif re.match(r'^(ld-linux.*|lib(c|m|pthread|dl|rt|resolv|util)\.so.*)$', name):
                system.add(str(dependency)); continue
            copy_dependency(dependency)
        if sys.platform != 'win32':
            if not shutil.which('patchelf'): raise RuntimeError('patchelf is required for Linux relocation')
            for path in [*seeds, *copies.values()]:
                run('patchelf', '--set-rpath', '$ORIGIN/' + os.path.relpath(library_dir, path.parent), path)
    files = [*seeds, *copies.values()]
    inventory = {'schema':'kyna.portable-runtime/v1', 'platform':sys.platform, 'qt_version':queries.get('QT_VERSION'),
        'system_dependencies':sorted(system), 'binaries':[{'path':p.relative_to(root).as_posix(), 'sha256':digest(p), 'source':str(origins.get(p, p))} for p in sorted(set(files))]}
    if sys.platform == 'win32':
        inventory['system_dependency_policy'] = 'OS DLLs in Windows/System32, SysWOW64, WinSxS and the Windows root are excluded; MSVC redistributables remain audited and bundled.'
    (root / 'runtime-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    return inventory

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=pathlib.Path)
    parser.add_argument('--binary', action='append', required=True, type=pathlib.Path)
    parser.add_argument('--search-directory', action='append', default=[], type=pathlib.Path)
    parser.add_argument('--qtpaths', type=pathlib.Path)
    parser.add_argument('--qt-location', default=pathlib.Path('qt'), type=pathlib.Path)
    args=parser.parse_args()
    if args.qt_location.is_absolute() or '..' in args.qt_location.parts: parser.error('qt-location must remain inside staging')
    result=stage(args.root,args.binary,args.search_directory,args.qtpaths,args.qt_location)
    print('Staged',len(result['binaries']),'portable binaries; Qt',result['qt_version'])
if __name__=='__main__': main()
