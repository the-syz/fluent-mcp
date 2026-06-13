# fluent-research-mcp

`fluent-research-mcp` 是一个用于 Ansys Fluent / PyFluent 工作流自动化的本地 MCP server。它把 Fluent 仿真中常见的环境检查、项目初始化、算例运行、UDF 管理、结果导出和运行摘要封装成可由 MCP 客户端调用的结构化工具。

项目目标是让 Fluent 仿真流程更容易被记录、复现和诊断，尤其适合需要把 CFD 计算纳入自动化科研流程、工程验证流程或智能体工具链的场景。

## 主要特性

- 环境诊断：检查 Python、PyFluent、Fluent 可执行文件、license 线索和编译器可用性。
- 项目初始化：生成统一的 Fluent 项目目录和默认配置。
- 算例执行：支持 PyFluent 后端和 Fluent batch/journal 后端。
- 运行审计：保存输入快照、journal、日志、状态文件、摘要和报告。
- UDF 工作流：写入 UDF 源文件，生成 diff，要求审查后再编译加载。
- 结果导出：导出结果清单、CSV 数据和可选图片。
- 结构化返回：所有 MCP 工具返回统一的 `ok`、`stage`、`message`、`artifacts`、`warnings`、`errors` 字段。

## 适用场景

- 用 MCP 客户端调用 Fluent/PyFluent 进行可追踪仿真。
- 在批处理环境中运行已有 Fluent case/data。
- 对 UDF 变更进行审查、编译和加载。
- 为失败的 Fluent 运行生成可读的诊断报告。
- 为研究或工程项目保留可复现的运行记录。

## 仓库结构

```text
.
├── src/fluent_research_mcp/     # MCP server 和 Fluent 工作流工具
├── tests/                       # 单元测试
├── cases/official/              # 可用于诊断的 Fluent 示例算例
├── examples/fluent_smoke/       # 最小化 Fluent batch 冒烟测试
├── pyproject.toml               # Python 包配置
├── requirements.txt             # 最小运行依赖
└── README.md
```

生成的运行目录、Fluent transcript、缓存文件和本地实验数据不会进入版本库。

## 环境要求

- Python 3.11 或更新版本
- Ansys Fluent，用于真实求解和 batch 诊断
- 可用的 Fluent license
- 使用 `pyfluent` 后端时需要 PyFluent 相关依赖

只启动 MCP server 或运行非 Fluent 依赖工具时，不要求本机已经安装 Fluent。涉及 Fluent 的工具会在环境不可用时返回结构化错误，便于上层客户端判断失败原因。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

安装开发和测试依赖：

```powershell
python -m pip install -e .[test]
pytest
```

安装 Fluent/PyFluent 相关依赖：

```powershell
python -m pip install -e .[fluent,test]
```

也可以使用 `requirements.txt` 安装最小运行依赖：

```powershell
python -m pip install -r requirements.txt
```

## 启动 MCP server

```powershell
python -m fluent_research_mcp.server
```

MCP 客户端配置示例：

```toml
[mcp_servers.fluent-research-mcp]
command = '<repo>\\.venv\\Scripts\\python.exe'
args = ['-m', 'fluent_research_mcp.server']
startup_timeout_sec = 30
tool_timeout_sec = 600
```

如果 Fluent 不在 `PATH` 中，可以通过环境变量指定可执行文件：

```toml
[mcp_servers.fluent-research-mcp.env]
FLUENT_PATH = 'C:\\Program Files\\ANSYS Inc\\v252\\fluent\\ntbin\\win64\\fluent.exe'
```

## MCP 工具

| 工具 | 用途 |
| --- | --- |
| `check_environment` | 检查 Python、PyFluent、Fluent、license、编译器和项目目录 |
| `create_project` | 创建标准项目目录和默认配置 |
| `open_case` | 用 PyFluent 打开已有 Fluent case/data |
| `run_solver` | 创建运行目录，运行 Fluent，并写出状态、摘要和报告 |
| `write_udf_files` | 写入 UDF 源文件并生成可审查 diff |
| `compile_load_udf` | 编译并加载已审查的 UDF |
| `export_results` | 导出结果清单、CSV 和可选图片 |
| `summarize_run` | 重新生成某次运行的 `summary.json` 和 `report.md` |

## 示例算例

仓库提供一个小型 Fluent case/data，用于验证 Fluent 启动、算例读取和基础网格检查：

```text
cases/official/noz_anim-1-00640.cas
cases/official/noz_anim-1-00640.dat
```

该算例是真实 Fluent case/data 文件，不是占位文件。它是否能完成求解仍取决于本机 Fluent 版本、license、维度参数和求解设置。

使用 MCP 命令行入口执行一次 batch 求解：

```powershell
python -m fluent_research_mcp.run_case . cases\official\noz_anim-1-00640.cas --data-file cases\official\noz_anim-1-00640.dat --backend batch --fluent-dimension 3ddp --processor-count 1 --iterations 10
```

运行产物会写入 `runs/<run_id>/`，包括输入快照、journal、日志、状态文件、摘要和报告。`runs/` 属于生成物，默认不提交。

## 冒烟测试

`examples/fluent_smoke/read_mesh_check.jou` 是一个最小化 Fluent journal：

```scheme
/file/read-case "cases/official/noz_anim-1-00640.cas"
/file/read-data "cases/official/noz_anim-1-00640.dat"
/mesh/check
/exit yes
```

从仓库根目录运行：

```powershell
fluent 3ddp -g -i examples\fluent_smoke\read_mesh_check.jou
```

如果 Fluent 可执行文件不在 `PATH` 中，使用实际路径：

```powershell
& 'C:\Program Files\ANSYS Inc\v252\fluent\ntbin\win64\fluent.exe' 3ddp -g -i examples\fluent_smoke\read_mesh_check.jou
```

这个测试适合做分层诊断：如果 Fluent 在读取算例前退出，优先检查 Fluent 路径、license 或启动环境；如果进入 `/file/read-case` 或 `/file/read-data` 后失败，再检查算例文件、版本兼容性或路径。

## 开发

运行测试：

```powershell
pytest
```

查看版本库状态：

```powershell
git status --short
```

建议在提交前确认运行产物、缓存文件和本地实验数据没有进入 Git。

## 许可

本项目不包含 Ansys Fluent 软件本体，也不提供 Fluent license。使用 Fluent、PyFluent 和相关示例文件时，请遵守 Ansys 的许可条款。
