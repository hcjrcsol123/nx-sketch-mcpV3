# P2 独立高级评审

评审日期：2026-11-08；评审实例：`/root/review`（高级模型，独立于实现者）。仅评审 P2 的 T06—T12，不授予 P3 开发或整件交付许可。实时任务状态由 TL 独占维护 `docs/V3-state.md`，本文件只保存评审意见与证据适用范围。

最终结论：**P2 独立评审接受，建议 TL 接收 T06—T12 及必要子项 T10.a。无未关闭阻塞发现；R01—R04 均已关闭。** 接受范围为版本化合同、声明性账本、严格限定的块体事务及已实测双版本最小链；不等于参考样件或通用 UG11 产品发布通过。以下分批记录保留当时的条件，最终以末尾 D2 和本结论为准。

## 发现及关闭记录（按严重程度）

### R02 — 高：T10 执行入口忽略能力需求和额外未覆盖区域

- 受影响验收：T10 执行前门禁；清单第 4 节规定遗漏区域/未满足能力不得成为可执行计划。
- 位置：`src/nx_sketch_mcp/v3/nx2506_executor.py:123–147`。
- 机制：`create_block` 校验三个操作、五个参数及 confirmed，但完全不检查 `capability_requirements`，也不检查三个操作是否覆盖了全部计划区域。在有效 fixture 加入未知必需能力，或追加一个 confirmed=true 但未被操作引用的区域，仍会进入 datum/sketch/extrude 写调用。不能将这些声明默默忽略后当作受支持块体。
- 最小关闭动作：对受限 P2 入口明确限定允许的能力需求；拒绝未知能力。要求恰有一个区域，三个操作均使用它。增加这两类输入在任何 transport 调用前拒绝的定向负例，无须实现通用覆盖规划器。
- 状态：已关闭。`T10-EXEC-20261108-C3` 限定已知两项能力及单一区域/全部操作引用；`p2-t10-capability-poll-retest.txt` 的定向 6/6 包含两种反例且断言零 transport 调用。仅复审增量，未重跑原测试。

### R03 — 中：桥层未强制回滚读回证据

- 受影响验收：T09/T10 UNKNOWN/失败门禁。
- 位置：C1 `src/bridge/M2Bridge.cs:4812–4816`；对应 `M2ModelContract.cs` 的 V3 事务合同。
- 机制：桥接受任何 `ROLLED_BACK` 状态字符串并作为普通 FAILED 返回、继续允许后续动作，却没有核对 `rollback_readback_verified`。当前原生实现确实只在完整回滚验证后返回该状态，但损坏或未来实现的 DTO 缺证/false 情况不能被桥拒绝。
- 最小关闭动作：V3 合同明确 UNCHANGED 只允许首个写调用前，ROLLED_BACK 要求回滚读回成功；桥对 ROLLED_BACK 强制布尔 true 证据，否则冻结 UNKNOWN，并用 fake 覆盖 true/false/缺失。
- 状态：已关闭。C2 桥代码/合同修正及独立目录编译已定向核准；继承到 C3 的 C# fake 10/10 含 true/false/缺失证据，前者普通 FAILED，后两者 UNKNOWN 并冻结后续调用。此风险最初由 SI 提出，评审随后独立检查原生及桥代码确认，非评审者冒充首次发现。

### R04 — 中：T12 重开预览后未拒绝语义/修订变化

- 受影响验收：T12 新鲜持久性读回与安全停止。
- 位置：初版 `tests/v3/smoke_plan/run_block_once.py:210–216`。
- 机制：post-prepare session 只检查 owner/epoch/dirty 类型，忽略 revision 和 `semantic_changed_since_previous_read`；若该读回已明确报告模型变化，仍可能使用先前的 before 证据归还并标 PASS。
- 最小关闭动作：要求 post-prepare revision 等于当前 executor revision，语义变化明确 false；dirty 可变化但如实记录。增加语义/修订变化时不归还、不 PASS 的定向负例。
- 状态：已关闭。前后语义字段均须明确 false，后读 revision 必须等于当前值；`P2-RUNNER-R04-RETEST-01` 的 3/3 包含语义/修订变化两个子例，均停止、不归还、不关闭。dirty 变化仍允许记录，没有改成 P1 的只读源件要求。

### R01 — 中：T07 一次运行缺少环境及冻结代码标识

