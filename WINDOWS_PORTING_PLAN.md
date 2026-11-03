# Meep Windows 原生移植实施指南

更新日期：2026-10-17  
目标：Windows x64 + MSVC + CMake + 标准 Windows CPython 扩展，不提供 Scheme 接口。  
状态：首阶段已实施。MSVC/CMake 串行双精度核心、Python、Harminv、MPB 核心和 CPython 3.12 x64 wheel 已构建并验证；当前使用方法、测试结果和剩余范围见 [WINDOWS_BUILD.md](WINDOWS_BUILD.md)。独立 Linux 基线、另一台 Windows 机器验收及并行功能仍待完成。

当前开发环境已改用独立安装的 Intel oneMKL 2025.3.0，Python 虚拟环境不再安装 MKL SDK。新电脑配置、离线复现及 VS 调试分别见 [配置指南](WINDOWS_BUILD.md) 和 [调试指南](WINDOWS_DEBUG.md)。

## 1. 已确定的技术路线

| 项目 | 决策 |
| --- | --- |
| 运行平台 | Windows x64 原生运行 |
| 编译器 | MSVC，具体工具集版本在环境验证阶段锁定 |
| 构建系统 | 新增 CMake 构建，保留上游 Autotools 文件以便对照和维护 |
| Python | 面向标准 Windows CPython，首阶段固定一个 Python 小版本 |
| Python 绑定 | 复用上游 SWIG 接口和 Python API |
| Scheme | 关闭，不构建 Scheme 前端，不引入 Guile 运行依赖 |
| 几何库 | 保留并移植 libctlgeom |
| BLAS / LAPACK | 使用 Intel oneMKL 的 CPU 接口 |
| FFT | 优先采用 oneMKL FFTW3 兼容接口，保留现有 FFTW3 调用 |
| 整数接口 | 首阶段采用 oneMKL LP64，即 BLAS/LAPACK 使用 32 位整数参数 |
| 数据输出 | 首阶段保留串行 HDF5 |
| 并行 | 首阶段关闭 MPI、OpenMP；完成正确性验证后分别加入 |
| 分发 | 通过 Python wheel 安装，并在干净 Windows 环境验收 |

oneMKL 作为数值计算后端，不替代 Meep、libctlgeom、MPB 或 Harminv 的算法和接口代码。这些组件仍需完成 MSVC/CMake 集成。

## 2. 功能范围与阶段边界

### 2.1 首个可用版本

- 能在标准 Windows CPython 中执行 `import meep as mp`。
- 保持上游基本 Python 使用方式，包括 `Simulation`、几何、材料、源和场数据访问。
- 支持串行、双精度的基本 FDTD 仿真。
- 验证 PML、常见边界条件、DFT/通量监测和 HDF5 输出。
- 支持实际使用到的 Python 材料函数、源函数等回调。
- 能安装 wheel，并在不依赖开发机特殊环境变量的情况下运行。

### 2.2 后续功能

| 功能 | 依赖与实施安排 |
| --- | --- |
| 共振频率、衰减率、Q 值分析 | 接入 Harminv + oneMKL BLAS/LAPACK |
| 本征模源、模式分解及相关模式计算 | 接入 libmpb + oneMKL BLAS/LAPACK + FFTW3 兼容接口 |
| Python MPB 接口 | 增加相应绑定和 Python 模块，并审查跨模块共享状态 |
| 特殊函数相关能力 | 按上游功能检测接入 GSL，验证 Bessel 等相关场初始化功能 |
| 多线程 | 验证 MSVC OpenMP 与 oneMKL 线程层的组合 |
| MPI | 选择兼容 MPI 实现，并验证 Meep、Python 绑定、HDF5 和 FFT 的组合 |
| GDS 导入 | 优先采用 gdstk，并实现到 Meep 几何对象的转换 |

阶段性关闭某个依赖意味着对应功能暂不可用，不代表最终移植已经完整支持该功能。构建记录和验收报告必须列出启用、关闭和未验证的能力。

## 3. 依赖处理方案

