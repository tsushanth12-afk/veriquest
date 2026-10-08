#!/bin/sh
# Image-owned runner; no token in argv/environment; read-only inputs.
set -u
umask 077
record_resources() {
    # Kernel evidence, read with shell builtins even when no PID can be forked.
    while read -r key value; do
        [ "$key" != max ] || printf '%s' "$value" > /workspace/output/pids.events
    done < /sys/fs/cgroup/pids.events
    while read -r key value; do
        [ "$key" != oom_kill ] || printf '%s' "$value" > /workspace/output/memory.events
    done < /sys/fs/cgroup/memory.events
}
cd /workspace/output || exit 1
iverilog -g2012 -o sim.vvp /workspace/input/testbench.v /workspace/input/submission.v 2>&1
compile_code=$?
printf '%s' "$compile_code" > compile.exit
record_resources
[ "$compile_code" -eq 0 ] || exit "$compile_code"
vvp sim.vvp 2>&1
run_code=$?
printf '%s' "$run_code" > simulation.exit
record_resources
exit "$run_code"
