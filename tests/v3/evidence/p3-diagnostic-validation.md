# P3 T13.b 逐调用 dirty 诊断验证

## 背景与边界

此前 P3-NATIVE-02 首次 detail 读取记录 dirty false→true、两次库存不等及 UNKNOWN_FROZEN，详见 [首次实机索引](p3-native-run-index.md)。用户随后指示继续开发，root 按用户决定正常关闭该 NX、选择不保存，不调用 `nx_return`；[收尾记录](../../../workspace/v3/p3/P3-NATIVE-02/user-approved-shutdown-record.json) 记录源件及副本磁盘字节未变，退出后未观察到 NX/Journal/helper。此为受控停止，不是成功归还或内存未变的证据。旧实机首败保留。

T13.b 为诊断 dirty 首次出现位置，不宣称几何全域或设计意图已验证。v2 路径在逐调用事件记录首次 dirty/未知，之后只执行必要清理；若故障或状态不明则保留 payload 并冻结，禁止重放/自动归还。完全 clean 也只表示该次诊断链及库存对比未发现变化，不构成几何或可靠性验收。

## 首次离线测试：失败保留

人工代码标识 `P3-T13B-C1`，工作目录 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`。隔离 Python 3.14.7、pytest 9.1.1，插件自动加载及字节码关闭。以下新范围一次执行：**23 passed、15 subtests passed、2 测试失败及 4 子测试失败**，退出码 1；[原始输出](p3-t13b-c1.txt)。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/reference_geometry_cases/test_dirty_diagnostic.py tests/v3/reference_detail_bridge_cases/test_detail_adapter.py tests/v3/test_reference_detail_runner.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-t13b-c1.txt; exit $LASTEXITCODE
```

失败均为 `test_detail_adapter.py`：clean/after_dirty 应观察 `(captures,native_calls)=(2,2)`，实际 `(0,0)`；native_dirty/native_error/invalid_clean/throw 应为 `(1,1)`，实际 `(0,0)`。SI 查明模拟 `NXOpen.Tag` 值 5 为命名枚举，`ToString()` 返回 `Part` 而假 binding 是 `5`，身份门禁因此正确拒绝；尚未进入库存采集，并非真实 NX 故障。假件改为未命名数值枚举，托管生产代码未改；受影响测试复验见下，首败保留。

E1 另发现 native v2 非分配型 UF 失败可能误报 `CLEAN_TRACE`，计划补修及假件反例。上述 native 假件在 C1 通过不能覆盖后续变动，须仅针对改动及新反例复验。runner 假件在本次通过，若无相关修改不重复。旧 P1/P2、先前候选及默认协议未因新 build 重跑。

C1 产物及源副本在 `workspace/build/v3-p3-t13b-c1/`，构建日志 `workspace/build/v3-p3-t13b-c1.log`，该目录 `native-build-record.txt` 记录 native 构建及源核对，`source-copy-record.txt` 列八份源副本及直接字节核对；它们不以 hash 作标识。

## C2 两处受影响范围的定向复验

修复 adapter 假件后，E1 修改 native 代码以将 UV、matrix、edge_class 等非分配型 UF 失败标为 `NATIVE_ERROR` 并仅继续清理；相应假件新增反例。native 代码及产物人工标识 `P3-T13B-C2`，在 `workspace/build/v3-p3-t13b-c2/`；托管生产代码继承 C1。仅对两个受影响文件合批一次：**22 passed、4 subtests passed**，退出码 0；[原始输出](p3-t13b-c2-retest.txt)。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/reference_geometry_cases/test_dirty_diagnostic.py tests/v3/reference_detail_bridge_cases/test_detail_adapter.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-t13b-c2-retest.txt; exit $LASTEXITCODE
```

runner 继承 C1 通过证据。该复验为模拟故障，不证明真实 NX 读取不产生 dirty；仍需独立评审与受控实机验证。

## R06 托管桥修复后的 C3 复验

独立评审 R06 指出 adapter 已报告 dirty/fault 后，桥不能再调用原生 `RequireCurrentBinding`；SI 修改桥以保留诊断 payload 并粘性冻结，同时加强 clean 事件完整性验证。人工标识 `P3-T13B-C3`，CLR 构建在 `workspace/build/v3-p3-t13b-c3/`，native 继承 C2。仅运行受影响 adapter 测试和桥 fake 指定用例一次：**4 passed、13 subtests passed**，退出码 0，[原始输出](p3-t13b-c3-retest.txt)。测试覆盖故障后不再读取 binding、payload 保留及冻结后拒绝归还；不重跑未修改的 native 与 runner。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/reference_detail_bridge_cases/test_detail_adapter.py tests/v3/reference_detail_bridge_cases/test_detail_bridge.py::DetailBridgeTests::test_authorization_validation_dispatch_and_freeze 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-t13b-c3-retest.txt; exit $LASTEXITCODE
```

## T13.b 首次实机诊断与收尾

root 在 NX2506 已绑定的独立副本中执行一次；人工代码标识 `P3-T13B-C3`，cwd 同上，输入仍使用 P1 已存 snapshot，探索阈值均 0.001 mm。root 提供的执行命令如下，历史 PID 和会话身份不可复用，此命令不应重放：

```powershell
python -B tests/v3/run_reference_detail_once.py --pid 13564 --part 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-DIAG-01\reference-readonly.prt' --config 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-DIAG-01\isolated\mcp-config.json' --evidence-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-DIAG-01\native-01' --match-linear 0.001 --curve-tolerance 0.001 --surface-tolerance 0.001
```

[summary](../../../workspace/v3/p3/P3-DIAG-01/native-01/detail-summary.json) 为 `STOP_MANUAL_CHECK`、未尝试归还，[Python 退出码记录](../../../workspace/v3/p3/P3-DIAG-01/python-exit-record.json) 为 2。[脱敏诊断快照](../../../workspace/v3/p3/P3-DIAG-01/native-01/detail-snapshot.json) 显示 F0002 的 59 个 native 事件保持 clean；F0005 前 11 个事件保持 clean，第 12 个事件 `UF_BREP_ask_geometry` 对当次会话的 Circular 边 63602 调用返回 0 后 dirty false→true，后续仅执行两个清理事件；`inventory_after=null`、差异状态 `unavailable_after_dirty`，`read_consistency_fault=true`、`UNKNOWN_FROZEN`。该结果定位了一次观测路径，不证明根因已消除，也不证明其他面或调用无副作用。

root 依据用户继续诊断授权正常退出时选择不保存，[收尾及保全记录](../../../workspace/v3/p3/P3-DIAG-01/shutdown-preservation.json) 报告只涉及 `reference-readonly.prt`、未调用 `nx_return`、未强杀或热替换，源件及副本磁盘字节未变；root 同时报告退出后无 NX、Journal、helper。它不是成功归还的证据，也不能证明 dirty 内存未变。