- 受影响验收：T07 的可追溯离线证据；依据 `docs/V3-stage-handoff.md` 第 5 节。
- 位置：`tests/v3/evidence/p2-t07-ir.txt:1–4`；台账修订 9 的 `P2-IR-20261108-C1` 尚标为暂定。
- 后果：已有命令、cwd、7/7 结果及烟测输入说明，但没有本次实际 Python 版本/解释器位置与明确的代码/输入版本绑定，后续无法判断该证据是否适用某次修订。
- 最小关闭动作：基于原运行记录补入人工代码标识、输入 fixture 路径/版本和实际 Python 环境；无需重跑有效的 7 项测试。不计算哈希，不把修改时间或大小当作内容一致证明。
- 状态：已关闭。原测试记录已补 `T07-IR-20261108-C1`、初始数值版 fixture、Python 3.14.7 与 `C:\Python314\python.exe`；增量记录绑定 `T07-IR-20261108-F2` 公式版 fixture。原始结果未重跑。未发现要求重跑 T07 测试的代码缺陷。

## 批次 A1：T07 结构合同

冻结输入由 TL 提交：`src/nx_sketch_mcp/v3/__init__.py`、`ir.py`、`tests/v3/test_ir.py`、`tests/v3/smoke_plan/block-plan.json`、`tests/v3/evidence/p2-t07-ir.txt`。本评审只读源码与既有证据，未运行测试或 NX。

结论：T07 代码及证据审查接受，R01 已关闭。已有一次 7/7 结果可复用。结构合同有版本拒绝、严格字段校验、复制隔离与 JSON 往返、来源/公式/关系保留、未知操作拒绝、参数及操作依赖环检查、量纲检查、显式持久化会话 Tag/JID 字段拒绝。支持域仅为基准平面、矩形草图和 create 拉伸；不能据此宣称其他操作或样件分区已支持。

增量 A1.1：fixture 的 `height` 从独立 20 mm 改为 `width * 2 / 3`，初始值保持 20 mm，并引入明确的关联公式。已审 `p2-t07-formula-fixture-retest.txt` 的两项往返定向复验（2/2），理由与影响范围充分；接受此增量，不要求重跑原 7 项。该公式的原生使用者与宽高联动仍须 T09/T12 证明，R01 的元信息补录同时适用于这份增量证据。

残余风险与待验证接口：

- `Plan` 明确不声明可执行性；未确认区域/操作/关系、开放项、能力要求、未解释区域及参数账本完整性须由 T08/T10 的执行前门禁实际拒绝。
- 公式结构/量纲检查不等于有限数值求值，除零、溢出和几何有效域需在执行前拒绝；需要 T10 适用负例证据。
- 来源逻辑 ID 是声明性语义身份，并不证明已唯一重定位。任何后续原生解析仍须当前会话唯一性校验，不能将逻辑字符串重新解释为旧 Tag/JID。
- mm/m/inch 与刚体坐标转换的执行效果、原生 Driving/使用者、参数编辑与持久性尚不属于此批次证据。

## 批次 A2：T08 参数账本

冻结输入：`src/nx_sketch_mcp/v3/parameter_ledger.py`、`tests/v3/test_parameter_ledger.py`、`tests/v3/evidence/p2-t08-ledger.txt`，人工标识 `P2-LEDGER-C1/C2`。静态审查及已有 6/6 复测摘要接受，无阻塞发现。摘要明确区分首次 3 失败/1 错误、fixture 公式变更引起的测试适配与复测，不伪装完整原始日志；六项共用变更后的 setUp，复测范围有依据。

账本逐项暴露计划参数/区域缺漏、分类/单位/初值/编辑域/越界策略错误、关系双向链接缺漏、未确认记录、来源范围失配和未解释面。它始终返回 `execution_approved=False`，派生量及关系始终列入 `requires_evaluation`，所以合成 235 面候审通过不构成真实样件覆盖或求值通过。

残余风险：供给的 inventory 完整性与确认记录只作声明性核对，实际来源语义、区域解释是否充分、遗漏于 IR 之外的工程尺寸仍须后续识别/人工确认及参数验证；此评审不将账本自洽提升为整件参数完整。T10 不得把 `ready_for_review=True` 当成执行批准，也必须独立拒绝未确认操作、未求值关系及开放项。实际样件缺口继续保留 P3 门禁，本批未实施识别。

