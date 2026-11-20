# V3 参考件重建与交付

本次交付包含由同一默认计划分别生成的两个原生参数件，以及可在已验 UG11 环境独立运行的脚本包。默认件三段全件几何与双端参数、持久性证据见[产品验证记录](../../tests/v3/evidence/p7-reference-chain.md)。

| 使用目的 | 交付文件 |
| --- | --- |
| 在 NX2506 查看或编辑默认件 | [外球叉_参数化.prt](../../workspace/v3/p7/T31-DELIVERY-01/NX2506/外球叉_参数化.prt) |
| 在 UG11 查看或编辑默认件 | [外球叉_参数化.prt](../../workspace/v3/p7/T31-DELIVERY-01/UG11/外球叉_参数化.prt) |
| 在其他目录从空白件重建 UG11 模型 | 复制[整个脚本包](../../workspace/v3/p7/T31-DELIVERY-01/UG11-Bundle/)，按[包内运行说明](../../workspace/v3/p7/T31-DELIVERY-01/UG11-Bundle/README.md)操作 |

2026-11-20 整理时核对，上表中的 UG11 交付副本目前与首次验收时的文件字节不同。需要复查首次验收件时，请使用[UG11 实机保存原件](../../workspace/v3/p7/T31-UG11-01/result/blank.prt)，它与当时的几何验证副本逐字节一致。11 月 19 日双版本重建的[中文命名模型](../../workspace/v3/p7/REBUILD-20261119-01/deliver/)也已核对，两个交付文件均与同次运行中保存、重开并核名的模型逐字节一致。

**其他已交付版本**

| 交付 | 双版本模型与结果 | UG11 脚本 |
| --- | --- | --- |
| 11 月 19 日中文命名版 | [NX2506、UG11 模型](../../workspace/v3/p7/REBUILD-20261119-01/deliver/) · [验证摘要](../../workspace/v3/p7/REBUILD-20261119-01/trial-result.json) | [完整包](../../workspace/v3/p7/REBUILD-20261119-01/ug11-bundle/) |
| 11 月 20 日全局入口版 | [NX2506、UG11 模型及验收记录](../../workspace/v3/p7/GLOBAL-REBUILD-20261120-01/deliver/) | [完整包](../../workspace/v3/p7/GLOBAL-REBUILD-20261120-01/UG11-Bundle/) |

历史评审中的原始会话路径按执行时记录。项目已按“运行与交付”精简，最终结论、已知故障与当前仍可运行的验证见[状态台账](../V3-state.md)。

## 适用范围

- 已审参考路线接受磁盘内容与 P1/P3 已审样件完全一致的独立文件。产品重建已审构造，另外把当前 NX 读取到的面载体与拓扑对应到该构造。它不支持把这一方案直接套用到尺寸或姿态不同的任意零件。
- `nx_analyze_v3_reference` 也可不传 `source_path`，只返回当前读取的几何候选和未解决项。这些候选没有完整裁剪、材料侧和可执行建模证明。
- 同构造族的原生参数化保存件可从当前模型推断尺寸。在一个 104 项尺寸均已改变的实际样件上，产品恢复了当前驱动值和 2,016 个构造步骤，事后同该件已验的 218 面几何证书相符。对其他输入，需分别核实完整几何及执行适用性。[实件证据](../../workspace/v3/p7/T31-FAMILY-D02/case-acceptance.json)
- 文件字节比较和只读锁不使用哈希。计划中引用的 P1 面编号只属于该次观察；不要把 Tag、JournalIdentifier、所有权、epoch 或 revision 带到另一个 NX 会话。

## 已审参考的读取和建模

在规划特征树时，按部位和用途给草图及其生成的特征命名，例如“尾槽轮廓”和“尾槽切除”。NX2506 和 UG11 的 NXOpen 提供 `NXObject.SetName`，草图对应的特征可由 `Sketch.Feature` 取得。MCP 客户端从 `design_guidance.preferences` 读取命名建议，在所用接口支持时写入显示名。