## T13.c 圆边 evaluator 替代：首次离线验证

人工代码及构建标识 `P3-T13C-C1`，产物及源码快照在 `workspace/build/v3-p3-t13c-c1/`。新增路径依据当次选定面当前会话的边 tag/type 白名单，对受限圆边使用 evaluator；未知边、覆盖缺失、溢出、调用错误或 dirty 禁止作为 clean 放行。runner 接受根 detail v2 及内层 probe v3，要求完整 edge coverage、topology 对象、无 geometry overflow 和 clean trace；这些条件不证明几何等价。

按实现者确认的共享 fake/wrapper 影响，五个受影响文件合批一次：**57 passed、32 subtests passed**，退出码 0，[原始输出](p3-t13c-c1.txt)。其中 `test_wrapper_contract.py` 和 `test_dirty_diagnostic.py` 涉及此前合同，但因共享 fake/wrapper 修改而受影响；其他旧协议及候选算法未重跑。测试均为 fake 或离线状态机，不连接 NX；尚需独立评审及受控实机验证。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/reference_geometry_cases/test_circular_evaluator.py tests/v3/reference_geometry_cases/test_wrapper_contract.py tests/v3/reference_geometry_cases/test_dirty_diagnostic.py tests/v3/reference_detail_bridge_cases/test_detail_adapter.py tests/v3/test_reference_detail_runner.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-t13c-c1.txt; exit $LASTEXITCODE
```

## T13.c 一次受控实机读取

root 在 NX2506 授权独立副本上执行一次，标识 `P3-T13C-C1`、证据 ID `P3-DETAIL-3444b40a6faa4210ad64c45f344b27be`，cwd 同上。命令与上述 T13.b 实机命令相同，但 PID 为 6388、part/config/evidence 路径均为 `workspace/v3/p3/P3-CIRCLE-01/` 下对应路径；三个探索阈值仍各 0.001 mm。历史 PID 与会话身份不可复用，这不是重放指令。

[summary](../../../workspace/v3/p3/P3-CIRCLE-01/native-01/detail-summary.json) 记录 `inspection=response_recorded`、`return=HUMAN_OWNED`、`status=RETURNED`、`geometry=INCONCLUSIVE`；[Python 退出码记录](../../../workspace/v3/p3/P3-CIRCLE-01/python-exit-record.json) 为 1，符合 runner 对几何未定的约定，不代表读取发生 UNKNOWN。[详细快照](../../../workspace/v3/p3/P3-CIRCLE-01/native-01/detail-snapshot.json) 为根 detail v2 `ok=true`、无一致性故障/停写，前后库存及完整 diff 存在且 changes 为空。managed `diagnostic_events` 中的采样点为 false；native 中间事件的 dirty=null 是摘要字段，结合各 native 事件的 before/after 记录判读，不视为缺少 dirty 测量。

F0002 的 59 个 native 事件和 F0005 的 75 个 native 事件均为 `CLEAN_TRACE`；两个局部结果报告完整边覆盖、topology 对象且无 geometry/event overflow。F0005 的四个 Circular 边各经六个 EVAL 阶段，共 24 次；本次 trace 未对这些圆边使用此前导致 dirty 的 BREP 几何查询。该证据仅涵盖指定两个面与本次会话、参数和调用，不证明其他面无副作用，也不证明曲面、修剪域或整件几何已经解释。`geometry_details_complete=false`，计划仍未取得整件执行批准。

[收尾保全记录](../../../workspace/v3/p3/P3-CIRCLE-01/shutdown-preservation.json) 显示 `HUMAN_OWNED` 后正常关闭，未保存，原件和工作副本磁盘字节各与读取前基线一致、原件修改时间未变，采用直接比较而非摘要；未强杀或热替换。[进程观察](../../../workspace/v3/p3/P3-CIRCLE-01/shutdown-processes.json) 显示当时无相关活动进程。保全记录限该次磁盘状态，不能扩展为对全部模型或未来读取的保证。

## T13.d/d1/e 详细库存及曲面候选首次离线验证

共享归一化人工标识 `P3-DETAIL-INVENTORY-1.0-C1`，与新 EXTRUDE/TORUS 识别器最终冻结源码一起一次测试；工作目录、Python 3.14.7 和 pytest 9.1.1 环境同前。输入使用已有效的 P3-CIRCLE-01 clean 快照及构造反例，不启动 NX、不重读两面，也不重跑未改的旧 common 和候选。首次结果 **29 passed、24 subtests passed**，退出码 0；[原始输出](p3-detail-profiles-c1.txt)。命令：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_detail_inventory.py tests/v3/detail_extrusion_regions tests/v3/detail_torus_regions 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-detail-profiles-c1.txt; exit $LASTEXITCODE
```

该批检查已有诊断事件和来源归一化，以及受限 EXTRUDE 母线、TORUS 参数和边界候选与合成反例。两类候选保留未确认状态；不因识别或此批通过宣称完整修剪域、原生建模等价或整个样件已解释。高级独立评审及分析入口接线尚待完成。

独立评审 R08 指出 TORUS 候选缺少快照来源和 observation 身份。E1 为每条候选加入 `snapshot_id`、`coverage_role=observation` 和 `execution_approved=false`，并增加实样及合成断言；受影响的 `tests/v3/detail_torus_regions/` 单独复验 **13 passed**、退出码 0，[原始输出](p3-detail-torus-c2-retest.txt)。环境和命令与上次相同，仅 pytest 测试路径改为该目录、输出路径改为上述文件；未重跑其他模块。该结果待独立复核，不代表已确认几何。

评审 R07 对截断 trace 的疑虑需核对最终冻结版本；SI 报告相关加严及反例已在首次 29+24 测试之前完成，未发生后续改动，因此保留首测证据并交评审重新核对，不为时序交错重复运行。

### 详细库存分析入口与新报告

冻结的 detail 入口仅对新增 `tests/v3/test_analysis_detail_integration.py` 首测一次：**3 passed**、退出码 0，[原始输出](p3-detail-integration-c1.txt)。该测试检查同一 P3 快照作用域、两个候选、未决门禁和不覆盖；cwd 及环境同前，pytest 文件和输出分别替换为上述路径。已有识别器测试及 NX 读取未重跑。

使用同一 P3-CIRCLE-01 详细快照及其归还 summary，首次生成 [P3-ANALYSIS-03 报告](../../../workspace/v3/p3/P3-ANALYSIS-03/model-plan.json)，退出码 0；新目录未覆盖 01/02：