## 批次 C1：T06 原生探针

已审 `tests/v3/ug11_probe/T06Probe.cs`、`Run-T06.ps1`、`README.md`、`Test-ReleaseGuard.ps1` 及 `workspace/v3/p2/T06-20261108-01/02/03` 各自的 `native-evidence.tsv`、`claim.txt`。原生代码与 03 成功链接受；下述索引增量已关闭证据补录项，T06 在实测精确版本及本烟测操作域内评审接受，不重跑已经有效的链。

- 01（C1）在建件前错误拒绝原生版本字符串，记录保留；02（C2）在未保存的草图阶段报 1175012，没有伪装为成功。03（C3）对独立固定基准点采用 Midpoint 关联，并逐调用留证；矩形边没有整体 Fix。
- 03 原生记录证明四个 Driving 尺寸、草图 DOF=0、每项有实际 SKETCH 使用者、EXTRUDE 的直接草图父特征，以及一次 solid 创建。`width` 30→36 mm、`height` 20→24 mm、`x` 10→14 mm 的公式与几何响应相符；保存、关闭、重开后重新枚举几何/约束/特征，公式、使用者、状态及尺寸保持。没有跨重开复用旧几何 Tag 来定位。
- 实际观察为 `NX V11.0`、加载的 NXOpen assembly/file/product `11.0.0.33`、C# NXOpen 与独立 `run_journal.exe` 入口。运行门禁只接受该精确对；官方维护包名称保持 unknown，不能从 DLL 版本推断命名维护包或其他 UG11 版本支持。许可只证明本次原生操作实际可运行，不声明具体许可 feature 或 entitlement。
- 包围盒及线端点只用于该已知矩形烟测响应检查，不能替代真实样件全域几何验收；数值门限不是制造公差。

索引补录项（最小动作，无需重测）：记录每次准确命令、C1/C2/C3 改动对应、01/02 失败后及 03 完成后的进程/未保存模型处置观察与原始 runner 日志核查结果，证明后续不是自动重放 UNKNOWN。README 的“未证明”与“C3 未验证”旧叙述须更新为 03 的观察，保留其余真实限制。此处不否认已成立的原生观测，但尚不凭 exit code 宣称安全收尾完整。

增量 C1.1：已审 `tests/v3/ug11_probe/T06-run-index.md`、更新后的 README、`workspace/v3/p2/t06-root-observations.json`，补录项关闭。索引记录各次准确命令/代码改动及原日志检查；root 的观察摘要明确不是原始进程转录，确认每次结束后无残留 NX/Journal/helper，01/02 未保存 PRT，03 正常结束；失败尝试没有自动重放。当前 C3 对应成功证据；C1/C2 未保留源码快照的事实明确，不以人工编号伪装字节身份。官方维护包名称仍未知，但本任务后续 profile 可且仅可采用上述实际运行/加载版本组合，不据此声明全部 UG11 兼容。此次仅审补录，没有重新审查或执行原生链。

## 批次 B1：T09/T10 实机前代码审查

已审新 `V3/ParameterBinding.cs`、M2ModelContract 的 `IV3BlockBindingAdapter`、M2Bridge 的 block prepare/execute/verify 接线、M2OpenModelAdapter 的 V3Block 区块及其调用的历史/关联/表达式投影、Python server/bridge 接线、`v3/nx2506_executor.py`、构建清单新增源文件、绑定 helper fake、executor/protocol 测试和现有离线记录。候选构建日志 `workspace/build/v3-p2-build-c1.log` 成功；这仅证明编译，不代替原生运行。

静态结果：除 R02 外，未发现阻止限定烟测的代码缺陷。原生适配限定当前绑定的毫米正 XY 单块，四个真实 Driving 加 Extrude end 表达式；prepare/execute 检查 revision 与原生几何，execute 用 undo/update/回读及非目标表达式/历史/约束关联保全，失败无法证明回滚则 UNKNOWN。桥将消费的计划绑定到 owner/epoch/session/load，成功后另有 fresh 原生验证；未知结果冻结，不因旧操作结果缓存而自动重放。表达式公式仅允许本次宽高关系，未冒充通用公式编辑器。