| 组件 | 处理方式 | 风险/工作量 | 第一版 |
| --- | --- | --- | --- |
| CPython | 标准 Windows x64 发行版，锁定一个小版本 | 主要是版本、架构和扩展 ABI 匹配 | 必需 |
| NumPy | 使用与目标 Python 匹配的包，提供编译头文件 | 检查 SWIG typemap 和数组接口兼容性 | 必需 |
| SWIG | 使用上游接口，锁定验证通过的版本 | 包装代码生成和头文件解析 | 构建时必需 |
| libctlgeom | 从匹配版本的 libctl 中提取几何库构建，新增 CMake | 必需依赖中优先验证的组件 | 必需 |
| oneMKL | 提供 BLAS、LAPACK、FFTW3 兼容接口 | 调用约定、复数、FFT 布局及线程层 | 数值后端 |
| HDF5 | 使用经过验证的 Windows/MSVC 构建 | 旧 API 兼容、DLL 部署、与 h5py 共存 | 保留 |
| zlib 等 HDF5 依赖 | 由 HDF5 的同一依赖方案管理 | 统一运行库和部署 | 按需 |
| Harminv | 新增 CMake，采用已有 C++ 复数路径，连接 oneMKL | 复数与 BLAS/LAPACK 接口 | 后续 |
| libmpb | 只构建所需库，排除 Scheme 可执行程序，新增 CMake | 独立求解器、FFT 和数值库集成 | 后续 |
| GSL | 可评估 vcpkg 的 MSVC 构建 | 确认启用的具体功能 | 按需 |
| Guile / Scheme | 排除运行依赖；解决源码生成步骤 | 见下一节 | 不构建前端 |
| libGDSII | 不作为新移植的首选依赖 | 上游已标记弃用，改用 gdstk 需要转换代码 | 不纳入首版 |

SciPy、h5py、matplotlib 等 Python 依赖按选定 Meep 版本的实际导入关系整理，验证其 Windows 包与扩展共存。不要把“核心 C++ 可编译”等同于“完整 Python 包可运行”。

### 3.1 libctlgeom 与 Guile 的边界

Python 几何接口仍依赖 libctlgeom，不能因为关闭 Scheme 就删除全部 libctl 相关代码。

libctl 的部分文件由 Scheme 工具生成，例如 `ctlgeom-types.h`、`geom-ctl-io.c`。上游说明正式发行 tarball 包含预生成文件，而从 Git 获取的源码需要额外生成步骤。

推荐流程：

1. 选择与 Meep 匹配的 libctl 版本。
2. 优先使用包含预生成文件的正式发行源码，并记录来源与校验值。
3. 如需修改几何规格或使用尚无生成文件的版本，在可复现的生成环境中更新文件。
4. 将生成文件、生成工具版本及命令一并纳入维护记录。
5. 验证 Windows 日常构建、安装和运行不依赖 Guile。

不要为了去掉生成步骤而重新实现几何算法。

### 3.2 oneMKL 替代 BLAS/LAPACK

MPB 和 Harminv 中的调用需要逐项与 oneMKL 对齐：

- 函数符号、命名规则和调用约定。
- 按地址传参、矩阵列主序和 leading dimension。
- 整数参数宽度。首阶段按 LP64 匹配现有 `int` 参数；LP64 不限制程序运行在 Windows x64。
- 实数/复数精度、复数存储布局、复数返回方式。
- 所需函数及包装入口，包括复数点积和本征值问题。

优先保留已经验证正确的调用结构；确有需要时集中在数值适配层转换为 CBLAS/LAPACKE，避免分散修改求解算法。

使用适合的 oneMKL 预编译库，可以避免为 BLAS/LAPACK 本身另外引入 Fortran 编译器。原 Autoconf 生成的 Fortran 名称映射和包装规则仍需在 CMake 中明确处理。

补充：本次调查中，vcpkg 的 OpenBLAS 配方设置了 `BUILD_WITHOUT_LAPACK=ON` 和 `NOFORTRAN=ON`。未来如果增加 OpenBLAS 后端，应重新检查配方和 LAPACK 来源，不能以安装了 OpenBLAS 作为 LAPACK 已齐全的依据。

### 3.3 oneMKL 替代 FFTW

先使用 oneMKL FFTW3 兼容接口，继续保留现有 `fftw_*` 调用：