```powershell
python tests/v3/run_p3_analysis.py --snapshot workspace/v3/p3/P3-CIRCLE-01/native-01/detail-snapshot.json --detail-summary workspace/v3/p3/P3-CIRCLE-01/native-01/detail-summary.json --output workspace/v3/p3/P3-ANALYSIS-03/model-plan.json --linear 0.001 --angular 0.0001
```

输入 snapshot `P3-DETAIL-3444b40a6faa4210ad64c45f344b27be`，线性 0.001 mm 与角度 0.0001 rad 是探索匹配阈值，不是实际精度或制造公差。报告列 225 条候选/未解记录，包含一条样条挤出面和一条环面子午回转候选；235 面中 70 面有候选关联、150 面列为复杂面未解、17 面为残余、64 面有候选重叠；**0 面已确认且经几何证明解释，235 面未解释**。`execution_approved=false`，构造顺序仍未决。两条详细候选和计数增加均不代表完整修剪域、可执行整件或双版本支持已验证。

## T13.f 单球面读取准备：首次离线验证

人工构建标识 `P3-T13F-C1`，隔离产物及逐字节源码关联记录位于 `workspace/build/v3-p3-t13f-c1/`。在项目根目录采用上述 Python 3.14.7 / pytest 9.1.1 环境，以下受影响范围一次首测 **30 passed、29 subtests passed**，退出码 0；[原始输出](p3-t13f-c1.txt)。该批涵盖球面 native fake、1–2 面选择器协议/桥、单球面与同面双描述符、runner 选择文件及失败停写。`detail_common` 因选择器数量改变而修改，故只复验下列四个具体 common 节点，包括一项此前真实双面快照兼容；未泛跑旧 common、旧算法或默认 P1 回归。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/reference_geometry_cases/test_sphere_geometry.py tests/v3/test_reference_detail_selector_extension.py tests/v3/reference_detail_bridge_cases/test_detail_selector_bridge.py tests/v3/reference_detail_bridge_cases/test_detail_adapter.py::DetailAdapterTests::test_single_sphere_and_two_descriptors_for_same_face tests/v3/test_detail_inventory.py::DetailInventoryTests::test_single_detail_scope_and_mismatched_native_events tests/v3/test_detail_inventory.py::DetailInventoryTests::test_duplicate_or_unsupported_selector_is_rejected tests/v3/test_detail_inventory.py::DetailInventoryTests::test_synthetic_single_spherical_detail_preserves_scope tests/v3/test_detail_inventory.py::DetailInventoryTests::test_actual_detail_retains_session_scope_raw_geometry_and_incomplete_root tests/v3/test_reference_detail_runner.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-t13f-c1.txt; exit $LASTEXITCODE
```

测试不启动 NX，不证明球面实机读取成功或全部球面已解释；尚需独立评审及经授权的单次实机验证。runner 选择文件需包含 P1 snapshot ID 和 1–2 个无会话 Tag/JID 的描述符，并在发起请求前在该库存中验证唯一性；单球面之外的历史两面不会因此重读。

### 一次 F0023 球面实机读取

root 在 NX2506 授权独立副本上执行一次，代码 `P3-T13F-C1`，证据 ID `P3-DETAIL-3d39080929344bfb8bfad2a5a54920ee`。调用使用上述 T13.c 命令形式，将 PID 改为 15756、所有运行路径改为 `workspace/v3/p3/P3-SPHERE-01/` 对应文件，并加 `--selectors-json 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SPHERE-01\selectors.json'`；三个读取参数各 0.001 mm。此处为历史调用记录，不可复用会话身份或重放。

[summary](../../../workspace/v3/p3/P3-SPHERE-01/native-01/detail-summary.json) 记录单个 F0023 唯一匹配、`RETURNED/HUMAN_OWNED`，几何仍为 `INCONCLUSIVE`；[退出码记录](../../../workspace/v3/p3/P3-SPHERE-01/python-exit-record.json) 为 Python 1（runner 未决结果约定）。[详细快照](../../../workspace/v3/p3/P3-SPHERE-01/native-01/detail-snapshot.json) 显示 `ok=true`、无一致性故障或停写，前后库存完整且 diff 空；球面 58 条 native 事件 before/after 均 clean，3 条 Circular 边各经 6 个 EVAL 阶段共 18 次，边覆盖完整且无 geometry overflow。该结果仅针对本次球面及会话；不证明其完整裁剪面、原生参数化或其余球面已确认，`geometry_details_complete=false`。

该读取已归还，但 NX 仍打开；root 另行安排不同面的受控读取与最终收尾。收尾及源保全记录尚待提供，不提前认定退出状态。

### T13.g F0004 既有实读与重启恢复补录

本节补索引关机前已经发生的一次实读，不是新的 NX 调用或复验。依据 [独立评审 H.3](p3-independent-review.md) 的受限放行，root 在 `P3-SPHERE-01` 同一干净会话、已归还的独立副本上，以新 takeover 和 [F0004 语义选择文件](../../../workspace/v3/p3/P3-SPHERE-01/selectors-f0004.json) 首次读取新目标；证据目录为 `native-02-f0004`，绑定 epoch 3。此处的 epoch 仅标识历史观察，不可跨会话复用。[摘要](../../../workspace/v3/p3/P3-SPHERE-01/native-02-f0004/detail-summary.json) 记录单项 UF19 / SurfaceOfRevolution 选择和三个 0.001 mm 读取参数。

root 从历史工具记录提供的实际执行命令如下，仅供追溯，**不是重放指令**；历史 PID、会话身份和配置不可复用：

```powershell
python -B tests/v3/run_reference_detail_once.py --pid 15756 --part 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SPHERE-01\reference-readonly.prt' --config 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SPHERE-01\isolated\mcp-config.json' --evidence-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SPHERE-01\native-02-f0004' --match-linear 0.001 --curve-tolerance 0.001 --surface-tolerance 0.001 --selectors-json 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SPHERE-01\selectors-f0004.json'
```

随后 PowerShell 将 Python 的 `$LASTEXITCODE` 写入退出记录，值为 1；包含该记录动作的整个 shell 命令退出码为 0，不能用 shell 退出码代替 Python 的未决结果。

[详细快照](../../../workspace/v3/p3/P3-SPHERE-01/native-02-f0004/detail-snapshot.json) 显示 F0004 唯一匹配，根响应 `ok=true`、无一致性故障及停写、`first_change=null`；63 条 native 事件的 dirty before/after 全为 false，`CLEAN_TRACE`、边覆盖完整且无 event/geometry overflow。managed dirty 采样均为 false；前后库存完整、diff 为 `complete` 且 `changes=[]`，两次 native 样本相等。根几何 type 205，生成线为 type 102 样条，7 个控制点、阶次 4；这是本次原始字段观察，不能据此确认完整裁剪、参数方向、全域几何或设计意图。`geometry_details_complete=false`，两次库存一致也不证明全几何未变。

