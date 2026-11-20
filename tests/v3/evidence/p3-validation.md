# P3 离线验证证据索引

## 范围与结论

- 人工代码标识 `P3-ANALYSIS-C1`；不是文件或模型摘要。配置为本次工作区 P3 新增的库存归一化、T13—T17 分区及关系识别、T19 计划门禁、对应测试和 `tests/v3/run_p3_analysis.py`。本索引不证明其后修改仍适用。
- 2026-11-08，工作目录 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`。离线统一测试 **49 passed，30 subtests passed**，退出码 0；结果仅证明这次指定测试通过，不证明样件全形状、原生构造、可编辑性或版本兼容性。
- 输入为 P1 正式唯一实机读取 [snapshot](../../../workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json)，标识 `P1-REFERENCE-7812d302a165453badcd339473b5dba3`；库存 235 面、622 边，完整修剪曲面和边曲线未采集，标识只在原会话和 revision 范围内有效。P1 参考读取与源文件保全见 [P1 实机索引](p1-native-run-index.md)，P2 双版本块体贯通见 [P2 索引](p2-smoke-native-index.md)。未因换阶段重跑这些未受影响证据；它们不证明实际样件分区或全形状。
- P3 首次实际库存计划仍不完整：**0/235 面有确认且有几何证明的解释，所有 235 面未解释；执行未获批准，构造顺序未定**。按 P3 完整出口仍缺确认和几何证据，应维持 BLOCKED，等待补读与真实确认，不将测试通过或候选数视作整件完成。

## 一次统一离线测试

系统 `python` 为 3.14.7，检查 `python -m pytest --version` 返回无 pytest；这只是环境检查，未执行用例。采用已有工作区隔离环境 `C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe`，Python 3.14.7、pytest 9.1.1；未安装依赖。禁用插件自动加载并禁写字节码。实际命令（PowerShell，cwd 如上）：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_region_inventory.py tests/v3/profile_regions tests/v3/addition_regions tests/v3/cut_regions tests/v3/relation_regions tests/v3/transition_regions tests/v3/test_model_plan.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-analysis-c1.txt; exit $LASTEXITCODE
```

原始输出：[p3-analysis-c1.txt](p3-analysis-c1.txt)。测试使用真实 P1 快照及构造反例，覆盖输入状态和拓扑完整性、局部分区候选、关系求值、未确认或未知几何与计划门禁；细项以指定测试文件为准。无本次测试失败或需复验项。若后续修改，记录影响和原因，只复验受影响测试，并保留首次输出。

### R01/R02 修复后的定向复验

独立评审发现候选结构/来源和依赖资格、能力关闭记录的门禁问题（详见独立评审记录）；受影响的 T19 `model_plan` 及对应测试完成修复，人工标识 `P3-MODEL-PLAN-C2`。仅运行受影响文件一次，环境与 cwd 同上，**12 passed，13 subtests passed**，退出码 0；[原始输出](p3-model-plan-c2-retest.txt)。命令：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_model_plan.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-model-plan-c2-retest.txt; exit $LASTEXITCODE
```

未重跑未受影响分区测试及真实库存 CLI；后者仍是 C1 历史结果，不能作为 C2 已重新生成的报告。

### T13.a 新增接口和受影响旧协议首次离线测试

`P3-DETAIL-C1`，环境及 cwd 同上。一次执行以下命令，**15 passed、30 subtests passed、2 failed**，退出码 1；首败原始证据：[p3-detail-c1.txt](p3-detail-c1.txt)。两项失败均为 `reference_geometry_cases/test_wrapper_contract.py` 调用 `vcvars64.bat` 的 cmd.exe 引号处理，编译器未启动，因而这两项未取得 native helper 行为证据。复现见下列原始测试命令与对应测试；E1 修复该测试启动方式后仅复验受影响文件，要求两项均通过，且保留首败。其余已通过范围不重复。

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/test_reference_detail_protocol.py tests/v3/reference_detail_bridge_cases tests/v3/reference_geometry_cases tests/v3/test_reference_detail_runner.py tests/v3/test_reference_protocol.py tests/v3/test_reference_unknown_gate.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-detail-c1.txt; exit $LASTEXITCODE
```

