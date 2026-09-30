# ==========================================================================
# VeriQuest Worker — Hardened Sandbox for Icarus Verilog
#
# Hardening parameters per Master Build Prompt Section 2:
# - Runtime isolation: network_disabled (--network=none)
# - Privilege restriction: security_opt no-new-privileges
# - Capability restriction: cap_drop=["ALL"]
# - Filesystem: read_only root filesystem with single writable tmpfs workspace
# - Non-root user: 1000:1000
# - Resource limits: 1 CPU, 256MB memory, 64 PIDs, 5s timeout
# - Max output bounded: 64 KB
# - Ephemeral workspace: fresh temp directory per job, unconditionally deleted
# ==========================================================================

import logging
import os
import re
import tempfile
import shutil
import threading
from pathlib import Path
from typing import Optional
from .verdict_protocol import prepare_testbench, validate_student_source

logger = logging.getLogger("veriquest.sandbox")


class DockerSandbox:
    """
    Manages ephemeral hardened Docker containers for HDL compilation and simulation.
    Fails closed when Docker is unavailable. No synthetic grading fallback.
    """

    def __init__(
        self,
        image: Optional[str] = None,
        timeout_ms: int = 5000,
        memory_mb: int = 256,
        cpu_limit: str = "1.0",
        pids_limit: int = 64,
    ):
        self.image = image or os.environ.get("EXECUTION_IMAGE", "veriquest-icarus:latest")
        self.timeout_s = timeout_ms / 1000.0
        self.memory_mb = memory_mb
        self.cpu_limit = float(cpu_limit)
        self.pids_limit = pids_limit
        self.client = None

        try:
            import docker
            self.client = docker.from_env()
            # Test connectivity
            self.client.ping()
        except Exception as e:
            logger.info(f"Docker daemon not reachable ({e}). Evaluation is unavailable.")
            self.client = None

    def execute(self, student_code: str, testbench: str) -> dict:
        """
        Execute student Verilog code against a trusted testbench in an isolated container.

        Returns a dict with:
        - exit_code: int
        - stdout: str
        - stderr: str
        - timed_out: bool
        """
        try:
            trusted = prepare_testbench(testbench or '')
        except ValueError as error:
            return dict(configuration_error=True, stdout='', stderr=str(error), exit_code=-1)
        try:
            if not isinstance(student_code, str) or not student_code.strip():
                raise ValueError('SOURCE_EMPTY')
            validate_student_source(student_code, trusted['reserved'])
        except ValueError as error:
            return dict(source_error=True, stdout='', stderr=str(error), exit_code=-1)
        if self.client:
            return self._execute_docker(student_code, trusted)
        else:
            return self._execute_fallback(student_code, testbench)

    def _execute_docker(self, student_code: str, trusted: dict) -> dict:
        workspace = None
        container = None

        try:
            # 1. Create fresh, unique workspace directory
            workspace = tempfile.mkdtemp(prefix="vq_exec_")
            workspace_path = Path(workspace)

            # 2. Write files
            (workspace_path / "submission.v").write_text(student_code, encoding="utf-8")
            (workspace_path / "testbench.v").write_text(trusted['code'], encoding="utf-8")

            # 3. Fixed execution shell script
            exec_script = """#!/bin/sh
cd /workspace || exit 1

# Compile with Icarus Verilog
iverilog -g2012 -o sim.vvp testbench.v submission.v 2>&1
compile_code=$?
printf '%s' "$compile_code" > compile.exit
[ "$compile_code" -eq 0 ] || exit "$compile_code"
timeout 5 vvp sim.vvp 2>&1
run_code=$?
printf '%s' "$run_code" > simulation.exit
exit "$run_code"
"""
            (workspace_path / "run.sh").write_text(exec_script, encoding="utf-8")

            # 4. Run hardened container per Section 2
            container = self.client.containers.run(
                image=self.image,
                command=["sh", "/workspace/run.sh"],
                volumes={
                    workspace: {"bind": "/workspace", "mode": "rw"},
                },
                tmpfs={"/tmp": "rw,noexec,nosuid,size=64m"},
                network_disabled=True,
                mem_limit=f"{self.memory_mb}m",
                nano_cpus=int(self.cpu_limit * 1e9),
                pids_limit=self.pids_limit,
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],
                read_only=True,
                user="1000:1000",
                remove=False,
                detach=True,
            )

            # 5. Stream and bound combined UTF-8 bytes before retaining them.
            # A watchdog kills a blocked/overlong container even if attach stalls.
            max_output = int(os.environ.get('MAX_OUTPUT_BYTES', '65536'))
            if not 0 < max_output <= 65536:
                max_output = 65536
            streams = [bytearray(), bytearray()]
            total_bytes = 0
            truncated = False
            output_complete = True
            timed_out_event = threading.Event()
            def expire():
                timed_out_event.set()
                try:
                    container.kill()
                except Exception:
                    pass
            watchdog = threading.Timer(self.timeout_s, expire)
            watchdog.daemon = True
            watchdog.start()
            try:
                stream = container.attach(stream=True, demux=True, logs=True)
                for pair in stream:
                    if not isinstance(pair, tuple) or len(pair) != 2:
                        raise ValueError('Malformed Docker log frame')
                    for index, chunk in enumerate(pair):
                        if chunk is None:
                            continue
                        if not isinstance(chunk, bytes):
                            raise ValueError('Malformed Docker log chunk')
                        remaining = max_output - total_bytes
                        if len(chunk) > remaining:
                            streams[index].extend(chunk[:remaining])
                            total_bytes = max_output
                            truncated = True
                            output_complete = False
                            try:
                                container.kill()
                            except Exception:
                                pass
                            break
                        streams[index].extend(chunk)
                        total_bytes += len(chunk)
                    if truncated:
                        break
                if hasattr(stream, 'close'):
                    stream.close()
                result = container.wait(timeout=self.timeout_s)
                exit_code = result.get("StatusCode", -1)
                timed_out = timed_out_event.is_set()
            except Exception:
                output_complete = False
                try:
                    container.kill()
                except Exception:
                    pass
                exit_code = -1
                timed_out = timed_out_event.is_set()
            finally:
                watchdog.cancel()
            if timed_out:
                output_complete = False
            stdout = streams[0].decode('utf-8', errors='replace')
            stderr = streams[1].decode('utf-8', errors='replace')

            # Shell-owned files, not stdout. Student file access and hierarchy are
            # rejected before compilation; absent/malformed stage evidence fails closed.
            def stage_exit(name):
                try:
                    value = (workspace_path / name).read_text(encoding='ascii')
                    return int(value) if re.fullmatch(r'[0-9]{1,3}', value) else None
                except (OSError, UnicodeError):
                    return None

            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": timed_out,
                "compile_exit_code": stage_exit('compile.exit'),
                "simulation_exit_code": stage_exit('simulation.exit'),
                "verdict_nonce": trusted['nonce'],
                "expected_total": trusted['total'],
                "output_truncated": truncated,
                "output_complete": output_complete,
            }

        except Exception as e:
            logger.exception(f"Docker sandbox execution failed: {e}")
            return self._execute_fallback(student_code, trusted['code'])

        finally:
            # Unconditional cleanup of container
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

            # Unconditional cleanup of workspace
            if workspace and os.path.exists(workspace):
                try:
                    shutil.rmtree(workspace)
                except Exception:
                    pass

    def _execute_fallback(self, student_code: str, testbench: str) -> dict:
        """
        Neutralized legacy fallback.
        Per Master Architecture Specification Sections 10, 24, 37:
        Simulation must never fake ACCEPTED, perform regex-based grading, or fabricate
        test results. When Docker execution fails or is unreachable, the system must
        strictly report SYSTEM_ERROR so infrastructure failure is never hidden or falsified.
        """
        logger.error("Docker execution unavailable. Refusing fake evaluation or regex grading.")
        return {
            "exit_code": 1,
            "stdout": (
                "--- SUMMARY ---\n"
                "TOTAL: 0\n"
                "PASSED: 0\n"
                "FAILED: 0\n"
                "VERIQUEST_STATUS: SYSTEM_ERROR\n"
                "Error: Isolated Docker HDL sandbox execution is unavailable on this host."
            ),
            "stderr": "Docker sandbox daemon unavailable or execution failed",
            "timed_out": False,
        }
