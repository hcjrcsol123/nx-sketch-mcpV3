# P3 参考几何读取接口调查

日期：2026-11-08。性质：技术调查记录，不是阶段状态、验收或交接记录。调查只读取已有 P1 证据、源码、已安装 NX2506 头文件和托管程序集；未启动 NX、运行实机采集、写参考件、执行 Git 或计算 hash。除明确标示的 P1 已有实测和离线反射结果外，下列接口行为来自安装文件的文档或项目源码，尚未对本样件验证。

## 已继承的实际证据与候选

P1 证据为 `workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json` 及其同目录 summary、takeover 记录；范围和安全边界见 `docs/v3/capability-map.md`。该次记录选中 1 个 solid body、1 个 BREP，235 面、622 边；源 STEP、保存版本及原始特征历史未知。235 面的 `SolidFaceType` 与 `AskFaceData` UF 类型分组为：Planar/22 13、Cylindrical/16 56、Conical/17 16、Spherical/18 10、SurfaceOfRevolution/19 96、Swept/20 44。快照明确标示 `geometry_details_complete=false`：没有完整修剪曲面和完整边曲线定义。记录内 tag 和 JournalIdentifier 只在当时会话和 revision 范围内有效，后续会话须重新定位，不能复用。

实际球面数据中，中心 `(0,0,0)` mm、半径 32 mm 有 6 面；中心 `(0,4,0)` mm、半径 40 mm 有 2 面；中心 `(0,0,0)` mm、半径 31 mm 有 2 面。它们是解析底层球面候选，并不证明完整球体、修剪范围或半径是否共享驱动参数。

举例：P1 会话面 `63148` 为 UF 20，邻接边类型为 2 Linear、2 Spline，其盒在 Y 方向约为 -123.0822066 至 -71 mm。它适合作为线性挤出候选的补读目标；包围盒和边类型不能证明母线、方向、修剪域或设计特征。面 `63150` 为 UF 19，邻接 2 Intersection、1 Spline、1 Circular，轴和盒不足以复原母线或修剪环。面 `63151` 为 UF 19，四条邻边均为 Circular，`AskFaceData` 记录轴 `(0,-1,0)`、点 `(0,-124.273479089,0)` mm，半径字段 11 和 2 mm；这是待核实的环面候选，不可把所有 UF 19 都认作环面。数值是记录中的底层数据，不是已经确认的设计尺寸。

JournalIdentifier 中的三个坐标不能代替完整曲线。有限点、有限 UV 采样、面积或包围盒也不构成对整个修剪面的形状证明。

## 已安装接口与限制

以下路径均为本机安装文件：

- `C:/0sf/ug/UGOPEN/uf_modl.h:2393` 的 `UF_MODL_ask_face_data` 按面型提供解析信息；类型 19 为 revolved (toroidal)、20 为 extruded。其盒只包含面，不保证最小。`uf_modl.h:2619` 的 `UF_MODL_ask_face_uv_minmax` 返回 UV 四个极值，不包含面内孔洞和修剪环。
- `C:/0sf/ug/UGOPEN/uf_modl.h:2767` 的 `UF_MODL_ask_face_torus_type` 可查询环面类型；类型常量在 `uf_modl_types.h:116` 起。托管签名见 `C:/0sf/ug/NXBIN/managed/NXOpen.UF.xml:30385`。对确认是环面的情况，结合 `AskFaceData` 可描述底层解析环面，但仍缺实际修剪域。
- `C:/0sf/ug/UGOPEN/uf_modl.h:2857` 的 `UF_MODL_ask_face_edges` 给出关联边；`uf_modl.h:2898` 的 `UF_MODL_ask_face_loops` 给出环及其边，原生返回链表须用 `UF_MODL_delete_loop_list` 释放。在安装的托管 XML 中未找到 `AskFaceLoops`，不能假定现有 C# 包装可调用。只有无序边集合或 UV 矩形不足以确定环的顺序、方向、周期接缝和内孔。
- `C:/0sf/ug/UGOPEN/uf_evalsf.h:9` 起描述曲面评估接口；`Initialize2`/evaluate 可求点和导数，但不直接返回完整母线。已有 `src/bridge/F12BodyGeometrySnapshot.cs` 采 5×5 UV 点；它只在 `Face.FaceType.Parametric` 时调用 `AskBsurf`，有限采样不是完整曲面证明。其边 evaluator 支持线、圆弧、椭圆、样条及样条控制点和节点读取，但对不受支持的边会失败，不能预设本件 622 条均完整可取。
- `C:/0sf/ug/UGOPEN/uf_modl_bsurf.h:500` 起说明 `UF_MODL_ask_bsurf` 仅对 PARAMETRIC 和 OFFSET 面有效，不能直接假定可读取本件 UF 19/20 面。已安装 `UF_MODL_ask_revolution` 接收回转**特征** ID（`uf_modl_sweep.h:1549`），不能从只剩 BREP 的 P1 历史恢复原特征；安装头文件检索未找到针对 face 的 AskFaceSweep 母线查询。

