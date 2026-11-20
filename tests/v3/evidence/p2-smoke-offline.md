# P2 夹具及块体判据证据索引

日期：2026-11-08，Asia/Shanghai；工作目录 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`。以下离线测试均使用假 NX/合成数据，不证明实机成功或 P2 完成。

## 首次离线控制流

- ID `P2-BLANK-FAKE-01`：`python -B -m unittest discover -s tests/v3/smoke_plan -p test_blank_fixture.py -v`；4 tests OK。覆盖空白件成功路径、已有文件拒绝、已有工作件拒绝、保存异常保留与拒绝重放。该批假对象将创建枚举与查询枚举错误地设计为同值，未发现下述实机故障。
- ID `P2-SMOKE-FAKE-01`：`python -B -m unittest discover -s tests/v3/smoke_plan -p 'test_*.py' -v`；8 tests OK（以上 4 项加 4 项块体 oracle：三态正例、同体积错误位置、宽度改变而高度未联动、单位/数量/非有限值拒绝）。

## 首次 NX2506 夹具失败与调查

- ID `P2-NX2506-BLANK-01`：root 唯一实机通道调用 `C:\0sf\ug\NXBIN\run_journal.exe`，脚本 `tests/v3/smoke_plan/create_blank_fixture.py`；环境 `P2_BLANK_RUN_DIR=C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p2\P2-NX2506-01\fixture`、`UGII_BASE_DIR=C:\0sf\ug`、`UGII_ROOT_DIR=C:\0sf\ug\UGII`。进程退出码 1；[现场结果](../../../workspace/v3/p2/P2-NX2506-01/fixture/fixture-result.json) 状态 `FAIL_OR_UNCERTAIN`，stage `verify`，报告 `units="1"`，保存文件存在，四项计数 0、dirty false、未保存项为 0。此结果不证明工作件单位。
- 发现原 Journal 把 `part.PartUnits` 与创建入参的 `NXOpen.Part.Units.Millimeters` 相比；已有 `src/nx_sketch_mcp/journal_wrapper.py:43` 与 `tools/v2/f11-create-mcp-fixture.py:289` 将 `PartUnits` 与 `NXOpen.BasePart.Units.Millimeters` 相比。错用枚举类型与该失败相符，但旧证据没有记录两个枚举的比较结果，故不能仅凭 `"1"` 确认根因或实际单位。
- 修复：读取比较改用 `NXOpen.BasePart.Units.Millimeters` 并记录原始值、预期枚举值及比较结果；假 NX 创建枚举与读取枚举改为不同类型值，新增错误单位拒绝。ID `P2-BLANK-FAKE-ENUM-RETEST-01`：同首次离线夹具命令，5 tests OK；这是离线控制流验证，不是对原始实机文件的单位判定。
- 原失败证据和已生成 PRT 保留，不重建、不覆盖。后续由 root 在隔离 GUI 中正常打开该路径，经授权接管与新鲜读取检查实际 PID/完整路径、`part_units`、空白特征/草图/实体及 dirty 前后，补充只读结果；只有实际单位为毫米且空白状态已证实，才可将原 PRT 接受为 T12 起始夹具。若字段缺失、读出不同或其他状态不确定，保持 BLOCKED，人工调查，不能把原失败改写为 PASS。

## T12 runner 定向离线验证

- ID `P2-BLOCK-CHECKS-FAKE-01`：`python -B -m unittest discover -s tests/v3/smoke_plan -p test_binding_checks.py -v`，3 tests OK。假数据验证 T09 fresh 四检查与同一读回、公式/真实消费者及几何；缺失历史、公式、消费者及不一致读回拒绝。该检验仅验证验证器本身，不代表 T09 实机能力。
- ID `P2-RUNNER-FAKE-01`：`python -B -m unittest discover -s tests/v3/smoke_plan -p test_run_block_once.py -v`，2 tests OK。伪服务器及伪 Executor 验证成功流程在重开后只做 prepare、在确认安全归还后关闭；保存 UNKNOWN 时不重试、不归还、不关闭，且输出未包含测试用的两个 ownership 值。单元桩不能证明真实桥协议兼容性、原生模型状态或实机成功，实际链及独立审查仍待执行。
- ID `P2-RUNNER-R04-RETEST-01`：独立评审指出重开 prepare 后缺少 revision/语义变化核验；补充前后语义状态必须明确为 false、准备后 revision 保持当前值，dirty 字段只记录。执行同一 runner 测试命令，3 tests OK，其中新增两个子例模拟 prepare 后语义变化或 revision 变化，均 STOP、无归还、无关闭。仍属假服务器证据。
- ID `P2-RUNNER-T10A-GRAPH-01`，代码人工标识 `P2-SMOKE-T10A-20261108-01`（不是内容摘要）：按 T10.a 已冻结接口修改重开选择，支持内部 DatumCsys 可见或不在枚举两种情况；每个可见特征必须唯一且属于当前原生支持及 Extrude 闭合图。命令 `python -B -m unittest discover -s tests/v3/smoke_plan -p test_run_block_once.py -v`，cwd 为本文开头所列项目目录，使用 `C:\Python314\python.exe`、Python 3.14.7 / MSC v.1944 64-bit AMD64；4 tests OK。含两种可见情况、祖先缺失、内部父错、额外特征、实体及 Extrude 父链错的合成用例。此结果不证明真实重开图已经匹配。
