# P3-SHOULDERS-01 42 项肩部实读索引

本记录覆盖新采集的 42 项肩部，原 F0004/F0022 按已有实读证据继承，未重新读取或复审旧 proof。44 项均有受限实读不代表完整几何、编辑域或 0.001 mm 目标成立；实时状态见 `docs/V3-state.md`。

项目根目录 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`，root 为唯一实机操作通道。独立副本、新会话、已接受 T13.o C2 托管制品与 T13.f 原生制品；计划、限定输入及阈值见 [read-queue](../../../workspace/v3/p3/P3-SHOULDERS-01/read-queue.json)，复制见 [runtime-copy-record](../../../workspace/v3/p3/P3-SHOULDERS-01/runtime-copy-record.json)。未公开私有配置或 INIT 内容。

## 实际执行与逐项证据

root 工具转录记录从项目根目录执行 `python -B workspace/v3/p3/P3-SHOULDERS-01/operator-one.py init` 一次，退出 0；其后同一命令将末参数 `init` 分别替换为整数 `1` 至 `42`，每个索引执行一次、各退出 0。root 先执行索引 1，随后显式执行 10 批各 4 项（索引 2 至 41），最后执行索引 42；这些是各自独立 CLI 调用，不是自动续批。外层调用成功不等于几何通过。42 项内部 once 均记录退出 1，表示 response recorded 且几何 INCONCLUSIVE。

每项真实 `sys.executable`、完整 argv 和 cwd 存于该项 `command.json`，同目录保留 stdout、stderr、退出记录、DISPATCHED/CLEAN 及 summary/takeover/snapshot/status 四份原始 proof；`operator-ledger` 保留 42 份 dispatch、42 份 completion 和 INIT，另有 `LEDGER-STARTED.json`。TV 只读核对计划顺序、外置台账与每项命令/退出/证据 ID 的对应关系；42 个 label 和 snapshot ID 均唯一，所有 summary 均 RETURNED/HUMAN_OWNED，完整 inventory diff 为空。每项 63 条 native event，实际根几何类型 205、generator 类型 102。原 controller 当期严格校验及 CLEAN 记录保留；TV 未再执行 NX 或旧测试。

[逐项 completion-manifest](../../../workspace/v3/p3/P3-SHOULDERS-01/completion-manifest.json)列出 42 项标签、唯一 ID、证据目录和命令文件路径；它是只读索引而非原始 proof。原始 `command.json` 记录的进程为 `C:\Python314\python.exe`，其参数逐项以文件为准；历史 epoch `5760:639300003222955668` 仅为本次已退出会话的记录，不可复用。

## 事件与审计更正

每项 63 条 native event 的 called 为 true，dirty_before/dirty_after 均 false。逐项只读核对总计 2646 条事件：1890 条非 void 调用的适用返回码为 0；756 条 `UF_BREP_ask_identifier` 为 void 阶段，其 `uf_rc` 为 null。该约定见 `src/nx_sketch_mcp/v3/regions/detail_common.py` 的事件合同。TV 初次只读检查错误地假设每条都须 `uf_rc == 0`，因此该断言失败；按既有 void 合同核对后，上述字段一致。该失败是审计断言过强，不是新原生采集失败，也未触发重读。资源释放、trace 完整性和其余严格合同以当期 validator 记录及独立评审为据，不把 null 描述为返回 0。

## 安全收尾及保全

[shutdown-preservation](../../../workspace/v3/p3/P3-SHOULDERS-01/shutdown-preservation.json)记载受控 NX 正常 Alt+F4 退出、无保存提示、未保存、未强杀、未热替换 DLL；[shutdown-processes](../../../workspace/v3/p3/P3-SHOULDERS-01/shutdown-processes.json)记载受控 PID 5760 已消失且观察相关进程为空。TV 直接比较原件、before、独立工作副本字节相同，原件 mtime 与 [复制记录](../../../workspace/v3/p3/P3-SHOULDERS-01/source-copy-record.json)相同；36 个列明源码与冻结副本字节相同，见 [source-evidence-record](../../../workspace/v3/p3/P3-SHOULDERS-01/source-evidence-record.json)及 [source-freeze-at-shutdown](../../../workspace/v3/p3/P3-SHOULDERS-01/source-freeze-at-shutdown.json)。操作员脚本及连接配置也与各自冻结副本直接字节相同。

[operator-preservation](../../../workspace/v3/p3/P3-SHOULDERS-01/operator-preservation.json)记录 42 dispatch/42 completion、无 STOP、无 `OPERATOR-LOCK.json`。其记录说明最初错误检查了无关 `LOCK.json`，后来按实际 operator 锁名更正；TV 按正确锁路径核对。未以时间/大小代替字节比较，未进行哈希。该索引不将收尾记录外推到未来进程状态；新增实读与几何解释仍须独立评审和 TL 接收。