### 受容差转换的二维修剪曲面

`C:/0sf/ug/UGOPEN/uf_modl_bsurf.h:535` 起记载 `UF_MODL_ask_2dtrim_bsurf` 支持所有面型，接收转换选项与容差，输出 B-surface、环数、每环边数、边方向及二维修剪曲线 ID。托管签名为 `NXOpen.UF.UFModl.Ask2dtrimBsurf(NXOpen.Tag, System.Int32[], System.Double, NXOpen.UF.UFModl.Bsurface@, System.Int32@, System.Int32[]@, System.Int32[]@, NXOpen.Tag[]@)`，见 `C:/0sf/ug/NXBIN/managed/NXOpen.UF.xml:29121`。B-surface 的阶数、有理标志、节点、齐次控制点等结构见 `uf_modl_types.h:273`；原生文档要求以 `UF_MODL_free_bsurf_data` 释放。

同一头文件明确：输出的 `edge_bcurves` 为临时曲线 tag，**所有临时曲线必须先删除再释放数组**。因此若本次调用返回非空曲线，不能把它视作仅分配堆数据的纯读取；但文档不能证明某个特定面的返回必然非空。失败时部分输出、清理和 dirty 影响均未实测。该接口不符合当前 P1 参考件的纯只读采集合同。可在授权的隔离、可丢弃工作副本上单独评估：记录本体和 dirty 前后状态，逐一检查临时对象、释放和异常路径，失败隔离，验证所有权后不保存退出。不得把这一备选方法描述为已验证安全，亦不得静默修改源件。

即使转换成功，得到的是指定容差下的转换 B 面及修剪数据；容差不是已证实的整面比较误差，也不恢复原生历史和工程参数。不能把所有非解析曲面转换为固定控制点，再称为全参数设计。

## UF_BREP 原生候选路线

安装头文件 `C:/0sf/ug/UGOPEN/uf_brep.h:22` 起说明，`UF_BREP_ask_topology` 和 `UF_BREP_ask_geometry` 分别提取拓扑树和原始几何；按面提取的协议见 `uf_brep.h:160` 起。`uf_brep_types.h:535` 起定义 `UF_BREP_revolve_s`：轴上一点、轴方向及完整 generator 几何；`uf_brep_types.h:553` 起定义 `UF_BREP_extrude_s`：挤出方向及 generator 几何。枚举还包括 `TORUS_GEOM`、`SPHERE_GEOM` 和 B-surface。`uf_brep.h:560` 起说明环内边/fin 的方向；`uf_brep_types.h:760` 起说明有向子项、环顺序及邻接。对无直接 NX tag 的 fin/vertex 可使用文档所述标识，但其作用域仍需记录。