- 采用 oneMKL 的 `include/fftw` 头文件，统一链接到选定的 oneMKL 配置。
- CMake 中依据 FFTW3 API 的实际可用性设置功能宏；不能仅按是否存在独立 FFTW 库判断。
- 检查 plan 创建失败；正确配对 `fftw_malloc` / `fftw_free`。
- 遵循 Intel 对 FFTW 包装层的要求，不沿用不适用的 `FFTW_DLL` 配置。
- 确保同一目标中的 FFTW 符号由选定后端提供，避免同时链接重复实现。

兼容层不是原版 FFTW 的完整实现：不支持长双精度 FFT 和部分布局；wisdom 等部分函数为空实现，规划标志的行为也有差异。必须验证实际使用的 API、布局和步长。

MPB 串行源码使用了批量复数 FFT、实数/复数转换和指定 stride/dist 的调用。这些是重点测试对象，目前只有源码层面的可行性判断，尚未确认全部组合可用。

如果某个必需调用无法兼容，先定位具体布局或 API，再决定局部适配、增加原版 FFTW 后端或改用 oneMKL 原生 FFT 接口。不要在没有测量和失败证据时大范围重写 FFT 调用。

MPI FFTW 包装层需要另外构建，且有独立的功能限制。串行兼容验证不能替代 MPI 验证。

## 4. 环境与版本锁定

实施前建立版本清单，至少记录：

| 项目 | 必须记录的信息 |
| --- | --- |
| Meep | tag/commit、获取来源、本地补丁 |
| libctl、MPB、Harminv | 各自版本、生成文件来源和本地补丁 |
| MSVC / Windows SDK | 工具集版本、目标架构 |
| CMake / 构建工具 | 稳定版本、生成器和配置方式 |
| CPython / SWIG / NumPy | 精确版本、解释器路径、架构 |
| oneMKL | 版本、整数接口、链接方式、线程层 |
| HDF5 / GSL 等 | 版本、获取渠道、启用功能、运行库配置 |

建议使用与 oneMKL 文档支持范围一致的生成器开展首轮验证，例如 Ninja + MSVC。Visual Studio 解决方案生成器作为后续单独验证项。

原生目标和相关静态依赖应统一架构及 MSVC 运行库。普通 CPython 的第一轮构建使用 Release，或使用 Release 运行库的 RelWithDebInfo；Debug 配置另外核对 Python、运行库和依赖匹配关系。

本机已有的 Qt MinGW 不作为本方案的默认编译器。依赖来源以版本清单为准，不通过临时追加多个工具链路径来解决链接问题。

## 5. CMake 设计与源码适配

### 5.1 建议目标

以下是拟新增的目标划分，不代表当前仓库已经存在这些目标：

| 目标 | 责任 |
| --- | --- |
| 几何库目标 | 构建不依赖 Guile 运行时的 libctlgeom |
| 数值后端目标 | 集中提供 oneMKL 头文件、链接依赖和相关配置 |
| Meep 核心目标 | 编译求解器和所需几何/数据接口 |
| Python 扩展目标 | 由 SWIG 包装代码生成 `_meep.pyd` |
| 可选 MPB/Harminv 目标 | 分别构建相关功能，明确传递依赖 |
| 测试与安装目标 | 执行对应功能测试，安装 Python 包和运行依赖 |

第一阶段可以将核心和 libctlgeom 静态链接到单个 `_meep.pyd`，减少 DLL 导出接口的维护量。静态链接方式仍须使用与目标 Python 匹配的运行库。

如果后续增加 `_mpb.pyd` 或独立 C++ DLL，必须审查核心、几何库、回调和全局状态的共享方式，再决定是否引入共享 DLL。不要直接将有共享状态的库复制到多个扩展中并默认其行为正确。

### 5.2 配置检测与生成文件

- 从 `configure.ac` 和各级 `Makefile.am` 整理依赖、源文件、条件分支及编译选项。
- 使用 CMake 功能检测和配置模板生成 `config.h`、公开配置头等文件。
- 实现 `sphere-quad.h`、`step_generic_stride1.cpp` 等生成规则，正确声明生成器和输入依赖。
- 将生成文件放在构建目录，支持源码目录外构建和多个配置。
- 为核心、包装代码和使用公开头文件的目标传递一致的精度及功能配置。

**特别注意功能宏语义：** 上游同时使用 `#ifdef HAVE_...` 和 `#if HAVE_...`。对于 `#ifdef` 分支，把关闭功能定义为 `0` 仍会进入该分支。应逐项选择“未定义”或“数值 0”的生成方式，不能机械地将全部宏改成 `#cmakedefine01`。

