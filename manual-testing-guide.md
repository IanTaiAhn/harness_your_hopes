# Manual testing guide — Projects 1–5

Layer-by-layer breakdown of all five rungs, plus concrete manual steps for surfacing each project's known shortcomings by hand — not just "run it and see if it works," but specific pokes at the exact places each design cuts corners. Projects 1–3 were written after Project 3 landed, as a reference before starting Project 4. Projects 4–5 were added after the capstone landed, once both had code but were still waiting on a real Ollama run.

## How `measurements/results.md` actually gets filled in

Nothing in this repo writes to a project's `results.md` automatically — it's a hand-authored template (literal `___` blanks, empty table cells, `<!-- Fill in after ... -->` comments) and stays that way until someone transcribes real evidence into it. The evidence itself comes from two sources, and both are needed:

1. **Automated raw logs, produced just by running the code.** `log_token_usage()` (`common/ollama_client.py`) writes per-turn token counts to `measurements/tokens.jsonl` inside every `generate()`/`run_session()` call; `run_suite.py` writes each task's `{self_reported, verified, attempt}` to `measurements/runs.jsonl` as it runs and prints a summary; `audit.py` (Project 3) writes every allowed/refused action to `audit.jsonl`. These happen for free just from doing a normal run — no extra step required.
2. **Manual pokes, from this guide.** Kill points (`taskkill`), hand-edited `progress.json`, `mklink /J` junctions, ablation flags (`-NoFeatureList`/`-NoGitLog`/`-NoCommit`) — the specific "break it" maneuvers listed per project above can't be automated away; they're deliberate interventions a person (or an agent driving the terminal) performs, watching what happens each time.

The actual step that's still manual either way: reading the `.jsonl` output plus what you observed during the break-it pass, and writing the summarized numbers/pass-fail/takeaway into that project's `results.md` by hand. `results.md` is the artifact — it's meant to be the human-readable distillate of the raw logs and observed behavior, not something the harness produces on its own.

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

---

## Project 4 — Generator–evaluator loop

**Layers**
- `generator.py` — `generate()`: a Project-1-style write_file/read_file loop, ends when the model replies with plain text starting `TASK_COMPLETE`/`TASK_FAILED`. The self-report is returned but trusted nowhere downstream.
- `evaluator.py` — `evaluate_deterministic()` runs `pytest <test_path> -v` as a subprocess (60s timeout) and pulls the failing test name + assertion out of the output for feedback; `evaluate_judge()` is a second-model-call fallback for criteria that can't be expressed as a test.
- `run_suite.py` — `run_one()`: generate → evaluate → on failure, feed `result.feedback` back into `generate(feedback=...)`, bounded by `MAX_RETRIES = 2`. Logs every attempt to `measurements/runs.jsonl`.
- `tasks/` — 20 task specs + fixed pytest checks; `conftest.py`'s `collect_ignore_glob` keeps them out of a repo-wide `pytest` run.

**Manual tests, and what each one exposes**