需要安装并配置项目的 NX2506 MCP 桥、NXOpen 和一个 MCP 客户端。客户端先完成 `initialize` 与 `notifications/initialized`。下面的操作必须在同一项目的证据文件可用时进行；MCP 客户端应读取工具响应中的 `structuredContent`，并检查 `isError`。首次读取时，响应可能大于 2 MB。

1. 把参考 PRT 复制到新的独立本地文件。对源文件和副本取得禁止写入及删除的读锁，确认两者内容逐字节相同；锁须在 NX 加载副本**之前**取得，并保持至参考 NX 会话正常关闭。该过程的启动、PID、进程启动时刻、锁和退出记录应由受控启动器保留。单独调用 MCP 工具不能证明锁在加载之前已存在。
2. 在受控的 NX2506 参考会话打开该副本。检查当前进程及 epoch、零件路径、完整加载、毫米单位和未修改状态。经用户明确授权后，调用 `nx_takeover`，传入 `expected_pid`、`expected_session_epoch`（`PID:UTC启动ticks`）、`expected_part_path`、`artifact_scope: "saved_independent_copy"` 和 `authorize: true`。保留本会话返回的 `ownership_id`、`binding_epoch`、`revision_id`、`load_instance_id`。
3. 在同一会话调用 `nx_analyze_v3_reference`：

   ```json
   {"ownership_id":"<current-owner>","binding_epoch":1,"revision_id":"<current-revision>","snapshot_id":"<new-unique-snapshot>","linear":0.001,"angular":0.0001,"source_path":"C:\\work\\reference-copy.prt"}
   ```

   `linear` 为参考件长度单位下的候选匹配阈值，`angular` 为弧度；它们不是公差或精度证明。多实体必须按工具 schema 传入当前会话的 `body_id`。客户端应对照接管结果和受控启动记录，检查 `read_provenance` 的 epoch、load instance、路径、revision、实体、单位和前后未修改状态。`reviewed_source.status` 应为 `current_inventory_matches_reviewed_disk_source`，并检查其 `correspondence`、`group_count`、`output_id` 和 `design_guidance`。面和边的对应是所报告载体、邻接与重数的对应；边等价类不伪造单边身份，不证明全部有限裁剪。
4. 规划特征时，草图能表达所需几何和编辑关系就优先使用原生参数化草图。例如，先在一个原生草图里绘制同一平面轮廓的线段、圆弧和样条，再让拉伸或回转直接引用这个草图作为截面。修改轮廓时可打开该草图编辑尺寸和约束。建模前向用户展示 `design_guidance` 中适用的共享轮廓和阵列建议，说明哪些尺寸会联动、哪些需要独立修改。用户可以保留现有构造。`nx_v3_compare_design_options` 会比较客户端提供的 `plan` 和 `groups`，几何相同但驱动身份不同的轮廓会得到 `keep_independent`。
5. 完成参考读取后，按当前会话凭据调用 `nx_return`，确认返回人工控制，再由受控启动器正常关闭该参考会话并保存退出证据。锁保护应持续到关闭；异常或结果不明时停止并保留现场。
6. 在**另一个**已识别的 NX2506 会话中准备独立、空白、毫米制目标零件。重新 `nx_takeover`，取得该目标自己的凭据；用 `nx_inspect_part` 确认目标身份与空白状态。调用 `nx_v3_review_disk_source`，参数 `source_path` 为仍受保护的已审副本，核对返回 `group_count` 和 `output_id` 与第 3 步一致。
7. 从 `group_index: 0` 起按顺序调用 `nx_v3_review_disk_source` 取每组 `steps`。每组使用新的 `operation_id` 和当前目标的所有权、epoch、revision 调用 `nx_prepare_v3_composition`；取得返回的 plan 后调用 `nx_execute_plan`，再调用 `nx_verify_part`。排队或执行中用 `nx_get_operation` 查询，确认本组已应用、读回和非目标保全通过后，使用验证返回的新 revision 继续下一组。不是所有工具返回 `SUCCEEDED` 都足以表示验证通过；检查对应结果和证据。任何 FAILED、UNKNOWN、超时、身份不符或验证不完整时停止，不自动重放或归还。
8. 确认目标是一个实体后，调用 `nx_save_copy`，指定新的绝对 `.prt` 路径和 `reopen: true`。确认保存、重开及表达式、几何、历史和关联检查通过；该操作会更换所有权和 epoch，后续 `nx_return` 必须使用返回的新凭据。再按项目验证程序检查整件几何、参数编辑和独立保存重开；操作级成功不替代这些证据。

