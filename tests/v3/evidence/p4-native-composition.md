# P4 NX2506 构造与约束证据

## 交付

P4 使用 P3 的 235 源面责任账和 161 节点构造计划。默认及关联候选由 [NX2506 组合编译器](../../../src/nx_sketch_mcp/v3/nx2506_composition.py) 生成。关联候选包含 88 组事务、2016 步、1841 条原生表达式声明或公式。每组按现有授权、修订、prepare、execute、get 和 fresh verify 调用。NX 原生历史以持久逻辑属性标记节点，同会话的快照几何保全用原生 Tag 比对，并核验未参与布尔的实体测量值。整件候选保留 `execution_approved=false`。

[stock](../../../src/nx_sketch_mcp/v3/nx2506_stock.py)、[C5](../../../src/nx_sketch_mcp/v3/nx2506_c5.py) 和 [头部](../../../src/nx_sketch_mcp/v3/nx2506_head.py) 共享轴径、口面和 stock 包络。原生模块创建关联直线、三点圆弧、Studio Spline、回转轴、有限拉伸和回转，并通过现有布尔工厂核对输入与输出。关联截面由表达式点和原生曲线特征组成。圆截面采用原生中心重合与 Driving 半径。

C# 产物构建于 NX2506.1700，使用 `tools/build-m2-bridge.ps1` 和隔离目录 `workspace/build/v3-p4-c13`。构建输出见 [C13 日志](../../../workspace/v3/p4/P4-20261118-16/build.log)。定向检查使用项目已有 Python 环境，覆盖新组合编译、C5、头部和既有执行器、块体桥、F17/F20/F21 协议，结果为 **58 passed，157 subtests passed**。

## 实机结果

整件运行工作目录为本仓库根，已打开独立毫米 fixture，隔离运行编号 P4-20261118-17。实际执行命令如下。

```powershell
python -B tests/v3/composition_cases/run_native_once.py workspace/v3/p4/P4-20261118-17 --case full --save
```

| 编号 | 范围 | 观察 |
| --- | --- | --- |
| P4-20261118-01/02 | 圆截面和表达式拉伸 | 中心重合与半径 Driving，后续计算为 WellConstrained、0 DOF。5 mm 半径生成直径 10 mm、深 10 mm 的圆柱。旧 M2 编辑入口拒绝编辑具有派生式依赖的半径，prepare 结束时未派发模型写入。见 [圆柱结果](../../../workspace/v3/p4/P4-20261118-02/native-02/summary.json)、[拒绝证据](../../../workspace/v3/p4/P4-20261118-02/native-02/0014-response.json)。 |
| P4-C5-STUDIO-01 / P4-C5-FIN-01 | Studio Spline API 探针 | 原始 F0002 基底和 F0024 的 clamped FIN 各通过一次表达式控制点更新。NX 回读显示四阶、实际节点、实际控制点和原生使用者。后者保留接近端点的短跨度。见 [原基底](../../../workspace/v3/p4/P4-C5-STUDIO-01/result.json)、[FIN](../../../workspace/v3/p4/P4-C5-FIN-01/result.json)。 |
| P4-EXPR-UNITS-01 / P4-CURVE-ASSOCIATION-01 | NX 表达式与共享点探针 | Radians、长度量纲的乘积平方根及弧度三角函数实测。修改共享端点与弧中点表达式后，关联线段及圆弧均更新，更新错误数为 0。见 [量纲](../../../workspace/v3/p4/P4-EXPR-UNITS-01/result.json)、[曲线更新](../../../workspace/v3/p4/P4-CURVE-ASSOCIATION-01/result.json)。 |
| P4-20261118-09 | P3 默认首个成员组合 | 22 边 stock 回转、首翼直拉伸、roll 回转、保留 stock 求交、刀具求并、尾槽减料和首翼减料均通过，终态单实体，已安全归还。见 [运行摘要](../../../workspace/v3/p4/P4-20261118-09/native/summary.json)。 |
| P4-20261118-13 | P3 关联 stock 与第一成员组合 | stock 22 边原生表达式点、两条 FIN 样条及封闭曲线、roll 两点轴、stock 起始站位与尾槽宽/半径均进原生产品链。实际 stock 保留求交、合并和减料通过 fresh 核验，终态单实体，状态 HUMAN_OWNED。见 [驱动 stock](../../../workspace/v3/p4/P4-20261118-13/native/0028-response.json)、[驱动刀具](../../../workspace/v3/p4/P4-20261118-13/native/0064-response.json)、[运行摘要](../../../workspace/v3/p4/P4-20261118-13/native/summary.json)。 |
| P4-20261118-15 | 原生头部组合 | 六个轴向件、18 个环面切块、头部求并及在 stock 上减料通过。首次保存前检查因部分空间曲线几何重合而拒绝。见 [头部布尔](../../../workspace/v3/p4/P4-20261118-15/native/0261-response.json)、[保存拒绝](../../../workspace/v3/p4/P4-20261118-15/native/0275-response.json)。 |
| P4-20261118-16 | 关联首翼、尾槽与完整头部保存重开 | 使用每条 V3 轮廓曲线的持久逻辑标识和完整几何比较，圆弧、线段及精确 FIN 样条一并保存重开。expression、geometry、history、associations 均 VERIFIED，已安全归还。见 [保存结果](../../../workspace/v3/p4/P4-20261118-16/native/0383-response.json)、[运行摘要](../../../workspace/v3/p4/P4-20261118-16/native/summary.json)。 |
| P4-REGEN-01/02 | 新会话打开独立保存副本进行定向编辑 | 尾槽宽 5.00→5.01 mm，原生拉伸限位 −2.500/+2.500→−2.505/+2.505 mm，实体体积下降。F0002 的 P2 横向坐标 +0.0001 mm，原生实体体积随之改变。两次更新均为 0 错误并保持单实体和 71 面。见 [尾槽再生](../../../workspace/v3/p4/P4-REGEN-01/result.json)、[C5 再生](../../../workspace/v3/p4/P4-REGEN-02/result.json)。 |
| P4-20261118-17 | 22 成员、尾槽与完整头部的默认整件 | 88 组事务全部 fresh VERIFIED。终态为一个实体，218 个内核面，体一致性故障数为 0。expression、geometry、history、associations 保存重开均 VERIFIED。已归还并正常退出。内核面数仅用于库存记录。见 [原生库存](../../../workspace/v3/p4/P4-20261118-17/native/2861-response.json)、[保存重开](../../../workspace/v3/p4/P4-20261118-17/native/3037-response.json)、[归还](../../../workspace/v3/p4/P4-20261118-17/native/3038-response.json)、[退出](../../../workspace/v3/p4/P4-20261118-17/shutdown.json)。 |
| P4-REGEN-03 | 新会话从整件的另一份独立副本编辑共享 C5 控制点 | F0002 的 P2 横向坐标 +0.0001 mm。22 个直拉伸和 22 个 roll 回转输入的 FIN 样条均变化，各样条的最大控制点位移均至少为 0.00009156 mm。两端控制点位移均为 0。更新错误数为 0，单实体和 218 面保持。见 [整件再生](../../../workspace/v3/p4/P4-REGEN-03/result.json)。 |

