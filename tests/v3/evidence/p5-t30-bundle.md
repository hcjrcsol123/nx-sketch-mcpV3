# T30 独立交付包验收

交付目录为 [UG11](../../../workspace/v3/p5/T30-DELIVERY-01/UG11/)，复制时包含目录中的全部 10 个文件。Windows 上的默认预检、参数文件示例、指定不同安装目录和结果目录的方法见[包内使用说明](../../../workspace/v3/p5/T30-DELIVERY-01/UG11/README.md)。

## 输入和范围

导出端使用 T24 已验的 P3 数学计划、能力 profile 与实际编译器。包内 IR 记录 ABS 毫米坐标系、七个区域中 235 个源面的逻辑对应、161 个构造节点、10 项设计决定的逻辑标识、2,016 个编译步骤和驱动消费映射。参数表列出 104 项独立尺寸的默认值、单位及含端点的已证范围。槽轴 Z 位置使用 P6 核实的 mm 单位。接收电脑用 Python 3.10+ 标准库即可生成参数化 Journal；包内文档另外列出实际运行所需的 Windows、PowerShell 和匹配的 UG11 环境。[逻辑 IR](../../../workspace/v3/p5/T30-DELIVERY-01/UG11/logic-ir.json) [参数表](../../../workspace/v3/p5/T30-DELIVERY-01/UG11/parameter-schema.json) [运行时 profile](../../../workspace/v3/p5/T30-DELIVERY-01/UG11/profile.json)

T24 的实机建模、目标版本与保存重开证据，以及 P6 的几何、编辑、持久性和失败处理证据按其原有范围继承。正式产品入口和复制包首次在实际空白 UG11 会话建件归 T31。本轮执行到参数生成、预检及 C# 静态编译为止。[T24 原生及收尾记录](p5-ug11-native.md) [P6 独立验收](p6-independent-review.md#最终决定)

## 最终实物和验证

从仓库根导出时使用下列命令，输出父目录已存在。目标目录由导出器独占创建。正式包只包含交付文件，测试程序、日志、编译产物均在包外。参数版的 C# Journal 只使用当前会话对象，历史源 PRT、开发机绝对路径和会话凭据未打入包。[导出输出](../../../workspace/v3/p5/T30-VERIFY-01/export-final.txt)

~~~powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -B -m nx_sketch_mcp.v3.export_bundle --root . --plan workspace/v3/p3/P3-FINAL-PLAN-01/final-plan.json --output workspace/v3/p5/T30-DELIVERY-01/UG11
~~~

- **复制与参数一致性**。在仓库外的临时目录复制全部文件，并从另一个工作目录用隔离的 Python 3.14.7 执行。实际交付的默认 journal.cs 与 T24 已验收的常规建模 Journal 逐字节一致。槽宽 5.01 mm 的版本经包内参数入口生成，并对照实际参数、C# 内容及清单。临时目录在检查后释放。[迁移验证程序](../../../workspace/v3/p5/T30-VERIFY-01/verify_transfer.py) [实际命令、环境与结果](../../../workspace/v3/p5/T30-VERIFY-01/transfer-final.json)
- **真实安装预检与静态编译**。从上述复制目录调用启动器的默认预检，选中本机 NX11 安装。检查通过且预留结果目录未创建。随后按 NX11 Journal 的受限程序集组合，用 .NET Framework 4 的 csc 编译非默认脚本为库，退出码 0；未加载该库。启动器的原生阶段仍须在未来运行中核实实际加载身份、操作记录、关闭和输出。所用程序集与准确命令均已记录在[迁移结果](../../../workspace/v3/p5/T30-VERIFY-01/transfer-final.json)。
- **拒绝与输出保全**。8 项定向离线测试全部通过，覆盖默认和非默认与 T24 对照、缺计划或运行依赖、错误版本或语言、无效/越界/重复参数、参数与脚本错配和输出占用。[测试](../test_export_bundle.py) [最终原始输出](../../../workspace/v3/p5/T30-VERIFY-01/offline-final.txt)

开发初测曾出现有效参数被误拒，以及建议记录保留历史快照标识和仓库路径。相应检查现已修正，负例及迁移对照覆盖这些问题。版本字段和单个文件存在不足以确认参数与 Journal 匹配，最终版会按当前参数重新生成预期输入并核对。既有 T24 模板增加了导出用替换位置，常规生成路径沿用；编译器与设计建议的既有 15 项离线回归通过。最早一次导出的候选保留在验证目录，唯一对外交付目录为本页顶部链接。[导出实现](../../../src/nx_sketch_mcp/v3/export_bundle.py) [独立评审](p5-t30-independent-review.md)