## 导出 UG11 便携包

在有项目证据的 MCP 服务端调用 `nx_v3_export_reviewed_ug11`，传入已审独立副本的绝对 `source_path` 和不存在的绝对 `output_path`。输出目录的父目录必须存在；若目标已存在则拒绝覆盖。成功状态是 `generated_only`，不是 NX 验收。将完整包复制到目标机器后，运行不需要开发工作区、源 PRT、MCP 或 NX2506；需要包内 `README.md` 所列 Python 和已验证 UG11 配置。

在包目录运行预检，示例路径按实际安装位置替换：

```powershell
$env:UGII_LANG = 'simpl_chinese'
.\Run-Bundle.ps1 -NxInstallDir 'C:\Siemens\NX11' -OutputDir 'C:\ug11-result'
```

预检通过、明确授权原生运行后，使用同一命令并追加 `-Execute`。新输出目录不得已存在，遵循包内说明检查 `native-evidence.tsv`、状态和日志；失败或结果不明不能直接复用同一输出目录。参数覆盖及生成步骤见包内 `README.md`；104 个驱动的数学窗口不是对每一种组合的原生验证。

## 已有参数化构造的不同尺寸保存件

调用 `nx_v3_start_parametric_file_analysis`，传入唯一 `operation_id`、现有本地绝对 `.prt` `source_path`、父目录已存在且自身不存在的绝对 `output_path`，以及明确授权 `authorize: true`。该操作由产品启动一个独立的空白 NX 批处理；它不读取或接管已打开的 GUI 零件，也不接受调用者上传的观察 JSON。监督器保留源文件和新建副本的只读锁，使用共享 NX 进程互斥、GUI 可执行文件锁、已审 NX2506.1700 / NXOpen 2506.0.0.0 版本检查及既有防火墙配置检查，再由固定的产品 Journal 采集两次样本、检查单实体、毫米单位、无跨零件依赖和前后未修改，关闭而不保存，并由产品内部分类。

例如开始任务：

```json
{"operation_id":"family-read-001","source_path":"C:\\work\\parametric-source.prt","output_path":"C:\\work\\family-evidence-001","authorize":true}
```

调用 `nx_v3_get_parametric_file_analysis` 并传入 `{"operation_id":"family-read-001"}` 查询持久状态。`STARTING` / `RUNNING` 只是最后记录，不能证明监督器健康；`UNKNOWN` 时停止并调查，不重试或清除互斥标记。`SUCCEEDED` 返回 `family_plan`、当前观察的驱动值和推断的覆盖值；它标记为 `recognized_candidate`、`execution_approved: false`，其构造模板仍来自已审参考，不是完整现测的修剪几何。当前没有将该候选直接提交 NX2506 的受验收产品步骤；不同尺寸的最终几何和编辑行为需额外验证。某些原生读取可能使 NX 把零件标记为已修改；此路线对此停止，不把脏状态当成成功。已知不支持的输入只有在确认关闭且未保存、文件未变化时才返回 `REJECTED`；读取后出现脏状态或无法确认收尾时返回 `UNKNOWN`。

该批处理检查的是既有本机防火墙配置和 NX 进程互斥，不声称进行了外部可达性扫描；许可证所需连接按安装环境提供。输出目录记录副本、原始观察、网络预检及日志；原始观察不能作为外部输入重新冒充产品采集。
