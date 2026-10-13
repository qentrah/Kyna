#!/usr/bin/env python3
"""Run real native adapters, checked wrappers, rejected conversions, and install/build smoke tests."""
import hashlib, os, pathlib, shutil, subprocess, sys, tempfile
ky, root, gui, geometry, ml = map(pathlib.Path, sys.argv[1:])
ky, root, gui, geometry, ml = (p.resolve() for p in (ky, root, gui, geometry, ml))
env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", QT_FORCE_STDERR_LOGGING="1")
if os.name == "nt":
    # Windows runners provide a desktop session. Exercise the production QPA
    # plugin and native font database. GUI code must also remain resident for
    # Qt's process-global meta-types after session cleanup.
    env["QT_QPA_PLATFORM"] = "windows"
def run(args, success=True, cwd=root):
    r = subprocess.run([str(ky), *map(str,args)], cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
    assert (r.returncode == 0) == success, (args, r.returncode, hex(r.returncode & 0xffffffff), r.stdout, r.stderr)
    return r
assert "[9, 11]" in run(["--native-library",ml,"run",root/"examples/native/apps/regression.ky"]).stdout
assert "1" in run(["--native-library",geometry,"run",root/"examples/native/apps/hull.ky"]).stdout
mesh_output = run(["--native-library",geometry,"run",root/"examples/native/apps/mesh.ky"]).stdout
assert abs(float(mesh_output.splitlines()[-1]) - 1/6) < 1e-6
unexpected=gui.parent/'unlisted-kyna-test.dll'
portable_windows_gui=sys.platform=='win32' and (gui.parent/'runtime-inventory.json').is_file()
if portable_windows_gui:
    assert not unexpected.exists()
    unexpected.write_bytes(b'not an executable DLL')
try:
    assert "GUI callback delivered" in run(["--native-library",gui,"run",root/"examples/native/apps/gui_smoke.ky"]).stdout
finally:
    if portable_windows_gui:unexpected.unlink()
with tempfile.TemporaryDirectory(prefix="kyna-native-packages-") as folder:
    project=pathlib.Path(folder)
    def source(code):
        p=project/"main.ky";p.write_text(code);return p
    if portable_windows_gui:
        # Failed initialization must not commit a partially configured engine.
        # Restore the inventory inside the same VM, then retry GUI startup.
        import json
        inventory=gui.parent/'runtime-inventory.json';original=inventory.read_text()
        restored=json.dumps(original,ensure_ascii=False)
        path=json.dumps(inventory.as_posix(),ensure_ascii=False)
        recovery=source('try { guiWindow("Unavailable",64,64); } catch (failure) { console.log("GUI_INIT_REJECTED"); } try { writeFile('+path+','+restored+'); } catch (failure) { console.log(failure); } var w=guiWindow("Recovered",64,64); fn stop(): void { guiQuit(); } guiAfter(1,stop); collectGarbage(); guiRun(); console.log("GUI_INIT_RECOVERED");')
        run(['--native-library',gui,'check',recovery],cwd=project)
        try:
            inventory.write_text('{"schema":"invalid","binaries":[]}')
            recovered=run(['--native-library',gui,'run',recovery],cwd=project)
            assert 'GUI_INIT_REJECTED' in recovered.stdout and 'GUI_INIT_RECOVERED' in recovered.stdout,recovered
        finally:inventory.write_text(original)
    # ky build --native compiles an authored C++ adapter, not just a staging shell.
    native_source = project/"authored-native"
    native_source.mkdir()
    (native_source/"fixture.cpp").write_bytes((root/"tests/native/native_v2_fixture.cpp").read_bytes())
    (native_source/"CMakeLists.txt").write_text(f'''cmake_minimum_required(VERSION 3.25)
project(AuthoredNative LANGUAGES CXX)
find_package(Threads REQUIRED)
add_library(fixture MODULE fixture.cpp)
target_compile_features(fixture PRIVATE cxx_std_20)
target_include_directories(fixture PRIVATE "{(root/"sdk/kyna_embedding/include").as_posix()}" "{(root/"library/native/include").as_posix()}")
target_link_libraries(fixture PRIVATE Threads::Threads)
set_target_properties(fixture PROPERTIES PREFIX "" SUFFIX ".native")
''')
    authored_build = project/"authored-build"
    run(["build", "--native", native_source, "--output", authored_build], cwd=project)
    authored_library = next(authored_build.rglob("fixture.native"))
    result = run(["--native-library", authored_library, "run", source('var r=createTestResource(); console.log(readTestResource(r));')])
    assert result.stdout.strip() == "42"
    missing = project/"no-cmake-project"
    missing.mkdir()
    failed = run(["--diagnostic-format", "json", "build", "--native", missing, "--output", project/"failed-native"], False, cwd=project)
    import json
    payload = json.loads(failed.stderr)
    assert payload["diagnostics"][0]["code"] == "KBUILD1005", payload
    absent_env = {**env, "PATH": ""}
    failed = subprocess.run([str(ky), "--diagnostic-format", "json", "build", "--native", native_source, "--output", str(project/"absent-tool")], env=absent_env, cwd=project, capture_output=True, text=True, timeout=30)
    assert failed.returncode == 2 and json.loads(failed.stderr)["diagnostics"][0]["code"] == "KBUILD1004", failed.stderr
    for library,code in [(ml,'mlTrain([[1.0, 2.0]], [1.0]);'),(ml,'var m = mlTrain([[1.0, 2.0]], [3.0, 5.0]); mlDispose(m); mlPredict(m, [[3.0]]);'),(geometry,'geometryOrientation([0.0], [1.0, 1.0], [2.0, 2.0]);')]:
        run(["--native-library",library,"run",source(code)],False)
    source('fn failure(): void { var bad: any = 1; bad(); } var timer=guiAfter(1,failure); guiRun();')
    run(["--native-library",gui,"run",project/"main.ky"],False)
    for dimensions in ['0, 480', '-1, 480', '2147483648, 480', '640, 2147483648']:
        result = run(["--native-library", gui, "run", source('var f: any = guiWindow; f("Invalid", '+dimensions+');')], False)
        assert "KNATIVE1003" in result.stderr and "positive 32-bit" in result.stderr
    icon=project/'icon.ppm';icon.write_bytes(b'P6\n1 1\n255\n\x20\xd0\x60')
    import json
    run(["--native-library",gui,"run",source('guiIcon('+json.dumps(icon.as_posix())+');')])
    rejected=run(["--native-library",gui,"run",source('guiIcon("/missing-kyna-icon.png");')],False)
    assert 'KNATIVE1003' in rejected.stderr and 'readable local image' in rejected.stderr
    run(["--native-library",gui,"check",source('guiIcon(42);')],False)
    # Callback contracts must also hold when static typing is explicitly bypassed.
    # Invalid durations fail before Qt starts, including on a host without a
    # usable platform plugin. This must be a structured failure, not a Qt abort.
    for duration in ('-1', '2147483648'):
        invalid=source('fn callback(): void {} guiAfter('+duration+',callback);')
        rejected=subprocess.run([str(ky),'--native-library',str(gui),'run',str(invalid)],env={**env,'QT_QPA_PLATFORM':'kyna-invalid-platform'},capture_output=True,text=True,timeout=30)
        assert rejected.returncode==1 and 'KNATIVE1003' in rejected.stderr and 'timer duration is out of range' in rejected.stderr, rejected
    for code, expected in [
        ('fn wrong(value: int): void {} var callback: any = wrong; guiAfter(1,callback);', 'KNATIVE1003'),
        ('fn wrong(): int { return 1; } var callback: any = wrong; guiAfter(1,callback); guiRun();', 'KNATIVE1004'),
    ]:
        for imported in (False, True):
            (project/'dep.ky').write_text('export var marker=1;')
            source(('import { marker } from "./dep.ky";' if imported else '') + code)
            failure=run(["--native-library",gui,"run",project/"main.ky"],False)
            assert expected in failure.stderr, failure.stderr
    # A retained child keeps its native parent alive after language roots disappear.
    source('fn make() { var window=guiWindow("Ownership",320,240); var layout=guiColumn(window); return guiInput(layout,"retained child"); } var child=make(); collectGarbage(); console.log(guiRead(child));')
    assert 'retained child' in run(["--native-library",gui,"run",project/"main.ky"]).stdout
    source('geometryOrientation([0.0,0.0], [1.0,1.0], [2.0,2.0]); console.log(geometryIntersection([0.0,0.0],[1.0,0.0],[2.0,0.0],[3.0,0.0]));')
    assert "[]" in run(["--native-library",geometry,"run",project/"main.ky"]).stdout
    # Wrappers retain checked contracts across ordinary imports.
    (project/"ml.ky").write_text((root/"examples/native/packages/ml.ky").read_text())
    run(["--native-library",ml,"check",source('import { train } from "./ml.ky"; train(false, []);')],False)
    source('import { train, predict } from "./ml.ky"; var m = train([[1.0, 2.0, 3.0]], [3.0, 5.0, 7.0]); console.log(predict(m, [[4.0]]));')
    run(["--native-library",ml,"build","main.ky","--output",project/"explicit-app"],cwd=project)
    launcher=project/"explicit-app"/("run.cmd" if sys.platform=="win32" else "run")
    explicit=subprocess.run([str(launcher)],env=env,capture_output=True,text=True,timeout=30)
    assert explicit.returncode==0 and "[9]" in explicit.stdout,(explicit.stdout,explicit.stderr)
    host = "darwin" if sys.platform == "darwin" else "windows" if sys.platform == "win32" else "linux"
    import platform
    target=host+("-arm64" if platform.machine().lower() in ("arm64","aarch64") else "-x86_64")
    import tarfile
    portable = (ml.parent / "runtime-inventory.json").is_file()
    # Raw build DLLs can depend on sibling Armadillo/BLAS libraries. Install a
    # complete relocated ML archive on every platform, including the raw-build
    # CTest run; the relocated release run already supplies its closure.
    if not portable:
        sys.path.insert(0,str(root/'build_tools/packaging'))
        from portable_runtime import stage
        staged=project/'portable-ml';staged.mkdir()
        original=ml
        ml=staged/original.name;shutil.copy2(original,ml)
        stage(staged,[pathlib.Path(ml.name)],[original.parent])
        portable=True
    # Single-file installation remains covered by a self-contained authored
    # binding, rather than an ML adapter with undeclared external dependencies.
    legacy=project/'single-file-project';legacy.mkdir()
    fixture_sha=hashlib.sha256(authored_library.read_bytes()).hexdigest()
    (legacy/'kyna.toml').write_text(f'[project]\nentry = "main.ky"\n[dependencies.fixture.native]\nversion = "1.0.16"\ntarget = "{target}"\nabi = 2\npath = "{authored_library.as_posix()}"\nsha256 = "{fixture_sha}"\n')
    (legacy/'main.ky').write_text('var r=createTestResource(); console.log(readTestResource(r));')
    run(['install'],cwd=legacy);run(['install','--locked'],cwd=legacy)
    assert run(['run','main.ky'],cwd=legacy).stdout.strip()=='42'
    def add_runtime(tar):
        if portable:
            for file in sorted(ml.parent.rglob('*')):
                if file.is_file() and file != ml:
                    tar.add(file, arcname=file.relative_to(ml.parent).as_posix(), recursive=False)
    artifact_path = ml
    archive_settings = ''
    if portable:
        artifact_path = project / 'portable-ml.tar.gz'
        with tarfile.open(artifact_path, 'w:gz') as tar:
            tar.add(ml, arcname=ml.name)
            add_runtime(tar)
        archive_settings = f'archive = true\nlibrary = "{ml.name}"\n'
    checksum=hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    (project/"kyna.toml").write_text(f'[project]\nentry = "main.ky"\n[dependencies.ml.native]\nversion = "1.0.16"\ntarget = "{target}"\nabi = 2\npath = "{artifact_path.as_posix()}"\nsha256 = "{checksum}"\n'+archive_settings)
    run(["install"],cwd=project)
    run(["install","--locked"],cwd=project)
    # A second lock write failure restores the first lock, including removal.
    native_lock = project/".kyna/native.lock"
    before_native = native_lock.read_bytes()
    source_lock = project/"kyna.lock"
    before_source = source_lock.read_bytes()
    original_manifest = (project/"kyna.toml").read_text()
    source_lock.unlink(); source_lock.mkdir()
    (project/"kyna.toml").write_text('[project]\nentry = "main.ky"\n[dependencies]\n')
    run(["install"], False, cwd=project)
    assert native_lock.read_bytes() == before_native
    assert source_lock.is_dir()
    source_lock.rmdir(); source_lock.write_bytes(before_source)
    (project/"kyna.toml").write_text(original_manifest)
    # Removing the final native dependency must remove its stale registration.
    (project/"kyna.toml").write_text('[project]\nentry = "main.ky"\n[dependencies]\n')
    run(["install", "--locked"], False, cwd=project)
    assert native_lock.read_bytes() == before_native
    run(["install"], cwd=project)
    assert not native_lock.exists()
    (project/"kyna.toml").write_text(original_manifest)
    run(["install"], cwd=project)
    assert "[9]" in run(["run","main.ky"],cwd=project).stdout
    run(["build","main.ky","--output",project/"dist"],cwd=project)
    launcher=project/"dist"/("run.cmd" if sys.platform=="win32" else "run")
    app=subprocess.run([str(launcher)],env=env,capture_output=True,text=True,timeout=30)
    assert app.returncode==0 and "[9]" in app.stdout,(app.stdout,app.stderr)
    failure=run(["--diagnostic-format","json","build","main.ky","--output",project/"dist"],False,cwd=project)
    import json
    diagnostic=json.loads(failure.stderr)
    assert diagnostic["schema"] == "kyna.diagnostic/v1", diagnostic
    assert "KBUILD1001" in failure.stderr and "Choose a fresh" in failure.stderr
    artifact=next((project/".kyna/native").rglob(ml.name if portable else "*.native"));artifact.write_bytes(b"tampered")
    run(["run","main.ky"],False,cwd=project)
    # Native archives retain source wrappers and verify every installed file.
    import tarfile, io
    archive=project/"ml.tar.gz"
    with tarfile.open(archive,"w:gz") as tar:
        tar.add(ml,arcname="libkyna_ml.so")
        add_runtime(tar)
        data=(root/"examples/native/packages/ml.ky").read_bytes(); info=tarfile.TarInfo("ml.ky"); info.size=len(data);tar.addfile(info,io.BytesIO(data))
    sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    (project/"kyna.toml").write_text(f'[project]\nentry = "main.ky"\n[dependencies.ml.native]\nversion = "1.0.16"\ntarget = "{target}"\nabi = 2\npath = "ml.tar.gz"\nsha256 = "{sha}"\narchive = true\nlibrary = "libkyna_ml.so"\n')
    (project/"ml.ky").unlink();source('import { train, predict } from "ml"; var model=train([[1.0,2.0,3.0]],[3.0,5.0,7.0]); console.log(predict(model,[[4.0]]));')
    run(["install"],cwd=project);run(["install","--locked"],cwd=project)
    assert "[9]" in run(["run","main.ky"],cwd=project).stdout
    run(["build","main.ky","--output",project/"archive-app"],cwd=project)
    launcher=project/"archive-app"/("run.cmd" if sys.platform=="win32" else "run")
    app=subprocess.run([str(launcher)],env=env,capture_output=True,text=True,timeout=30)
    assert app.returncode==0 and "[9]" in app.stdout,(app.stdout,app.stderr)
    wrapper=next((project/".kyna/native").glob("*/ml.ky"));wrapper.write_text("tampered")
    run(["run","main.ky"],False,cwd=project)
    # Listing validation must reject raw path spellings before Windows path
    # normalization. The preceding real installs also cover Windows tar CRLF.
    import re
    for unsafe in ('../escape','C:/escape','folder\\..\\escape','control\rname'):
        with tarfile.open(archive,'w:gz') as tar:
            info=tarfile.TarInfo(unsafe);tar.addfile(info)
        text=re.sub(r'sha256 = "[a-f0-9]+"','sha256 = "'+hashlib.sha256(archive.read_bytes()).hexdigest()+'"',(project/'kyna.toml').read_text())
        (project/'kyna.toml').write_text(text)
        rejected=run(['install'],False,cwd=project)
        assert 'unsafe native archive path' in rejected.stderr,rejected.stderr
    # A verified archive is still rejected if it contains a link.
    with tarfile.open(archive,"w:gz") as tar:
        info=tarfile.TarInfo("unsafe");info.type=tarfile.SYMTYPE;info.linkname="/tmp";tar.addfile(info)
    text=re.sub(r'sha256 = "[a-f0-9]+"','sha256 = "'+hashlib.sha256(archive.read_bytes()).hexdigest()+'"',(project/'kyna.toml').read_text());(project/"kyna.toml").write_text(text)
    run(["install"],False,cwd=project)
    # Reject expanded size before writing an oversized member to staging.
    class Zeroes:
        def read(self, count): return bytes(count)
    with tarfile.open(archive,"w:gz",compresslevel=1) as tar:
        info=tarfile.TarInfo("oversized");info.size=513*1024*1024;tar.addfile(info,Zeroes())
    text=(project/"kyna.toml").read_text()
    import re
    text=re.sub(r'sha256 = "[a-f0-9]+"', 'sha256 = "'+hashlib.sha256(archive.read_bytes()).hexdigest()+'"', text)
    (project/"kyna.toml").write_text(text)
    rejected=run(["install"],False,cwd=project)
    assert "512 MiB" in rejected.stderr, rejected.stderr

print("Optional native package and application smoke tests passed")
