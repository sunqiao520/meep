# 在其他电脑复现当前 Meep 仿真环境

记录日期：2026-11-03。仓库：<https://github.com/sunqiao520/meep>。

本仓库基于 Meep 1.35.0，包含 Windows 原生 MSVC 移植，Python 包版本为 **1.35.0+msvc2**。以下流程恢复本项目的开发、仿真、调试和 Notebook 环境。目标电脑使用 **Windows x64**；Linux、macOS、WSL 或 Conda 的上游 Meep 包不属于本次验证的同一构建环境。

## 1. 本次上传的环境基线

| 项目 | 当前电脑实际版本 / 设置 |
| --- | --- |
| 系统 | Windows 11 x64，系统版本 10.0.22000 |
| Visual Studio | VS2022 Community 17.7.34221.43 |
| MSVC 工具集 / C++ 编译器 | 14.37.32822 / 19.37.32825.0 |
| Windows SDK | 10.0.22621.0 |
| Python | 标准 CPython 3.12.0 x64 |
| CMake / Ninja / SWIG | 3.31.10 / 1.13.2 / 4.5.1 |
| Intel oneMKL | 独立开发 SDK 2025.3.0，LP64、sequential、dynamic |
| NumPy / SciPy / h5py / Matplotlib | 2.4.1 / 1.18.1 / 3.16.0 / 3.11.2 |
| 运行方式 | 串行、双精度，`OMP_NUM_THREADS=1`、`MKL_NUM_THREADS=1` |

完整的机器无关版本快照见 [environment-baseline.json](environment-baseline.json)。Python 基础包及 Notebook 包分别固定在 [requirements-windows.lock.txt](../requirements-windows.lock.txt) 和 [requirements-notebooks.lock.txt](../requirements-notebooks.lock.txt)。第三方源码及其来源版本见 [UPSTREAM_SOURCES.json](../UPSTREAM_SOURCES.json)，已随仓库提交，无需单独初始化子模块。

第三方测试数据的发布调整见 [THIRD_PARTY_NOTES.md](THIRD_PARTY_NOTES.md)。

## 2. 安装基础软件并克隆仓库

新电脑先安装 Git、Visual Studio 2022（或 VS2022 Build Tools）的“使用 C++ 的桌面开发”，以及标准 **CPython 3.12 x64**。VS 中需要 MSVC v143 x64/x86 和 Windows SDK；使用 VS 图形界面时同时安装 C++ CMake 工具。Python 安装时保留 Python Launcher 和 Tcl/Tk，后者供独立绘图窗口使用。

需要尽量接近本机结果时，使用表中相同的 Python 补丁版本、MSVC 工具集和 SDK。其他 VS2022 工具集或 Python 3.12 补丁版本应重新执行下文的测试，不能直接视为已经验收。

在 PowerShell 中执行：

```powershell
git clone --branch development https://github.com/sunqiao520/meep.git
cd meep
git branch --show-current
git rev-parse HEAD
```

分支应为 `development`。保存 `git rev-parse HEAD` 输出的提交号；要复现某次确定的源码，在两台电脑使用同一个提交号。`main` 保存初始可用基线，`development` 用于后续开发。只需源码 ZIP 时，可在 GitHub 先切换到 `development` 再下载。

## 3. 一次性配置依赖

以下命令均在克隆后的项目根目录执行，不要求先激活虚拟环境：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/setup.ps1 -InstallOneMKL
```

脚本下载固定版本的 Intel 官方 oneMKL 安装器，校验 SHA256 和数字签名，然后创建 `.venv` 并安装固定版本的构建工具和科学计算包。安装 oneMKL 时可能出现管理员确认；此参数使用安装器的静默模式并接受 Intel 许可条款。默认 SDK 安装位置是 `C:\Program Files (x86)\Intel\oneAPI\mkl\2025.3`。

已装好该版本的独立 SDK 时，省略 `-InstallOneMKL`。Python 或 SDK 在自定义位置时，显式指定：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/setup.ps1 -PythonExe "D:\Python312\python.exe" -MklRoot "D:\Intel\oneAPI\mkl\2025.3"
```

`windows.local.json` 保存新电脑的 SDK 路径，由脚本重新生成。脚本最终应输出 `[OK] Pinned Python dependencies and standalone SDK are ready.`；实际环境报告写入 `build/windows/environment-report.json`。

## 4. 编译并运行一次仿真

先构建适合调试的 Debug 配置：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/build.ps1 -Configuration Debug -Fresh
.\.venv\Scripts\python.exe tools/windows/run.py --preset windows-msvc-debug python examples/windows/debug_simulation.py
```

预期打印当前克隆目录中的 `out/build/windows-msvc-debug/python/meep/__init__.py`，场数组形状为 `(40, 40)`，最大幅度约 `1.3434411353`，没有断言错误。应通过 `run.py` 选择构建目录；仅在未配置包路径的系统 Python 中执行 `import meep` 不能验证此构建。

正式仿真使用 Release，并执行完整的项目回归入口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/build.ps1 -Configuration Release -Fresh -Test
.\.venv\Scripts\python.exe tools/windows/run.py --preset windows-msvc-release python tools/windows/smoke.py
```

