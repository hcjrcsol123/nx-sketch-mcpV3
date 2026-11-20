# P3 首次原生补读观察

本记录只分析已落盘数据和源码，不操作 NX。实机原始证据为 `workspace/v3/p3/P3-NATIVE-02/native-01/detail-snapshot.json`、同目录 `detail-summary.json` 和 `detail-takeover.json`，以及 `workspace/v3/p3/P3-NATIVE-02/runtime-copy-record.json`。记录中的 tag、local identifier、session、PID 仅指这次运行，不是跨会话标识或后续操作凭据。

## 运行状态和证据边界

`detail-summary.json` 将本次记录标识为 `P3-DETAIL-54635234d12e46669ae97c5106e55816`，NX 进程 PID 16252；其文件为 `workspace/v3/p3/P3-NATIVE-02/reference-readonly.prt`，是工作副本，非原始测试件。请求匹配、曲线及曲面转换容差均为 0.001 mm；这些设置不是模型精度或形状验收公差。两面分别以面型、UF 类型、包围盒和边数匹配，各有一个候选；匹配依据不能单独证明几何等价。

快照记录 `is_modified_before=false`、`is_modified_after=true`，两次库存比较结果为不等；`read_consistency_fault=true`、`ok=false`、`ownership_state=UNKNOWN_FROZEN`、`writes_halted=true`。`guard_errors=[]`、`verification_sample_errors=[]` 不改变该结论。`detail-summary.json` 明确记录 return 未尝试、结果未解决，需人工检查。本次记录不能证明归还或安全收尾完成。

当前快照只持久化第一次 `inventory`，第二次仅留下错误列表和 `two_native_samples_equal=false`，没有完整第二份库存或字段级差异。因此证据只证明受限库存的序列化比较不等，不能识别哪个具体字段或对象不同；也不能判断模型几何发生了何种变化。revision 是 `cached_not_refreshed`，不能拿缓存值证明内容不变。未知状态下不得基于本记录继续 NX 调用、清理、重试、保存或自动归还；人工处置由唯一操作通道负责。

## 两个面的有限几何观察

下列只是 UNKNOWN 发生时已返回的诊断信息，不是已验证的全件计划或完整修剪面定义。两个原生面结果均为 `INCONCLUSIVE`、`geometry_details_complete=false`。两面 `uv_box_rc=0`、`topology_rc=0`、`topology_release_rc=0`，拓扑 states 为空；遍历中记录的 `geometry_rc` 和 `geometry_free_rc` 均为 0、各 states 为空。C3 的 `incomplete_observed=false` 仅表示其实现未遇到可识别的不完整情况；源码仍无条件标记完整修剪和独立验证未建立，不能解释为几何完整或副作用已排除。

| 请求 | 本次匹配 | 实际返回的底层几何 | 有限拓扑 |
| --- | --- | --- | --- |
| F0002 | tag 63148，UF 20，Swept | `EXTRUDE_GEOM`（206），方向 `(0,-1,0)`；generator 为 4 阶、7 控制点、非有理样条，带节点、齐次控制点和参数区间 `[0,1]` | 1 面、1 环、4 fin、4 边；边几何为 2 直线和 2 样条；每个 fin 返回样条几何。 |
| F0005 | tag 63151，UF 19，SurfaceOfRevolution | `TORUS_GEOM`（204），中心 `(0,-125.273479089,0)` mm，轴 `(0,1,0)`，主/次半径 11/2 mm，参考方向 `(0,0,1)` | 1 面、1 环、4 fin、4 边；4 边返回圆弧，4 fin 返回样条几何。 |

树中每面各有 8 个被遍历的顶点节点条目；这是树遍历次数，不能误写成 8 个不同顶点。fin 和边的有向子项及原始几何数据保存在原始 JSON 中，包含可能重复引用；本表不宣称已验证闭环、边界在面上、周期接缝处理或内域完整性。UF_BREP 映射配置包含 `BLEND_TO_BSURFACE` 和 `INTERSECTION_TO_SPLINE`；fin 样条不能仅凭返回类型推断必为原始未近似曲线。

F0002 的 `uv_box` 为 `[0.0778576066258845,0.922579242069922,-0.053,-0.0006053001755869801]`。generator 的部分节点为 `[0,0,0,0,0.07785760913846,0.5224881258948,0.9225792444503,1,1,1,1]`；完整数组在快照中。虽然部件单位记录为 mm，这些 UV 参数的量纲和与母线、三维长度的换算尚未单独核实，不能将 V 差直接称作 mm 挤出长度。