oneMKL 可通过 `find_package(MKL CONFIG REQUIRED)` 和 `MKL::MKL` 接入。整数接口、线程层和链接方式的参数以所安装版本的 `MKLConfig.cmake` 为准，在版本清单中记录；不要假设不同版本的选项名称和默认值相同。

### 5.3 MSVC 兼容处理

- 检查 GNU/POSIX 接口，例如源码中已有的 `vasprintf` 调用。
- 检查目录创建、文件路径、临时文件、计时和错误处理。
- 检查数学函数、常量、编译器扩展和 C/C++ 语法差异。
- 保留已有效的平台回退；确有需要时新增小范围兼容实现。
- 保持异常、内存分配和释放边界一致。
- 对新增 DLL 边界明确导出符号和所有权约定。

不要通过全局关闭警告、伪造检测结果或删除代码来掩盖实际兼容错误。

### 5.4 建议构建开关

以下命名是设计建议，尚未实现，不能直接当作可执行配置使用：

| 建议开关 | 首阶段值 | 备注 |
| --- | --- | --- |
| `MEEP_BUILD_PYTHON` | ON | 保留现有 Python API |
| `MEEP_BUILD_SCHEME` | OFF | 不构建 Scheme 前端 |
| `MEEP_WITH_MKL` | ON | 统一数值后端 |
| `MEEP_WITH_HDF5` | ON | 保留场数据输出 |
| `MEEP_WITH_HARMINV` | OFF | 后续阶段启用 |
| `MEEP_WITH_MPB` | OFF | 后续阶段启用 |
| `MEEP_WITH_GSL` | 按需求 | 明确对应功能范围 |
| `MEEP_WITH_MPI` | OFF | 单独验证 |
| `MEEP_WITH_OPENMP` | OFF | 单独验证 |
| `MEEP_BUILD_TESTS` | ON | 按启用功能选择测试 |

## 6. Python 扩展和分发

### 6.1 接口构建

- 复用 `meep.i`、NumPy typemap、辅助头文件及上层 Python 模块。
- 使用 CMake 的 Python 查找模块，在同一次查找中请求解释器、`Development.Module` 和 NumPy，核对它们来自同一环境。
- 将编译时功能配置同步给 SWIG，保证包装代码与核心启用的接口一致。
- 安装 `_meep.pyd`、生成的包初始化文件、版本信息及上层模块，不能只复制扩展文件。
- 验证数组形状、数据类型、连续性、复数、引用计数、对象生命周期、回调与异常传播。
- 第一版按选定 CPython 小版本构建 wheel；扩大 Python/NumPy 支持范围时建立对应测试矩阵。

### 6.2 打包

使用 `pyproject.toml` + scikit-build-core 连接 Python 构建与 CMake 安装目标。处理：

- 构建依赖、运行依赖、版本号和 wheel 平台标签。
- oneMKL、HDF5 等需要部署的 DLL，以及目标机器所需的运行库。
- 包内 DLL 位置和加载方式，避免依赖开发机 PATH。
- 关闭功能的可发现性：包应能正常导入，调用未启用功能时给出清楚的结果或错误。
- 与 NumPy、SciPy、h5py 等包同时导入和运行的验证。

如果 Meep 和 h5py 使用不同 HDF5 构建，应验证同时导入及文件互读；不跨不同 HDF5 实例传递原生对象句柄。

## 7. 实施里程碑与验收标准

### M0：获取源码，锁定环境与基线

- [x] 获取 Meep 及所需依赖，固定版本并记录修改位置。
- [x] 确认 libctlgeom 的预生成文件齐全。
- [x] 建立 MSVC、CMake、CPython、SWIG、NumPy 和 oneMKL 的版本清单。
- [x] 运行最小 oneMKL 链接程序，确认 LP64 配置和运行依赖。
- [ ] 使用同版本 Linux/WSL 构建准备数值参考结果；它仅作为验证基线，最终产品原生运行。

验收：环境可复现，依赖来源明确，参考算例及其输入、结果、误差判据已保存。

### M1：libctlgeom 和 C++ 核心

- [x] 新增几何库、配置头和必要生成规则。
- [x] 编译 libctlgeom，运行几何对象和空间判断测试。
- [x] 编译串行 Meep 核心，补齐必要的 MSVC 兼容实现。
- [x] 运行最小 C++ 场传播与 HDF5 输出算例。

