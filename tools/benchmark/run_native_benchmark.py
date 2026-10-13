#!/usr/bin/env python3
"""Compare verified geometry and GUI workloads with equivalent direct C++ calls."""
import argparse
import hashlib
import json
import os
import pathlib
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time


def sample(command, expected, repetitions, environment):
    timings = []
    memory = []
    for index in range(repetitions + 2):
        started = time.perf_counter_ns()
        with tempfile.TemporaryDirectory(prefix="kyna-native-rss-") as directory:
            rss_file = pathlib.Path(directory) / "rss.txt"
            supported = pathlib.Path("/usr/bin/time").is_file() and sys.platform in {"darwin", "linux"}
            measured = (["/usr/bin/time", "-l" if sys.platform == "darwin" else "-v",
                         "-o", str(rss_file), *command] if supported else command)
            result = subprocess.run(measured, capture_output=True, text=True,
                                    env=environment, timeout=30)
            peak = None
            if supported:
                pattern = (r"(\d+)\s+maximum resident set size" if sys.platform == "darwin"
                           else r"Maximum resident set size \(kbytes\):\s*(\d+)")
                match = re.search(pattern, rss_file.read_text())
                if match:
                    peak = int(match.group(1)) * (1 if sys.platform == "darwin" else 1024)
        elapsed = (time.perf_counter_ns() - started) / 1e9
        if result.returncode or result.stdout.strip() != expected:
            raise RuntimeError(f"Incorrect workload: {command}: {result.stdout} {result.stderr}")
        if index >= 2:
            timings.append(elapsed)
            memory.append(peak)
    return {"wall_seconds": timings, "median_seconds": statistics.median(timings),
            "peak_rss_bytes": memory}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=pathlib.Path, required=True)
    parser.add_argument("--ky", type=pathlib.Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--baseline", type=pathlib.Path)
    args = parser.parse_args()
    if args.repetitions < 3:
        parser.error("use at least three measured repetitions")
    root = pathlib.Path(__file__).resolve().parents[2]
    build, ky = args.build.resolve(), args.ky.resolve()
    environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    report = {"schema": "kyna.native-workloads/v1", "informational": True,
              "platform": platform.platform(), "warmups": 2,
              "repetitions": args.repetitions, "workloads": {}}
    for name, expected in [("geometry", "4000"), ("gui", "1000")]:
        source = root / "tools/benchmark/programs/native" / (name + ".ky")
        cpp_source = source.with_suffix(".cpp")
        candidates = list((build / "native").glob(f"*kyna_{name}.*"))
        candidates += list((build / "native/Release").glob(f"*kyna_{name}.*"))
        library = next((p for p in candidates if p.suffix in {".so", ".dll", ".dylib"}), None)
        if library is None:
            raise RuntimeError(f"Build the {name} adapter first")
        suffix = ".exe" if os.name == "nt" else ""
        cpp = build / (f"kyna_{name}_benchmark" + suffix)
        if not cpp.exists():
            cpp = build / "Release" / cpp.name
        cpp_measurement = sample([str(cpp)], expected, args.repetitions, environment)
        native_measurement = sample([str(ky), "--native-library", str(library),
                                     "run", str(source)], expected, args.repetitions, environment)
        fingerprint = hashlib.sha256(source.read_bytes() + cpp_source.read_bytes()).hexdigest()
        report["workloads"][name] = {
            "correct": True, "expected_output": expected, "iterations": 1000,
            "source_sha256": fingerprint, "library_sha256": hashlib.sha256(library.read_bytes()).hexdigest(),
            "cpp": cpp_measurement, "kyna": native_measurement,
            "cpp_binary_bytes": cpp.stat().st_size, "native_artifact_bytes": library.stat().st_size,
            "cli_bytes": ky.stat().st_size,
            "ratio": native_measurement["median_seconds"] / cpp_measurement["median_seconds"]}
    report["measurement_scope"] = "Process startup, source checking and execution; not isolated binding overhead."
    if args.baseline:
        baseline = json.loads(args.baseline.read_text())
        if baseline.get("schema") != report["schema"] or baseline.get("platform") != report["platform"]:
            raise RuntimeError("Baseline schema and platform must match")
        for name, workload in report["workloads"].items():
            before = baseline["workloads"][name]
            if before["source_sha256"] != workload["source_sha256"] or not before["correct"]:
                raise RuntimeError(f"Baseline workload changed: {name}")
            workload["baseline_change_percent"] = {
                engine: (workload[engine]["median_seconds"] / before[engine]["median_seconds"] - 1) * 100
                for engine in ["cpp", "kyna"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
