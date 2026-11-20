# P3 Swept 首批采集与用户暂停证据

本记录仅索引实际产物；实时状态见 docs/V3-state.md。用户明确要求暂停以准备可能关机，未完成 P3，不进入 P4。

本次实验为 `workspace/v3/p3/P3-SWEPT-01/`，cwd `C:/0sf/1PROJECT/AI/design/nx-sketch-mcp`。runtime 来自已审 T13.o C2 托管制品及复用 T13.f 原生 DLL；复制记录、普通路径检查、冻结 Python 源与当前源直接字节一致记录均在该目录。未 Git、未计算文件/目录/模型 hash。

三批实际命令使用同一已打开独立工作副本，controller 下 connection-only 配置无 launch 项；当前 session epoch 在当时为 `6648:639298346546755302`，现已退出，禁止复用。init 只建立文件；三次 run 分别明确 count 1、4、4，每次由 root 派发，未自动下一批。每项由 once runner 经原子 guarded takeover 获取新凭据；前一项通过完整证据验证并归还后才继续。

```powershell
python -B tests/v3/run_swept_queue.py init --run-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-01\controller' --part 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-01\reference-readonly.prt' --config 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-01\controller\connection.json' --pid 6648 --session-epoch '6648:639298346546755302' --match-linear 0.001 --curve-tolerance 0.0001 --surface-tolerance 0.0001 --angular-tolerance 0.0001
python -B tests/v3/run_swept_queue.py run --run-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-01\controller' --session-epoch '6648:639298346546755302' --count 1
python -B tests/v3/run_swept_queue.py run --run-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-01\controller' --session-epoch '6648:639298346546755302' --count 4
python -B tests/v3/run_swept_queue.py run --run-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p3\P3-SWEPT-01\controller' --session-epoch '6648:639298346546755302' --count 4
```

init 和三次批命令实际 Python 退出码均为 0，逐次结果见 init-result.json、batch-01/02/03-result.json；单项 once 的退出1是 geometry=INCONCLUSIVE 约定，不是 G 验收通过。9个新目标为 F0008、F0010、F0017、F0034、F0039、F0052、F0057、F0058、F0072，每项原始 takeover/snapshot/status/summary 在controller/item-*/evidence，DISPATCHED 与 CLEAN 标记保留。每项记录 clean、空库存diff、RETURNED/HUMAN_OWNED；用户暂停时无在飞 dispatch、无LOCK、此前无错误STOP。

用户暂停后 root 写入 UserRequestedPause 的持久 STOP，未再派发；正常关闭本次 NX、不保存，原件及工作副本与本次before直接字节相同、原件mtime不变、无NX/Journal/helper。见 `shutdown-preservation.json`、`shutdown-processes.json`。这9项的受限独立实机补审尚待后续，不能仅靠CLEAN标记宣布全几何完成。

`pause-manifest.json` 保存全部9项来源/结果引用及剩余33个语义选择器，下一为F0077；之前F0002/F0024两项直接继承。共11/44取得细节，仍不证明44面全部已解释或0.001 mm目标达到。

后续仅在用户明确继续后：核当前状态，继承9项及原2项，不重读。旧controller固定42并绑定已退出epoch，没有安全的跨session自动恢复接口；不得删STOP/改旧context绕过。须先离线实现/审查从已验证证据构建33项新队列的最小适配，再创建新的当前会话上下文。此处命令是历史证据，禁止直接重放。
