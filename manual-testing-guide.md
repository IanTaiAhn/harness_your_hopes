# Manual testing guide — Projects 1–3

Layer-by-layer breakdown of the first three rungs, plus concrete manual steps for surfacing each project's known shortcomings by hand — not just "run it and see if it works," but specific pokes at the exact places each design cuts corners. Written after Project 3 landed, as a reference before starting Project 4.

---

## Project 1 — Bare-metal tool loop

**Layers**
- `common/ollama_client.py` — transport: one HTTP POST per turn, token accounting.
- `tools.py` — the hands: `read_file`/`write_file`/`run_command` + `TOOLS_SCHEMA`/`DISPATCH`. No policy, no persistence — whatever the model asks for, it gets.
- `agent.py` — the loop: `messages` list grows every turn (full transcript, nothing summarized), `_normalize_tool_calls` handles structured vs. fallback-JSON tool calls, `MAX_JSON_RETRIES`/`MAX_TURNS` are the only guards that exist.

**Manual tests, and what each one exposes**

1. **Happy path baseline** — `uv run python agent.py "read <file>, count the lines, write the count to a new file"`. Watch the per-turn prompt-token count grow. This is just to have a working reference before you start breaking things.
2. **Reproduce the documented off-by-one** — point it at a file with a tricky trailing-newline situation (a file ending in `\n` vs. one that doesn't) and ask it to count lines without giving it a counting tool. Watch whether it reaches for `run_command` (`(Get-Content file).Count`) or just eyeballs the raw text in its own context. **Exposes:** no dedicated tool for exact operations the model can't reliably eyeball.
3. **Force the malformed-JSON path for real** — give it a deliberately confusing multi-part instruction ("read file A, then depending on what it says either write to B or C, and also tell me a joke") and watch the console for `malformed tool-call JSON`. **Exposes:** the model dropping out of structured tool-calling isn't rare-but-theoretical — it's provokable with ambiguity.
4. **Exhaust `MAX_TURNS`** — give it an open-ended task with no natural stopping point ("keep reading files in this folder until you find something interesting"). Watch it hit turn 15 and fail loudly instead of hanging. **Exposes:** there's no completion criterion beyond "the model decided to stop" — the turn cap is the only backstop.
5. **Blow past `num_ctx`** — point it at a file with several thousand lines. With `num_ctx=8192` and zero compaction logic, watch either an error or the model start "forgetting" the beginning of the file it read. **Exposes:** Project 1 has *no* context management at all — this is the gap Project 2.5 exists to fill, and it's worth seeing fail before you build the fix.
6. **Unix-command confusion** — ask it to "list the files in this folder." Watch whether it tries `ls` before falling back to `Get-ChildItem`. **Exposes:** the documented, still-open checkbox in the README — the model reaching for Unix habits on Windows.
7. **Kill it mid-task** — `taskkill /F /PID <pid>` partway through a 3-step task, then rerun the exact same command. **Exposes:** zero persistence — it starts completely over, no memory the previous attempt ever happened. This is the motivating gap for Project 2.
8. **No permission gate at all** — ask it to `"read C:\Windows\System32\drivers\etc\hosts and write its contents to out.txt"`. It will just do it — no allowlist, no confirmation, no audit trail. **Exposes:** the gap Project 3 exists to close. Worth seeing this succeed unchecked before you compare it against Project 3 refusing the same thing.

---

## Project 2 — Survive a restart

**Layers**
- `state.py` — the persistence: `Progress` dataclass, `save_atomic()` (temp file + `os.replace`, retried against `PermissionError`).
- `agent.py` — `build_messages()` rebuilds the prompt **from the `Progress` summary**, never from a stored transcript; `seed_plan()` hardcodes the plan for the default task; the loop advances one planned step per turn and saves before the next model call.

**Manual tests, and what each one exposes**

1. **Baseline resume** — run it, let step 1 finish (`file1.txt` appears), then `cat progress.json` to see exactly what got persisted, then kill and rerun to confirm it picks up at step 2 without redoing step 1.
2. **The five required kill points** — `taskkill /F /PID <pid>` at: (a) while it's waiting on `chat()`, (b) right as a tool call is executing, (c) right after a tool call prints but before the "Resuming" line on the next run, (d) mid-way through the 4th step (which needs 3 `read_file` calls before the summary write), (e) after all 4 steps finish but before the process exits. After each, inspect `progress.json` by hand before rerunning.
3. **The real shortcoming — one tool call is trusted as "the whole step," unconditionally.** Look at `agent.py:169-196`: after *any* tool call(s) in a turn, the code unconditionally does `progress.steps_completed.append(current_step); progress.steps_remaining.pop(0)` — there's no check that the tool call the model made actually matches what the step asked for. **Manually provoke it:** get the model to call `read_file` instead of `write_file` on the "create file1.txt" step (e.g. by phrasing the task so the model second-guesses itself and checks something first) — watch `progress.json` mark that step "completed" even though `file1.txt` was never created. That's a real, non-hypothetical bug you can trigger, not just a theoretical gap.
4. **Silent result loss in multi-call turns** — same code region: `step_output = output` is reassigned on every iteration of the `for call in tool_calls` loop, so if the model batches two tool calls in one response, only the *last* one's result survives into `progress.last_tool_result` — the first call's outcome (even an error) is thrown away. Provoke it by getting the model to make 2 calls in one turn and check `progress.json`'s `last_tool_result` only reflects the second.
5. **Trust the file blindly on resume** — hand-edit `progress.json` after a kill: mark a step "completed" that was never actually done (e.g. remove `file2.txt` from disk but leave it in `steps_completed`). Rerun. **Exposes:** resume has no verification step — it trusts whatever's on disk completely. This is exactly the self-reported-success problem Project 4's generator/evaluator split exists to catch, just one layer earlier.
6. **Race two processes** — start `agent.py` twice against the same `progress.json` in quick succession. **Exposes:** no locking; both may read the same `steps_remaining[0]`, both do the same step, both `save_atomic()` — last writer wins, work gets duplicated silently.

---

## Project 3 — Permission-gated file agent

**Layers**
- `policy.py` — `Allowlist.check()`: `Path.resolve()` + `is_relative_to()` against the roots. This is the Python-level gate.
- `audit.py` — append-only JSONL, every attempt, allowed or not.
- `tools.py` — `list_dir`/`move_file`/`delete_file` added to Project 1's `read_file`/`write_file`. **`run_command` is absent on purpose.**
- `agent.py` — `gated_call()` wraps every dispatch: checks the allowlist for *every* path key on the tool (both `src` and `dest` for `move_file`), refines `write_file` → `overwrite` only if the target exists, gates `delete`/`overwrite` behind `_confirm()`, audits regardless of outcome.
- `Dockerfile` — the actual enforcement boundary; everything above it is "your own code policing itself."

**Manual tests, and what each one exposes**

1. **Baseline, no container** — set `WORKSPACE_ROOT` to a real messy folder (PowerShell: `$env:WORKSPACE_ROOT="C:\path\to\folder"`), run `"organize the files in the workspace by extension"`, then `cat measurements/audit.jsonl` to see the full trail.
2. **Prompt-level escape attempt** — directly ask it to `"read C:\Windows\win.ini and copy its contents into the workspace"`. Watch the console show `error: ... outside allowlist roots ...` fed back to the model, and confirm `audit.jsonl` shows `"allowed": false`. **Exposes:** the system prompt telling the model "nothing outside {root} exists" is persuasion, not enforcement — this test proves the *allowlist*, not the prompt, is what actually stops it (try rephrasing until the model actually attempts it, rather than just refusing on its own — a refusal from the *model* proves nothing about the harness).
3. **Confirmation gate, both branches** — run it interactively (real terminal) with a task that needs `delete_file`; you should see a real `Allow delete on ...? [y/N]` prompt. Answer `n` once, confirm the file survives; rerun answering `y`, confirm it's actually gone.
4. **Non-interactive fail-closed** — run it with stdin redirected (`uv run python agent.py "delete gone.txt" < NUL` on Windows, or under Task Scheduler) and confirm it refuses automatically instead of hanging on `input()` forever.
5. **The real attack list, tested directly against `policy.py`** — this is the one that matters most, and it's better done as a quick Python REPL check than by hoping the model happens to try it:
   ```python
   from policy import Allowlist
   a = Allowlist([r"C:\Users\you\workspace"])
   a.check(r"C:\Users\you\workspace\..\..\Windows\System32")   # `..` traversal
   a.check(r"C:foo")                                            # drive-relative
   a.check(r"\\?\C:\Windows\System32")                          # UNC
   a.check(r"C:\Users\you\workspace\PROGRA~1")                  # 8.3 short name, if applicable
   ```
   Plus a real junction: `mklink /J C:\Users\you\workspace\escape C:\Windows\System32`, then `a.check(r"C:\Users\you\workspace\escape\cmd.exe")`. **Exposes:** whether `is_relative_to()` genuinely holds up against each Windows-specific trick — this is exactly what the Linux environment this project was authored in couldn't verify (only `..` and a symlink, the Linux analog of the junction, were tested there), so it's the one place a manual pass on real Windows adds information the authoring environment literally couldn't.
6. **Compare against the real boundary** — `docker build` the image, bind-mount only a subfolder, `docker exec` into the running container and try `cat /etc/passwd` or `ls /`. **Exposes:** the qualitative difference the whole project is about — Python-only is a check that can have a bug; the container makes the rest of the filesystem *not exist* for that process, full stop.
7. **Content-based exfiltration (out of scope, worth knowing)** — ask it to read a file inside the workspace and write its content into a new filename that encodes something sensitive. The allowlist has no opinion here — it gates *where*, never *what*. Not a bug, but worth being clear-eyed that this project's threat model is path traversal, not data handling.
