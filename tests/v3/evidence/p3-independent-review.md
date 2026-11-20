# P3 独立高级评审

评审日期：2026-11-08。评审实例 `/root/p3_review` 与实现、验证实例不同；仅写本文件。未运行测试、启动 NX、执行 Git 或计算文件/目录/模型 hash。P1/P2 已接受证据直接继承，不重新评审其结论。

## A. Python 候选分析与 T19 首批评审

范围为人工代码标识 `P3-ANALYSIS-C1` 的 `regions/common.py`、`profiles.py`、`additions.py`、`cuts.py`、`relations.py`、`transitions.py`、`model_plan.py`、`tests/v3/run_p3_analysis.py` 及对应新增测试。原生读取模块仍在开发，不属于本节。以下行号指本次冻结版本。

### 发现（按严重度）

1. **R01 / 中等 / OPEN：非法候选仍可贡献“已解释”覆盖。** 受影响：[model_plan.py](../../../src/nx_sketch_mcp/v3/model_plan.py)，第 43—88 行；[test_model_plan.py](../test_model_plan.py) 的 `test_duplicate_unknown_and_invalid_sources_have_specific_findings`。字段、来源或参数不合法时仅增加 finding，未取消几何解释资格；随后只凭确认、证明标记、snapshot 和 coverage_role 就将合法来源子集计入 `explained`。已有测试候选携带重复/foreign 面及不存在的边，但仍带 confirmed/proven，能沿代码路径将 F1 计为已解释，测试只查错误码。后果是持久覆盖账同时报告来源无效与区域已解释，后续人工确认流程可能据此少算未解释区域；`execution_approved=false` 不修复覆盖统计。最小修复：将候选的结构、来源、参数有效性与解释资格绑定，保留错误诊断但不让非法候选贡献 explained；至少增加上述非法来源用例的 explained=0 断言，保留合法确认覆盖正例。仅定向复验受影响的模型计划测试，不重跑首批全部测试或真实分析。

2. **R02 / 中等 / OPEN：能力关闭依据未进入持久计划。** 受影响：[model_plan.py](../../../src/nx_sketch_mcp/v3/model_plan.py)，第 95—97、138—151 行。函数使用 `capability_evidence` 的 closed/evidence 消除 `open_capability`，但返回值没有保存采用的关闭记录。候选仅保留需求名称；JSON 报告的后续接手者无法判断哪个证据关闭了该门禁或检查适用范围。最小修复：在输出保留实际采用的能力关闭证据与所对应需求/候选，或在缺少可持久追溯关闭记录时维持开放；扩展 `test_open_items_and_capability_requirements_are_gated`，确认关闭证据经报告序列化仍可读取。无需原生测试。

### 已读取证据与适用结论

- [TV 索引](p3-validation.md) 与 [首次测试输出](p3-analysis-c1.txt)记录一次离线运行：49 passed、30 subtests passed。命令、cwd、解释器/pytest 版本和匹配阈值由索引保存；本评审仅读取，不重复执行。关系测试包含合法 IR 公式求值、共享/独立编辑假设、非法量纲/循环和零除负例，但不证明真实设计关系或双端原生联动。
- [真实库存首次输出](../../../workspace/v3/p3/P3-ANALYSIS-01/model-plan.json)为 222 条候选/未解记录，来源总数 235 面；68 面关联候选，150 面复杂曲面未解，17 面残余，42 面候选重叠；0 面确认且有证明的解释，235 面均未解释。构造顺序未定，执行未批准。R01/R02 的问题分支均未被此报告使用：没有 confirmed/proven 候选，也没有能力关闭输入；不要求重跑这一有效首次产物。
- 识别器保留局部来源、原生字段、匹配残差、歧义和未确认尺寸；未将 UF 面类型宣称为历史特征，未把平面邻接判为盲孔/通孔，未把几何等半径宣称为驱动关系。复杂面逐面留下 T04.a/b/d，过渡不直接释放受限 F16/F17。CLI 独立输出、快照内逻辑 ID、未确认候选与 P2 IR1.0 的边界清楚。
- 首批代码存在 R01/R02，暂为 **CHANGES**；修复后仅审差异与最小复验证据。该结论不重新否定已接受 P1/P2，也不将本次全部验证作废。

### 阶段出口与残余风险

真实样件完整截面、曲面/边界修剪、设计意图与编辑域尚未解释，全部面仍未形成确认方案，布尔/修饰构造顺序未形成。因此 **P3 尚不满足 DONE**。有限候选功能和明确缺口账可作为部分交付；235 面各有记录、离线测试通过、执行门禁恒 false 均不能替代清单 T13—T17/T19 的实际区域计划、确认与覆盖出口。P3 所属识别缺口不得仅移交为 P4/P5 后端问题；已具备明确方案的后端映射和原生传播则按所属阶段验证，不倒等后续整件验收。

下一批必要评审是 T13.a 原生补读模块与授权接线冻结后的实机前审查，重点为 ABI、UF_BREP 分配/释放、只读状态守卫、异常与冻结、会话内来源映射和缺失数据声明。编译/离线验证就绪后才审，不提前审变化中的文件。实机后仅增量审新增证据，不重做已有效审查。

### A.1 R01/R02 定向关闭复核

人工修复标识 `P3-MODEL-PLAN-C2`；仅复核 `model_plan.py`、`test_model_plan.py` 的上述问题及 [定向复验](p3-model-plan-c2-retest.txt)，命令/环境/范围见 [TV 索引](p3-validation.md)。TV 一次运行 12 passed、13 subtests passed，退出码 0；评审未执行测试。

- **R01 CLOSED**：结构/来源/参数维度错误记入失格集合；重复候选 ID、未知或重复依赖、依赖环及依赖失格传播均在统计 explained 前处理。确认和证明引用要求非空字符串。定向反例明确断言 explained=0，合法确认候选正例仍计 F1；原错误诊断保留。
- **R02 CLOSED**：严格校验实际采用的 closed/evidence 记录，将其复制到 `capability_evidence`，以 `capability_uses` 保存候选与需求对应；测试经 JSON 往返仍保留关闭依据，空白/非字符串/额外未知字段不关闭门禁。

首批受限 Python 候选分析及 T19 记账实现现可接受为 **P3 部分交付**；本次范围无剩余代码阻塞发现。此前 C1 首测和真实报告保持历史适用性，未重跑、未将其冒充 C2 新生成产物。阶段完整几何、设计确认、覆盖和构造顺序阻塞保持不变；本节不批准 P3 DONE，也不批准尚未评审的 T13.a 原生实机操作。

## B. T13.a 原生补读与授权接线实机前评审

范围：`P3-DETAIL-C1` 的 `ReferenceGeometryNative.cpp`、`ReferenceGeometry.cs`、`ReferenceDetail.cs`、M2 合同/桥/adapter 接线、Python server/bridge、构建清单、detail runner 及本次新增测试；不重审 A 节。

### 发现（按严重度）

1. **R03 / 高 / OPEN / 实机前阻塞（SI/E1 自查提出，独立评审核实）**：`ReferenceGeometryNative.cpp` 的几何释放与 topology 释放返回非零时，C1 只设置 `incomplete=true`，仍向 managed wrapper 返回 ABI 成功。wrapper 据此正常返回，adapter 可以继续第二面，生命周期未知未进入冻结。最小修复为记录释放失败，尽力清理其余所有资源后返回非零且输出指针/长度为 null/0；wrapper 既有异常由 bridge 转成粘性 UNKNOWN。`UF_free` 返回 void，不得据其调用宣称有返回码成功。最小验证为 fake UF 注入 geometry/topology 两类释放失败，检查 ABI 失败、输出为空、其余释放仍发生；定向构建 C2 native 并保存与冻结源码、实际部署路径关联。既有 bridge 异常冻结测试直接继承，不重跑无关项。TL 已冻结实机启动等待该项关闭。

### C1 已有证据及接受边界

- 读取 [C1 构建日志](../../../workspace/build/v3-p3-candidate-c1.log)、[native 独立编译记录](../../../workspace/build/v3-p3-candidate-c1/native-build-record.txt)及[依赖记录](../../../workspace/build/v3-p3-candidate-c1/dependencies.txt)。CLR 四产物与 native 分别构建；`build-m2-bridge.ps1` 本身不构建 native，不能把 CLR build complete 当作 native 制品来源。native 记录保存 MSVC x64、当前 NX2506 头文件/libufun、命令/cwd及复制目标；依赖为 libufun.dll、KERNEL32.dll。构建不证明 NX 实际加载。
- [离线首测](p3-detail-c1.txt) 15 passed、30 subtests passed、2 failed；两项失败在 fixture 的 cmd/vcvars 引号处理，编译器尚未开始，不是 UF 行为失败。只改测试启动方式后，[定向复验](p3-detail-native-c2-retest.txt) 2 passed；这处 C2 是测试启动修正，尚不是 R03 原生源码修复版。命令与环境见 [TV 索引](p3-validation.md)。未重复任何测试。
- 已核当前安装 `uf_defs.h` 的 tag_t=unsigned int、`uf_brep.h` 的 geometry/topology/state 释放规则。窄 ABI 的 uint32、double、char**、uint64* 与 C# uint/double/IntPtr/ulong、Cdecl x64一致；原生缓冲由同 DLL free，wrapper finally 释放缓冲。fake 测试证明正常及部分 UF 失败后的树/geometry/state 清理、managed 异常/非法 UTF-8/超量缓冲的释放。新 R03 故障分支仍待证据。
- detail 只允许 UF19/UF20 各一面及两个不同标签，当前体新库存中按类型、包围盒、边数匹配，必须每项唯一且两面不同才调用 native；不接收旧 Tag。匹配仅定位候选，不证明旧新面全几何等价。前后库存及 dirty 变化、无法比较或异常转入冻结；revision 明示缓存，完整几何仍 false。实际 NX 进程/线程由既有受权队列承担。
- runner 拒绝源文件/硬链接、已存在证据目标，使用本次 ownership/epoch/revision；未知读取、状态不匹配和未知归还不重放、不归还或自动关闭。稳定的未匹配只记录 INCONCLUSIVE。保留脱敏输出，实际加载、源件保全和安全归还仍须首次实机记录。

除 R03 外，本次审查未发现另一个当前限定两面只读诊断的阻塞。仍不批准启动，待 R03 源码与必要证据冻结后只做增量复核。原生未支持的 SP/B-surface 等类型、深度/数据限额及映射误差均是显式不完整边界；本次诊断不得释放整件计划或关闭全部复杂曲面缺口。

### B.1 R03 关闭及一次受限诊断放行

仅增量复核原生源码 `P3-DETAIL-NATIVE-C2`、fake UF 新增释放故障、构建脚本和 [test-run C3 定向证据](p3-detail-native-c3-retest.txt)：2 passed、退出码 0；测试命令与代码/运行编号区别见 [TV 索引](p3-validation.md)。本评审未重测。

**R03 CLOSED**：任一显式 `UF_BREP_free_geometry_data` 或 `UF_BREP_release_topology` 返回非零即设置 cleanup_failed，最终返回 ABI 3 且保持 null/0 输出；其余 owner 继续清理。异常展开路径原先返回 ABI 2，仍走失败；不声称失败释放已成功或重试释放未知指针。fake 注入两种释放错误，分别检查非零结果、空输出及全部其他 geometry/tree/state 清理计数。继承的 wrapper 异常与 bridge 冻结证据支持停止后续面调用及写入。

[C2 native 构建记录](../../../workspace/build/v3-p3-candidate-c2/native-build-record.txt)保存编译输入快照、与工作区源码逐字节比较、精确命令、环境路径和退出码 0。新增 `tools/build-v3-reference-native.ps1` 将源码复制到新输出目录后编译，拒绝现有源码快照/DLL；未改的 CLR 四产物沿用 C1并明确记录，不将 C2 native 冒称 CLR 重建。没有 hash、NX 启动或 DLL 热替换。

现无阻塞 **TL 在既有唯一队列、独立副本和 C2 隔离 runtime 中执行一次 UF19/UF20 两面只读诊断** 的剩余发现。此次只放行诊断取证，不是发布或整件能力验收。实际 DLL 加载、唯一语义匹配、数据/状态码、dirty 与库存前后比较、源件保全和安全归还仍需该次实机证据；任何异常/UNKNOWN 沿现有门禁停止，不重放。本节不关闭 T04.a/b/d 全部几何缺口，不支持 P3 DONE。实机后仅审新增运行证据。

### B.2 新失败路径使 B.1 放行暂时撤回

**R04 / 高 / OPEN / 实机前阻塞（E1 新增自查，独立评审判定）**：B.1 后 E1 指出 `UF_BREP_ask_geometry` 返回非零且输出 type 仍为 `UF_BREP_GEOM_ALL(0)` 的路径。C2 此时仅记不完整，`GeometryOwner` 因零类型跳过释放，最终仍可能 ABI 0；已读头文件没有明确保证失败时零类型意味着完全没有部分分配。无法解释的资源状态不应沿正常结果继续第二面。此前 fake 仅覆盖失败但已填充 EXTRUDE 类型的情形，不能证明该新分支。

最小修复：将任一 ask_geometry 非零记为原生失败，按已可识别结构尽力释放，其余 tree/state 正常清理，最终非零 ABI/null/0，交现有 wrapper/bridge 进入 UNKNOWN；不得对零类型猜测 union 成员并盲目释放。新增 fake 非零+零类型分支，验证无正常结果、其余可识别资源释放；测试不能证明未知分配不存在。无需将所有不相关只读 UF 错误一律改成 UNKNOWN，也不重跑无关测试。

E1 随后补充的同类合同边界纳入同一 R04：两类分配型读取的 `ask_topology != 0` 或成功却 tree=null、`ask_geometry != 0` 或成功却 type=0，均要求失败 ABI/无正常结果。fake 覆盖这四种失败合同及可识别资源清理；UV/matrix/edge_class 等不分配读取仍可显式 INCONCLUSIVE，不扩大冻结规则到无关错误。

**B.1 一次诊断放行暂时撤回。** TL 已报告隔离 NX 启动但尚未开件、接管或调用 reader，因此当前没有未知读取副作用，不将当前进程虚记为 UNKNOWN。先正常退出空 NX，再构建/部署修订制品，禁止热替换。待修复、定向证据及制品版本关联后，仅复核 R04。

### B.3 R04 关闭并恢复 C3 一次诊断放行

**R04 CLOSED**。仅增量复核 `P3-DETAIL-NATIVE-C3`：`ask_topology` 非零或空树、`ask_geometry` 非零或零 geometry 类型均设置 native_failure，正常路径尽力清理已暴露资源后返回 ABI 3/null/0；零类型不盲目解引用/释放 union。异常路径继续非零 ABI，释放失败规则保持。fake 的六类失败涵盖两种查询错误、两种无效成功输出和两种释放错误，均无正常输出，并检查 tree/geometry/state 清理计数；正常读取正例仍返回 INCONCLUSIVE。

[test-run C4](p3-detail-native-c4-retest.txt)定向 2 passed、退出 0，命令由 [TV 索引](p3-validation.md)保存；[C3 构建记录](../../../workspace/build/v3-p3-candidate-c3/native-build-record.txt)关联源码复制/逐字节比较、精确命令和退出 0，CLR 不变继承 C1。评审没有重测或启动 NX。[空 NX 收尾](../../../workspace/v3/p3/P3-NATIVE-01/pre-read-shutdown-record.json)保存正常退出事实；该轮无 PRT、ownership 或 reader 调用，不称原生读取失败或 UNKNOWN。

恢复仅针对 **C3 隔离 runtime、独立副本、唯一实机通道的一次 UF19/UF20 两面首次只读诊断** 的放行。无已知剩余实机前阻塞；仍须实机证据核对实际加载/唯一匹配/读取状态/前后保全/归还。fake 无法证明未知 UF 内部资源不存在或真实几何完整，只证明对可观察失败的停止处理。不得据此标 P3 DONE、关闭复杂面全量解释缺口或执行整件重建。

## C. 首次实机失败证据与冻结收尾评审

### 发现与结论

**R05 / 高 / OPEN / T13.a 与 P3 阻塞：真实读取未保持只读状态。** 输入为 `P3-NATIVE-02` 独立副本，NX PID16252、v2506.0.0.1700；[接管](../../../workspace/v3/p3/P3-NATIVE-02/native-01/detail-takeover.json)成功后，[detail 原始响应](../../../workspace/v3/p3/P3-NATIVE-02/native-01/detail-snapshot.json)明确 `is_modified_before=false`、`is_modified_after=true`、`two_native_samples_equal=false`、`ok=false`、`read_consistency_fault=true`、`writes_halted=true`、`ownership_state=UNKNOWN_FROZEN`。这直接否定 T13.a 本次只读守卫验收；不能因 UF 返回码正常或取得数据而接受实现完成。

最小关闭证据须先解释副作用来源及受影响范围，再在同一 P3 的限定修复任务中证明读取守卫成立；当前不得重放以补证。本节不修改代码或操作 NX。现有输出未保存第二份完整库存或差异项，故不能从该响应确定变化对象，更不能推测仅为无害 dirty。首次失败必须保留；新的诊断/修复及最小复验范围在恢复可解释状态后另定。

### 新证据核对

- 两描述符各 `matching_count=1`，F0002/F0005 均 MATCHED；两次 topology/release 返回码均 0、topology states 空。原生子结果仍为 INCONCLUSIVE、完整几何 false。只能证明定位和所列返回字段，不能覆盖上层只读失败或证明完整修剪/参数关系。
- [runtime 复制记录](../../../workspace/v3/p3/P3-NATIVE-02/runtime-copy-record.json)关联 C3 native 与四个既有 CLR 产物，并记录逐字节复制比较；[启动记录](../../../workspace/v3/p3/P3-NATIVE-02/launch-record.json)和接管中的 PID/session 信息一致。本节不重新构建或重审既有离线证据。
- [runner 摘要](../../../workspace/v3/p3/P3-NATIVE-02/native-01/detail-summary.json)为 STOP_MANUAL_CHECK，inspection=`unresolved_or_frozen; manual check required`，return=`not attempted; outcome unresolved`。未到 status 查询点；没有成功归还证据，不能写 HUMAN_OWNED。TL 报告没有重放、保存或后续模型操作。
- [冻结时磁盘保全](../../../workspace/v3/p3/P3-NATIVE-02/source-preservation-frozen.json)记录原件和工作副本磁盘字节未变，方法为直接字节比较。该证据只保护磁盘，不将内存 UNKNOWN 或 dirty 变化判为无影响。

### 收尾边界与人工核查

适用 [V3-stage-handoff §6](../../../docs/V3-stage-handoff.md)：“UNKNOWN 停止后续写入，人工核查进程、模型及外部副作用，不自动重放/解冻；不强杀 NX、不热换 DLL，按既有流程安全归还。”[AGENTS.md](../../../AGENTS.md)也要求 UNKNOWN 停写、不重放、不自动解冻。因此当前允许只读证据归档、已授权文件的磁盘比较和界面/进程核查；不得 nx_return、保存模型、重试读取、重启以清状态或热换 DLL。

关闭脏副本会丢失当前尚未解释的内存状态，应交用户人工核查当前 NX 只包含本次独立副本、没有其他未保存模型，并决定保留现场诊断还是正常关闭且不保存该副本。这一步来自明确的人工恢复要求；不按一般正常收尾授权自动丢弃未知状态。人工决定后仅正常关闭受控程序，不强杀、不改源件；记录退出前冻结事实和退出后实际进程/磁盘状态，不能把退出冒称成功的 ownership 归还或 UNKNOWN 已解释。

**最终当前结论：T13.a 真实只读守卫未通过，P3 BLOCKED。** 已接受的受限 Python 部分交付及 R01—R04 修复结论保留；R05 未关闭，整件计划、完整曲面解释及设计确认尚未完成。后续接手仍为 P3，不进入 P4。

## D. T13.b 逐调用诊断增量实机前评审

### 新发现

**R06 / 高 / OPEN / 实机前阻塞：故障 payload 返回后桥层仍访问 NX。** `M2Bridge.cs` 约第 794 行在 detail adapter 返回 DIRTY_STOP/NATIVE_ERROR 后，无条件调用 `RequireCurrentBinding(binding)`；`M2OpenModelAdapter.IsBindingCurrent` 会再次访问 Session、WorkPart、Tag/FullPath。若检查失配，`RequireCurrentBinding` 还会释放并清除绑定、抛错，使已产生的 first_change/events 只剩通用错误。该行为违反本次明确的“首次 dirty 后仅清理、保留结构化结果并冻结”合同，adapter/native 的短路测试无法覆盖这一桥层后处理。

最小修复：detail 故障或未知响应先在生命周期锁下冻结，跳过 post-adapter NX 身份查询，只处理缓存的 binding/ownership 一致性并保留 payload；clean 响应仍保留既有后置身份核验。定向 bridge 假件在故障返回后再次调用身份检查即失败，断言没有该调用、payload 保留、状态 UNKNOWN_FROZEN、后续模型动作拒绝。应与 SI 同期自查的 clean trace 字段增强一起冻结，仅复验受影响项。

### 已读证据和非重复接受边界

- 已读 [用户批准收尾记录](../../../workspace/v3/p3/P3-NATIVE-02/user-approved-shutdown-record.json)：用户指示“通过，继续开发”，TL 正常关闭旧 NX，退出对话框仅列独立副本并选择不保存；磁盘源件/副本未变、退出后无相关进程。该事实更新 C 节的“人工待答”现场状态，不关闭 R05，不改写成正常 ownership 归还。
- T13.b native C2 共用原生遍历，通过 probe 包装 UF 调用，记录前后 dirty、是否调用、返回码和清理属性；dirty 或有返回码的失败停止新读，只继续必要清理。已存在 dirty 时第一项读取不调用；诊断将几何文本输出到丢弃流以保留有界 events，明示几何/state 明细省略，不称完整几何。
- Managed 入口检查绑定 partTag 和 FullyLoaded，不能从 UF_PART_is_modified(false) 推断已加载；native dirty/error 后不读第二面，也不采 after 库存，明确 unavailable 状态。clean 路径才保存双库存和逐字段差异。runner 仅在完整 clean 证据满足时进入 status/return，未知结果保留且不重放。
- [T13.b 证据索引](p3-diagnostic-validation.md)保存 C1 首次 23 passed/15 子项及 adapter 假件 Tag 命名引起的 2 测试、4 子项首败；C2 定向两文件 [22 passed/4 子项](p3-t13b-c2-retest.txt)。production adapter 与 fake/native 行为测试分别读取，评审未重跑。runner C1 证据继承。native C2 构建记录关联冻结源码副本、编译命令与退出 0，managed 继承 T13.b C1，不能与更早 T13.a C1 混淆。

当前仍不放行新 NX 诊断，等待 R06 及同期 clean-validator 增强最终冻结。R05 是实际只读失败，T13.b 只是定位工具，诊断获准也不关闭 R05。

### D.1 R06 关闭及 C3 诊断放行

**R06 CLOSED**，增量版本 `P3-T13B-C3`。detail adapter 返回故障、缺失/非法 fault 字段或 null 结果时，桥先在生命周期锁内冻结，跳过后置 `RequireCurrentBinding`；有效 payload 只经过缓存 binding/owner/epoch 检查后保留。clean/default 路径仍保留既有身份检查。假件在故障后任何再次身份查询即抛错，定向结果证明原诊断字段保留、UNKNOWN_FROZEN、归还被拒绝。

同期 clean trace 增强检查事件 rc 与 void 语义、数值类型/序号、dirty 前后、part/face 标签、起始 UV/topology 顺序、topology release 和 geometry 分配/释放配对。对应非法 rc、void、序号缺口、缺释放、错标签、起始顺序及 dirty 反例均使 adapter 停止第二面并保留故障结果。它不证明可信 producer 以外的任意伪造事件，也不证明实际 NX 形状完整。

[C3 定向输出](p3-t13b-c3-retest.txt)为 4 passed、13 subtests passed，命令/环境见 [诊断索引](p3-diagnostic-validation.md)。[CLR 构建日志](../../../workspace/build/v3-p3-t13b-c3.log)显示四产物构建完成；[native 继承记录](../../../workspace/build/v3-p3-t13b-c3/native-inheritance-record.txt)明确沿用 T13.b C2，九份源码/假件副本清单保留，不声称重建或重测未修改 native。没有重复旧验证。

当前无阻塞 **新独立副本、C3 隔离 runtime、唯一实机通道的一次 T13.b 逐调用诊断** 的剩余发现。首次 dirty/error 后只能清理、保存已取得的诊断文件并冻结；不得为了取得完整 after/diff 再读。TL 可按用户已批准继续开发及收尾方式，核对本次测试副本/窗口归属后正常退出且不保存；这不是解冻、不是成功 ownership 归还，不在未知会话重试。新的实机定位证据仍需审查，R05 保持 OPEN，P3 完整出口未满足。

### D.2 首次逐调用实机定位证据

仅读取 `P3-DIAG-01` 的 [原始响应](../../../workspace/v3/p3/P3-DIAG-01/native-01/detail-snapshot.json)、[摘要](../../../workspace/v3/p3/P3-DIAG-01/native-01/detail-summary.json)和 [Python 退出码](../../../workspace/v3/p3/P3-DIAG-01/python-exit-record.json)，不重放调用。

F0002 唯一匹配，59 个 native 事件均 clean，结果 CLEAN_TRACE。F0005 唯一匹配，前 11 个事件 clean；第 12 项 `UF_BREP_ask_geometry`，当前会话 edge tag 63602、topology_type 8，dirty false→true，UF rc=0。第 13/14 项分别为 geometry free 和 topology release，均为清理，没有后续几何查询。同次 `inventory_before` 将该 tag 记录为 Circular，并关联面 63151/63172；这提供圆弧边调用的限定调查依据，Tag 仍不可跨会话复用。

托管事件止于 `native:1`、first_change 指向 native sequence 12；`inventory_after=null`、diff=`unavailable_after_dirty`，没有以空 diff 冒充未变。响应 ok=false、read_consistency_fault=true、writes_halted=true、UNKNOWN_FROZEN，runner STOP_MANUAL_CHECK、未调用 return；独立记录 Python 退出码为 2。**T13.b 的首次变化定位、停止新查询、必要清理和结构化冻结目标已有本次实机支持。**

此证据仅将首次可观察 dirty 定位到该圆弧边的 UF 查询区间，不证明内部机制为 matrix 创建，也不证明其他边/调用没有额外问题。F0002 clean 也不扩展到所有 Swept 面或所有会话。后续 T13.c 可围绕有来源的圆弧读取替代方案拆小任务，仍需独立设计/故障路径/实机证据；R05 保持 OPEN，不因诊断成功关闭只读失效。TL 已进入授权的正常不保存退出收尾；本节写入时尚未读取该轮最终退出及磁盘保全记录，因此不提前宣称收尾完成。

### D.3 T13.b 收尾补证

后续已读 [shutdown-preservation.json](../../../workspace/v3/p3/P3-DIAG-01/shutdown-preservation.json) 与 [shutdown-processes.json](../../../workspace/v3/p3/P3-DIAG-01/shutdown-processes.json)：TL 按已批准方式正常退出唯一独立副本、不保存、不调用 return、不强杀/热替换，原件/副本磁盘字节未变，相关进程列表为空。T13.b 的限定定位与停止诊断任务可接受完成；该收尾不证明旧 dirty 内存未变，也不关闭 R05 或整个 P3。

## E. T16.a 圆周轴位置关系候选独立评审

