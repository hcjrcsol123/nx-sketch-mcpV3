# P1 实机参考件读取证据索引

- 实机证据 ID：`P1-REFERENCE-7812d302a165453badcd339473b5dba3`；日期 2026-11-08，Asia/Shanghai；工作目录 `C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`。
- 配置标识 `C4` 是团队手工标识，不是文件或模型 hash。CLR 四个候选制品来自 `workspace/build/v3-p1-candidate`，复制至本次隔离目录 `workspace/v3/p1/P1-20261108-01/isolated/runtime`；NX 入口为该目录下 `M2Entry.dll`，隔离启动目录为 `isolated/profile/startup`。Python 为本次工作区的 `src/nx_sketch_mcp`；NX 读取到的版本为 `v2506.0.0.1700`，NXOpen 版本 `2506.0.0.0`；PID 7712，客户端配置超时 120 s。该标签不单独证明所用文件内容的唯一身份。
- root 先以 `tools/start-nx-global.ps1 -Config <isolated/mcp-config.json> -NxExe C:\0sf\ug\NXBIN\ugraf.exe -StartupDirectory <isolated/profile/startup> -AsJson` 启动单个隔离 NX，随后使用以下命令。第一次运行时 `native` 目标目录尚不存在，参数检查退出，未调用 NX；root 创建目录后以完全相同命令执行第二次，退出码 0，用时 1.8535 s。这是唯一一次正式实机参考件读取，没有超时重放。

```powershell
python -B tests/v3/run_reference_once.py --pid 7712 --part 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p1\P1-20261108-01\reference-readonly.prt' --config 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p1\P1-20261108-01\isolated\mcp-config.json' --evidence-dir 'C:\0sf\1PROJECT\AI\design\nx-sketch-mcp\workspace\v3\p1\P1-20261108-01\native'
```

实机调用次序为 takeover、一次 `nx_inspect_reference`（该次读取内部的两份原生采样用于一致性比较）、只读 bridge status、return。结果为 `HUMAN_OWNED`；之后正常关闭该 NX 窗口，未保存、未强杀。窗口退出和余留既有 helper 的情况见 [关闭记录](../../../workspace/v3/p1/P1-20261108-01/shutdown-record.json)。

- [takeover 原始记录](../../../workspace/v3/p1/P1-20261108-01/native/p1-reference-takeover.json)：独立副本完整加载；毫米；一个 BREP 特征，0 草图；该阶段 dirty `false → false`。
- [参考库存原始记录](../../../workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json)：1 个 solid body，选体已解决；235 个面、622 条边，面到边及边到面的字段均已返回；未知面标签列表为空。两份原生采样在所报告字段范围内相等，读前后 dirty `false → false`；库存、复核采样和守卫错误列表均为空。`inventory_complete=true` 是该接口的库存采集结论；`geometry_details_complete=false`，裁剪曲面和完整边几何未包含。
- [结果摘要](../../../workspace/v3/p1/P1-20261108-01/native/p1-reference-summary.json)：`inspection=complete`、`return=HUMAN_OWNED`。该次快照的来源及保存时 NX release 为 unknown；UF 值 36 是零件历史计数而非 NX 软件版本。revision 为 `cached_not_refreshed`，样本相等不证明完整几何或全模型没有变化；标识仅在当前会话和 revision 范围使用。
- [源件保全](../../../workspace/v3/p1/P1-20261108-01/source-preservation.json)：证据 ID `P1-SOURCE-PRESERVATION-001`；关闭后原件和工作副本分别与读取前留存副本直接逐字节相等，原件修改时间未变，未计算摘要。该记录只覆盖磁盘内容，dirty 使用上述两段原生记录。复制前基线见 [复制记录](../../../workspace/v3/p1/P1-20261108-01/source-copy-record.json)。

此记录只覆盖本机一次授权副本读取；多实体歧义、未知面或故障注入不由该次实机样件证明。客户端 UNKNOWN 测试与假适配器拒绝/冻结证据另见同目录 P1 离线测试记录。工程意图、完整几何定义及源 STEP 均未由此结果确认。
