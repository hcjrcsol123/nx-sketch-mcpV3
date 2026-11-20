# P7 独立评审

## T31 首次复核，2026-11-19

| 级别 | 影响与现有证据 | 关闭条件 |
| --- | --- | --- |
| 阻塞整链验收 | `analyze_current_reference` 消费当前读取并返回未确认候选。旧 P3 计划可为同一磁盘输入提供已审构造，但实机绑定、生成的整件计划及 NX2506 新保存件仍需串联。两个会话中的 Tag 或数组序号不能标识同一个面。 | 将实读绑定到当前清洁的受控源副本、选体、会话与版本，记录当前源驱动的识别或有证据的计划重建。把生成计划、实际授权建模及保存重开输出逐一对应。[服务入口](../../../src/nx_sketch_mcp/v3/service.py) [磁盘来源绑定](../../../src/nx_sketch_mcp/v3/reference_evidence.py) |
| 阻塞几何验收 | T26 三段几何界绑定于特定旧保存件。新 UG11 输出的 218 面、562 边、相同脚本及同次重开证明的各项一致性仍允许局部几何差异。每向 0.001 mm 的目标中，旧参考至 NX2506 仅余约 0.000002228 mm。 | 提供新旧件全边界、材料侧及 ABS 毫米坐标等价证据，或证明每件双向附加误差并在各段未用余量内合成。对新件的参数、持久性证据分别建立适用关系。[旧证书](../../../workspace/v3/p6/T26-UG11-01/three-link-bounds-r2.json) [迁移评估](../reference_chain/geometry_equivalence.md) |
| 阻塞 T31 泛化与建议验收 | 当前载体候选可量取槽宽、半径和位置；合成快照、对旧库存改数或改名均无法独立证实同族实物上的产品行为。普通库存路径的建议 actions 为空。 | 对真实同族异尺寸或姿态件经产品入口实读，记录自动得到的变化量、输入覆盖和执行范围。实录建模前 MCP 建议与适用条件、应保持独立的反例、保留原方案的选择。[识别测试](../reference_chain/test_reference_recognition.py) [槽测试](../reference_chain/test_reference_slot.py) [T31 验收条件](../../../docs/V3-development-checklist.md) |

## 接受的独立 UG11 子链

审阅实机预检、隔离运行器、已执行脚本和原始记录。T31-UG11-01 在仓库外新目录执行正式 T30 包。独立复核逐字节一致的全部 10 个文件、执行副本中的 Journal 和清单。五个已知参考或开发件各有子进程拒读记录，句柄保持到执行完毕。Journal 在毫米空白件中建模，文件创建和重开使用同一个新输出路径。[隔离运行器](../reference_chain/Run-T31-Ug11.ps1) [隔离记录](../../../workspace/v3/p7/T31-UG11-01/isolation-claim.txt) [启动记录](../../../workspace/v3/p7/T31-UG11-01/result/claim.txt)

实机报告 NX V11.0，程序集、文件、产品版本均为 11.0.0.33，界面语言 `simpl_chinese`。独立按清单重建并对齐 2,016 个构造步骤及 4 个保存或关闭步骤的全部 4,040 行有序检查点。保存前与重开后均为 218 面、562 边，Journal 另核对特征身份、表达式及关联。重开读前 clean，读取后 dirty，最后无保存关闭并逐字节保全；终态 PASS、runner 返回 0。标准错误记录成功信息。该证据可用于正式包独立建件、同次保存重开及已知来源隔离。完整 P6 编辑矩阵与三段几何的继承仍按上表复核。[原生记录](../../../workspace/v3/p7/T31-UG11-01/result/native-evidence.tsv) [标准错误](../../../workspace/v3/p7/T31-UG11-01/result/runner-stderr.txt)

**UG11 新件的独立副本编辑和跨进程重开通过。** 两个进程各有六个源路径的独立子进程拒读记录，均返回 0。编辑阶段初始限位 ±2.5 mm，编辑为 5.1 mm 槽宽后为 ±2.55 mm。新进程重开仍为 ±2.55 mm，跨件父子数均为零，最终无保存关闭且磁盘字节保全。独立解码 P6、P7 各自编辑后的快照，595 条特征类型、父关系和驱动登记逐行相同。按表达式名称对齐的 1,841 条记录，其 RHS 与数值全部相同。该证据建立同版同一编辑点上 P6 与新 UG11 产物的参数历史对应。其余编辑用例可按此前真实测试的取值和消费者范围引用，并标明继承。[P7 编辑记录](../../../workspace/v3/p7/T31-UG11-PERSIST-01/edit-evidence.tsv) [新进程重开](../../../workspace/v3/p7/T31-UG11-PERSIST-01/reopen-evidence.tsv) [P7 快照](../../../workspace/v3/p7/T31-UG11-PERSIST-01/snapshot.tsv) [P6 快照](../../../workspace/v3/p6/T28-UG11-01/snapshot.tsv)

