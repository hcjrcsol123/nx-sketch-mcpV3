# P3-LOWER-STEP-READ-01 单平面独立采集索引

2026-11-13，独立实例 `/root/validation_r68`；仅读取新原始证据及直接bytes保全，没有NX调用、重放、旧测试、Git或hash。**受限接受F0137一次新采集、实际HUMAN归还及正常关闭保全，可交头部有限域分析。** 不是完整头部材料、0.001 mm或P3阶段验收。

前置及具体单项计划见[解析reader审查](p3-analytic-detail-review.md)。新隔离C1 runtime、普通参考副本、root唯一通道；历史PID2592、epoch `2592:639301595458933613`已退出，不可复用。原始输入为[detail-snapshot](../../../workspace/v3/p3/P3-LOWER-STEP-READ-01/native-01-F0137/detail-snapshot.json)，snapshot/evidence ID均为 `P3-DETAIL-5efe7a3aab3545c18b664623ef50c993`，binding=1。

## 实际结果

F0137 selector唯一MATCHED，root209为plane：point `[0,-26,0]` mm、normal `[0,1,0]`、u0 `[0,0,1]`、geometry_sense=1。实际两loops，每环两FIN/两边，四个互异原class10 circular evaluator完整返回：

| 本会话边记录 | 圆心Y / mm | 半径 / mm | 原有限角区间 |
| --- | ---: | ---: | --- |
| 63713、63849 | −26.000000000000004 | 24.08318915758 | [0, 3.141592653589793] |
| 63673、63675 | −26.000000000000004 | 16.88194301613 | [0, 3.141592653589793] |

完整axis、edge/FIN geometry/sense、子链orientation、端点和父面关联在原树中保存。63675所需原EVAL现在取得；标签数值只属本次session，不因与历史数字一致就跨会话当稳定身份。root平面Y与圆心记录Y的3.55e-15 mm差保留，不抹成严格同数；该差不是已测native tolerance。

76个事件全部called=true、dirty_before/after=false；57个返回码阶段rc0，19个void阶段null，未将null伪记0。CLEAN_TRACE、edge_coverage_complete=true、无incomplete/overflow，root/节点states空，topology_state_count=0；按tag/type核geometry ask/free及EVAL initialize/free计数平衡。完整 `inventory_before == inventory_after == inventory`、diff空，无first_change/read_consistency_fault/writes_halted。

独立逐项核command、dispatch、原始退出及stdout/stderr、summary、takeover、snapshot、status、root209-loop-circle-validation与completion；请求标签、cwd、独立copy、connection、新epoch一致。实际runner退出1，stdout JSON等于summary、stderr空，geometry=INCONCLUSIVE；外层执行成功不把它改称几何通过。

summary的RETURNED/HUMAN_OWNED是受审runner收到真实归还响应后的记录。detail-status是归还前AI_OWNED状态，与现有控制流相符；本索引不伪称另有归还后status文件。session/load/binding/revision关联正确，无第二项或STOP/重放。

准确命令见该目录command.json：隔离Python `-B run_reference_detail_once.py`，match_linear=.001 mm、curve/surface request=.0001 mm、新epoch及单selector；cwd项目根。阈值/请求值不是实测几何误差证据。

## 正常收尾和共同源帧

[shutdown-processes](../../../workspace/v3/p3/P3-LOWER-STEP-READ-01/shutdown-processes.json)及[shutdown-preservation](../../../workspace/v3/p3/P3-LOWER-STEP-READ-01/shutdown-preservation.json)记录17:44:06 +08:00在归还后用窗口Close正常退出、未请求保存、未强杀，NX/Journal/helper为空。动作依据root受控记录；进程为空只证明该观察时点。

独立直接bytes核原件、新before与copy仍430553 bytes一致，原件和copy的mtime均等于本次复制基线；104 live源与freeze、五runtime与C1、connection/plan与各自冻结副本相同。实际connection无launch段，未输出凭据。第一次准备已独立证明新before与已接受CONE before完整bytes相同，本次复用该关系，不重新比较旧源全集。

新snapshot库存单位Millimeters、absolute_part_coordinates及独立copy路径与summary/复制记录一致，因此可将此单源加入已接受的共同保存part ABS毫米关联。该结论不授予相同UV/边参数、跨session Tag身份、source有效性或完整材料占据。

本次独立收证为隔离Python `-B -`、UTF-8只读JSON、树递归和bytes比较，一次exit0；没有执行任何采集runner或旧测试。geometry_details_complete=false及source/材料限制保持。下一步只分析这份已取得的两环、四原弧和方向，不能因76 clean事件自行标完整头部或P3通过。