已核现有证据：executor 初次 5/5、关联映射/重开预览增量 7/7、Python mocked bridge 3/3。C# 新桥事务的授权/过期版本/未知结果/fresh 门禁尚需 root 已安排的 fake 证据；helper fake 不替代该层。绑定 helper 与编译也不证明实际尺寸或位置能驱动 NX 几何，最终 T09/T10 接收待 T12 原生链。

时序观察：`Executor._operation` 默认最多 100 次轮询且没有间隔，fake 首次成功不证明正常 NX 长操作能在该预算内完成。实机调用前应设置适用预算或补有界等待与延迟完成/耗尽测试；耗尽必须保留停写、不重放语义。此点主要影响可用性，不能以扩大预算掩盖 UNKNOWN。

增量 B1.1：C3 将轮询改为单调时钟 120 秒预算、0.25 秒间隔及最大轮询数，clock/sleeper 可注入。定向 6/6 包含预算耗尽后不重放，并复验成功链、UNKNOWN、fresh 失败受影响路径；此时序意见关闭，真实 NX 时延仍由实机记录体现。

增量 B1.2：C# 首次 fake 全部受 prepare 请求规范化错误阻断，原始失败保留在 `p2-block-bridge-run-c1.log`。SI 的 C3 仅将 `normalized["binding_epoch"]` 设为已验证的 int，防止 JsonNumber 进入 canonical serializer；授权语义未改。定向审此行及 `v3-p2-build-c3.log` 成功记录。已审 `tests/v3/block_bridge_cases/{BlockFake.cs,test_block_bridge.py,run_once.py}` 和 `p2-block-bridge-run-c2.txt/.log`：该一次复测实际绑定 C3 DLL/helper，10/10，覆盖 owner/epoch/revision/显式目标、operation ID 冲突/缓存返回而不重复 execute、计划单次消费、APPLIED 缺读回、执行异常/UNKNOWN、回滚 true/false/缺失、fresh 检查失败/异常的冻结。未运行测试；不是原生几何/回滚实机验证。

实机前结论：R02/R03 已关闭，T09/T10 的 C3 桥候选与 C3 Python executor 可在 root 单一通道、独立空白毫米夹具上开展一次限定烟测。没有未关闭的代码阻塞发现；真实尺寸/位置响应、绑定消费者、保存重开和新会话读回仍须 T12 原生证据后才能完成任务验收。

重开预览只向独立输出件 prepare，不 execute；现有 Capture/ExtrudeBuilder getter 可能改变 dirty，必须记录并披露及安全收尾，不套用 P1 参考源只读承诺，也不因 dirty 变化自动认定几何持久性失败。新会话须重新枚举和唯一解析原生身份，实际持久性仍以读回内容为据。

## 批次 C2：T11 IR 驱动 UG11 原型

已审 `v3/ug11/{profile,runtime,__init__}.py`、`tests/v3/ug11_probe/test_t11.py`、离线及实机索引，并核对生成实例 `workspace/v3/p2/T11-20261108-01` 的输入、Journal 关键路径、runner、claim 和原始 native-evidence。结论：T11 代码与本次原生证据接受，不重跑 T06/T11。

严格输入仅为人工确认的固定 XY 矩形/拉伸、五项长度参数和宽高公式；未知能力、开放项、额外关系/操作/源文件引用均拒绝。生成器由宿主 Python 生成 C#，不把 Python 当作 UG11 内置语言；原生运行在建件前检查 release、assembly/file/product 版本及语言环境。生成的新路径拒绝覆盖，失败保留产物且不自动重放，运行不读取参考 PRT。

一次 IR 驱动链独立于 T06 必要探针：初始 bbox `[10,5,0,40,25,15]` mm；先仅改 width 到 36，height 联动 24，bbox `[10,5,0,46,29,15]`；再仅改 x 到 14，bbox `[14,5,0,50,29,15]`；保存关闭重开后重新枚举的四个 Driving、公式、SKETCH 使用者、DOF=0 和原生历史保持，后正常关闭。索引如实区分 root 收尾观察与原始进程转录，不仅凭 exit code 判断。

限制保留：IR `datum_plane` 在此原型映射为固定 XY support Plane 和草图生成的 DATUM_CSYS，不声明任意基准面或要求两版历史名称逐字相同；正式维护包名称 unknown。此次未读体积、未单独编辑/读回 Extrude depth 的原生使用者，不将四个 Driving 和有限块体几何检查升级为全部工程参数域或整件 G/P 验收。宿主 Python 元信息补入离线摘要即可，不需重测。