范围仅 `regions/circular_relations.py`、`tests/v3/circular_relation_regions/test_circular_relations.py` 及 [首次 14 passed](p3-t16a-c1.txt)，命令/环境见 [独立索引](p3-diagnostic-validation.md)。无当前受限候选范围的阻塞发现，可接受为 P3 部分交付。

规则以负 sense 柱面、半径匹配和组内全部轴方向约束分组，轴线投到公共平面后拟合圆，并检查闭环角间距/相位残差；保留来源、位置、方向、邻接签名及差异。真实库存用例保留 22 轴观察和两个邻接签名例外；不同数量/姿态/尺度、缺失/重复/非均匀/非平行/共线反例及 IR 角度表达式正反例均有首次证据。未把等间距位置解释为已确认阵列/孔或驱动关系。

残余风险明确：规则可能错过混杂组中的子环；规则不能识别仍形成更小规则环的遗漏；近似平行轴的公共平面观察不证明全长共轴关系，邻接签名差异可能来自面分裂。完整修剪/材料侧、种子/相位基准、工程意图和编辑域均未确认，双端原生传播尚待所属阶段。该新模块尚未改变 C1 的首次完整候选报告，不把旧报告声称为包含新关系的重生成结果，不计入已解释几何或 P3 DONE。

### E.1 入口增量接线

新增 CLI 将 circular_relations 候选纳入原有汇总，来源仍绑定当前快照且 coverage_role=observation，不贡献 explained。已读 `test_analysis_circular_integration.py` 及 [1 passed 首次证据](p3-t16a-integration-c1.txt)，包括来源/未确认门禁与输出冲突拒绝；未重跑已接受识别器。新路径 [P3-ANALYSIS-02](../../../workspace/v3/p3/P3-ANALYSIS-02/model-plan.json)为 223 条记录，其中 1 条圆周候选，235 面仍全部未解释、execution_approved=false；旧报告未覆盖。该受限接线接受，不扩大阶段结论。

## F. T13.c 圆边 evaluator 替代实机前评审

范围仅 `P3-T13C-C1` 的 v3 native/wrapper、当次边白名单、managed/runner 合同和对应新增/受影响测试。**未发现阻塞限定两面新副本首次实读的新增问题**；尚不关闭 R05。

- 已核当前安装 `uf_eval.h`：initialize_2 为 curve/edge 分配 evaluator、不近似程序生成边，返回指针须 UF_EVAL_free；arc 的 center/x_axis/y_axis 为 ABS 数据。代码先核 is_arc，再依次取得 evaluator limits、periodicity、arc 数据，最后释放；六阶段任一失败或 dirty 只继续必要清理并保留故障 trace，初始化错误但已分配 pointer 也由 owner 清理。
- 白名单来自相同 guarded inventory 的选中 face，逐项核对边唯一、数值 Tag、支持类型及 edge→face 反向邻接。native 仅对白名单 Circular 且 UF_BREP_EDGE_NORMAL 的边走 EVAL；未知、重复白名单、不匹配、覆盖缺失或非 normal 圆边不退回危险读取。一个合法边在多 fin 中重复出现及其各自 orientation 保留；clean trace 要求完整六阶段配对与访问集合覆盖。
- 非圆边保留既有分支，若实际返回 ARC 则停在 type mismatch，不再查询 matrix。圆弧输出分别保存 evaluator_limits/arc_limits、periodic 两字段，不合并、不把周期性等同整圈裁剪。fin orientation 与 evaluator 参数方向关系明确 `unverified`，不得直接当作已验证回路方向。
- v3 同次返回有界 topology/geometry 和事件；900 KiB topology 子预算及事件限额触发失败时保留 trace，无假 clean。`geometry_details_complete=false`、INCONCLUSIVE 保持。root topology states 明细有意省略且显式标注，保留 count，不宣称状态及 UV 修剪完整。该限制仍阻塞后续全域解释声明。
- [首次离线证据](p3-t13c-c1.txt)为 57 passed、32 subtests passed，五个受影响文件与理由见 [索引](p3-diagnostic-validation.md)。包含六阶段 dirty/error、释放、参数/周期差异、方向、白名单和预算负例；共享 fake/wrapper 改动对应必要回归，不是无依据重跑。[CLR 日志](../../../workspace/build/v3-p3-t13c-c1.log)与 [native 构建记录](../../../workspace/build/v3-p3-t13c-c1/native-build-record.txt)关联源码副本、命令和成功退出。评审未构建或测试。

放行 **新独立副本、T13.c C1 隔离 runtime、唯一队列的一次两面实读**。真实 clean 事件、相同当次库存前后对比、归还/正常退出及磁盘保全仍需新增证据；失败继续冻结、不得重放，按已批准的测试收尾方式处理。R05 只有在该限定读取路线的真实只读证据成立后才可受限关闭，不能因此证明全部 235 面、完整修剪、设计意图或 P3 DONE。

### F.1 T13.c 首次实机及 R05 受限关闭

**R05 CLOSED（仅已验证的两面 v3 受控读取路径）**。读取 [P3-CIRCLE-01 原始响应](../../../workspace/v3/p3/P3-CIRCLE-01/native-01/detail-snapshot.json)：F0002/F0005 各唯一匹配，内层 schema v3；分别 59/75 个 native 事件全部 dirty_before/after=false，CLEAN_TRACE、edge_coverage_complete=true，geometry/event overflow=false，topology 与几何同次保留。F0005 四个当前圆边各有完整 EVAL 六阶段，共 24 项，同一边没有 UF_BREP_ask_geometry 调用。所有 managed dirty 采样为 false。

根响应 ok=true、read_consistency_fault=false、writes_halted=false，first_change=null；完整库存 before/after 均保留，diff status=complete、changes=[]，two_native_samples_equal=true。[runner 摘要](../../../workspace/v3/p3/P3-CIRCLE-01/native-01/detail-summary.json)记录 RETURNED/HUMAN_OWNED；[Python 退出码 1](../../../workspace/v3/p3/P3-CIRCLE-01/python-exit-record.json)对应此 runner 的 geometry=INCONCLUSIVE 正常结果，不是 UNKNOWN 或执行失败，不能仅看退出码判断几何完成。

[正常退出与磁盘保全](../../../workspace/v3/p3/P3-CIRCLE-01/shutdown-preservation.json)及[进程收尾](../../../workspace/v3/p3/P3-CIRCLE-01/shutdown-processes.json)确认归还后正常退出、不保存、不强杀/热换，原件/副本磁盘字节和原件 mtime 未变，无 NX/helper/Journal 留存。评审仅读取新证据，未重跑任何调用。

接受 **T13.c 受限替代实现及 T13.a 的 F0002/F0005 两面原生读取路线**。R05 的早期真实失败和 T13.b 定位历史保留；关闭不适用于旧 v1/v2 读取、其他面/边型或其他版本。仍为 geometry_details_complete=false、INCONCLUSIVE，方向关系/UV 修剪/全域形状/工程意图均未由本次证据关闭。P3 尚需真实区域解释、其余来源几何与确认计划，不进入 P4，也不标整阶段 DONE。

## G. T13.d/d1/e 离线 detail 解释首评

范围仅 `detail_common.py`、`detail_extrusions.py`、`detail_tori.py` 及对应三个新测试模块，输入为已接受的 P3-CIRCLE-01；无 CLI 接线、无新 NX、未重复原生验证。

### 发现

1. **R07 / 中等 / OPEN：截断 native trace 仍被归一化为 clean 输入。** `detail_common._clean_trace` 只要求事件列表非空及每个现存项序号/dirty/rc 有效；将真实 trace 截成第一项 UV 事件，保留原 CLEAN_TRACE/coverage 标记，仍满足当前逻辑。代码未要求 topology/geometry/EVAL 路径及释放配对、事件来源 tag 和访问边集合齐全。后果是遗失证据可进入被声明为严格 guarded detail 的识别输入，与实机层已冻结的 v3 合同不一致。最小修复：在离线入口核必要 v3 序列、配对和来源/访问集合，拒绝截断、删 cleanup 后重编号或错来源标签；只增加/运行受影响归一化反例与已有真实输入正例，不重跑 NX。
2. **R08 / 中等 / OPEN：圆环面候选丢失快照作用域。** `detail_tori.recognize` 在 results.append 输出没有 `snapshot_id` 和 `coverage_role`。F/E ID 仅快照内有效，P1 与新的 P3 快照可同时出现 F0005；当前又没有获准的 CLI 接线负责补作用域，候选独立传递后不可可靠定位，交 T19 会触发 snapshot mismatch。最小修复：候选明确带当前 snapshot_id 和 observation 角色，证据中保留相同作用域；真实及合成用例断言，不要求重跑旧识别器。

### 已核数学与边界

样条拉伸模块核母线阶次、节点/权重/有效参数区间、非零方向及逐 fin/edge 来源；无效数据保留 unresolved 记录，不将 UV 差或包围盒当长度/深度，不把常量控制点当工程全参数。圆环模块限定 R>r>0，以中心、轴、圆半径和载体平面验证子午圆或平行圆，保留两个 arc 参数域和 fin 路径，未推断 360°、修剪闭合或驱动意图。

已对照安装 `uf_brep_types.h`：torus 参考方向允许不垂直但不得平行；fin 与其父 loop 若均指定同一边方向则应一致。代码采用的这两条并非凭外观假设。载体匹配阈值仅数值匹配，不是制造公差或全域曲面误差。torus 规则不匹配返回空候选，使用者必须保留该区域未解释，不可把空结果解释为不存在；当前无汇总接线，不能借此减少未解释覆盖。

本次首评为 **CHANGES**，等待 R07/R08 修复与本批首次/必要定向证据。R05 已接受的两面读取范围不受这些离线输入合同缺陷重新否定；整件区域解释和 P3 出口仍未满足。

随后收到并读取本批 [首次结果](p3-detail-profiles-c1.txt)：29 passed、24 subtests passed，退出码 0；准确命令/环境见 [TV 索引](p3-diagnostic-validation.md)。这是本批已存在用例的有效证据，不覆盖 R07/R08 所指出的遗漏；保留首次产物，只对修复影响复验。

### G.1 冻结版本时序核对与 R07/R08 关闭

**R07 CLOSED（最终首测版本已修，不追加重测）**。TL/SI/TV 核对显示，G 首评读到的为事件校验加严前的过渡源码；完整校验已在首次 29+24 运行前冻结。重新只读当前 `_clean_trace`，确认必须有初始 UV/topology、指定 face tag、恰一次最终 topology release、所有 geometry 分配/释放配对、Circular EVAL 六步及非圆 BREP 来源约束、全部源边访问覆盖。原“仅剩 sequence1”反例现在必因缺 topology/release/geometry/边覆盖拒绝；首测包含末事件截断、错误 topology tag、无效阶段/rc/dirty 反例。直接继承首次证据，不为评审与冻结时序交错重复测试。此前 G 节“首次证据未覆盖 R07”的表述仅针对当时读到的过渡源码，本段为最终适用结论。

**R08 CLOSED**。圆环面候选新增当前 snapshot_id、coverage_role=observation、execution_approved=false；真实和合成输出明确断言。已读 [仅 torus 定向 13 passed](p3-detail-torus-c2-retest.txt)及索引命令/环境，未重跑其他模块或原生读取。

当前本批限定 detail 归一化、样条母线拉伸观察及 ring-torus 载体观察可接受为 P3 部分交付，无剩余本批代码阻塞。CLI 尚未接线，不宣称形成新的完整计划。全部观察仍未确认，完整修剪/参数方向、工程驱动项、其余源面和整阶段出口保持开放。

### G.2 detail CLI 增量接线

随后授权的新接线通过 `--detail-summary` 读取对应 P3 detail/归还记录，使用 detail normalizer 和两类局部识别；P1 默认路径保留。外来候选 snapshot 不一致直接拒绝，不重新贴成当前来源。已读 [3 passed 首次接线证据](p3-detail-integration-c1.txt)及测试，覆盖作用域、原始证据保留、外来快照拒绝和不覆盖输出。[P3-ANALYSIS-03](../../../workspace/v3/p3/P3-ANALYSIS-03/model-plan.json)来源为 P3-CIRCLE-01 的新 snapshot，225 条候选/未解记录含两条 detail 观察，0 面已解释、235 面未解释、execution_approved=false。该接线接受；旧 P1/ANALYSIS01/02 未覆盖，不将不同快照 F/E ID 混合为同一来源。

## H. T13.f 球面 native 分支预审

仅静态审查新增 UF_BREP_SPHERE_GEOM 分支、新 sphere 假件及 `test_sphere_geometry.py`，未审仍在整合的 selector/runner/构建，未作球面实机放行。

本次新增分支未发现阻塞：字段符合当前安装 `UF_BREP_sphere_t` 的 center/axis/u0_ref_direc/radius；头文件明确参考方向可不垂直但不得平行，代码只作非零/非平行退化检查而不捏造正交约束。半径须正有限，向量/中心须有限，非法数据进入失败并沿既有 owner 释放；原始 UV 和有向拓扑由原路径保留。输出显式 underlying_sphere_only、UF_BREP_native_unverified，不把新字段冒充已验证坐标框架、完整球面修剪或参数化方案。

必要证据仍为 TV 球面定向结果、冻结的受控选择/来源/runner 合同与构建关联；到位后只增量复核。尚无球面实机数据，不扩大 R05 的既有两面关闭范围。

### H.1 T13.f C1 完整增量实机前评审

`P3-T13F-C1` 的受控 selector、adapter 单面路径、Python 协议、detail_common/runner 动态事件范围及 sphere 新测试已冻结。**无阻塞单个明确球面目标首次受控实读的新增发现。**

协议仅接受一至两项，精确 UF18/Spherical、19/SurfaceOfRevolution、20/Swept 配对；重复标签和相同语义描述在请求层拒绝，两个近似不同描述实际定位同一当前 face 时不调用 native。原生边白名单及响应预算保持，单面不扩大到批量全件。runner 的显式 JSON 必须关联既有 P1 snapshot、字段/类型有效、在 P1 库存唯一定位不同面；不接收旧 Tag，实际调用再用新会话库存唯一匹配。默认两面路径保留，响应 trace/detail 个数由本次请求决定。

[最小新批](p3-t13f-c1.txt)为 30 passed、29 subtests passed，具体节点及命令见 [TV 索引](p3-diagnostic-validation.md)；包含球面数据/dirty/清理、新 selector 协议/bridge、单面 adapter/归一化和 runner。未重跑有效 P1/P2 或已接受两面实机。[CLR 构建](../../../workspace/build/v3-p3-t13f-c1.log)与 [native 记录](../../../workspace/build/v3-p3-t13f-c1/native-build-record.txt)保存成功退出及源码关联。评审未测试或操作 NX。

放行 TL 在 **新独立副本、C1 隔离 runtime、唯一队列中仅一个明确球面目标的首次读取**，不附带未知 F0004，不重读 F0002/F0005。结果仍须实际 clean/库存一致/归还与磁盘保全证据；任何 dirty/故障按已接受守卫停止并保留结果。现有 sphere 原生 frame、完整 UV/trim 和工程参数未经验证，不能提前接受 T04.d 全量解释或 P3 DONE。

### H.2 单球面首次读取证据

已读 [P3-SPHERE-01 detail](../../../workspace/v3/p3/P3-SPHERE-01/native-01/detail-snapshot.json)、[摘要](../../../workspace/v3/p3/P3-SPHERE-01/native-01/detail-summary.json)和 [Python 退出码](../../../workspace/v3/p3/P3-SPHERE-01/python-exit-record.json)。目标为独立选择的 F0023，唯一匹配；58 项 native 事件全部 dirty false，三圆边共 18 EVAL 事件；root geometry=203，中心(0,0,0)、轴Y、u0参考Z、半径31 mm。边覆盖成立、无事件/几何溢出、managed 采样 clean；完整 before/after diff=[]，first_change=null，未冻结。runner RETURNED/HUMAN_OWNED，退出码1仍为已定义的 geometry=INCONCLUSIVE。

上述支持单目标的受限原生读取；source_frame 仍 UF_BREP_native_unverified、scope 仍 underlying_sphere_only，不闭合球面裁剪/工程关系。当前 NX 保留已归还副本供下一独立目标，尚无最终退出与磁盘保全记录，不提前宣称该轮收尾完成。

### H.3 同一干净会话新增 F0004 首次读取计划

TL 提交的新限定目标 F0004 在已接受 P1 库存中为 SurfaceOfRevolution/UF19、radius=0、四边；这些字段不确定其完整 root geometry 或生成线类型。允许 **在当前已归还且干净的同一独立副本/NX 中执行一次该新目标首次读取**，无需仅因换目标重启；这是本节新增的有界许可，不把 H.1 单球面授权扩成同次多面读取。

要求通过新 takeover 取得当前 ownership/epoch/revision，按 P1 语义描述唯一定位，使用新的证据目录/selector记录；不得沿用旧 Tag 或旧凭据。入口发现 dirty 即拒绝。面或生成线的 BREP 查询可能仍出现 ARC 相关副作用，不能凭类型预称安全；已有逐调用 guard 必须首 dirty/error 后停新查询、仅清理、保留 payload 并冻结。随后按用户已批准方式正常退出且不保存，不在未知会话重放或换方式再试。此次不重读球面或已接受的 F0002/F0005，不进入 P4。

### H.4 T13.g 新 UF19 目标首次读取补审

2026-11-09，由新的独立高级评审实例 `/root/p3_review_resume` 仅读取新增实际证据；A—H.3 已接受结论直接继承，未重审旧源码、运行测试、调用 NX、执行 Git 或计算 hash。**本次限定的 F0004 来源读取未发现新增阻塞，可接受为 P3 部分交付；不批准完整几何或 P3 DONE。**

已读 [新目标选择记录](../../../workspace/v3/p3/P3-SPHERE-01/selectors-f0004.json)、[native-02-f0004 原始响应](../../../workspace/v3/p3/P3-SPHERE-01/native-02-f0004/detail-snapshot.json)、[runner 摘要](../../../workspace/v3/p3/P3-SPHERE-01/native-02-f0004/detail-summary.json)与 [Python 退出码](../../../workspace/v3/p3/P3-SPHERE-01/python-exit-f0004-record.json)。F0004 按 P1 来源语义描述唯一 MATCHED，实际 SurfaceOfRevolution/UF19，四条边；原生 root geometry=205，包含轴点、轴向及 type=102 的非有理样条生成线，order=4、7 极点、11 节点、参数区间 [0,1]。这是本次原生字段事实，不将生成线控制点当已确认工程驱动尺寸，也不由 UF19 推断完整历史特征。

native schema v3 的 63 项事件序号连续，全部 called=true、dirty_before/after=false；有返回码的调用均为 0，identifier 的 void 返回保持 null。16 次 BREP geometry 查询各有释放，一条圆边有完整 EVAL 六阶段，最后一项为 topology release；edge_coverage_complete=true，事件/几何均未溢出，outcome=CLEAN_TRACE。所有 managed dirty 采样为 false，first_change=null，ok=true、read_consistency_fault=false、writes_halted=false；完整 before/after 库存均保留，diff status=complete、changes=[]、two_native_samples_equal=true。

runner 记录 RETURNED/HUMAN_OWNED；原始读取及归还前 status 为 AI_OWNED，不能混写为读取期间已人工持有。Python 退出码 1 对应 geometry=INCONCLUSIVE，不能解释为冻结失败或全几何通过。此次仅新增一个 UF19 源面证据，没有重读球面或此前两面；不扩大旧 R05 关闭结论到任意其他面/边/API。

残余限制：geometry_details_complete=false，原生坐标框架、参数方向、UV/裁剪完整性、曲面全域一致性及工程意图尚未由本次读取验证，root topology state 明细仍显式省略。后续若形成该面候选方案，仍须对上述实际依赖给出限定解释及证据；不得仅因取得样条数据将区域计为已解释。22 组共享半径/节圆半径/相位等角且数量固定 22 的用户确认另属待实现的设计意图输入，本节不把该确认扩成该源面或整件几何通过。关机前正常退出尚无记录，本节不补造正常退出/未保存事实，恢复后的实际状态以另行只读核查记录为准。

### H.5 关机后恢复记录补审

已读 TL 的 [2026-11-09 恢复记录](../../../workspace/v3/p3/P3-SPHERE-01/post-reboot-recovery-20261109.json)。该记录基于本轮首次只读恢复核查：系统本次启动时间为 18:03:55（Asia/Shanghai），未观察到活动 NX/Journal/helper，旧代理已不活动；原件与 source-before、工作副本与 source-before、原件与 P1-before 的直接字节比较均相同。最后两次 reader 记录均为 RETURNED/HUMAN_OWNED、无冻结且库存 diff 空；球面结论继承 H.2，新 UF19 结论见 H.4。评审不重复进程检查、字节比较或原生读取。

**恢复记录可接受为当前空闲状态与磁盘保全的检查点，没有阻塞继续本阶段独立离线工作的新增发现。** `normal_nx_exit_before_shutdown_verified=false` 和 disk_only_limit 明确保留：这不能证明关机前正常退出、未保存操作或旧内存完整，也不能补写为已按 H.3 正常收尾。旧会话已经结束，不复用任何旧 ownership/epoch/revision、Tag 或凭据；如后续确需新增实机操作，仍需各自有界任务及全新会话授权绑定。本次历史退出方式的缺失不要求重放两次已有效的读取，也不改变其受限几何结论。

H.4—H.5 为本次有界证据补审终点。T16.b 的新设计确认实现须等待新代码及必要定向证据冻结后另行独立审查；本节未审变化中的实现，未接受 P3 阶段出口或后续阶段执行。

## I. T16.b 共享关系设计确认增量审查

范围仅 `relation_decisions.py`、`model_plan.py` 的新 intent 附加层、CLI 新 `--relation-decision` 路径及两个对应新测试文件；原始确认由 TL 保存于 [P3-USER-22-SHARED-01](../../../docs/v3/decisions/p3-shared-22-user-decision.json)。既有候选算法、T19 覆盖审查及已接受测试直接继承。

当前静态审查未发现该有界意图绑定的新增阻塞。实现只接受原始确认规定的两类候选、同一 ANALYSIS-03 路径和 snapshot、相同 22 面集合及存在的来源边；当前候选必须与已链接报告完整结构相同，不能悄悄改变 frame、成员顺序、参数或关系来源。确认记录保留了原问题、原答复及未知的精确消息时间；没有把记录时间当实际确认时间。

输出独立 `relation_intents`，保留拟合坐标基与 atan2 角度约定、按原成员顺序的相位及共享节圆半径引用；固定数量 22，角间距为 `full_turn / fixed_count`，成员角为 `shared_phase + pitch * i`，成员半径引用共享半径。`model_plan` 在原报告形成后追加该层，未改变候选确认、几何证明、coverage 或 execution 门禁。原生位置绑定、联动、编辑范围和几何等价均未因此成立。新测试使用真实候选记录核作用域失配/重复/改帧/改顺序等拒绝、IR 算术及确认前后报告不变，不把算术求值当原生传播证明。

本节暂待首次/必要定向测试的准确运行记录和一次 ANALYSIS-04 真实应用产物补齐后完成证据接受；评审不重跑测试，不要求因换评审重做已存在有效验证。

### I.1 T16.b 证据补齐与受限接受

已读 [SI 自测记录](p3-t16b-selfcheck.txt)：系统 Python 的 pytest 不可用，未运行测试；改用 unittest 后首次 3 项通过，将 pitch 从观察值改为 `full_turn / fixed_count` 后，仅受影响文件 2 项定向通过。记录明确是当时工具输出的转录摘录，非完整原始 PTY 日志，未采集单次时间戳；不冒称有独立 TV 首测，也不为补归档重复执行。代码/测试审查及真实新产物与这一受限验证证据相符。

[TV 索引](p3-diagnostic-validation.md)保留 ANALYSIS-04 首次因目标父目录不存在的 FileNotFoundError：没有报告产物，不算成功；创建该新目录后同一命令一次成功。后者空输出记录是事后创建，退出码 0 来自执行工具，不能由空文件推断通过。[ANALYSIS-04](../../../workspace/v3/p3/P3-ANALYSIS-04/model-plan.json) 的实际内容含一条 relation_intent、22 成员，准确绑定原确认及 ANALYSIS-03；225 条 candidates 和整个 coverage 与旧报告结构相同，已解释 0、未解释 235、execution=false。

实际意图初值为共享圆柱半径 0.7363898417823 mm、节圆半径 11.848889841783512 mm、相位 0.2855921266687233 rad，数量固定 22，继承原 Y 轴、U=Z/V=X 基、F0172→F0129 成员顺序；这些是计划值和已确认的关系意图，尚非已建立的原生驱动项。**接受 T16.b 的有界意图记录、绑定与算术/CLI 接线，无剩余本批阻塞。** 有效编辑域、三角位置公式到实际约束的映射、双端原生联动和几何验证仍待对应任务，未接受 T16 全部关系或 P3 DONE。

## J. T13.h / T13.i 球面与样条回转面候选增量首评

### 发现

1. **R09 / 中等 / OPEN / 仅 T13.i：矛盾的同边方向仍进入候选。** [detail_revolutions.py](../../../src/nx_sketch_mcp/v3/regions/detail_revolutions.py) 的 `_occurrences`（首评第 68、78 行）分别检查 `fin_ref.orientation` 和其 `edge_ref.orientation` 是 ±1，却没有要求两者一致。当前安装 `C:\0sf\ug\UGOPEN\uf_brep_types.h` 第 716—726 行说明两处均表示同一条边相对于 loop 的遍历方向；两处同时指定时必须相同。静态路径显示，只把实际输入的一处方向翻转，其余来源和生成线保持不变，仍返回 `possible_spline_revolution_surface` 及看似有效的 edge_occurrences；`direction_relation=unverified` 是 evaluator 参数方向尚未证明，不能代替这一已知拓扑合同。最小修复是在该入口拒绝两处不一致并输出 unresolved；新增矛盾方向反例，必要时仅复验受影响的真实正例。无需重跑球面、既有原生读取或全批测试。评审未运行此反例。

### 已核边界及证据

球面模块仅在 UF18/root203、有效中心/正半径/不退化轴与参考向量、完整来源边及有向拓扑条件下检查圆载体相容：圆心沿圆法向相对球心偏置，偏置与圆半径的勾股关系匹配球半径。球面原生 frame 与 ABS 相同仍明确为未验证假设；有限阈值不是全域误差或制造公差。非法/缺失数据保留 unresolved 及原始 topology，合法结果仍为 observation、unconfirmed、execution=false，未证明球冠闭合、裁剪或材料侧。

回转面模块限定 UF19/root205 的有效正权样条，保留生成线、轴、原始拓扑、UV 和来源；检查控制点在包含轴的同一平面容差带内，并用正权 B-spline 凸包及严格正的同侧径向下界给出保守避轴条件。未通过该下界仅表示不能证明分离，不推断实际跨轴；不由原生回转载体推断 360°、闭截面、实体特征或常量极点即全参数。变换/有理权重及非平面、退化轴、无效节点/权重等新测试覆盖本受限规则。

已读 [首批原始输出](p3-sphere-revolve-c1.txt)：44 passed。该证据继续有效；它未覆盖 R09 的矛盾方向情形。准确命令/环境及冻结关联待 TV 索引补录。本批结论为 **T13.i CHANGES（R09）；T13.h 静态范围无阻塞，待运行元信息补齐后受限接受**。两模块尚未接入 CLI，不能把旧完整报告冒充包含本批的新产物；全几何、坐标框架、裁剪、工程参数及 P3 出口仍保持未决。

### J.1 T13.h 首测元信息补齐

