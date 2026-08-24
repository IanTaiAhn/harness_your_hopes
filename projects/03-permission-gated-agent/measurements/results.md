# Project 3 — Measurement Log

| Attack | Python allowlist only | With sandbox underneath |
|---|---|---|
| `..` traversal | | |
| drive-relative paths (`C:foo`) | | |
| UNC paths (`\\?\C:\...`) | | |
| directory junctions (`mklink /J`) | | |
| case-insensitivity tricks | | |
| 8.3 short names (`PROGRA~1`) | | |

(✓ blocked / ✗ escaped)

## Takeaway

<!-- How many escaped Python-only? How many escaped with the sandbox underneath (should be 0)? -->
