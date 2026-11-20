# P3-REGIONS-02 两项新区域实读索引

本索引只覆盖 F0022 和 F0041 的 C2 两次新采集，不重验旧区域或扩大到其他面；实时进度见 `docs/V3-state.md`。根目录 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`，root 为唯一实机通道，使用独立副本和新会话。制品为已接受的 T13.o C2 托管运行时与 T13.f 原生 DLL，见 [runtime-copy-record](../../../workspace/v3/p3/P3-REGIONS-02/runtime-copy-record.json)。两项的选择器、顺序、预算、匹配阈值及目标见 [read-queue-c2](../../../workspace/v3/p3/P3-REGIONS-02/read-queue-c2.json)。0.001 mm、0.0001 mm 及 0.0001 rad 是请求和匹配配置，不是实际几何精度或制造公差。

## 首次参数拒绝与 C2 原生采集

第一次 F0022 命令以 `selectors-F0022.json` 的列表作为输入，CLI 要求的是包含 `source_snapshot_id` 和 `selectors` 的对象；argparse 在创建 McpServer 之前拒绝，退出码 2。实际 [错误记录](../../../workspace/v3/p3/P3-REGIONS-02/native-01-F0022/argument-error.txt)、[退出记录](../../../workspace/v3/p3/P3-REGIONS-02/native-01-F0022/python-exit-record.json)、[原 STOP](../../../workspace/v3/p3/P3-REGIONS-02/STOP.json)和错误 selector 均保留。DISPATCHED 标记在 CLI 调用前写入，不证明原生调用；当次无 initialize、takeover 或 inspect，也无四份 detail 产物。独立评审 T.1 受限接受以正确 envelope 的 C2 计划在同一受控会话继续，见 [评审记录](p3-independent-review.md)；这不是自动清除 STOP 或重放一次已知原生读取。

以下完整命令由 root 本轮实际工具调用转录；原始记录保存退出码及必要产物，没有独立 stdout 日志。实际可执行文件为 PATH 上 `python`，cwd 为项目根目录。历史 session epoch 仅作本次已退出进程的证据，不得复用。

```powershell
python -B tests/v3/run_reference_detail_once.py --pid 876 --part 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\reference-readonly.prt' --config 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\connection.json' --evidence-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\native-01-F0022' --match-linear 0.001 --curve-tolerance 0.0001 --surface-tolerance 0.0001 --selectors-json 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\selectors-F0022.json' --expected-session-epoch '876:639299934281974910'
python -B tests/v3/run_reference_detail_once.py --pid 876 --part 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\reference-readonly.prt' --config 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\connection.json' --evidence-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\native-c2-01-F0022' --match-linear 0.001 --curve-tolerance 0.0001 --surface-tolerance 0.0001 --selectors-json 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\selectors-F0022-c2.json' --expected-session-epoch '876:639299934281974910'
python -B tests/v3/run_reference_detail_once.py --pid 876 --part 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\reference-readonly.prt' --config 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\connection.json' --evidence-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\native-c2-02-F0041' --match-linear 0.001 --curve-tolerance 0.0001 --surface-tolerance 0.0001 --selectors-json 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-REGIONS-02\selectors-F0041-c2.json' --expected-session-epoch '876:639299934281974910'
```

C2 两次退出码均为 1，代表 response recorded 且几何 `INCONCLUSIVE` 的约定，不是该读取失败或几何通过。root 在当期对两项调用 `run_swept_queue.validate_evidence` 严格核验；各自 CLEAN、退出记录及四份原始 detail 文件保存在以下独立目录。TV 本次只读核对 summary/snapshot ID、退出码、native trace 计数、空库存 diff 和归还状态；不重复调用原生读取或旧证据测试。

| 面 | 原始证据 | snapshot ID | native events | 结果 |
| --- | --- | --- | --- | --- |
| F0022 | [native-c2-01-F0022](../../../workspace/v3/p3/P3-REGIONS-02/native-c2-01-F0022/) | `P3-DETAIL-4ed0b9f6316940b4a367be44a240b24c` | 63 | CLEAN_TRACE，完整空 diff，RETURNED/HUMAN_OWNED，INCONCLUSIVE |
| F0041 | [native-c2-02-F0041](../../../workspace/v3/p3/P3-REGIONS-02/native-c2-02-F0041/) | `P3-DETAIL-1011c288d0574e98b6b961bac9ab4908` | 119 | CLEAN_TRACE，完整空 diff，RETURNED/HUMAN_OWNED，INCONCLUSIVE |

## 保全及限制

[shutdown-preservation](../../../workspace/v3/p3/P3-REGIONS-02/shutdown-preservation.json)记载受控 NX 正常 Alt+F4 退出，无保存提示、未保存、未强杀或热替换 DLL；[shutdown-processes](../../../workspace/v3/p3/P3-REGIONS-02/shutdown-processes.json)记载受控 PID 已消失及观察相关进程为空。TV 直接比较原件、before 和独立工作副本字节相同，原件 mtime 与 [复制记录](../../../workspace/v3/p3/P3-REGIONS-02/source-copy-record.json)一致；36 个列明源码与本次冻结副本直接字节一致，对应 [source-evidence-record](../../../workspace/v3/p3/P3-REGIONS-02/source-evidence-record.json)及 [source-freeze-at-shutdown](../../../workspace/v3/p3/P3-REGIONS-02/source-freeze-at-shutdown.json)。不使用哈希或将元数据当字节一致证明。

两项是限定范围的原生响应，不证明其他肩部或扇区的几何、完整修剪、设计意图、实际可执行建模或 0.001 mm 全域误差。完成索引不代表 P3 已完成；新增证据仍待独立评审及 TL 接收。
