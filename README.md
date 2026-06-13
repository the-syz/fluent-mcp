# fluent-research-mcp

`fluent-research-mcp` 是一个面向本地科研工作的 MCP server，用来把 Ansys Fluent / PyFluent 仿真流程整理成可复现、可审计、可由智能体调用的工具链。

它的定位不是替代 Fluent 图形界面，而是把常见工程动作封装成稳定接口：检查环境、创建项目目录、打开已有算例、运行求解、记录运行产物、审查 UDF 变更、导出结果，并为成功或失败的运行生成摘要。

## 仓库结构

```text
.
├── src/fluent_research_mcp/     # MCP server 和 Fluent 工作流工具
├── tests/                       # 路径安全、摘要、工具返回值、UDF diff 等单元测试
├── cases/official/              # 随仓库保留的一个真实 Fluent 示例算例
├── examples/fluent_smoke/       # 最小化 Fluent journal 冒烟测试
├── pyproject.toml               # Python 包配置和可选依赖组
├── requirements.txt             # 简单安装用的运行时依赖
└── README.md
```

学习笔记、Notebook、论文资料、个人实验算例、Fluent 运行目录和 transcript 日志默认不会进入 Git；这些内容通过 `.gitignore` 保留在本地。

## 环境要求

- Python 3.11 或更新版本
- Ansys Fluent，用于真实求解
- 可用的 Fluent license
- 使用 `pyfluent` 后端时需要 PyFluent 相关依赖

只运行 MCP server 的核心接口不强制要求安装 Fluent。依赖 Fluent 的工具在检测不到 Fluent、PyFluent 或 license 时，会返回结构化错误，而不是直接崩溃。

## 安装

创建虚拟环境并安装项目：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

开发和测试环境：

```powershell
python -m pip install -e .[test]
pytest
```

真实 Fluent / PyFluent 工作流：

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

Codex Desktop MCP 配置示例：

```toml
[mcp_servers.fluent-research-mcp]
command = 'F:\fluent-mcp\.venv\Scripts\python.exe'
args = ['-m', 'fluent_research_mcp.server']
startup_timeout_sec = 30
tool_timeout_sec = 600
```

如果 Fluent 不在 `PATH` 中，可以配置 `FLUENT_PATH`：

```toml
[mcp_servers.fluent-research-mcp.env]
FLUENT_PATH = 'E:\Program Files\ANSYS Inc\v252\fluent\ntbin\win64\fluent.exe'
```

## 已实现工具

- `check_environment`：检查 Python、PyFluent、Fluent、license 线索、编译器和项目目录。
- `create_project`：创建标准项目目录和默认配置。
- `open_case`：用 PyFluent 打开已有 Fluent case/data。
- `run_solver`：创建运行目录、保存输入快照、运行 Fluent，并写出状态、摘要和报告。
- `write_udf_files`：写入 UDF 源文件并生成可审查 diff，不直接编译。
- `compile_load_udf`：在确认 diff 已审查后编译并加载 UDF。
- `export_results`：导出结果清单、CSV 和可选图片。
- `summarize_run`：重新生成某次运行的 `summary.json` 和 `report.md`。

所有工具都返回统一字典结构，包含 `ok`、`stage`、`message`、`artifacts`、`warnings` 和 `errors`。

## 示例算例

仓库中保留了一个真实 Fluent 示例算例：

```text
cases/official/noz_anim-1-00640.cas
cases/official/noz_anim-1-00640.dat
```

这个算例来自 Fluent 官方示例文件，文件本身是真实的 Fluent case/data，不是占位文件。是否能在你的机器上跑通，还取决于 Fluent 版本、license、求解器维度和批处理命令是否配置正确。

使用 MCP 命令行入口进行 batch 求解：

```powershell
python -m fluent_research_mcp.run_case F:\fluent-mcp cases\official\noz_anim-1-00640.cas --data-file cases\official\noz_anim-1-00640.dat --backend batch --fluent-dimension 3ddp --processor-count 1 --iterations 10
```

运行后会生成 `runs/<run_id>/`，其中包括 journal、日志、状态文件、摘要和报告。`runs/` 是生成物，默认不提交到 Git。

## 冒烟测试

`examples/fluent_smoke/read_mesh_check.jou` 是一个最小化 Fluent journal，用来验证 Fluent 能读取仓库中的示例 case/data，并执行网格检查。

从仓库根目录启动 Fluent batch 时可以使用：

```powershell
fluent 3ddp -g -i examples\fluent_smoke\read_mesh_check.jou
```

如果你的 Fluent 可执行文件不叫 `fluent`，请使用实际路径，例如：

```powershell
& 'E:\Program Files\ANSYS Inc\v252\fluent\ntbin\win64\fluent.exe' 3ddp -g -i examples\fluent_smoke\read_mesh_check.jou
```

这个冒烟测试适合做分层诊断：如果 Fluent 在读取算例前退出，通常是 Fluent 路径、license 或启动环境问题；如果已经进入 `/file/read-case` 或 `/file/read-data` 后失败，再优先检查算例文件、版本兼容性或文件路径。

## 开发

运行测试：

```powershell
pytest
```

查看准备提交的文件：

```powershell
git status --short
```

当前公开仓库的目标范围是 MCP 源码、测试、一个最小化 Fluent 示例、一个官方示例算例和必要的项目配置。个人学习资料、Notebook、论文 PDF、运行结果和实验性算例建议继续保留在本地。

