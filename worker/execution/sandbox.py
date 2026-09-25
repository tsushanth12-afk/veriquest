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
from pathlib import Path
from typing import Optional

logger = logging.getLogger("veriquest.sandbox")


class DockerSandbox:
    """
    Manages ephemeral hardened Docker containers for HDL compilation and simulation.
    Includes a deterministic HDL verification fallback when Docker daemon is not active.
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
            logger.info(f"Docker daemon not reachable ({e}). Using deterministic HDL execution engine.")
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
        # If Docker is available, run containerized
        if self.client:
            return self._execute_docker(student_code, testbench)
        else:
            return self._execute_fallback(student_code, testbench)

    def _execute_docker(self, student_code: str, testbench: str) -> dict:
        workspace = None
        container = None

        try:
            # 1. Create fresh, unique workspace directory
            workspace = tempfile.mkdtemp(prefix="vq_exec_")
            workspace_path = Path(workspace)

            # 2. Write files
            (workspace_path / "submission.v").write_text(student_code, encoding="utf-8")
            (workspace_path / "testbench.v").write_text(testbench, encoding="utf-8")

            # 3. Fixed execution shell script
            exec_script = """#!/bin/sh
set -e
cd /workspace

# Compile with Icarus Verilog
iverilog -g2012 -o sim.vvp testbench.v submission.v 2>&1

# Run simulation if compiled
if [ -f sim.vvp ]; then
    timeout 5 vvp sim.vvp 2>&1
else
    echo "VERIQUEST_STATUS: COMPILATION_ERROR"
    echo "Compilation failed: sim.vvp not generated"
    exit 1
fi
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

            # 5. Wait with timeout
            try:
                result = container.wait(timeout=self.timeout_s)
                exit_code = result.get("StatusCode", -1)
                timed_out = False
            except Exception:
                try:
                    container.kill()
                except Exception:
                    pass
                exit_code = -1
                timed_out = True

            # 6. Capture stdout & stderr bounded to MAX_OUTPUT_BYTES
            stdout = ""
            stderr = ""
            try:
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            except Exception:
                pass

            max_output = int(os.environ.get("MAX_OUTPUT_BYTES", 65536))
            stdout = stdout[:max_output]
            stderr = stderr[:max_output]

            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": timed_out,
            }

        except Exception as e:
            logger.exception(f"Docker sandbox execution failed: {e}")
            # Fall back to deterministic evaluator if Docker failed during run
            return self._execute_fallback(student_code, testbench)

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
