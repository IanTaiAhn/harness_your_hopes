# Real enforcement boundary for Project 3: only the target folder is
# bind-mounted at runtime, so anything outside it is simply not present
# to the process, regardless of what the Python allowlist does or misses.
#
# Build:  docker build -t harness-p3 .
# Run:    docker run --rm -v D:\messy-folder:/workspace:rw harness-p3
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# TODO: agent.py should read its allowlist root from an env var (e.g.
# WORKSPACE_ROOT=/workspace) so the same code runs identically in and
# out of the container — only the bind mount changes what's reachable.
CMD ["python", "agent.py"]
