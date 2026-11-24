# CI Workflow Walkthrough

A guided tour of the continuous-integration (CI) setup in this repository.
Read this alongside `.github/workflows/ci.yml`.

This repo started as a companion to the "GitHub Actions Zero to Hero" video.
Its original workflow (`first-actions.yml`) was a good first step, but it had
a few beginner-only choices. This walkthrough explains the replacement, why
each piece is there, and how to experiment with it safely.

---

## 1. What changed

| File | Before | After |
| --- | --- | --- |
| `.github/workflows/first-actions.yml` | Only workflow; push-only; Python 3.8/3.9; `checkout@v3`, `setup-python@v2` | Renamed to `ci.yml` and rewritten (see below) |
| `src/addition.py` | Held both `add()` and a test function | Production code only |
| `src/test_addition.py` | Didn't exist | Real test module with 5 parametrized cases |
| `requirements-dev.txt` | Didn't exist | Pinned test dependency: `pytest==9.2.0` |
| `.gitignore` | Didn't exist | Ignores caches, bytecode, and virtualenvs |
| `walkthrough.md` | Didn't exist | This document |

The old file was renamed with `git mv` rather than deleted and recreated, so
git keeps its history.

---

## 2. The workflow, section by section

Open `.github/workflows/ci.yml` and follow along.

### 2.1 Name and triggers

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

- `name` is what appears in the Actions tab and on PR checks.
- `on:` defines **events**. Two events are wired up:
  - `push` to `main` — verifies the state of the main branch after a merge.
  - `pull_request` targeting `main` — this is the important one. It runs the
    checks on the *proposed* code, before it is merged. GitHub shows the result
    as a check on the PR, and you can require it to pass before merging.
- The tutorial version used `on: [push]`, so it never checked PRs.

### 2.2 Permissions

```yaml
permissions:
  contents: read
```

GitHub gives each workflow a token. By default that token can have fairly
broad write access. Declaring `contents: read` applies the principle of least
privilege: if the workflow is ever compromised (for example by a malicious
dependency), it still cannot push code or change repository settings. This
workflow only reads the repo, so `read` is all it needs.

### 2.3 Concurrency

```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

- `group` defines which runs are "the same". Here, all runs for one workflow
  on one ref (a branch or PR) share a group.
- `cancel-in-progress: true` means if you push a second commit while the first
  run is still going, the first is cancelled. That saves runner minutes and
  gives you feedback on the newest code faster.

### 2.4 Job and runner

```yaml
jobs:
  test:
    name: pytest (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
```

- A workflow contains **jobs**; jobs run in parallel by default and each gets
  a fresh virtual machine. This workflow has one job, `test`.
- `runs-on: ubuntu-latest` is a GitHub-hosted Linux runner. No self-hosted
  runner needed (the video also covers configuring one — that's a separate,
  more advanced topic).
- `name:` uses the matrix value so each job is labelled clearly in the UI.

### 2.5 Matrix strategy

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ["3.11", "3.12", "3.13", "3.14"]
```

- `matrix` clones the job once per value, so you get four independent jobs.
  That tells you whether your code works on every supported Python version,
  not just the one on your laptop.
- `fail-fast: false` keeps all four running even if one fails. With the default
  (`true`), GitHub cancels the remaining jobs at the first failure, hiding
  useful information.
- The original matrix was Python 3.8 and 3.9. Both are **end-of-life** (3.9
  stopped receiving support in October 2025; 3.8 earlier). The versions above
  are the actively supported ones at the time of writing. Note that Python
  versions are quoted as strings: unquoted `3.10` would become the number
  `3.1` after YAML parsing — a classic gotcha.

### 2.6 Steps

```yaml
steps:
  - name: Check out the repository
    uses: actions/checkout@v7

  - name: Set up Python ${{ matrix.python-version }}
    uses: actions/setup-python@v7
    with:
      python-version: ${{ matrix.python-version }}
      cache: pip
      cache-dependency-path: requirements-dev.txt

  - name: Install dependencies
    run: |
      python -m pip install --upgrade pip
      python -m pip install -r requirements-dev.txt

  - name: Run the test suite
    run: python -m pytest -v --cov=src --cov-report=term-missing
```

- `uses:` calls a reusable action; `run:` executes shell commands.
- `checkout@v7` fetches your repository into the runner. `@v7` is a **major
  version tag**, which gets bug fixes automatically but won't introduce
  breaking changes. The old workflow used `@v3` (very stale).
- `setup-python@v7` installs the matrix's Python version and adds it to `PATH`.
- `cache: pip` plus `cache-dependency-path` caches downloaded wheels between
  runs, keyed on `requirements-dev.txt`. Change that file and the cache key
  changes, so you never silently reuse stale dependencies. The tutorial had
  no caching.
- Dependencies come from `requirements-dev.txt` instead of an unpinned
  `pip install pytest`. Pinning means CI and your laptop run the same test
  runner version — no "works on my machine" surprises.
- `python -m pytest -v` discovers and runs the tests, with verbose output
  showing each case. Using `python -m pytest` (rather than bare `pytest`)
  guarantees you use the interpreter that was just set up.
- `--cov=src --cov-report=term-missing` adds a coverage table to the job log,
  showing which lines in `src/` were exercised and which were not. The plugin
  comes from the pinned `pytest-cov==7.1.0` in `requirements-dev.txt`.
- The old workflow did `cd src` then named the file explicitly. A properly
  named `test_*.py` file is auto-discovered, so no `cd` or filename is needed.

---

## 3. The tests

`src/addition.py` now only contains the function under test:

```python
def add(a: int | float, b: int | float) -> int | float:
    """Return the sum of two numbers."""
    return a + b
```

`src/test_addition.py` contains the tests:

```python
@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(1, 2, 3), (1, -1, 0), (0, 0, 0), (-5, -7, -12), (2.5, 0.5, 3.0)],
)
def test_add(a, b, expected):
    assert add(a, b) == expected
```

Two ideas worth learning here:

1. **Separate tests from production code.** Originally `test_add()` lived in
   `addition.py`. That works, but keeping tests in a `test_*.py` file lets
   pytest find them automatically and keeps the shipped module clean.
2. **Parametrize.** One test function covers five input combinations. pytest
   reports each as a separate case (`test_add[1-2-3]`, etc.), so you get broad
   coverage with very little code. Adding a new case is a one-line change.

---

## 4. Run it locally

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

Expected output:

```
collected 5 items

src/test_addition.py::test_add[1-2-3] PASSED
...
5 passed in 0.01s
```

The same command runs in CI. If it passes locally, it should pass in the
workflow (modulo Python-version differences, which is exactly what the matrix
checks).

---

## 5. Watch it run in GitHub

1. Commit and push the changes:

   ```bash
   git add .
   git commit -m "Add solid CI workflow with tests and walkthrough"
   git push origin main
   ```

2. Open <https://github.com/man1328/GitHub-Actions-Zero-to-Hero/actions>.
   You'll see a run named `CI` with four jobs — one per Python version.

3. Click a run, then a job, to expand each step and read its log. The
   `Run the test suite` step shows the five passing cases and the coverage
   table for `src/`.

4. To see the PR behaviour, create a branch, make a change, push it, and open
   a pull request against `main`. The `CI` check appears on the PR page.

---

## 6. Make it fail on purpose (the best way to learn)

1. In `src/test_addition.py`, change `(1, 2, 3)` to `(1, 2, 4)`.
2. Commit and push.
3. In the Actions tab you'll see **all four** matrix jobs fail (thanks to
   `fail-fast: false`), and the test output will show `assert 3 == 4`.