随后已读 [TV 索引的 T13.h/i 段](p3-diagnostic-validation.md)：项目根目录、隔离 Python 3.14.7 / pytest 9.1.1、两个新测试目录的准确首测命令及退出码 0 齐全；44 passed 是一次合批，未重跑 reader 或旧候选。球面使用线性/角度数值阈值各 1e-6，回转使用 0.001 / 0.0001，均为匹配阈值，不是几何精度结论。**T13.h 球面条件载体观察可受限接受，无本批剩余阻塞**；J 节 frame/裁剪/方向/材料/意图限制保持。T13.i 仍等待 R09 最小修复及定向新证据。

### J.2 R09 关闭与 T13.i 受限接受

**R09 CLOSED。** 仅增量复核 `_occurrences` 新增的 `edge_ref.orientation == fin_ref.orientation` 要求及新反例：翻转同一 edge_ref 的方向后输出 unresolved，保留 confirmed/execution=false 和方向来源诊断。已读 [两个节点定向输出](p3-revolve-r09-retest.txt)：冲突反例与受影响真实载体正例均通过，2 passed、退出码 0；[TV 索引](p3-diagnostic-validation.md)保存准确命令和环境。原 44 项首次证据继承，没有全批重跑或 NX 调用。

**接受 T13.i 的受限样条回转载体观察，无剩余本批阻塞。** 这仅补齐已知拓扑方向合同，不证明 fin 遍历与几何参数方向关系、完整裁剪、载体到实体构造或可编辑工程参数。T13.h/i 尚待新 CLI 接线及其首次证据才能形成各自新报告，既有报告不自动升级；后续审查仅覆盖新增接线/产物。本轮 I/J 接受均为 P3 部分交付，不批准 P3 DONE 或进入 P4。

### J.3 球面/回转面 CLI 接线与新报告

仅增量审 `run_p3_analysis.py` 的两个 recognizer 接入、新 `test_analysis_sphere_revolve_integration.py`、原 detail 集成 helper 新增的两个 mock 及新报告；J.1/J.2 已接受算法直接继承。入口只在 detail 模式调用两模块，保持相同库存来源、外来 snapshot 拒绝及独立新输出；原 helper 未放宽既有断言。新测试涵盖真实两来源各自候选/原证据路径/未确认门禁、缺失球面数据保留 unresolved 和输出冲突拒绝。

已读 [首次接线输出](p3-sphere-revolve-integration-c1.txt)：5 passed、2 subtests passed、退出码 0；[TV 索引](p3-diagnostic-validation.md)保存准确命令、Python/pytest 环境及重验旧 helper 影响的原因。未重跑模块 44 项或 native 读取。TV 在新父目录下各首次生成 [ANALYSIS-05](../../../workspace/v3/p3/P3-ANALYSIS-05/model-plan.json) 和 [ANALYSIS-06](../../../workspace/v3/p3/P3-ANALYSIS-06/model-plan.json)，两条命令退出 0。

只读产物核对：05 来源为 sphere/native-01 的独立 snapshot，仅新增 F0023 球面观察；06 来源为 native-02-f0004 的独立 snapshot，仅新增 F0004 样条回转载体观察。两者分别关联各自三条/四条来源边、原始 topology 与证据路径，均 observation、confirmed=false、execution=false；每份 224 条候选/未解记录，0 面已解释、235 面未解释。坐标框架及 UV 限制继续保留。两份报告均未传 relation decision、无 relation_intents，符合 ANALYSIS-03 确认不能隐式跨 snapshot 复制的边界；ANALYSIS-04 的既有确认仍然有效，不是被撤销。

**本次有界接线与两份首次产物接受，无新增阻塞。** 01—04 未覆盖，05/06 不是跨快照完整几何合并账；工程意图、完整裁剪和参数化构造仍按 I/J 限制验证。本节不扩大实机读取范围，不审尚待单独派单的空间分组或补读建议，不批准 P3 DONE。

## K. T13.j 四个新目标的逐项受控读取计划预审

范围仅 [空间工作分解](../../../docs/v3/sample-regional-workbreakdown.json) 的四项读取建议与 TL 最新收窄计划，不验收该文件全部空间分组/204 条跨组边，不重审 T13.f 已接受实现，不运行测试或 NX。**未发现阻塞下述限定计划的新增技术问题；放行条件仍是新隔离 runtime/副本关联、当前绑定与逐项守卫成立，不能将本节作为实际读取成功证据。**

只读对照已接受 P1 原生库存，在 0.001 mm 包围盒匹配阈值、准确 surface/UF type 和边数条件下，四项各只匹配其本身；selector 仅含 label、surface_type、uf_type、bounding_box、edge_count，没有旧 Tag/JID。该检查只是读取已有 JSON 的输入域核对，不是 NX 重读或几何等价验证：

| 顺序 | P1 来源标签 | 入口类型 | P1 四条边的类型观察 | 本次取证目的 |
| --- | --- | --- | --- | --- |
| 1 | F0024 | UF20 / Swept | 2 Linear、2 Spline | 相邻局部单元另一侧生成线及边界 |
| 2 | F0125 | UF19 / SurfaceOfRevolution | 3 Circular、1 Intersection | F0004 邻面载体与肩部局部边界 |
| 3 | F0138 | UF19 / SurfaceOfRevolution | 4 Circular | 球面/平面邻接过渡的载体与边界 |
| 4 | F0046 | UF19 / SurfaceOfRevolution | 1 Spline、2 Intersection、1 Circular | 头部复杂面群中的一个来源面 |

机械 JSON 当前仍写入口一般能力“1 或 2 selectors”和 batch 1/1/2/2；TL 的最新计划明确收窄为 **每次只读一个目标，按上述顺序最多四次**，本节以该收窄计划为准。TL 须在具体队列/台账中持久化单目标顺序和停止条件，不能把旧 batch 分组直接作为两面请求。此次不重读 F0002/F0005/F0023/F0004，也不自动追加第五个目标。

执行前使用新独立参考副本、新会话、已接受 T13.f 制品的隔离 runtime 与来源关联记录；不得使用关机前会话、凭据或 Tag。每项使用新的 takeover/当前 ownership、epoch、revision，当前选体库存重新唯一定位并校验当次边白名单，各自独立证据目录。只有上一项完整 clean、前后库存可比较且 diff 空、无停写并已 RETURNED/HUMAN_OWNED，才可考虑下一项；入口 dirty、无法授权/匹配、异常边类、unsupported native data、溢出或其他不完整读取都按计划停止队列，不因拿到部分字段继续追加。

首次 dirty/UF error/一致性故障或 UNKNOWN 后停止剩余查询，仅既有必要 cleanup、保留 payload 并冻结；不得重放或自动解冻。按用户持续批准的恢复方式正常退出本次受控副本且不保存，不强杀、不热换；记录实际归还/退出与磁盘保全，发生 UNKNOWN 时不得把关闭冒称正常 ownership 归还。正常末项完成也需实际归还/退出和保全记录。若仅是既有 `geometry_details_complete=false / INCONCLUSIVE`，须区分其已知全几何限制与新增 unsupported/溢出等故障，不把该常规字段本身冒充读取失败或全几何通过。

残余风险未关闭：根曲面或生成线可能进入尚未实测的 BREP/ARC 路径，P1 类型和边观察不能证明这些调用无副作用；既有逐调用守卫只能控制可观察故障后的继续行为，不能预先保证四次成功。每个结果只适用于该来源面，不外推同群/左右/22 个重复成员。最多四项后先评估实际边界、生成规律与材料角色仍缺什么，再限定下一任务；不得无上限累积代表面或据此关闭全几何/设计意图/P3 出口。实机后仅新增运行证据需独立审查。

### K.1 T13.j 四次首次单目标实读证据

仅审 [P3-REGIONS-01 队列](../../../workspace/v3/p3/P3-REGIONS-01/read-queue.json)及各新原始响应/summary/退出记录，不重审代码、不运行测试或 NX。**四个来源面的本次受限读取未发现新增阻塞，实际结果支持 clean 读取与分别归还；最终正常退出和读后磁盘保全仍待补，不提前接受整个运行收尾。** 队列已持久化每请求一个 selector、固定四目标顺序及停止规则，解决 K 节旧机械分批建议与执行计划的区别。

| 新证据目录 | 唯一匹配目标 | 实际根几何 | clean native 事件 | 圆边 EVAL 事件 | 原生载体字段观察 |
| --- | --- | --- | --- | --- | --- |
| [native-01-F0024](../../../workspace/v3/p3/P3-REGIONS-01/native-01-F0024/detail-snapshot.json) | F0024 / UF20 | 206 | 59 | 0 | 方向 (0,-1,0)，生成线 type102、order4、7 极点、非有理 |
| [native-02-F0125](../../../workspace/v3/p3/P3-REGIONS-01/native-02-F0125/detail-snapshot.json) | F0125 / UF19 | 204 | 71 | 18 | 环面 R=3.151110158218 mm、r=0.7363898417823 mm |
| [native-03-F0138](../../../workspace/v3/p3/P3-REGIONS-01/native-03-F0138/detail-snapshot.json) | F0138 / UF19 | 204 | 75 | 24 | 环面 R=24.08318915758 mm、r=6 mm |
| [native-04-F0046](../../../workspace/v3/p3/P3-REGIONS-01/native-04-F0046/detail-snapshot.json) | F0046 / UF19 | 204 | 63 | 6 | 环面 R=24.68073994091 mm、r=15 mm |

每份均恰一项 MATCHED、matching_count=1，原请求与 K 节 descriptor 相同；match/curve/surface 三参数均 0.001 mm。native 事件序号连续，called=true、dirty_before/after=false，有返回码的调用均为 0；首两项为 UV/topology，末项 topology release。BREP geometry 查询及释放次数分别 17/17、14/14、13/13、16/16，圆边各具六个 EVAL 阶段。四份均 CLEAN_TRACE、edge_coverage_complete=true、incomplete_observed=false、无 geometry/event overflow；managed 的八次 dirty 采样各为 false，native 摘要事件另保持 dirty=null。

四份根响应均 ok=true、read_consistency_fault=false、writes_halted=false、first_change=null；双库存保留、diff status=complete 且 changes=[]、two_native_samples_equal=true。各 summary 均 RETURNED/HUMAN_OWNED，四个独立退出记录均 Python 1，对应 geometry=INCONCLUSIVE；不是 UNKNOWN 或读取失败，也不是全几何完成。后续三项退出记录含实际 argv 及 previous_continuation_check=true，与前项完整结果相符。F0024 退出记录目前仅 target/sequence/code，准确命令/cwd 尚待从已有工具历史补入运行索引，不能凭后项推造第一项命令，更不为补元信息重放。

[runtime 复制记录](../../../workspace/v3/p3/P3-REGIONS-01/runtime-copy-record.json)关联未改的 P3-T13F-C1 五制品、隔离目录与直接字节复制比较；[source-copy 记录](../../../workspace/v3/p3/P3-REGIONS-01/source-copy-record.json)保留新独立副本和读前基线；[启动记录](../../../workspace/v3/p3/P3-REGIONS-01/launch-record.json)记新 NX PID2824。四个 reader 指向同一本轮副本；不复用旧 boot 会话。该启动/读前记录不能代替实际退出及读后磁盘保全；本节时 TL 报告 NX 仍开着但已归还，四目标队列已结束，没有新增读取获准。

残余限制保持：四份 geometry_details_complete=false，库存相同不证明全域几何未变；原生框架、UV/边界参数方向、完整裁剪、材料侧和设计关系均未关闭。三处 UF19 实际返回环面并不证明其属于相同工程特征；F0024 的样条与另一侧的关系仍须受限离线解释。先评估既定四个问题及缺口，不外推未读成员、不扩大 R05 到任意路径，不将本节作为 P3 DONE 或新实机队列许可。

### K.2 T13.j 正常退出与保全补证

仅读取新增 [首项退出/argv 记录](../../../workspace/v3/p3/P3-REGIONS-01/exit-F0024.json)、[正常退出及保全](../../../workspace/v3/p3/P3-REGIONS-01/shutdown-preservation.json)和[退出后进程观察](../../../workspace/v3/p3/P3-REGIONS-01/shutdown-processes.json)，不重跑任何比较、reader 或测试。首项准确 argv 已由 root 实际工具历史转录，明确事后补录、没有重放，参数/目标/新证据目录与原始结果相符。

归档小项仍需 TL/TV 补记该首项真实 cwd：本节读取时 exit 记录未含 cwd，诊断索引尚未登记 T13.j。应从原工具调用核实后补录，不根据相对 runner 路径自行推造，也不为补该字段重跑。此项不否定已成立的原始读取和退出/磁盘保全事实。

2026-11-09 19:08:39（Asia/Shanghai）的记录确认本轮 NX2824 在四次分别 RETURNED/HUMAN_OWNED 后正常退出、未保存；原件和工作副本磁盘字节未变，原件 mtime 未变，无 NX/Journal/helper 留存，无强杀或 DLL 热替换。**T13.j 四个新来源面的有界读取及本轮正常收尾可受限接受，无剩余读后保全阻塞。** 这是 P3-REGIONS-01 的实际新收尾，不补证或改写此前关机中断的 P3-SPHERE-01 退出历史。

本节不审机械后续载体/镜像关系推导，不把读到的不同样条表达判为相同曲线，也不把环面/平面/球载体关系视为完整裁剪或工程意图。K.1 的几何、材料侧、参数化与阶段出口限制保持；后续先进行获授的离线轮廓/最小缺失集合分析，本次四目标读取许可已经用尽，没有更多实机读取获准。

### K.3 首项 cwd 归档补齐

