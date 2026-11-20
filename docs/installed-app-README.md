# NX Sketch MCP 安装版

此安装提供 NX2506 桥接和 V3 本机参考件规划。使用 [V3 参考件重建指南](docs/v3/reference-rebuild.md) 前，请先了解其已审样件范围和原生验证边界；既有功能见 [V2 功能边界](docs/V2.md)。MCP 客户端应读取实际连接返回的 `tools/list`，而不依赖固定工具数量。

`app` 是受管程序文件。安装上级目录的 `installation.json.source_root` 明确绑定了原项目：V3 规划、已审证据和默认参考件仍从该项目读取，文件和证据未复制到安装目录。该路径必须保持可用；如果不可用、源文件或安装绑定不一致，V3 相关操作会拒绝运行。安装版 [V3 指南](docs/v3/reference-rebuild.md) 不使用安装目录内不存在的 `workspace/v3`。源项目的完整开发台账与证据请从 `source_root` 下查阅。

更新时，在绑定的项目目录中新建一个空构建目录，使用已安装 NX2506 的路径，例如：

```powershell
$env:UGII_BASE_DIR = 'C:\Path\To\NX2506'
$V3Build = 'C:\Path\To\NewEmptyV3Build'
pwsh -NoProfile -File tools/build-m2-bridge.ps1 -OutputDirectory $V3Build
pwsh -NoProfile -File tools/build-v3-reference-native.ps1 -OutputDirectory $V3Build
pwsh -NoProfile -File tools/install-local.ps1 -BuildRoot $V3Build
```

安装器要求现有 `installation.json`、匹配的 `source_root` 和完整构建制品；会先验证暂存程序的 V3 规划及 UG11 导出，再更新受管文件。显式指定 `-CleanReplace` 时，它删除整个旧 `app` 并移动已验证的新 `app`，不备份或自动恢复旧版；安装根下的配置、token、sessions 和 Journal 协调目录保留。删除开始后出错须保留暂存并调查。它不创建 MCP 注册，不更改私有配置或 token。启动或更新前应保存并退出 NX、Journal 和 helper；更新后重新连接 MCP。离线检查不等于原生执行、几何验证或全版本兼容。

已导出的 UG11 包可在独立目录中按其自身 README 使用，不需要安装版或源项目。