4. Revert the change, commit, push, and watch them go green again.

This teaches the whole feedback loop: code change → automated check → clear
failure → fix → green build.

---

## 7. Gotchas you may hit

- **`yamllint` warns about `on:` being "truthy".** That's a YAML 1.1 quirk;
  GitHub's parser treats `on` as a key correctly. `actionlint` — the linter
  that actually understands Actions — accepts the file cleanly.
- **pytest doesn't find a test.** It only collects files named `test_*.py` or
  `*_test.py` (and functions named `test_*`). That's why the test lives in
  `src/test_addition.py` now.
- **`from addition import add` works even though the test is in `src/`.**
  pytest inserts the test file's directory into `sys.path` during collection.
  If you later add an `__init__.py` to `src/`, switch to
  `from src.addition import add`.
- **Don't pin to a moving tag like `@latest`.** Use a major tag (`@v7`) or a
  full commit SHA. A major tag is the normal, readable choice; a SHA is the
  most secure choice for high-risk repos.
- **Python 3.10 unquoted becomes `3.1`** in YAML. Always quote version strings.

---

## 8. Where to go next

Natural extensions, roughly in order of usefulness:

1. **Coverage** — add `pytest-cov==7.1.0` to `requirements-dev.txt`, then
   **reinstall the dependencies** (editing the file alone does not install
   anything):

   ```bash
   python -m pip install -r requirements-dev.txt
   python -m pytest --cov=src --cov-report=term-missing
   ```

   Expected tail of the output:

   ```
   Name                   Stmts   Miss  Cover
   ------------------------------------------
   src/addition.py            2      0   100%
   src/test_addition.py       5      0   100%
   ------------------------------------------
   TOTAL                      7      0   100%
   ```

   If you see `error: unrecognized arguments: --cov=src --cov-report=term-missing`,
   the plugin simply isn't installed in the interpreter you're using. Re-run
   the `pip install -r requirements-dev.txt` command above inside your
   activated venv. `.coverage` and `htmlcov/` are already in `.gitignore`.
2. **Linting** — add a `lint` job using [ruff](https://docs.astral.sh/ruff/)
   (`ruff check .` and `ruff format --check .`) so style problems are caught
   alongside test failures.
3. **Branch protection** — in repository settings, require the `CI` check to
   pass before merging to `main`.
4. **Dependabot** — enable dependency updates so pinned versions don't rot.
5. **Self-hosted runner** — the last part of the video shows how to host your
   own runner; useful when you need GPUs, private network access, or specific
   hardware for real model training jobs.
6. **Deployment** — the `examples/` folder already has Kubernetes and Docker
   Swarm workflows to study when you're ready to go beyond CI.

---

## 9. Version choices (verified 2026-11-24)

| Item | Value | Source |
| --- | --- | --- |
| `actions/checkout` | `v7` (latest release `v7.0.1`) | GitHub Releases API |
| `actions/setup-python` | `v7` (latest release `v7.1.0`) | GitHub Releases API |
| `pytest` | `9.2.0` | PyPI JSON API |
| `pytest-cov` (optional, section 8) | `7.1.0` | PyPI JSON API |
| Python matrix | `3.11`–`3.14` | python.org active releases |

Re-check these when you come back to the repo months later; the pattern stays
the same even when the numbers change.