已只读复核 [exit-F0024.json](../../../workspace/v3/p3/P3-REGIONS-01/exit-F0024.json) 新增 cwd 为 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`，来源明确为原 root exec_command 工作目录历史。K.2 的最后归档小项已补齐，没有重跑；K.1—K.2 受限接受结论与所有几何限制不变。

## L. T13.l 单条主轴毛坯子午轮廓的三目标读取预审

范围仅 [工作分解的 y_axis_outer_stock_candidate](../../../docs/v3/sample-regional-workbreakdown.json) 中三处未直接取得的 carrier/局部边界证据，以及 TL 提出的固定三次单面读取计划；不验收 20 段轮廓全体的精度、闭合、毛坯包络、材料角色或可执行构造，不审新增 flank 工程参数方案。**本次限定取证目的与输入域未发现新增阻塞，可按以下前提准备新队列；不是实际读取成功或完整轮廓放行。**

只读核 P1 库存和三个无 Tag/JID descriptor：按 UF19/SurfaceOfRevolution、六个 bbox 分量各 0.001 mm 匹配阈值及准确边数，每项均只匹配其指定来源面。顺序与最小范围为：

| 顺序 | 新目标 | P1 实际边数/类型 | 独立证据缺项 |
| --- | --- | --- | --- |
| 1 | F0169 | **48**：14 Circular、34 Intersection | 正 X 肩部根载体、轴向中心/分支及到 R12.1665/R13 的局部有向边界 |
| 2 | F0167 | 4 Circular | 正 X 颈部根载体、中心/分支及 y=-52 到 -49 的边界 |
| 3 | F0066 | 4 Circular | 正 X 上缘根载体、中心/分支及 y=14 到 17 的边界 |

F0169 的准确 P1 边数为 48，队列不得采用口头近似“约49”作 descriptor。三项 P1 AskFaceData 的 origin Y 分别为 -68.38205261748568、-50.5、15.5 mm；它们不是已验证的环面中心。radius/radius_data、bbox、相邻解析面和 JID 文本不能单独证明所拟环面根类型、支路及有向修剪。已有 F0005/F0138 等载体在别的来源面，不提供这三项的等价映射；本次只读材料中没有足以严格替代其中一项的解析证明。因此未建议为减少调用而将任一假定中心写成事实，也不为复用形式重读旧面。

TL 须先持久化确切三目标单面队列、selectors 和停止条件，使用新独立副本、新会话及已接受且未改的 T13.f 隔离制品；制品/源副本关联有据，每项重新取得当前绑定与凭据。只在前一项 clean、双库存完整 diff 空、无停写且 RETURNED/HUMAN_OWNED 后继续；当前库存中重新唯一定位、边白名单仍按原合同，不使用旧 Tag。每项目录独立，不能合并为多面请求；完成三项即停止，不自动读 F0126/F0168/F0160 或其他面。

F0169 边数明显更多，Intersection 的样条规模、拓扑及事件量仍未知。原 **900 KiB topology、2 MiB 单面、4096 events** 硬门禁不放宽；不凭边数推定必能装入预算。首次 unsupported、溢出、UF error、dirty、库存不一致或 UNKNOWN 停止全部剩余目标，按已接受守卫仅必要 cleanup、保留 payload/冻结，不重试或改预算继续。随后按用户持续批准正常关闭本次独立副本且不保存，记录真实归还/退出及磁盘保全；故障关闭不冒称正常 ownership 归还。

三项即使成功，也只提供该来源面的原生载体和有界拓扑字段；仍可能不足以证明子午线修剪端点、20 段连续关系、全旋转包络或真实材料域。对侧 F0126/F0168/F0160 未自动匹配/验证，全部 142 个相关面不在本次范围，固定全周旋转和端面填实仍是规划假设。不得把同一 UF19 名称或拟合标量视为同一曲面，不据此进入 P4 实建或宣称 G 通过；实机后只审新增证据，再决定哪些依赖已足够、哪些仍明确阻塞。

### L.1 T13.l 三次原生读取及收尾接受

仅核 [P3-STOCK-01 队列](../../../workspace/v3/p3/P3-STOCK-01/read-queue.json)、三个新原始 snapshot/summary、各 exit 记录及读前/退出保全记录；已接受代码和测试直接继承，未调用 NX 或重跑比较。**三目标的限定读取与本轮正常收尾可接受，无新增阻塞；不接受整体毛坯包络、子午闭合或完整几何。**

| 新原始证据 | 唯一匹配 | clean native 事件 | 根 type204 的 center Y / major R / minor r（mm） |
| --- | --- | --- | --- |
| [native-01-F0169](../../../workspace/v3/p3/P3-STOCK-01/native-01-F0169/detail-snapshot.json) | F0169，48 边 | 687 | -69.76410523497 / 17.1665 / 5 |
| [native-02-F0167](../../../workspace/v3/p3/P3-STOCK-01/native-02-F0167/detail-snapshot.json) | F0167，4 边 | 75 | -52 / 16 / 3 |
| [native-03-F0066](../../../workspace/v3/p3/P3-STOCK-01/native-03-F0066/detail-snapshot.json) | F0066，4 边 | 75 | 15.732050807570001 / 43 / 2 |

三次各恰一个 selector/detail、matching_count=1，描述符与 L 节一致；事件序号连续，called=true、dirty_before/after=false，有返回码的调用均为 0；均以 UV/topology 开始、topology release 结束。F0169 有 179 次 geometry 查询与 179 次释放，14 圆边各六次 EVAL；后两面各 13 次 geometry 查询/释放和四圆边 EVAL。三份 CLEAN_TRACE、incomplete_observed=false、edge_coverage_complete=true，event/geometry overflow=false；较大的 F0169 本次未触限，不由此推出更大拓扑也能读取或允许放宽预算。managed 的八次 dirty 采样各为 false，native 摘要项 dirty=null 保持语义区分。

三份均 ok=true、无 read fault/halt、first_change=null，完整 before/after diff status=complete、changes=[]、two_native_samples_equal=true；各自 summary 为 RETURNED/HUMAN_OWNED。三份 exit 均保存准确 argv/cwd 与 Python 1，后两份含前项 continuation check；该码仍表示 INCONCLUSIVE，而非 UNKNOWN 或全几何通过。运行命令、路径和结果由 [TV T13.l 索引](p3-regional-read-index.md)关联；未新增第四次读取。

[制品关联](../../../workspace/v3/p3/P3-STOCK-01/runtime-copy-record.json)记录未改 P3-T13F-C1 五制品直接字节复制及新隔离会话；[源副本记录](../../../workspace/v3/p3/P3-STOCK-01/source-copy-record.json)保存独立工作件/读前基线，[启动记录](../../../workspace/v3/p3/P3-STOCK-01/launch-record.json)与三份结果的 NX14752 相符。[收尾](../../../workspace/v3/p3/P3-STOCK-01/shutdown-preservation.json)及[进程观察](../../../workspace/v3/p3/P3-STOCK-01/shutdown-processes.json)确认 2026-11-09 20:27:23（Asia/Shanghai）三次归还后正常退出、不保存，原件/副本磁盘字节和原件 mtime 不变，无 NX/Journal/helper，无强杀或热换。

实读中心/半径与先前规划数字相符，只把那些数值从假设补为三个指定来源的 native 字段；没有验证整个 20 段截面、坐标解释、裁剪分支、材料域或对侧面。geometry_details_complete=false 和全域限制继续保留，R05 不扩大到任意路径。M 节首次 section 产物保留其当时 unresolved 状态，不自动改写为已闭合；后续新的 C0 规划或 knot-insertion 数学工具须冻结后各自审查，不在本节提前接受。三目标许可已完成，无新实机队列获准。

## M. T13.k 独立齿侧样条与截面规划合同审查

范围仅 `section_candidates.py`、`test_section_candidates.py`、[原始用户表达选择](../../../docs/v3/decisions/p3-independent-flanks-user-decision.json)及 [P3-SECTION-01 首次产物](../../../workspace/v3/p3/P3-SECTION-01/section-candidate.json)。旧 IR/CLI/model_plan 和已接受识别器、原生读取直接继承；评审未测试或操作 NX。**当前限定的来源绑定与 planning-only 合同无新增阻塞，可作为 P3 部分交付接受；真实截面与可编辑参数方案仍未完成。**

用户确认只覆盖两条独立样条保留原始差异、控制点尺寸及端点约束作为拟议表达，并固定各自原阶数/节点；没有确认裁剪区间、全部极点的有效驱动作用、精确端点接触/相切条件、编辑域或全部 22 齿形相同。模块精确核该决定的 ID/答复/四项 scope，以及两个不同 snapshot、选择标签与各自 observed_basis；来源路径限定在项目内，重复 JSON 键、混合 snapshot/summary、错误节点/全域或新增 scope 被拒绝。它是本样件两条指定来源的有界合同，不是任意零件的通用截面识别器。

两侧读取使用各自已归还的原始 detail/summary，并经已接受 normalizer 与样条拉伸观察识别；输出不重新标成共同 snapshot。只读核首次产物中每个 original_generator 与其实际原始生成线完全相同，分别保留不同节点矢量、order4、7 个单位权重极点及原全域 [0,1]。face_uv_box 另存、映射未验证，actual_generator_trim.interval=null；没有将首末极点当修剪端点，也没有静默裁剪/重节点后称保留原基。source 的 F/E ID 各属自身快照，共同截面坐标框架仍未验证。

端点合同目前是 C(a)/C(b) 的拟议 point_on_carrier，a/b、carrier 与实际对应均 unresolved；`driving_parameters=[]` 如实表示尚未实现驱动项。control-point active support、实际使用者、约束可解性和编辑域各有独立 open requirement。接受这些记录不等于证明全部极点影响可见裁剪段，更不等于独立编辑后仍保持封闭、接触或有效实体。

固定六节点 DAG 明确区分两段样条、局部 sketch_loop、stock_meridian、stock_revolve 与 local_modification；依赖引用存在且无循环，端点/活动支撑/全部有向边/闭合、材料侧、终止和布尔顺序未被绕过。毛坯引用当前 20 段原候选和原假设，F0169/F0167/F0066 在本产物中仍列 unresolved，闭合/full-rotation/material-role 未验证。节点 kind 只是规划类型，不是可直接交现有 IR 或执行器的实体/草图操作；本合同没有实现任一约束求解或参数使用者。

[首次新文件输出](p3-section-contract-c1.txt)为 2 passed、7 subtests passed，退出码 0；[TV 索引](p3-diagnostic-validation.md)保存准确命令、Python/pytest 环境和一次实际 API 产物生成命令。测试核真实原生成线保留、两来源拆分、UV 与全域分离、typed DAG/全部阻塞状态，并覆盖错来源/错 basis/额外授权范围/混合归还摘要等拒绝。首次产物为 planning_only，geometry_proven/edit_domains_confirmed/execution_approved 均 false；旧算法和 reader 未重跑。

下一可验证进展应是具来源和明确坐标/参数语义的实际修剪与端点对应、原基上的有效支撑及使用者定义，再据此形成闭环、可解约束和有效编辑域；仅增加更多 blocked 节点或 false 标记不能完成 T13。机械 FIN/SP 与三维边系数分析未由本节独立证明，不作为关闭几何门禁的证据。M 节接受不关闭完整截面、整件覆盖或 P3 出口，也不扩大实机范围。

## N. T13.m 给定非有理样条区间限制数学工具审查

范围仅 `spline_restrict.py`、`test_spline_restrict.py` 与本批首次证据；未运行测试、NX 或 P6 比较器，未审变化中的 stock_profile。**未发现阻塞当前给定表达式数学合同的新增缺陷，可受限接受；不据此确认源面实际裁剪、坐标映射、工程驱动参数或完整几何。**

### 算法与来源依赖

输入仅非有理、无 weights 的有限且可准确表示为 binary64 的数值，order≥2、节点非降、有效 a<b 位于活动域内；节点重数不超过 order，活动域内部 full-order 不连续节点拒绝。后者避免在同一个闭区间端点暗中选择不相同的左右值。整数转 float 如不能精确表示即拒绝，不把大整数先舍入成另一个问题。

`_insert` 的 span/multiplicity 三段控制行范围与单次 Boehm 插入一致：左段保留原行、右段复制前一行，中段使用 `(u-U_i)/(U_{i+p}-U_i)` 的精确凸组合。分别把 a、b 的重数升到 order，再以首个 a 和末个 b 裁出节点及同索引控制行；结果保留区间内原节点，端点钳制，非钳制源端也有首测。Fraction 全程解释原 binary64 数值为精确有理数，没有按门限把 a/b 吸附到邻近原节点。

原 poles 到派生 poles 的矩阵以精确分子/分母保留；行非负且和为 1，派生 poles 不是独立工程参数。source_influence 的 `upper_exact` 是矩阵对应列最大系数所给的原基函数上界，不是声称已求得该基函数精确 supremum。只有整列精确为零才 inactive，极小非零依赖不抹去；support_interval_hull 明确只是支撑闭包，不承诺两个端点处非零。source 原 basis/data 保留，两齿侧各自传入，不做镜像或相同基假设。

### 统一位置界与数值边界

精确派生点为 Qᵢ，输出一次 binary64 舍入点为 Q̂ᵢ；程序用 Fraction 精确计算 `E = max_i Σ_d |Qᵢ,d − Q̂ᵢ,d|`。由于同一个输出节点/阶次上的非有理 B-spline 基函数非负且和为 1，对给定闭区间每个 t，`||C(t)−Ĉ(t)||₁ ≤ E`；同单位欧氏范数也不大于该 L1 界。逐坐标界分别成立。输出节点全来自原节点/a/b 的 binary64 值，未引入新的节点舍入项。

`_upward` 将精确非负界转 float 后再转回 Fraction 比较；如低于精确值，以 nextafter 朝 +∞ 上调。静态检查：正数下溢成 0 时会升到最小正 subnormal，不错误报告零；恰好精确零保留零；转换溢出返回 +∞，仍是保守界，但没有有限精度信息，后续不能把 +∞ 当作精度通过。派生 poles 另拒绝非有限结果；正常插入的凸组合不会超出有限源坐标的凸包。误差和/差使用 Fraction，不先作浮点求和造成误差界下估。

这里界定的是“以给定 binary64 输入为精确表达式”的原曲线与“以输出舍入 poles 为精确表达式”的派生曲线之差；不包含后续数值求值器运算舍入、NX 源近似、坐标变换、内核、未验证实际 trim 或编辑后的重算误差。没有单位换算；FIN 混合参数坐标的 L1 数值不能据此标成毫米几何误差。新调用者需根据自己的坐标单位、求值/编辑链重新说明适用界，不能把本数学界搬成整件 G 结论。

### 已有验证及接受限制

已读 [首批 25 passed](p3-spline-restrict-c1.txt)，退出码 0；[TV 索引](p3-diagnostic-validation.md)保存项目根目录、Python 3.14.7 / pytest 9.1.1 和准确命令。测试逐个共同非零 knot span 取 order 个不同精确有理节点，配合两表达式次数≤order−1 的性质证明该测试曲线每段多项式恒等，并另核闭区间端点；这不同于有限浮点拟合误差采样，但也不泛称测试穷尽了任意输入。

首测包含多重节点、未钳制源、相邻可表示端点的极短域、全零列/微小非零列、非法输入及两个实际齿侧三维生成线。真实 a/b 为外部显式观察数，测试没有证明它们是实际修剪域。FIN 案例仅为数学输入。首测未单独实测 max-float/subnormal 极端路径，本节上述数值边界为代码/数学审查，不伪造为运行证据；若后续接入要求这些运行边界，再据新接口风险做最小针对验证，不重跑本批已有效矩阵。

当前接受限于该数学工具。原控制点的真实可见作用、使用者与约束、两侧共用坐标、端点载体关系、可解编辑域以及真正源几何偏差仍未由本批关闭；M 节的规划合同不会因工具存在而自动变成已实现截面。P3 出口和任何 P4/P6 执行均未放行。

## O. T13.n 单子午毛坯数值规划首评

范围仅 `stock_profile.py`、`test_stock_profile.py`、`run_stock_profile.py`、本轮 meridian-proposal/plan 和 [用户线性目标记录](../../../docs/v3/decisions/p3-linear-geometry-target.json)；既有原生读取与 IR/model_plan 不重审。评审未运行测试或 NX。

### 发现（按严重度）

1. **R10 / 中等 / OPEN：与底部闭合边重叠的轮廓仍标为简单环。** [stock_profile.py](../../../src/nx_sketch_mcp/v3/stock_profile.py) 首评第 299—315 行的 same-y 方向检查从 0 开始，只看 `segments[:-2]`，遗漏末尾 bottom closure 到首段的周期连接。具体静态反例为外链 `(y,r)=(0,2)→(0,1)→(2,1)→(2,0)`，再经轴到 `(0,0)`、底边到 `(0,2)`；首段使用 y=0 平面，后续用 R1 圆柱与 y=2 平面，全部现有检查可通过且面积非零，但首段与底边在 r∈[1,2] 重叠。报告仍给 `simple_by_monotone_chain=true`，会把不合法的重叠草图边链作为简单截面。最小修复是把底部闭合边的径向正向延续纳入起始 same-y 运行，或明确拒绝初始同 y 向内段；新增该负例及初始合法向外径向段正例，仅定向验证受影响闭合检查。当前样件首段 y 严格增加，因此不要求据此重做原生或全部旧样件验证。

2. **R11 / 中等 / OPEN：环面详细库存缺少单位门禁。** 同文件 `_torus` / `calculate_profile` 核了 P1 与 proposal 为 mm，却没有核每个 detail inventory 的 unit。把同样的 center/R/r 数值声明为 inch 或缺少单位仍会以 mm 构造圆弧、输出毫米面积与残差；源 frame 标为 unverified 不能使单位混用合理。新合成 torus fixture 恰未提供 unit，首测因此没有覆盖此拒绝合同。最小修复为本受限 mm 路径显式要求每份 detail unit=mm，单位缺失/未知/其他单位均拒绝；补最小负例并使合法 fixture 显式带 mm。此次实际四个已接受来源是 mm，这个缺口不否定已有实读证据，也不要求重跑 NX。

3. **R12 / 低 / OPEN：新报告仍把已取得的三面 root 写成“尚未直接读取”。** [meridian-proposal.json](../../../workspace/v3/p3/P3-STOCK-01/meridian-proposal.json) 的末项 assumptions 及 s8/s10/s19 source_description 从早期工作分解继承，当前 [meridian-plan.json](../../../workspace/v3/p3/P3-STOCK-01/meridian-plan.json) 原样输出，与已经加载的 F0169/F0167/F0066 type204/中心/半径来源发生表述冲突。后果是交接者无法区分尚缺 root 还是仅缺 trim/frame/包络。最小修复为明确这些是历史原提案描述，另列本次已实读载体与仍未验证的分支/修剪边界，或更新新的规划描述后生成新编号产物；保留首次报告和原证据，不手改原始读取、不以文案变化触发旧测试重跑。

### 已核数学和边界

圆弧以 `y=cy+ρ cos(t), r=R+ρ sin(t)` 表达，固定径向分支限制到半圆；从原建议 y 计算共享顶点，并记录调整距离，再核相邻直线的 P1 carrier 残差。正 y 单调半圆分支的径向内部极值发生在 y=cy；实现将该点纳入 radial_range，不只比较两端。实际 F0066 候选内部半径最大 45 mm，超过端点半径，已在首次测试中断言。圆弧对 Green 面积积分的三项 `ρcy·Δsin − ρR·Δcos + ρ²Δt` 与参数式一致；直线用叉积。非有限/近零累计面积被拒绝，但这是 double 数值结果，没有精确面积误差证书；不能当作用户几何精度达标证据。

共享顶点提供计算轮廓的 C0 邻接，不能证明源面边界一致或相切。除 R10 的闭合接缝遗漏外，y 单调、内部正半径与每个同 y 连续运行不反向是此受限简单性判定的依据；没有声称支持任意非单调轮廓。圆弧投影后相邻线段允许在 matching 阈值内偏离载体，残差有记录，不冒称每条数值线都与源解析载体精确重合。需要保留拟议截面、真实修剪、材料角色与包络四者的区别。

实际首次产物含 20 条来源候选段加轴/底闭合共 22 段、四圆弧，signed_area=-3754.326404926589 mm²；此值仅记录本次规划计算。2π 明示为 TL 对辅助毛坯的构造选择，不能证明原件全周等价；[0.001 mm 用户目标](../../../docs/v3/decisions/p3-linear-geometry-target.json)仅作为后续验收目标引用，报告 not_evaluated，没有与数值 epsilon=1e-9 mm 或探索 matching=0.001 mm/0.0001 rad 混为已达精度。source_geometry/whole_stock_envelope/execution 门禁均 false，但它们不能代替 R10/R11 所缺的有效输入与简单环判断。

已读 [本批首测](p3-stock-profile-c1.txt)：6 passed、17 subtests passed。该首次证据保留，不覆盖上述两个新增缺口；当前结论为 **CHANGES**，等待最小修复/定向证据及清晰的新产物。不得将简单数值毛坯规划接受扩成 P3 整件完成、材料侧已知或 P4/P6 执行许可。

### O.1 R10—R12 有界修复预核（待定向证据）

2026-11-09，由恢复后的独立高级实例 `/root/p3_review_continue` 追加。继承 A—N 已接受结论，特别是 R05/R09 的受限关闭与 N 节 25 项数学工具证据；未重审旧矩阵、运行测试、操作 NX、执行 Git 或计算 hash。只审 `stock_profile.py`、新增 seam/unit 测试和 [C2 提案](../../../workspace/v3/p3/P3-STOCK-01/meridian-proposal-c2.json) 的本次差异范围。

**当前未发现修复引入的新阻塞；R10—R12 暂不关闭，等待 TV 最小定向结果及新 C2 plan。** R10 的 same-y 方向初值改为 +1，把由轴向首顶点向外的底闭合段纳入周期接缝；第一段若同 y 向内即拒绝，若向外则允许，首次严格增 y 后重置。末端仍在 outer 中，原有同 y 方向检查继续拒绝顶部径向回折。新增测试包含底部重叠/合法向外、顶部重叠/合法向内四种情形。无需因此重验原生读取或旧数学工具。

R11 在 `_torus` 使用详细库存前要求显式 `unit=mm`，缺失、unknown、inch 均拒绝；合法合成 fixture 已补 mm，新增用例同时保留合法正例。实际四份毫米来源的受影响正例应定向检查，不把改单位 fixture 作为重跑全部 stock 测试的理由。

R12 新 C2 提案的 s8/s10/s19 与总 assumptions 明确区分历史 P1 推测、T13.l 已取得的三个 native root 和仍未知的 native-to-ABS frame、directed trim、对侧来源。首次 proposal/plan 保留。新 plan 尚未在本节读取，不以提案文本已改冒称输出已修复；待首次生成后核相应描述及门禁继续为 false 即可。

## P. T13.o 严格 session epoch 接管安全增量预审

范围仅 `server.py` 的 nx_takeover 可选字段与新 wire 路由、`bridge.py` 命令白名单、`M2Bridge.cs` 严格接管分支、[接口合同](../../../docs/v3/session-epoch-takeover.md)、两个新 session epoch 测试文件，以及 `run_reference_detail_once.py` 可选 flag。不审未实现的 42 面队列，不变更或重验旧 reader/native，不据此批准新的 NX 操作。

**静态未发现当前增量的阻塞缺陷；结论为待冻结关联与定向验证，尚非运行接受。** `expected_session_epoch` 限制为规范正整数 PID:UTC ticks，与 expected_pid 一致且不超 DateTime.MaxValue。有字段时只发送 `ownership.takeover_if_session`；不带字段仍走原四参数 `ownership.takeover`。C# 两个 wire 分支分别要求准确键集合，旧命令不能偷偷接收 strict 字段；Python 调用失败不尝试旧命令。旧后端未知命令拒绝须由既有旧制品的首次新命令负例佐证。

`Start` 捕获 `_processId` 和进程启动 UTC ticks 组成 `_sessionEpoch`，无模型查询。严格 Takeover 在同一 `_lifecycle` 锁内检查 stopping、粘性停写、HUMAN_OWNED、PID 和 epoch，随后才设 TAKEOVER_CHECK、增加 binding epoch 和创建 adapter 工作；不一致不会排队或调用 adapter。该校验绑定进程世代，不证明同一进程内桥重载实例或模型状态；load_instance、当前 ownership/binding/revision 与所选独立零件仍须后续原有合同验证。UNKNOWN 不会因匹配新 epoch 自动清除。

once 新 flag 在建连前核格式，传入 nx_takeover，并在读取前核成功回包的 session_epoch 等于请求；不符保留 uncertain/STOP_MANUAL_CHECK，不继续 inspect 或自动归还。未提供 flag 的默认路径保持原语义。协议文件计划覆盖 legacy/strict 路由、非法输入、old-backend 无 fallback、host UNKNOWN；C# 文件计划覆盖缺失/错误/stale epoch 的零 adapter 调用和不增 binding epoch、匹配接管/归还及旧后端拒绝。以上是已读测试代码，不是通过声明。

关闭本预审待办的最小证据：SI 对 `v3-p3-t13o-c1` 编号源码/构建输入/制品关联的冻结记录；TV 首次执行上述新用例；once 可选 flag 的最小 mock 成功转发与返回 epoch 不符时零 inspect 证据。无需全量旧 bridge/reader 回归或真实 NX 重跑。离线通过仍不能证明生产 NX 实际加载该制品或授权任何新目标；新实机队列、隔离部署、当前进程世代、来源保全和归还证据须由其另行受限计划处理。

### O.2 R10—R12 定向证据关闭与 C2 规划接受

本节仅收口 O.1 待办；只读新增日志、TV 索引、测试覆盖及新 plan，没有重测。**R10、R11、R12 CLOSED；当前受限毛坯数值规划可接受为 P3 部分交付，无新增阻塞发现。** [定向原始日志](p3-stock-profile-c2-retest.txt)为 5 passed、3 subtests passed，[TV T13.n C2 索引](p3-diagnostic-validation.md)记录退出码 0、项目根 cwd、Python 3.14.7 / pytest 9.1.1 及准确五节点命令。旧矩阵不重跑。

R10 的底部重叠负例与合法向外正例、顶部回折负例与合法向内正例均在该五节点范围内，直接验证 O 节失效机制及修复后的边界。R11 的显式 mm 正例、缺失/unknown/inch 三反例成立；实际四载体来源与合成圆弧两个受影响正例通过。该证据与 O.1 静态修复核查共同关闭缺口，不扩大为任意轮廓简单性算法。

R12 已核 [meridian-plan-c2.json](../../../workspace/v3/p3/P3-STOCK-01/meridian-plan-c2.json) 的三处 source_description、总 assumptions 及 source_evidence：分别对应 F0169/F0167/F0066 的既有快照与 native root；不再把已取得 root 写成尚未读取，仍明确 frame、directed trim 和对侧面未验证。TV 记录以 C2 proposal 首次独占生成，退出码 0，旧提案和首次计划保留。

新报告为 planning_only，22 段/4 圆弧，数值闭合与受限简单性为 true，面积仍 -3754.326404926589 mm²；这些仅是给定拟议截面的计算结果。source_geometry_proven、whole_stock_envelope_proven、execution_approved 仍 false，stock_revolve 仍 blocked，0.001 mm 用户目标仍 not_evaluated。真实修剪/材料侧/包络、全周构造适用性、可编辑参数与后续几何精度仍须各自证据；不关闭 P3 整件出口，不批准 P4/P6 或新 NX 操作。

### P.1 T13.o 首次离线行为证据受限接受

**已测 C1 二进制及本次 Python/runner mock 的新增离线行为可受限接受；完整冻结源码到制品链仍待核，不能据此接受新的 C2 二进制或放行 NX。** 本节只核 [原始输出](p3-session-epoch-c1.txt)、[TV T13.o 索引](p3-diagnostic-validation.md)及其准确测试范围：10 passed、27 subtests passed，退出码 0，环境与 O.2 相同。未运行任何测试或构建。

新协议四项覆盖 legacy/strict 路由、非法 epoch 写前拒绝、UNKNOWN_COMMAND 不回退及 host UNKNOWN 阻断。C# 两项通过实际 `v3-p3-t13o-c1` fake host/helper 验证缺失/非法/stale epoch 失败时 ownership 仍 HUMAN_OWNED、binding epoch 未增且 takeover adapter 计数为零；匹配 epoch 接管/归还及 legacy 正例成立。旧 `v3-p3-t13f-c1` 对新命令返回 UNKNOWN_COMMAND 且状态/计数不变。C# 冻结守卫本次由 P 节静态审查及继承门禁支持；不把 host UNKNOWN 测试误报为新 C# 冻结故障注入。

once 三个新增节点及受影响 legacy 正例已覆盖：合法 epoch 原样传入且返回后才 inspect；回包缺 epoch、错误 epoch、明确拒绝及旧后端拒绝均仅一次 takeover，零 inspect/return、不自动 close，状态为 STOP_MANUAL_CHECK；十种非法 flag 在任何调用前拒绝且无证据文件。默认请求未携带可选字段。至此 P 节所需新增控制流验证已提供，无需重复这十项或旧 reader 矩阵。

TV 明确 C1 缺少完整可追溯冻结源码快照，因此这些结果只属于实际被测 C1 制品及当前 Python/mock。后续 SI 若产生 C2，应提供独立的源码/编译输入/输出关联和必要的最小适用性证据；本节不预判 C2 等价，不以 C1 测试替代该链路。原生辅助库、真实加载、部署与新目标运行继续按另行受限计划审查，UNKNOWN 人工恢复规则保持不变。

### P.2 T13.o C2 冻结制品链及单项行为接受

仅增量读取 `workspace/build/v3-p3-t13o-c2` 的记录、冻结关键分支及新增一项行为证据。**P/P.1 的源码到制品关联待办现关闭；T13.o 严格会话接管的 C2 候选可作为后续受控测试前置接受，无新增阻塞发现。** 未重审全项目、重跑测试、构建、调用 NX 或计算 hash；C1 Python 协议/runner/旧后端证据保持原范围继承，不将其改称 C2 新测。

[source-copy-record](../../../workspace/build/v3-p3-t13o-c2/source-copy-record.json)列 67 个不同路径，全部 direct_byte_comparison=equal；包括托管编译输入、原生源、构建脚本、此次 Python/runner/测试及合同。[build-verification](../../../workspace/build/v3-p3-t13o-c2/build-verification.json)记录构建后冻结副本仍与工作区相同、differences=[]。本节依据这些已有逐字节核对证据，不拿文件大小或 mtime 代替内容一致，也未重复比较已有效输入。

[compiler-invocations](../../../workspace/build/v3-p3-t13o-c2/compiler-invocations.jsonl)为冻结脚本实际 csc 调用行捕获的四条参数；每个 C# 输入均位于该 C2 source 快照，helper/entry 引用本次 C2 M2Bridge.dll，NX 引用来自已安装 NX2506。`build-record.ps1` 在未改冻结脚本编译行设记录断点；冻结脚本该行确为 `& $compiler @arguments`，每次非零退出立即失败。四个输出为 M2Bridge.dll、M2JsonlHelper.exe、M2Entry.dll、M2Startup.dll。[构建上下文](../../../workspace/build/v3-p3-t13o-c2/build-context.json)记录准确 cwd、命令、Roslyn 5.900.26.35703 和 NXOpen 2506.0.0.0；[构建输出](../../../workspace/build/v3-p3-t13o-c2/build-output.log)记录四次编译、既有 Swept API 废弃警告及 build complete，[退出记录](../../../workspace/build/v3-p3-t13o-c2/build-exit-code.txt)为 0。不由该编译推断旧 sweep 域得到扩展。

[执行策略首拒绝](../../../workspace/build/v3-p3-t13o-c2/preflight-policy-rejection.log)保留脚本尚未加载即被策略拒绝的事实；随后实际命令只在新 PowerShell 进程参数中使用 ExecutionPolicy Bypass，记录脚本未调用持久 Set-ExecutionPolicy。该首拒绝不隐去，也不误作一次失败编译。原生复用记录分别确认当前 cpp 与已接受 T13.f 编译源逐字节相同、复制的 ReferenceGeometryNative.dll 与 T13.f 制品逐字节相同；原生未重编、未新运行，原有受限证据直接继承。

[TV C2 单项索引](p3-diagnostic-validation.md)给出准确命令：动态加载原测试模块，仅进程内把 NEW 指向 C2，执行 `NewSessionEpochBridgeTests.test_missing_stale_and_valid_epoch_and_legacy` 一次。[原始输出](p3-session-epoch-c2-artifact.txt)为 1 test OK，退出码 0；不是十项矩阵重测。该项对实际 C2 bridge/helper 核缺失/非法/stale epoch 及旧命令带新字段拒绝、零 adapter 接管、ownership/binding epoch 不变，再核严格成功接管/归还及 legacy 成功接管/归还。新制品适用性已有此直接行为证据，不仅靠 C1 结果推定。

本接受关闭 C2 候选的冻结链与离线安全增量前置，不是生产发布、真实 NX 加载或任意读取许可。下一次受控测试仍须明确目标/停止条件、隔离 runtime 与该 C2 五制品的复制关联、当前进程 epoch、独立零件保全及安全归还；这些属于后续具体计划与实机证据。不得热换已加载 DLL，不解除 UNKNOWN，也不据本节提前接受尚未审查的 42 面队列代码或整件几何。

## Q. T13.p 有界 Swept 队列控制器离线审查

范围仅 [run_swept_queue.py](../run_swept_queue.py)、[test_swept_queue.py](../test_swept_queue.py)、[首测输出](p3-swept-queue-c1.txt)及 [TV T13.p 索引](p3-diagnostic-validation.md)；只为核新调用者的证据门禁查阅既有 once/normalizer 接口，不重审或重测原实现。未准备真实队列目录、启动 once/NX、测试、构建、Git 或 hash。

**未发现当前受限控制器的阻塞缺陷，可接受其离线实现作为 P3 部分交付；尚未批准具体 42 面运行计划。** 其固定 P1 快照中 Swept/UF20 必须恰有 42 个未读面，另外明确排除已有 F0002/F0024；各来源需四条不同边、两 Linear/两 Spline，六分量 bbox 与匹配阈值下的 descriptor 在 P1 唯一。输出只有标签/类型/bbox/边数，不传历史 Tag。固定数量与来源约束是本样件队列边界，不是通用识别能力或全体曲面支持声明。

init 仅创建固定 plan/context，不调用 NX。part 拒绝原件及其硬链接；config 必须在 run_dir 内、不能与 part 冲突，内容以直接字节编码保存并在每次调度前比较。该编码是本地配置副本，不是 hash，也不是可公开的脱敏配置。plan 每批重新与既有 P1 派生结果核对；路径/配置/非法计数/不连续产物拒绝，既有结果不覆盖。当前 epoch 由唯一操作通道提供，与固定 context 精确相等；每个子调用强制带 `--expected-session-epoch`，真正的进程世代核验由 P 节已接受的严格后端完成，不把调用者重复提供字符串当作独立进程测量。

每次显式 run 默认一项、上限四项；没有自动循环所有批次的入口。以独占创建 LOCK 串行化同目录调度，发起子进程前独占写入 selector 与 DISPATCHED，flush/fsync 记录；使用参数数组、shell=False。子进程完成后只有退出码 1 加完整 validator 成功才创建 CLEAN 并允许下一项，几何仍 INCONCLUSIVE。普通异常尽力创建 STOP 并保留 LOCK；KeyboardInterrupt 保留 LOCK 和已创建 dispatch，不依赖 STOP 一定写成。成功批次才解除本批 LOCK；已存在锁、STOP、缺 CLEAN 的 dispatch 或非连续队列均拒绝，不自动删除或重放。恢复时对连续 CLEAN 项重新核已有文件而非重读 NX；手工移除锁也不能使未决 dispatch 自动重放。

validator 不只信 CLEAN/返回码：summary 必须 RETURNED/HUMAN_OWNED、记录准确单面请求与 PID/part/P1；takeover、snapshot、status 的 session epoch、binding epoch、load instance 对应，revision 对应读取，状态无停写。既有 once 检查 managed trace 后，再调用已接受 normalizer，要求实际前后库存相同/完整空 diff、唯一 observed face 与 descriptor 相符、native 顺序/身份/成功返回码与配对释放、边覆盖、无 overflow/incomplete/dirty。失败停止后续项，不把单项归还或 P1 类型相似当作 42 面成功。

首测为 **12 passed、1 skipped、15 subtests passed，退出码 0**；准确命令/cwd/隔离 Python 3.14.7、pytest 9.1.1 见 TV 索引。调度全为 fake，覆盖默认/四项顺序、epoch、外部 STOP、锁竞争、中断与不重放、路径和硬链接。部分故障名仅通过注入 validator 抛错证明停队，不能冒称每种真实故障都分别经默认 validator 验证。另一个既有证据的临时单面切片用于默认 validator 正例；其十类字段损坏、缺 summary 和错误退出码负例有实际检查。切片修改是明确的测试 fixture，不是新的源读证据。

残余限制：目录符号链接逃逸拒绝是本次唯一跳过项，不计通过；源码另有硬链接条件 skip 分支，本次硬链接项未跳过。真实运行前使用新建普通目录/普通证据文件并核路径，无须为补该跳过项重跑旧矩阵。文件 fsync 不证明掉电时目录项和磁盘硬件持久性；任何掉电/中断仍按未知状态人工检查，不凭缺文件重放。外部 STOP 在项间生效，不能中止已在进行的读取；控制器没有强杀/超时复位，卡住时不能启动替代队列。尚无真实 42 项数据规模、完整返回与安全收尾证据；原 900 KiB topology/2 MiB perface/4096 events 门禁不因本控制器改变，首次异常停止。

后续具体计划须单独确定目标顺序与首批范围、C2 隔离 runtime 关联、当前进程 epoch、独立工作件读前保全以及退出/归还流程。Q 节只接受控制器离线边界，不授权现在 init/run，不关闭 T04.a 或 P3 整件几何、参数意图与覆盖缺口。

### Q.1 P3-SWEPT-01 具体受控实读计划接受

仅审 TL 在 Q 节之后提交的具体计划，继承 P.2/Q 及既有 native/once 证据，不重测。**本计划在下述边界内无阻塞发现，允许 TL/root 准备独立目录并按首批一面、后续显式小批执行；不是已有实机成功声明。** 本次尚未 init 或启动 NX。范围为已审 P1 生成顺序的 42 个未读 UF20/Swept、每面四边（两 Linear/两 Spline），排除 F0002/F0024；不得扩展到其他面、其他曲面类别或 P4。

目录采用独立 `P3-SWEPT-01` 父目录存工作副本、before 基线、C2 隔离 runtime 与 launch 配置；controller 子目录初始化时仅放 connection-only JSON，part 在其外的同一实验目录。connection-only 配置不带 launch、不存 token 值，只引用本实验 helper/token 路径，符合 Q 节 init 的目录约束。root 在启动前留存源件/副本保全与 C2 五制品复制关联，核新建目录、文件及祖先路径无 reparse/junction、resolve 边界正确；这项操作性约束承担本次 symlink 负例未运行的残余风险，不据此宣称恶意路径安全已全面测试。context/config 保持私有且不纳导出。

只由 root 唯一实机通道启动本次 NX2506，取得该次实际 PID:UTC-start-ticks 后初始化 context。首批 `count=1`，审实际 strict takeover 回包、唯一目标、全部 clean native/managed 证据、前后完整空 diff、无停写和 RETURNED/HUMAN_OWNED；各项成立才由 root 显式发起后续每批至多四项。每批返回 root 核状态，禁止自动调用下一批，累计至多 42 个新目标。每项仍独立一次单面请求、新 ownership/binding，不跨会话重启续队，不复用旧凭据。

数值参数接受为 `match_linear=0.001 mm`、归一化 `angular=0.0001 rad`，仅此次新面的 curve/surface requested approximation 各 `0.0001`（毫米工作件中的请求值）。既有接口允许有限正值，本次未改算法或门限；更紧请求可能增加样条规模，尚无规模成功保证。它是面向后续 0.001 mm 几何目标的数据预算，不能证明源逼近、FIN 参数坐标、坐标变换、裁剪、组合误差或整体 G 已达到该值；旧来源不因新预算重读。原 900 KiB topology、2 MiB 单面、4096 events 硬门禁保持不变。

任何 native unsupported/error/overflow、不完整、dirty、库存不一致、epoch 不符或队列异常立即停止剩余目标，保留 STOP/LOCK/dispatch 与原始证据，不重试、不跳过失败面、不加预算或自动复位。发生中断而仅存 LOCK 同样停队人工核查。采集期间冻结源码与制品；若需修改，先停止并正常收尾，不能热换 DLL。正常路径每项归还后，最终按既有授权正常退出且不保存并记录磁盘保全；UNKNOWN/故障不得冒称已正常 ownership 归还，按人工核查后已授权的安全关闭流程处理，不强杀 NX。实读后仅审新增证据；即使 42 项全 clean，也只增加受限载体/拓扑数据，不自动关闭 T04.a、真实裁剪/参数方案或 P3 整件出口。

### Q.2 P3-SWEPT-01 已完成九项及暂停保全的独立补审

2026-11-11，仅审已有采集产物和暂停记录，继承 A—Q.1 的适用源码、制品及验证结论。**未发现这九项受限采集证据的阻塞缺陷；接受其作为已取得、无需重读的 P3 来源数据。** 本审查未运行产品、validator、测试或 NX，未构建、Git、计算 hash；只解析已有 JSON 核对事实。新会话剩余队列适配及其验证不在本节接受范围。

[暂停索引](p3-swept-pause-index.md)关联的原 [controller](../../../workspace/v3/p3/P3-SWEPT-01/controller) 中，`item-01-F0008` 至 `item-09-F0072` 连续存在，依次为 F0008、F0010、F0017、F0034、F0039、F0052、F0057、F0058、F0072。逐项读取 selector、DISPATCHED、CLEAN 和 evidence 下 takeover/snapshot/status/summary；不是只信 CLEAN 标记。九个 selector 与原 plan 前九项逐字段一致，其 P1 来源快照对应已接受库存，每个 descriptor 在该库存的匹配域内唯一，实际 observed face 的 UF20/Swept、六分量 bbox 及四条边与请求一致。summary 的 P1、独立工作件路径和 snapshot ID 与原始响应及 pause-manifest 相符。

三次显式批次为 1、4、4，批记录退出码均 0；逐项 CLEAN 所记 once 退出码 1 与 summary 的 geometry=INCONCLUSIVE 相符。历史 epoch 与 [launch-record](../../../workspace/v3/p3/P3-SWEPT-01/launch-record.json) 的 PID/启动 ticks 对应；各项 takeover、snapshot、status 和 DISPATCHED 的 epoch 相同，load_instance 对应，takeover/read 的 revision 相同，binding epoch 依次为 1、3、5、7、9、11、13、15、17。结合 Q/Q.1 已审的强制 expected-session-epoch 路径，接受此次严格会话读取证据；这些历史标识不成为后续凭据。

各项内层 schema 为 v3，每项 59 个原生事件，序号连续，全部实际调用且 dirty_before/after=false，带返回码的调用均为 0；geometry 查询与相应释放配对，topology 最终释放成功，四边全覆盖。outcome=CLEAN_TRACE，failure_reason/first_dirty_sequence=null，event/geometry overflow 和 incomplete_observed 均 false。每项九条托管诊断中八个实际 dirty 采样为 false，另一个 native 聚合条的 dirty=null、outcome=CLEAN_TRACE；不将该聚合条误报为第九次 false 采样。原始拓扑保留两 Linear/两 Spline 边、root type 206 及 type 102、order 4、七极点 generator；这些是读得的载体数据，不是全形状解释。

九项均 inventory_complete=true，原始 inventory_before、inventory_after 与 inventory 实际相等，含 235 面/622 边；diff 为 complete/changes=[]，two_native_samples_equal=true，read_consistency_fault=false、first_change=null、writes_halted=false。status 的读前后 modified 均 false、dirty_changed_by_read=false、active_operations=0。**detail-status 是归还前 AI_OWNED 观察；逐项 RETURNED/HUMAN_OWNED 的依据是已审 once 在归还成功后持久化的 detail-summary，而非把该 status 误称为归还后快照。**

[pause-manifest](../../../workspace/v3/p3/P3-SWEPT-01/pause-manifest.json) 的九项 snapshot 引用与实际证据相符；remaining_selectors 与原 plan 的后 33 项逐字段相同，首项 F0077。目录中恰有九个 DISPATCHED 和九个 CLEAN，没有未决 item 或 LOCK；[STOP](../../../workspace/v3/p3/P3-SWEPT-01/controller/STOP.json) 保留 reason_type=UserRequestedPause、new_dispatch_allowed=false。停止原因是用户暂停，不能删除 STOP、修改旧 context 或重新派发已完成项；原 F0002/F0024 继续继承，共 11/44 面已取得细节。

[runtime-copy-record](../../../workspace/v3/p3/P3-SWEPT-01/runtime-copy-record.json) 将五制品关联至已接受 T13.o C2 托管与复用 T13.f 原生 DLL，并记录直接字节复制一致；[source-evidence-record](../../../workspace/v3/p3/P3-SWEPT-01/source-evidence-record.json) 的 36 个冻结 Python 文件均有保存副本，[source-freeze-at-pause](../../../workspace/v3/p3/P3-SWEPT-01/source-freeze-at-pause.json) 记录暂停时仍逐字节一致、differences=[]。本节继承这些采集期冻结证据，不以时间/大小替代内容证明，也不因正在实施后续适配而重新否定旧冻结源码的适用性。普通路径前置记录仍只证明当时观察，不扩大为并发恶意文件替换防护。

[close-request](../../../workspace/v3/p3/P3-SWEPT-01/close-request.json)、[shutdown-preservation](../../../workspace/v3/p3/P3-SWEPT-01/shutdown-preservation.json) 和 [shutdown-processes](../../../workspace/v3/p3/P3-SWEPT-01/shutdown-processes.json) 相互对应：九项归还后正常关闭、不保存、不强杀/热换，原件及工作副本与 before 直接字节相同、原件 mtime 未变，当时无 NX/Journal/helper。它们证明历史收尾及磁盘保全，不声称观察了关机全过程或替代新会话现场核查。私有 context/config/token 不输出或进入交付包。

残余边界：全部 geometry_details_complete=false、INCONCLUSIVE，完整 UV/方向/修剪、坐标关系、源逼近误差、0.001 mm 全域目标、工程驱动项与整件覆盖仍未关闭；不得据这九项或未来 42 项全 clean 宣布 T04.a/P3 DONE。后续只可在新的受控会话中读取证据支持的剩余 33 项，且先完成最小离线适配、新增验证和独立审查；旧 epoch/context 不可复用，不重读上述十一面，不进入 P4。

### Q.3 续队列 C1 增量首审：CHANGES

仅审 `run_swept_queue.py` 相对 Q 节冻结副本的增量、新增测试及 [首次定向输出](p3-swept-resume-c1.txt)，不重跑或重审旧矩阵。**R13 / 高 / OPEN：继承时丢失末尾完整 item 会被当成未采集，违反禁止重读约束。** `completed_prefix`（当前第 194 行起）在第一个不存在的 item 处正常结束；`expected_plan.verify`（当前第 292—295 行）只要求该长度大于零，随后直接切出后缀，未与已持久化暂停完成集合交叉核对。具体反例：原 `P3-SWEPT-01` 的整个 `item-09-F0072` 若不可恢复地缺失，而前八项、STOP、42 项 plan、context、退出保全及 pause-manifest 仍在，初始化会将已完成九项误判为八项，生成 34 项并把 F0072 再派发。原 pause-manifest 和 Q.2 已明确它完成，因此不能把缺目录解释为从未派发。这是代码路径静态反例，本审查未删除证据或运行复现。

最小关闭条件：将暂停时已声明的完成集合及其来源/会话关联作为不可静默缩减的核对依据，同时仍逐项读取真实证据、调用既有 validator 判定有效，不能只信 manifest 的 count/CLEAN 自述。声明完成项缺目录、缺文件或不一致须停止；核定的剩余顺序也应与声明一致。多段链每段均适用。新增一个“最后完整 item 目录消失”的拒绝负例，并只复验受影响的继承正例/链式行为；不重读 native、不重跑旧全部矩阵。

其余已核增量：`read_json` 拒绝重复键；`init --inherit-run` 仅在新目录写 plan/context，旧目录只读；逐段要求明确 UserRequestedPause STOP、无 LOCK、旧 context/config 完整、容差相同、不同 epoch，重建并精确比较 P1 派生计划，再核正常退出和当前源件/旧副本/before 的直接字节保全。递归经 resolved 路径防环、epoch 去重及 42 段上限限制，且每段至少一项完成，未扩到 P1 原 42 项以外。新 `run_batch` 每批重新核继承链和当前 prefix，异常保持 STOP/LOCK；默认一项、上限四项、DISPATCHED 先于子调用及严格 epoch 传递保持原边界。目录/JSON 的一致性校验不构成对本地有权限者同时伪造整套证据的认证，也不消除 Q 节并发文件替换与掉电持久性限制。

[TV 索引](p3-diagnostic-validation.md)给出准确 11 节点范围、命令、cwd、Python 3.14.7 / pytest 9.1.1、退出 0；原始日志为 **11 passed、15 subtests passed**。五项合成继承测试使用 fake 证据校验器，覆盖缺单文件/内容损坏/暂停与保全异常、无序/未决、重复 epoch/自环及多段顺序；一个既有九项实例通过真实 validator 形成临时 33 项/F0077 计划，再以 fake 调用验证新 epoch 传递；另五项为直接受影响旧控制流。旧 STOP/context 字节不变有断言。测试没有覆盖 R13 的整个末尾 item 消失，不以这 11 项通过关闭该问题。旧 symlink 跳过仍未验证，真实新会话/目录计划尚未提交，本节不放行新采集；Q.2 已接受的九项原始采集不受此调用者缺陷否定。

### Q.4 R13 修复及 C2 定向证据闭环

**R13 CLOSED；受限续队列适配可接受为 P3 部分交付，无本批剩余阻塞发现。** 只审新增 `validate_pause_manifest`、其在继承链中的调用、相关测试调整与 [C2 原始输出](p3-swept-resume-c2-retest.txt)，继承 Q.3 未受影响的审查和证据。本评审未测试、构建、调用 NX 或修改任何原始证据。

每段继承现在先通过原 `completed_prefix`/真实 validator 核完成证据，再把其结果与必须存在的 pause-manifest 对照：来源快照、旧 epoch、禁止复用/派发、原排除项、整数完成/剩余数量、逐项标签、归还/CLEAN 声明、summary evidence ID、精确原始 summary/snapshot 路径及全部剩余 selector 顺序均须相符；证据 ID 在该段去重。清单只作声明集合的交叉核对，不能凭清单中的 native_clean 或 count 跳过实际证据。整个末尾目录丢失会形成 prefix 与声明长度不等，在写新 plan/context 前拒绝；清单缺失、不一致或证据原文件缺失同样拒绝。多段路径递归逐段应用，不允许旧段的丢失被后段遮盖。

首版拟新增尾项反例只覆盖“先 init、后移走尾项、再 run”，原 C1 已能借计划差异拒绝，不能直接回归 R13 的首次 init 漏洞。审查已在测试执行前要求补强同一节点；实际冻结并执行的版本在移走末尾目录后先尝试**首次 init**，断言拒绝且无 plan/context，再验证已有新 run 零派发/保持 STOP。没有为补强前版本产生多余测试记录。

[TV C2 索引](p3-diagnostic-validation.md)保存准确五节点命令、项目根 cwd、沿用隔离 Python 3.14.7 / pytest 9.1.1 及退出码 0；结果 **5 passed、7 subtests passed**。范围是上述首次初始化负例、清单缺失/多减重复/错来源/epoch/路径/剩余顺序及原 snapshot 缺失反例、单段 9→33、新 epoch 的有界派发、多段 13→29 以及真实旧九项证据正例。合成项仍用 fake validator/派发；真实旧项只读用原 validator，临时新 F0077 派发仍为 fake，未运行真实 once/NX。C1 其余有效结果继承，不重跑全部矩阵。

本接受限于受信本地证据的受控继承；不能证明恶意同时重写原始数据、清单及所有引用不会成功，也不把路径预检当作并发文件系统防护。Q/Q.1 的普通路径、源码/制品冻结、单一 root 通道、严格当前 epoch、每批至多四项、失败持久 STOP/不重放、人工处置和正常收尾约束继续有效。后续具体新会话须单独确定独立副本、C2 runtime、当前进程世代及来源保全；本节不授权复用旧 context/epoch、不重读已取得十一面、不提升几何完整性或 P3 出口。

### Q.5 P3-SWEPT-02 剩余三十三项具体计划增量审查

仅审 TL 提交的新会话计划，继承 Q.1—Q.4 的适用合同及证据，未启动/初始化队列或运行任何测试。**在下述边界内无新增阻塞发现，接受该具体受控计划作为 TL/root 后续准备与派发依据；不是三十三项实际可读或已成功的声明。**

新 `P3-SWEPT-02` 父目录保存独立工作副本、before 及 T13.o C2 五制品隔离 runtime（含已接受的复用原生 DLL）；controller 子目录初始化前只放 connection-only 配置。启动前记录源件/新副本/before 的直接字节保全、五制品复制关联与当前源码副本，检查新目录、文件及祖先均为普通路径、无 reparse/junction。源码和制品在活跃读取期间冻结；不计算 hash，不热换 DLL。此前 symlink 测试跳过与 fsync 不证明掉电持久性的限制保留，不能以准备计划本身代替实际检查记录。

root 为唯一 NX 通道；启动后取得该次实际 PID:UTC-start-ticks，以不同于所有前驱的当前 epoch 执行 `init --inherit-run P3-SWEPT-01/controller`。旧 STOP/context/manifest 与原始证据完全保留。通过 Q.4 的逐项原证据、暂停集合及退出保全交叉核对后，新计划必须恰为旧 plan 的后三十三项、F0077 起；原九项及 F0002/F0024 不再读取。新 context/config 属私有资料，不导出或公开；旧 Tag、owner、token、binding 或 epoch 不复用。

match_linear=0.001 mm、angular=0.0001 rad；curve/surface requested approximation 沿旧队列各 0.0001（毫米工作件中的请求值），未改算法/硬预算，也不构成实际误差保证。首批仅 `count=1`，核当前严格 epoch、唯一匹配、完整 native/managed clean、前后完整空 diff、无冻结与 summary RETURNED/HUMAN_OWNED 后，才由 root 显式派下一批，每批最多四项且返回 root 核状态，累计最多三十三个新目标。不能自动循环全部剩余项，不能由首项成功推广到其他项。

任何缺证据、不完整、epoch 不符、unsupported、overflow、dirty、error、异常锁/队列或未知结果均立即停剩余项，保留 STOP/LOCK/dispatch/原始数据，不跳过、不重试、不加预算、不在旧 context 中跨会话续跑。未来若用户再次暂停，须按 Q.4 保存该段完整暂停集合及收尾证据；不能把错误 STOP 改成 UserRequestedPause 以绕过门禁。正常路径每项先归还，最终按既有授权正常关闭且不保存，记录源件/副本字节保全与进程收尾；异常现场仍遵守 UNKNOWN 人工核查、不强杀规则。即使全部读得 clean，也只新增载体/拓扑数据，完整修剪、工程参数、全域几何及 P3 出口仍需其独立证据，不进入 P4。

### Q.6 P3-SWEPT-02 三十三项实际采集及正常收尾接受

**新增三十三项受限采集证据可接受，无本批阻塞发现。** 本节独立读取新 controller 的 plan、全部三十三项 selector/DISPATCHED/CLEAN/takeover/snapshot/status/summary、九批结果及准备/收尾记录，不重审 Q.1—Q.5、不重读旧十一项的原生响应，也未运行产品 validator、测试、构建、NX、Git 或 hash。私有 context/config/token 未读取或输出。来源整理模块不在本节范围内。

[完成索引](p3-swept-complete-index.md)记录项目根 cwd 与 root 实际工具调用转录；[completion-manifest](../../../workspace/v3/p3/P3-SWEPT-02/completion-manifest.json)逐项列原始路径/唯一 snapshot ID。命令依据是工具转录，init/batch 结果仅独立保存动作、数量、epoch 与退出码，不将其误称为完整命令/stdout 文件。新 plan 精确等于原 42 项 plan 的后 33 项，从 F0077 至 F0234，inherit_run 指向保留的 P3-SWEPT-01。九批为首批一项及八次显式四项，全部退出 0；root 每批返回后核证再派发，非控制器自动循环。

逐项 selector 与 plan 相同，P1 来源绑定正确；每个语义 descriptor 在 P1 对应域内唯一，实际匹配一面，其 UF20/Swept、bbox 和四边与请求一致。新 launch 的 PID/start-ticks 对应各项 DISPATCHED、takeover、snapshot、status 的同一严格 session epoch；各项 load_instance 和 takeover/read revision 相符，binding epoch 从 1 至 65、步长 2，均使用本次独立工作件。三十三个 snapshot ID 各不相同。请求维持 match=0.001、curve/surface=0.0001，毫米库存，不复用旧会话标识作为新授权。

每项 59 个 native 事件，合计 1947：序号连续，均实际调用，dirty_before/after=false；适用返回码为 0，geometry 查询/释放配对、topology 最终释放成立，四边覆盖完整。schema v3、CLEAN_TRACE，无 failure/first_dirty、overflow 或 incomplete_observed。每项八个托管 dirty 采样均 false，另一个 native 聚合事件为 dirty=null/CLEAN_TRACE，不误记为九次 false 采样。原始拓扑均保留 root type 206、type 102/order 4/七极点 generator、两条 type 101 及两条 type 102 边；它们是载体/边数据，不能由类型或阶数相同断言齿形等同。

各项 inventory_complete=true，实存 inventory_before、inventory_after、inventory 相等，含 235 面/622 边；inventory_diff=complete/changes=[]，two_native_samples_equal=true、read_consistency_fault=false、first_change=null、writes_halted=false。status 读前后 modified=false、active_operations=0、仍为归还前 AI_OWNED；已审 once 成功归还后写出的 summary 均 RETURNED/HUMAN_OWNED。单项 CLEAN 的退出 1 对应 recorded-response/geometry INCONCLUSIVE，不是几何通过。目录恰有连续三十三个 item、三十三个 DISPATCHED 与 CLEAN，无未决项、LOCK 或 STOP。

[源副本记录](../../../workspace/v3/p3/P3-SWEPT-02/source-copy-record.json)、[runtime 复制](../../../workspace/v3/p3/P3-SWEPT-02/runtime-copy-record.json)和 [普通路径前检](../../../workspace/v3/p3/P3-SWEPT-02/path-preflight.json)保留新副本/before 与旧基线的直接字节关系、已接受 C2 五制品关联及当时普通路径观察。[源码冻结记录](../../../workspace/v3/p3/P3-SWEPT-02/source-freeze-at-shutdown.json)记录 36 个列明源码与保存副本直接字节一致、changed=[]，副本均存在；TV 索引亦保留只读直接字节复核。它们不证明未列源码、恶意并发改动或未来环境。

[退出保全](../../../workspace/v3/p3/P3-SWEPT-02/shutdown-preservation.json)记录逐项归还后正常 Alt+F4 退出、无保存提示且未保存，未强杀/热换；源件及工作副本与 before 直接字节相同、源件 mtime 不变。[进程收尾](../../../workspace/v3/p3/P3-SWEPT-02/shutdown-processes.json)确认受控 PID 消失、所观察 NX/helper/Journal 相关进程为空。无须为补收尾或换评审重跑任何读取。

至此结合继承的十一项，共四十四个 Swept 目标各有细节采集证据；本次只新增接受后三十三项。所有新增项仍 geometry_details_complete=false、INCONCLUSIVE，完整 UV/方向/修剪、坐标关系、0.001 mm 全域误差、工程驱动及整件区域解释尚须后续证据。本结论可支持关闭该有界采集子任务，不关闭 T04.a 或 P3 整阶段，不放行 P4，也不批准新的额外采样。

## R. Swept 母形共同基比较与受限设计候选审查

**未发现阻塞提出本项设计选择的问题：可向用户询问是否接受两条独立原始七极点母形，在已确认的二十二位置中同侧共享，实际边界分别核实。** 本结论只支持询问设计意图，不表示用户已经确认，不证明四十四个完整齿侧/整齿同形，也不授权执行。审查范围是冻结的 [analyze.py](../../../workspace/v3/p3/P3-SWEPT-ANALYSIS-01/analyze.py) 与 [mechanical-observations.json](../../../workspace/v3/p3/P3-SWEPT-ANALYSIS-01/mechanical-observations.json)。执行者记录命令为项目根下 `python workspace/v3/p3/P3-SWEPT-ANALYSIS-01/analyze.py`；本审仅读源码及结果、检查输出算术一致性，没有运行会重写输出的脚本或重做已接受 spline_restrict 数学验证。

现有两份用户决定只分别确认二十二轴共享尺寸/等角关系，以及 F0002/F0024 两条独立可编辑样条保留各自原阶/节点；不包含本次新增的同侧共享母形。因此必须保留新选择为 proposed_for_user_decision_not_confirmed，不能由原决定自动推出。备选保留四十四条独立母线表达式合理；改用五极点截面边作独立驱动会改变原已确认编辑基底，应另作选择。

ANALYSIS-03 原关系框架为 +Y，plane_basis_u=(0,0,1)、plane_basis_v=(1,0,0)，与本脚本 theta=atan2(x,z)、t=x cos(theta)-z sin(theta)、r=x sin(theta)+z cos(theta)、y 不变的约定相符。其拟合轴点在 XZ 中约为 (1.80e-16, -2.08e-30) mm；脚本采用原点轴的框架假设已显式记录，不把极小差异隐含为严格误差包围。使用的是逐成员实测角，未擅改为另一个相位约定或把等角设计误差归零。F0064 两个参考恰是原已确认 F0002/F0024；输出有二十二成员、四十四个不同面标签，每组两侧。以中间节点族区分两侧只适用于该批已检查数据，不是通用侧面识别器；跨快照成员绑定仍依赖单独 source-map 审查。

给定数据均为非有理、单位权重、[0,1] 夹持三次表达式；母线七极点/原 Y=-124 mm，截面边五极点且全部极点 Y=-71 mm，所有扫掠方向为 (0,-1,0)。`common` 对每一比较对取原始二进制节点多重集合的并集，以已有 `_insert` 对精确 Fraction 极点插入，不吸附近邻节点；这样比较完整共同基控制网而非只比较原始节点不同的七个数或少量采样。原插结算法证明直接继承。输出局部坐标与记录旋转公式相符，共同基节点/极点维数及由控制差向量求得的最大范数与摘要一致。

同侧母线最大控制差为约 9.7774e-12 mm，同侧截面边约 1.5027e-8 mm。它们支持“共享表达式是合理设计候选”，但计算先使用浮点三角旋转，最终转浮点求范数，未提供向外舍入包围；只能称给定表达式、相同参数对应下的全域凸包估计，不能称严格数值误差上界，更不能称 native 逼近/源件/制造精度。控制网转为共同基是比较表示，不可把新增比较极点替换成独立驱动而改变用户原基底。

相反侧先作局部 t 镜像及参数反向，是选定对应，不是求全局最短距离；母线约 2.1581e-4 mm 的控制差不构成实际几何差的下界，也不推翻保留两条独立母形的选择。y=-71 四段候选闭环中的圆弧仅为给定载体/端点径向相容假设；未提取真实圆弧范围、确定材料侧、相切或布尔语义，不在本节接受为可执行切除方案。

残余验证：source-map 跨快照唯一映射尚待独立审；实际 UV/trim、参数对应、可见段中原极点驱动性、端部连接、肩/后部封闭、编辑域、原生约束以及整件误差仍开放。用户即使接受同侧共享，也只确认共享驱动与传播关系，不能因此关闭这些几何/接口验证或 P3 出口。

## S. Swept 来源映射增量首审：CHANGES

范围仅新增 [swept_sources.py](../../../src/nx_sketch_mcp/v3/swept_sources.py)、[test_swept_sources.py](../test_swept_sources.py)、[run_swept_sources.py](../run_swept_sources.py) 与实际 [source-map.json](../../../workspace/v3/p3/P3-SWEPT-ANALYSIS-01/source-map.json)。**R14 / 中等 / OPEN：旧两项证据入口把同时缺失的会话身份当成一致。** `_validate_legacy` 只比较 takeover/status/snapshot 的 `get("session_epoch")` 是否相等，三者全部缺键或为 null 时仍相等；summary/status 的 PID 亦仅比较相等，二者全部缺失同样可过。后续 `once.clean_diagnostic_response` 和 `normalize_detail_snapshot` 不负责补该身份检查，因此其余原始字段完整时，会话身份不完整的旧项仍可进入来源映射。该 helper 是本次新增合同，不能用旧实读已接受替代其对缺失输入的拒绝。

最小关闭条件：显式要求正整数 PID、非空有效的历史 epoch 且其进程部分对应 PID，再核三份 epoch 一致、status PID 一致；缺失/null/非法/不符均拒绝。增加一个只针对该 helper 的身份正反例，保持旧证据只读或使用临时 fixture，不调用 NX，不重跑旧采集矩阵。现有实际旧两项有身份字段，R14 不否定其已接受事实；无需为此重读或仅为重存而重复生成不变 source-map。

其余已核：新 33 项和继承九项通过已审队列门禁/暂停集合与当前完成清单核证；旧两项走上述 helper 后再归一化。每个 detail 面先在自身 snapshot 内定位，再按单位、类型、bbox、边数和邻接类型签名向 P1 作双向各唯一匹配，圆柱还检查半径、法向标记、无向轴夹角及轴线垂距；不把跨会话 Tag 或相同 F 编号当对应证明。归一化输入已验证数值有限、向量长度、互反邻接，匹配阈值仍只是候选关联域。

原用户关系的两条候选、snapshot、来源成员集合及 ANALYSIS-04 intent 与原 ANALYSIS-03 绑定；二十二成员 index、observed_angle、原 frame 和角约定逐项比较。映射圆柱至 P1 后要求互反邻接，每柱恰有两个 Swept，合计四十四面各出现一次。输出保留 detail_snapshot_id 下的局部面/边编号、原母线、原路径、选择依据及未知 UV/trim；同侧顺序未自动认定，共享形状不假设。原 F0002/F0024 的 snapshot/path/basis 与原两独立样条决定相符，未改用户原基底。

实际 source-map 有二十二成员、四十四个不同 P1 面及不同 detail snapshot；成员序、角度、frame 与原 intent 相同，逐项 snapshot/path/母线 basis 及成员两侧集合与 R 节机械记录一致。geometry_explanations_conferred_by_this_map=0、geometry_proven=false、execution_approved=false；输出未含 token、私有 context/config 或 ownership 字段。它证明受限观察关联，不是全形状、跨会话精确框架或原生误差证明。CLI 仅允许 workspace/v3/p3 内已有父目录的新输出，以独占创建避免覆盖；没有 NX 调用。

首次验证元信息由 SI 的实际工具转录提供，本节持久化，不伪称另有完整 stdout。cwd 为 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`；隔离 Python 环境与前文一致。以下首次测试退出 0，[原始输出](p3-swept-sources-c1.txt)为 **8 passed**：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_swept_sources.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-swept-sources-c1.txt; exit $LASTEXITCODE
```

八项是合成语义/双向歧义、单位/bbox/邻接、圆柱轴、22×2 分区、重复/非互反邻接、JSON 与关系角顺序绑定测试；不是完整 evidence ingestion 故障矩阵，未覆盖 R14。实际唯一 source-map 生成构成完整只读集成正例，同 cwd、退出 0，工具转录输出 22/44、geometry_proven=false：

```powershell
& 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -B tests/v3/run_swept_sources.py --output workspace/v3/p3/P3-SWEPT-ANALYSIS-01/source-map.json; exit $LASTEXITCODE
```

此前一次 New-Item 前置步骤因机械代理已创建分析目录而报“已存在”，在 CLI 启动前中止；随后使用既有目录一次生成成功，没有覆盖机械文件。该前置失败保留，不算一次 source-map 生成失败。评审只读代码/产物并核数据关联，没有运行上述命令或任何测试；等待 R14 最小修复与证据，整件几何/trim/编辑驱动和 P3 出口仍不在本节放行范围。

### S.1 R14 最小修复及单节点证据接受

**R14 CLOSED；本次来源映射模块及已生成的受限 source-map 可接受，无本批剩余阻塞。** 只复审 `_validate_legacy` 新身份前置条件、单个新增测试与原两项记录中相关身份字段，未重做旧采集审核、测试或生成 source-map。先前 S 节其余静态评审及实际映射核对直接继承。

新守卫要求 summary PID 为正整数（排除 bool）、status PID 亦为整数且相等；epoch 必须是长度有界的 ASCII canonical `PID:positive-start-ticks` 字符串，无空值/前导零，PID 前缀必须相符、ticks 不超有效上界。之后保留三份 epoch、binding/load/revision 及完整 clean/归还检查。全部缺失或 null 现在在相等比较前拒绝，不会把未知身份当一致。只读字段核查确认旧 F0002 与 F0024 各自现存 summary/status PID 及三份 epoch 满足新条件，不打印身份或把它们用于新会话。

[定向原始输出](p3-swept-sources-c2-retest.txt)为 **1 passed**，退出 0。该一节点先验证有效合成身份，再循环七类拒绝：双方缺 PID、bool PID、PID 不符、三份 epoch 全缺、非 canonical、epoch 属另一 PID、单份 epoch 不符。它使用 fake `clean_diagnostic_response` 隔离本次新增身份合同，不宣称新跑了原生诊断或七个独立测试。null/空字符串、零/负值及 ticks 上界分支由静态检查支持，没有将其另报为已执行反例。

准确命令由 SI 实际工具转录，cwd 为 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`，环境沿 S 节，仅本节点一次：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_swept_sources.py::test_legacy_session_identity_missing_or_mismatched_is_rejected 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-swept-sources-c2-retest.txt; exit $LASTEXITCODE
```

旧八项不重跑、原 source-map 不重生成；此次修复不改变有效原数据的输出。接受范围仍是相同零件绝对坐标及既定阈值下的唯一候选关联与已确认关系的来源保全，不是对本地有权限者伪造整套证据的认证。精确跨会话几何关系、完整修剪、共享驱动落地和整件误差继续按 R/S 的开放项处理，不关闭 P3 或授权新采集。

## T. P3-REGIONS-02 两项新定义读取计划受限接受

**该具体两目标计划无剩余阻塞，接受 TL/root 在其明确边界内启动新会话并逐项采集。** 仅读 [read-queue](../../../workspace/v3/p3/P3-REGIONS-02/read-queue.json)、两个 selector 文件、P1 对应库存及新增准备记录；未测试、NX 调用或复验旧 native 路径。仅这两个此前未取详细定义的目标，不增加采样轮次或重读四十四个 Swept/其他已取得定义。

F0022 与 F0041 的 selector 各与 P1 原记录逐字段相同，并在 0.001 mm 匹配域各唯一；单独 selector 文件与队列一致。第一项 F0022 为 UF19/SurfaceOfRevolution、四边（Spline、Intersection、Circular、Intersection），其 P1 直接邻接包括已读取 F0111、F0125、F0169 及 F0040；本次目的是取得第二个肩部母线及同树 FIN/边，与原 F0004 及 F0111 作具体对照，不推广其余二十一个肩部。第二项 F0041 同为 UF19/SurfaceOfRevolution，实际八边（含 Circular/Intersection/Spline），并非四边；目的是原生确定上头载体及八边，为已有有限点拟合之外的局部接口规划补缺。“R8.9 torus”在读取前仅为候选，不能预先视为原生类型/中心已证明，也不推广其他五个区段。

审查指出初稿未显式固定调用数值后，TL 已补 `thresholds`：match=0.001 mm、curve/surface requested 各 0.0001 mm、angular=0.0001 rad；补 `hard_budgets`：topology=921600 bytes、per-face=2097152 bytes、native events=4096、changed=false。它们分别是匹配/请求值及不变硬限，不是已达到的精度或实际复杂度成功保证，无需为此修改或重测已接受读取器。

[源副本](../../../workspace/v3/p3/P3-REGIONS-02/source-copy-record.json)记录原件/新副本/before 与已接受 SWEPT-02 基线直接字节一致、源 mtime；[runtime](../../../workspace/v3/p3/P3-REGIONS-02/runtime-copy-record.json)关联已接受 T13.o C2 托管及 T13.f 原生五制品的直接字节复制。[源码冻结](../../../workspace/v3/p3/P3-REGIONS-02/source-evidence-record.json)保留实际导入源副本，[路径前检](../../../workspace/v3/p3/P3-REGIONS-02/path-preflight.json)记录 77 个路径、reparse_points_found=[]。仅承担准备时观察，不能保证后续并发修改；新未导入的离线规划模块不替代读取链冻结。私有 connection-only 配置不输出，当前尚未启动 NX。

root 是唯一启动/操作通道，启动后必须取得当前实际 PID:UTC-start-ticks，每次 once 都传 strict expected-session-epoch，使用新接管凭据及各自独占 evidence 目录。最多两次、每次单面，先 F0022；root 见唯一匹配、完整 native/managed clean、空 before/after diff、无停写及 RETURNED/HUMAN_OWNED 后才显式释放 F0041。首个 unsupported/error/incomplete/overflow/dirty/错 epoch/未知或证据不符即持久 STOP、保存原始结果、停剩余目标，不跳过、不重试、不解冻、不提高预算。

正常逐项归还后，只正常关闭本次受控 NX、不保存、不强杀/热换；保存进程收尾、原件/副本字节与 mtime 保全及导入源码冻结记录。异常现场先解释状态并按已授权 UNKNOWN 人工核查/收尾流程处理，不冒称正常归还。即使两项成功，也只新增各自载体/拓扑观察；完整修剪、源误差、封闭工具、材料侧、工程参数及整件误差仍未证明，不直接批准几何构造或 P3 出口。

### T.1 CLI 输入前置拒绝与独立 C2 替代计划

**确认原 F0022 CLI 在构造 MCP server 前因 selector 外层格式拒绝，没有发生 initialize、takeover 或 inspect；接受独立 C2 替代计划在同一当前受控 NX 会话中按原两目标边界执行。** 此结论不是对未知 native 操作的重放许可，也不清除原 STOP。T 节只比对了 selector 内容，遗漏 once 要求的外层对象格式，先前接受存在输入合同审查遗漏；本节显式纠正，原失败保留。

[原失败目录](../../../workspace/v3/p3/P3-REGIONS-02/native-01-F0022)的 python-exit-record 为 2，argument-error 保存实际错误转录 `invalid P1 descriptors: ValueError`，preflight-rejection 记录因输入为 list 而非要求的对象。原 DISPATCHED 是 root 在 CLI 前写下的标记，不独自证明发生原生调用。独立检查 once 源码确认：`explicit_selectors` 首先要求精确 `{source_snapshot_id, selectors}` 对象；该 ValueError 在 `main` 中进入 `parser.error`、SystemExit(2)，位置早于 `McpServer(load_config(...))`、summary 创建和 initialize/takeover/inspect。因此无四份 detail 文件与明确错误分支相互支持；结论不只靠“未见结果文件”作推断。

[C2 队列](../../../workspace/v3/p3/P3-REGIONS-02/read-queue-c2.json)只更换正确 envelope 的 selector 文件及两个独占新 evidence 目录 `native-c2-01-F0022`、`native-c2-02-F0041`，目标、顺序、最多两次、数值及硬预算不变。原 read-queue、坏 selector、DISPATCHED、退出记录和 [STOP](../../../workspace/v3/p3/P3-REGIONS-02/STOP.json)均保留；C2 supersedes 明确指回本次前置失败。没有代码/runtime 改动，也不将原 T 节接受当作 C2 已执行成功。

按 TL 明确授权，仅对两份新输入进行一次离线实际 parser 检查，未调用 `main`、McpServer、测试矩阵或 NX。在项目根用 `python -B -` 导入 `tests/v3/run_reference_detail_once.py`，分别执行 `explicit_selectors(Path('workspace/v3/p3/P3-REGIONS-02/selectors-F0022-c2.json').resolve(), 0.001)` 和 F0041 对应调用；工具退出 0，返回分别为 `F0022 ACCEPT count 1 edges 4`、`F0041 ACCEPT count 1 edges 8`。这只证明 C2 envelope 与 P1 唯一 descriptor 合同满足，不是实机结果。

同一会话继续的依据是上述前置拒绝尚未创建 server 或开始接管，不存在本 runner 留下的 UNKNOWN/native 未决操作；不是复用旧会话凭据。root 仍须使用此次实际当前 epoch 的 strict guard，每项新接管，先 F0022 完整 clean/空 diff/HUMAN 后才显式释放 F0041；若进程世代已变、会话状态无法解释或新项失败，则停止而非沿用本接受绕过。原停止计划不再派发，C2 新错误单独持久化且不自动重试；最终正常不保存退出、磁盘与源码保全仍按 T 节收尾。

### T.2 C2 两项新增原生响应及正常收尾接受

**受限接受 F0022、F0041 两项 C2 采集及正常收尾，无本批阻塞发现。** 只审新两份 evidence 目录及收尾；未调用 NX、旧测试或产品 validator，也未重读旧区域原生响应。[实读索引](p3-regions02-index.md)保存准确 cwd、root 工具调用转录命令、两项 snapshot ID/路径及退出码；命令不是另存的独立 stdout。原前置输入拒绝仍按 T.1 解释为无 server/native 调用，不改记为原生失败，原 STOP、坏 selector 和失败目录均保留。

[native-c2-01-F0022](../../../workspace/v3/p3/P3-REGIONS-02/native-c2-01-F0022)与 [native-c2-02-F0041](../../../workspace/v3/p3/P3-REGIONS-02/native-c2-02-F0041)的 DISPATCHED 均指向 C2 和本次 epoch，选择器/请求符合队列；各当前匹配唯一。takeover、snapshot、status 的 epoch、binding/load 及读修订对应，binding 分别 1、3，路径为本次独立件，未将旧 CLI 标记当一次接管。每项 root 严格 validator 的 CLEAN 记录与原始 evidence 相互支持；评审另核实际字段，不只采信标记。

F0022 有 63 个 native 事件、四边；原生 root type 205，type 102/order 4/七极点非有理 generator 与轴/轴点保留。F0041 有 119 个事件、八边；原生 root type 204，报告 major_radius=28.94434210744、minor_radius=8.9、center=[0,4,0]，同时保留其轴及 u0_ref_direction。这关闭“未取得该载体原生定义”的数据缺口，不等于真实裁剪或几何构造已证。

两项事件序号连续，native dirty_before/after 全 false、CLEAN_TRACE，适用返回码为 0；BREP geometry 查询/释放配对且 topology 成功释放，无 overflow/incomplete/failure。圆边分别一条和两条走已接受 EVAL 六阶段，初始化、判型、limits、periodic、arc 及 free 返回码均 0；这些圆边的 BREP geometry_rc/free_rc=null 表示未使用该路径，不能误报为失败或伪称 BREP 释放调用已执行。每项八次托管 dirty 采样为 false，另有 native 聚合条 dirty=null/CLEAN_TRACE。

两项实存前后完整库存相同，均 235 面/622 边，inventory_diff=complete/changes=[]、two_native_samples_equal=true；read_consistency_fault=false、first_change=null、writes_halted=false，status active_operations=0 且读前后 modified=false。归还前 status 为 AI_OWNED；归还后的 summary 均 RETURNED/HUMAN_OWNED。两项 Python 退出码各 1，符合 recorded-response/geometry INCONCLUSIVE 约定；geometry_details_complete=false，未升为几何通过。

[shutdown-preservation](../../../workspace/v3/p3/P3-REGIONS-02/shutdown-preservation.json)记录 C2 两项归还后受控 NX 正常 Alt+F4 退出、无保存提示且未保存，不强杀/热换，源件/工作副本与 before 直接字节相同、源 mtime 未变；[shutdown-processes](../../../workspace/v3/p3/P3-REGIONS-02/shutdown-processes.json)确认受控 PID 已消失、观察相关进程为空。[source-freeze-at-shutdown](../../../workspace/v3/p3/P3-REGIONS-02/source-freeze-at-shutdown.json)为 36 个导入源、changed=[]，TV 索引保留直接字节复核。原 CLI 拒绝不要求清 STOP 或重新采集来补历史证据。

残余验证仍为载体坐标/参数与完整裁剪对应、端部/肩部连接、封闭工具、材料侧、编辑约束及全域误差；不能从这两项推广其他二十一个肩部或五个上头区段。可将两项资料交后续限定离线规划，不据此宣布整件可执行、P3 DONE 或批准额外采样。

## U. T19.a 区域设计 DAG 合同首审：CHANGES

范围仅新增 [regional_design_dag.py](../../../src/nx_sketch_mcp/v3/regional_design_dag.py)、[测试](../test_regional_design_dag.py)、[组装入口](../run_regional_design_dag.py)及 P3-DAG-01 规划报告。以下为首次冻结 C1 的独立审查发现；SI 已自报前两项并经本审确认，后两项由本审提出。实现进入修复后不再扫描编辑中版本，待再冻结增量复审。未运行测试、NX 或重审旧数学/原生模块。

1. **R15 / 高 / OPEN：用户决定未绑定具体获准内容。** `_attestation` 的 `p3-region-user-decision/1.0` 仅保存 claims 名称、snapshot/region 和 decision_id，没有所确认的参数值、单位/消费者或具体区域节点。实现者可改变参数并同步改 evidence 的 parameter_witness，旧 decision 仍能确认同名 claim，无法证明用户接受的是该具体设计。最小修复：每个用户 claim 的精确决定见证与当前受审参数或区域/节点相等；决定文件本身纳入受审内容冻结。针对“同名 claim 但值/构造改变”补拒绝证据，不要求 P6 几何认证。

2. **R16 / 高 / OPEN：审查仅绑定路径，受审内容和其来源可原位变更。** `_attestation` 的 review 只指 evidence_path；`_source` 只核文件存在及 P1 身份字段。保留 review accepted 而修改同路径的 argument、参数/节点见证，或改变被引用数据但保留 snapshot_id，仍能被当成已独立审查。最小修复：review 锁住受审 evidence 的完整有限 JSON 内容，并将全部实际依赖的 source/decision 内容与独立冻结副本直接字节核对（不使用 hash）；缺项、变更、同文件/硬链接假副本应拒绝。信任 review 本身不被协同伪造的边界可以明示，但不能把路径相同当内容相同。

3. **R17 / 高 / OPEN：减料规划可以没有目标材料。** `_polygon_prism` 同时接受 stock/subtract，但只检查自身截面和高度；DAG 对 depends_on=[] 合法，不检查 subtract 的材料目标。将已测合法夹具的 region/node kind 同改为 subtract、其余新见证保持一致，即可在没有任何 stock/target 的计划中得到 p3_ready=true。最小修复：当前正例域先限定为有定义的 stock prism，subtract 保持 unsupported/阻塞；或增加明确唯一目标体合同及依赖校验。本次不要求实现后端布尔，也不以以后 P4 会发现来接受无目标设计。

4. **R18 / 中等 / OPEN：参数消费者是自述，未绑定到受支持构造中的实际引用。** 节点 parameters 与参数 consumers 互指只证明两个清单一致；polygon_prism 实际仅引用 height_parameter。额外 width 等已确认参数可出现在清单而完全不驱动 vertices/height，仍进入 ready。最小修复：在该受限类型中要求参数集合精确等于构造真正使用的参数；如果暂仅支持 height，就拒绝额外未引用项。补“声称被使用但构造未引用”反例，不能把声明消费者或以后原生绑定当作本层设计依赖。

除此之外，C1 已有可达的 P3 planning-ready 正例，而非硬编码永远 false：受审 stock polygon_prism、完整责任/区域声明、确认参数及固定顺序可就绪，即便 P4 capability 仍 open，execution_approved 仍 false、verified_geometric_explanation_count 仍 0。新模块与旧 model_plan/IR 分离，P3 能力开放阻塞自身、P4/P5/P6 能力单列延后，不要求先运行 P6。已有纯函数检查覆盖毫米绝对坐标、P1 输入与引用 JSON 相等、责任重复/遗漏、局部边作用域、依赖循环/不存在、参数量纲/有限值/除零、简单多边形及构造字段；这些不能替代四项缺口的关闭。

[首次输出](p3-regional-design-dag-c1.txt)为 **9 passed**。读取测试代码确认有 ready 正例、孤立 true/unreviewed/错 claim/变构造拒绝、用户 claim/负误差界、责任/快照/有向边、参数/依赖、截面自交/缺边以及 P3 与后端阶段区分。该九项未覆盖上述新反例，不以首测通过放行 C1 合同。审查记录和用户决定属于可信项目文件而非认证签名；representation_error 仅核定有来源的有限非负表达误差界，不自动分配或证明整件 0.001 mm 总误差预算。

实际首份为 [design-dag.json](../../../workspace/v3/p3/P3-DAG-01/design-dag.json)，不是 design-dag-c1.json；后份 [design-dag-c2.json](../../../workspace/v3/p3/P3-DAG-01/design-dag-c2.json)独立生成、未覆盖首份。C2 实存七区域/七节点、235 个不同责任面且无遗漏/重复，reviewed_design_face_count=0、verified_geometric_explanation_count=0、p3_ready=false、execution_approved=false；所有 construction 仍 unresolved。T04_a/b/c 保持 P3 open，T18/T24/T26 分别列 P4/P5/P6，不把后端门禁假称已实现。

C2 对上头 Q 增补潜在附加边界片、非流形接触、缺 source-bound clip 和材料侧证据；三点 membership 仅描述候选，不证明源材料侧。被否定的肩部 C2 扫角没有进入节点或当前方案。报告是责任与待办账，不能把 235 面责任覆盖写成 235 面几何解释。以上实际 blocked 报告未因四个合同漏洞被误放行，但“可达 ready 的通用正例合同”须等修复和最小相关复验后接受。

### U.1 C2 修复核查及剩余数值反例

C2 再冻结后已核 R15—R18 的实现改动：用户决定新增逐 claim 的精确见证；review 保存完整 evidence_witness，并按各 source 与独立冻结副本逐字节比较、拒绝 samefile；区域/节点/参数/能力及决定依赖必须纳入审查来源。可就绪构造收紧为单个 stock polygon_prism，subtract/多操作保持阻塞，node.parameters 必须恰为其真正引用的 height_parameter。[C2 定向日志](p3-regional-design-dag-c2.txt)为 **9 passed**，仅九个新增/直接受影响节点，退出 0。实际样件未重生成，[contract-delta](../../../workspace/v3/p3/P3-DAG-01/contract-delta.md)明确两份历史报告早于修正合同、仍 blocked，未冒称以 C2 重新验过。

**R19 / 中等 / OPEN：受限 polygon 的自交判定会因乘积下溢漏检。** `_polygon_prism.intersects` 使用 `x*y < 0 and z*w < 0` 判方向异号，合同只要求有限坐标、没有保证该乘积可表示的尺度下限。明确反例为 `[[0,0],[2e-100,2e-100],[0,2e-100],[1e-100,0]]`：两条非相邻边确实交叉，浮点 area2 约 2e-200、非零且有限，方向量约 1e-200，而异号乘积约 -1e-400 下溢为零，从而未报自交。该输入虽远小于机械尺度，仍位于当前宣称接收的有限数值域内；不能把没有验证的尺度约束默认为已存在。本审静态推导，没有运行或写入反例数据。

最小关闭：对输入 binary64 的方向/面积使用精确算术，或建立明确且已证明安全的数值域与不易下溢的符号判定；补这个单独负例，并保留合法 stock 正例可达。无需重做旧 spline 数学或原生验证。

另需补强 R15 现有单节点证据：C2 测试直接修改 decision 文件会先触发冻结字节不等，尚未孤立证明“保留旧决定，变更新提案/新受审见证后仍拒绝”。应保持原 decision 及其冻结副本不动，只更新 proposed 参数/节点与相应新 evidence/review，再断言旧决定不认可新内容。此为同节点新增必要断言，不要求重跑九项矩阵。以上两处最小收口前不接受完整 ready 合同；实际样件仍未误放行。

### U.2 R15—R19 闭环与 T19.a 受限合同接受

**R15、R16、R17、R18、R19 CLOSED；接受当前受限区域设计 DAG 合同作为 P3 部分交付，无本批剩余阻塞。** 仅复审再冻结增量、新定向证据及历史报告适用性说明，未运行测试/NX或重生成样件。接受不是 T19 整任务或 P3 完成，也不是承诺真实样件已支持本模块唯一可就绪的构造域。

R15：decision 的每个 claim 精确绑定区域/节点或参数见证，并且 decision 本身属于独立冻结的受审来源。C3 新反例先建立真正 p3_ready=true 的有效夹具，再分别更改参数值和节点截面，生成新 evidence/review，但保留原 decision 及其冻结副本字节不变，两种情况均拒绝；直接覆盖旧决定不能确认新提案的失效机制。R16：review 的完整 evidence_witness 与当前有限 JSON 内容相等，全部实际 region/node/parameter/capability/decision 来源必须列入受审 source 集合并与不同文件的冻结副本逐字节一致；samefile、变更来源、遗漏区域来源及修改已审 argument 的反例成立。该检查仍信任项目审查记录及独立冻结副本不被有权限者一起伪造，不是签名认证，也不宣称抵御并发文件替换。

R17：ready 域明确限于单个 stock polygon_prism，非 stock、减料、多操作及其他构造保持 blocked；不再把无 target 的减料当成可解释方案。R18：该类型 parameters 精确等于唯一 height_parameter，且保留与参数 consumers 互反检查；额外声明但未引用的参数拒绝。合法高度、固定截面和全部受审设计证据仍可就绪，P4 open 可延后，execution_approved 恒为 false；这不是要求提前完成 P6。

R19：有限输入坐标先转为精确 Fraction；面积、方向量及相交计算都在精确算术中完成，因此 binary64 数值的方向异号不再被乘积下溢或舍入隐藏。C3 原反例被拒绝，普通简单截面仍可作为候选，另一 C3 节点也再次证实完整 stock 正例可就绪。该数学结果只针对输入表达式，不证明源边对应、native 模型有效性或制造精度。

[C3 日志](p3-regional-design-dag-c3.txt)为 **2 passed**、退出 0；继承 [C2 日志](p3-regional-design-dag-c2.txt)的九个新增/直接受影响节点 **9 passed**、退出 0，以及 [C1 首次日志](p3-regional-design-dag-c1.txt)的 **9 passed**。C1/C2 是当时不同合同上的记录，不合并成一套同时存在版本的测试总数。C3 只运行新增的数值反例和旧决定不确认新提案节点，没有重复九项矩阵或原生证据。

以下准确命令、环境及退出码根据 SI 实际工具转录持久化，不为补日志重跑。各次 cwd 均为 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`；测试禁插件自动加载/字节码，使用已列隔离 Python。C1 首次、C2 定向、C3 最小收口依次为：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_regional_design_dag.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-regional-design-dag-c1.txt; exit $LASTEXITCODE
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_regional_design_dag.py::test_reviewed_polygon_design_ready_with_later_backend_open tests/v3/test_regional_design_dag.py::test_unreviewed_or_mismatched_records_cannot_promote_claim tests/v3/test_regional_design_dag.py::test_wrong_user_decision_or_error_bound_rejected tests/v3/test_regional_design_dag.py::test_open_p3_is_distinct_from_deferred_backend tests/v3/test_regional_design_dag.py::test_decision_and_review_witness_bind_exact_content tests/v3/test_regional_design_dag.py::test_reviewed_source_must_match_independent_frozen_bytes tests/v3/test_regional_design_dag.py::test_review_cannot_omit_a_region_source tests/v3/test_regional_design_dag.py::test_subtraction_is_unsupported_and_unconsumed_parameters_fail tests/v3/test_regional_design_dag.py::test_polygon_self_intersection_and_missing_boundary_rejected 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-regional-design-dag-c2.txt; exit $LASTEXITCODE
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_regional_design_dag.py::test_exact_polygon_sign_rejects_tiny_self_intersection tests/v3/test_regional_design_dag.py::test_old_decision_cannot_confirm_new_reviewed_proposal 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-regional-design-dag-c3.txt; exit $LASTEXITCODE
```

两次样件组装的命令文本相同、同 cwd、各退出 0，其间 runner 只随新头部审查调整输出文件名和规划说明，依次生成 design-dag.json 与 design-dag-c2.json；它们均早于本合同修复，之后未重生成：

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -B tests/v3/run_regional_design_dag.py; exit $LASTEXITCODE
```

