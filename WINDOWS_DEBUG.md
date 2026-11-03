# VS2022、VS Code 与 Python 调试流程

本指南针对当前移植源码及独立 oneMKL SDK。先完成 [项目配置](WINDOWS_BUILD.md)，再按需要选择 C++ 原生调试或 Python 调用 C++ 的调试。

## 1. 首次准备 Debug 构建

在项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/build.ps1 -Configuration Debug -Fresh
```

后续修改后重新构建时省略 `-Fresh`。输出目录为 `out/build/windows-msvc-debug`，其中应能看到：

```text
meep_debug_example.exe
meep_debug_example.pdb
mkl_sequential.2.dll
mkl_core.2.dll
python/meep/_meep.cp312-win_amd64.pyd
python/meep/_meep.pdb
```

Meep/MPB 编译为带调试信息的代码，统一链接 `/MD` 运行库，使用标准 CPython 3.12。oneMKL 本身来自 Intel 的预编译 SDK，本项目主要调试 Meep、MPB 及绑定源码。

## 2. C++ 调试：从最小算例开始

1. VS2022 打开项目文件夹。
2. 选择 **Windows x64 Debug** 配置，等待 CMake 完成，生成项目。
3. 打开 `examples/windows/minimal.cpp`。
4. 在 `fields.step();` 行左侧设置断点，或选中该行按 F9。
5. 启动目标选择 `meep_debug_example.exe`，按 **F5**。
6. 停住后，使用 F10 单步跳过，F11 进入函数；可进入 `src/step.cpp` 的 `meep::fields::step()`。
7. 在“局部变量”和“监视”窗口检查 `fields`、`grid`、`fields.time()`，并查看“调用堆栈”。

最小算例建立 4×4 的二维真空区域、PML 和高斯点源，运行到时间 10，打印观测点的 Ez。MKL DLL 已暂存到 exe 旁，F5 无需额外配置系统 PATH。

也可以在“解决方案资源管理器”切换到 **CMake 目标视图**，右键 `meep_debug_example` 选择调试。VS 的目标启动方式见 [Microsoft CMake 调试说明](https://learn.microsoft.com/en-us/cpp/build/configure-cmake-debugging-sessions?view=msvc-170)。

如需传入参数或修改工作目录，在目标的“调试和启动设置”中生成 `launch.vs.json`，让 VS 自动填充 `projectTarget`。该设置位于本机 `.vs` 目录，源码迁移后重新生成即可。

## 3. 从 Python 调用处调试 Meep C++

适用于排查 Python API、SWIG 绑定、FDTD 内核或 MPB 的调用问题。

### 第一步：启动并暂停 Python

在普通 PowerShell 中执行：

```powershell
.\.venv\Scripts\python.exe tools/windows/run.py --preset windows-msvc-debug python examples/windows/debug_simulation.py --wait
```

程序打印 **Python PID**，并停在等待输入的位置。记下 PID，暂时不要按回车。

### 第二步：VS 附加到该进程

1. 在 VS 中打开同一源码目录，选择 **Windows x64 Debug**。
2. 打开 `src/step.cpp`，在 `meep::fields::step()` 中设置断点。
3. 使用 VS 的“调试 → 附加到进程”。
4. 按终端打印的 PID 选择 Python 进程；不要只按 `python.exe` 名称选择。
5. 代码类型选择 **本机 / Native**，然后附加。

### 第三步：继续运行

返回 PowerShell 按回车。程序随后导入当前构建的 `_meep.pyd` 并开始仿真，C++ 断点应在调用 `fields::step()` 时绑定并停住。

该流程在导入扩展前暂停，因此刚附加时断点暂未绑定是正常的。扩展载入后，VS 可从其旁边加载 `_meep.pdb`。

原生附加方式用于检查 C/C++ 调用堆栈和变量。若仅需调试 Python 代码，可使用下一节的 Python 调试器。

## 4. 单独调试 Python 代码

不需要额外安装 VS Python 工作负载，可先使用 CPython 自带的 pdb：

```powershell
.\.venv\Scripts\python.exe tools/windows/run.py --preset windows-msvc-debug python -m pdb examples/windows/debug_simulation.py
```

常用命令：

| 命令 | 含义 |
| --- | --- |
| `n` | 执行下一行 |
| `s` | 进入 Python 函数 |
| `b <行号>` | 设置断点 |
| `p <表达式>` | 查看值，例如 `p sim.resolution` |
| `c` | 继续运行 |
| `q` | 退出调试 |

`pdb` 在 Python 层逐行执行；进入原生实现时使用前一节的 VS Native 附加方式。

## 5. 排查空心断点与符号问题

先确认打印的包路径：

```powershell
.\.venv\Scripts\python.exe tools/windows/run.py --preset windows-msvc-debug python -c "import meep; print(meep.__file__)"
```

应位于当前项目的 `out/build/windows-msvc-debug/python/meep`。

| 检查项 | 正常情况 |
| --- | --- |
| VS 配置 | Windows x64 Debug |
| 进程 | 与终端打印的 PID 一致 |
| 代码类型 | Native |
| 模块窗口中的 `_meep` | 路径来自当前 Debug 输出目录 |
| PDB | 与 `.pyd` 或 exe 同次生成，符号已加载 |
| 源码 | 与构建时相同；修改后已重新生成 |

在 VS 的“调试 → 窗口 → 模块”中查看 `_meep` 的实际路径和符号状态。如果来自 `site-packages` 或 Release 目录，停止进程，通过指定 Debug 预设的 `run.py` 重新启动。

不要把 Release wheel 复制成 Debug 扩展，也不要只替换 PDB。生成时 `.pyd` 被占用，需要先结束 Python 进程和调试会话。

## 6. 常用调试入口

| 排查内容 | 入口 |
| --- | --- |
| FDTD 时间推进 | `src/step.cpp`，`meep::fields::step()` |
| Python 高层仿真流程 | `python/simulation.py` |
| SWIG 参数与回调转换 | `python/meep.i`、`python/meep-python.hpp`、`python/typemap_utils.cpp` |
| 材料与几何转换 | `src/meepgeom.cpp`、`third_party/libctl/utils/geom.c` |
| 模式计算 | `src/mpb.cpp`、`third_party/mpb/src/maxwell/`、`third_party/mpb/src/matrices/` |
| 数值后端 ABI 与 FFT | `tests/windows/numeric_backend.cpp`，目标 `meep_numeric_backend` |

调试改动后，先跑最小算例和相关测试，再执行 Release 回归。这样可以把 C++ 逻辑错误、Python 接口问题和构建环境问题分别定位。

本轮已验证 Debug 原生算例在系统 PATH 下直接启动，以及通过 pdb 设置 Python 断点、查看 `(40, 40)` 场数组并继续运行。相关日志为 `build/windows/native-debug-clean-path.log`、`build/windows/python-pdb.log`；VS 图形界面附加步骤由开发者按上述流程操作。

## 7. VS Code 调试 Python 示例

### 准备与首次运行

1. 用 VS Code 的“文件 → 打开文件夹”打开 **项目根目录**，例如 `E:\SourceCode\meep`，不要只打开 `python/examples` 子目录。
2. 安装 Microsoft 的 **Python** (`ms-python.python`) 和 **Python Debugger** (`ms-python.debugpy`) 扩展；本机已安装。无需安装 VS2022 的 Python 工作负载，也无需向 `.venv` 额外安装 debugpy。
3. 新电脑先按 `WINDOWS_BUILD.md` 运行 `tools/windows/setup.ps1` 准备 `.venv`、VS2022 C++ 工具链和独立 oneMKL。VS Code 的构建任务会调用现有 VS2022 编译器。
4. 打开 `python/examples/straight-waveguide.py`，在第 32 行 `sim.run(until=200)` 左侧点击设置断点。
5. 按 `Ctrl+Shift+D` 打开“运行和调试”，选择 **Meep: Python straight-waveguide (Debug)**，按 **F5**。
6. 首先执行 **Meep: build Debug** 任务，配置并增量构建 Debug 扩展；成功后 Python 调试器启动，并在断点停住。第一次构建可能较慢。
7. 在“变量”和“监视”中查看 `sim`、`cell`、`geometry`；在“调试控制台”输入 `sim.resolution`，应得到 `10`。

项目自带 `.vscode/launch.json`、`tasks.json`、`settings.json` 和扩展推荐；所有项目路径均相对于 `${workspaceFolder}`，复制源码到其他电脑后不需要修改这些路径。

### 调试其他示例与单步操作

打开需要调试的 `python/examples/*.py`，选择 **Meep: Python current example (Debug)** 后按 F5。此配置运行当前活动编辑器中的文件，因此启动时确认选中的是示例 `.py`。固定的 straight-waveguide 配置始终运行直波导示例，适合进入包内部后反复调试。

| 操作 | 快捷键 / 方法 |
| --- | --- |
| 设置或取消断点 | F9，或点击行号左侧 |
| 继续 | F5 |
| 单步跳过 | F10 |
| 进入 Python 函数 | F11 |
| 跳出 Python 函数 | Shift+F11 |
| 停止 | Shift+F5 |
| 查看变量、数组形状 | “变量”“监视”或“调试控制台”，如 `sim.resolution`、`ez_data.shape` |
| 传递示例参数 | 在所选 `launch.json` 配置的 `args` 中填写，如 `["-N", "2"]`；参数取决于具体示例 |

`justMyCode: false` 允许进入 Meep 的 Python 包代码。Python 调试器可以查看仿真参数、控制流程和 NumPy 数据；进入 `_meep.pyd` 的 C++ 实现需要本机调试器，见前面的原生调试流程。

### 环境、绘图与结果位置

调试配置明确指定：

| 项目 | 设置 |
| --- | --- |
| Python | `${workspaceFolder}/.venv/Scripts/python.exe` |
| Meep 包搜索路径 | `${workspaceFolder}/out/build/windows-msvc-debug/python` |
| 工作目录 | `${workspaceFolder}` |
| 绘图后端 | `TkAgg`，`plt.show()` 显示独立窗口；关闭图窗后程序继续 |
| 数值线程数 | `OMP_NUM_THREADS=1`、`MKL_NUM_THREADS=1` |

这里直接启动示例，**不会经过将后端强制设为 Agg 的 `run.py`**。当前构建的 Meep 扩展会从包内 `.libs` 加载独立 oneMKL SDK 的运行库。无需手工修改系统 PATH。

`TkAgg` 需要基础 CPython 安装包含 Tcl/Tk；本机已具备。其他电脑如缺少 tkinter，可修改 Python 安装添加 Tcl/Tk，或把配置中的 `MPLBACKEND` 改为 `Agg` 并用 `plt.savefig(...)` 保存图片。相对路径的结果文件默认写入项目根目录；示例如果调用 `use_output_directory(...)` 等方法，则以其设置为准。

在断点处的“调试控制台”输入以下表达式检查实际加载位置：

```python
__import__('sys').executable
__import__('meep').__file__
```

第二项应指向 `out/build/windows-msvc-debug/python/meep/__init__.py`。如果 Python 扩展先前记住了其他解释器，可通过 `Ctrl+Shift+P → Python: Select Interpreter` 选择项目 `.venv`；项目提供的 F5 配置仍会显式使用 `.venv`。

调试时导入的是构建目录中的 Python 包。修改 `python/simulation.py` 等源码后，停止调试并重新 F5，构建任务会重新复制包源码。F11 进入包代码时编辑器可能打开 `out/build/.../python/meep/simulation.py`；正式修改应回到源码目录 `python/simulation.py`。不要只修改构建目录中的副本。

不要在 `_meep.pyd` 被 Python 占用时重新链接；先停止已有调试进程。基础 FDTD 示例可先从 straight-waveguide 开始；`mpb_*.py` 所需的独立 `meep.mpb.ModeSolver`、MPI/GDS 等功能尚未接入当前移植。

配置字段参考 [VS Code Python 调试文档](https://code.visualstudio.com/docs/python/debugging)。

本轮使用本机 VS Code Python Debugger 扩展自带的 debugpy 适配器，按固定直波导配置实际启动：在第 32 行和第 37 行命中断点，读取 `sim.resolution == 10`，仿真后场数组形状为 `(160, 80)` 且所有值有限，绘图后端为 `TkAgg`。验证记录在 `build/windows/vscode-python-debug.json`；验证在创建图窗前结束，未操作 VS Code 图形界面。

## 8. VS Code 运行 Jupyter Notebook

`.ipynb` 的 cell 由独立的 Jupyter 内核执行，不会使用 `.py` 文件 F5 调试时的 `launch.json` 环境，也不会自动执行其中的构建任务。原始环境只有 Python 脚本所需依赖，缺少 `ipykernel`；补装内核后仍需要提供当前构建的 Meep 包路径。

完成基础项目配置后，在项目根目录执行一次：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/setup_notebook.ps1
```

脚本使用 `requirements-notebooks.lock.txt` 固定 Notebook 依赖，在项目 `.venv` 内安装 `ipykernel`、执行验证所用的 nbclient，以及 MP4 导出所需的 imageio-ffmpeg；基础数值包版本由原来的锁定文件约束。随后增量构建 Debug 版 Meep，创建项目虚拟环境内的 `meep-debug` kernelspec，并生成本机 `.vscode/notebook.local.env`。FFmpeg 可执行文件放在 `.venv/Scripts/ffmpeg.exe`，系统 PATH 保持原样。

VS Code 中的操作：

1. 打开项目根目录，确认 Microsoft 的 **Python** 和 **Jupyter** 扩展已启用。
2. 打开 `python/examples/straight-waveguide.ipynb`。
3. 点击右上角“选择内核 → 选择其他内核 → Jupyter Kernel”，选择 **Meep (Debug, Python 3.12)**。也可从“Python 环境”中选择项目 `.venv/Scripts/python.exe`；其环境由 `python.envFile` 指定的本机文件提供。不要选择另一套系统 Python。
4. 如果未出现新内核，执行 `Developer: Reload Window` 后重选；如果此前已启动内核，先点击 Notebook 的“重启内核”。
5. 点击“全部运行”，或从第一格起依次按 `Shift+Enter`。后面的 cell 依赖前面的 `mp`、`sim`、`Animate` 等对象。

可新增诊断 cell：

```python
import sys
import meep as mp
import shutil
print(sys.executable)
print(mp.__file__)
print(shutil.which("ffmpeg"))
```

三个路径应分别来自当前项目的 `.venv`、`out/build/windows-msvc-debug/python/meep`、`.venv/Scripts/ffmpeg.exe`。Notebook 使用 `%matplotlib inline` 在 cell 下方显示图片，运行环境默认也选择 inline 后端；`.py` 调试配置仍显式使用 TkAgg。

直波导 Notebook 的后半部分会记录动画并写出 `media/straight_waveguide.mp4`，需要 FFmpeg；脚本已配置。相对路径由 Notebook 的工作目录决定，一般为 `python/examples`；如果自己修改工作目录，先确保 `media` 子目录存在。

修改 C++ 或 Python 包源码后：先停止并重启或关闭旧内核，按 `Ctrl+Shift+B` 构建 Debug，再重新启动内核并从头运行。单纯再次运行 cell 不会卸载并重新加载已经载入的 `.pyd`。修改 cell 本身则可直接重跑。

其他配置可使用 `setup_notebook.ps1 -Configuration Release`，或在依赖已安装、目标已构建时直接运行 `configure_notebook.py --configuration Release`；它会更新 Notebook 默认的 Meep 路径，之后需要重启内核。新电脑重新生成本机配置，不复制 `.venv` 或 `notebook.local.env`。

离线使用时先在联网机器执行 `prepare_offline.ps1 -Notebooks`，再在目标机器执行 `setup_notebook.ps1 -Wheelhouse .cache/wheelhouse`。VS Code 内核选择机制见 [官方文档](https://code.visualstudio.com/docs/datascience/jupyter-kernel-management)。

本轮已通过真实 `meep-debug` Jupyter 内核，从头执行原始直波导 Notebook 的 14 个代码 cell，另加一格诊断：场数组为 `(160, 80)`，所有数值有限，MP4 导出成功。执行副本和视频保存在 `build/windows/notebook-run/`，结果记录为其中的 `result.json`；原始 Notebook 的 cell 和输出未改写。
