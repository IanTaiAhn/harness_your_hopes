# Drives N genuinely-fresh coding_agent.py processes, simulating real
# context-window resets between sessions. Run from this directory.
#
# Usage: .\run_loop.ps1 -Iterations 10

param(
    [int]$Iterations = 10
)

for ($i = 1; $i -le $Iterations; $i++) {
    Write-Host "=== Iteration $i ==="
    & uv run python coding_agent.py
}