该批覆盖新 detail 请求校验、bridge 假件、独立副本 runner 假件和因共享入口改变而受影响的旧协议/UNKNOWN 门禁；不连接实机。native 测试构建的是临时 fake 库，不是 NX 几何验证。本批不构成实机前全部放行证据，仍需独立评审和失败项复验。

E1 修复测试的命令启动方式，改为生成临时 cmd 脚本，未修改 native 源码；`P3-DETAIL-NATIVE-C2` 仅复验此前失败文件一次，**2 passed**，退出码 0。[原始复验输出](p3-detail-native-c2-retest.txt)。首次失败发生在 vcvars 启动阶段，不能归因为原生 API 失败。命令及环境：

```powershell
$env:PYTHONPATH='src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe' -m pytest -q tests/v3/reference_geometry_cases/test_wrapper_contract.py 2>&1 | Tee-Object -FilePath tests/v3/evidence/p3-detail-native-c2-retest.txt; exit $LASTEXITCODE
```

此后发现 native 释放调用非零必须传播为异常并粘停；E1 修改 native 源和假件，加入 geometry_free/topology_release 失败注入及其余资源继续释放的断言。native 代码人工标识 `P3-DETAIL-NATIVE-C2`；运行标识 `P3-DETAIL-NATIVE-TEST-C3`，与上方仅改测试启动方式的 C2 复验区分。仅对同一受影响文件再次运行：**2 passed**，退出码 0，[原始结果](p3-detail-native-c3-retest.txt)。环境和命令与上方相同，仅 `Tee-Object` 输出名替换为 `tests/v3/evidence/p3-detail-native-c3-retest.txt`。此为假件故障注入，不等同于 NX 原生实机故障验证。

独立评审 R04 进一步发现分配型 UF 查询失败或无效成功输出必须失败并尽力清理。E1 修改 native 源及假件（native 源 `P3-DETAIL-NATIVE-C3`），加入拓扑/几何查询失败、空拓扑与 `GEOM_ALL` 无效输出、资源释放计数等反例。运行标识 `P3-DETAIL-NATIVE-TEST-C4`，仅复验上述受影响文件一次：**2 passed**，退出码 0，[原始结果](p3-detail-native-c4-retest.txt)。命令与上方相同，仅 `Tee-Object` 输出名改为 `tests/v3/evidence/p3-detail-native-c4-retest.txt`。假件测试本身不证明真实 NX 行为；实机前仍需独立复核。

## 首次实际库存分析

独立新目录 `workspace/v3/p3/P3-ANALYSIS-01/` 预先创建且不存在覆盖；CLI 使用系统 Python 3.14.7，实际命令如下，退出码 0、无标准输出：

```powershell
python tests/v3/run_p3_analysis.py --snapshot workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json --output workspace/v3/p3/P3-ANALYSIS-01/model-plan.json --linear 0.001 --angular 0.0001
```

[原始计划与复现字段](../../../workspace/v3/p3/P3-ANALYSIS-01/model-plan.json)：单位 mm，匹配阈值线性 0.001 mm、角度 0.0001 rad，仅为探索性假设，不是参考精度或制造公差。输出 222 条候选/未解记录：150 条复杂曲面未解，34 条同轴柱锥链、34 条锥形过渡、2 条增料、1 条减料及 1 条等半径关系候选。68 面有关联候选、150 面列为复杂面未解、17 面为残余，42 面存在候选重叠；这些分类不能当成已解释面数，也不证明其几何互斥。`explained_faces=0`、`unexplained_face_ids` 共 235、`execution_approved=false`，构造操作顺序未决。`findings` 的重复记录反映逐候选/逐能力门禁，不是独立缺陷数。

后续必要证据包括：原生修剪边界/曲面定义及定位，区分真实增减料和过渡，记录关系及参数意图的可追溯人工确认，解决全部残余和重叠并给每区域几何解释；开放能力需在对应阶段关闭。若补读或分析出错，应保留首次尝试、精确输入和失败现象，只对受影响项修复复验；不可从本次离线通过推定后续 NX 实测结果。