验收：核心可执行真实计算；验证程序及交付依赖中无 Guile 运行要求。

### M2：基本 Python 仿真

- [x] 接通 SWIG、Python 开发文件和 NumPy。
- [x] 构建并导入 `_meep.pyd` 和上层 `meep` 包。
- [x] 验证基本仿真、材料、源、PML、数组访问和 Python 回调。
- [x] 验证通量与 HDF5 输出，运行保留上游参考断言的测试；独立 Linux 对照仍待补充。

验收：从标准 Windows Python 运行基本算例；所有启用功能有明确测试结果。

### M3：可安装的基础 wheel

- [x] 新增 Python 打包配置和 CMake 安装规则。
- [x] 处理版本信息、依赖 DLL 和运行库部署方式。
- [ ] 在无开发工具、无额外开发机 PATH 的 Windows 测试环境安装 wheel。
- [x] 在本机独立虚拟环境移除开发 PATH 和 SDK 环境变量验证 wheel。
- [x] 验证与常用 Python 依赖共存及场数据互读。

验收：基础版本可安装、可复现运行，并清楚记录未启用的功能。

### M4：Harminv + oneMKL BLAS/LAPACK

- [x] 新增 Harminv 的 CMake 构建和已有 C++ 复数路径配置。
- [x] 验证所需 BLAS/LAPACK 符号、整数宽度和复数接口。
- [ ] 用已知频率、衰减率的信号验证 Harminv。
- [x] 用 Meep 环形谐振器验证频率、衰减率和振幅。
- [ ] 补充独立信号与 Q 值专项对照。

验收：数值结果满足预先制定的误差标准，wheel 中包含该能力并通过安装测试。

### M5：MPB + oneMKL FFTW3 兼容层

- [x] 新增只构建所需库的 MPB CMake 配置，排除 Scheme 前端。
- [x] 接通 oneMKL BLAS/LAPACK 和 FFTW3 兼容接口。
- [x] 验证三维交错批量原地复数 FFT、本征模源和二维模式分解。
- [ ] 覆盖实际使用的批量 FFT、步长、原地变换和实数/复数布局。
- [ ] 验证本征频率、残差、本征模源和模式分解。
- [ ] 如需 Python MPB 接口，增加绑定，并验证跨扩展共享状态。

验收：目标 MPB 功能与参考结果一致到规定容差，已有基础 Python 测试继续通过。

### M6：线程、MPI 与性能

- [ ] 首先测量单线程基线，再分别测试 oneMKL 内部线程和 Meep OpenMP。
- [ ] 统一规划 OpenMP 运行时和线程数，检查嵌套线程及性能变化。
- [ ] 选择并验证 MPI 实现；Meep、mpi4py 和并行依赖使用兼容的 MPI 组合。
- [ ] 单独构建和验证 MPI FFT 包装层、分布式布局及所需并行 HDF5。
- [ ] 记录进程数/线程数、内存和结果差异，完成多进程安装环境测试。

验收：目标并行组合数值正确、能稳定运行，性能结论有测量依据。

## 8. 数值验证要求

| 层次 | 重点验证 |
| --- | --- |
| BLAS | 实数/复数矩阵运算，复数共轭与非共轭点积 |
| LAPACK | 所需本征值问题、返回状态、残差及参数宽度 |
| FFT | 1D/2D/3D、批量、步长、原地/非原地、实数/复数及归一化 |
| 几何 | 基本体、组合对象、周期对象及业务实际使用的几何能力 |
| FDTD | 场传播、PML、材料色散、边界条件及业务算例 |
| 频域量 | DFT、反射/透射与通量，使用一致的参考归一化 |
| MPB | 本征频率、残差、模式系数；处理相位和简并带来的比较差异 |
| Python | 数组所有权、回调、异常、重复创建和销毁仿真 |
| 分发 | 干净环境安装、依赖加载、文件输出及与 Python 科学计算包共存 |

比较时固定源码版本、网格、材料、源、精度和终止条件。按物理量制定绝对/相对容差，避免要求不同编译器或数值后端结果逐位相同。

FFT 往返测试必须按所采用的变换约定处理归一化，避免重复缩放。除结果比较外，记录 plan 创建、数值库返回状态、内存峰值及重复运行稳定性。

