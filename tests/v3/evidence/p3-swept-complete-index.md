# P3 Swept 33 项续读完成证据索引

本索引记录 `P3-SWEPT-02` 本次 33 个新目标的只读采集，实时状态以 `docs/V3-state.md` 为准。它不表示 P3 或整件几何验收完成。前两项 F0002/F0024 和旧队列九项按[暂停索引](p3-swept-pause-index.md)及其原证据继承，本次未重新读取或复核这 11 项的原生响应。

## 配置、命令与范围

项目根目录 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`，PowerShell，非登录 shell；root 唯一实机通道。P3-SWEPT-02 使用独立零件副本、新连接上下文，以及已接受的 T13.o C2 托管制品和 T13.f 原生 DLL；复制记录为 [runtime-copy-record](../../../workspace/v3/p3/P3-SWEPT-02/runtime-copy-record.json)，36 个冻结源码文件及直接字节对照记录为 [source-evidence-record](../../../workspace/v3/p3/P3-SWEPT-02/source-evidence-record.json) 和 [source-freeze-at-shutdown](../../../workspace/v3/p3/P3-SWEPT-02/source-freeze-at-shutdown.json)。连接配置为私有 connection-only；不公开配置或凭据。旧会话 STOP/context 未作为新会话使用。

以下命令根据 root 本轮实际工具调用转录；`init-result.json` 和各 `batch-XX-result.json` 独立记录动作、会话、数量和退出码，但没有保存完整命令行或 stdout，故不将转录说成独立 stdout 文件。历史 session epoch 仅用于识别本次已退出进程，不得复用。

```powershell
python -B tests/v3/run_swept_queue.py init --run-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-02\controller' --part 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-02\reference-readonly.prt' --config 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-02\controller\connection.json' --pid 12448 --session-epoch '12448:639299920216055500' --match-linear 0.001 --curve-tolerance 0.0001 --surface-tolerance 0.0001 --angular-tolerance 0.0001 --inherit-run 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-01\controller'
python -B tests/v3/run_swept_queue.py run --run-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-02\controller' --session-epoch '12448:639299920216055500' --count 1
python -B tests/v3/run_swept_queue.py run --run-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-02\controller' --session-epoch '12448:639299920216055500' --count 4
```

最后一条 `--count 4` 实际独立运行八次，而非循环自动续批。root 工具转录记录对应 `dispatched_clean=1` 和每批 `dispatched_clean=4`；init 与九批结果均记录退出码 0，见 [init 结果](../../../workspace/v3/p3/P3-SWEPT-02/init-result.json)及 [batch-01](../../../workspace/v3/p3/P3-SWEPT-02/batch-01-result.json) 至 [batch-09](../../../workspace/v3/p3/P3-SWEPT-02/batch-09-result.json)。单项 once 返回码 1 是 recorded-response/geometry INCONCLUSIVE 约定，不能当成几何验收通过。

## 逐项与收尾核查

TV 只读调用当前冻结控制器的 `completed_prefix` 和严格 `validate_evidence` 检查 33 项记录；以新 plan 与旧暂停清单的 `remaining_selectors` 全量比较，核对每项 selector、dispatch、CLEAN、takeover、snapshot、status、summary、连续顺序、唯一 snapshot ID、完整空 inventory diff。33 项严格检查成立，每项 59 条 native diagnostic event，summary 均 `RETURNED`/`HUMAN_OWNED`、geometry `INCONCLUSIVE`；无 STOP/LOCK。所有新项的标签、各自 snapshot ID 和原始 summary/snapshot/dispatch/CLEAN 路径保存在 [completion-manifest.json](../../../workspace/v3/p3/P3-SWEPT-02/completion-manifest.json)，原始 takeover/status 位于各项同一 `evidence` 目录。该清单是本次只读核验索引，不替代原始证据；未重新执行 NX 或旧测试。

| 实际批次 | 新目标 |
| --- | --- |
| 01 | F0077 |
| 02 | F0084、F0085、F0086、F0088 |
| 03 | F0091、F0093、F0094、F0103 |
| 04 | F0107、F0111、F0114、F0134 |
| 05 | F0144、F0146、F0149、F0159 |
| 06 | F0170、F0180、F0184、F0186 |
| 07 | F0197、F0207、F0208、F0214 |
| 08 | F0216、F0217、F0221、F0222 |
| 09 | F0224、F0227、F0228、F0234 |

[正常退出及保全记录](../../../workspace/v3/p3/P3-SWEPT-02/shutdown-preservation.json)记载本次受控 NX 正常 Alt+F4 退出、无保存提示、未保存、未强杀及未热替换 DLL；[进程记录](../../../workspace/v3/p3/P3-SWEPT-02/shutdown-processes.json)记载 PID 12448 已消失且所观察相关进程为空。TV 另以直接字节比较核对原件、本次 before 和独立副本相同，原件 mtime 与 [复制记录](../../../workspace/v3/p3/P3-SWEPT-02/source-copy-record.json)相同；36 个列明源码当前字节与本次 source-evidence 副本相同。该核查不以时间或大小代替字节比较，不构成对未列源码或未来环境的保证。

此前 11 项与本次 33 项合计 44 个 Swept 细节观察；它们只覆盖各自受限采集合同。完整面修剪、实体几何、工程意图及 0.001 mm 全域目标仍未证明，不能由 CLEAN/空 diff 或面数宣称完成；P3 后续工作和独立审查仍需按台账执行。