**参考件与新 UG11 默认件的整件 G 通过。** 复核八组原生采集、有限裁剪验证器与当前实际输出路径；隔离副本与正式包生成件逐字节相等。NX2506 读取一个正体积、有界、连通闭壳的毫米实体，ABS 框架一致，UF 一致性故障为零，八次采集均记录磁盘副本保全。按证书复计 88 个翼面、44 个根面、38 个头部面、24 个过渡接口、12 个毛坯环带、8 个尾槽面、4 个轴向头部面，218 项各自唯一。相对 P3 的逐面最大双向界 0.00009636342329812967 mm，加上继承的参考至 P3 界，参考与此 UG11 保存件每向不超过 0.0009553634232981297 mm。另两段待新 NX2506 保存件绑定。网络预检记录指定 ugraf 的入站规则，未测 run_journal 对外可达性。[新件库存](../../../workspace/v3/p7/T31-UG11-G-01/observations.json) [采集登记](../../../workspace/v3/p7/T31-UG11-G-01/geometry-witness-complete.json) [UG11 单段证书](../../../workspace/v3/p7/T31-UG11-G-01/three-link-bounds-r2.json)

## 默认参考件、同源计划与交付包

**SOURCE-05 的实读和同源计划对应通过。** 复核产品实际响应、源件/独立副本字节、装载的会话及选择信息。实读来自干净的完全装载件，前后 dirty 均为 false。当前 235 个面与 P1 的 235 个面逐一唯一对应，七个 P3 区域完整。622 条边形成按相邻面与边属性对应的等价类，其中 17 类存在个体歧义，代码保留类内歧义。P3 组装器在锁定文件完全相同时从已审证据重建默认计划，产品为 `head.result` 返回 88 组构造、22 条共享轮廓建议及 1 条圆周布置建议。运行器保留普通库存分析的 planning_only 状态。此结论限于所读取的默认输入及对应计划。[实读与对应](../../../workspace/v3/p7/T31-SOURCE-05/product-source/0008-response.json) [汇总](../../../workspace/v3/p7/T31-SOURCE-05/product-source/summary.json)

**SOURCE-05 收尾日志记录过一次 STOP，已独立核对应归属。** 对应 PID 3564 的正常退出 JSON 已在受控句柄仍持有时写出。随后脚本因仍见相关进程而停止，原始 claim 中的通用异常说明保留。源 PID 于 13:48:18 UTC 正常退出。目标 PID 11864 在脚本两次空闲检查后于 13:48:35 UTC 启动。收尾时短暂存在的进程身份仍未知。独立核对上述时序及源件/副本字节，接受锁覆盖源件实读直至该源进程退出。[保全日志](../../../workspace/v3/p7/T31-SOURCE-05/preload-claim.txt) [专用 NX 退出](../../../workspace/v3/p7/T31-SOURCE-05/shutdown.json) [事后对账](../../../workspace/v3/p7/T31-SOURCE-05/source-reconciliation.json)

经本次 MCP 导出的 10 个文件与前述在实际 UG11 空白会话执行的 10 个文件，独立复查文件名集合和全部内容均完全相等。该核对将产品导出结果与已测的正式包关联，无需重复运行 UG11。[产品导出与执行包对应](../../../workspace/v3/p7/T31-DELIVERY-01/bundle-verification.json)

**NX2506 新件的默认构造及同次保存重开通过。** 独立对账 3,147 次产品调用，88 组的请求及响应索引均连续一致。以操作标识合并轮询后，prepare、execute、fresh verify 各 88 次，另有 1 次 save_copy，265 项的终态均为 SUCCEEDED。逐组几何、历史、绑定和非目标保全均为 VERIFIED，保存重开另核对关联和表达式。全部终态无停写，独立空白件生成新的 `reviewed-result.prt`，安全归还 HUMAN_OWNED，专用 NX 正常退出。启动器曾因窗口就绪判断而停在接管前，恢复记录指向同一专用目标进程；实际产品调用中仅有一次接管、一次保存。[现场继续记录](../../../workspace/v3/p7/T31-TARGET-01/resume-claim.txt) [产品调用原始记录](../../../workspace/v3/p7/T31-TARGET-01/product-target/) [保存件](../../../workspace/v3/p7/T31-TARGET-01/fixture/reviewed-result.prt) [关闭记录](../../../workspace/v3/p7/T31-TARGET-01/shutdown.json)