## 9. 维护和交付记录

每个里程碑完成后保存：

1. 精确版本和补丁清单。
2. 可重现的配置、构建、测试和安装命令。
3. 启用/关闭功能清单和测试报告。
4. 关键算例的输入、结果、误差和性能记录。
5. wheel、依赖部署方式及已知限制。

当前目录在编写初始方案前尚无 Meep 源码；现已集成 Meep 1.35.0 及依赖的官方 release 源码，来源与 SHA256 见 `UPSTREAM_SOURCES.json`。本文件保留总体设计；具体构建目标、已验证能力和后续工作以 `WINDOWS_BUILD.md` 为准。

后续实施优先顺序：M0 → M1 → M2 → M3 → M4 → M5 → M6。若业务提前需要某项功能，可调整顺序，但应保持依赖和验收条件明确。

## 10. 参考资料

以下资料在方案讨论中于 2026-10-17 核对。上游 master 和软件包配方会变化，实施时应以锁定版本的文件为准。

- [Meep 安装说明](https://meep.readthedocs.io/en/latest/Installation/)
- [Meep 源码构建和开发说明](https://meep.readthedocs.io/en/latest/Build_From_Source/)
- [Meep configure.ac](https://github.com/NanoComp/meep/blob/master/configure.ac)
- [Meep 核心构建规则](https://github.com/NanoComp/meep/blob/master/src/Makefile.am)
- [Meep Python 构建规则](https://github.com/NanoComp/meep/blob/master/python/Makefile.am)
- [Meep SWIG 接口](https://github.com/NanoComp/meep/blob/master/python/meep.i)
- [libctl 上游说明](https://github.com/NanoComp/libctl)
- [libctlgeom 构建规则](https://github.com/NanoComp/libctl/blob/master/utils/Makefile.am)
- [Harminv 复数实现](https://github.com/NanoComp/harminv/blob/master/harminv-int.h)
- [Harminv 数值库调用](https://github.com/NanoComp/harminv/blob/master/harminv.c)
- [MPB 安装说明](https://mpb.readthedocs.io/en/latest/Installation/)
- [MPB FFT 调用](https://github.com/NanoComp/mpb/blob/master/src/maxwell/maxwell_op.c)
- [oneMKL C/C++ 调用约定](https://www.intel.com/content/www/us/en/docs/onemkl/developer-guide-windows/2023-0/call-lapack-blas-and-cblas-from-c-language-env.html)
- [oneMKL LP64 / ILP64 接口](https://www.intel.com/content/www/us/en/docs/onemkl/developer-guide-windows/2024-0/using-the-ilp64-interface-vs-lp64-interface.html)
- [oneMKL FFTW3 兼容层限制](https://www.intel.com/content/www/us/en/docs/onemkl/developer-reference-c/2025-0/using-fftw3-wrappers.html)
- [oneMKL MPI FFTW3 包装层](https://www.intel.com/content/www/us/en/docs/onemkl/developer-reference-c/2026-0/mpi-fftw3-wrappers.html)
- [oneMKL CMake 集成](https://www.intel.com/content/www/us/en/docs/onemkl/developer-guide-windows/2025-1/cmake-config-for-onemkl.html)
- [CMake FindPython](https://cmake.org/cmake/help/latest/module/FindPython.html)
- [CMake UseSWIG](https://cmake.org/cmake/help/latest/module/UseSWIG.html)
- [CMake MSVC 运行库配置](https://cmake.org/cmake/help/latest/variable/CMAKE_MSVC_RUNTIME_LIBRARY.html)
- [scikit-build-core](https://scikit-build-core.readthedocs.io/en/latest/guide/getting_started.html)
- [vcpkg HDF5](https://vcpkg.io/en/package/hdf5.html)
- [vcpkg GSL](https://vcpkg.io/en/package/gsl.html)
- [vcpkg OpenBLAS 构建配方](https://github.com/microsoft/vcpkg/blob/master/ports/openblas/portfile.cmake)
- [Microsoft MPI](https://learn.microsoft.com/en-us/message-passing-interface/microsoft-mpi)
- [MSVC OpenMP](https://learn.microsoft.com/en-us/cpp/parallel/openmp/openmp-in-visual-cpp?view=msvc-170)