[contract-delta](../../../workspace/v3/p3/P3-DAG-01/contract-delta.md)已将历史报告与修正合同分开，不能把历史 blocker 列表称为最新代码重算结果。其关于后来肩 C3 的更新只继承另份独立审查所接受的条件数学，不在本节重新计算或扩大接受。真实样件依旧 235 面责任/0 几何解释、P3 未就绪；stock 包络、有限槽工具、齿侧/齿根、肩和两端头部的源边界、材料侧、裁剪、参数、顺序及误差仍须具体方案/证据。representation_error 的记录不等于整件 0.001 mm 目标已实现，后续能力缺口保持原阶段归属，不把这些 P3 设计缺口推给 P4/P6。

## V. 两项新用户决定原话记录的范围审查

**受限接受两份原话决定记录，未发现扩大用户授权的阻塞问题。** 依据 TL 转交的用户回复“均为前者”及记录中对应两个二选一原问题，静态检查 [共享母形决定](../../../docs/v3/decisions/p3-shared-flank-templates-user-decision.json) 和 [尾槽独立尺寸决定](../../../docs/v3/decisions/p3-rear-slot-independent-user-decision.json)。两者保留原回复和回答上下文，明确精确消息时间不可得、记录时间不是伪造的用户消息时间。未审尚在实现的 decision_bindings，不重验 source-map、DAG 或槽几何。