1. **Baseline single task** — `uv run python -c "from generator import generate; print(generate('write tasks/solutions/x.py with def f(): return 1'))"`, then run `evaluate_deterministic` against a matching hand-written test. Just to see the two halves agree before trying to make them disagree.
2. **Provoke the headline gap directly** — hand-run one of the deliberately under-specified tasks (`task_09_word_frequency`, `task_17_is_anagram`, `task_19_rotate_list`, `task_20_title_case`) through `run_suite.run_one()`. Watch the 4B plausibly reply `TASK_COMPLETE` while `evaluate_deterministic` fails on the one detail (case sensitivity, rotation direction, small-word capitalization) the test pins down and the prompt doesn't. **Exposes:** the self-reported-vs-verified gap this whole project exists to measure, on a single task instead of waiting for all 20.
3. **Check the feedback is actually specific** — after the rejection above, print `result.feedback` and confirm it's the failing test name + `assert`/`E` line (`evaluator.py:21-36`), not a bare "failed". Then compare a retry given that real feedback against one you've manually degraded to the string `"failed"`. **Exposes:** whether specific feedback measurably helps the 4B fix its own mistake, or whether it just burns a retry either way — this is the thing `MAX_RETRIES = 2` is betting on.
4. **Exhaust the retries** — pick or write a task hard enough that a 4B genuinely can't pass it in 2 attempts (nested logic, an off-by-one in indexing). Confirm `run_one()` returns `verified: False` while `self_reported` may still be `True` from the last attempt. **Exposes:** the two fields in `runs.jsonl` really can disagree in either direction, not just the "claimed done, wasn't" direction task 2 exercises.
5. **Kill mid-suite** — `Ctrl+C` partway through `run_suite.main()`'s 20-task loop, then rerun. **Exposes:** there's no resume here — `runs.jsonl` has partial data on disk, but `main()` always starts at `task_specs[0]`, so a rerun redoes every already-passed task from scratch. This is a real regression against Project 2's whole point, just one layer up the ladder.
6. **The judge path is written but unwired** — `grep -n evaluate_judge run_suite.py` comes back empty; only `evaluate_deterministic` is ever called by the suite driver. Exercise it directly instead: `uv run python -c "from evaluator import evaluate_judge; print(evaluate_judge('explain what this function does in one sentence', '<some summary text>'))"`. **Exposes:** the model-as-judge fallback exists and is unit-tested, but the actual 20-task measurement never reaches it — worth deciding on purpose (all 20 tasks are meant to be deterministic-checkable) rather than discovering it as a silent gap after the real run.
7. **Break the evaluator's own timeout** — point `evaluate_deterministic` at a test file whose reference solution would need to busy-loop (or just `time.sleep(70)` inside a throwaway test), confirm it comes back `passed=False, feedback="evaluator timed out after 60s"` rather than hanging the whole suite. **Exposes:** a runaway generated solution (e.g. an infinite loop in a `reverse_words` attempt) fails safely instead of stalling `run_suite.py` on task N forever.
8. **A broken test is a silent bug in the measurement** — temporarily edit one `test_task_NN.py` to assert something the spec never asked for, run that task through `run_one()`, and watch it exhaust retries against a generator that was actually right. **Exposes:** `evaluate_deterministic` is only as trustworthy as the fixed test it runs — there's no independent check that the 20 ground-truth tests themselves are correct beyond the throwaway reference-solution pass mentioned in the README, which isn't committed and so can't be re-verified from this repo alone.

---

## Project 5 — Capstone (initializer / coding-agent)

