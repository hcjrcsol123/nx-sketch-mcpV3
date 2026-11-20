# P5 T21–T24 独立评审

## 最终结论

**T21、T22、T23、T24 在本轮真实计划、受限操作和已记录的 NX11 环境内独立评审接受。三项首轮发现均已关闭，无阻断项。** 接受依据是 FULL-03 的已完成检查点和 FULL-03-CLOSE-01 对同一保存件的专门收尾复验；FULL-03 原始运行保留失败状态。T21 后槽四项修改和 T23 轴径、C5 控制点的直接编辑有原生几何读回。T22 验证了 41 次实际拉伸和槽宽限位传播，T24 验证完整的操作和输入消费映射及受限布尔。详见[整件冻结记录](../../../workspace/v3/p5/FULL-03/native-evidence.tsv)和[收尾复验](../../../workspace/v3/p5/FULL-03-CLOSE-01/native-evidence.tsv)。

**收尾与版本等价。** FULL-03-CLOSE-01 使用专门 schema，在空白 UG11 会话中打开启动器锁定源件后生成的新副本。重开核验前 dirty=False，核验后 dirty=True；共用收尾函数对保存字节进行比较、明确无保存关闭、检查 Work/Display 均空并再次逐字节比较。启动器离开 runner 后再把副本与仍处于只读锁定状态的源文件逐字节对照，两次检查均通过，码 0、无残余受控进程、唯一终态 PASS。独立评审在项目根用 `compiler.lower_plan` 和 `render_journal(..., verify_edits=True)` 原位生成文本作只读比较：冻结 FULL-03 Journal 与当前模板展开的全部构造、编辑及首次保存文本相同；逐行差异仅在原 Journal 14837 至 14839 的关闭/重开/最终关闭三行及新增的收尾函数。三份 Journal 的 `CheckReopen` 文本相同，修正后主 Journal 与收尾复验的 `Ug11ReadOnlyClose` 类文本相同。评审未启动 NX，也未重复执行分项测试。[收尾 claim](../../../workspace/v3/p5/FULL-03-CLOSE-01/claim.txt)；[复验 Journal](../../../workspace/v3/p5/FULL-03-CLOSE-01/journal.cs)；[原整件 Journal](../../../workspace/v3/p5/FULL-03/journal.cs)

**保留边界。** 218 面、562 边是该 UG11 默认保存件及重开的库存。完整 UG11 与参考的几何误差、104 项逐参数及组合的系统验证和独立环境持久性仍属于 P6。当前整件样条编辑实证覆盖首成员两项输入截面，尾槽四项编辑在整件上完成。其他安装版本、正式打包及产品入口均未由本次实证覆盖；T30 保持待接手。[阶段验收](../../../docs/V3-stage-handoff.md)

## 首轮发现

1. **高，输入依据可自我比对。** 首版 `lower_plan` 使用调用者指定的根目录读取基线，通常正是待编译计划本身，且仅比较指定顶层字段。源 `stock_revolve` 的角度或轴若在该文件被更改，P4 的受限实现仍构造 Y 轴、360° 回转。撤销意图确认或将 `readiness_checks.within_target` 置为 false 也可绕过顶层比较。关闭条件为实际输入对独立受控依据的内容或语义核对，并提供上述变更的拒绝证据。[编译器](../../../src/nx_sketch_mcp/v3/ug11/compiler.py)；[P4 默认构造](../../../src/nx_sketch_mcp/v3/nx2506_composition.py)
2. **高，编辑及草图的整合验收可出现误判。** 首版 Journal 对编辑完成后的点和表达式做相互对照，未比较编辑指令目标与独立的原生前后值，也未核实后槽草图是实际拉伸的父特征。编译后槽特例未调用已有双半圆校验。关闭条件为核实圆草图对原截面的适用性、真实拉伸选用草图、直接编辑前后实际尺寸或几何的变化，以及关联限位或回转输入的传播。[Journal](../../../src/nx_sketch_mcp/v3/ug11/journal_template.cs)；[草图绑定](../../../src/nx_sketch_mcp/v3/ug11/templates/SketchBinding.cs)
3. **高，保存重开检查会拒绝正确模型。** 首版 `CheckReopen` 预期 `v3_` 前缀表达式数为 E.Count，但后槽构造在 E 外创建了 `v3_ug11_slot_y_distance`。关闭条件为按名比较期望和观察到的驱动及辅助表达式，并核对相关 RHS，随后采集原生重开记录。[Journal](../../../src/nx_sketch_mcp/v3/ug11/journal_template.cs)；[后槽构造](../../../src/nx_sketch_mcp/v3/ug11/templates/SketchBinding.cs)

## 后槽原生证据 T21-02

独立检查了原始 TSV、运行 claim、随运行冻结的 Journal 和 manifest。NX V11.0、NXOpen 11.0.0.33、简体中文空白会话中，圆心两向及半径由三项 Driving 约束控制，求解状态 WellConstrained、自由度 0。圆截面进入实际有限拉伸。独立改变槽宽 5→5.1 mm、圆心 Y −162.6→−162.61 mm、圆心 Z 42→42.01 mm、半径 37.5→37.51 mm，分别更新、观察并恢复。宽度改变时读取两端限位，另外三项读取实际圆心和圆半径。保存、关闭、重开和最终关闭均完成，特征标识与 8 个工程表达式已核对。运行记录包含活动 Public 网络配置、两栈端口独占、映像独占、退出码 0 和唯一终态 PASS。[实机流水](../../../workspace/v3/p5/T21-02/native-evidence.tsv)；[原生断言](../../../workspace/v3/p5/T21-02/journal.cs)；[启动及退出](../../../workspace/v3/p5/T21-02/claim.txt)