[摘要](../../../workspace/v3/p3/P3-SPHERE-01/native-02-f0004/detail-summary.json) 记录 `RETURNED/HUMAN_OWNED`、`geometry=INCONCLUSIVE`；[Python 退出记录](../../../workspace/v3/p3/P3-SPHERE-01/python-exit-f0004-record.json) 为 1，属于 runner 的几何未决结果，不是该次读取失败或 UNKNOWN。此前 F0023 球面 58 个 clean 事件、归还及其受限结论继续继承，不因重启重读。

上述球面段落中“NX 仍打开”是当时的历史状态，并非重启后的现状。用户关机中断了计划中的收尾，**没有本次 NX 正常退出、不保存的直接证据，不能补记为正常退出**。[TL 重启后核查记录](../../../workspace/v3/p3/P3-SPHERE-01/post-reboot-recovery-20261109.json) 记载原件与 `P3-SPHERE-01` 副本磁盘字节各与读取前基线一致，最后两个 reader 均已归还 `HUMAN_OWNED` 且无冻结。磁盘字节比较和 reader 归还不能替代缺失的正常退出证据，也不能推断关闭过程中的内存状态。

## T13.h/i 球面与样条回转观察首次离线验证

仅对冻结的新 `regions/detail_spheres.py`、`regions/detail_revolutions.py` 所属两个新测试目录合批首次运行，工作目录为 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`，隔离 Python 3.14.7、pytest 9.1.1，插件自动加载及字节码关闭。结果 **44 passed**，Python 退出码 0；[原始输出](p3-sphere-revolve-c1.txt)。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/detail_sphere_regions tests/v3/detail_revolution_regions 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-sphere-revolve-c1.txt; exit $LASTEXITCODE
```

测试分别消费既有 [F0023 球面快照](../../../workspace/v3/p3/P3-SPHERE-01/native-01/detail-snapshot.json)及[归还摘要](../../../workspace/v3/p3/P3-SPHERE-01/native-01/detail-summary.json)、[F0004 快照](../../../workspace/v3/p3/P3-SPHERE-01/native-02-f0004/detail-snapshot.json)及[归还摘要](../../../workspace/v3/p3/P3-SPHERE-01/native-02-f0004/detail-summary.json)，另用变换、比例及畸形数据等离线反例。球面测试设置线性与角度数值阈值各 `1e-6`；回转测试使用线性 `0.001`、角度 `0.0001`，它们是输入验证/探索阈值，不是制造精度。结果只支持未确认的局部载体观察及其限定反例，不证明完整裁剪、设计意图、全域几何或执行获准；未启动 NX，也未重复既有 reader 或旧候选测试。

### R09 回转面方向冲突定向复验

针对 R09 的 fin 与 edge 方向冲突修复，只执行新增冲突反例及既有真实载体正例两个节点一次，使用上述工作目录、Python 3.14.7、pytest 9.1.1 和相同环境。结果 **2 passed**，退出码 0，[原始输出](p3-revolve-r09-retest.txt)；原 44 项首批证据保留且不重跑。该批为离线数据测试，无 NX 读取，R09 是否关闭交独立评审确认。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/detail_revolution_regions/test_detail_revolutions.py::test_conflicting_fin_and_edge_orientation_remains_unresolved tests/v3/detail_revolution_regions/test_detail_revolutions.py::test_actual_carrier_preserves_provenance_and_open_design 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-revolve-r09-retest.txt; exit $LASTEXITCODE
```

### 球面及回转面分析入口首次接线验证

SI 冻结接线后，对新增集成文件与 helper 增加 mock 后实际受影响的原 detail 接线文件合批首次运行；工作目录、Python 3.14.7、pytest 9.1.1 及环境同上。结果 **5 passed、2 subtests passed**，退出码 0，[原始输出](p3-sphere-revolve-integration-c1.txt)。原识别器 44 项及 native reader 不重跑。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_analysis_sphere_revolve_integration.py tests/v3/test_analysis_detail_integration.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-sphere-revolve-integration-c1.txt; exit $LASTEXITCODE
```

确认两个新目录及目标均不存在后显式创建父目录，使用系统 Python 3.14.7 分别生成以下两个报告；两条命令均退出 0，标准输出和标准错误为空：

```powershell
python tests/v3/run_p3_analysis.py --snapshot workspace/v3/p3/P3-SPHERE-01/native-01/detail-snapshot.json --detail-summary workspace/v3/p3/P3-SPHERE-01/native-01/detail-summary.json --output workspace/v3/p3/P3-ANALYSIS-05/model-plan.json --linear 0.001 --angular 0.0001
python tests/v3/run_p3_analysis.py --snapshot workspace/v3/p3/P3-SPHERE-01/native-02-f0004/detail-snapshot.json --detail-summary workspace/v3/p3/P3-SPHERE-01/native-02-f0004/detail-summary.json --output workspace/v3/p3/P3-ANALYSIS-06/model-plan.json --linear 0.001 --angular 0.0001
```

[ANALYSIS-05](../../../workspace/v3/p3/P3-ANALYSIS-05/model-plan.json) 基于球面快照 `P3-DETAIL-3d39080929344bfb8bfad2a5a54920ee`，有一条 F0023 `possible_spherical_carrier`；[ANALYSIS-06](../../../workspace/v3/p3/P3-ANALYSIS-06/model-plan.json) 基于 F0004 快照 `P3-DETAIL-e1d85ede2c5341708252bc35b42d8874`，有一条 `possible_spline_revolution_surface`。两项均为对应快照内 `observation`、`confirmed=false`、`execution_approved=false`。两报告各 224 条候选/未解记录、69 面有候选关联，235 面中 0 面已解释、235 面未解释，整体 `execution_approved=false`。阈值仅用于探索，不是制造公差。

这两个调用未传 `--relation-decision`，报告无该关系意图：已有用户确认绑定的是 ANALYSIS-03 快照，不能因逻辑 ID 同名跨快照套用；[ANALYSIS-04](../../../workspace/v3/p3/P3-ANALYSIS-04/model-plan.json) 中已记录的用户确认未撤销。既有 01–04 未覆盖，这些新观察仍未证明完整几何或工程意图。

## T16.b ANALYSIS-04 首次报告调用：失败保留

SI 的首次自测记录在 [p3-t16b-selfcheck.txt](p3-t16b-selfcheck.txt)；该证据直接继承，本次未重复。TL 授权以 ANALYSIS-03 相同的 P3-CIRCLE-01 快照和归还摘要、原阈值及 [22 面共享决策](../../../docs/v3/decisions/p3-shared-22-user-decision.json)生成新报告。项目根目录、系统 Python 3.14.7，首次实际命令：

