# P3-PHYSICAL-EDGES-READ-01 固定16面独立采集索引

2026-11-13，独立实例 `/root/validation_r68`。只读新原始证据、同树父面/几何及直接bytes保全；没有NX调用、重放、旧测试、Git或hash。**受限接受本16个新面采集、36个计划缺物理圆边的原定义取得、逐项HUMAN归还及正常关闭保全。** 这是来源采集接受，不是原边到候选的误差、完整材料或P3阶段验收。

具体计划/operator/准备见[解析reader审](p3-analytic-detail-review.md)。固定队列[read-queue](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/read-queue.json)，C1隔离runtime、新普通独立copy，root唯一通道。历史PID11548、epoch `11548:639301617236063699`已退出，不可沿用。

## 原始结果

每行原始目录均含snapshot/summary/takeover/status、command、DISPATCHED、实际退出、raw stdout/stderr及CLEAN；外账含对应dispatch/completion。完整16个snapshot/evidence ID见[completion-manifest](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/completion-manifest.json)，独立核全部互异、与各原始文件及外账相符。

| 序号 / 面 | 原始目录 | 根 | 边数 | 事件 | class10 / class11 |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 F0196 | [native-01](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-01-F0196/detail-snapshot.json) | 209 | 14 | 222 | 8 / 6 |
| 2 F0131 | [native-02](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-02-F0131/detail-snapshot.json) | 203 | 4 | 67 | 2 / 2 |
| 3 F0157 | [native-03](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-03-F0157/detail-snapshot.json) | 203 | 4 | 67 | 2 / 2 |
| 4 F0171 | [native-04](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-04-F0171/detail-snapshot.json) | 203 | 4 | 67 | 2 / 2 |
| 5 F0177 | [native-05](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-05-F0177/detail-snapshot.json) | 203 | 4 | 67 | 2 / 2 |
| 6 F0203 | [native-06](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-06-F0203/detail-snapshot.json) | 203 | 4 | 67 | 2 / 2 |
| 7 F0232 | [native-07](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-07-F0232/detail-snapshot.json) | 203 | 4 | 67 | 2 / 2 |
| 8 F0031 | [native-08](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-08-F0031/detail-snapshot.json) | 202 | 5 | 84 | 5 / 0 |
| 9 F0115 | [native-09](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-09-F0115/detail-snapshot.json) | 201 | 4 | 67 | 4 / 0 |
| 10 F0021 | [native-10](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-10-F0021/detail-snapshot.json) | 202 | 4 | 67 | 4 / 0 |
| 11 F0048 | [native-11](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-11-F0048/detail-snapshot.json) | 202 | 4 | 67 | 4 / 0 |
| 12 F0035 | [native-12](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-12-F0035/detail-snapshot.json) | 209 | 4 | 76 | 4 / 0 |
| 13 F0020 | [native-13](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-13-F0020/detail-snapshot.json) | 201 | 4 | 67 | 4 / 0 |
| 14 F0044 | [native-14](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-14-F0044/detail-snapshot.json) | 201 | 4 | 67 | 4 / 0 |
| 15 F0056 | [native-15](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-15-F0056/detail-snapshot.json) | 202 | 4 | 67 | 4 / 0 |
| 16 F0206 | [native-16](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/native-16-F0206/detail-snapshot.json) | 202 | 4 | 67 | 4 / 0 |

实际2 plane/6 sphere/5 cone/3 cylinder；root有限字段、正radius/合法half-angle及非退化axis/normal-u0均独立核对。总75个边出现数中57 class10、18 class11；共享边会重复出现，不能当75个互异物理边。class11的返回表示继续与原class10区别，不因本队列包含“物理边”就改称全部原存曲线。

1253个事件全部called=true、dirty_before/after=false：919个返回码阶段rc0，334个void阶段null。逐树无geometry states、topology_state_count=0，无incomplete/overflow，edge_coverage_complete=true、CLEAN_TRACE；按tag/type核geometry ask/free及EVAL initialize/free平衡。16项完整before/after/inventory逐对象相等、diff空，无first_change/read_consistency_fault/writes_halted。