`uf_brep.h:459` 起明确：blend 面、intersection 边、tolerant 边没有直接对应的可用几何类型，可能需要近似；`uf_brep_types.h:894` 起要求至少提供 BLEND→BSURFACE 和 INTERSECTION→SPLINE 的映射，并显式提供相应曲线/曲面容差。耐差边既有 SP 曲线的精度由形成时确定，缩小本次读取容差不会提高它。周期面、接缝、奇点与 SP 曲线的对应、展平选项及可能的分面均有约束；应保留输入选项、原类型、转换类型、状态和容差，不能把转换当精确原定义。

原生资源规则：`UF_BREP_ask_geometry` 的数据用 `UF_BREP_free_geometry_data` 释放，返回 states 用 `UF_free`，`UF_BREP_ask_topology` 的树用 `UF_BREP_release_topology` 释放；异常和部分成功时也须有可验证的清理路径。读取拓扑与读取几何之间不得更改该体拓扑。不能因为文档描述了提取接口，就宣称本机调用对 dirty、模型内容或资源必然无影响；这些要在受控实机上核查。

托管可用性：`C:/0sf/ug/NXBIN/managed/NXOpen.UF.xml:5130` 起列有 `UFBrep` 和部分类型，但未列 `UFBrep` 方法。离线在 Windows PowerShell/.NET Framework 加载安装的两个程序集并反射 `Public, Instance, DeclaredOnly`，结果无方法输出；没有连接或启动 NX。可复现最小命令（输出为空表示该反射范围没有方法）：

```powershell
powershell.exe -NoProfile -Command '[System.Reflection.Assembly]::LoadFrom("C:\0sf\ug\NXBIN\managed\NXOpen.dll") | Out-Null; $a = [System.Reflection.Assembly]::LoadFrom("C:\0sf\ug\NXBIN\managed\NXOpen.UF.dll"); $a.GetType("NXOpen.UF.UFBrep").GetMethods([System.Reflection.BindingFlags]"Public,Instance,DeclaredOnly") | ForEach-Object { $_.ToString() }'
```

这只证明检查的托管类型/方法范围；不证明 C 原生 DLL、ABI、许可和运行时可用。候选实现需受控原生 C helper 或经核实 ABI、结构布局和资源管理的 P/Invoke，不能直接宣称 `UFSession.Brep` 已提供这些方法。

## 最小可验证子项

建议在 P3 内先限定一个原生读取原型及离线合同：对重新定位到 P1 候选 `63148` 的 UF 20 面，以及 `63151` 的 UF 19 面，分别采集面拓扑和几何、环/fin/边的方向及必要曲线定义；保留来源、单位、UV 范围、实际原生类型、完整 generator 数据或环面定义、转换标志、容差、所有状态和未读取字段。预期可能读到 EXTRUDE、REVOLVE 或 TORUS，但必须按实际返回分支；不支持、歧义、转换失败、资源清理失败或状态不可解释时输出 UNKNOWN/INCONCLUSIVE，不以预期类型覆盖结果。

离线测试应覆盖非线性母线、非圆环回转面、变截面反例、周期接缝和内环、转换/部分读取错误及资源释放；之后仅在授权的唯一实机通道验证目标面能否取回、来源能否重新对应、前后模型状态及清理。完整修剪曲面比较应明确容差、误差方法和不确定性；有限采样只能作为诊断，不能单独证明整个域等价。一个面或一次读取成功不能关闭所有 44 个 UF 20、96 个 UF 19 和 10 个球面缺口，也不证明 F13/F21 的组合、参数编辑或双版本支持。

即使完整 BREP 读取成功，原特征顺序、独立/关联尺寸、对称/阵列、相同半径是否为设计关系，以及可接受编辑范围仍不能由形状唯一推出。必须保留歧义与未解释区域，必要时请求设计意图确认；P3 对应区域计划应明确来源、候选操作、参数关系、开放项及后续验证门禁。
