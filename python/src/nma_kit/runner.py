"""Run generated notebooks end to end (`nma-kit run-notebooks`), for the scheduled course-nightly workflow.

The instructor notebook of each page is the one that runs: it has the solutions filled in, so it has no
intentional errors. A failure on a `runtime: colab` page (a GPU or ML-library notebook) is only flagged
for a manual check, because the scheduled job runs on CPU. This module needs only nbclient and nbformat
(the Colab image has both), and no course settings except in `list_targets`.
"""

import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

PASSED, FAILED, TIMEOUT, NEEDS_CHECK = "passed", "failed", "timeout", "needs-check"
BREAKING = (FAILED, TIMEOUT)
DEFAULT_TIMEOUT = 1200  # seconds for one whole notebook


@dataclass
class Result:
    """The outcome of one notebook."""

    notebook: str
    runtime: str
    state: str
    where: str = ""    # "<notebook>, cell N" of the first problem
    message: str = ""  # the last line of the error
    seconds: float = 0.0


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


def run_notebook(path: Path, runtime: str = "browser", timeout: float = DEFAULT_TIMEOUT) -> Result:
    """Execute one notebook in a fresh kernel, in the notebook's own folder, within `timeout` seconds in total."""
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError, CellTimeoutError, DeadKernelError

    path = Path(path)
    name = path.as_posix()
    nb = nbformat.read(path, as_version=4)
    start = time.monotonic()
    current = {"index": 0}

    def on_cell_start(cell, cell_index):
        current["index"] = cell_index + 1
        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise _OutOfTime
        client.timeout = max(1, math.ceil(remaining))

    client = NotebookClient(nb, timeout=math.ceil(timeout), kernel_name="python3",
                            resources={"metadata": {"path": str(path.resolve().parent)}})
    client.on_cell_start = on_cell_start

    def result(state, where="", message=""):
        return Result(name, runtime, classify(state, runtime), where, message, round(time.monotonic() - start, 1))

    try:
        client.execute()
    except CellExecutionError:
        for index, cell in enumerate(nb.cells, 1):
            errors = [o for o in cell.get("outputs", []) if o.get("output_type") == "error"]
            if errors:
                return result(FAILED, f"{name}, cell {index}", f"{errors[0]['ename']}: {errors[0]['evalue']}")
        return result(FAILED, name, "a cell failed")
    except (CellTimeoutError, _OutOfTime, TimeoutError):
        return result(TIMEOUT, f"{name}, cell {current['index']}", f"over {timeout:g} s")
    except DeadKernelError:
        return result(FAILED, f"{name}, cell {current['index']}", "the kernel died (out of memory?)")
    return result(PASSED)


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
