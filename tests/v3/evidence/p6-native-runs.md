# P6 分项实机记录

日期为 2026-11-19，时区 Asia/Shanghai。以下命令均从仓库根目录 C:\0sf\1PROJECT\AI\design\nx-sketch-mcp 执行。TL 独占实机队列，每次启动器在新的 PowerShell 进程内运行。P6 采用已保存的默认模型，输入和运行结果保存在项目私有工作区。

## 库存和全域边界

库存运行以 tests/外球叉.prt、workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/fixture/full-result.prt、workspace/v3/p5/FULL-03/blank.prt 为输入。启动器将三件分别复制为独立目录内的 reference.prt、nx2506.prt、ug11.prt，持有源件的只读句柄，并在退出后核对输入副本字节。NX2506 每次只打开一件，读取后不保存关闭。三个选体均为唯一有效毫米实体，参考件 235 面/622 边，两结果件各 218 面/562 边。通常包围盒及质量属性为诊断量。[库存原始记录](../../../workspace/v3/p6/NATIVE-INVENTORY-01/observations.json) [库存运行起止与保全](../../../workspace/v3/p6/NATIVE-INVENTORY-01/observe-claim.txt)

~~~powershell
pwsh -NoProfile -File tests/v3/run_p6_nx2506.ps1 -RunName NATIVE-INVENTORY-01 -Journal tests/v3/geometry/p6_native_inventory.py -Mode Inventory
pwsh -NoProfile -File tests/v3/run_p6_nx2506.ps1 -RunName T26-UG11-01 -Journal tests/v3/composition_cases/p4_native_tail_brep.py -Mode Brep
~~~

第二条命令将 FULL-03/blank.prt 复制到 workspace/v3/p6/T26-UG11-01/edited-full.prt。NX2506 在该副本上采集全部 218 面，所有原生探针正常返回，启动器退出后再次核对与锁定源件的字节。之后每个分组均读这个副本；从相同 BREP 对照 P3 默认计划生成该组的定位规格。[BREP 来源与运行后保全](../../../workspace/v3/p6/T26-UG11-01/observe-claim.txt) [规格及区域算法](../../../workspace/v3/p6/T26/说明.md)

下表保留 TL 实际调用和返回顺序。命令共用前缀为 pwsh -NoProfile -File tests/v3/geometry/t26_run_groups.ps1 -Directory workspace/v3/p6/T26-UG11-01。多组调用通过 PowerShell 的 -Command 参数传递数组。各组保留自己的网络策略观察、原始输出和日记日志。包装在原生调用前后检查独立副本与 FULL-03 的字节，拒绝覆盖已有采集，并检查进程退出和采集结果。NX2506 网络记录限定于已配置的 ugraf 入站规则；UG11 使用其启动器的有效入站策略、双栈端口占用及交互程序独占检查。

| 调用参数 | 实际采集 | 结果与复用 |
| --- | --- | --- |
| 首次使用默认全部组 | root | 已完整采集 44 面。首次离线旧比较器缺默认 pitch_radius_mm，补读参数后又发现实际圆柱/圆环没有旧旋转面 generator 字段。保留首败，改用适合实际解析类型的既有有限域方法，在原始读回上通过 |
| -Groups head-axial,tail,head | head-axial、tail | 前 4 面通过。尾部原生输出完整，离线旧比较器缺默认 slot.width，队列在此停止。后以 P3 四项默认槽参数在同份数据上证明 8 面 |
| -Groups head | head 的 ribbon 和 complement | 两次新进程读同一副本，38 面离线通过，包装退出 0 |
| -Groups flank | 直翼与滚翼 | 运行时规格 edited-flank-face-specs.json，原生输出 native-edited-flank-facets.json。使用当时包装的 P4 离线分派，44+44 面通过，退出 0。P6 随后对每行按 0.000141 mm 余量复核 |
| -Groups stock-bands | 12 个轴身带区 | P6 适配器输出 within_limit，退出 0 |
| -Groups stock-interfaces | s6、s7、s8 接口 | P6 适配器结合同一件的根面、翼面及带区证据，输出 PASS，退出 0 |

所有分组的采集目录均为 workspace/v3/p6/T26-UG11-01。齿翼采集命令对应的原生 Journal 为 tests/v3/composition_cases/p4_native_c5_straight_facets.py，启动环境 P4_BOUNDARY_PRT 指向上述 edited-full.prt，P4_STRAIGHT_KIND=edited_flank，P4_STRAIGHT_SPECS 与 P4_STRAIGHT_OUTPUT 均指向该目录表列文件。每个跨会话读回重新用物理几何定位，标签只用于当次 BREP 内的对应。本索引于运行后按 TL 的调用与输出汇编。包装的离线验证分派随适配完善，未保存每次分派脚本的逐版快照。[分组程序](../geometry/t26_run_groups.ps1) [三段全件界](../../../workspace/v3/p6/T26-UG11-01/three-link-bounds-r2.json)

## 编辑、持久性与失败

T28 两版都在新目录编辑 5.0→5.1 mm 槽宽，保存后退出，再启动新进程测量。参考路径、P1 基准副本及该版本默认件来源在两次运行期间均通过子进程验证拒绝读取。NX2506 编辑和重开之间脚本增补了 dirty 与重开后磁盘比较，只按各次实测字段验收。[两版运行命令与原始记录](../persistence_independence/T28-evidence-and-protocol.md)

T27-UG11-CONSUMERS-01 在 C# Journal 编译时因 HashSet 缺少引用而退出，模型入口未执行。02 在修改内存副本后遇到诊断断言，原本要求 max 包络的不活动支路也产生非零几何位移。退出后独立核对，唯一 PRT 和锁定基线逐字节相同，程序未调用模型保存。保留 02 原始失败，单独审查新的 03 用例，所有会话对象从新副本取得。[T27 用例、运行及结果审计命令](../parameter_edit_cases/README.md) [失败现场](../../../workspace/v3/p6/T27-UG11-CONSUMERS-02/) [独立复核](p6-independent-review.md)


03 的 Journal 与启动器均正常完成，实际 104 项编辑均恢复，五个组合分别核对 1,546 对关系。实际运行的 Journal、清单和原生输出保留在此编号下，重开读回后明确不保存关闭；启动器报告复制件与基线逐字节相同。单位及已编译参数窗口按记录独立审计。[逐项与组合汇总](../../../workspace/v3/p6/T27-UG11-CONSUMERS-03/assessment.json) [104 项原生单位](../../../workspace/v3/p6/T27-UG11-CONSUMERS-03/driver-unit-audit.json) [退出与保全](../../../workspace/v3/p6/T27-UG11-CONSUMERS-03/claim.txt)