```powershell
python tests/v3/run_p3_analysis.py --snapshot workspace/v3/p3/P3-CIRCLE-01/native-01/detail-snapshot.json --detail-summary workspace/v3/p3/P3-CIRCLE-01/native-01/detail-summary.json --output workspace/v3/p3/P3-ANALYSIS-04/model-plan.json --linear 0.001 --angular 0.0001 --relation-decision docs/v3/decisions/p3-shared-22-user-decision.json
```

**失败，退出码 1，无报告产物。**工具输出的 traceback 指向 `tests/v3/run_p3_analysis.py:91` 的 `target.open("x", encoding="utf-8")`，末行 `FileNotFoundError: [Errno 2] No such file or directory`，目标为 `workspace/v3/p3/P3-ANALYSIS-04/model-plan.json`；目标父目录不存在。未观察到决策绑定失败，不据此宣称新报告的决策、覆盖或执行状态已验证。旧报告未覆盖，未改动 source 或 confirmed，未重试。

复现条件为目标父目录不存在时执行上述首次命令；已通知 TL/SI。待其确认处置并授权必要复验后，应确保目标父目录存在且输出文件仍不存在，再仅执行该报告生成一次；复验须退出码 0、产生独立报告并核对决策绑定及关联范围、coverage 和 `execution_approved`，失败仍保留原始信息，不手改结果充当通过。原首次失败记录不删除。

### ANALYSIS-04 第二次报告生成

TL 随后授权处理首次失败：确认目标目录及文件均不存在，仅创建 `workspace/v3/p3/P3-ANALYSIS-04/`，再次确认目标文件不存在，然后以本节上述完全相同的 Python 命令执行一次。**退出码 0**，生成 [ANALYSIS-04 报告](../../../workspace/v3/p3/P3-ANALYSIS-04/model-plan.json)；命令标准输出和标准错误均为空。由于 `Tee-Object` 在无输出时未创建日志，事后创建了零字节 [输出记录](p3-analysis04-attempt2.txt)以表示空输出；退出码由执行工具返回，不从空日志推断。该操作是首次报告生成失败后的定向复验，不是测试重跑。

只读核对报告与决策、ANALYSIS-03：snapshot ID、决策 ID、两个候选 ID 及 22 面集合一致，存在一条 `user_confirmed_relation_intent`、22 个成员；报告 coverage 与 ANALYSIS-03 完全相同，仍为 235 面中 0 面已解释，`execution_approved=false`。意图中 `geometry_proven=false`、`native_propagation_verified=false`、`execution_approved=false`；用户确认的是关系意图，不能据此宣布几何、编辑传播或整件可执行已验证。保留上方首次失败，旧报告未覆盖，决策和候选未手改。

## T13.k 独立齿侧样条和毛坯规划合同首次验证

后续 T13.l 三个新毛坯载体的受控实读及正常收尾，见[区域实读索引](p3-regional-read-index.md)的 T13.l 节；该证据不代表 stock 截面已闭合。

SI 冻结的实际模块为 `src/nx_sketch_mcp/v3/section_candidates.py`。只对 `tests/v3/test_section_candidates.py` 首次运行一次，项目根目录，隔离 Python 3.14.7、pytest 9.1.1，插件自动加载与字节码关闭。结果 **2 passed、7 subtests passed**，退出码 0；[原始输出](p3-section-contract-c1.txt)。输入为 [用户原始决定](../../../docs/v3/decisions/p3-independent-flanks-user-decision.json)、两次已归还的 F0002/F0024 源快照与摘要及既有毛坯工作分解；包含混合来源、错误 basis、UV 当全域等负例。未重跑原算法测试或原生读取。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_section_candidates.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-section-contract-c1.txt; exit $LASTEXITCODE
```

首次测试通过后，确认 `workspace/v3/p3/P3-SECTION-01/` 不存在并创建，确认输出目标不存在；用系统 Python 3.14.7 调用模块实际 API 一次、标准 JSON `allow_nan=False` 且文件独占创建，退出码 0，生成 [section-candidate.json](../../../workspace/v3/p3/P3-SECTION-01/section-candidate.json)。项目根目录执行命令如下：

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -c "import json; from pathlib import Path; from nx_sketch_mcp.v3.section_candidates import load_section_candidate; root=Path.cwd(); result=load_section_candidate(root/'docs/v3/decisions/p3-independent-flanks-user-decision.json', repository_root=root); data=json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False); (root/'workspace/v3/p3/P3-SECTION-01/section-candidate.json').open('x', encoding='utf-8').write(data + '\n')"
```

只读核对输出为 `p3-section-candidate/0.1`、`planning_only`；F0002 和 F0024 保留各自快照、不同原始节点矢量和原始阶数，`actual_generator_trim` 未验证、面 UV 到母线参数的映射未验证，`driving_parameters=[]`。六个带类型的齿侧、局部闭环、毛坯截面/回转及局部修饰节点均为 `blocked`，要求仍 open；毛坯 20 段为暂定候选，F0169/F0167/F0066 载体、截面闭合和材料角色仍待核。用户确认是表达意图，`geometry_proven=false`、`edit_domains_confirmed=false`、`execution_approved=false`；这不是已经实现参数驱动、可执行建模或完整几何验证。

## T13.m 样条区间限制数学合同首次验证

冻结的 `src/nx_sketch_mcp/v3/spline_restrict.py` 首次只运行新文件 `tests/v3/test_spline_restrict.py`；项目根目录、隔离 Python 3.14.7、pytest 9.1.1，插件自动加载及字节码关闭。结果 **25 passed**、退出码 0，[原始输出](p3-spline-restrict-c1.txt)。命令：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_spline_restrict.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-spline-restrict-c1.txt; exit $LASTEXITCODE
```

测试针对给定非有理 B 样条表达式和显式区间，检查有理数精确依赖系数、分段多项式恒等、端点、保留微小非零依赖、派生控制点与原控制点的关系及输出浮点舍入上界，并拒绝越域、非有限或不支持的输入。真实齿侧数学输入来自 [F0002](../../../workspace/v3/p3/P3-CIRCLE-01/native-01/detail-snapshot.json) 与 [F0024](../../../workspace/v3/p3/P3-REGIONS-01/native-01-F0024/detail-snapshot.json) 各自的三维、7 控制点、4 阶母线，区间 a/b 由现有工作分解中的观察显式提供；未因此证实该区间为真实裁剪域，也未从 UV 推导区间。其他 FIN 案例只作为给定曲线的数学输入，不能将其坐标舍入界当作毫米几何误差。

给定表达式闭区间上的浮点舍入界不覆盖源数据、坐标框架、原生内核近似、真实裁剪或未来编辑误差，不是模型全域精度证明。未运行旧算法测试或 NX，新数学及合同等待独立评审；该首测不批准执行或证明参数编辑成立。

## T13.n 毛坯母线规划合同首次验证

SI 冻结 `stock_profile.py` 后，仅对 `tests/v3/test_stock_profile.py` 首次运行；项目根目录、隔离 Python 3.14.7 / pytest 9.1.1，插件自动加载及字节码关闭。结果 **6 passed、17 subtests passed**，退出码 0；[原始输出](p3-stock-profile-c1.txt)。这批离线验证给定候选母线的受限 C0、简单闭环和构造角度合同与拒绝反例，不重复原生读取或旧算法测试。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_stock_profile.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-stock-profile-c1.txt; exit $LASTEXITCODE
```

