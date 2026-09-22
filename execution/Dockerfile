# ==========================================================================
# VeriQuest Execution — Minimal Icarus Verilog Sandbox Image
# ==========================================================================

FROM debian:bookworm-slim

# Install only iverilog — minimal attack surface
RUN apt-get update && \
    apt-get install -y --no-install-recommends iverilog && \
    rm -rf /var/lib/apt/lists/* && \
    # Create non-root execution user
    useradd -r -s /bin/false -d /workspace veriquest

WORKDIR /workspace

# Run as non-root
USER veriquest

# Default command (overridden per execution)
CMD ["echo", "VeriQuest execution image ready"]