## 批次 D1：T12 NX2506 runner 实机前审查

已审 `smoke_plan/run_block_once.py`、`binding_checks.py`、独立块体数值 oracle 及对应离线测试/索引。R04 及 C# 桥门禁证据均已关闭，runner 限定控制流可进入独立输出件的一次实机验证。它不启动或关闭 NX，拒绝参考源、已有输出和非空证据目录，核对预期 PID/工作件路径、毫米单位和空白历史后才建块；每项绑定/编辑要求 execute 及 fresh 检查。保存重开必须新 ownership/epoch，随后重新枚举对象与唯一约束映射，仅 prepare 读取当前绑定，没有 execute 拟议 37 mm 修改。

保存 UNKNOWN 或任何异常都停止，不重试、不归还、不关闭 MCP server；仅安全归还确认后关闭本 runner 的服务器。请求/响应和摘要移除 ownership/令牌等键及已捕获秘密值，fake 覆盖两个 ownership 值不出现在证据或 stdout。原始运行仍须在本地检查其他可能的诊断秘密，不能把字段脱敏视为任意日志的绝对保证。

T12 实际 NX2506 结果尚未提交，不认可整体烟测 PASS。已有夹具首次失败与单位枚举修正记录可保留并使用实际新鲜读回验证原生成件，不应重建/覆盖或将首次失败重写为成功。P2 整阶段仍未评审接受。

## 批次 B2：T10.a 真实支撑图补缺 C4

触发依据：root 报告 native-01 的 datum 创建/fresh 成功，但显式 datum 的 legacy_driving 草图创建被旧 fixed 支撑规则拒绝，且已验证 ROLLED_BACK；T09 尚未运行。root 已调查无 UNKNOWN/活动操作、正常归还及关闭独立未保存夹具，未将该失败重写为成功。一次 SUPPORT-01 诊断以未保存零件读取真实 `外部 DatumPlane → 内部 DatumCsys → Sketch` 图，完成后关闭，没有实体/保存输出；此诊断不是产品授权链验收。

已定向审 `workspace/v3/p2/P2-NX2506-SUPPORT-01/native-graph.tsv`、`V3/SupportGraphPolicy.cs`、M2OpenModelAdapter 的 `V3ReadDatumSupportedSketchAudited`/新增查找分支/V3ReadBlock 图白名单、构建源清单、新 pure-policy harness/测试及 `p2-support-graph-policy-offline.txt`、`v3-p2-build-c4.log`。C4 代码审查接受，可进入受影响链的必要实机验证；不重审既有事务或重跑无关测试。

新增分支要求当前 part 对象、唯一同一 Coincident 支撑 Plane、其唯一 datum 几何、内部 datum 的组件/实体一致、唯一父子链、SmartObject 直接及递归父集合精确匹配，标量/方向/点为受限常量叶节点，变换尺度/正交性/草图frame一致。额外、重复、缺失或外部节点拒绝。builder 清理失败或读取前后 dirty/库存不一致转为分析状态未知。F21 fixed 支撑原路径保留；没有把非零父数量无条件视为固定支撑。

V3ReadBlock 不再假设枚举必须恰三项，而是仅允许已查实的 external datum/internal datum/sketch/extrude 四个身份；必须实际枚举到 external datum、sketch、extrude，允许 NX 枚举省略 internal，但原生内部图仍强制检查。Extrude 的父节点也收紧为唯一 Sketch。

证据限制：pure-policy 测试覆盖一个目标图、11 个变边/重复/漏边及11个不可用列表；没有实测任意复杂图。SUPPORT-01 逐层读图支持候选关系，但新 UF 递归集合返回、builder清理后状态审计及保全链仍须通过下一次实际新代码运行；不凭编译/集合断言宣称已解决原生问题。runner 对3/4项历史的匹配也需依同一图约束对齐后再运行。

增量 B2.1：已审 runner `select_reopened` 对齐：仅唯一 ABSOLUTE_DATUM_PLANE/SKETCH/EXTRUDE 及可选 DATUM_CSYS，要求原生 support ancestor、外部 datum/内部 datum/sketch/extrude 的闭合父子关系及唯一body，未简单放宽数量限制。测试新增3/4项正例和缺祖先/错内部父/额外feature/错body/错Extrude父负例；`p2-smoke-offline.md` 已补 `P2-RUNNER-T10A-GRAPH-01` 的4/4、命令/cwd/环境和人工代码标识。代码及离线摘要接受，不需重跑已有效UG11或其他阶段证据。