首测通过并确认目标不存在后，在项目根目录用系统 Python 3.14.7 一次生成 [meridian-plan.json](../../../workspace/v3/p3/P3-STOCK-01/meridian-plan.json)，退出码 0、无标准输出/标准错误：

```powershell
python -B tests/v3/run_stock_profile.py --proposal workspace/v3/p3/P3-STOCK-01/meridian-proposal.json --output workspace/v3/p3/P3-STOCK-01/meridian-plan.json
```

该 `planning_only` 方案记录 22 段（含轴线及底部封口），`closed_by_shared_vertices=true`、`simple_by_monotone_chain=true`，限给定母线及计算假设；回转角 2π 是 TL 构造假设，回转节点仍 `blocked`。用户线性 0.001 mm 目标标为 `not_evaluated`，匹配阈值不能替代该目标的几何比较；`source_geometry_proven=false`、`whole_stock_envelope_proven=false`、`execution_approved=false`。这不是参考包络、原生实建或几何误差达标的证明。

产物 `assumptions` 的最后一条仍称 F0169/F0167/F0066 载体未直接读，与 [T13.l 实读索引](p3-regional-read-index.md)记录的三次读取不一致；这是当前源假设文本与实读历史的表述差异，已通知 SI/评审核查其对绑定和结论的影响，未手改方案或数字。独立评审及必要处理待完成。

### T13.n C2：R10—R12 定向复验与新规划

针对 [独立评审 R10—R12](p3-independent-review.md) 的修复，在项目根目录使用隔离 Python 3.14.7、pytest 9.1.1，关闭插件自动加载和字节码，仅运行两个接缝新反例及正例、单位门禁新反例及正例、受该合同影响的实际来源和合成圆弧两个旧用例一次。**5 passed、3 subtests passed，退出码 0**；[原始输出](p3-stock-profile-c2-retest.txt)。未重跑其余 C1 测试或原生读取。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_stock_profile.py::StockProfileTests::test_actual_sources_closed_candidate_arc_extremum_and_gates tests/v3/test_stock_profile.py::StockProfileTests::test_generic_four_segment_and_arc_profile tests/v3/test_stock_profile.py::StockProfileTests::test_bottom_same_y_overlap_rejected_and_outward_allowed tests/v3/test_stock_profile.py::StockProfileTests::test_top_same_y_overlap_rejected_and_inward_allowed tests/v3/test_stock_profile.py::StockProfileTests::test_torus_detail_requires_explicit_mm 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-stock-profile-c2-retest.txt; exit $LASTEXITCODE
```

目标不存在检查后，使用同一隔离 Python 首次独占生成 [meridian-plan-c2.json](../../../workspace/v3/p3/P3-STOCK-01/meridian-plan-c2.json)，退出码 0，标准输出和标准错误为空；退出码来自执行工具，不从空输出推断：

```powershell
& 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -B tests/v3/run_stock_profile.py --proposal workspace/v3/p3/P3-STOCK-01/meridian-proposal-c2.json --output workspace/v3/p3/P3-STOCK-01/meridian-plan-c2.json
```

只读核对新报告为 `planning_only`、22 段含 4 圆弧，三处说明与 assumptions 区分历史推断、T13.l 已读 F0169/F0167/F0066 载体及未验证的 frame、修剪和对侧面；来源记录指向各自已有读取。`source_geometry_proven=false`、`whole_stock_envelope_proven=false`、`execution_approved=false`，回转仍 `blocked`，0.001 mm 目标仍 `not_evaluated`。旧 proposal、首次规划和证据保留；本项不证明真实包络、几何误差或可执行建模，R10—R12 是否关闭由独立评审判定。

## T13.o 会话 epoch 定向离线验证

对冻结的 Python 协议、严格接管桥及 once runner 变更，只运行两个新测试文件和 runner 的 3 个新 epoch 用例及 1 个旧兼容用例一次；项目根目录、隔离 Python 3.14.7 / pytest 9.1.1、禁用插件自动加载和字节码。**10 passed、27 subtests passed，退出码 0**；[原始输出](p3-session-epoch-c1.txt)。测试包括无效/失配 epoch 拒绝、旧后端不回退、UNKNOWN 门禁、合法及旧式接管、runner 停止路径；C# 测试启动隔离 fake host/helper 并编译临时 harness，没有启动或连接 NX。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_session_epoch_protocol.py tests/v3/test_session_epoch_bridge.py tests/v3/test_reference_detail_runner.py::DetailRunnerTests::test_matched_response_is_recorded_but_geometry_remains_inconclusive tests/v3/test_reference_detail_runner.py::DetailRunnerTests::test_expected_session_is_sent_and_checked_before_inspection tests/v3/test_reference_detail_runner.py::DetailRunnerTests::test_expected_session_mismatch_or_rejection_stops_without_fallback tests/v3/test_reference_detail_runner.py::DetailRunnerTests::test_expected_session_invalid_is_rejected_before_calls 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-session-epoch-c1.txt; exit $LASTEXITCODE
```

桥 fake 使用既有 `workspace/build/v3-p3-t13o-c1` 托管产物与旧后端 `v3-p3-t13f-c1`；当前 C1 构建与完整冻结源码的对应尚无可追溯源码快照，结果仅表明实际被测二进制及当前 Python/mock 的上述离线行为，不证明新的 C2 构建产物或真实 NX 组合已验证。原生辅助库及可追溯制品链由 SI 另行完成；本结果不放行实机，不替代 UNKNOWN 时人工核查，也不扩展旧原生证据。

### T13.o C2 制品单用例首次行为验证

