# NX Sketch MCP 本机安装

此目录是已经配置的 NX Sketch MCP 安装。当前程序包含 V2 与 V3 接口；以客户端连接后实际发现的工具列表为准。使用方法见 [安装版说明](app/README.md)、[V3 参考件重建指南](app/docs/v3/reference-rebuild.md) 和 [V2 功能边界](app/docs/V2.md)。

安装不携带参考 PRT、完整证据工作区或私有配置。V3 参考件识别、已审方案重建和 UG11 包生成需要持续读取本机 `installation.json` 的 `source_root` 所指项目及其已审证据；源目录移动、删除或不一致时相关操作会拒绝执行。导出的 UG11 便携包按照包内说明运行，不再需要该源项目。

更新前保存并正常关闭 NX、Journal 和 helper，断开正在使用此安装的 MCP 客户端。安装器不终止进程、不热替换 DLL、不改变私有配置、token 或授权。运行已绑定项目的 `tools/install-local.ps1`；可用 `-BuildRoot` 指向一个包含四个托管制品和 `ReferenceGeometryNative.dll` 的完整构建目录。省略时使用项目 `workspace/build/current/M2`，缺少任一制品即停止。完整命令及准备步骤见 [安装版说明](app/README.md)。更新后重新连接客户端；离线安装检查不构成 NX 原生运行或几何验证。显式指定 `-CleanReplace` 会先验证暂存程序，再删除整个旧 `app` 并部署新 `app`，不备份或自动恢复旧版；安装根的配置、token、sessions 和 Journal 协调目录保留。删除开始后若出错，应保留暂存并调查，不能自动重试。

若操作结果为 UNKNOWN，停止并调查，不重放或自动解除冻结。