**Layers**
- `contract.py` — single source of truth: `FEATURES` (the ordered ladder), `TEST_FILES` (feature → ground-truth test), `CLI_CONTRACT` (the spec text). Both other files import from here so the spec the model sees and the spec the tests check can't drift apart.
- `initializer.py` — runs once: writes `target/feature_list.json` (all `false`), `target/CONTRACT.md`, copies `tests_template/` → `target/tests/`, copies `init.ps1`, `git init` + `core.autocrlf true` + first commit.
- `coding_agent.py` — runs fresh every invocation: `load_feature_list()` / `read_git_log()` first, `pick_target_feature()` picks exactly one, a Project-1-style tool loop scoped to `target/` via `_resolve_in_target()`, `write_file()` refuses `feature_list.json` and anything under `tests/`, `restore_tests_from_git()` before every evaluation as a second independent guard, `evaluate_deterministic()` (not the model's `TASK_COMPLETE`) as the only commit trigger, retries bounded by `MAX_RETRIES = 2`.
- `run_loop.ps1` — drives N genuinely-fresh `coding_agent.py` processes; `-NoFeatureList`/`-NoGitLog`/`-NoCommit` flip the `ABLATE_*` env vars `coding_agent.py` reads.

**Manual tests, and what each one exposes**

1. **Baseline initializer** — `uv run python initializer.py`, then inspect `target/`: `feature_list.json` all `false`, `CONTRACT.md` matches `contract.py`'s `CLI_CONTRACT`, `tests/` has all 5 `test_0N_*.py` files, `git log` in `target/` shows exactly one commit. Rerun the initializer without deleting `target/` first and confirm it refuses (`SystemExit(... "already initialized" ...)`) instead of clobbering.
2. **One process, one feature, one commit** — from `projects/05-capstone/`, `uv run python coding_agent.py` once. Confirm the console shows `mode=single target=add-item`, and afterward `target/feature_list.json` has exactly `add-item: true`, `git log` in `target/` has exactly one new commit, and `target/tests/` is byte-identical to `tests_template/` (i.e. the model didn't touch it even if it tried). **Exposes:** the "one feature per fresh process" contract actually holding, not just being described in the prompt.
3. **The self-report is genuinely decorative** — instrument (or just eyeball via the printed `self_reported=` line) a session where the model says `TASK_COMPLETE` but `evaluate_deterministic` rejects it. Confirm `feature_list.json` is *not* updated and no commit happens — the retry loop fires on `verified`, never on `self_reported` (`coding_agent.py:299-308`). **Exposes:** the exact failure mode Project 4 was built to catch, now load-bearing inside the capstone instead of just measured in isolation.
4. **Attack the model's own bookkeeping** — craft a prompt (or, faster, call `write_file("feature_list.json", "{}")` / `write_file("tests/test_01_add_item.py", "...")` directly against `coding_agent.py`'s `DISPATCH`) and confirm both raise `PermissionError` before touching disk. Then delete/bypass the guard in `write_file()` locally and confirm `restore_tests_from_git()` still undoes a hypothetical edit to `tests/` after the session ends. **Exposes:** the two independent layers described in the README actually being independent — the second one has to hold even if the first has a bug.
5. **Catalog mode (the feature-list ablation)** — `.\run_loop.ps1 -NoFeatureList -Iterations 1` against a freshly re-initialized `target/`. Confirm the console shows `mode=catalog target=(agent must infer)`, and check `build_system_prompt`'s "no feature-tracking file" branch is really what got sent (add a temporary `print(system_prompt)` if needed). **Exposes:** whether the 4B can actually infer progress from `git log` + reading `todo.py` alone, or whether it re-implements an already-done command, wasting the session — this is the measurement the README's "Measure" section is asking for.
6. **Git-log ablation** — `.\run_loop.ps1 -NoGitLog -Iterations 1` on a `target/` with at least one prior commit already in place (run one normal baseline session first, then re-run with this flag rather than starting from zero). Confirm the prompt shows `(git log withheld for this ablation run)` and watch whether the model, now flying with only `feature_list.json` and no commit history, redoes work already reflected in `todo.py` on disk. **Exposes:** how much of "don't repeat work" is actually coming from the git-log read vs. the feature list.
7. **Commit ablation, then a real restart** — `.\run_loop.ps1 -NoCommit -Iterations 2`. Confirm the console shows `verified [...] but commit is ablated` and `git log` in `target/` gains zero commits across both iterations, yet `feature_list.json` *does* get updated (that write isn't gated by the ablation). Then run a third iteration with commits re-enabled and check whether the agent's tool-loop context (which has zero memory of prior sessions either way) causes it to re-derive or conflict with the uncommitted working-tree changes already sitting in `todo.py`. **Exposes:** the gap between "the harness knows the feature passed" and "that fact survived to the next process" — the two are cleanly separable here in a way they aren't in the baseline.
8. **Kill mid-session** — `taskkill /F /PID <pid>` on `coding_agent.py` partway through a tool-calling turn (mirror Project 2's test 2), then rerun. **Exposes:** unlike Project 2, there's no `progress.json` here at all — the recovery signal is entirely `git log` (nothing committed yet, so nothing lost) plus whatever partial, uncommitted edit was left in `target/todo.py` by the killed process. Check whether that half-written file confuses the next fresh session's `read_file` step before it writes over it.
9. **Feed it a stale `tests_template/`** — deliberately break one `tests_template/test_0N_*.py` (e.g. assert the wrong print string against `contract.py`'s actual spec text) before running `initializer.py`, then run the loop against that feature. **Exposes:** same class of gap as Project 4 test 8 — a wrong ground-truth test silently caps the whole capstone at "never passes this feature," and nothing in the harness would tell you the test, not the model, is the problem.
