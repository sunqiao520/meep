# 第三方源码说明

原始上游归档的版本、下载地址和 SHA256 记录在 [UPSTREAM_SOURCES.json](../UPSTREAM_SOURCES.json)。这些摘要对应原始下载文件；仓库中的源码还包含 Windows 移植和以下发布调整。

## HDF5 1.14.6 的测试输入调整

2026-11-03，首次上传时 GitHub 推送保护拦截了上游 `tools/libtest/h5tools_test_utils.c` 中一组 AWS 格式的测试凭据。已通过 HDFGroup 官方仓库的 `hdf5_1.14.6` 固定标签确认原文件与公开上游源码一致。

本仓库将该文件中三组相同的测试凭据替换为 `example-access-key-id` 和 `example-secret-access-key`，并更新对应测试用例名称。输入和预期结果同步替换，保留元组解析和 ROS3 文件访问配置测试的逻辑。未使用推送保护的放行功能。

此文件属于 HDF5 上游工具测试；当前 Meep Windows 构建关闭 HDF5 工具及其测试，不编译此文件。当前仿真验收覆盖 HDF5 核心库的实际读写；本次未额外构建完整 HDF5 工具测试套件。
