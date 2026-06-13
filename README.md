# fluent-research-mcp

`fluent-research-mcp` is a local MCP server for making Ansys Fluent and PyFluent research workflows easier to inspect, reproduce, and automate.

The server is designed for single-user local research work. It can create project directories, validate Fluent/PyFluent environments, run existing Fluent cases, record solver artifacts, review UDF changes before compilation, export selected results, and summarize completed or failed runs.

## Repository layout

```text
.
├── src/fluent_research_mcp/     # MCP server and Fluent workflow tools
├── tests/                       # Unit tests for path safety, summaries, tools, and UDF diffs
├── cases/official/              # One tracked Fluent sample case
├── examples/fluent_smoke/       # Minimal Fluent journal smoke test
├── pyproject.toml               # Package metadata and optional dependency groups
├── requirements.txt             # Runtime dependency list for simple installs
└── README.md
```

Local learning notes, notebooks, paper notes, generated run folders, Fluent transcript files, and experimental cases are intentionally excluded from Git by `.gitignore`.

## Requirements

- Python 3.11 or newer
- Ansys Fluent for real solver runs
- A valid Fluent license for solver operations
- PyFluent dependencies when using the `pyfluent` backend

The core MCP server can be installed without Fluent. Fluent-dependent tools return structured errors when Fluent, PyFluent, or a license is unavailable.

## Installation

Create a virtual environment and install the server:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

For development and tests:

```powershell
python -m pip install -e .[test]
pytest
```

For real Fluent/PyFluent workflows:

```powershell
python -m pip install -e .[fluent,test]
```

If you prefer a plain requirements file:

```powershell
python -m pip install -r requirements.txt
```

## Start the MCP server

```powershell
python -m fluent_research_mcp.server
```

Codex Desktop MCP configuration example:

```toml
[mcp_servers.fluent-research-mcp]
command = 'F:\fluent-mcp\.venv\Scripts\python.exe'
args = ['-m', 'fluent_research_mcp.server']
startup_timeout_sec = 30
tool_timeout_sec = 600
```

If Fluent is not on `PATH`, configure `FLUENT_PATH`:

```toml
[mcp_servers.fluent-research-mcp.env]
FLUENT_PATH = 'E:\Program Files\ANSYS Inc\v252\fluent\ntbin\win64\fluent.exe'
```

## Tools

- `check_environment`: inspect Python, PyFluent, Fluent, license hints, compiler availability, and project paths.
- `create_project`: create a standard project directory with default config folders.
- `open_case`: open an existing Fluent case/data file with PyFluent.
- `run_solver`: create a run directory, snapshot inputs, run Fluent, and write status/report artifacts.
- `write_udf_files`: write UDF source files and generate an auditable diff without compiling.
- `compile_load_udf`: compile and load reviewed UDF files.
- `export_results`: export selected result files, CSV data, and optional images.
- `summarize_run`: regenerate `summary.json` and `report.md` for a run.

All tools return a consistent dictionary with `ok`, `stage`, `message`, `artifacts`, `warnings`, and `errors`.

## Sample case

This repository tracks one small Fluent sample case under:

```text
cases/official/noz_anim-1-00640.cas
cases/official/noz_anim-1-00640.dat
```

Example batch run:

```powershell
python -m fluent_research_mcp.run_case F:\fluent-mcp cases\official\noz_anim-1-00640.cas --data-file cases\official\noz_anim-1-00640.dat --backend batch --fluent-dimension 3ddp --processor-count 1 --iterations 10
```

Batch runs create `runs/<run_id>/` with journals, logs, status, summaries, and reports. These generated artifacts are ignored by Git.

## Development

Run the test suite:

```powershell
pytest
```

Check which files will be committed:

```powershell
git status --short
```

The intended public repository content is the MCP package, tests, a minimal smoke example, and the single official sample case. Keep personal notes, notebooks, paper PDFs, generated Fluent outputs, and experimental cases local.
