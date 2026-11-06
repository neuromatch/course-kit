"""Run generated notebooks end to end (`nma-kit run-notebooks`), for the scheduled course-nightly workflow.

The instructor notebook of each page is the one that runs: it has the solutions filled in, so it has no
intentional errors. A failure on a `runtime: colab` page (a GPU or ML-library notebook) is only flagged
for a manual check, because the scheduled job runs on CPU. This module needs only nbclient and nbformat
(the Colab image has both), and no course settings except in `list_targets`.
"""

import json
import math
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

PASSED, FAILED, TIMEOUT, NEEDS_CHECK = "passed", "failed", "timeout", "needs-check"
BREAKING = (FAILED, TIMEOUT)
DEFAULT_TIMEOUT = 1200  # seconds for one whole notebook
CELL_TIMEOUT = 300  # seconds for one cell: a stalled cell costs this much, not the whole notebook budget
RETRIES = 1  # a notebook that timed out is run once more in a fresh kernel (timeouts can be stalls, not slowness)
KILL_GRACE = 60  # seconds past the timeout before the notebook's process is killed


@dataclass
class Result:
    """The outcome of one notebook."""

    notebook: str
    runtime: str
    state: str
    where: str = ""    # "<notebook>, cell N" of the first problem
    message: str = ""  # the last line of the error
    seconds: float = 0.0
    attempts: int = 1
    timed_out: bool = False  # also true for a `needs-check` that was a timeout: only timeouts are run again

# Runs in the kernel before the notebook's own cells. In a Colab-like stack (ipywidgets 7, ipykernel 6.17) a cell
# with `widgets.interact` waits out its whole timeout when no front end is attached, so the scheduled run swaps
# `interact` for a stand-in that calls the function once with the controls' initial values, which is what a
# reader sees first. It tests the function, not ipywidgets.
HEADLESS_INTERACT = '''\
def _nma_install_headless_interact():
    try:
        import ipywidgets
    except ImportError:
        return
    import inspect
    from numbers import Number

    def initial(control):
        if hasattr(control, "value") and not isinstance(control, (str, bytes)):  # a widget
            return control.value
        if isinstance(control, tuple) and len(control) in (2, 3) and all(isinstance(v, Number) for v in control):
            low, high = control[0], control[1]
            whole = all(isinstance(v, int) for v in control)
            step = control[2] if len(control) == 3 else (1 if whole else (high - low) / 100)
            value = low + round((low + (high - low) / 2 - low) / step) * step
            return int(value) if whole else value
        if isinstance(control, (list, tuple)):
            first = control[0]
            return first[1] if isinstance(first, tuple) and len(first) == 2 else first
        if isinstance(control, dict):
            return next(iter(control.values()))
        return control

    def interact(__f=None, **controls):
        def run(f):
            parameters = inspect.signature(f).parameters
            values = {name: initial(control) for name, control in controls.items() if name in parameters}
            for name, parameter in parameters.items():
                if name not in values and parameter.default is not parameter.empty:
                    values[name] = initial(parameter.default)
            f(**values)
            return f
        return run(__f) if __f is not None else run

    for module in (ipywidgets, ipywidgets.widgets):
        module.interact = interact
        module.interactive = lambda f, **controls: interact(f, **controls)


_nma_install_headless_interact()
del _nma_install_headless_interact
'''


class _OutOfTime(Exception):
    pass


def classify(state: str, runtime: str) -> str:
    """A failure or timeout of a `runtime: colab` notebook is flagged for a manual check, not failed."""
    if state in BREAKING and runtime == "colab":
        return NEEDS_CHECK
    return state


def has_failures(results: list[Result]) -> bool:
    """True when a notebook failed or timed out (`needs-check` does not count)."""
    return any(r.state in BREAKING for r in results)


def list_targets(settings, runtime: str = "") -> list[dict]:
    """The instructor notebooks `nma-kit notebooks` generated, with each page's runtime.
    Pages without a kernelspec have no notebook, so they are not listed."""
    # Imported here: the run job in the Colab image installs the kit without its dependencies.
    from nma_kit.cells import runtime_of
    from nma_kit.config import NOTEBOOKS_DIR, page_location
    from nma_kit.convert import has_kernelspec

    targets = []
    for _, directory in settings.content_roots:
        for page in sorted(Path(directory).rglob("*.md")):
            if not has_kernelspec(page):
                continue
            location = page_location(settings, page)
            notebook = f"{NOTEBOOKS_DIR}/{location.notebook_dir}/instructor/{location.stem}.ipynb"
            page_runtime = runtime_of(page.read_text(encoding="utf-8"))
            if runtime and page_runtime != runtime:
                continue
            targets.append({"notebook": notebook, "runtime": page_runtime})
    return targets