## 36个计划缺口的实际身份与定义

独立以旧stock24缺项和六球12项为固定36个目标集合。对每次**新会话库存**中的边取两个实际incident face，再分别按UF/type、边数和完整bbox唯一映射到P1逻辑面；该36目标中每个父面对只对应一个目标物理边。按此双父面对而不是跨会话Tag相等，逐一找到全部36项，共38次原树使用。

这36项实际均为class10 circular_evaluator，包含有限arc_limits、evaluator_limits、center/radius/x_axis/y_axis、两个原顶点及其所在loop/FIN子链方向。不是依据P1 Circular预设结果。F0035的相反半圆即使共用两端点，其不同另一父面也在本次绑定中被区分；没有把任意非空端点匹配当覆盖。F0196实际两环（外2边、内12边），六口内目标与另外六class11边分别记录，外两半圆亦保留。

因此本次仅关闭“这36边原定义尚未取得”的采集缺口。有限分支到候选的数学对应、source有效定向语义、区域材料和误差组合仍需几何审查；不由双父身份或读取成功自动给数值通过。

## 串行、归还与收尾

16实际runner退出均1、raw stdout JSON等于summary、stderr空，表示已保存INCONCLUSIVE响应；operator退出0不是runner几何通过。command/dispatch/completion的argv、cwd、selector、新epoch、evidence_id一致，binding依次1、3、…、31。每项summary的HUMAN_OWNED来自受审runner实际归还响应；detail-status为归还前AI_OWNED，未伪称另有归还后status。

root显式批序[1]、[2..5]、[6..9]、[10..13]、[14..16]，operator每次仍只一index。外账恰16 dispatch/16 completion、各前项完成后才下一派发，未发现第17项、STOP、未决lock或重放；批序据root操作记录，落盘次序支持其单项顺序，不以mtime证明内容。

准确单项命令在各command.json：隔离Python `-B run_reference_detail_once.py`，cwd项目根，本次独立copy、connection和单selector；match_linear=.001 mm、curve/surface request=.0001 mm、angular matching=.0001 rad。阈值/请求不是几何目标已达到的证据。

[shutdown-processes](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/shutdown-processes.json)和[shutdown-preservation](../../../workspace/v3/p3/P3-PHYSICAL-EDGES-READ-01/shutdown-preservation.json)记录18:20:41 +08:00全部归还后窗口Close正常退出、未请求保存、未强杀，相关NX/Journal/helper为空。独立直接bytes核原件/new-before/copy仍430553 bytes相等，原件/copy双mtime与本次基线相符；104 live源与freeze、五runtime与C1、operator/connection与外账冻结相同，read-queue与INIT/anchor原始plan相等。未输出私有配置。

新before↔已接受LOWER before在本次准备已完整bytes核实；16新库存均Millimeters/absolute_part_coordinates，part路径与summary/本次copy一致，故可追加共同保存part ABS源关联，不重比旧before全集。不授予相同UV参数、跨session Tag身份、源独立计量或完整材料结论。

本次两项独立只读审计（原始调用/保全，36双父定义覆盖）均exit0；未执行operator、reader、旧validator测试或数学计算器。geometry_details_complete=false保持。新数据现可交机械正式消费，P3出口仍须各区域和统一计划真实闭合。

## 共同源帧C5增量

受限接受SI的[frame-contract-c5.json](../../../workspace/v3/p3/P3-SOURCE-FRAME-01/frame-contract-c5.json)及run_source_frame_c5.py。一次只读JSON增量审计exit0：原C4的11条source、原合同和not_conferred限制逐对象不变；恰增LOWER F0137一项及本16项，共28。17个新ID/summary/face label/mm ABS/recorded copy逐一相符，新增before关联准确引用本次已审的LOWER→CONE及PHYSICAL→LOWER记录；没有再比较旧PRT全集或运行生成器。

新增索引文件存在本身不是通用认证；本次接受以本审和LOWER索引已实际完成的原始采集/bytes核对为依据。source单位、ABS与保存part来源关联不扩大成UV统一、跨session Tag、材料或独立计量结论。
