# P3 T13.j 区域细节实读索引

## 范围与配置

[P3-REGIONS-01 读取队列](../../../workspace/v3/p3/P3-REGIONS-01/read-queue.json) 限定独立测试副本上的四个新目标，依次 F0024、F0125、F0138、F0046；每次一个语义 selector、新 takeover 和单独证据目录。P1 来源快照为 `P1-REFERENCE-7812d302a165453badcd339473b5dba3`，运行环境 NX2506，读取参数 `match-linear`、`curve-tolerance`、`surface-tolerance` 各 0.001 mm；这些是探索参数，不是制造公差。旧 reader 证据未为该队列重跑。

F0024 历史调用如下，工作目录为项目根目录；其[退出记录](../../../workspace/v3/p3/P3-REGIONS-01/exit-F0024.json)已补完整 argv，来源标注为 root 工具调用历史的事后转录，未重放。此记录用于追溯，**不是重放指令**，历史 PID、配置及会话身份不能复用：

```powershell
python -B tests/v3/run_reference_detail_once.py --pid 2824 --part 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-01\reference-readonly.prt' --config 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-01\isolated\mcp-config.json' --evidence-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-01\native-01-F0024' --match-linear 0.001 --curve-tolerance 0.001 --surface-tolerance 0.001 --selectors-json 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-01\selectors-F0024.json'
```

后三次准确 argv 与 Python 退出码保存在各目标退出记录；这些也仅供追溯，不可重放或跨会话复用。队列的目的分别是评估 F0024 与既有 F0002 的局部侧面、F0125 对 F0004 附近肩部、F0138 对球面/平面过渡、F0046 对头部复杂曲面边界的约束。是否足以建立区域解释须由机械离线评价，不能单凭采集结果预判。

## 四次读取结果

| 目标 | 快照与摘要 | 退出与命令记录 | native 事件 | 根几何 type | 绑定 epoch |
| --- | --- | --- | ---: | ---: | ---: |
| F0024 | [快照](../../../workspace/v3/p3/P3-REGIONS-01/native-01-F0024/detail-snapshot.json) / [摘要](../../../workspace/v3/p3/P3-REGIONS-01/native-01-F0024/detail-summary.json) | [退出记录](../../../workspace/v3/p3/P3-REGIONS-01/exit-F0024.json) | 59 | 206 | 1 |
| F0125 | [快照](../../../workspace/v3/p3/P3-REGIONS-01/native-02-F0125/detail-snapshot.json) / [摘要](../../../workspace/v3/p3/P3-REGIONS-01/native-02-F0125/detail-summary.json) | [argv 与退出记录](../../../workspace/v3/p3/P3-REGIONS-01/exit-F0125.json) | 71 | 204 | 3 |
| F0138 | [快照](../../../workspace/v3/p3/P3-REGIONS-01/native-03-F0138/detail-snapshot.json) / [摘要](../../../workspace/v3/p3/P3-REGIONS-01/native-03-F0138/detail-summary.json) | [argv 与退出记录](../../../workspace/v3/p3/P3-REGIONS-01/exit-F0138.json) | 75 | 204 | 5 |
| F0046 | [快照](../../../workspace/v3/p3/P3-REGIONS-01/native-04-F0046/detail-snapshot.json) / [摘要](../../../workspace/v3/p3/P3-REGIONS-01/native-04-F0046/detail-summary.json) | [argv 与退出记录](../../../workspace/v3/p3/P3-REGIONS-01/exit-F0046.json) | 63 | 204 | 7 |

四面均在各自请求唯一匹配；native 事件 dirty before/after 均为 false、`CLEAN_TRACE`，managed dirty 采样均为 false，边覆盖完整且无 event/geometry overflow。各根响应 `ok=true`、`read_consistency_fault=false`、`writes_halted=false`、`first_change=null`；前后库存完整，diff `complete` 且 `changes=[]`，两次 native 样本相等。上述 epoch 和 Tag 均只属于当次历史会话，不能跨会话复用；库存一致不证明全几何不变。

