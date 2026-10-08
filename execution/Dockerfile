# ==========================================================================
# VeriQuest Execution — Minimal Icarus Verilog Sandbox Image
# ==========================================================================

FROM debian:bookworm-slim

# Install only iverilog — minimal attack surface
RUN apt-get update && \
    apt-get install -y --no-install-recommends iverilog && \
    rm -rf /var/lib/apt/lists/* && \
    # Create non-root execution user
    groupadd -g 1000 veriquest && \
    useradd -u 1000 -g 1000 -s /bin/false -d /workspace veriquest

WORKDIR /workspace

COPY run.sh /usr/local/bin/vq-run
RUN sed -i 's/\r$//' /usr/local/bin/vq-run && chmod 0555 /usr/local/bin/vq-run

# Run as non-root
USER 1000:1000

# Default command (overridden per execution)
CMD ["echo", "VeriQuest execution image ready"]