F0005 的 `uv_box` 为 `[π,2π,π/2,π]`。同一快照 `AskFaceData` 记录其 point 为 `(0,-124.273479089,0)` mm、轴 `(0,-1,0)`，与 `UF_BREP` 结果中心在 Y 方向相差 1 mm 且轴反向。轴线方向反向本身可能代表同一方向线；Y 差则不能忽略。本记录不假定是 API 语义、数据、坐标转换或实现哪一方造成，必须在允许的后续受控验证中独立核实；未解决前不能选一组作为已验证的重建参数。

## matrix_tag 与 dirty：已知和未知

F0005 返回的四个圆弧带三个本次会话 matrix tag（62814、62815、62832），其 `matrix_rc` 为 0。`C:/0sf/ug/UGOPEN/uf_brep_types.h:260` 起说明圆弧结构 `matrix_tag` 用于矩阵方向，`arc_center` 在该矩阵坐标系中；`C:/0sf/ug/UGOPEN/uf_csys.h:127` 起将 `UF_CSYS_ask_matrix_values` 描述为读取指定矩阵的值。`uf_csys.h:107` 起另有 `UF_CSYS_create_matrix` 创建矩阵的接口。

实际使用的 C3 源码为 `workspace/build/v3-p3-candidate-c3/ReferenceGeometryNative.cpp`，构建和直接字节复制记录分别在同目录 `native-build-record.txt` 和上述 runtime 复制记录中。可见圆弧序列化会读取 `g->geom.arc.matrix_tag`，调用 `UF_CSYS_ask_matrix_values`；源码未显式调用 `UF_CSYS_create_matrix` 或删除矩阵。原生 `UF_BREP_ask_geometry` 的文档描述堆分配与几何提取，但已检查的文档未说明返回的 matrix tag 必定预存、必定新建、调用后归谁所有或是否会使 part dirty。矩阵 tag 的存在、成功读取、非零值和相同 tag 重用均不能证明对象创建或持久化。`UF_BREP_free_geometry_data` 成功也只证明其记录的返回码为 0，不证明所有 NX 对象未创建或模型状态不变。

因此当前证据无法将 dirty 或库存不等归因于 `UF_BREP_ask_geometry`、matrix、`UF_CSYS_ask_matrix_values`、拓扑提取、库存读取或其他环节。不得删除这些 tag，也不能以假设的临时对象为由运行清理。需要供应商文档支持或后续安全隔离的阶段化诊断才可归因。

## 后续受限修复接口需求

在 UNKNOWN 已按项目规程人工解决之前，不安排实机复试。之后的修复应先限定为诊断与受限读取合同：

1. 保留**每一步前后** dirty、原生返回码、资源释放结果和可序列化库存，分别隔离初始库存、拓扑读取、各类几何读取、矩阵值读取、释放及最终库存；同时保存两份库存和字段级差异，而非仅存比较布尔。不得把本实验工作副本中观察到的 tag 删除当作清理策略。若任何一项状态突变、返回不确定或清理失败，立即冻结并保留证据。
2. 仅在项目授权的独立可丢弃工作副本和唯一通道上进行，预先明确所有权、可观察对象范围、异常处理和不保存退出条件；在来源和安全性未证明前，不能在参考件或当前冻结会话上执行。测试应覆盖单一几何类型/调用、无圆弧对照和带圆弧的最小对照，以限定因果，但仍不能单凭相关性确认内部创建机制。
3. 另行核实 F0005 两种返回的坐标语义与 F0002 UV 参数量纲，并用完整修剪域、转换误差、接缝和邻接处理做后续几何验证；无法解释时保持 INCONCLUSIVE。只读探针需要记录实际测量，不能用对目标结果的假设填补。
4. 读取数据为底层几何，不恢复 BREP 原特征历史。完整母线、控制点或环面本身不能唯一确定工程 driving 尺寸、同轴/等径关系、设计范围或操作顺序；这些关系必须由可验证规则或设计意图确认。仅将母线控制点冻结也不能称为全参数设计。

## 继续调查：UF 19 点与 UF 20 参数

本节是对上述已落盘记录的离线解读，保留前述观察和 UNKNOWN 时的原始处置记录；本节没有调用 NX、重做原生采集或重新检查 API 可用性。后续会话处置状态以技术负责人记录为准。

### F0005：中心与轴上一点

