# Copied into target/ by initializer.py. todo.py only needs the Python
# stdlib, and target/ is nested inside this repo's own directory tree,
# so `uv run` here resolves upward to the same root .venv Project 1-4
# already use -- there's no separate venv to create. This script is a
# sanity check today, and the place a future feature's real dependency
# would get installed.
Write-Host "Checking uv + python are on PATH..."
uv run python --version
if ($LASTEXITCODE -ne 0) {
    Write-Error "uv run python failed -- is uv installed and on PATH?"
    exit 1
}
Write-Host "OK -- todo.py has no extra dependencies to install."