历史失败保留在同一 P4 工作目录。UF 样条短跨度、活动区间重参数化、NX 重排几何 JournalIdentifier、公共零坐标重复表达式和头部大小写不敏感命名冲突均有失败及回滚记录。保全未关闭，首次已知失败后先停止后续写入。实机运行使用独立的毫米测试件、隔离编译产物、新进程身份和本地命名管道。NX 的现存本地防火墙规则在各次隔离启动前有效。

## 阶段结果（修订 93）

P4 在用户确认的逐件验收范围内完成。新版 NX2506 保存件经历 88 组授权事务、fresh 核验、保存重开及安全归还，并通过 218 面和整件布尔误差验收。104 项驱动有单项实机证据，五个完整原生编辑件分别通过。连续原生全区间证明按用户决定免验。见 [最新版 P4 验收记录](p4-error-and-edit-domain.md#p4-阶段验收修订-93)、[新版默认件](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/fixture/full-result.prt)。

## 历史阶段结果（修订 75）

默认整件已通过 NX2506 独立保存重开，文件为 [full-result.prt](../../../workspace/v3/p4/P4-20261118-17/fixture/full-result.prt)。尾槽宽度和 C5 控制点编辑通过既有 P3 必要检查并在 NX 中再生。必要条件只证明指定候选满足已检查的条件，整件允许编辑域仍为 `not_established`。见 [必要条件输出](../../../workspace/v3/p4/P4-REGEN-03/necessary-domain-checks.json)。

P4 尚缺覆盖整个候选的原生表示及布尔误差证据。P3 默认数学上界为 0.000859 mm，距离 0.001 mm 目标还有 0.000141 mm。形状一致性和保存重开材料属于生命周期证据，不能给这项上界。基于缺失的误差和编辑域证据，P4 保持受阻，关联候选未晋级为可放行。工作停在 P4。隔离会话和 Journal 均已退出。

修订 75 在保持既有整件交付的基础上增加误差实测、样条曲线上界和编辑域结果。见 [P4 补充实证](p4-error-and-edit-domain.md)。