## 批次 D2：C4 NX2506 最终原生增量及安全收尾

已核 `tests/v3/evidence/p2-smoke-native-index.md` 的 C4 记录及 `workspace/v3/p2/P2-NX2506-02/native-01` 的67组请求/响应顺序、关键原生结果和摘要，隔离部署记录指向 `v3-p2-candidate-c4`。源码改动原因、候选/runner/输入/环境标识、准确命令与 cwd 有据；只读核证据，没有重新运行任何 NX 或测试。

- 运行 NX build `v2506.0.0.1700`，初始独立夹具为毫米、FullyLoaded、零特征/草图/实体/表达式，dirty false。datum/sketch/extrude/bind/width/x 六次 execute 各有 APPLIED 及相应 fresh 成功；后三次 update 错误数0、非目标保全 true。新支撑图分支经过这条正式授权链实际运行，T10.a 在该限定图域闭合。
- `0037/0045/0052-response.json` 各含 bindings/geometry/history/non_target_preservation 四项 VERIFIED。四个草图参数有真实 Driving 几何关联与 SKETCH 使用者，`v3_depth` 为 Extrude end 且有 EXTRUDE 使用者；width 的原生引用列表含 height，height 原生 RHS 为 `v3_width*2/3`。宽高 30/20→36/24 mm，随后 x 10→14 mm；bbox 与三个独立期望一致，体积9000→12960→12960 mm³，原生 body consistency faults=0。
- `0059-response.json` 保存/重开为真，expression/geometry/history/associations 全部 VERIFIED，binding epoch 1→2，旧计划失效。`0061/0062` 从当前绑定重新枚举四个特征闭合图和四个 Driving、DOF0；编号即使文字相同也不是沿用旧句柄。这里是同一 NX 进程内保存重开/重新绑定证据，不冒称另一次 NX 进程启动。
- `0064/0065` 仅 prepare width=37 的提议，读取的 before 仍为 width36/height24/x14及相同使用者/实体；之后没有 execute。`0063/0066` revision9、semantic_changed=false、dirty true→true。首次重开 session 的语义变化与后续稳定 revision 均保留；dirty 布尔不变不被当作无副作用证明。
- `0067-response.json` 确认 HUMAN_OWNED、safe_for_human=true、in_flight0、writes_halted=false。root 的 `P2-NX2506-02/shutdown-record.json` 记录正常关闭、对仅 `block-final.prt` 的 getter dirty 选择不再保存，保留已验证磁盘副本，未强杀且最终 remaining_processes 为空。

结论：T09/T10/T10.a/T12 在此有限输入/精确环境下代码、授权链和原生证据接受；继承先前已接受 T06/T07/T08/T11，P2 出口证据成立。首次失败、已验证回滚、诊断与必要复验均保留，不借完整成功覆盖失败历史。最终任务 DONE 与阶段接收仍由 TL 写唯一台账。

## 残余风险及阶段边界

真实参考样件仍未进行 P3 分区识别、设计意图确认或整件计划；T04.a—d 后续能力缺口没有因本次块体通过而关闭。账本自洽不证明工程尺寸全量识别。UG11 profile 仅覆盖实测 `NX V11.0 / 11.0.0.33` 的 C# 原型及固定 XY 支撑映射，正式维护包名称仍未知；NX2506 新事务仅正 XY 块体和固定宽高关系，不是通用表达式/特征执行器。

本阶段没有验证任意编辑域边界、拓扑变化、所有实际故障注入、完整样件三段 G/双端 P 或 P5 独立产品包；有限bbox/体积/端点和成功回读不能升级为全域几何或制造精度声明。UG11未测体积、未独立编辑/回读depth使用者的限制保留。这些是后续阶段既定验证范围，不阻塞本次有限架构出口，也不得据此提前发布整件能力。

P1 已接受的只读库存与能力审计直接继承，所有本轮有效证据不因换 AI 重跑。评审实例未执行 Git、文件/目录/模型哈希、NX 启动、测试重跑或源码/台账修改；本文件为唯一写入文件。本阶段应由 TL 完成交接后停止，P3 必须由用户启动新主 AI。
