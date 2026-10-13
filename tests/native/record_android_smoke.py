#!/usr/bin/env python3
"""Record the actual lifecycle smoke on an explicitly selected disposable emulator."""
import argparse,os,pathlib,subprocess,sys,time,uuid
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--serial',required=True)
parser.add_argument('--output',required=True,type=pathlib.Path)
args=parser.parse_args()
if not args.serial.startswith('emulator-'):parser.error('recording is restricted to a test emulator')
env=dict(os.environ,ANDROID_SERIAL=args.serial)
def adb(*arguments):return subprocess.run(['adb',*arguments],env=env,check=True,capture_output=True,text=True).stdout
adb('logcat','-c')
remote='/data/local/tmp/kyna-smoke-'+uuid.uuid4().hex+'.mp4'
recording=subprocess.Popen(['adb','shell','screenrecord','--time-limit','20',remote],env=env)
try:
    time.sleep(1)
    adb('shell','monkey','-p','org.kyna.application','1')
    subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('verify_android_smoke.py'))],env=env,check=True)
    recording.wait(timeout=30)
    if recording.returncode:raise RuntimeError('Android screen recorder failed')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    adb('pull',remote,str(args.output))
    log=adb('logcat','-d')
    if 'KYNA_ANDROID_STARTED' not in log or 'KYNA_ANDROID_SMOKE_OK' not in log:raise RuntimeError('Application proof markers missing')
    args.output.with_suffix('.log').write_text('\n'.join(line for line in log.splitlines() if 'KYNA_ANDROID_' in line)+'\n')
    print('Recorded verified ARM64 Android application:',args.output)
except Exception:
    args.output.with_suffix('.failure.log').write_text(adb('logcat','-d'))
    raise
finally:
    if recording.poll() is None:recording.terminate();recording.wait(timeout=5)