此夹具仅包含后槽，重开核对范围是实体数、特征标识和上述工程表达式；原生草图父子关系、重开后的尺寸状态和其余样条/轴/布尔需结合整件运行读回。T21-01 因 NX Journal 编译时的 System.Core 引用报错结束，未创建零件，保留首次尝试记录。[首次运行](../../../workspace/v3/p5/T21-01/claim.txt)

## 源输入与运行失败复核

- 首轮发现 1 的根因已在编译器改正。固定证据根后，先使用 P3 组装器从独立上游数据重建，再完整比较候选和基线。定向反例覆盖 stock 轴、删除节点、清空确认、关闭几何就绪及仅替换被读取基线。源计划包含的相同节点不要求原生 1:1 建特征；每个数学节点与每个实际非表达式步骤都经过映射闭合检查。[编译器](../../../src/nx_sketch_mcp/v3/ug11/compiler.py)；[定向反例](../test_ug11_compiler.py)；[操作映射](../../../src/nx_sketch_mcp/v3/ug11/operation_map.py)
- T24 已有从 104 项独立量（86 个毫米、18 个弧度）对应到命名表达式、量纲、公式依赖及实体消费特征的静态检查，默认编译也会执行。T24 的映射在提交原生几何验收前仍保持 `execution_approved=false`。[驱动溯源](../../../src/nx_sketch_mcp/v3/ug11/driver_map.py)；[整件产物](../../../workspace/v3/p5/FULL-02/manifest.json)
- FULL-01 在首个弧度表达式报 NX 3520016。UNITS-01 独立读出安装名称 `Radian`，以 0.523598775598299 rad 计算出基本量 30°、正弦 0.5。FULL-02 使用修正名称通过该表达式节点，在第一个成员上的拉伸生成后，严格样条使用者断言拦截运行。该次没有保存整件。核验须有等价的原生间接消费者证据，且应对直接编辑后的实际极点或曲线作比较。[FULL-01](../../../workspace/v3/p5/FULL-01/native-evidence.tsv)；[UNITS-01](../../../workspace/v3/p5/UNITS-01/native-evidence.tsv)；[FULL-02](../../../workspace/v3/p5/FULL-02/native-evidence.tsv)

## 整件 FULL-03 的实证边界

冻结 manifest 显示 161 个源节点全部映射至 175 个原生实体特征，包含 41 次有限拉伸、47 次回转和 87 次布尔；另有 1841 条表达式，合计 2016 个构造步骤。冻结 TSV 中有 175 个实体特征回执。源参数全部进入驱动表。圆草图和实体截面消费、关联曲线的点与表达式链、Studio Spline 实际极点和原始基函数对应的节点矢量，均在此次执行代码中受检查。[映射](../../../workspace/v3/p5/FULL-03/manifest.json)；[冻结 Journal](../../../workspace/v3/p5/FULL-03/journal.cs)

六个原生编辑检查点完成。轴径从 24.333 改到 24.3331 mm 时，回转的截面、轴向、整周扫角及实际圆柱半径通过读回。F0002 的 P2 横向坐标直接编辑后，首成员直拉伸和回转的输入样条最大极点位移均为 0.0000091560876864588461 mm，原生 Section 再次选中同一曲线；恢复后逐极点核对。轴径和 C5 在相应构造节点后编辑后恢复；四个槽参数在整件构造后编辑后恢复。保存和关闭成功，重开得到相同的 218 面、562 边、一个实体、特征/轮廓标识及声明表达式，重新定位的槽尺寸及其拉伸父子关系通过。[原始记录](../../../workspace/v3/p5/FULL-03/native-evidence.tsv)

**FULL-03 最终状态为失败。** `final_close begin` 后，重开核验后的零件 dirty 触发门禁。无 `final_close complete` 或终态 PASS；批处理已经退出。第一个导致 dirty 的 API 未由该运行定位。关闭此项可取原保存件的独立副本，用同一修正后的关闭逻辑验证无保存关闭、会话清空、退出以及磁盘字节保全。此前已完成的构造、编辑和重开检查可逐项复用。[运行 claim](../../../workspace/v3/p5/FULL-03/claim.txt)

## 审查对象及验收口径

- T21 核对样件原生草图、基准、Driving 尺寸及使用者。共享表达式点、轮廓曲线和样条须进入实际拉伸或回转。直接编辑应产生可定位的原生几何响应。P2 块体仅覆盖其自身的矩形草图。[开发清单](../../../docs/V3-development-checklist.md#d-ug11-后端与独立验收)
- T22/T23 核对有限拉伸的方向和两端限位、回转轴与两角、完整 Section 与目标实体。原生回读应覆盖实际构造所需的轴向位置与尺寸传播。实例所需独立布尔归 T24 验收。[P4 关联编译器](../../../src/nx_sketch_mcp/v3/nx2506_composition.py)
- T24 核对源计划 235 个面责任、161 个节点、14 类数学操作的显式映射，以及共享参数和 104 项可编辑输入。头部载体可在有限块实现内共同消费，原生特征数以实际构造为准。未知操作、无法表示的源语义、缺少使用者和失效的运行证据均须在其归属门禁处拒绝。[P3 最终计划](../../../workspace/v3/p3/P3-FINAL-PLAN-01/final-plan.json)；[P4 驱动账](../../../workspace/v3/p4/P4-ACCEPTANCE-20261119/per-driver-edit-domain.json)
- 执行结论以实际 UG11 身份、空白会话、独立输出、NX 回读及失败收尾记录为据。对照已有 P4 证据，记录分项原生结果的边界。双端整件几何与逐参数系统矩阵留在 P6，产品正式入口首次交付链在 P7。[阶段验收](../../../docs/V3-stage-handoff.md#4-七阶段唯一归属与接续条件)