`-Test` 依次运行原生 CTest、基础 Python 回归和 Harminv/MPB 专项测试；MPI 相关跳过符合当前串行配置。`smoke.py` 另行验证 PML 时间推进、有限且非零的电场、HDF5 写入/读取和 MPB 本征模。均匀介质算例的频率应约为 `0.2`，`kx` 约为 `0.2`，并打印实际加载的 MKL DLL 路径。

慢速机器可在构建命令后增加 `-TestTimeoutSec 1800`；内存有限时用 `-Jobs 2`。后续增量构建可省略 `-Fresh`。

运行自己的脚本时保持同一入口，例如：

```powershell
.\.venv\Scripts\python.exe tools/windows/run.py --preset windows-msvc-release python python/examples/straight-waveguide.py
```

`run.py` 默认使用无窗口的 `Agg` 绘图后端，适合计算与保存图片；需要绘图窗口和断点时使用下面的 VS Code 配置。

## 5. 恢复 VS Code 与 Jupyter Notebook

在 VS Code 中打开项目根目录，安装 Microsoft 的 Python、Python Debugger 和 Jupyter 扩展。`.vscode` 中的共享配置已随仓库提交。

- Python 脚本：选择 `Meep: Python straight-waveguide (Debug)` 并按 F5。构建任务会先增量构建 Debug，再运行直波导示例；`TkAgg` 显示独立图窗。
- Notebook：先执行以下命令安装固定依赖、构建 Debug 并生成本机内核：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/setup_notebook.ps1
```

打开 `python/examples/straight-waveguide.ipynb`，选择 **Meep (Debug, Python 3.12)** 内核，从第一格开始“全部运行”。内核不可见时重新加载 VS Code 窗口。脚本也会准备 `.venv/Scripts/ffmpeg.exe`，供 Notebook 导出 MP4。

可在 Notebook 中运行以下诊断：

```python
import sys, shutil
import meep as mp
print(sys.executable)
print(mp.__file__)
print(shutil.which("ffmpeg"))
```

三项路径应来自当前项目的 `.venv`、`out/build/windows-msvc-debug/python/meep` 和 `.venv/Scripts/ffmpeg.exe`。更新 C++ 或包源码后，先停止旧调试进程或内核，重新构建，再启动内核并从头运行。详细说明见 [WINDOWS_DEBUG.md](../WINDOWS_DEBUG.md)。

## 6. 同步代码与迁移规则

新电脑日常同步开发分支：

```powershell
git switch development
git pull --ff-only origin development
```

同步前先保存或提交本机改动。依赖清单变化时重新运行 `setup.ps1`；Notebook 依赖或路径变化时重新运行 `setup_notebook.ps1`。切换源码后重新构建，再启动仿真。需要更换编译器、SDK 或 Python 时使用 `-Fresh` 重新配置。

仓库保存源码、第三方源码、配置模板、锁定清单和说明。`.venv`、`.venv-wheel`、`.cache`、`out`、`build`、`dist`、`.vs`、`windows.local.json`、`.vscode/notebook.local.env` 已被忽略；它们含本机路径或生成产物，应在每台电脑重新创建。需要保留的仿真参数和自定义脚本请提交到仓库，计算输出可另行归档。上游自带的 HDF5 测试数据仍保留。

离线迁移时，在联网开发机执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/prepare_offline.ps1 -Notebooks
```

携带生成的源码 ZIP、`.cache/installers/` 中的固定 oneMKL 安装器、完整 `.cache/wheelhouse/`（包括 `sha256.json`），以及 VS2022、Python 安装介质。解压源码并保持缓存相对目录，在目标电脑执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/setup.ps1 -InstallOneMKL -Wheelhouse .cache/wheelhouse
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/setup_notebook.ps1 -Wheelhouse .cache/wheelhouse
```

离线大文件不随 Git 仓库上传。源码 ZIP 也包含本指南与环境基线。

## 7. 验收依据与边界

本次上传前在当前电脑重新执行并通过：环境版本检查、`pip check`、Release CTest **10/10**、基础 Python 回归 **114 通过 / 1 项 MPI 跳过**、Release 集成验证（PML、HDF5、MPB）和 Debug 最小仿真。源码导出包也已检查包含本指南和环境基线。具体基线与验证摘要见 [environment-baseline.json](environment-baseline.json)。新电脑应自行完成第 4 节的回归测试；本次未在另一台物理电脑上验收。

不同 CPU 和工具链可能产生微小浮点差异，复现以同一源码提交、固定依赖和数值容差为依据。当前移植支持串行双精度、HDF5、Harminv 与 MPB 核心；MPI、OpenMP、Scheme、GSL/GDS、独立 `meep.mpb.ModeSolver` 尚未接入，完整伴随优化矩阵未验收。某些上游示例需要这些功能，不应据此认为基础安装失败。已知几何随机压力用例见 [WINDOWS_BUILD.md](../WINDOWS_BUILD.md#几何随机压力检查的已知问题)。

故障排查、wheel 打包和更详细的构建参数见 [WINDOWS_BUILD.md](../WINDOWS_BUILD.md)。