安装的 `C:/0sf/ug/UGOPEN/uf_modl.h:2393` 将 `AskFaceData` 的 UF 19 称为 `revolved (toroidal)`；对于 revolved，输出 `point` 的定义是轴上一点，对于 torus，文档写的是中心。F0005 的 `AskFaceData.point=(0,-124.273479089,0)` 和 `UF_BREP` 的中心 `(0,-125.273479089,0)` 位于同一 Y 轴上，轴向相反而轴线相同。**如果**该次 `AskFaceData` 采用 revolved 轴上一点的语义，1 mm 的轴向差异与同一轴线相容；但现有记录不能确认它实际采用了文档中哪个语义分支，不能仅凭数值将两种定义混同，或将该差异归因为几何修改。

`C:/0sf/ug/UGOPEN/uf_brep_types.h:421` 起将 `UF_BREP_torus_s.center` 明确定义为主中心；`uf_brep_types.h:591` 起的 union 和 `UF_BREP_geometry_s` 按 type 选择对应成员。C3 编译源 `workspace/build/v3-p3-candidate-c3/ReferenceGeometryNative.cpp` 在 `UF_BREP_TORUS_GEOM` 分支直接序列化 `g->geom.torus.center`、`axis`、`u0_ref_direc` 及主/次半径；这与编译所用安装头文件的成员布局和命名一致。已有源码检查未发现从其他 union 成员取值或把 `pt_on_axis` 误写为 torus center；这不构成对整个运行时 ABI、NX 内部实现或返回值精度的实证。

现有局部边界也支持但不单独证明 BREP 中心的解释。F0005 圆弧边 `63576` 半径为 2 mm，其两个记录顶点为 `(0,-123.273479089,-11)` 和 `(0,-125.273479089,-9)` mm；两点均距 `(0,-125.273479089,-11)` mm 为 2 mm，且与主半径 11 mm、主中心 Y 为 -125.273479089 mm 的一个截面相容。这是对两个端点和记录值的局部算术一致性检查，并非整个圆弧、修剪面或模型内容验证。圆弧结构的 `arc_center` 在矩阵坐标系，见 `uf_brep_types.h:260`；不得不经矩阵变换就把它当绝对坐标。

### F0002：fin 参数与空间长度

`C:/0sf/ug/UGOPEN/uf_brep_types.h:553` 起规定 BREP 挤出曲面的 V 从生成线起算，沿挤出方向为正，按部件单位表示；U 继承生成曲线参数。样条的阶数、节点、齐次控制点、活动区间定义见 `uf_brep_types.h:318`，其参数本身不能默认是 mm。`C:/0sf/ug/UGOPEN/uf_modl.h:2619` 的 `AskFaceUvMinmax` 返回该面的 UV 参数范围，但未在该段说明与 BREP 导出参数的关系。`uf_modl.h:2525` 起的 `AskFaceProps` 文档指出输入面参数未归一化；其具体尺度不能仅从这一点确定。

本次 `AskFaceUvMinmax` 的 V 范围为 `[-0.053,-0.0006053001755869801]`，差值为 `0.05239469982441302`，不是 0.05299。它是 UV 的包围范围，而非直接测得的修剪边长度。generator 的 7 个控制点的 Y 均为 -124 mm、挤出方向为 `(0,-1,0)`；在返回树中，fin `4272` 两个齐次控制点（权重为 1）的 `(u,v)` 为 `(0.9225792444475764,-0.0009177934150964018)`、`(0.9225792444475764,-0.053)`，其关联直线边 `63694` 的端点 Y 分别为 -123.08220658490359、-71 mm。算术上，两端均符合 **本次数据的局部关系** `Y(mm) = -124 - 1000×v`。另一个关联 fin `4276` 的 `v=-0.0014` 与边 `63620` 的端点 `Y=-122.6` mm 也符合这一关系。

这些成对观察支持该次 fin/面 UV 的 V 数值与以 mm 表达的空间长度存在 1000 倍尺度，但不能由此推出所有面、所有版本或全部 NX 参数一律采用米、mm 转换，也不能将其写为未经验证的全局转换规则。UV 矩形包含的值未必都在实际修剪面内。后续若安全验证，可对明确对应的参数点读取空间点与一阶导数，记录输入参数、单位、坐标系、选项和结果，并用多个独立对应点检验该局部比例；这些点验证映射的候选关系，仍不能独立证明整面或全部修剪域等价。
