# Drives N genuinely-fresh coding_agent.py processes, simulating real
# context-window resets between sessions. Run from this directory.
#
# Usage: .\run_loop.ps1 -Iterations 10
# Ablation runs (see README.md "Measure"), one flag per component:
#   .\run_loop.ps1 -NoFeatureList
#   .\run_loop.ps1 -NoGitLog
#   .\run_loop.ps1 -NoCommit
# Delete target/ and rerun initializer.py between configurations so each
# ablation starts from the same clean baseline, not on top of the last one.

param(
    [int]$Iterations = 10,
    [switch]$NoFeatureList,
    [switch]$NoGitLog,
    [switch]$NoCommit
)

if ($NoFeatureList) { $env:ABLATE_NO_FEATURE_LIST = "1" }
if ($NoGitLog) { $env:ABLATE_NO_GITLOG = "1" }
if ($NoCommit) { $env:ABLATE_NO_COMMIT = "1" }

for ($i = 1; $i -le $Iterations; $i++) {
    Write-Host "=== Iteration $i ==="
    & uv run python coding_agent.py
}

Remove-Item Env:\ABLATE_NO_FEATURE_LIST -ErrorAction SilentlyContinue
Remove-Item Env:\ABLATE_NO_GITLOG -ErrorAction SilentlyContinue
Remove-Item Env:\ABLATE_NO_COMMIT -ErrorAction SilentlyContinue
