#! /usr/bin/env python

import sys, time, subprocess

def run(cmd):
    result = subprocess.call(cmd)
    sys.stdout.flush()
    return result
    
counter = 0
while True:
    run("check_sessions.py")
    run(["process_emails.py", "--smtp=mail"])
    if counter % 10 == 0:
        run(["pypy", "/usr/local/bin/execute_turn.py"])
    counter += 1
    time.sleep(60)