SI 的 [C2 构建核对](../../../workspace/build/v3-p3-t13o-c2/build-verification.json)记录四次托管编译使用冻结源码副本并于构建后与工作区逐字节核对；原生 DLL 继承已接受的 T13.f 制品，未重编。该记录本身不证明行为。对 `workspace/build/v3-p3-t13o-c2` 的新托管制品，按 TL 授权以原测试模块动态加载、仅在进程内将 `NEW` 指向 C2，运行 `NewSessionEpochBridgeTests.test_missing_stale_and_valid_epoch_and_legacy` 一次：**1 test OK，退出码 0**；[原始输出](p3-session-epoch-c2-artifact.txt)。未修改测试默认 C1 路径、未覆盖 C1 输出，未重跑 Python 协议、runner 或旧后端用例。

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -B -c "import importlib.util, pathlib, sys, unittest; root=pathlib.Path.cwd(); spec=importlib.util.spec_from_file_location('p3_session_epoch_c2', root/'tests/v3/test_session_epoch_bridge.py'); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); module.NEW=root/'workspace/build/v3-p3-t13o-c2'; suite=unittest.TestSuite([module.NewSessionEpochBridgeTests('test_missing_stale_and_valid_epoch_and_legacy')]); result=unittest.TextTestRunner(verbosity=2).run(suite); sys.exit(not result.wasSuccessful())" 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-session-epoch-c2-artifact.txt; exit $LASTEXITCODE
```

该一个用例依次断言新接口缺失、格式无效、过期 epoch 及旧接口带新字段的四项拒绝；各拒绝后 ownership 仍为 HUMAN_OWNED、binding epoch 不变、adapter 接管次数为零。之后检查有效严格接管/归还以及旧式接管/归还。`unittest` 原始输出报告一个用例，不单独报告子项数量；以上是用例所含断言而非另行计数的测试结果。仅使用隔离 fake host/helper、临时编译的 harness，未启动 NX、未调用原生辅助 DLL；结果仅对该 C2 制品的假件合同成立，不能证明真实 NX 环境、完整读取或授权新的实机操作，仍待独立评审。

## T13.p Swept 受控队列首次离线验证

经 SI 确认源码及测试冻结、全部 queue 调度调用注入 fake，TL 授权只运行新文件 `tests/v3/test_swept_queue.py` 一次。项目根目录、隔离 Python 3.14.7 / pytest 9.1.1，禁用插件自动加载及字节码。结果 **12 passed、1 skipped、15 subtests passed，退出码 0**；[原始输出](p3-swept-queue-c1.txt)。源码中唯一跳过分支为环境不支持创建目录符号链接，故该测试未验证符号链接逃逸拒绝；不能将其计为通过。未重复旧协议、reader 或其他既有测试。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_swept_queue.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-swept-queue-c1.txt; exit $LASTEXITCODE
```

测试检查 P1 清单中 42 个待选面与 F0002/F0024 排除、默认一项及显式四项的顺序和上限、session epoch、STOP/锁/中断后未完成 dispatch 拒绝重放，以及输入路径和硬链接等拒绝。假调度在调用时检查已存在 `DISPATCHED.json`；测试不证明掉电时磁盘持久性。一个保存的单面证据切片被复制并调整为临时 fixture，严格校验器检查接受及损坏反例；它不是新的实机读取或对 42 面的实际验证。其余队列故障模式以注入的假校验失败验证停队行为，不代表每一种真实故障均被真实证据校验器分别检测。未执行真实 once、队列准备或 NX，42 面几何支持仍未证明；待独立评审。

## T16.a 圆周角位置关系首次离线测试

与 T13.b 分开运行，`P3-T16A-C1`；相同 cwd、Python 与 pytest 环境，实际命令如下，**14 passed**，退出码 0，[原始输出](p3-t16a-c1.txt)。输入为既有 P1 快照和合成反例，覆盖候选圆周关系和参数联动，未启动 NX；候选关系仍未确认，不可当作完整特征或可执行模型。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/circular_relation_regions 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-t16a-c1.txt; exit $LASTEXITCODE
```

### T16.a 入口接线与新报告

`P3-T16A-INTEGRATION-C1` 将圆周关系加入分析入口。仅新接线测试 `tests/v3/test_analysis_circular_integration.py` 运行一次：**1 passed**、退出码 0，[原始输出](p3-t16a-integration-c1.txt)。命令与上方相同，仅 pytest 测试路径及输出文件名替换为该文件和 `tests/v3/evidence/p3-t16a-integration-c1.txt`；14 项已通过识别器测试未重复。

同一 P1 snapshot 和阈值在独立新目录首次生成 [P3-ANALYSIS-02 计划](../../../workspace/v3/p3/P3-ANALYSIS-02/model-plan.json)，退出码 0，命令如下；未覆盖 P3-ANALYSIS-01：

```powershell
python tests/v3/run_p3_analysis.py --snapshot workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json --output workspace/v3/p3/P3-ANALYSIS-02/model-plan.json --linear 0.001 --angular 0.0001
```

新增 1 条 `possible_circular_axis_spacing` 未确认候选，报告总计 223 条候选/未解记录；235 面中 68 有候选关联、150 列为复杂面未解、17 为残余，候选重叠面 64。**已确认且经几何证明解释的面仍为 0，全部 235 面未解释**；`execution_approved=false`、构造顺序未决。阈值仅探索性匹配，不是参考精度/制造公差；候选重叠或数量增加不代表实际区域已闭合。

## T13.p 跨会话恢复队列首次定向离线验证

SI 冻结 `tests/v3/run_swept_queue.py` 与 `tests/v3/test_swept_queue.py` 后，经 TL 授权在项目根目录运行恢复新增测试及直接受影响的旧队列控制流用例一次；隔离 Python 3.14.7、pytest 9.1.1，关闭插件自动加载及字节码。**11 passed、15 subtests passed，退出码 0**；[原始输出](p3-swept-resume-c1.txt)。命令：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_swept_queue.py::InheritedQueueTests tests/v3/test_swept_queue.py::ActualPausedEvidenceTests::test_saved_nine_revalidated_and_next_plan tests/v3/test_swept_queue.py::QueueTests::test_default_one_explicit_four_and_contiguous_order tests/v3/test_swept_queue.py::QueueTests::test_epoch_required_and_different_session_stops tests/v3/test_swept_queue.py::QueueTests::test_external_stop_between_items tests/v3/test_swept_queue.py::QueueTests::test_crash_dispatch_is_never_replayed_or_lock_cleared tests/v3/test_swept_queue.py::QueueTests::test_preexisting_output_and_noncontiguous_output_stop 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-swept-resume-c1.txt; exit $LASTEXITCODE
```

新增 5 个合成用例在临时目录采用 fake 校验器及 fake 派发，检查 9→33、F0077 起按序、不同 epoch、旧 STOP/context 不变，以及证据变更或缺失、暂停/保全记录异常、重复/未完成及非连续 dispatch 等拒绝。新增 1 个用例只读调用真实校验器检查已保存 9 项，构建临时新上下文并以 fake 派发 F0077；验证了旧 STOP/context 字节不变。另运行 5 个直接受 `init`、`run_batch` 和 prior-prefix 检查改动影响的旧用例；其余 C1 证据继承。C1 中目录符号链接用例曾因环境不支持而跳过，仍不能记为通过。

