# P3-TAIL-READ-01 四面实读独立证据索引

2026-11-13，独立审核 `/root/p3_acceptance`；仅只读原始证据和收尾记录。**接受本次4个新面的受控采集、逐项归还、正常关闭记录及字节保全，可交机械分析。** 这是源输入采集接受，不是有限区域、完整trim、材料、参数化、0.001 mm或P3阶段验收。UF17/Conical未进行native读取。

范围与前置见[解析reader及队列审](p3-analytic-detail-review.md)。实验为[TAIL-READ01](../../../workspace/v3/p3/P3-TAIL-READ-01/read-queue.json)，C1独立runtime，新参考副本；cwd `C:/0sf/1PROJECT/AI/design/nx-sketch-mcp`，root唯一实机通道。历史PID7968、epoch `7968:639301552881734459`已退出，只供来源关联，不能复用。

## 原始证据及结果

| 序号 / 面 | 原始快照 | binding epoch | BREP根 | FIN/边出现数 | native事件 | 返回 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 F0116 | [eeda92ae…](../../../workspace/v3/p3/P3-TAIL-READ-01/native-01-F0116/detail-snapshot.json) | 1 | 201圆柱 | 5 | 80 | HUMAN_OWNED |
| 2 F0059 | [a1172acc…](../../../workspace/v3/p3/P3-TAIL-READ-01/native-02-F0059/detail-snapshot.json) | 3 | 209平面 | 6 | 89 | HUMAN_OWNED |
| 3 F0119 | [b9156e05…](../../../workspace/v3/p3/P3-TAIL-READ-01/native-03-F0119/detail-snapshot.json) | 5 | 209平面 | 6 | 89 | HUMAN_OWNED |
| 4 F0001 | [05067189…](../../../workspace/v3/p3/P3-TAIL-READ-01/native-04-F0001/detail-snapshot.json) | 7 | 209平面 | 4 | 63 | HUMAN_OWNED |

完整快照ID、原路径及逐项计数见[completion-manifest](../../../workspace/v3/p3/P3-TAIL-READ-01/completion-manifest.json)，该索引不替代原始proof。四个ID唯一。表中21条为各面树的边出现数，不能直接当21个独立物理边或跨会话Tag身份。

逐项核对`detail-summary/takeover/snapshot/status.json`、`command.json`、实际退出、stdout/stderr、DISPATCHED/CLEAN及外部dispatch/completion：计划标签、请求、快照ID、epoch、完整命令和cwd相符。每项once实际退出1，表示响应已保存且几何INCONCLUSIVE；不是失败被忽略，也不是几何通过。stdout与summary一致，stderr为空。首F0116完成后才由root显式调用2、3、4，operator每次只允许下一项，外账4 dispatch/4 completion连续，没有第五项或fallback。

每项的selector唯一MATCHED，毫米、指定独立副本和新会话一致。四次原始`inventory_before == inventory_after == inventory`直接比较相等，`inventory_diff={status:complete,changes:[]}`；无read_consistency_fault、first_change或writes_halted。四个native诊断均CLEAN_TRACE、edge_coverage_complete=true、无incomplete/overflow，topology_state_count=0；所有已保存节点geometry states为空，root及FIN/edge完整保存。

321条事件逐条核对called=true、dirty_before/dirty_after=false；229个有返回码阶段rc0，92个identifier/UF_free_states等既有void阶段为null，不把null伪记为0。每面geometry分配/释放按tag/type计数平衡，各一次topology/release；独立收证不重放这些调用。F0116边几何类为3条class10、2条class11；其余三面分别6/6/4条class10。因此机械分析须保留class11转换表示与原class10曲线的差别，不能把全部返回spline都视为原存曲线。

**归还记录顺序**：`detail-status.json`是既有runner归还前的status，其AI_OWNED、in_flight字符串`"0"`、active_operations=0、writes_halted=false与代码合同相符。`detail-summary.return=HUMAN_OWNED/status=RETURNED`只在runner收到实际nx_return响应为HUMAN_OWNED后设置，并写stdout/summary；本索引以这一受审runner证据记录归还，不把归还前status说成归还后status，也不补造独立return-response文件。后续takeover的binding依次1/3/5/7与逐项归还一致。

准确命令由每项`command.json`保留：实际隔离Python、`-B tests/v3/run_reference_detail_once.py`、PID、独立part、connection路径、该项evidence/selector路径、match_linear=.001 mm、curve/surface请求=.0001 mm及expected_session_epoch。请求精度不是实测形状上界，不输出连接凭据。

## 收尾与保全

[shutdown-processes](../../../workspace/v3/p3/P3-TAIL-READ-01/shutdown-processes.json)记录16:33:54 +08:00相关NX/Journal/helper为空；[shutdown-preservation](../../../workspace/v3/p3/P3-TAIL-READ-01/shutdown-preservation.json)记录在四项归还后按窗口Close正常退出、未请求保存、未强杀，以及16:34:23保全结果。正常关闭动作依据root受控操作记录，进程观察证明该时点无相关进程，不外推未来状态。

独立只读直接比较确认：原件、source-before、工作副本430553 bytes一致；原件mtime_ns等于复制前记录；104个live源与本实验冻结源一致；operator/connection分别等于外账冻结字节；5个runtime制品与C1一致。未使用hash，也未以mtime替代内容。**工作副本初始mtime没有记录，不声称其mtime保全。** 当前外账与anchor一致，无STOP、无OPERATOR-LOCK；保留所有原始记录，禁止重新init或重放已完成索引。

## 独立收证方式和限制

本审用隔离Python只读JSON、递归节点/事件与直接bytes核对，最终exit 0；没有运行任何NX、operator、旧测试或几何生成器。首次收证脚本错误地要求归还前status为HUMAN_OWNED，断言失败；核对既有runner及strict validator后纠正为上述真实记录顺序，再完成本次收证。该失败来自审查脚本期望，不是模型dirty、native失败或一次额外采集，未改任何原证据。

原reader及snapshot的`geometry_details_complete=false`保持。机械可消费这4个独立来源的解析carrier、原FIN/边及方向、状态和邻接；仍须建立有限域、源表示关系、材料及候选对应，不能因321条clean就把16边、四面或整件几何标为已解释。

## 共同源坐标C3增量

独立受限接受[frame-contract-c3.json](../../../workspace/v3/p3/P3-SOURCE-FRAME-01/frame-contract-c3.json)。其原五条来源与已接受C2逐记录相同，未重比旧PRT全集。新增TAIL before与共同CARRIERS before的完整430553 bytes直接比较相等；四条新增snapshot ID、summary evidence ID、inventory的Millimeters/absolute_part_coordinates及part_path与已记录独立copy逐项一致。该一次新来源核对exit 0，无hash或native调用。

C3生成时写的TAIL采集/收尾“pending”现由本索引及analytic review的实际接受补充，不为纯文义再次运行生成器或改写旧证据。可据此关联TAIL与既有当前保存PRT的共同ABS毫米帧；不授予独立坐标计量、相同UV/曲线参数、跨会话Tag身份、native材料/有效性或全形状结论。
