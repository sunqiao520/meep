# Windows 项目配置与复现指南

更新日期：2026-10-17。源码基于 Meep 1.35.0；当前移植包版本为 **1.35.0+msvc2**。

本项目使用 **VS2022 / MSVC + CMake + 独立安装的 Intel oneMKL 2025.3.0 + CPython 3.12 x64**。oneMKL 不再安装到 Python 虚拟环境中。调试步骤见 [WINDOWS_DEBUG.md](WINDOWS_DEBUG.md)。

通过 GitHub 获取本项目并在新电脑恢复环境的完整流程见 [中文复现指南](docs/REPRODUCE.zh-CN.md)，其中也提供本次上传时的实际环境版本与验收结果。

## 1. 新电脑先安装两项基础软件

| 软件 | 安装内容 |
| --- | --- |
| [Visual Studio 2022](https://visualstudio.microsoft.com/vs/) 或其 Build Tools | “使用 C++ 的桌面开发”，包括 MSVC v143 x64/x86、Windows SDK；使用 VS 界面还需“适用于 Windows 的 C++ CMake 工具” |
| [标准 Windows CPython](https://www.python.org/downloads/windows/) | **3.12 x64**，建议同时安装 Python Launcher，以便 `py -3.12` 可用 |

不需要安装 Intel C++/Fortran 编译器、Guile、MinGW、MSYS2 或 Bash。项目脚本会安装固定版本的 CMake、Ninja、SWIG 和 Python 科学计算包。

本次验证的工具集是 MSVC **14.37.32822**、Windows SDK **10.0.22621.0**、CPython **3.12.0 x64**。其他电脑应保持 VS2022、Windows x64 和 CPython 3.12；需要进一步接近本机工具链时，在 VS 安装器的“单个组件”中安装相同工具集和 SDK。每台电脑的实际版本记录在环境报告中。

## 2. 第一次配置：执行一个脚本

先克隆开发分支（也可复制或解压本移植版本的完整源码），在项目根目录打开 PowerShell：

```powershell
git clone --branch development https://github.com/sunqiao520/meep.git
cd meep
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/setup.ps1 -InstallOneMKL
```

脚本会依次：

1. 下载固定版本的 Intel 官方离线安装包，核对 SHA256 和 Intel 数字签名，再安装独立 SDK；已安装相同版本则跳过。
2. 创建项目 `.venv`，安装 `requirements-windows.lock.txt` 中的固定依赖；旧环境中的 pip 版 MKL 会被移除。
3. 生成本机的 `windows.local.json`，保存 SDK 路径。
4. 检查 VS2022、Python、SDK 和依赖，保存 `build/windows/environment-report.json`。

Intel 安装步骤可能弹出 Windows 管理员确认。`-InstallOneMKL` 使用 Intel 安装器的静默模式并接受其许可条款；默认安装到：

```text
C:\Program Files (x86)\Intel\oneAPI\mkl\2025.3
```

版本、下载地址及 SHA256 固定在 [tools/windows/dependencies.json](tools/windows/dependencies.json)。安装参数依据 [Intel 安装文档](https://www.intel.com/content/www/us/en/docs/oneapi/installation-guide-windows/2025-1/command-line-options.html)。SDK 安装不会给当前项目切换编译器，项目继续使用 MSVC。

已有独立 SDK 时无需再次安装：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/setup.ps1
```

Python 或 SDK 装在自定义目录时，一次性指定：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/setup.ps1 -PythonExe "D:\Python312\python.exe" -MklRoot "D:\Intel\oneAPI\mkl\2025.3"
```

`windows.local.json` 是本机配置，不应复制到其他电脑。共享的 CMake 预设中没有本机盘符、用户名或 SDK 绝对路径。

## 3. 编译与测试

第一次建议先构建 Debug，方便后续设置断点：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/build.ps1 -Configuration Debug -Fresh
```

日常增量构建省略 `-Fresh`。其他常用命令：

```powershell
# Release 构建及回归测试
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/build.ps1 -Configuration Release -Test

# 优化构建，同时保留调试符号
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/build.ps1 -Configuration RelWithDebInfo

# 生成 Release Python wheel
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/build.ps1 -Configuration Release -Wheel

# 重新检查环境
.\.venv\Scripts\python.exe tools/windows/doctor.py
```

`-Test` 执行 CTest、115 项上游基础 Python 测试和 5 项 Harminv/MPB 等专项测试。Debug 下会排除耗时的 PML 收敛测试；需要包含该项时使用 `-FullTest`。Release 下的 `-Test` 包含 PML。
慢速机器可通过 `-TestTimeoutSec 1800` 调整单项 CTest 的时间上限，默认 600 秒。

`-Fresh` 让 CMake 重新生成配置缓存，用于更换 SDK、Python、工具集，或从旧版移植环境迁移；不删除源码。并发数默认 4，可加 `-Jobs 8`。

需要运行 `.ipynb` 示例时，另执行 `tools/windows/setup_notebook.ps1` 安装固定版本的 Notebook 依赖并配置内核、Meep 路径和 FFmpeg；完整步骤见 [调试指南第 8 节](WINDOWS_DEBUG.md#8-vs-code-运行-jupyter-notebook)。这部分依赖是可选的，不影响只运行 `.py` 的基础环境。

## 4. 在 VS2022 中打开和构建

1. 在 VS2022 中“打开文件夹”，选择项目根目录。
2. 配置下拉列表选择 **Windows x64 Debug**。日常优化调试也可选 **Windows x64 RelWithDebInfo**。
3. 等待 CMake 配置完成，再生成项目。
4. 选择启动目标 `meep_debug_example.exe`，按 F5；完整断点步骤见 [调试指南](WINDOWS_DEBUG.md)。

如果添加预设前已打开文件夹，关闭并重新打开以刷新配置列表。从旧 pip SDK 版本迁移时，执行一次“删除缓存并重新配置”，或者使用上一节的 `-Fresh` 命令。

VS 可能在 IDE 数据库中另行记住旧的 `-DMKL_ROOT=.../.venv/Library` 参数；仅删除 CMake 缓存也可能再次传入它。当前配置会识别并忽略这类 Python SDK 参数和 Python SDK 的 `MKLROOT` 环境值，继续查找独立 SDK，并把最终路径写回缓存。日志中的 `Ignoring legacy Python MKL_ROOT ...` 表示已执行迁移。显式指定的非 Python SDK 路径仍优先使用，并执行完整性和版本检查。

本机 SDK 位置来自 `windows.local.json`；如该文件中的路径错误，可重新运行 `tools/windows/setup.ps1 -MklRoot "<独立 SDK 目录>"`。配置成功时，输出中的 `Meep standalone oneMKL` 应指向 Intel 独立安装目录。不要修改或删除正在运行的 VS 数据库来修复此问题。

VS 和命令行脚本使用同一组 [CMakePresets.json](CMakePresets.json)，输出位置一致：

| 配置 | 输出目录 |
| --- | --- |
| Debug | `out/build/windows-msvc-debug/` |
| RelWithDebInfo | `out/build/windows-msvc-relwithdebinfo/` |
| Release | `out/build/windows-msvc-release/` |

旧版 `build/windows` 中的编译产物不再作为开发入口；该目录同时保留历史记录和本轮验证日志。

Debug 使用 `/Od` 和调试符号；各配置统一使用 **`/MD`**，与标准 Windows CPython 保持运行库兼容，不需要调试版 Python。wheel 安装不提供开发用 PDB；调试源码时使用上述构建目录。

## 5. 运行当前构建的 Python 包

从 Debug 构建运行最小算例：

```powershell
.\.venv\Scripts\python.exe tools/windows/run.py --preset windows-msvc-debug python examples/windows/debug_simulation.py
```

使用 Release 时将预设名改为 `windows-msvc-release`。`run.py` 设置子进程的 MSVC、独立 SDK 和 Python 包路径，不修改全局 PATH。算例会打印实际加载的 `meep` 路径，应位于所选预设的 `out/build/.../python/meep` 中。

单独执行集成验证：

```powershell
.\.venv\Scripts\python.exe tools/windows/run.py --preset windows-msvc-debug python tools/windows/smoke.py
```

该验证运行 PML 仿真、检查场数组、写出 HDF5 并用 h5py 读取、求解均匀介质 MPB 模式，还会打印进程实际加载的 MKL DLL 路径。

安装 wheel：

```powershell
python -m pip install .\dist\pymeep-1.35.0+msvc2-cp312-cp312-win_amd64.whl
```

wheel 内含所需的顺序 CPU MKL DLL 和许可证，使用者无需安装开发 SDK；需要 Windows 的 VC++ x64 运行库。开发机的原生算例也会在可执行文件旁暂存 MKL DLL，以便直接从 VS 启动。

## 6. 把环境迁移到其他电脑

优先通过上面的 GitHub 克隆命令获取源码。需要离线交付时，可以生成源码压缩包：

```powershell
.\.venv\Scripts\python.exe tools/windows/export_source.py
```

生成 `dist/meep-windows-msvc2-source.zip` 及 SHA256 文件，包含本项目的移植源码、第三方源码、预设、脚本和文档。新电脑解压后按第 1、2、3 节执行即可。

不要搬迁 `.venv`、`.venv-wheel`、`out`、`build`、`.vs` 或 `windows.local.json`。Python 虚拟环境、CMake 缓存和调试数据库包含创建时的机器路径，应在新电脑重新生成。

若新电脑无法联网，先在开发机准备离线缓存：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/prepare_offline.ps1
```

除源码压缩包外，再携带：

- `.cache/installers/intel-onemkl-2025.3.0.460_offline.exe`
- 完整 `.cache/wheelhouse/`，包括 `sha256.json`
- VS2022 和 CPython 3.12 的安装介质，供未安装基础软件的电脑使用。

在新项目中保持缓存的相对目录位置，然后执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/setup.ps1 -InstallOneMKL -Wheelhouse .cache/wheelhouse
```

Python 依赖会校验本地 wheel 摘要，并通过 `--no-index` 安装；SDK 安装器会使用已经校验的本地缓存。

## 7. 依赖策略与记录

| 内容 | 记录位置 |
| --- | --- |
| Python 构建工具及包版本 | `requirements-windows.lock.txt` |
| SDK 版本、官方安装包和摘要 | `tools/windows/dependencies.json` |
| 本机 SDK 路径 | `windows.local.json`，不提交、不搬迁 |
| 本机 VS、SDK、Python 和包版本 | `build/windows/environment-report.json` |
| 某次 CMake 构建实际使用的路径和版本 | 对应输出目录的 `meep-build-info.json` |
| 上游源码版本及原始归档 SHA256 | `UPSTREAM_SOURCES.json` |

oneMKL 固定为 **2025.3.0 / LP64 / sequential / dynamic**。CMake 从同一 SDK 取得头文件、链接库、运行 DLL 和许可证，并拒绝 `.venv` 中的 SDK 路径。自行升级版本时应一并更新依赖清单并重新运行数值验证。

复现以相同平台、固定依赖和数值容差为依据。不同 CPU 或编译器下不要求浮点结果、PDB 或 wheel 摘要逐字节一致；需要比较环境时，先对照两台电脑的环境报告。

## 8. 常见问题

| 现象 | 处理 |
| --- | --- |
| 找不到 `MKLConfig.cmake` | 运行 `setup.ps1`，确认安装的是独立开发 SDK，并查看 `windows.local.json` |
| 提示 MKL 路径属于 Python 环境 | 旧 CMake 缓存仍指向 pip SDK；使用 `build.ps1 -Fresh` 或 VS 重新生成缓存 |
| SDK 版本不匹配 | 安装固定的 2025.3.0，避免把 `latest` 自动升级当作同一环境 |
| Python 版本或 NumPy 不匹配 | 运行 `setup.ps1 -PythonExe <3.12 x64 python.exe>`，再用 `doctor.py` 检查 |
| 找不到 Ninja/SWIG | 运行 `setup.ps1` 安装项目工具；无需修改系统 PATH |
| `_meep.pyd` 无法写入 | 结束加载它的仿真 Python 进程或调试会话，再生成 |
| 调试运行的是旧包 | 检查算例打印的 `meep.__file__`；通过 `run.py --preset ...` 运行当前构建 |

## 9. 当前功能范围与验证记录

已接入串行双精度 Meep、libctlgeom、HDF5、Harminv、MPB 核心、本征模源和模式分解。MPI、OpenMP、Scheme、GSL/GDS 和独立 `meep.mpb.ModeSolver` 尚未接入，完整伴随优化矩阵未验收。

本轮独立 SDK 的构建、测试与打包日志：

- `build/windows/standalone-setup.log`
- `build/windows/standalone-release.log`
- `build/windows/standalone-debug-build.log`
- `build/windows/standalone-debug-tests.log`
- `build/windows/standalone-wheel-smoke.log`

本轮结果：Release CTest **10/10**；基础 Python 测试 **114 通过、1 项 MPI 跳过**；专项 Python 测试 **5/5**；Debug CTest **9/9**（排除耗时 PML）；wheel 在无 SDK PATH 的独立环境中验证通过。原生 Debug 算例也在仅有 Windows 系统 PATH 的环境下直接运行通过。

另将源码压缩包解压到 `build/repro/Meep Source`，在该含空格的路径中新建 `.venv`，使用离线 wheel 缓存安装依赖、重新编译 C++ 算例和 Python 扩展，并通过数值后端、原生算例和 Python 集成三项验证。该检查使用同一台 Windows 电脑，尚未替代另一台物理电脑的硬件验收。记录见 `build/windows/repro-setup.log`、`repro-build.log`、`repro-tests.log`。

整体移植路线和后续范围保留在 [WINDOWS_PORTING_PLAN.md](WINDOWS_PORTING_PLAN.md)。

### 几何随机压力检查的已知问题

为使日常回归可重复，CTest 的 prism 测试固定 `LIBCTL_TEST_PRISM_SEED=1`，保持原有断言和容差。额外随机输入检查发现 libctl 4.7.1 的近边界分类可能给棱柱增加一个交点；4 个复现种子及一个完整失败输入保存在 `tests/windows/prism-random-cases.json`。该问题发生在未依赖 MKL 的几何代码中，本轮保留其算法，未宣称这些随机压力用例已修复。

单独复现其中一个压力用例：

```powershell
$env:LIBCTL_TEST_PRISM_SEED = '1792200798'
& .\out\build\windows-msvc-debug\ctlgeom_test-prism.exe
Remove-Item Env:LIBCTL_TEST_PRISM_SEED
```

该压力用例预期会报告线段差异；测试程序现在会打印种子和失败输入，便于后续独立修复。
