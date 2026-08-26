# Real enforcement boundary for Project 3: only the target folder is
# bind-mounted at runtime, so anything outside it is simply not present
# to the process, regardless of what the Python allowlist does or misses.
#
# Build (from repo root, so pyproject.toml and common/ are in context):
#   docker build -t harness-p3 -f projects/03-permission-gated-agent/Dockerfile .
# Run:
#   docker run --rm -v D:\messy-folder:/workspace:rw harness-p3
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project

COPY . .

# agent.py reads its allowlist root from WORKSPACE_ROOT, so the same code
# runs identically in and out of the container -- only the bind mount
# changes what's actually reachable at that path.
ENV WORKSPACE_ROOT=/workspace
RUN mkdir -p /workspace

CMD ["uv", "run", "python", "projects/03-permission-gated-agent/agent.py"]