def shard(targets: list[dict], count: int) -> list[list[dict]]:
    """Split the targets into at most `count` groups, dealt out in turn so each group has a similar mix.
    One CI job runs one group, so the Colab image is pulled once per group, not once per notebook."""
    if not targets:
        return []
    count = max(1, min(count, len(targets)))
    return [targets[i::count] for i in range(count)]


def _title(cell) -> str:
    """The first line of a cell, plus its first line of code when that one is a comment (`# @title ...`,
    `# @markdown ...`), to name the cell in logs and reports."""
    lines = [line.strip() for line in "".join(cell.source).splitlines() if line.strip()]
    if not lines:
        return "(empty)"
    code = next((line for line in lines if not line.startswith("#")), "")
    title = f"{lines[0]} | {code}" if lines[0].startswith("#") and code else lines[0]
    return title[:100]


def _execute(path: Path, runtime: str, timeout: float, cell_timeout: float = CELL_TIMEOUT,
             progress: Path | None = None, headless_widgets: bool = True) -> Result:
    """Execute one notebook in this process (a fresh kernel, in the notebook's own folder), within `timeout`
    seconds in total and `cell_timeout` seconds for each cell. `progress` is rewritten at each cell start, so a supervisor can name a cell that hangs."""
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError, CellTimeoutError, DeadKernelError

    path = Path(path)
    name = path.as_posix()
    from nma_kit.solutions import is_exercise_cell

    nb = nbformat.read(path, as_version=4)
    # The instructor notebook still has each exercise cell (it raises on purpose) right before the
    # `# Solution` cell that defines the same names: run without the exercise cells, like render-scrolly.
    # `numbers` keeps the cells' numbers in the notebook, for the error report.
    numbers = [i for i, cell in enumerate(nb.cells, 1) if not is_exercise_cell(cell)]
    nb.cells = [cell for cell in nb.cells if not is_exercise_cell(cell)]
    if headless_widgets and any("interact" in "".join(cell.source) for cell in nb.cells if cell.cell_type == "code"):
        nb.cells.insert(0, nbformat.v4.new_code_cell(HEADLESS_INTERACT))
        numbers.insert(0, 0)  # not a cell of the notebook
    start = time.monotonic()
    current = {"index": 0, "title": ""}  # the notebook number and first line of the cell that is running
    stall = {"timer": None, "dumped": False}
    os.environ.setdefault("PYTHONFAULTHANDLER", "1")  # the kernel inherits it: SIGABRT then prints every thread's stack

    def dump_stacks():
        """A cell is about to time out: make the kernel print where it is stuck (to the job log), then give up on it."""
        pid = getattr(getattr(getattr(client, "km", None), "provisioner", None), "pid", None)
        if pid:
            print(f"  cell {current['index']} is stuck; stack of the kernel:", flush=True)
            stall["dumped"] = True
            os.kill(pid, signal.SIGABRT)

    def on_cell_start(cell, cell_index):
        if stall["timer"]:
            stall["timer"].cancel()
        current["index"] = numbers[cell_index]
        current["title"] = _title(cell)
        if cell.cell_type == "code" and current["index"]:
            print(f"  cell {current['index']}: {current['title']}", flush=True)
        if progress:
            progress.write_text(json.dumps(current), encoding="utf-8")
        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise _OutOfTime
        client.timeout = max(1, math.ceil(min(remaining, cell_timeout)))
        if cell.cell_type == "code":
            stall["timer"] = threading.Timer(max(1, client.timeout - 3), dump_stacks)
            stall["timer"].daemon = True
            stall["timer"].start()

    client = NotebookClient(nb, timeout=math.ceil(min(timeout, cell_timeout)), kernel_name="python3",
                            resources={"metadata": {"path": str(path.resolve().parent)}})
    client.on_cell_start = on_cell_start

    def result(state, where="", message=""):
        return Result(name, runtime, classify(state, runtime), where, message, round(time.monotonic() - start, 1),
                      timed_out=state == TIMEOUT)

    try:
        try:
            client.execute()
        finally:
            if stall["timer"]:
                stall["timer"].cancel()
    except CellExecutionError:
        for index, cell in zip(numbers, nb.cells, strict=True):
            errors = [o for o in cell.get("outputs", []) if o.get("output_type") == "error"]
            if errors:
                return result(FAILED, f"{name}, cell {index}", f"{errors[0]['ename']}: {errors[0]['evalue']}")
        return result(FAILED, name, "a cell failed")
    except (CellTimeoutError, _OutOfTime, TimeoutError):
        return result(TIMEOUT, f"{name}, cell {current['index']}", f"over {min(timeout, cell_timeout):g} s in: {current['title']}")
    except DeadKernelError:
        if stall["dumped"]:  # we aborted the kernel ourselves, to read its stack
            return result(TIMEOUT, f"{name}, cell {current['index']}", f"over {min(timeout, cell_timeout):g} s in: {current['title']}")
        return result(FAILED, f"{name}, cell {current['index']}", "the kernel died (out of memory?)")
    return result(PASSED)