第一项确认二十二组同侧共享两条独立原始母形，不是四十四条各自独立。保留两模板各自原七极点、阶数/节点以及原已确认二十二轴关系；source_binding 的二十二成员与原 source-map 逐字段一致，template_observation_sources 与原两独立样条决定一致。来源成员中的 `shared_shape=not_assumed` 是历史观察字段，记录不篡改旧观察；新意图由当前 scope 明确确认，不能混淆为几何观察已证明整齿相同。各成员 trim/连接证据分别保留，原完整裁剪、肩端部、极点实际驱动性、五极点替代和编辑域/原生落地仍未确认。

第二项确认尾槽宽度、半径及轴 Y/Z 位置四个独立尺寸，保持居中且无额外跨参数联动。记录初值 5、37.5、-162.6、42 mm 与所引 slot-plan-c2 的现有 derived 数据一致；中心 X=0 和两侧 x=±width/2 表达所选居中关系，+X 是原无向轴线的规范方向，不改变原 -X 圆柱轴线几何。source/tool 逐字段对应所引槽计划，未把其数学闭工具声明升为源材料侧或真实布尔结果。该选择是在现有来源初值下确认参数关系，不授权任意未来改值或未验证编辑区间。

两份 not_confirmed 均保留实际 trim/材料占据、stock 包络、约束可解性、native binding 及 0.001 mm 实现等边界；共享设计意图不替代 trim 证明，尾槽独立尺寸意图不替代 material-side 证明。本节仅接受记录与选项范围，后续来源绑定需其独立审查，不因此宣布完整区域构造、P3 ready 或 execution 获准。

### V.1 两决定绑定首审：CHANGES

仅审新增 [decision_bindings.py](../../../src/nx_sketch_mcp/v3/decision_bindings.py)、[测试](../test_decision_bindings.py)、[入口](../run_decision_bindings.py) 和 [首次实际意图输出](../../../workspace/v3/p3/P3-DECISIONS-02/decision-bindings.json)。不重新审查旧 source-map、DAG、槽几何或 native/math 矩阵。**发现以下两个待修复合同问题；原用户决定范围仍按 V 节接受。**

