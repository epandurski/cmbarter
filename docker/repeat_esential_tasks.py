#! /usr/bin/env python
#
# This file is needed by "Dockerfile-tasks".

import os, sys, time, subprocess

def run(cmd):
    result = subprocess.call(cmd)
    sys.stdout.flush()
    return result

smtp_encryption = os.environ.get('SMTP_ENCRYPTION', 'none').strip().lower()
process_emails = ["process_emails.py"]
if smtp_encryption == "none":
    pass
elif smtp_encryption == "ssl":
    process_emails.append("--ssl")
elif smtp_encryption == "starttls":
    process_emails.append("--starttls")
else:
    print("ERROR: invalid SMTP_ENCRYPTION value.")
    sys.exit(1)

minor_digits = max(0, int(os.environ.get('MINOR_DIGITS', '0')))
execute_turn = ["pypy", "/usr/local/bin/execute_turn.py", "--level=%i" % minor_digits]

counter = 0
while True:
    time.sleep(60)
    run(process_emails)
    if counter % 10 == 0:
        run(execute_turn)
    counter += 1