四份摘要均记录 `RETURNED/HUMAN_OWNED` 和 `geometry=INCONCLUSIVE`；四次 Python 退出码均为 1，表示 runner 的几何未决结果，不是读取失败或 UNKNOWN。所有快照 `geometry_details_complete=false`；根几何 type 及 clean trace 不证明完整修剪、曲面参数化、邻接构造意图或整件几何。

队列四次采集已完成，证据尚待评审。[收尾及保全记录](../../../workspace/v3/p3/P3-REGIONS-01/shutdown-preservation.json)记载四次各归还后正常退出、未保存、未强杀或热替换，原件和工作副本磁盘字节均与基线一致，原件修改时间不变；[进程观察](../../../workspace/v3/p3/P3-REGIONS-01/shutdown-processes.json)记录无活动进程，TL 报告未见 NX、Journal 或 helper。磁盘保全采用已记录的直接字节比较；本次补录未重复比较。该证据只覆盖本次收尾和磁盘状态，不扩大四个面几何的结论。

当前没有更多采集队列，机械席位先离线评价现有数据；是否足够解释区域仍待证据，不能由正常归还或退出推断。

## T13.l 毛坯母线载体三次实读

[P3-STOCK-01 队列](../../../workspace/v3/p3/P3-STOCK-01/read-queue.json)限独立副本中 F0169、F0167、F0066 三个新目标、每次单 selector；作用是补一条拟议母线的局部载体与相关边，不是完整包络或截面闭合验证。工作目录、准确历史 argv 和 Python 退出码见下表各退出记录；历史 PID、配置和会话身份不得复用，记录不是重放指令。三次请求的 `match-linear`、`curve-tolerance`、`surface-tolerance` 均为 0.001 mm，仅为探索参数。

| 目标 | 快照 / 摘要 | argv、cwd、退出记录 | native clean 事件 | 根几何 type 204 原始字段：center Y、major R、minor r（mm） |
| --- | --- | --- | ---: | --- |
| F0169 | [快照](../../../workspace/v3/p3/P3-STOCK-01/native-01-F0169/detail-snapshot.json) / [摘要](../../../workspace/v3/p3/P3-STOCK-01/native-01-F0169/detail-summary.json) | [记录](../../../workspace/v3/p3/P3-STOCK-01/exit-F0169.json) | 687 | −69.76410523497、17.1665、5 |
| F0167 | [快照](../../../workspace/v3/p3/P3-STOCK-01/native-02-F0167/detail-snapshot.json) / [摘要](../../../workspace/v3/p3/P3-STOCK-01/native-02-F0167/detail-summary.json) | [记录](../../../workspace/v3/p3/P3-STOCK-01/exit-F0167.json) | 75 | −52、16、3 |
| F0066 | [快照](../../../workspace/v3/p3/P3-STOCK-01/native-03-F0066/detail-snapshot.json) / [摘要](../../../workspace/v3/p3/P3-STOCK-01/native-03-F0066/detail-summary.json) | [记录](../../../workspace/v3/p3/P3-STOCK-01/exit-F0066.json) | 75 | 15.73205080757、43、2 |

三个目标各自唯一匹配；所有 native 事件 dirty before/after 均为 false、`CLEAN_TRACE`，managed dirty 采样均为 false，未记录 incomplete，边覆盖完整且无 event/geometry overflow。根响应均 `ok=true`、无 read fault/no halt、`first_change=null`；前后库存完整且 diff `complete`、`changes=[]`，两次 native 样本相等。摘要均为 `RETURNED/HUMAN_OWNED`、`geometry=INCONCLUSIVE`；三个 Python 退出码均为 1，表示几何未决，不是读取失败或 UNKNOWN。`geometry_details_complete=false`；type 204 和原始参数不单独证明坐标解释、裁剪分支、截面闭合、材料侧或完整模型。

[收尾及磁盘保全](../../../workspace/v3/p3/P3-STOCK-01/shutdown-preservation.json)记录三次均归还后正常退出、未保存、未强杀或热替换，原件及工作副本字节和原件修改时间与基线一致；[进程观察](../../../workspace/v3/p3/P3-STOCK-01/shutdown-processes.json)记录无活动进程。上述直接字节比较为已有证据，本次索引未重复执行。三根载体及相关边已采集，拟议闭合 stock 方案仍待单独实现和验证。
