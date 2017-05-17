#! /usr/bin/env python

import sys, time, subprocess

run = lambda cmd: subprocess.call(cmd)
counter = 0
while True:
    run("check_sessions.py")
    run(["process_emails.py", "--smtp=mailserver"])
    if counter % 10 == 0:
        run("execute_turn.py")
    counter += 1
    time.sleep(60)
    
