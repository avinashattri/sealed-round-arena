MAIN GOAL (never lose this): a working, demo-ready prototype of "Sealed-Round Arena" (Hack in the Hills Track 04, Bayora), built by ONE person (me) with you building. Passing the acceptance test with every claim honestly labelled is the only thing that matters.

# AGENTS.md
Read this file, docs/STATUS.md and the current docs/phases/PHASE_n.md at the start of EVERY conversation. Memory lives in repo files, not chat. Keep this file under 10,000 characters (Antigravity rule files are reportedly capped at 12,000).

## Rules
1. One task at a time. Task IDs are P<phase>.T<n>.
2. Before first use of any tool, flag, version, URL or setting, check --help, official docs, or run a tiny test. Log it in docs/COMMANDS.md (command | how verified | date). Anything tagged [VERIFY FIRST] must be verified before use.
3. Run the task's DONE command and show its output before saying done. Never edit a test, expected output or DONE command to make it pass. If the DONE command is wrong, tell me.
4. Never stub or fake a result. Simulations and stand-ins are labelled SIMULATION / STAND-IN in code, output and docs/status.yml.
5. Commit after each task: type(scope): summary, <=72 chars (types feat fix docs test chore ci). Update docs/STATUS.md. Tag at checkpoints (v0.1 P1, v0.2 P2, v0.3 P3, v0.4 P4, v1.0-rc1 P6, v1.0 P7).
6. Never change anything fixed in docs/SPEC.md without asking me. Propose, then wait.
7. Never commit secrets, models, datasets, evidence/ (replay/ is the exception after I review it) or harmful text. Fake canaries only (BYR- plus 16 hex).
8. After 2 failed fixes on one error: stop and report the error, what you tried, and options.
9. Stay lean. Short replies, no essays, no repeated plans. Patch edits, not whole-file rewrites. View line ranges. Don't re-read big files without need. If quota runs low, stop at a task boundary and tell me.
10. Privileged or destructive steps (sudo, iptables, gVisor install, rm -rf, docker system prune, docker volume rm, anything outside the repo): never run them yourself. Put them in scripts/priv/ or a make target, show me the script, then NEED YOU. Only exception: `make clean` after I approve it once. It is scoped to the sra-naive and sra-hardened compose projects plus repo-local secrets/ and shared/, and never prunes.
11. No docker.sock mount into any container. No published ports in hardened. No --privileged, no host network or PID. Secrets are files under /run/secrets, never env vars in hardened.
12. Windows/WSL2: repo lives at ~/sealed-round-arena (ext4). Use the ACCESS mode (W/L/F) found in step 0. LF line endings only. Docker Engine inside Ubuntu, not Docker Desktop.
13. Honesty: never write "secure", write "held against these N probes". Every claim in README/CLAIMS.md needs a proof command.

## Run protocol
- End each phase with "CHECKPOINT n:" plus proof output plus a one-line go/no-go. Then wait for me to reply "continue".
- Need something only I can do: print one line "NEED YOU: <one exact action>. Reply done." and wait.
- Order: thin slice (P0.T8) first, then core-lite, then extras in ranked order (SPEC section 1). When a phase runs over 25% of its solo hours, apply the next drop-list item, say which, and continue.
- Never cut: leak lab, naive-vs-hardened comparison, loop with failure tracing, signed audit, threat model (and commit-reveal, which the acceptance test needs).

## Conventions
Python 3.12, venv .venv, PY=.venv/bin/python, FastAPI, pydantic v2, httpx, PyNaCl, pytest, ruff, Streamlit. Makefile uses `.RECIPEPREFIX := >`. Tests: `.venv/bin/pytest <path> -q`. Paths, ports, names: docs/SPEC.md only; never invent new ones.
