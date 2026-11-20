# P3-CARRIERS-01 44 项新载体实读索引

本记录覆盖 P3-CARRIERS-01 的 44 个新载体；既有 97 项数据直接继承，本次未重读或复审，另外 9 个球面未派发。采集记录不证明完整几何、工程意图或 0.001 mm 全域精度；实时状态以 `docs/V3-state.md` 为准。

执行 cwd 为 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`，root 为唯一实机通道。实验使用独立工作副本、新会话与既有受审制品，复制配置见 [runtime-copy-record](../../../workspace/v3/p3/P3-CARRIERS-01/runtime-copy-record.json)。44 个目标、排除项、root 204 字段门禁、匹配阈值和固定预算见 [read-queue](../../../workspace/v3/p3/P3-CARRIERS-01/read-queue.json)；匹配及近似请求值不是已达到的形状误差或制造公差。私有连接配置及 INIT 内容不在此复制。

## 实际操作与逐项证据

root 本轮工具转录记录从项目根目录执行 `python -B workspace/v3/p3/P3-CARRIERS-01/operator-one.py init` 一次，退出 0；随后以同一命令将末参数 `init` 分别替换为整数 `1` 至 `44`，每索引执行一次，外层 operator 各退出 0。首项为 F0156；随后 10 次显式四项批次处理索引 2 至 41，最后处理索引 42 至 44。批次由 root 明确控制，并非自动续派。44 个内部 once 均记录退出 1，表示 response recorded 且几何 INCONCLUSIVE，非几何验收通过。

每项实际 `sys.executable`、完整 argv、cwd 保存在各自 `command.json`，同目录保留 once 退出记录、stdout/stderr、DISPATCHED/CLEAN 和 summary/takeover/snapshot/status 四份原始 proof；外置 operator-ledger 保存 44 份 dispatch、44 份 completion 与 INIT，另有 `LEDGER-STARTED.json`。TV 只读对照计划、台账、命令、退出、证据 ID 和序列，44 项标签与 snapshot ID 均唯一；各项 root geometry 类型 204、CLEAN_TRACE、完整空 inventory diff、RETURNED/HUMAN_OWNED。root 当期 strict validator 及字段守卫结果与 CLEAN 标记保留；TV 未再次调用 NX 或重跑旧测试。

[逐项 completion-manifest](../../../workspace/v3/p3/P3-CARRIERS-01/completion-manifest.json)列出各项标签、snapshot ID、原始证据目录、命令文件、事件数及边数，供定位原始记录；它不替代原始 proof。历史 session epoch `9904:639300041636116524` 仅用于识别已退出会话，不得复用。

| 每项 native 事件数 | 项数 |
| --- | ---: |
| 63 | 11 |
| 71 | 19 |
| 75 | 4 |
| 84 | 2 |
| 119 | 3 |
| 132 | 2 |
| 161 | 2 |
| 687 | 1 |

其中 F0126 为索引 24，观察面有 48 条边、687 条 native events；记录的既定预算未增加。对全部 4140 条事件只读核对，调用均标记 called，dirty_before/dirty_after 均 false；3028 个非 void 阶段返回码 0，1112 个既有 void 阶段返回 null。void/null 按 `src/nx_sketch_mcp/v3/regions/detail_common.py` 事件合同解释，不记作返回 0；释放配对及完整性以当期严格 validator 和独立评审为据。

## 收尾及保全

[shutdown-preservation](../../../workspace/v3/p3/P3-CARRIERS-01/shutdown-preservation.json)记录受控 NX 正常 Alt+F4 退出、无保存提示、未保存、未强杀及未热替换 DLL；[shutdown-processes](../../../workspace/v3/p3/P3-CARRIERS-01/shutdown-processes.json)记载受控 PID 9904 已消失，观察相关进程为空。TV 直接比较原件、before 和独立工作副本字节相同，原件 mtime 与 [复制记录](../../../workspace/v3/p3/P3-CARRIERS-01/source-copy-record.json)相同；36 个列明源码与冻结副本字节相同，见 [source-evidence-record](../../../workspace/v3/p3/P3-CARRIERS-01/source-evidence-record.json)和 [source-freeze-at-shutdown](../../../workspace/v3/p3/P3-CARRIERS-01/source-freeze-at-shutdown.json)。operator 程序与连接配置也分别与冻结副本直接字节一致。

[operator-preservation](../../../workspace/v3/p3/P3-CARRIERS-01/operator-preservation.json)记载 44 dispatch/44 completion，无 STOP、无实际 `OPERATOR-LOCK.json`；TV 按该正确锁路径只读核对。未以元数据代替字节比较，未计算哈希。收尾记录不外推未来进程状态；新增证据待独立评审及 TL 接收。
