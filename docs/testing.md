# 验证与保留范围

精简后的项目保留安装回归、产品运行自检、最终验收报告与已知故障摘要。可从项目根执行以下离线检查。第一条测试在独立临时安装中验证安装、拒绝条件和失败处理；第二条验证本机安装的 V3 计划与 UG11 独立包导出。

```powershell
python -B -m unittest discover -s tests/installation -p test_install_v3.py
python -I -B tools/verify-installed-v3.py "$env:USERPROFILE/.codex/nx-sketch-mcp/app"
```

2026-11-20 清理后，安装回归 10 项通过。从本机实际登记的全局 STDIO 命令发现 51 个工具，指定参考件返回 88 个构造组，导出 10 个 UG11 文件。另对保留的区域及参数数据核对 235 面对应和同族案例 104 项驱动，重新编译了四个托管制品和一个原生 DLL。该轮为离线检查，未启动 NX。

**历史边界。** 较早的 V2 本地框架与单位转换子集分别通过 7、4 项；当时全量 M2 结果为 355/356，`M3RectangleContractHarness` 仍反射已移除的 `ValidateRectangleCorners`。F21 inventory 也依赖当时的 EXE 和 JSON。按用户选择清理了旧矩阵、临时测试件及原始日志，不能据此宣称历史全量回归通过。

实机操作继续要求独立副本、授权、串行和正常归还。历史实机验收摘要和故障记录见[V3 台账](V3-state.md)，测试数值的适用范围见[V3 交付说明](v3/reference-rebuild.md)。