## 默认件三段 G、双端 P 及持久性决定

**独立接受指定默认件的三段全件 G。** 新 NX2506 保存件与有限面采集件逐字节相同、ABS 毫米框架一致，218 个有限面各自唯一。逐项复计 132 个轴部面、32 个毛坯或尾部面、37 个头部面、1 个圆角面、16 个实际解析裁剪相同的迁移面。每向至 P3 的上界为 0.00013877198722851017 mm。三段各取双向上界，参考↔NX2506 为 **0.0009977719872285103 mm**，新 NX2506↔新 UG11 为 **0.00023513541052663984 mm**，参考↔新 UG11 为 **0.0009553634232981297 mm**，均在 0.001 mm 内。[新件与几何采集绑定](../../../workspace/v3/p7/T31-NX-G-01/default-finite-validation/fresh-output-binding.json) [逐面结果](../../../workspace/v3/p7/T31-NX-G-01/default-finite-validation/corrected-default-boolean-bound.json) [三段合成](../../../workspace/v3/p7/T31-DELIVERY-01/output-acceptance.json)

**独立接受两个新默认产物在 P6 约定编辑点上的证据适用性，以及本次独立副本编辑、保存、跨进程重开。** 新 NX2506 保存件与独立编辑输入逐字节相同。默认、编辑后及重开时均为单个 218 面、562 边有效实体，UF 一致性故障为零。槽宽从 5.0 mm 编辑到 5.1 mm 后，新件实际限位从 ±2.5 mm 变为 ±2.55 mm，体积由 213442.0801041426 变为 213439.88248389785 mm³，新进程重开保留该体积。两次运行各观察到一个加载件及零跨件父子。对齐新旧件编辑前、编辑后和新件重开的 594 个特征及 2,017 条表达式，对应集合与定义相同。UG11 对应的 595 条特征及 1,841 条表达式核对见上文。既有 104 项驱动、单位与有限编辑点按 P6 原有范围继承。0.001 mm 全件界仅覆盖已证明的默认目标。[NX2506 编辑](../../../workspace/v3/p7/T31-NX-PERSIST-01/edit.json) [新进程重开](../../../workspace/v3/p7/T31-NX-PERSIST-01/reopen.json) [P6 参数验收范围](p6-independent-review.md)

## 同族异尺寸实物首败及当时的阶段决定

1. **阻塞 T31／T32。** `p7-family-mixed-20261119-01` 在真实 NX2506 v2506.0.0.1700 中打开具有 104 项非默认驱动的独立件。冻结的 `family-journal.py` 第 192 行比较两个连续 `read(part, ident)` 的完整字典，两个样本使用同一个 ident。权威 `family-observation.json` 报 `native observations differ`，未保存任一样本、差异字段或成功计划。在此之前未进入分类器或有效的几何验证。当前不能确定具体是无序邻接枚举的先后次序、某个数值，还是另一真实读回差异。归档实现的面、边及邻接用列表逐项比较，顺序变化确实足以触发报错；代码与现存日志无法证明当次只发生了顺序变化。最小修正为保留可比较的原始双读与分字段差异，仅对语义无序集合按该次会话的实体身份无损规范化，保留数值及真实拓扑差异门禁。该改动可先离线验证。[MCP 提交](../../../workspace/v3/p7/T31-FAMILY-01/submission.json) [最终 UNKNOWN](../../../workspace/v3/p7/T31-FAMILY-01/product-result.json) [对照用 P4 变体证书](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/corrected-native-mixed-brep/complete-edited-boolean-evidence.json)
2. **阻塞旧操作重新执行。** 双读不等抛出异常后，冻结 Journal 的通用异常分支只保存错误，未执行显式无保存关闭。外层模型观测的 `script_outcome=RETURNED` 表示脚本捕获异常并返回。wrapper 起始为空，结束仍有此次 `source-copy.prt`，dirty=false、419 条曲线、1 个实体、594 个特征；记录的 1,014 个 added 属于打开到该会话的对象集合。监督器据此正确保留 UNKNOWN。独立复核时相关进程已经退出，同时持读锁逐字节比较原 P4 保存件、P7 输入副本和运行副本，三者为不同文件且内容全部一致。此项证明磁盘保全；显式关闭证据和缺失双读仍无法事后补造。应保留该操作记录与 `active.json`，任何后续实机运行先按项目人工恢复程序明确处置该不确定状态。权威脚本、内外层观测及 state 均位于 `%USERPROFILE%/.codex/nx-sketch-mcp/journal-coordination/operations/p7-family-mixed-20261119-01/`。[实机工作目录](../../../workspace/v3/p7/T31-FAMILY-01/) [产品监督器](../../../src/nx_sketch_mcp/v3/family_supervisor.py)