测试未启动 NX 或真实 once runner，未在实际目录初始化新队列，未删除旧 STOP 或修改旧 context。合成故障仅证明受测假件和控制流，不能证明每种实际外部故障均被检测；旧 9 项仍是 INCONCLUSIVE 只读观察，非完整几何或 0.001 mm 精度验证。新实机会话和派发需由 TL 按唯一通道及独立评审结论另行控制。

### T13.p C2：R13 暂停清单及完整尾项丢失定向复验

针对独立评审 R13，SI 增加暂停清单与前驱计划、连续已完成项和原始证据的交叉校验；并按审查意见补强尾项整目录缺失后的首次初始化反例。代码冻结后，经 TL 授权在同一项目目录及隔离 Python/pytest 环境，仅运行新增两项、受影响单段和多段正例及实际旧证据只读正例一次：**5 passed、7 subtests passed，退出码 0**；[原始输出](p3-swept-resume-c2-retest.txt)。C1 原始证据保留，其余旧矩阵未重复。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_swept_queue.py::InheritedQueueTests::test_missing_entire_completed_tail_never_replayed tests/v3/test_swept_queue.py::InheritedQueueTests::test_manifest_and_original_proof_cross_checks tests/v3/test_swept_queue.py::InheritedQueueTests::test_remaining_33_and_new_epoch_bounded_dispatch tests/v3/test_swept_queue.py::InheritedQueueTests::test_multiple_segments_reject_reused_epoch_and_preserve_order tests/v3/test_swept_queue.py::ActualPausedEvidenceTests::test_saved_nine_revalidated_and_next_plan 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-swept-resume-c2-retest.txt; exit $LASTEXITCODE
```

合成反例在临时目录移走整段已完成尾项后，断言首次初始化拒绝且不产生 plan/context，同时已有新 run 拒绝且无派发；另检查清单缺失、数量/重复、来源、epoch、证据路径及剩余项污染等。合成测试采用 fake 证据校验器和假派发，只证明所测结构及控制流。实际旧 9 项通过真实校验器只读核验，临时新上下文的 F0077 派发仍为 fake；旧 STOP/context 字节不变。没有启动 NX 或在实际目录初始化队列。R13 的关闭与适配接受取决于独立评审及 TL，旧数据仍为 INCONCLUSIVE，不证明完整几何。

### T13.p P3-SWEPT-02：33 项续读及正常收尾

root 实际完成 9 次显式批次（首批 1，之后各 4），新 33 项逐项保留原始证据，批次退出码均 0。TV 只读核对全量剩余顺序、33 个严格 validator 结果和连续 CLEAN、59 native events/项、完整空库存 diff、RETURNED/HUMAN_OWNED；source、before、工作副本字节相同，36 个列明源码与冻结副本相同，正常退出及进程记录一致。每项 ID/路径、实际命令及其工具转录依据、收尾记录与适用限制详见[完整索引](p3-swept-complete-index.md)和[逐项清单](../../../workspace/v3/p3/P3-SWEPT-02/completion-manifest.json)。前 11 项直接引用已有证据，未重读；本次未重复 NX 测试或旧矩阵。

所有结果是受限读取证据，几何仍 INCONCLUSIVE；44 个观察不证明完整几何、工程意图或 0.001 mm 全域误差。独立评审及 TL 接收待记录。

### P3-REGIONS-02：F0022/F0041 两项 C2 原生读取

首次 F0022 selector envelope 在 McpServer 创建前由 argparse 拒绝，exit 2，原 STOP、错误输入及错误证据保留；独立 T.1 受限接受正确 envelope 的 C2 替代。随后 root 在同一受控会话各实读 F0022/F0041 一次，exit 1 是 recorded response/INCONCLUSIVE 约定。两项 CLEAN_TRACE，分别 63/119 native events，完整空库存 diff、RETURNED/HUMAN_OWNED；root 当期严格 validator 核验。TV 只读核对原始结果及收尾，原件/before/工作副本字节相同、原件 mtime 未变，36 个源码与冻结副本字节一致。准确命令、失败及工具转录依据、原始文件与限制见 [P3-REGIONS-02 索引](p3-regions02-index.md)。没有重读旧证据或再次运行 NX。

这些是两个限定区域的采集结果，几何仍 INCONCLUSIVE，不能推及其他区域、完整修剪或 0.001 mm 全域目标；新增证据待独立评审及 TL 接收。

### P3-SHOULDERS-01：42 项新肩部实读

root 在独立会话经一次 init 和各索引一次 operator CLI 取得 42 项新响应；外层调用均 exit 0，内部 once 均 exit 1/INCONCLUSIVE。TV 只读核对 42 项计划、台账、原命令和证据对应，各 63 native events、root 205/generator 102、完整空 diff、RETURNED/HUMAN_OWNED，42 dispatch/42 completion；原 F0004/F0022 直接继承。原件/before/副本、36 项源码、operator 与连接配置的冻结副本直接字节比较一致，原件 mtime 未变；正常退出及正确 `OPERATOR-LOCK.json` 保全记录一致。

审计初次错误地要求所有事件 `uf_rc == 0`，因 void `UF_BREP_ask_identifier` 的 null 而失败；对照既有事件合同后只读核对为 756 void/null、1890 非void/0，全部 called 且 dirty 前后 false，非新增原生失败。准确执行依据、逐项路径、保全与限制见 [肩部实读索引](p3-shoulders-read-index.md)。未重读旧 proof、运行 NX 或重跑旧测试；此有限实读不证明完整几何或全域误差，新增证据待独立评审及 TL 接收。

### P3-CARRIERS-01：44 项新载体实读

root 通过一次 init 和各索引一次 operator CLI 取得 44 项新响应，外层均 exit 0，内部 once 均 exit 1/INCONCLUSIVE。TV 只读对照 44 项计划、外置台账、原始命令及 proof，均 root 204、CLEAN_TRACE、完整空 diff、RETURNED/HUMAN_OWNED；F0126 为 48 边/687 native events，既定预算未增加。事件总计 4140，3028 非void/0、1112 void/null，均 called 且 dirty 前后 false；void/null 按既有合同解释。原件/before/副本、36 项源码、operator 与配置各自冻结副本直接字节相同，原件 mtime 未变；正确 `OPERATOR-LOCK.json` 与正常退出记录一致。

逐项 ID、事件数、原始命令路径、实际执行转录依据及保全限制详见 [载体实读索引](p3-carriers-read-index.md)。既有 97 项未复审或重读，9 球面未派发；未再次运行 NX 或旧测试。该受限实读不证明完整几何、工程意图或全域误差，新增证据待独立评审及 TL 接收。
