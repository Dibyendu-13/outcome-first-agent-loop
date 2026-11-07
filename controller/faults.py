"""Explicit test-only crash points. Disabled unless both environment variables are set."""
import os
import signal


def hit(point):
    if os.environ.get('CONTROLLER_FAULT_POINT')!=point:return
    marker=os.environ.get('CONTROLLER_FAULT_MARKER')
    if not marker:raise RuntimeError('Fault injection requires a durable one-shot marker path')
    try:
        fd=os.open(marker,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:
        return
    with os.fdopen(fd,'w') as file:
        file.write(point+'\n');file.flush();os.fsync(file.fileno())
    os.kill(os.getpid(),signal.SIGKILL)