1. **R20 / 高 / OPEN：共享相位当前值与固定模板参考值混用，字段编辑不传播。** `evaluate_flank_poles` 把 intent.shared_phase_rad 同时赋给默认当前 phase 和 base_phase，旋转差为 `phase + i*pitch - (base_phase + anchor*pitch)`。直接修改已输出的共享相位字段、使用默认求值时，该修改在两项中抵消，全部极点保持不动。当前测试只给临时 `phase=` 覆盖值，绕过了该失效机制；输出 rotation_expression 却区分 shared_phase/reference_phase，后者没有独立字段。最小修复：把不可变的来源参考相位/anchor 与可编辑当前相位分开，默认求值读当前驱动值，增加修改字段本身的二十二成员传播反例/正例。不能将有字段、可传临时参数或假定 P4 会处理视为已实现关系。

2. **R21 / 中等 / OPEN：原已确认圆周关系的初值没有完整绑定。** `bind_flanks` 对当前 phase 仅要求有限并在 0.0001 rad 内接近观测成员角，未将其初值精确对应原 circular candidate；因此小于该匹配阈值的初值漂移会通过。原已确认 shared_pitch_circle_radius/shared_cylinder_radius 也未在新关系绑定中校验和携入，仅保留 prior_decisions 路径。最小修复：由原已接受候选/关系记录直接绑定并保留这些初值、单位和固定二十二成员关系；将初值一致性与允许后续编辑分开，新增小幅基线变更拒绝及受影响关系传播证据。无需重跑旧识别，也不得顺带引入未获确认的“改变半径自动移动母形极点/端点”耦合。

其余已核增量：当前 source-map 与机械记录各二十二成员/四十四侧，标签、snapshot、detail/summary 路径、原母线极点/节点/方向逐项对应；每组两个不同侧、每面只用一次，两个模板是 F0002/F0024 原 order 4、七极点、单位权重非有理基底。侧别按已知两组节点族且要求唯一，不代表任意样条类别识别。frame 保持原 +Y/u=+Z/v=+X 与 atan2 约定，anchor 是成员 index 10；实际母形不能因共同基比较而换成五极点截面边。

尾槽的四个独立值、X=0、+X 无向轴线规范方向及 x=±width/2 与用户原话记录、slot-plan-c2 来源及 P1 派生内容一致；本次薄绑定调用原已接受 plan_slot 对当前输入做一致性核对，不重跑旧几何测试。evaluate_slot 的宽度/半径/Y/Z 单独输入及居中输出保持关系，有限正宽/半径与有限坐标检查存在。输出保留 edit_domains/material_side/trim/active_support 未验证，geometry_proven、native_binding_verified、execution_approved 均 false；新确认不是 native 编辑或全几何证明。

[首次测试输出](p3-decision-bindings-c1.txt)为 **32 passed**、退出 0。新测试覆盖 22×2/原独立基底、通过临时 phase 参数与同侧极点输入的代数传播、另一侧不随动、槽四值/居中、决定/来源/顺序/缺侧/错侧/节点/框架及非法值反例；未覆盖 R20 的字段编辑或 R21 的小幅基线漂移。准确命令和 cwd 由 SI 工具转录，cwd=`C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_decision_bindings.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-decision-bindings-c1.txt; exit $LASTEXITCODE
```

同 cwd 唯一首次实际输出退出 0，二十二成员/四十四侧/四个槽独立参数，实际命令：

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -B tests/v3/run_decision_bindings.py; exit $LASTEXITCODE
```

评审只读代码、测试及产物，没有执行上述命令。等待两个关联问题一次合并修复及最小定向证据；旧输出保留，若输出合同改变则另存新版本，不覆盖用户决定或原采集。

### V.2 R20/R21 闭环与两决定 C2 来源绑定接受

**R20、R21 CLOSED；受限接受两决定 C2 来源绑定，无本批剩余阻塞。** 只审本次 delta、定向测试和 [decision-bindings-c2.json](../../../workspace/v3/p3/P3-DECISIONS-02/decision-bindings-c2.json)，继承 V/V.1 未受影响结论。没有重跑原 32 项、旧识别/几何测试或 NX，原 C1 文件保留。

R20：输出现分别保留来源基准 `reference_phase_rad` 和当前驱动 `shared_phase_rad`；求值以当前值或显式覆盖值减去独立固定参考，anchor/index 仍用既有约定。新增字段编辑用例将当前相位增加 0.05 rad、保持 reference 不变，在全部二十二位置核默认求值与显式覆盖相同，且极点确实移动；原 `.25 mm` 同侧极点输入和 `.1 rad` 相位覆盖传播正例仍通过。reference 是来源基准，后续参数编辑不得把它一并改写成当前值。

R21：phase、pitch-circle radius、shared cylinder radius 的初值现精确对应原已接受候选参数，并检查各维度/单位及固定 count、full turn、派生 pitch；观测角残差只用于匹配，不能代替初值绑定。三项各增加 1e-10 的反例均被拒绝。输出保留原确认的圆柱共享半径 0.7363898417823 mm、节圆半径 11.848889841783512 mm 及二十二轴位置关系。新轴位置求值只实现原 frame 下 `origin + R*(cos(angle)*u + sin(angle)*v)`，定向检查二十二位置及相位/节圆半径变化；没有将半径改动擅自耦合到母形极点或端点，`radius_to_flank_endpoint_coupling` 明确仍为 unverified_constraint_requirement。

[C2 定向日志](p3-decision-bindings-c2.txt)为 **7 passed**、退出 0：五个选定节点，其中原参数微改反例参数化为三项。包含两个直接受影响正例、当前相位字段编辑、已确认轴位置关系以及三个原初值反例；其余 C1 适用证据继承，不重复整矩阵。准确命令由 SI 实际工具转录，cwd=`C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_decision_bindings.py::test_22_member_bijection_and_original_independent_bases tests/v3/test_decision_bindings.py::test_shared_pole_and_phase_propagate_to_all_22_without_coupling_sides tests/v3/test_decision_bindings.py::test_editing_current_phase_does_not_move_reference_phase tests/v3/test_decision_bindings.py::test_confirmed_axis_relations_propagate_without_claiming_flank_coupling tests/v3/test_decision_bindings.py::test_original_relation_parameter_tiny_tamper_is_rejected 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-decision-bindings-c2.txt; exit $LASTEXITCODE
```

实际 C2 输出同 cwd、一次退出 0，runner 改为独立 C2 文件、允许已有父目录但仍独占创建文件，不覆盖 C1；命令为：

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -B tests/v3/run_decision_bindings.py; exit $LASTEXITCODE
```

实际 C2 仍二十二成员/四十四个不同侧来源；成员记录、两个原始模板和整个尾槽绑定与 C1 相同，新增独立参考/当前相位及原共享半径/轴位置表达式。槽四独立参数及 x=0/±width/2 没有扩大成额外联动。顶层及两区域 geometry_proven、native_binding_verified、execution_approved 保持 false，旧 0.001 mm 目标的 achievement 仍 unverified。

剩余工作为每个成员的原始 trim/连接与可见极点支持、半径与母形端点约束、槽及其他区域材料侧、允许编辑区间与后端落地。定向代数测试不证明任意有限输入都可形成有效零件，用户意图确认也不证明全源几何等价；本接受不使样件 DAG ready，不关闭 P3 或进入 P4。

## W. DAG02 已确认意图与局部证据汇总增量接受

**受限接受 DAG02 汇总增量，无本批阻塞发现。** 范围仅 [run_regional_design_dag.py](../run_regional_design_dag.py)、实际 [P3-DAG-02/design-dag.json](../../../workspace/v3/p3/P3-DAG-02/design-dag.json)及须共读的 [clarifications.md](../../../workspace/v3/p3/P3-DAG-02/clarifications.md)。不重审已接受的 binder、DAG 核心、槽/肩/头部数学，不运行测试或 NX。

入口通过已审 `build_intents(load_inputs(ROOT))` 从原决定与来源重建结果，要求与 decision-bindings-c2 完整有限 JSON 逐字段相等，才把其 flanks/rear_slot/retained_geometry_target 复制进 confirmed_design_intents；不是手填 confirmed。实际输出这三个子对象与 C2 完全相同，22 成员、44 侧及四个槽独立参数保持来源范围。核心 DAG 的缺证明链区域 claims 仍 unknown/observed，参数仍 observed、没有伪造通用合同 attestation。四独立尺寸、固定 center_x=0、两个派生侧面式 ±slot_width/2 的单位、数值、分类及消费者清单对应当前意图。

已核实际责任账：七区域合计 235 个不同 P1 面，无重复/遗漏，reviewed_design_face_count=0、verified_geometric_explanation_count=0，p3_ready=false、execution_approved=false。核心 unconfirmed_parameters/region_parameters_missing 表示该合同的审查证明链、具体构造消费者尚缺，不表示用户对 V 节两项问题仍未回答。SI 已在未来 runner 输出中增加解释，并以 sidecar 澄清本次历史 JSON；未改核心门禁或偷偷提升 confirmation 字段。

局部证据引用逐项对应另一份 [区域独立评审](p3-region-plan-review.md) 的 X/Y/Z 接受范围，不重复其计算：肩 C4 仅 F0047、候选 S0 下的表达式界/退出，实际 stock、材料侧及 0..0.863 rad FIN/过切仍开；头 C3 仅 V01 与 F0041/F0046 的 V02 局部条件关闭，F0156/完整裁剪及其余区段未关；尾槽 Z 仅给定 S0/初值的有限裁剪和来源分解。runner 对 Markdown 的字符串存在检查只是引用完整性检查，不是自动验证独立审查结论的通用机制；本节已人工核对实际 X/Y/Z 的限制，不能把未来任意同名文档当作自动放行依据。

尾槽实值传递正确：三主面 15 个唯一邻边与 16 个区域边分开，后者增加的是 E0470；候选参与区间/终点数据与 region-construction.json 相同。E0619 残差 0.0010014998143148546 mm 原值保留，只是单个 JID 文本点对载体的观察，未变成全边界误差界或 P6 pass/fail。审查指出原 JSON 的 `unbounded-precision` 易误读为无限精度，SI 已将未来 runner 文字改为 `unverified positional precision`；历史 JSON 不重算/覆盖，由 sidecar 明确纠正含义，数据和状态没有改动。接受的是 JSON 加澄清说明，不将该历史词语按无限精度解释。

SI 工具转录记录仅执行一次 CLI 帮助检查及一次真实 DAG02 组装，均退出 0；没有新增测试矩阵。cwd 均为 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`，准确命令：

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -B tests/v3/run_regional_design_dag.py --help; exit $LASTEXITCODE
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -B tests/v3/run_regional_design_dag.py; exit $LASTEXITCODE
```

帮助路径在读取/生成产物前退出；实际输出使用新目录及独占文件。上述文字/门禁解释发生在实际 JSON 生成之后，sidecar 如实记录该先后，没有为文义修改重跑生成、数值分析或旧验证。本汇总可作为当前 P3 检查点，仍须解决真实包络、源有向 trim/材料侧、参数消费者与允许域、组合顺序及后续执行/误差验证；不接受整件构造、不关闭 P3，也不恢复被否定的历史 C2 肩扫角或上头布尔方案。

## X. P3-SHOULDERS-01 四十二项新肩部定义计划受限接受

**该限定新读取计划无阻塞发现，在下述执行边界内接受；不是四十二项已成功或肩部同形的声明。** 审查 [read-queue.json](../../../workspace/v3/p3/P3-SHOULDERS-01/read-queue.json)、四十二个 selector envelope、[既有 parser 预检记录](../../../workspace/v3/p3/P3-SHOULDERS-01/selector-preflight.json)，并只读核 P1 拓扑及 [C5 覆盖记录](../../../workspace/v3/p3/P3-SWEPT-ANALYSIS-01/shoulder-trim-correspondence-c5.json) 的集合/关联；未重新运行 parser、旧测试或 NX，不审 C5 其他几何推导。

独立按 P1 同一快照边关联核得：四十四个已读长直翼各恰有一个 y_min≥-71.001 mm 的 SurfaceOfRevolution 邻面，公共边均为 Spline，四十四个肩部目标各不相同。其与既有二十二成员圆柱的归属、共边及 C5 mappings 一致。排除原 F0004/F0022 后的集合恰等于队列四十二项；每项 sequence、直翼/成员/共边引用对应，不包含两已读肩面或其他目标。这是逐对象原母线/同树 FIN 的具体信息缺口，不能以用户确认共享直翼母形推定肩部定义相同，亦不能把 C5 的拓扑关联当作肩部完整几何相等。

四十二项 selector 与 P1 的 UF19、SurfaceOfRevolution、六分量 bbox 及四边逐字段相同；原 radius/radius_data 均为 0，但不由此预言真实 BREP 类型。0.001 mm 描述匹配域内各唯一。所有文件都是正确 `{source_snapshot_id, selectors}` envelope、每文件一个目标；已记录 existing explicit_selectors 一次全接受、native_called=false，本审不重复该预检。当前各 evidence_dir 均尚不存在，旧已取得定义/失败历史继续继承而不重读。

执行可保持 root 逐项调用既有 once runner 和已接受 strict validate_evidence，不要求为本次新增软件 controller，也不扩大旧 Swept controller 的固定 scope。本接受不包含任何未提交的新 helper 实现。若封装操作命令，只能处理 root 此次明确给出的 1..4 项清单，不能外层自动续批。首批一项，后续每批显式最多四项，累计最多四十二个新目标；每批回交 root 核查后才释放下一批。

除严格 validator 的单目标、当前 epoch/binding/load、完整 native/managed clean、完整空库存 diff 和 RETURNED/HUMAN_OWNED 外，本队列还要求实际 root geometry_type=205、generator_type=102。即使普通读取本身 clean，只要不是此期待类型，也按本队列 unsupported 停止，不跳过/扩大域。match=0.001 mm、curve/surface requested 各 0.0001 mm、angular=0.0001 rad；topology 921600 bytes、单面 2097152 bytes、4096 events 不变。请求值不是实际精度，类型/预算成功必须由新结果证明。

每次 CLI 前独占保存并 fsync DISPATCHED；在派发前核持久 STOP、未决项和当前会话，前项原始证据通过上述全部条件后才可继续。成功证据及连续完成集合需持久记录，不能只靠聊天计数。异常、缺记录、错误退出、unknown、dirty、overflow、root 不符或中断均停止剩余项、持久 STOP、保留原产物，不重试、不跳过、不解冻；输入前置错误也只能走另行明确核查的替代计划，不自动重发。掉电/中断不能因缺文件就认定从未派发，fsync 不证明硬件/目录掉电持久性；不自动跨 epoch 续队或复用旧 ownership/Tag。

此刻仅计划准备、未启动 NX。实际开始前 TL/root 须保存新普通独立源副本/before、已接受 T13.o C2 五制品隔离 runtime 的直接字节关联、普通无 reparse 路径前检及三十六个实际导入 Python 源冻结记录；私有配置只作本次 connection-only 使用、不输出。启动后获取当前实际 PID:UTC-start-ticks，所有 once 强制 strict expected-session-epoch；活跃读取期间不改导入源/runtime、不热换 DLL。

正常逐项归还后仅正常关闭本次 NX、不保存，记录相关 NX/helper/Journal 收尾、源件/工作副本直接字节及源 mtime 保全、冻结源比对；异常现场仍按已有 UNKNOWN 人工核查与授权收尾规则处理，不强杀或伪造正常归还。即使四十二项均 clean，也只填各自原生定义/拓扑来源，完整 trim、肩部共享关系、stock/材料侧、过切和全域误差仍待后续限定分析，不宣布整 P3 DONE 或追加无限采样。

### X.1 本实验单项 operator 首审：CHANGES

范围是冻结的 [operator-one.py](../../../workspace/v3/p3/P3-SHOULDERS-01/operator-one.py)、[新增 fake 测试](../test_shoulder_operator.py)及 [C1 首测日志](p3-shoulder-operator-c1.txt)。X 节的计划接受不自动包括该新操作代码。**C1 有以下三个待关闭的本实验合同缺口；未启动 NX，不接受尚未完成的修复。** SI 已自报 R22，本审核实并一并提出其余关联问题；不扩展为一般控制器或对本地有权限者协同伪造的认证。

1. **R22 / 中等 / OPEN：历史原始退出/命令记录缺失仍可继续派发。** `_load_ledger` 给 strict validator 固定传入 1，再与 completion/CLEAN 的 1 比较，没有读取先前实际 `python-exit-record.json`；该记录丢失或变成其他退出码仍会被当成完整成功证据。`command.json` 同样未纳入历史核对。最小修复：每项历史原始退出码须存在、为严格整数 1、与 CLEAN/completion 相符；命令 argv/cwd 与本实验固定调用、初始化锁定解释器一致。缺失或变更必须零新派发、保留 STOP/LOCK，不能用人为填入的 1 补原始证据。

2. **R23 / 中等 / OPEN：新调度封装自身未被运行源码冻结覆盖。** `_sources` 只比对三十六个旧导入 Python 源；INIT 未锁定本 operator 文件，修改它后仍可通过现有源锁。其本身控制 STOP、事件次序和子调用，是本次实际执行代码，不能遗漏制品关联。最小修复：单独保存并比较本 operator 的独立冻结字节，保持原三十六导入源含义不变；封装改动时拒绝继续，不需要 hash、安装或通用版本管理。

3. **R24 / 中等 / OPEN：init 可固定与批准数值不一致的计划。** `_plan` 未检查 `thresholds` 和 `budgets_unchanged`，C1 fake 计划连这两项都可缺失；随后 `_context`/command 使用硬编码另一组值。即使实际当前 JSON 正确，初始化合同仍不能保证锁定计划与 X 节批准的实际调用相符。最小修复：在 init 前精确核本实验 match/curve/surface/angular 值、单位字段及不变 topology/per-face/events 预算；缺失/错值在派发前拒绝。无需扩大几何域或改既有读取器。

其余 C1 控制流静态可接受：显式 init 不调用 runner，已有 STOP/anchor/ledger/native 项拒绝重初始化；单次只接受下一个规范索引。外部 LEDGER-STARTED 与 INIT 固定 plan/coverage/context/源清单、连接配置另存私有字节；每项外部 dispatch 先 fsync，再创建单项证据/DISPATCHED/command，子进程后须经 strict validator 与实际 205/102 检查才写 CLEAN 和外部 completion。每次从头核连续原始证据，缺完整末项目录仍因外部 completion 被发现；中断、例外、STOP 或未决事件保留锁，不自动跳过/清锁/续项。初始化后 read-queue 和 C5 coverage 必须不变，结果写 ledger，不在 active 期间改 plan.items.state。移除第二次 normalize 合理，因为 strict validator 已执行该合同。

首测是本实验新 fake 文件唯一一次，**14 passed、退出 0**，不是旧 once/queue 矩阵重跑。覆盖 init/单项/fsync 调用存在、无自动下一项、STOP、外部未完成 dispatch、缺完整末项目录、连续旧 proof 损坏、epoch/plan/config/跳号/ledger缺失/意外目录、实际 root/gen 附加门禁和重复 init。fake validator/runner 不证明真实 native trace、实际加载或硬件掉电持久性；未将源码静态可见的 BaseException/锁竞争分支另称已故障注入测试。真实 `_plan` 的一次只读检查为 42 项/44 映射成功，不是实读或初始化。

准确首次测试命令由 SI 工具转录，cwd=`C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_shoulder_operator.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-shoulder-operator-c1.txt; exit $LASTEXITCODE
```

本审没有运行上述测试或任何实际 operator init/索引。等待三项一次合并最小修复及直接受影响 fake 证据；无需重跑原采集、old validator/native 或扩大软件 controller。配置冻结副本仍属于私有运行资料，不能随源码/公开审查输出传播。

### X.2 R22—R24 闭环与 operator C2 受限接受

**R22、R23、R24 CLOSED；接受本实验 operator C2，无本批剩余阻塞。** 仅审合并 delta、[C2 定向日志](p3-shoulder-operator-c2.txt)及新增/直接受影响 fake 断言，没有运行测试、实际 init、索引或 NX；X/X.1 未受影响边界继承。TL/root 落实 X 节准备记录后可新启受控 NX，init 一次，再显式索引 1 取得首项实机证据；本结论不是已有真实采集成功声明。

R22：INIT context 记录实际解释器 resolved 路径，后续 `_context` 与初始 context 比较时可发现解释器变化；统一 `_command` 用这个锁定值和固定参数构造 argv。外部 dispatch/completion 同时保存 command/cwd，项内 command 必须精确相符；历史 python-exit-record 必须存在、字段为严格整数 1，并与 CLEAN/completion 对应，随后才核原始 strict proof 和实际 205/102。原始退出缺失、0、bool 及 command 缺失/epoch 被改的五类反例均在旧项之后、下一项调用之前拒绝，累计实际 fake 调用数没有增加。

R23：init 单独创建并 fsync `operator-ledger/operator.frozen`，每次加载 ledger 在任何新外部 dispatch 前将本 operator 文件与其直接字节比较；原三十六导入源冻结继续独立核对。封装文件或解释器路径变化的两个反例均零派发、STOP。它固定本次执行版本，不声称防止有权限者同时替换代码和全部冻结记录；连接冻结副本继续私有。

R24：`_plan` 在 init 写 anchor 之前，核 X 节固定的四阈值、非精度声明及 topology/per-face/events 三预算，还核首批 1、最大显式批 4。缺阈值、改阈值、缺预算、events=4097、最大批=5 五种反例均拒绝，未创建 STARTED anchor、无 runner 调用。真实固定计划在新增守卫后又只读检查一次，仍为 42 项/44 映射；这次检查有 R24 改动作为原因，不是重做旧采集。

守卫顺序保持：锁 → 固定上下文/计划/C5/导入源/封装/config → 完整历史连续证据及退出/命令 → 明确下一索引 → fsync 外部 dispatch → 项内 DISPATCHED/command → 受控 once → 原始退出/strict/205-102 → CLEAN/外部 completion。任何异常或 STOP 保留锁和已产生证据；原异常分支不删除、重试或自动解冻。源码中不存在自动派下一索引/下一批，批次上限仍由 root 的显式释放流程约束；未修改旧 Swept controller 范围或增加第二遍 normalize。

C2 结果 **20 passed、退出 0**，是十组所选新/直接受影响节点展开后的计数；C1 其余有效行为证据继承，不重复全部旧 once/queue/native 矩阵。继续/缺末项/epoch、plan、config 变化以及错误 root/gen 两类回归也通过。所有调度仍为 fake，不能证明真实加载、native 行为、未注入的故障或掉电持久性。

准确命令按 SI 工具转录，cwd=`C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`，唯一 C2 定向运行：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_shoulder_operator.py::test_init_first_one_external_fsync_and_no_automatic_next tests/v3/test_shoulder_operator.py::test_contiguous_previous_proof_is_revalidated_before_next tests/v3/test_shoulder_operator.py::test_missing_entire_last_completed_directory_is_not_replayed tests/v3/test_shoulder_operator.py::test_changed_context_plan_or_incomplete_state_stops_without_dispatch[wrong_epoch] tests/v3/test_shoulder_operator.py::test_changed_context_plan_or_incomplete_state_stops_without_dispatch[changed_plan] tests/v3/test_shoulder_operator.py::test_changed_context_plan_or_incomplete_state_stops_without_dispatch[changed_config] tests/v3/test_shoulder_operator.py::test_wrong_root_stops_with_dispatch_but_no_completion tests/v3/test_shoulder_operator.py::test_prior_real_exit_and_command_records_must_match_external_ledger tests/v3/test_shoulder_operator.py::test_operator_and_interpreter_are_bound_before_dispatch tests/v3/test_shoulder_operator.py::test_init_rejects_unapproved_thresholds_budgets_and_batch 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-shoulder-operator-c2.txt; exit $LASTEXITCODE
```

同 cwd 真实计划只读检查，退出 0、输出 accepted_plan_items=42/reviewed_mappings=44，未建立 ledger 或启动 NX：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -B -c "import importlib.util,pathlib; root=pathlib.Path.cwd(); base=(root/'workspace/v3/p3/P3-SHOULDERS-01').resolve(); s=importlib.util.spec_from_file_location('shoulder_operator_actual',base/'operator-one.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); p,c=m._plan(root,base); print('accepted_plan_items=',len(p['items']),'reviewed_mappings=',len(c['mappings']))"; exit $LASTEXITCODE
```

之后仍须每项真实当前 epoch、唯一匹配、完整 clean/空 diff/HUMAN 和实际 205/102 成立才续；读取期间 plan/C5/封装/导入源/config/runtime 不改，首异常 STOP、不重放。原有准备、私有资料隔离、归还/正常不保存退出及磁盘/源码保全要求不变；不把辅助脚本通过或四十二项计划接受升为几何完成、P3 DONE 或无限补读许可。

### X.3 四十二项新肩部实际采集及收尾接受

**受限接受 P3-SHOULDERS-01 四十二项新增原生定义/拓扑采集及正常收尾，无本批阻塞发现。** 逐项读取所有新原始 summary/takeover/snapshot/status、command/exit/DISPATCHED/CLEAN 及外部 dispatch/completion，另核准备后的收尾保全记录。未运行 fake 测试、产品 validator、NX 或旧两面读取，未输出私有 INIT/context/config 内容。X/X.2 的软件/计划审查直接继承。

[实读索引](p3-shoulders-read-index.md)与 [completion-manifest](../../../workspace/v3/p3/P3-SHOULDERS-01/completion-manifest.json)列每项唯一 snapshot ID、证据及命令路径。root 工具转录记录在项目根用 `python -B workspace/v3/p3/P3-SHOULDERS-01/operator-one.py init` 一次退出 0，随后每个索引 1..42 各一次、各退出 0；首项 1、十个显式四项批次覆盖 2..41、最后单项 42，批间回交 root。每项原始 command.json 保留实际 `C:\Python314\python.exe`、完整 once argv/cwd，stdout/stderr 均在项内；内部 once 的真实退出码均为严格整数 1，对应 recorded-response/INCONCLUSIVE，不是几何通过。

四十二个目录从 native-01-F0013 至 native-42-F0231 与冻结计划连续对应，无重复目标或额外目录；每项当前面唯一匹配，请求类型/边数/bbox 与 selector 相同，P1 来源与本次独立工作件路径一致。takeover/snapshot/status 及外部记录使用本次同一 epoch，load_instance/读 revision 对应，binding_epoch 从 1 至 83、步长 2；四十二个 snapshot ID 均不相同。命令的 strict epoch 与 selector 路径、真实退出记录、项内标记及两份外部事件均逐字段对应。

每项 63 个 native 事件、四边、root type 205 和 generator type 102；原母线均记录 order 4、七极点。这些是逐项读得的定义，不能由阶数/极点数相同推出肩部同形。全部 2646 个事件实际 called、序号连续、dirty_before/after=false。1890 个具有返回码的事件 rc=0；756 个 UF_BREP_ask_identifier 事件按已接受 void 合同为 rc=null，不伪称返回 0。窄查 native 序列化源码的 has_rc=false 与归一化 void 合同相符。

每项 BREP geometry 查询和释放配对、适用返回码为 0，topology 成功释放；各有一个圆边通过已接受 EVAL 六阶段完整初始化/读取/free、rc=0，未调用对应圆边 BREP geometry 路径。trace 为 CLEAN_TRACE、edge_coverage_complete=true，无 failure/first_dirty、overflow 或 incomplete_observed。每项八次托管 dirty 采样 false，另一个 native 聚合条 dirty=null/CLEAN_TRACE；未把聚合条当额外 false 采样。

每项完整库存含 235 面/622 边，实际 inventory_before、inventory_after 与 inventory 相同，diff=complete/changes=[]、two_native_samples_equal=true；read_consistency_fault=false、first_change=null、writes_halted=false。status 无活动操作，读前后 modified=false；status 仍是归还前 AI_OWNED 记录，成功归还后的 summary 均 RETURNED/HUMAN_OWNED。外部 ledger 恰有 42 dispatch 和 42 completion，各完成 ID/事件数/205/102 与原始响应相符；本审按真实名称核无 STOP、无 OPERATOR-LOCK.json，未只检查无关 LOCK.json。