**阶段决定为 T31 的同族实物门禁待验证，T32 暂不能验收。** P4 的同族编辑件可作为独立几何与尺寸对照，已通过的默认件三段 G、双端 P 及持久性仍有效。关闭此门禁需要在允许重新开展实机工作后以新的操作编号恢复出真实变体驱动，验证该操作实际返回的计划与变体的完整数学构造、单位、消费者及已有有限面证据一致。原 UNKNOWN 运行不得用离线合成读数或已知对照尺寸补记成功。

**停止后的离线修正已复核。** 当前源码保留两份原始读回，对比时仅按同一次会话的实体身份整理面、边及其无序邻接成员。数值、向量、限位及公式继续逐项比较。有意义的差异将记录差异总数及首批字段路径；重复身份仍停止。独立核对代码和覆盖顺序变化、数值/向量变化及重复身份的模拟断言。此修正保留了故障定位信息，首次失配的具体字段仍未知。历史证据可在项目内读取。[冻结脚本与权威原始记录](../../../workspace/v3/p7/T31-FAMILY-01/failure-record/) [更新的采集器](../../../src/nx_sketch_mcp/v3/parametric_family_capture.py) [模拟用例](../reference_chain/parametric_family_capture_test.py)

## D02 实物复核与最终决定

**接受 T31 和 T32 指定样件、版本和构造族的交付。** 首败后用户已人工核查现场并明确授权一次新副本诊断。核对操作编号 `p7-family-mixed-20261119-d02` 的权威 state、实际返回值及留存样本，NX2506 v2506.0.0.1700 批处理返回 0，状态 SUCCEEDED，前后会话均为空且无增删改，副本读取前后 dirty=false 并无保存关闭。发布的原始观察与监督器持有的原始观察逐字节一致。两次留存的实际样本在规范化前已完全相同；旧操作具体失配字段仍未知，原 UNKNOWN 和人工处置记录保留。[一次性授权](../../../workspace/v3/p7/T31-FAMILY-01/failure-record/manual-recovery.json) [MCP 结果](../../../workspace/v3/p7/T31-FAMILY-D02/product-result.json) [两份读回、批处理记录及计划](../../../workspace/v3/p7/T31-FAMILY-D02/native/) [最终队列状态](../../../workspace/v3/p7/T31-FAMILY-D02/final-scene.json)

在独立持读锁的三个不同文件上，确认执行副本、重命名的产品输入与已有有限面证书的 P4 编辑保存件内容完全一致。此次从模型读出的槽宽为 5.068 mm，圆柱半径约 37.4976 mm，ABS 轴中点为 (0, −162.6062, 42.0046) mm。产品推断的全部 104 个非默认驱动与 P4 对照值逐项精确相同。独立按 P4 已记录的编辑值重新编译数学目标，核对 MCP 返回计划、受控操作保存计划、交付的 `family-plan.json` 三者内容一致；其全部 2,016 个步骤、161 个构造操作映射、104 个驱动及消费者映射以及最终对象标识均与上述独立编译相同。P4 对该实际编辑件已有 218 个唯一有限面及 218 个材料区域的证明，每向上界为 0.0002470398765667749 mm。此例足以证明经验证的原生构造族可从改名、异尺寸的实际输入恢复完整驱动与计划。几何证据依赖项目已验 P4 记录的历史关联，本次未为变体另行建件。[核对结果](../../../workspace/v3/p7/T31-FAMILY-D02/case-acceptance.json) [已有逐面证书](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/corrected-native-mixed-brep/complete-edited-boolean-evidence.json)

T32 最终接线沿用实测 MCP 入口及原 prepare、execute、fresh verify、save/reopen 门禁。复核使用说明中各命令、参数、来源锁、独立目标及受限的变体返回语义。两个命名 `外球叉_参数化.prt` 分别与相应 NX2506、UG11 实机产物逐字节一致；原封脚本包与实际执行的 10 个文件一致。残余适用限制是默认导入参考的严格同源性、异尺寸件需有已测的原生构造及参数关系、首次读回差异原因未知，以及前述几何界和编辑点各自的作用域。新来源、未知导入 BREP、改变姿态或新的 NX 版本需要针对相应能力补充验证。[最终使用说明](../../../docs/v3/reference-rebuild.md) [产品实测索引](p7-reference-chain.md) [命名交付目录](../../../workspace/v3/p7/T31-DELIVERY-01/)
