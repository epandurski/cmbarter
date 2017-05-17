#! /usr/bin/env python

import sys, time, subprocess

def run(cmd):
    result = subprocess.call(cmd)
    sys.stdout.flush()
    return result
    
counter = 0
while True:
    run("check_sessions.py")
    run(["process_emails.py", "--smtp=mailserver"])
    if counter % 10 == 0:
        run(["pypy", "/bin/execute_turn.py"])
    counter += 1
    time.sleep(60)
