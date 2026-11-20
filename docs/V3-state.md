# V3 状态与交付

更新时间：2026-11-20 11:25（Asia/Shanghai）。台账修订：131。

**P1～P7 已完成。** T01～T32 已在约定样件及版本范围内验收。2026-11-20 按用户确认的“运行与交付”口径精简项目，保留程序、可重建和安装的桥接文件、用户决定、实际运行依赖、交付物、最终结论和故障摘要。历史报告中部分路径为当时的测试现场，逐调用日志、临时模型、探针和中间构建已清理，无法从本目录完整重放旧验收。

本次从项目移出 47,808 个开发过程文件，约 2.29 GiB，已送入 Windows 回收站。保留 454 个文件，约 67 MiB，统计不含版本库元数据。三个正式双版本交付目录和对应 UG11 包均已核对。

## 使用入口

- [使用说明与模型索引](v3/reference-rebuild.md)列出各次交付的 NX2506、UG11 模型及其脚本包。[参考件](../tests/外球叉.prt)为毫米制单一导入实体，235 面、622 边，0 草图。
- 全局 `nx-sketch-mcp` 的程序版本字段为 0.22.0，本机已安装 V3 开发进度。已登记的全局服务以该项目为证据根目录。程序源码在 `src`，安装和构建入口在 `tools`，默认可安装桥接目录为 `workspace/build/current/M2`。
- `workspace/v3` 中保留的少量历史编号目录也是运行输入，包括 P1/P3 的独立参考副本、冻结的构造计划、区域数学数据和审核记录、P4 编辑窗口与 P6 原生驱动图。其原路径供产品和已验组装器读取。
- 草图优先与命名规则均已进入 MCP 初始化及规划建议。已验外球叉生成路线仍依赖表达式驱动的截面曲线；新输入、不同姿态、版本或特征组织的兼容范围须单独验证。[设计与验收清单](V3-development-checklist.md)

## 阶段结论

| 阶段 | 已接受范围 |
| --- | --- |
| P1 | NX2506 识别参考实体并核对只读保全及工具能力。[读取摘要](../tests/v3/evidence/p1-native-run-index.md) |
| P2 | IR、原生驱动绑定、双版本独立空白件烟测。[评审](../tests/v3/evidence/p2-independent-review.md) |
| P3 | 235 个参考面、七分区、161 个构造节点及用户确认的工程关系形成同源默认计划。[最终计划](../workspace/v3/p3/P3-FINAL-PLAN-01/final-plan.json) · [评审](../tests/v3/evidence/p3-final-plan-review-20261113.md) |
| P4 | NX2506 原生参数件、104 项单独编辑和 5 个实际组合按逐件口径验收。[误差与编辑范围](../tests/v3/evidence/p4-error-and-edit-domain.md) |
| P5 | UG11 11.0.0.33 原生建模、参数入口及 10 文件便携包。[独立包评审](../tests/v3/evidence/p5-t30-independent-review.md) |
| P6 | 三段几何、双端参数、独立编辑保存重开和故障处理。[独审](../tests/v3/evidence/p6-independent-review.md) |
| P7 | 通过真实入口完成同源参考到两版默认件的整链，并在已测原生构造族的异尺寸件恢复 104 项驱动。[最终决定](../tests/v3/evidence/p7-independent-review.md#d02-实物复核与最终决定) |

默认参考↔NX2506、NX2506↔UG11、参考↔UG11 的双向上界依次为 0.0009977719872285103、0.00023513541052663984、0.0009553634232981297 mm，限值 0.001 mm。两端各覆盖 218 个有限面。独立编辑将槽宽从 5.0 mm 改为 5.1 mm，保存后在新进程重开，实测限位 ±2.55 mm。[P7 最终汇总](../workspace/v3/p7/T31-DELIVERY-01/output-acceptance.json)

## 故障与使用边界

- P3 的早期原生读取曾因 dirty 变化而冻结；受限读取修正后才有后续干净样本。[诊断摘要](../tests/v3/evidence/p3-diagnostic-validation.md)
- UG11 的受限 C# 程序集、弧度单位名和关联读回曾导致建件失败；修正后的范围以已验版本为准。[原生运行摘要](../tests/v3/evidence/p5-ug11-native.md)
- 异尺寸实件首读两份样本不同，结果保留为 UNKNOWN。首败未留存两份样本，差异字段仍未知。用户人工核查后仅授权一次新副本诊断，D02 的两份原始读回一致，104 项驱动和 2,016 个步骤与既有案例相符。[首败摘要](../workspace/v3/p7/T31-FAMILY-01/failure-record/post-run.json) · [人工恢复](../workspace/v3/p7/T31-FAMILY-01/failure-record/manual-recovery.json) · [实件结论](../workspace/v3/p7/T31-FAMILY-D02/case-acceptance.json)
- 2026-11-19 NX2506 首次 C# 命名调用未产生建模前的证据，未达到模型操作，保留首败。随后用独立副本通过 Python 入口命名；UG11 使用原生 C# 入口。早期 P7 的一份 UG11 交付副本与当时的验收字节不同，原因未知，该副本、验收原件和后续两次双版本交付都已保留。[首败核对](../workspace/v3/p7/REBUILD-20261119-01/naming/NX2506-01/postcheck.json) · [11 月 19 日交付结论](../workspace/v3/p7/REBUILD-20261119-01/trial-result.json) · [11 月 20 日全局入口交付结论](../workspace/v3/p7/GLOBAL-REBUILD-20261120-01/deliver/验收记录.json)
- 关于较早 V2 回归的缺项和此次运行安装检查，见[测试说明](testing.md)。全局 NX 配置、凭据、正在生效的协调目录及项目外的用户模型均不属于本次清理范围。
