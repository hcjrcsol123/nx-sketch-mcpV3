# P2 手写块体架构烟测实机证据索引

日期：2026-11-08，Asia/Shanghai；工作目录 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`。这是有限架构证据，不是原样件重建、全域几何或生产能力验收。实时任务状态由 [V3 台账](../../../docs/V3-state.md) 单独维护。

## UG11：已有有效证据

- [T06 三次实机索引](../ug11_probe/T06-run-index.md)：前两次失败保留；03 使用经确认的 NX11 环境，完成空白件、四个 Driving、表达式使用者、width 到 height 公式联动、x 位置改变和保存关闭重开。明确版本及证据细节以索引为准，不推广到其他 UG 版本。
- [T11 IR 驱动原型索引](../ug11_probe/T11-run-index.md)：用当前 IR 的一次实机原型验证宽高公式与位置编辑及重开；独立评审和 TL 已接受。该次未测体积；其 datum 映射和能力限制以索引为准。这些是 UG11 单块体证据，不能代替 NX2506 T12 全链。

## NX2506：首次产品链失败，保留有效前段

`P2-NX2506-01/native-01` 使用隔离候选 C3 和保存的独立夹具，通过 [T12 runner](../smoke_plan/run_block_once.py) 执行。其初始 [session 回读](../../../workspace/v3/p2/P2-NX2506-01/native-01/0002-response.json) 和 [零件库存](../../../workspace/v3/p2/P2-NX2506-01/native-01/0003-response.json) 证明该次工作件为毫米、FullyLoaded、无特征/草图/实体/曲线，读前后 dirty false；这为先前夹具 Journal 单位检查失败提供独立的有效起始状态。原 Journal 的失败及枚举问题仍保留在 [离线与夹具索引](p2-smoke-offline.md)，不改写为 PASS。

当次既有授权链中 DatumPlane 创建成功且 [fresh 原生验证](../../../workspace/v3/p2/P2-NX2506-01/native-01/0008-response.json) 成功；随后创建草图在现有保全检查中失败，返回 `UNSUPPORTED_SWEEP_PRESERVATION`，`datum is not the unique parent of one sketch feature`。终态 [失败和回滚证据](../../../workspace/v3/p2/P2-NX2506-01/native-01/0015-response.json) 为 `FAILED` / `ROLLED_BACK`，语义、历史、几何、dirty 状态和实体恢复检查为 true，`writes_halted=false`。本次未进入 T09 绑定、实体创建、尺寸/位置编辑或保存重开，因此不构成 T09/T12 通过。

runner 停止后，root 另行 fresh 检查已知回滚状态、按授权安全归还；[归还记录](../../../workspace/v3/p2/P2-NX2506-01/known-rollback-return.json) 与 [正常关闭记录](../../../workspace/v3/p2/P2-NX2506-01/shutdown-record.json) 保留。失败日志及现场记录不可覆盖；T10.a 须查明原生支持关系并修复，按评审批准的受影响最小链复验。每次使用新会话身份，不复用已记录的会话标识或操作凭据。

## NX2506：C4 受影响链复验

`P2-NX2506-02/native-01` 由 root 独占执行，状态 `NX2506_PASS`、进程退出码 0；[摘要](../../../workspace/v3/p2/P2-NX2506-02/native-01/summary.json)。输入为本次新建的独立空白 PRT，输出为本次新路径 `P2-NX2506-02/block-final.prt`；未打开参考件。隔离 runtime 使用人工候选编号 `P2-C4`、构建目录 `workspace/build/v3-p2-candidate-c4`；runner 人工标识 `P2-SMOKE-T10A-20261108-01`，编号均非内容摘要。运行时 NX build `v2506.0.0.1700`、NXOpen `2506.0.0.0`；宿主解释器 `C:\Python314\python.exe`、Python 3.14.7。工作目录为本文开头所列项目目录。root 报告执行命令如下，路径标识本次私有环境，不是下次重放指令：

```powershell
python -B tests/v3/smoke_plan/run_block_once.py --pid 8188 --part 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p2\P2-NX2506-02\fixture\blank-mm.prt' --target 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p2\P2-NX2506-02\block-final.prt' --config 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p2\P2-NX2506-02\isolated\mcp-config.json' --evidence-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p2\P2-NX2506-02\native-01'
```

- [接管及初始读取](../../../workspace/v3/p2/P2-NX2506-02/native-01/0002-response.json) 确认毫米、FullyLoaded、读前后 dirty false；[库存](../../../workspace/v3/p2/P2-NX2506-02/native-01/0003-response.json) 为空白。按实际请求顺序执行 datum、Driving 矩形、实体拉伸，各经 prepare/execute/get/fresh；[拉伸 fresh](../../../workspace/v3/p2/P2-NX2506-02/native-01/0028-response.json) 成功。后续绑定、width 编辑、x 编辑的 execute 均 `APPLIED`、`readback_verified=true`、非目标保全成功、更新错误数为 0。
- [绑定初始 fresh](../../../workspace/v3/p2/P2-NX2506-02/native-01/0037-response.json)、[width 编辑 fresh](../../../workspace/v3/p2/P2-NX2506-02/native-01/0045-response.json)、[x 编辑 fresh](../../../workspace/v3/p2/P2-NX2506-02/native-01/0052-response.json) 的 `bindings`、`geometry`、`history`、`non_target_preservation` 四项均 `VERIFIED`。四个草图参数均为毫米 Driving 尺寸并返回几何使用者；depth 为毫米 Extrude 终止表达式且返回特征使用者。`v3_width` 的引用表达式含 `v3_height`，后者原生公式为 `v3_width*2/3`。
- 三态原生 bbox 分别为 `[10,5,0,40,25,15]`、`[10,5,0,46.00000000000001,29.000000000000007,15]`、`[14,5,0,50.00000000000001,29.000000000000007,15]` mm；体积分别为 `9000`、`12960.000000000005`、`12960.000000000005` mm³。与独立 `block_oracle.py` 的期望比较，最大坐标绝对误差约 `7.2e-15 mm`，最大体积绝对误差约 `5.5e-12 mm³`，均在数值门限内。门限是测试比较值，不代表制造精度；bbox/体积也不证明一般形状全域等价。
- [保存重开](../../../workspace/v3/p2/P2-NX2506-02/native-01/0059-response.json) 报告 saved/reopened，expression、geometry、history、associations 四项均 `VERIFIED`。重开后[新鲜库存](../../../workspace/v3/p2/P2-NX2506-02/native-01/0061-response.json) 实际有四个可见特征：`ABSOLUTE_DATUM_PLANE`、`DATUM_CSYS`、`SKETCH`、`EXTRUDE`；通过原生支持和父子链重新定位，未复用保存前对象 ID。新会话身份下 [prepare-only 请求](../../../workspace/v3/p2/P2-NX2506-02/native-01/0064-request.json) 使用 width `37`；其 [before](../../../workspace/v3/p2/P2-NX2506-02/native-01/0065-response.json) 原生读取五参数、公式、使用者及最终几何，与重开前一致。从该 prepare 至归还没有 `nx_execute_plan`，故没有在重开后实际编辑至 37。重开后首个 session 读取报告语义变化；后续 prepare 前后 revision 保持一致且语义变化均 false，dirty 均为 true；这是 true→true 的布尔观测，不证明没有任何副作用。
- [归还](../../../workspace/v3/p2/P2-NX2506-02/native-01/0067-response.json) 为 `HUMAN_OWNED` 且 `safe_for_human=true`。[收尾记录](../../../workspace/v3/p2/P2-NX2506-02/shutdown-record.json) 表明随后正常关闭 GUI，选择不保存 getter 后的 dirty，避免改变已核验的磁盘副本；未强制终止，观察时相关剩余进程列表为空。

以上证据用于本次单块体的 T09/T10/T12 限定验收；首次失败、限定支持图和 UG11 版本边界仍然有效。产品链复验不会自动关闭未测的参考样件识别、复杂组合、跨版本通用兼容或后续阶段的完整编辑矩阵。