def _run_child(command: list[str], deadline: float) -> bool:
    """Run `command` in its own process group and wait `deadline` seconds. On expiry the whole group (the
    runner and the kernel it started) is killed. Returns True if it finished by itself."""
    process = subprocess.Popen(command, start_new_session=True)
    try:
        process.wait(deadline)
        return True
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        return False


def _attempt(path: Path, runtime: str, timeout: float, cell_timeout: float, headless_widgets: bool) -> Result:
    """Run one notebook (see `_execute`) in a child process that is killed if it outlives `timeout` plus a
    grace period. nbclient's own timeout cannot fire when something blocks outside a cell (a widget waiting
    for a front end, the kernel shutting down), and one such notebook would hold the whole job."""
    path = Path(path)
    name = path.as_posix()
    start = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        progress, out = Path(tmp) / "progress.json", Path(tmp) / "result.json"
        command = [sys.executable, "-m", "nma_kit.runner", str(path), runtime, str(timeout), str(cell_timeout),
                   str(progress), str(out), "1" if headless_widgets else "0"]
        finished = _run_child(command, timeout + KILL_GRACE)
        seconds = round(time.monotonic() - start, 1)
        if out.is_file():
            return Result(**json.loads(out.read_text(encoding="utf-8")))
        if finished:
            return Result(name, runtime, classify(FAILED, runtime), name, "the notebook runner crashed", seconds)
        current = json.loads(progress.read_text(encoding="utf-8")) if progress.is_file() else {"index": 0, "title": ""}
        return Result(name, runtime, classify(TIMEOUT, runtime), f"{name}, cell {current['index']}",
                      f"hung: killed after {timeout + KILL_GRACE:g} s in: {current['title']}", seconds, timed_out=True)


def run_notebook(path: Path, runtime: str = "browser", timeout: float = DEFAULT_TIMEOUT,
                 cell_timeout: float = CELL_TIMEOUT, retries: int = RETRIES, headless_widgets: bool = True) -> Result:
    """Run a notebook, and run it again (up to `retries` times, in a fresh kernel) if it timed out: with widgets
    the kernel sometimes stalls between cells, and a stall is not a notebook problem. A failure is never retried.
    A pass after a retry stays a pass but says so, so flaky notebooks stay visible."""
    attempts, earlier = 0, []
    while True:
        attempts += 1
        result = _attempt(Path(path), runtime, timeout, cell_timeout, headless_widgets)
        if result.timed_out and attempts <= retries:
            earlier.append(f"{result.where}: {result.message}")
            print(f"  timed out ({earlier[-1]}), trying again", flush=True)
            continue
        result.attempts = attempts
        if result.state == PASSED and earlier:
            result.message = f"passed on attempt {attempts}; before: {earlier[0]}"
        return result


def summary_markdown(results: list[Result]) -> str:
    """The results as a Markdown table (job summary), problems first."""
    counts = {state: sum(r.state == state for r in results) for state in (PASSED, FAILED, TIMEOUT, NEEDS_CHECK)}
    lines = [f"{counts[PASSED]} passed, {counts[FAILED]} failed, {counts[TIMEOUT]} timed out, "
             f"{counts[NEEDS_CHECK]} need a manual check (`runtime: colab`).", "",
             "| Notebook | State | Where | Error | Seconds |", "|---|---|---|---|---|"]
    for r in sorted(results, key=lambda r: (r.state == PASSED, r.notebook)):
        message = r.message.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {r.notebook} | {r.state} | {r.where} | {message} | {r.seconds:g} |")
    return "\n".join(lines) + "\n"


def write_report(results: list[Result], path: Path) -> None:
    """Write the results as JSON (the report job merges these)."""
    Path(path).write_text(json.dumps([asdict(r) for r in results], indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":  # the child of `_attempt`: notebook, runtime, timeout, cell timeout, progress file, result file, headless widgets
    notebook, runtime_, timeout_, cell_timeout_, progress_, out_, headless_ = sys.argv[1:8]
    outcome = _execute(Path(notebook), runtime_, float(timeout_), float(cell_timeout_), Path(progress_), headless_ == "1")
    Path(out_).write_text(json.dumps(asdict(outcome)), encoding="utf-8")
