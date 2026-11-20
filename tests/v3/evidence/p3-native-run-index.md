# P3 T13.a 首次原生补读证据与冻结

2026-11-08，工作目录 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`。首次补读证据 ID `P3-DETAIL-54635234d12e46669ae97c5106e55816`；NX 进程 PID 16252 仅为当次历史值，不能复用于接管。NX build `v2506.0.0.1700`，长度单位 mm；隔离候选为 native 源 C3（`workspace/build/v3-p3-candidate-c3/`），托管 CLR C1（相同构建目录中的复制版本）。输入是独立副本 `workspace/v3/p3/P3-NATIVE-02/reference-readonly.prt` 及 P1 snapshot `workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json`；未复用 P1 的会话 Tag/JID。控制阈值 match-linear、curve-tolerance、surface-tolerance 各为 0.001 mm，均为本次读取参数，不是制造公差或全域误差界。

## 结果与当前边界

- [脱敏 summary](../../../workspace/v3/p3/P3-NATIVE-02/native-01/detail-summary.json)：`takeover=AI_OWNED`、`inspection=unresolved_or_frozen`、`return=not attempted`、`status=STOP_MANUAL_CHECK`；工具报告外层 exit_code 1，但未独立采集 Python 进程退出码，不能将外层码当作 Python 原始退出码。未重放、未保存；不能表示读取得到有效几何或安全归还。
- [脱敏 takeover](../../../workspace/v3/p3/P3-NATIVE-02/native-01/detail-takeover.json) 显示当次已加载独立副本；[脱敏 detail](../../../workspace/v3/p3/P3-NATIVE-02/native-01/detail-snapshot.json) 记录 F0002 和 F0005 各匹配一个面，但各自几何状态均为 `INCONCLUSIVE`。快照 `ok=false`、`complete=false`、`geometry_details_complete=false`、`read_consistency_fault=true`、`writes_halted=true`、`ownership_state=UNKNOWN_FROZEN`；dirty 从 false 变 true，`two_native_samples_equal=false`，revision 为 `cached_not_refreshed`。一致性故障下，不将匹配和返回数据用作确认或闭合复杂曲面的依据。
- 当前冻结期间停止写入、归还、重放及自动解冻，不能凭历史 PID、epoch 或凭据接手。异常成因尚未确定；需在人工核查隔离过程、模型、外部资源和恢复路径后处理。[冻结时保全记录](../../../workspace/v3/p3/P3-NATIVE-02/source-preservation-frozen.json) 使用直接字节比较，原件及副本磁盘内容与读取前各自基线一致、原件修改时间未变；这不证明 dirty 的内存模型未变。root 已询问用户如何处置现场，截至本记录尚未回复；未安全归还。

## 执行记录

root 提供的逐字命令如下，一次 detail 请求后触发冻结；这是历史证据，不是重放指令：

```powershell
python -B tests/v3/run_reference_detail_once.py --pid 16252 --part 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-NATIVE-02\reference-readonly.prt' --config 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-NATIVE-02\isolated\mcp-config.json' --evidence-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-NATIVE-02\native-01' --match-linear 0.001 --curve-tolerance 0.001 --surface-tolerance 0.001
```

先前 [P3-NATIVE-01 启动](../../../workspace/v3/p3/P3-NATIVE-01/launch-record.json) 之后，因 R04 评审撤回读取放行，在打开部件、取得所有权或调用读取之前 [正常关闭空 NX](../../../workspace/v3/p3/P3-NATIVE-01/pre-read-shutdown-record.json)，未强杀。P3-NATIVE-02 首次通过子 PowerShell 启动脚本时被执行策略拒绝，NX 未启动；之后使用当前会话正常启动，未修改安全策略，见 [启动记录](../../../workspace/v3/p3/P3-NATIVE-02/launch-record.json)。上述启动不构成第二次读取。

先前 [P3 离线验证索引](p3-validation.md) 包含 runner 及故障门禁假件、C1 首败和对应最小复验；这些不是本次 NX 成功证据。[几何 API 调查](p3-geometry-api-investigation.md) 说明接口假设、资源释放与未知限制，不代表对当前故障原因的结论。
