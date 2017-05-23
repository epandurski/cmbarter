#! /usr/bin/env python
#
# This file is needed by "Dockerfile-tasks".

import sys, time, subprocess

def run(cmd):
    result = subprocess.call(cmd)
    sys.stdout.flush()
    return result
    
counter = 0
while True:
    time.sleep(60)
    run("process_emails.py")
    if counter % 10 == 0:
        run(["pypy", "/usr/local/bin/execute_turn.py"])
    counter += 1
