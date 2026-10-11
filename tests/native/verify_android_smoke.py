#!/usr/bin/env python3
"""Require completion of the selected application; ignore other emulator processes."""
import re,subprocess,time

def application_lines(log, pids):
    lines=[]
    for line in log.splitlines():
        fields=line.split()
        if len(fields)<5 or not fields[2].isdigit():continue
        if fields[2] in pids or 'libkyna_android_shell_' in line:lines.append(line)
    return '\n'.join(lines)

def main():
    transitioned=False;pids=set()
    for _ in range(60):
        log=subprocess.check_output(['adb','logcat','-d'],text=True)
        current=subprocess.run(['adb','shell','pidof','org.kyna.application'],capture_output=True,text=True)
        pids.update(current.stdout.split())
        for line in log.splitlines():
            if 'KYNA_ANDROID_STARTED' in line:
                fields=line.split()
                if len(fields)>2 and fields[2].isdigit():pids.add(fields[2])
        application=application_lines(log,pids)
        if not transitioned and 'KYNA_ANDROID_STARTED' in application:
            time.sleep(2)
            subprocess.run(['adb','shell','input','keyevent','KEYCODE_HOME'],check=True)
            time.sleep(1)
            subprocess.run(['adb','shell','monkey','-p','org.kyna.application','1'],check=True,stdout=subprocess.DEVNULL)
            transitioned=True
        if 'KANDROID100' in application or 'Fatal signal' in application or 'FATAL EXCEPTION' in application:
            raise SystemExit('Android application failed:\n'+application[-8000:])
        if transitioned and 'KYNA_ANDROID_SMOKE_OK' in application:
            print('Android application callback/shutdown smoke passed');return
        time.sleep(1)
    raise SystemExit('Android application did not produce its completion marker')
if __name__=='__main__':main()
