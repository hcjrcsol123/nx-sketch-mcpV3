# P3-CONE-READ-01 两锥实读独立证据索引

2026-11-13，独立审查 `/root/validation_r68`；只读新原始记录和直接字节保全，没有NX调用、重放、旧测试、Git或hash。**受限接受首次UF17两锥采集、逐项HUMAN归还和正常关闭保全，可交机械分析。** 这是来源采集接受，不是有限域、材料、0.001 mm或P3阶段验收。

软件、计划及准备范围见[解析reader审查末节](p3-analytic-detail-review.md)。实际队列为[execution-plan](../../../workspace/v3/p3/P3-CONE-READ-01/execution-plan.json)，C1隔离runtime、普通独立参考副本，root唯一通道。历史PID3580、epoch `3580:639301573270396084`已退出，只供来源关联，禁止复用。

| 次序 / 面 | 原始detail | snapshot/evidence ID | binding | root / 边 / 事件 |
| --- | --- | --- | ---: | --- |
| 1 F0026 | [native-01](../../../workspace/v3/p3/P3-CONE-READ-01/native-01-F0026/detail-snapshot.json) | P3-DETAIL-1881da84b8404ed391d74427e6f0ce2f | 1 | 202 / 48 / 679 |
| 2 F0067 | [native-02](../../../workspace/v3/p3/P3-CONE-READ-01/native-02-F0067/detail-snapshot.json) | P3-DETAIL-17ad32c8c1a4492c9083ec3ce8422917 | 3 | 202 / 48 / 679 |

两个ID互异，逐项summary、takeover、snapshot、status、command、dispatch、actual-exit、原始stdout/stderr、root202校验和completion一致；每次只有一个selector，两次实际Python退出均为1，表示响应已记录且geometry=INCONCLUSIVE。外层wrapper退出0不是runner退出0。stdout JSON与summary相等，stderr空；不得把几何INCONCLUSIVE改写为几何通过。

两次selector唯一MATCHED，载体root202：apex `[0,-129.62433205009074,0]` mm，axis `[0,1,0]`，u0 `[0,0,1]`，半角 `1.0471975511965976` rad，有限且axis/u0非退化不共线。独立核原始字段，不把apex混成P1轴上一点。每面完整48个不同边tag在各自树中保存，class10为36条、class11为12条；共有物理边跨两树可能重复，96个边出现数不称96个独立边。class11的转换spline不得当作原存class10曲线。

每面679事件全部called=true、dirty_before/after=false；485个返回码阶段为rc0、194个void阶段为null。合计1358事件中970 rc0、388 null，null不伪记为0。逐节点无geometry states，topology_state_count=0，无incomplete/overflow，edge_coverage_complete=true、CLEAN_TRACE；按tag/type核geometry ask/free计数平衡。原件库存 `inventory_before == inventory_after == inventory`、完整diff空，无first_change/read_consistency_fault/writes_halted。

归还前status为AI_OWNED；summary的RETURNED/HUMAN_OWNED来自已审runner收到真实nx_return响应后的记录。它不是独立归还后status，不补造return-response文件。两次takeover/binding为1、3，session/load/revision关联正确。root受控操作记录及落盘顺序显示首completion后才第二dispatch，无第三项、STOP或重放；文件时间仅支持顺序观察，不作为文件内容或几何身份证明。

准确命令在各自command.json：隔离Python `-B tests/v3/run_reference_detail_once.py`，本次copy、connection-only配置、单目标selector及新epoch，cwd项目根；match_linear=0.001 mm、curve/surface request=0.0001 mm。继承strict validator使用的angular=0.0001 rad；这些仍是识别阈值/请求参数，非实际几何精度。

## 收尾、保全和源坐标

[shutdown-processes](../../../workspace/v3/p3/P3-CONE-READ-01/shutdown-processes.json)和[shutdown-preservation](../../../workspace/v3/p3/P3-CONE-READ-01/shutdown-preservation.json)记录17:06:43 +08:00两项归还后以NX窗口Close正常退出、未请求保存、未强杀，相关NX/Journal/helper为空。正常关闭动作依据root受控记录，进程观察只证明该时点。

独立只读直接bytes再次核：当前原件、新before、工作副本均430553 bytes一致；原件mtime及副本初始mtime均与本次复制记录一致；104个live运行相关源与freeze相同，五runtime与C1相同，connection和plan与各自冻结文件相同。connection实际无launch段。首次准备已独立证明新before与已接受TAIL before完整bytes一致，本次未重复旧PRT全集；两新snapshot的Millimeters、absolute_part_coordinates及独立copy路径均核对。因此可把本两锥关联到已接受共同part ABS毫米帧，不能推出UV参数一致、跨session Tag身份或独立坐标计量。

本次独立收证使用隔离Python `-B -`、UTF-8 JSON和内存递归/有理对象比对，一次exit 0，未执行任何reader/operator/validator测试或数学生成器。[completion-manifest](../../../workspace/v3/p3/P3-CONE-READ-01/completion-manifest.json)只是原始证据索引，不替代它们。geometry_details_complete=false及未证材料/trim范围保持；机械下一步可解释完整根、FIN/edge方向和24后边/两个接缝，不因clean事件或source计数直接关闭P3。

## 共同源帧C4增量

受限接受SI随后生成的[frame-contract-c4.json](../../../workspace/v3/p3/P3-SOURCE-FRAME-01/frame-contract-c4.json)及 `tests/v3/run_source_frame_c4.py`。一次只读JSON增量核对exit 0：原C3所有source记录、supported_contract、not_conferred及原trusted dependencies逐对象不变，恰新增上述两个已接受CONE snapshot/summary。两新ID、毫米/ABS、part路径与复制记录相符；new_comparison准确引用本次已审source-copy-record及430553字节来源关系。本审不再重比旧before文件或运行frame生成器。它是已有字节证据与新捕获的关联，不是仅凭一个历史true值重新认证任意变动文件；限制仍同本索引源坐标节。