[退出保全](../../../workspace/v3/p3/P3-SHOULDERS-01/shutdown-preservation.json)记录最终归还后受控 NX 正常 Alt+F4 退出、无保存提示且未保存、不强杀/热换；[进程记录](../../../workspace/v3/p3/P3-SHOULDERS-01/shutdown-processes.json)确认受控 PID 已消失、所观察相关进程为空。源件/工作副本与 before 直接字节相同、源 mtime 未变；[导入源冻结](../../../workspace/v3/p3/P3-SHOULDERS-01/source-freeze-at-shutdown.json)为三十六源、changed=[]，[operator-preservation](../../../workspace/v3/p3/P3-SHOULDERS-01/operator-preservation.json)及 TV 索引确认 operator/config 与各自冻结副本逐字节相同。

两项审计更正已透明保留：初次锁记录误查无关 LOCK.json 后按 OPERATOR-LOCK.json 修正；TV 初次把所有事件一概要求 rc=0 的过强断言失败，后按 void/null 合同核实。它们是检查/记录纠正，不是新采集失败，不触发重读或删除历史。

结合原 F0004/F0022，四十四个关联肩面现各有受限详细定义。所有新增项仍 geometry_details_complete=false、INCONCLUSIVE；实际生成规律、成员间是否共享、全有向 trim、stock/材料侧、邻区过切、编辑域及全域误差仍须限定离线证据。可关闭该有界采集子任务，不宣布四十四肩部同形、真实构造可执行或整 P3 DONE，也不自动追加采样。

## Y. P3-CARRIERS-01 固定四十四面定义缺口范围接受

**受限接受这份固定四十四目标的新定义计划，无本次范围阻塞；尚不接受未提交的 operator 适配或启动 NX。** 只读审 [read-queue](../../../workspace/v3/p3/P3-CARRIERS-01/read-queue.json)、[gap-matrix](../../../workspace/v3/p3/P3-CARRIERS-01/gap-matrix.json)、四十四个新 envelope 及 [预检记录](../../../workspace/v3/p3/P3-CARRIERS-01/selector-preflight.json)，核 P1 与已接受 remaining-detail-inventory/分区记录的集合及逐边关联，不重跑原五十三面盘点、旧唯一性矩阵、parser 或 native。

TL 这次明确选择的是尚未取得 BREP 有向 FIN/支持曲线/参数方向的四十四个正半径 UF19 候选，非自动承接盘点中全部五十三面。新目标集合与 remaining-detail-inventory 的 SurfaceOfRevolution.remaining 精确一致、无重复；排除项恰为已有详情的九十七面，另九个未读球面与八十五个 P1 解析平面/圆柱/圆锥面均不在队列。原盘点的 new_native_queue_approved=false 继续表示盘点本身不授权执行；本节针对另行提出的固定四十四项范围。分区计数为二十一肩根、四 stock、三下头、十六头部/其他，与当前分区来源一致，不把分区计数当几何解释覆盖。

逐项核对 selector 与 P1 UF19/SurfaceOfRevolution、bbox、边数一致，radius/radius_data 均为正；每文件确为正确 P1-scoped 对象 envelope、一个 selector。已记录现有 explicit_selectors 对四十四份新文件一次预检全接受，未启动 NX；本审只核新文件内容而不重复该运行。当前 evidence_dir 尚不存在，先读 F0156，其后固定清单顺序，不覆盖或读取九十七项旧定义。

gap-matrix 的每个面原始字段、分区、全边集合、边类型/邻接面及邻面已有 detail-summary 引用均与 P1/已接受盘点相符。`edges_without_adjacent_face_detail` 重新按邻接与已有详情集合核对一致，四十四面各至少有一条这样的边；已有邻面记录也仍标注跨会话同边绑定未验证，不把邻面数据当成本面完整 FIN。F0156 四边中三条没有已读邻面详情，优先取得其源 UV/方向有具体依据；F0126 为四十八边，其中二十四条无已读邻面详情。新读取目的因此不是重测已有标量半径，而是补本面坐标帧、有向环/FIN、支持边及源材料方向所需定义。

P1 UF19 的 origin 明确只作轴上位置观察，未当成 BREP torus center；normal_sense 也未单独提升为材料占据结论。root 204 是各项的队列预期，不是已观测或已证明 ring/torus。若新结果非 204，即使其一般读取 clean，也须保留结果并按本队列 unsupported 停止，不能跳面、改预期后重放或自动扩域。完整有向 trim、源精度和材料侧能否由新结果最终解释仍需后续独立分析，读取本身不保证关闭这些结论。

数值沿既有受控范围：match=0.001 mm、curve/surface requested 各 0.0001 mm、angular=0.0001 rad；topology 921600 bytes、per-face 2097152 bytes、4096 events 不变。F0126 的四十八边不获得额外预算或成功保证，首次 overflow/不完整即停；阈值和请求值不代表实际几何精度。只允许首批一项、随后 root 显式每项释放且每批最多四项、累计最多四十四个新目标，禁止外层自动续批或重复采样。

下一软件步骤只限复制已接受单项 operator 后为本固定 cohort/204 分支作必要 delta、最小新测并另行独立审，不重造通用 controller 或重跑旧矩阵。正式操作还须 TL 接收、独立副本/新当前 epoch、隔离 C2 runtime 与源/封装/config 冻结、完整外部 dispatch/completion、strict clean/空 diff/HUMAN 等门禁；有 STOP、锁、未完成派发、dirty、unknown、错误 root 或预算事件即停止、保留、不重试/跳过/自动恢复。最终继续按既有授权正常不保存退出并保存磁盘/源码/配置保全，不强杀或热换。该范围决定不开放九球面或额外解析面补读，不使 P3 ready/DONE 或进入 P4。

### Y.1 固定 cohort/204 operator 增量首审及 R25

范围是 [新 operator](../../../workspace/v3/p3/P3-CARRIERS-01/operator-one.py) 相对 X.2 已接受版的文本 delta、[新 fake 文件](../test_carrier_operator.py)与 [C1 日志](p3-carrier-operator-c1.txt)。逐差异核定：只换固定四十四面及其 P1/gap/inventory/分区来源合同、ledger schema/上限和 root 204 分支；未改初始化、当前 epoch、封装/导入源/config 冻结、外置连续记录、真实退出/命令校验及失败保留锁的控制流。旧 14+20 适用证据继承，没有重跑旧矩阵。

**R25 / 中等 / 首审 OPEN：仅核 type=204，空或退化的定义可被新分支记 CLEAN。** 新 `_root_and_generator` 最初只检查 type，并不要求 center、axis、u0_ref_direction、major/minor 字段；C1 fake 成功输入实际只有 `{"type":204}`。旧 strict 主要核来源/trace/拓扑及归还，不能替代本分支的载体字段要求。即使 native 序列化通常产生这些字段，完整定义缺失/零轴等异常仍不应让本计划进入下一项。此项由 SI 自查提出，经本审确认。

最小关闭条件：在 strict 成功后、CLEAN/completion 之前核 center/axis/u0 各三个有限实数、轴/参向非零且非共线、两个半径有限正值；缺失/退化保留原始数据、STOP/锁、不写完成或派下一项。不新增 major>minor 的 ring 限制，不宣称材料侧、坐标误差或完整 torus 几何已证明。

其余新范围合同可接受：plan 必须完整列四十四面、首 F0156 后其余标签固定排序，九十七已有详情和九球排除与已接受盘点一致；每项 root 预期明确 candidate，实际 P1 UF19 正半径、bbox/边数、局部路径/正确 envelope 与互反邻接均核对。gap 的每条边、邻面及既有 summary 引用按 P1 重建后逐字段相等；覆盖全部目标、无源详情边缺口仍须存在。初始化把完整盘点/gap/目标分区绑定入 ledger，active 时这些输入不能更改。独立只读核当前实际文件的有序 edge_evidence/缺边数组及首项顺序与新分支一致，没有重新运行原五十三面或 envelope 预检。

C1 新 fake **11 passed、退出 0**：无 generator 的 204、两个显式单项成功，无自动下一项；九类已读/球面/遗漏/重复/UF/预期/预算/gap/首项错误拒绝；错误 root 保留原始 dispatch、STOP/锁、无 completion 且再次调用不能派发。它不证明真实 native 204 数据或 R25 所缺字段。cwd=`C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`，准确命令由 SI 工具转录：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_carrier_operator.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-carrier-operator-c1.txt; exit $LASTEXITCODE
```

### Y.2 R25 闭环与 operator C2 最终受限接受

**R25 CLOSED；接受固定四十四面 carrier operator C2，无本批剩余阻塞。** 只核新增载荷守卫及 [C2 定向日志](p3-carrier-operator-c2.txt)，未执行测试、operator init/索引或 NX。结合 Y 节范围和下列已记录准备，允许 TL/root 新启当前受控会话、init 一次、先 F0156 单项取得真实证据；其余项仍按首项检查与显式至多四项批次释放，不能把软件接受当实读成功。

载荷守卫先要求严格整数 type=204，再要求 center/axis/u0 三分量且为有限非 bool 实数、major/minor 有限且正。轴与参向各按最大分量缩放后归一，再核叉积非零，避免简单原分量乘积因尺度溢出/下溢丢失方向；它只检查非退化信息，不要求精确正交/单位源向量或证明参数帧真实性。半径不比较大小，major=minor 的 fake 正例通过，未引入 ring 类型限制或把 P1 半径标量当实际 BREP 定义。

C2 **13 passed、退出 0**，仅四个直接相关节点展开：原无 generator 正例、错误 root、十个缺失/非法载荷变体及正半径非 ring 边界。缺中心、NaN/布尔中心、缺轴/零轴、零参向/平行方向、零 major、负 minor、缺半径均保留 raw snapshot、外部 dispatch、STOP/锁且无 completion；非有限 JSON 在既有读取门禁先拒绝，同样是合适的停止，不伪称全部变体都到达新增字段分支。旧 11/14/20 未重复运行，fake 仍不证明真实环境或任意 204 形状有效。

同 cwd 唯一 C2 定向命令：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_carrier_operator.py::test_204_without_generator_and_two_explicit_single_items tests/v3/test_carrier_operator.py::test_wrong_root_preserves_stop_and_never_sends_next tests/v3/test_carrier_operator.py::test_invalid_204_fields_stop_and_preserve_raw_evidence tests/v3/test_carrier_operator.py::test_positive_nonring_204_is_not_automatically_rejected 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-carrier-operator-c2.txt; exit $LASTEXITCODE
```

已读本实验 [source-copy-record](../../../workspace/v3/p3/P3-CARRIERS-01/source-copy-record.json)、[runtime-copy-record](../../../workspace/v3/p3/P3-CARRIERS-01/runtime-copy-record.json)、[path-preflight](../../../workspace/v3/p3/P3-CARRIERS-01/path-preflight.json)及导入源记录：新副本/before 与已接受 SHOULDERS01 基线直接字节关联，五个制品为已接受 C2 托管/T13.f 原生，准备时 121 路径无 reparse，私有 connection-only 配置不公开。init 后封装、三十六导入源、配置、计划和来源包继续冻结；F0126 仍四十八边且预算不增。

guard/ledger 顺序、原退出码/命令校验、源字节锁、single-index、STOP/锁不重放、异常收尾及无自动续批均继承 X.2，没把旧控制器泛化。本接受不授权九球或其他新目标，不解除任何历史 UNKNOWN，不将读取/结构检查升为完整 trim、材料侧、native 精度、P3 ready 或整件执行许可。

### Y.3 四十四项新载体实际采集及保全接受

**受限接受 P3-CARRIERS-01 新四十四项实际采集与正常收尾，无本批阻塞发现。** 逐项独立读取新 summary/takeover/snapshot/status、原始 command/exit/DISPATCHED/CLEAN 和外部 dispatch/completion，核准备后的收尾记录；未运行产品 validator、旧 fake 测试或 NX，没有重读/复审已有九十七面，也未输出私有 INIT/context/config 内容。

[实读索引](p3-carriers-read-index.md)与 [completion-manifest](../../../workspace/v3/p3/P3-CARRIERS-01/completion-manifest.json)列每项唯一 snapshot ID、命令及原始证据路径。root 工具转录记项目根执行 `python -B workspace/v3/p3/P3-CARRIERS-01/operator-one.py init` 一次，随后每索引 1..44 各一次，外层均退出 0。首 F0156 一项、十批显式四项覆盖 2..41、最后三项 42..44，批间回交 root；不是自动外层循环。每项真实解释器、完整 argv/cwd、stdout/stderr 及内部 once 原始退出记录保留；内部退出均为严格整数 1，即 recorded-response/geometry INCONCLUSIVE，不是几何通过。

四十四个实际目录与计划连续对应、无重复/额外项；目标集合与旧九十七面/九球排除集合没有交集。每面当前匹配唯一，UF19、边数/bbox 和请求与 selector 相符，来源 P1 及独立工作件正确。takeover/snapshot/status 与记录使用本次同一 epoch，binding_epoch=1..87、步长 2，load_instance 与读 revision 对应；四十四个 snapshot ID 均唯一。原 command/真实退出/CLEAN、项内与外部 dispatch、外部 completion 的 selector/epoch/命令/ID/事件数/root 逐字段一致。外部 ledger 恰 44 dispatch、44 completion，实际无 STOP 或 OPERATOR-LOCK.json。

各实际 root 均 type 204，center/axis/u0 三分量有限、轴与参向非零非共线，major/minor 有限正值；未以 major>minor 作本队列前提或由这些结构字段宣称完整 ring/材料侧已证。所有 native 调用 dirty_before/after=false、顺序连续且 called=true。总计 4140 事件，其中 3028 个适用返回码为 0，1112 个 UF_BREP_ask_identifier void 事件按合同 rc=null。BREP geometry 查询/释放配对、topology 最终释放成立；126 组圆边 EVAL 均有完整六阶段及成功 free。无 event/geometry overflow、incomplete_observed、failure 或 first_dirty，edge coverage 完整。各项托管 dirty 采样为 false，native 聚合条保持 dirty=null/CLEAN_TRACE 的既有语义。

事件分布与原始索引一致：63×11、71×19、75×4、84×2、119×3、132×2、161×2、687×1。F0126 是索引 24、实际四十八边/687 事件，全部上述检查成立，overflow=false，原 topology/per-face/events 预算没有增加；它的成功不授权以后加预算或推广其他输入域。

每项实存 before/after/inventory 相等、完整 inventory_diff=complete/changes=[]、two_native_samples_equal=true，read_consistency_fault=false、first_change=null、writes_halted=false；status 无活动操作、读前后 modified=false。归还前 status 为 AI_OWNED，成功归还后 summary 均 RETURNED/HUMAN_OWNED。所有新项仍 geometry_details_complete=false、INCONCLUSIVE；未把 empty diff 或 native root 字段齐备当作完整源 trim/形状证明。

[shutdown-preservation](../../../workspace/v3/p3/P3-CARRIERS-01/shutdown-preservation.json)记最终归还后受控 NX 正常 Alt+F4 退出、无保存提示且未保存，不强杀/热换；[shutdown-processes](../../../workspace/v3/p3/P3-CARRIERS-01/shutdown-processes.json)确认受控 PID 已消失、所观察相关进程为空。源件/副本与 before 直接字节一致、源 mtime 未变；[source-freeze-at-shutdown](../../../workspace/v3/p3/P3-CARRIERS-01/source-freeze-at-shutdown.json)为三十六源且 changed=[]，[operator-preservation](../../../workspace/v3/p3/P3-CARRIERS-01/operator-preservation.json)及 TV 索引确认封装/config 分别与冻结副本逐字节一致。没有用元数据替代字节检查或计算 hash。

本接受可关闭固定四十四项采集子任务，交后续限定来源/方向/裁剪分析。已有九十七项继续继承、九球仍未派发；完整有向曲线对应、材料占据、组合边界、编辑域及全域误差尚未由采集证明，不升为整件 G 通过、P3 ready/DONE 或追加读取许可。

## Z. F0123 返回 FIN 图与来源证书首审：CHANGES

范围为新增 [torus_trim_certificate.py](../../../src/nx_sketch_mcp/v3/torus_trim_certificate.py)、[测试](../test_torus_trim_certificate.py)、[入口](../run_torus_trim_certificate.py)及 [F0123-certificate.json](../../../workspace/v3/p3/P3-ROOT-TRIM-01/F0123-certificate.json)。不重跑旧 spline/native 矩阵、不启动 NX，也不把本次新增证明要求倒换为 P6 整件认证。SI 自查提出单 span/内点和 solid 措辞疑点；本审确认并补充方向合同缺口。

1. **R26 / 高 / OPEN：span 对之间分离不足以证明每条曲线自身单射。** `_graph` 只检查不同 Bézier spans 的控制盒分离及全环非零有向面积。明确反例：现 square_fins 的左边换成二次控制点 `(1,-1),(1,2),(1,1)`，其余边不变；该边会越过再回到顶端接点、重复经过同一位置，但不同 span 的分离条件及非零面积仍成立，因而可被标为 validated simple graph。最小修复：每个 span 加可证明单射的保守条件（如严格单调坐标投影），再保证所用内点的 left/top/bottom/right 邻接与跨 v=0 条件；对源原图不满足时拒绝或保留 conditional，不能凭全局面积掩盖自回退。补单 span 回退负例及实际受影响正例即可，不重做旧插结算法验证。

2. **R27 / 中等 / OPEN：FIN/edge 的源 sense 与几何端点方向未交叉核对。** `_topology` 只要求 FIN geometry_sense 属于 ±1 后保存，未核它与物理 FIN 端点匹配及 edge orientation 推出的 traversal 一致；class11 的 edge.geometry_sense 甚至未限制，并只抽取转换 3D spline 的 spans 数，没有把转换端点/方向同原顶点对照。因此只翻 sense 或改变转换端点仍可能被接受为源方向一致的定义。安装 `uf_brep.h` 的 ask_geometry 合同说明曲线 geom_sense 相对拓扑 start→end；最小修复是在本支持域内按该合同检查 FIN 和 class11 端点/方向，严格 integer±1，双向歧义/不符停止。圆 evaluator 的 edge sense=null 继续合法、使用独立 evaluator 双向端点匹配，不能强填为 +1。若某方向无法从证据确认，应降级相关结论而非忽略冲突。

3. **R28 / 低 / OPEN：把 is_solid 误写为实体有效性已证。** `build_certificate` 仅核选中 body 的 is_solid=true，但 source_material_side.scope 使用 selected valid solid。最小改为“记录为 solid；UF outward 到材料侧的解释依赖有效实体前提”，保留派生图内点的实际 native face membership/整体占据未证；无需为文义修正运行额外 NX 或体有效性检查。

其余数学及范围处理合理：每个完整非零 knot span 通过已接受 restrict_bspline 的精确依赖恢复 binary64 有理控制点，原插结证明继承；不同 span 的相交排除是充分的保守凸盒检查，有向面积积分式正确。UV 端点在明确阈值内用中点作派生识别，不覆盖原 FIN；原始最大接合差约 4.2919e-12 rad、阈值 1e-8 rad 仅作关联，不是 native 精度。控制盒限定在宽度小于两个周期的单一图域，故未自动猜测跨 seam lift；一个可证简单闭环的无孔结论只能属于该派生图。当前“simple graph”断言仍须 R26 修复。

source Definition 区分三条 class10 圆 evaluator 与两条 class11 两父隐式交线的 API 转换样条，未把后者称作源文件中原存的 3D 样条。F0126/F0169 父载体经已存 source detail、P1 唯一语义候选和已接受 strict 合同绑定；frame_correspondence 明示仍为 semantic candidate，不作精确跨会话帧证明。实际 implicit branch/source domain、API FIN/3D 转换与源对应误差、候选 stock/material 角色仍 conditional/open，execution_approved=false。对派生内点使用 torus 右手参数式、geometry_sense 一次定向的形式正确，不能再把 P1 normal_sense 乘一次或把派生内点视为原面成员已证。

[首次新测日志](p3-torus-trim-c1.txt)为 **16 passed**、退出 0，包含实际 F0123 五 FIN、F0125 四 FIN/全部非零 spans、新拓扑/状态/选项/映射/方向字段/缺边/顶点/多环拒绝、图跨周期/交叉/断开与样条基底反例。它未覆盖上述单 span 和 source sense 相容性问题，不以通过数代替证明。准确命令由 SI 工具转录，cwd=`C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_torus_trim_certificate.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-torus-trim-c1.txt; exit $LASTEXITCODE
```

实际证书一次生成、同 cwd、退出 0，命令如下；本审仅读产物、未重生成：

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -B tests/v3/run_torus_trim_certificate.py; exit $LASTEXITCODE
```

等待三项合并最小修复与直接相关证据。证书的目标是当前 PRT 返回定义及派生 FIN 图，不要求补历史 STEP 精度；但也不能以历史 STEP 不在目标内为由消除当前隐式支路/原生 trim 对应的具体开放项。

### Z.1 C2 图/方向修复闭环与单位入口缺口

**R26、R27、R28 CLOSED；当前还需关闭 R29 后接受新模块。** 只核 C2 delta、[定向日志](p3-torus-trim-c2.txt)及 [F0123-certificate-c2.json](../../../workspace/v3/p3/P3-ROOT-TRIM-01/F0123-certificate-c2.json)，没有运行测试/脚本或 NX。C1 原产物保留。

R26：每个派生 Bézier span 至少一个坐标的精确控制差全同弱号且有严格非零项，故其导数在开参数区间严格同号，闭区间曲线单射；这允许端点导数为零但排除回退/自重叠。再结合原 span 对凸盒分离、端点闭合和非零有向面积，可支持本保守域内简单闭环。新增 left 与上下边邻接、左边跨 v=0、class11 链 V 同向严格单调及正宽条带条件，为派生内点提供具体依据。原二次回退反例被拒绝，实际 F0123 五 FIN 和 F0125 四 FIN/五非零 spans 正例仍成立。

R27：FIN sense 为严格 integer±1，必须与端点映射和 edge orientation 得出的遍历同向性一致；class11 转换 3D 曲线完整 spans 的两端作双向唯一顶点匹配并与 edge sense 相符。圆 evaluator 保留 null BREP sense，独立用两向端点定向，另核其轴向量单位性/非退化。只翻 FIN sense、class11 sense、布尔替代或改变转换端点等反例均拒绝；未把匹配门限升为全曲线误差证书。R28：实际材料侧字段已改为 conditional_local_orientation，明确“body reported solid；有效实体是 UF outward/material 解释前提”，派生点的真实 source face membership 和整体占据仍未证。

本次数学声明只适用于派生接合后的有理控制网。实际 C2 的五段、约 4.2919e-12 rad 接合差、精确有向面积和派生内点记录保留，真实 implicit 分支、API 表示对应及 stock/tool/source 关系仍 conditional；source_definition 的 accepted_under_recorded_API_contract 不等于实际 trim 或整体几何验收。

**R29 / 中等 / OPEN：证书固定输出 mm，但来源入口未固定毫米。** `build_certificate` 的 target.unit 与 match_mm 约定为 mm，而 P1 和 `_load_detail` 没有显式要求 Millimeters；继承的 detail normalizer 支持 Inches/Meters，不能替本证书补固定毫米合同。异单位或缺失单位若未在本层拒绝，会使端点距离和输出单位语义不可靠。最小修复：P1 及每份加载的 target/parent detail 明确相同毫米单位，不默默换算或覆盖字段，补新单位拒绝及受影响正例。当前实际 P1/F0123/F0126/F0169 均已只读核为 Millimeters，R29 不是这些既有数据已发生单位错误，也不需重读 native 或为相同数值重生成证书。

C2 六个选定节点展开为 **23 passed、退出 0**，其中拓扑拒绝节点含十八类变体；未重跑未受影响的完整 span 基底用例或旧矩阵。准确命令按 SI 工具转录，cwd=`C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_torus_trim_certificate.py::test_actual_five_fin_source_classification_and_graph tests/v3/test_torus_trim_certificate.py::test_four_fin_source_has_all_nonzero_spans tests/v3/test_torus_trim_certificate.py::test_source_topology_rejects_incomplete_or_inconsistent_data tests/v3/test_torus_trim_certificate.py::test_synthetic_closed_graph_and_periodic_seam_rejected tests/v3/test_torus_trim_certificate.py::test_crossing_or_disconnected_derived_graph_is_not_accepted tests/v3/test_torus_trim_certificate.py::test_single_bezier_span_reversal_cannot_hide_self_overlap 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-torus-trim-c2.txt; exit $LASTEXITCODE
```

同 cwd 新 C2 产物一次生成、退出 0，runner 改独立输出名，C1 不覆盖：

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -B tests/v3/run_torus_trim_certificate.py; exit $LASTEXITCODE
```

### Z.2 R29 关闭与 F0123 受限证书接受

**R29 CLOSED；连同已关闭 R26—R28，接受当前受限来源/派生 FIN 图模块及 F0123 C2 证书，无本批剩余阻塞。** 接受边界严格是记录的 API 定义和显式派生接合后的图，真实 implicit 分支、原生 trim/source domain、材料有效性与候选 S0 对应仍 conditional，不能将名称“certificate”解读为整件或 P6 验收。

`_require_mm` 现在要求 inventory.units=Millimeters 和 coordinate_system=absolute_part_coordinates，在读取 P1 后立即调用，并在每份 target/parent detail 的 `_load_detail` 中、任何端点/父载体计算前调用。各原 strict 检查仍执行，单位不匹配不默默换算。四类单位/框架缺失或 Inches/Meters 反例拒绝，实际 F0123 和 F0125 受影响正例均通过。[C3 日志](p3-torus-trim-c3.txt)为 **6 passed、退出 0**，不是 23 项或旧 native/spline 矩阵重跑。

准确命令由 SI 工具转录，cwd=`C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_torus_trim_certificate.py::test_actual_five_fin_source_classification_and_graph tests/v3/test_torus_trim_certificate.py::test_four_fin_source_has_all_nonzero_spans tests/v3/test_torus_trim_certificate.py::test_source_unit_and_frame_must_be_millimeters_abs 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-torus-trim-c3.txt; exit $LASTEXITCODE
```

当前 F0123 C2 及其 F0126/F0169 父来源本就为毫米，Z.1 已独立读取单位字段核实；这次 guard 不改变实际证书内容，所以未重复生成 C2，亦未覆盖 C1/C2 历史。安装 `uf_brep_types.h` 的 edge class 枚举进一步核定 OPEN=1（两个不同顶点）、NORMAL=10（有 3D 曲线）、INTERSECTION=11（由两个曲面隐式定义），与本受限 4/5-FIN、三圆边及一/两交线边支持域一致；不扩展到 closed/ring/tolerant edge。

最终结论可区分三层：同树顶点循环/方向与 API 返回表示有来源；单 span 单调投影、span 对分离和有向面积支持接合派生图在限定周期图域内的单环无孔；真实 class11 隐式交线的完整唯一支路、FIN/3D 表示误差与源面完整域仍未证明。派生内点的法向只在 UF 参数方向、有效实体假设和 source membership 条件下解释，reported solid 不替代有效性测量。历史 STEP 精度不属于当前 PRT 目标，但 API 近似请求和毫米匹配门限仍不能当原生源误差或 Hausdorff 界。

本审未执行上述命令、原生操作或重复旧数学验证。可交下一限定 P3 证明/区域关联任务，不能据本接受设置完整 trim/G 通过、执行批准或 P3 DONE。
