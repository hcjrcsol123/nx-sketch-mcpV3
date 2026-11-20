# P4 原生误差与编辑域补充实证

默认件的 NX2506 建模表示及布尔偏差每向须在 0.00025 mm 内。已有 0.001 mm 整件目标继续适用。P3 默认源到数学构造的上界为 0.000859 mm，按两项上界相加证明整件目标时，留给 NX 的预算仍为 0.000141 mm。分区证明也可以逐区合成误差，前提是证明修剪边界及共享接口，且每区满足用户上限。允许编辑域沿用已有设计决定，其误差上限见修订 84。

## 默认整件与 P3 数学构造

实机采用已通过保存重开的 [NX2506 默认整件](../../../workspace/v3/p4/P4-20261118-17/fixture/full-result.prt)。每项读取或编辑使用独立副本及新 Journal。工作目录为本仓库根，使用安装的 `C:/0sf/ug/NXBIN/run_journal.exe` 和各脚本顶部所列输入环境变量。NX 入站阻断已在运行前核实。

| 检查 | 观察 | 覆盖范围 |
| --- | --- | --- |
| P3→NX | 142 个 P3 名义边界点分别查遍 218 个修剪面。NX 距离接口均返回 0 mm，按返回点坐标另算的最大点对距离约为 1.47×10⁻¹⁰ mm。 | 毛坯外表面、尾槽、22 个直翼及 22 个 roll 的两条翼侧、18 个头部环面区。只覆盖已测样点。见 [采样结果](../../../workspace/v3/p4/P4-BOUNDARY-20261118-01/result.json)。 |
| 距离灵敏度 | R9 圆柱截面设置已知正负径向偏移。0.000100、0.000141、±0.000250、0.000400 与 0.010000 mm 的控制点均读出对应距离。 | 确认该调用能区分两条控制预算附近的偏移。见 [校验结果](../../../workspace/v3/p4/P4-BOUNDARY-20261118-02/result.json)。 |
| NX→P3 | 从 218 个修剪面逐个采出一个经 NX UV 分类确认的内部点。在每个点沿面法向量两侧各偏移 0.000025 mm，用独立 P3 CSG 占据计算得到一内一外。 | 两侧计算采用二进制浮点并对 C5 截面使用圆弧和样条折线。该诊断覆盖每个面的一个内部点。见 [原生面采样](../../../workspace/v3/p4/P4-BOUNDARY-20261118-03/native-face-samples.json)、[反向样点夹逼](../../../workspace/v3/p4/P4-BOUNDARY-20261118-03/reverse-sample-brackets.json)。 |
| 内核边容差 | 562 条边均读回，最大核内边容差为 0.000005 mm。 | 这是 NX 模型公差属性。边界偏差仍按独立比较判定。见 [边容差](../../../workspace/v3/p4/P4-BOUNDARY-20261118-01/result.json)。 |

88 条 C5 原生 FIN 输入曲线全部按持久 ID 完整回读。把原生和 P3 名义曲线拆到共同节点分区后，用精确有理数 de Boor 求值及三次 Bernstein 控制点凸包，所得连续双向距离的保守上界为约 **1.661×10⁻¹⁴ mm**。参照是 P3 归档的二进制浮点默认极点和坐标帧。该证据适用于输入样条，曲面生成、修剪和求布尔仍需单独建立上界。见 [88 曲线原生回读](../../../workspace/v3/p4/P4-C5-BOUND-20261118-01/native-c5-profiles.json)、[有理数上界](../../../workspace/v3/p4/P4-C5-BOUND-20261118-01/c5-continuous-bound.json)。

## 尾槽区间与整件联动

固定其他输入为 P3 理想默认值时，有理数和开方外包围证明尾槽宽度 **4.9–5.1 mm** 内侧壁和中心出口分支保持。该区间为已证充分区间。核内再生检查覆盖以下确切编辑点，不能把两个联动点外推为一个组合区间。数学证明与候选评估见 [尾槽区间](../../../src/nx_sketch_mcp/v3/nx2506_slot_interval.py)、[联动候选评估](../../../src/nx_sketch_mcp/v3/nx2506_edit_domain.py)。

| 整件编辑点 | 实机结果 |
| --- | --- |
| 尾槽宽 4.9 mm | 拉伸界限为 −2.45/+2.45 mm，保留体积增大。见 [下端点](../../../workspace/v3/p4/P4-20261118-18/width-low-c2/result.json)。 |
| 尾槽宽 5.1 mm | 拉伸界限为 −2.55/+2.55 mm，保留体积减小。见 [上端点](../../../workspace/v3/p4/P4-20261118-18/width-high/result.json)。 |
| 尾槽宽 5.01 mm，F0002 P2 切向坐标增加 0.0001 mm | 槽限位为 −2.505/+2.505 mm，44 条对应样条均有内部控制点变化，两端控制点保持。见 [尾槽与 C5](../../../workspace/v3/p4/P4-20261118-18/coupled-tail-c5/result.json)。 |
| 共享轴径 24.3331 mm，口面 Y=17.0001 mm | Stock 半径读回 12.16655 mm，88 个 C5 外端点半径和 18 个头部裁剪限位随对应共享量更新。见 [轴径与口面](../../../workspace/v3/p4/P4-20261118-18/coupled-shaft-mouth/result.json)。 |

四个点均通过既有 P3 必要检查。NX 更新错误和实体一致性故障均为 0，每个终态为单实体，粗拓扑库存保持 218 面、562 边。默认保存件与各测试文件无保存改写。首次宽度下端点读取在任何写入前发现 Python UF 包装缺少一致性接口，保留失败日志。改用已安装的 libufun 导出接口后，从新副本通过。

四个额外角点覆盖以下局部联动候选框，全部通过整件再生。尾槽宽度为 4.9–5.1 mm，F0002 P2 切向坐标在默认值 1.2858096483109538 mm 的 ±0.0001 mm 内，其余输入固定。P1/P5 的端点消元在这个框中对 P2 保持仿射。两端点满足的仿射侧向及次序不等式和凸包上界可延伸到局部区间。尾槽与 C5 的材料作用区在固定毛坯下轴向分离。完整修剪域和所有联动参数仍需验证。见 [联动局部证明](../../../workspace/v3/p4/P4-20261118-19/local-domain-box.json)、[四角实机目录](../../../workspace/v3/p4/P4-20261118-19/)。

本轮定向离线测试为 8 项和 6 个子情形通过。原生运行已正常退出。

## 尚缺的放行证据

曲面片内部采样、反向样点夹逼和边容差尚未给出修剪曲面、交边和布尔产物的连续双向误差上界。有限整件再生样点也还没有覆盖所有已确认设计参数的连续值和组合范围。P4 保持受阻，默认整件及本轮证据留在本地，P5 未启动。


## P4 建模公差调整（C14）

2026-11-18 用户要求 P4 建模设置使用 0.00025 mm 距离公差和 0.01° 角度公差。在首个授权建模事务写入独立毫米零件，通过零件级 UF 回读验证设置和撤销。拉伸显式设置距离及角度公差，回转显式设置距离公差，截面使用指定角度，布尔显式设置距离公差。创建截面保留 0.0001 mm 的链与连接设置，保存重开后的实际截面距离为 0.00025 mm，链公差为 0.0001 或 0.0002375 mm。P4 配置按零件和相关原生特征应用。见 [撤销试验](../../../workspace/v3/p4/P4-TOLERANCE-PROBE-20261118-01/result.json)、[桥适配](../../../src/bridge/V3/CompositionAdapter.cs)、[特征创建](../../../src/bridge/V3/CompositionSolids.cs)。

C14 构建成功，21 项定向离线检查及 12 个子情形通过。相同 P3 构造重新执行 88 组授权事务，每组 fresh 记录的零件公差均正确。整件保存重开通过。另一独立新会话读回 41 个拉伸和 47 个回转的适用距离及角度公差，以及 87 个布尔的距离公差，没有读回不匹配。见 [隔离构建](../../../workspace/v3/p4/P4-TOLERANCE-NATIVE-20261118-01/build.log)、[重建摘要](../../../workspace/v3/p4/P4-TOLERANCE-NATIVE-20261118-01/native/summary.json)、[公差读回](../../../workspace/v3/p4/P4-TOLERANCE-NATIVE-20261118-01/reopen/tolerance-readback-02.json)。

新版整件具有 218 面、562 边。142 个 P3→NX 复测点最大点对距离为 1.4644361667980268×10⁻¹⁰ mm，最大无向切平面角差为 2.7555474961822617×10⁻⁹°。这是样点结果。尾槽宽 5.1 mm 与 F0002 P2 切向坐标 +0.0001 mm 的代表联动重新通过，44 条样条内部变化，两端保持，NX 更新错误数为 0。见 [新版整件](../../../workspace/v3/p4/P4-TOLERANCE-NATIVE-20261118-01/fixture/full-result.prt)、[距离与角差复测](../../../workspace/v3/p4/P4-TOLERANCE-NATIVE-20261118-01/reopen/boundary-and-angle.json)、[联动复测](../../../workspace/v3/p4/P4-TOLERANCE-NATIVE-20261118-01/edit-check/result.json)。

本轮完成设置与复验。连续修剪和布尔边界误差上界以及完整允许编辑域仍是 P4 放行条件。

## C14 有限边界预算复核

从同一 C14 保存件读取 218 个面、562 条边和 238 个闭环，分十类建立有限面对应。补齐了 20 个头部互补面的有向邻接环对应。按各组假设计算，原生偏差最大候选界为 **0.0000989954 mm**，再加 P3 界后的预算估算为 **0.0009579954 mm**。这两个数字仍为条件量。按二进制读回载体精确求交，12 个头部圆角与台阶连接点到任一精确交圈的最小间距下界为 **1.0535×10⁻⁷ mm**，与精确重合假设冲突。还需建立 NX 实际交边、修剪材料域及 P3 规范构造与浮点预览之间的连续对应。见 [条件预算及诊断](../../../workspace/v3/p4/P4-TRIM-20261118-03/conditional-budget-ledger.json)、[头部有向环](../../../workspace/v3/p4/P4-TRIM-20261118-03/head-directed-counterparts.json)。

在另一份 C14 副本上，使用 `C:/0sf/ug/NXBIN/run_journal.exe tests/v3/composition_cases/p4_native_tail_brep.py`，设置 `P4_BREP_SCOPE=all`、`P4_BREP_CURVE_TOL_MM=0.0000001` 重新读取 218 面。对导出的六条 A 环面与上圆角之间的样条，以有理数 Bernstein 控制界计算整条导出曲线到名义 R2.5 圆角载体的单向距离，最大上界 **2.761×10⁻⁷ mm**。边界转换误差、修剪后面域和反向距离仍需独立证据。见 [读取结果](../../../workspace/v3/p4/P4-TRIM-20261118-05/all-brep-tight.json)、[连续残差](../../../workspace/v3/p4/P4-TRIM-20261118-05/fillet-spline-residuals.json)。

修订 78 将这六条导出样条与 P3 的六条有限设计交边一一匹配。用单调投影、端点区间和解析根导数建立双向连续距离上界 **0.000001723 mm**，计算允许原生连接点与读回载体的精确交圈有偏差。随后从 C14 的另一独立副本直接调用 `UF_MODL_ask_curve_points` 读取原生边。NX 返回 875216 拒绝 0.0000001 mm 和 0.000001 mm 弦差，六边均接受 0.00001 mm，弦链端点与原生求值器回读端点一致。依据该接口文档的最大弦到曲线距离，**设计交边到原生边**的连续上界为 **0.000062893 mm**。相反方向、相邻有限面的填充及整件误差仍待证。两份模型副本均与 C14 默认件逐字节一致。见 [导出样条双向界](../../../workspace/v3/p4/P4-TRIM-20261118-05/fillet-finite-edge-bounds.json)、[原生边单向界](../../../workspace/v3/p4/P4-TRIM-20261118-07/canonical-to-original-edge-bounds.json)。

原生弦链在仓库根通过 `C:/0sf/ug/NXBIN/run_journal.exe tests/v3/composition_cases/p4_native_fillet_chords.py` 取得，`P4_BOUNDARY_PRT` 为本次独立副本，`P4_CHORD_OUTPUT` 为新的输出路径。两套界均由 `nx2506_head_trim.py` 对持久化的几何数据计算。

修订 79 按用户确认，设计边到 NX 原生边、NX 原生边到设计边两向的接受上限均为 **0.00025 mm**。用 `UF_FACET_tessellate_face` 对独立 C14 副本的上圆角面分面。NX 未报告分面错误，返回 12,748 个三角片。通过原生边的 12 个端点和闭环链顺序定位六条真实交边对应的分面边界。按 `uf_facet_tessellation.h` 的边界弦段与实体曲线段距离契约，采用 **0.00001 mm** 分面曲线误差。六条折线到对应 P3 设计边的连续双向最大上界为 **0.000103028 mm**。原生求值器在 5,248 个对应线段与曲线参数中点交叉核对，最大样点偏差约 **0.000004951 mm**。两项上界相加后，从原生边到设计边的反向上界为 **0.000113028 mm**，六边均通过。正向另有修订 78 的 **0.000062893 mm** 更紧上界。请求 0.000001 mm 分面误差时生成相同边界，采用经实机中点核对的 0.00001 mm。相邻修剪面的内部和整件布尔边界仍需验证。见 [原生分面与求值器检查](../../../workspace/v3/p4/P4-TRIM-20261118-10/native-fillet-facet-boundary.json)、[双向误差结果](../../../workspace/v3/p4/P4-TRIM-20261118-10/bidirectional-fillet-edge-bounds.json)。

实机命令从仓库根运行 `C:/0sf/ug/NXBIN/run_journal.exe tests/v3/composition_cases/p4_native_fillet_facets.py`，`P4_BOUNDARY_PRT` 指向独立 C14 副本，`P4_FACET_OUTPUT` 指向新输出。离线计算入口为 `nx2506_head_trim.assess_fillet_facet_boundary`。

## C14 完整修剪面分批验收

修订 80 至 81 累计验收 **25 个完整原生有限面**。每组以对应 P3 规范设计面为目标，计算双向连续距离。NX 原生模型以同一 C14 保存件的独立副本核对，读回物理特征用于识别不同会话的面。

| 验收范围 | 原生到设计双向上界 | 证据 |
| --- | --- | --- |
| 上部 R2.5 圆角完整面 | 0.000138772 mm | 两条原生修剪环经配对，六条交边的分面节点按原生边参数覆盖全边，域内和域外见证与 P3 相符。将边界连续移动到共同环面时，整个有限面以内外判定保持和最短角向路径得到双向上界。按 P3 全局 0.000859 mm 保守相加，此面的总界约 0.000997772 mm。见 [完整圆角面界](../../../workspace/v3/p4/P4-TRIM-20261118-11/upper-fillet-finite-patch.json)、[NX 边界参数和域内外见证](../../../workspace/v3/p4/P4-TRIM-20261118-11/native-fillet-facet-boundary.json)。 |
| 下部四个轴向面 | 8.264×10⁻¹³ mm | R31 球冠、下台阶环面、下圆角和 R40 带使用完整原生圆环、域内外见证和子午线连续匹配。补计精确下圆角半径和 R40 相切站位的预览偏差。见 [四面误差界](../../../workspace/v3/p4/P4-TRIM-20261118-12/lower-axial-head-finite-patches.json)。 |
| 轴身十二个普通环带 | 5.964×10⁻¹³ mm | 十二面均由两个完整原生圆环和 NX 域内外分类确定。本批对 P3 保留的输入和工程尺寸公式做有向区间求值，补齐其规范构造与浮点预览的传递。见 [十二面误差界](../../../workspace/v3/p4/P4-TRIM-20261118-13/stock-ordinary-finite-bands.json)。 |
| 尾槽切面与尾端保留面，共四面 | 0.000079293 mm | 提取原生五条相交边的有序分面折线，二阶导数界与连续端点匹配上界覆盖折线之间的整段。其他边继承原生直线及圆弧。四面域内外见证均通过。本组首算误用了肩部锥斜率的倒数，按 P3 的正切关系修正后复算。见 [四面误差界](../../../workspace/v3/p4/P4-TRIM-20261118-14/tail-four-finite-patches.json)、[保留的首次分析](../../../workspace/v3/p4/P4-TRIM-20261118-14/initial-analysis-invalid-cone-slope.json)。 |
| 尾槽相邻轴身四面 | 0.000026529 mm | 复用已验收的五条相交边和原生圆弧，四面原生域内与去料位置分类均正确。在同一圆锥或圆柱上用角向和子午方向的连续路径填充边界移动范围。见 [相邻四面误差界](../../../workspace/v3/p4/P4-TRIM-20261118-15/tail-adjacent-stock-finite-patches.json)。 |

原生检查在仓库根用 `C:/0sf/ug/NXBIN/run_journal.exe` 串行执行五个 Journal。每次使用 `P4_BOUNDARY_PRT` 指向该次独立副本，输出路径和 stock 输入为对应运行目录内的 JSON。上圆角使用 `p4_native_fillet_facets.py` 和 `P4_FACET_OUTPUT`。下部四面使用 `p4_native_axial_head_anchors.py` 和 `P4_AXIAL_OUTPUT`。普通轴身面使用 `p4_native_stock_band_anchors.py`、`P4_STOCK_ANCHOR_SPEC` 和 `P4_STOCK_ANCHOR_OUTPUT`。尾槽使用 `p4_native_tail_facets.py` 和 `P4_TAIL_FACET_OUTPUT`。尾槽相邻轴身面使用 `p4_native_tail_stock_anchors.py` 和 `P4_TAIL_STOCK_ANCHOR_OUTPUT`。五个读回均正常退出，副本逐字节与原 C14 一致。齿侧及其余头部有限面、整件布尔界及完整编辑域待验收。

## C14 编辑联动复验

固定其余驱动量时，用原始 C5 端点矩阵和有理区间验证两侧 **12 个控制坐标各 ±0.00001 mm**、**4 个连接角各 ±0.000001 rad**、尾槽宽 **4.9–5.1 mm** 可同时变化的理想区间。验证范围为截面不等式、22 槽相互分离、s7/s8 首次出口和保留体连通性。该区间是本轮选择的充分候选范围。NX 验证以下离散编辑点，剩余的原生连续范围和其他工程驱动量仍待放行。见 [区间输出](../../../workspace/v3/p4/P4-C5-DOMAIN-20261118-01/ideal-admission.json)。

- 四个连接角各测上下端点，共 8 点。每次对应 44 条 FIN 的指定端移动，另一端保持。首次试验将 NX 面类型变化视为失败。保留首次记录，复验将面类型改为记录项，以原生更新、单实体一致性、表达式读回和曲线响应判定。见 [首次记录](../../../workspace/v3/p4/P4-ANGLE-DOMAIN-20261118-01/F0002_alpha_root_rad-0/result.json)、[八点复验](../../../workspace/v3/p4/P4-ANGLE-DOMAIN-20261118-02/)。
- 12 个控制坐标各单独测正端点，另测全低及全高两个组合点，共 14 点。单独编辑时同侧 44 条 FIN 的内部点变化，两端和另一侧保持。组合编辑时两侧 88 条曲线更新，尾槽上下限随宽度更新。全部符合区间内这些点的预期响应。见 [输入与结果](../../../workspace/v3/p4/P4-C5-DOMAIN-20261118-01/)。
- 六个头部周向区域各测一个联动点，分别改动本区轴向角、A 环面主/次半径和两侧 B 环面管半径。每次实机回读三套轴及母线半径、中心高度和 A 区两条裁剪接缝；整件更新零错误、单实体一致性通过。见 [六区输入与结果](../../../workspace/v3/p4/P4-HEAD-DOMAIN-20261118-01/)。
- 在固定 stock 与头部的条件下，尾槽四驱动的理想区间为宽 **4.9–5.1 mm**、半径 **37.49–37.51 mm**、轴心 Y **−162.61 至 −162.59 mm**、轴心 Z **41.99–42.01 mm**。有理区间证明保留中心及侧壁出口的顺序，无再次切入，并与 16 个齿侧驱动区间相容。新增 5 个通过的 NX 点，包括半径/轴心坐标各自的正端点、20 驱动的全低及全高组合。回读两条原生圆弧的半径与轴心、对称拉伸限位，以及组合中 88 条 FIN 的联动。见 [区间输出](../../../workspace/v3/p4/P4-SLOT-DOMAIN-20261118-01/ideal-admission.json)、[五点结果](../../../workspace/v3/p4/P4-SLOT-DOMAIN-20261118-01/)。

运行从仓库根使用 `C:/0sf/ug/NXBIN/run_journal.exe tests/v3/composition_cases/p4_edit_probe.py`，`P4_EDIT_CASE` 指向各自的独立 C14 副本目录。各通过结果确认磁盘副本保持原样。离线通过 `PYTHONPATH=src` 下的 `python -B -m unittest discover -s tests/v3 -p test_nx2506_edit_domain.py` 和同命令的 `test_nx2506_slot_interval.py`，共 16 项通过。

## C14 默认整件和完整驱动清单（修订 82）

继承此前 25 个面，本轮逐面补齐剩余 193 个。验收记录按同一 C14 原生读取的面身份保存，各面记录闭环、对应设计对象、两向上界和值的证据链接。重复载体按各自的原始有限面登记，例如 22 个 `stock.s7` 面和六个同载体的球面。见 [218 面与整件布尔台账](../../../workspace/v3/p4/P4-ACCEPTANCE-20261119/per-face-and-boolean.json)。

| 本轮验收范围 | 面数 | 最高双向上界 |
| --- | --- | --- |
| C5 直拉伸齿侧 | 44 | 0.000024001 mm。原生锥相交边的有序分面以 Bernstein 多项式计算连续同图偏差，验证内部片与外部位置。见 [44 面](../../../workspace/v3/p4/P4-TRIM-20261119-01/verified-straight-finite-patches.json)。 |
| 直段和滚转齿根 | 44 | 直段 0.000018929 mm，滚转 0.000082087 mm。下圆弧、原生交边和 s8 唯一出口连续对应。见 [直段 22 面](../../../workspace/v3/p4/P4-TRIM-20261119-02/verified-straight-root-finite-patches.json)、[滚转 22 面](../../../workspace/v3/p4/P4-TRIM-20261119-03/verified-roll-root-finite-patches.json)。 |
| C5 滚转齿侧 | 44 | 0.000136379 mm。按共享 s7/s8 站位分相匹配全部原生退出边，并验证有限域。见 [44 面](../../../workspace/v3/p4/P4-TRIM-20261119-04/verified-roll-flank-finite-patches.json)。 |
| s6、s7 和 s8 轴身保留面 | 24 | 0.000136393 mm。共享各 C5 实边，逐个匹配闭环、外侧环和原生保留域。见 [s6 整面](../../../workspace/v3/p4/P4-ACCEPTANCE-20261119/verified-s6-stock-face.json)、[s7/s8 其余 23 面](../../../workspace/v3/p4/P4-TRIM-20261119-05/verified-s7-s8-finite-faces.json)。 |
| 头部 A/B 条带 | 18 | 0.000117435 mm。相切边使用原始圆弧，并直接用球面交边的解析高度和完整分面段约束弦线。在首次原生采集后保留 3 个有效面，续采其余 15 面。见 [18 面](../../../workspace/v3/p4/P4-TRIM-20261119-07/verified-head-ribbon-finite-faces.json)。 |
| 头部余下含口面 | 19 | 0.000083817 mm。对原生球、锥、台阶和口圈补齐有限闭环、共享原生边与内侧见证。见 [19 面](../../../workspace/v3/p4/P4-TRIM-20261119-08/verified-head-complement-finite-faces.json)。 |

默认 NX2506 布尔边界与 P3 规范边界按完整有限面并集取上界。正向和反向均为 **0.000138772 mm**，低于用户每向 0.00025 mm 上限。与 P3 已接受的源到规范上界 0.000859 mm 保守相加，参考整件到 C14 的双向上界为 **0.000997772 mm**，低于 0.001 mm。默认件的 88 组事务、原生保存重开及公差回读直接继承，另使用同一保存件的 562 条双向共享实边、238 个闭环与 218 个材料侧样点。所有 Journal 使用隔离副本和现有 NX 入站阻断，按原证据命令串行执行。

编辑证据对应 **104 个原批准独立驱动量**，各项均有独立的 C14 实机编辑通过记录。轴身 29 项做两端点和全低、全高组合共 60 次，均通过实机更新、22 条原生轮廓及相关部件检查。头部、C5 与尾槽保留既有逐项证据，并补齐头部独立输入、三项 C5 共享输入、全组合点及 C14 尾槽宽度两个单项端点。选取的范围登记在逐驱动量台账，含单位、原生表达式、单项及组合的实机记录。数学区间已覆盖理想尾槽出口、随轴径联动的齿侧旋转出口、头部构造帽和保留侧、头部与轴身的共享口面。见 [逐驱动量验收](../../../workspace/v3/p4/P4-ACCEPTANCE-20261119/per-driver-edit-domain.json)。

头部全低失效定位到上圆角相切端点的开方式，数学零项在 NX 求值时误保留旧值，母线端点偏差约 0.000075 mm，更新仍返回零错误。编译器将上下两个相切端点直接绑定到各圆角主半径。修正后的头部全低与全高，以及全 104 驱动的全低、全高和一组混合点，在独立副本中通过。公式在验证副本的内存会话中应用，原 C14 保存件用于默认几何验收。更新后的代码用 `test_nx2506_composition.py` 检查两项绑定。见 [旧值回读](../../../workspace/v3/p4/P4-EDIT-REMAINING-20261119-03/head-combination-low/result.json)、[组合复测](../../../workspace/v3/p4/P4-EDIT-JOINT-20261119-01/)。

完整原生允许域仍待验收。有限实机点及理想连续区间已通过上述各自范围的检查，任意区间内组合的原生修剪和整件布尔误差尚未取得覆盖全域的界。V3 执行候选仍未放行，P5 未启动。

## 编辑区间数学证明与完整原生点证据（修订 83）

本轮对 104 维联合区间补齐头部 A/B 条带有限事件、真实头部与轴身的全高度包含关系。理想区间内，头部圆角和口面事件、B 区球面与锥面事件均有唯一根与顺序界，头部全区与轴身有正间隙。联合证明继承轴身、尾槽、齿侧滚转和共享接口证据。已验证全低、全高的理想输入属于这组证明窗口，并验证越界宽度及直接赋值派生口面均拒绝。见 [理想联合区间](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/joint-ideal-edit-window.json)。

全低、全高、混合及一组全部位于区间内部的非对称输入，分别在 NX2506 中另存、重开。从原生读取完整有限面、闭环及材料侧，逐个与该编辑值的 P3 设计对应。四件都通过 218 个有限面对照。最大全件双向上界为 **0.000231636 mm**，低于每向 0.00025 mm。这里的参照是编辑后的设计，默认件对参考零件的 0.001 mm 验收沿用修订 82。见 [四个完整模型汇总](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/assessment.json)、[区间内部组合逐面记录](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/interior-brep/complete-edited-boolean-evidence.json)。

编辑后 NX 齿根载体含有理三次表示。通过正权重齐次圆方程残差、分段 Bernstein 包围和横向坐标单调性，验证该表示与对应编辑设计一致，再分别检查原生直段、滚转、轴身、尾槽和头部有限裁剪。默认账本中五个无界头部 B 环面标签改用此前已有的物理有限角色，几何上界保持其原验收值。全低首次读取原生曲线转换时，s8 达到原生输出上限，后续用已保存的同一件按 0.001 mm 读回原生载体及闭环，有限边界另用原生分面契约和解析比较。换档仅作用于读取转换的表示精度。区间内组合的 NX 齿根挤出方向读回了长度微小舍入的严格轴向向量。按原几何等价规范化该向量后，从已保存的 BREP 继续比对，整件上界为 0.000210337 mm。见 [逐次取证脚本](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/run_edited_case.ps1)、[逐件完整结果目录](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/)。

本阶段仍要求完整原生编辑区间的验收。联合数学区间与原生完整点的界已单独登记，尚无能够把这些点的原生误差上界扩展到整个组合区间的 NX 区间保证。现有 NX 读回接口和分面契约绑定具体已生成的模型。P4 仍未整体放行。

## 完整编辑区间的双向误差上限（修订 84）

对 104 个独立驱动量允许区间内的每个组合，使用该组合对应的 P3 设计作为参照。原生有限修剪面和整件布尔边界的 NX 到 P3、P3 到 NX 两个方向分别以 **0.0004 mm** 为上限，两个方向的上界合计须 **≤ 0.0008 mm**。默认件保持每向 0.00025 mm，原参考件到默认件的整件目标保持 0.001 mm。NX 建模距离和角度保持 0.00025 mm、0.01°。

按新口径复用四个完整编辑件的逐面证据。每向最高上界小于 **0.000231636 mm**，合计小于 **0.000463272 mm**，四个组合均满足要求。验收余项为整个区间内的原生误差界。NX2506 本地 `Features_BooleanBuilder.hxx` 的 `Tolerance1` 定义给出公差设置和读回，`uf_facet_tessellation.h` 的距离契约覆盖具体实体与其分面。现有证据仍缺这类构造在区间任意组合下从关联更新到最终布尔边界的统一误差保证。见 [四个完整模型与误差上限](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/assessment.json)。

在仓库根目录设置 `$env:PYTHONPATH='src'` 后，运行 `python -m unittest discover -s tests/v3 -p test_nx2506_edit_domain.py -v` 和 `python -m unittest discover -s tests/v3 -p test_nx2506_composition.py -v`，分别通过 15 项和 8 项。另用已有证据离线核对四组 218 面汇总，确认等于限值可通过，超过限值的下一浮点表示被拒绝。保留原始实机证据文件。

## 齿根滚转面与 s8 的理想交边全区间稳定性（修订 85）

四组既有编辑件中，轴身 s8 的最大误差上界均由相邻齿根滚转面的有限域界主导。每件的 22 条对应原生交边都是 `UF_BREP_EDGE_INTERSECTION`。NX2506 本地 `uf_brep_types.h` 将该边类型描述为由两相交载体隐式定义。该分类来自四个实际结果的回读。

对已接受的 104 维理想参数窗口，以 `v = Y + 71 mm` 为轴向坐标，取横向 `|t| ≤ 0.52 mm`。对 `v ∈ [2.48, 3.02] mm` 分 32 个有理端点子区间做有向区间计算。两端的径向间隙 `G` 分别严格为负和为正，`dG/dv ≥ 0.5466885`，所以每个横向位置均有唯一理想出口。同一横向位置的三维路径速度至多为 1.8。若同图内比较点的径向间隙残差上界为 ε，则沿理想载体修正到交点的三维距离至多为 `1.8ε / 0.5466885`。见 [计算脚本](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/uniform_ideal_root_exit.py)、[区间证据](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/uniform-ideal-root-exit-bound.json)。

对保持该隐式交边类型、同一裁剪分支且在相同 `t` 下完整对应的原生输出，若齿根载体在相同 `(t, v)` 下的位置误差为 `e_root`，s8 在相同轴向 `v` 下的径向误差为 `e_s8`，则径向间隙残差至多为 `e_root + e_s8`。在原生环及理想环有双向覆盖的前提下，沿对应载体所得交边误差界为 `e_root + 1.8(e_root + e_s8)/0.5466885`。仍需建立 NX 更新在完整窗口内保持这些交边、载体及分支对应的证据，并收齐其余有限面和布尔边界的统一误差界。

作为误差预算核对，即使把建模距离公差 0.00025 mm 当作该径向间隙残差的假定上界，使用上述换算得到的交点移动上界也约为 0.000823138 mm。要用此式将交点移动界控制到 0.0004 mm 以内，可用的残差界最多约为 0.000121486 mm，其他几何误差需另计。这个预算来自区间导数计算，NX 建模公差回读只记录设置值。

## 修正圆角公式的产品建模与保存后编辑（修订 86）

当前编译器生成的 88 组、2016 个步骤与原 C14 的事务输入相比，只有上下两个圆角端点的公式不同。使用 NX2506.1700、既有 C14 桥和隔离的毫米空白件，在仓库根执行 `python -B tests/v3/composition_cases/run_native_once.py workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119 --case full --save --evidence native-corrected`。88 组事务均通过执行和 fresh 读回，表达式、几何、历史、关联的保存重开检查均为 `VERIFIED`。两个新公式在重开后分别为 `v3_head_lower_fillet_major` 和 `v3_head_upper_fillet_major`，对应默认值 24.083189157584592 mm 和 30 mm，与原默认值一致。初次接管前尚无工作件，打开专用夹具后以新的接管结果运行。最终 `HUMAN_OWNED` 并正常退出。见 [运行摘要](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/native-corrected/summary.json)、[重开核验](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/native-corrected/2991-response.json)、[退出记录](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/shutdown.json)。

使用新保存件的独立副本，在设置 `P4_EDIT_CASE` 后用 `C:/0sf/ug/NXBIN/run_journal.exe tests/v3/composition_cases/p4_edit_probe.py` 执行此前的 52 个头部驱动全低输入。用保存件里的公式直接更新。NX 更新错误数为 0，单实体无一致性故障，218 面、562 边，副本原始字节完整。被核对的轴向母线端点和圆弧定义最大读回差约 0.0000000804 mm。该值覆盖本次母线核对。见 [新件直接编辑证据](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/head-low-reopened/result.json)。

按持久标识比较两个默认件的保存重开记录，419 条构造曲线定义逐条一致，表达式默认读值、实体体积及包围盒相同。另用 `run_journal.exe` 执行 `default-brep-compare/export_default_bodies.py`，通过 `UF_PS_export_data` 对两个独立副本各导出一个原生实体，去除文本换行后仍存在记录差异。仅在旧 C14 副本更新两条公式并另存重开后，导出正文同样存在差异。原 C14 的整件几何证书继续适用于原验收件，新件需另做有限面与整件误差复核。三个 Journal 串行运行且正常退出。见 [新旧导出对照](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/default-brep-compare/comparison.json)、[旧件副本公式迁移](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/default-formula-migration/comparison.json)。

## 新版默认件有限面复核（修订 87）

用 `p4_native_tail_brep.py` 和 `p4_native_fillet_facets.py` 分别采集新版默认件独立副本的 BREP 及上圆角分面，两次 Journal 均正常退出。仓库根设置 `$env:PYTHONPATH='src'`，执行 `python -B workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/default-finite-validation/verify_upper_fillet.py`。在新版实际有向环和原生材料域见证的基础上，上圆角完整有限面的双向误差上界均为 **0.00013877198722851017 mm**，加上 P3 界后约 **0.000997772 mm**，该面通过。见 [上圆角原生证据和验收](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/default-finite-validation/upper-fillet-finite-patch.json)。

同一目录执行 `python -B workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/default-finite-validation/compare_nominal_trims.py`，复用这次 BREP 和原 C14 完整证据。218 个对应载体的几何定义及方向逐条一致。18 面的所有边都是原生直线或圆弧，旧新记录的完整有限边、端点、有向环和载体一致。在原生定向有效实体的条件下沿用原 C14 的对应有限面证书。含重新复核的上圆角，新版已覆盖 19 面。另有 8 面的边读回记录存在差异。隐式交边的样条转换结果只能作为定位线索，对应裁剪分支及材料域仍需连续证据。见 [逐面对照及继承证书](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/default-finite-validation/analytic-trim-transfer.json)。

## 新版默认件整件布尔验收（修订 89）

在仓库根运行 `C:/0sf/ug/NXBIN/run_journal.exe workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/default-finite-validation/collect_remaining_faces.py`。同一个已核对有效入站防护的 NX2506 会话读入新版独立保存副本，完成头部、齿侧和齿根、轴身和尾槽的剩余原生取证，副本字节一致，Journal 正常退出。然后设置 `$env:PYTHONPATH='src'`，依次执行该证据目录下的 `head-delta/verify_full_head.py`、`shaft/verify_shaft_facets.py`、`stock-tail/verify_stock_tail.py` 和 `assemble_corrected_default.py`。见 [采集记录](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/default-finite-validation/native-batch-summary.json)。

完备证书覆盖新版默认件的 218 个有限面、562 条共享边、238 个闭环。16 个面沿用原 C14 的解析有限面界，上圆角沿用修订 87 对新版的独立结果，剩余面使用本次原生采集。NX 到 P3 及 P3 到 NX 的整件布尔边界误差上界各为 **0.00013877198722851017 mm**，与已验收的 P3 源误差合成后，参考到新版默认件的上界为 **0.0009977719872285103 mm**。新版默认件通过。连续 104 维组合区间内的原生误差上界仍待证。见 [新版默认件逐面与整件证书](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/default-finite-validation/corrected-default-boolean-bound.json)。

## 当前编译公式的联合区间定义域（修订 90）

仓库根设置 `$env:PYTHONPATH='src'`，执行 `python -B workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/compiled_formula_window.py`。复用 104 个独立驱动的实证映射，直接消费 `compile_associative_preview` 当前生成的公式。以精确实数语义和有向区间算术计算，1841 条表达式均有定义，74 个平方根被开方数非负，83 个除法分母的绝对值下界超过 0.5773484，8 个正切调用的余弦绝对值下界超过 0.4999989。全部 2296 个三角调用直接消费弧度表达式。NX 浮点求值误差、原生载体与有限裁剪及布尔结果的全区间上界仍待证。见 [公式证明产物](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/compiled-formula-window.json)。

## 公式舍入及 s8 载体扰动界（修订 91）

用户确认带符号偏差范围为 −0.0004 mm 至 +0.0004 mm，含端点。几何两方向仍以各自的非负最大距离作为上界，每向不超过 0.0004 mm，合计不超过 0.0008 mm。

在仓库根设置 `$env:PYTHONPATH='src'`，依次执行连续编辑证据目录中的 `compiled_formula_roundoff.py` 和 `s8_meridian_condition.py`。前者对 1841 条当前编译表达式逐层传播全区间数值误差，假定 binary64 最近值舍入、三角函数误差不超过 1 ulp、求值顺序及弧度单位保持。长度最大绝对误差上界小于 7.676×10⁻¹³ mm，角度小于 1.005×10⁻¹⁵ rad。后者结合编译输入的径向和轴向三点求圆方程，证明全区间内的小扰动不会导致这三个点共线。在精确三点圆弧及固定 Y 轴回转假设下，未裁剪 s8 载体整体上界小于 5.781×10⁻¹⁰ mm。见 [编译舍入界](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/compiled-formula-roundoff.json)、[三点圆弧载体界](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/s8-meridian-condition.json)。

本机 NX 文档规定 `UF_BREP_make_body` 需要调用方提供拓扑和几何，创建过程可能重求交边、调整顶点以及设置容差。`UF_BREP_heal_body` 的上限约束针对实体修复检查。`UF_MODL_compare_topology` 的面比较依赖分面及顶点距离，模型比较的 `max_deviation` 按采样点计算。上述接口可用于具体模型验证。覆盖整个 104 维组合区间的 NX 原生误差仍需证明，包括当前的求值合同、载体和裁剪分支及布尔保留域。默认件的已验收结果直接沿用。

## 接口查询及新版编辑验证入口修复（修订 92）

NX2506 的 `DSE_ContinuousDesignVariableBuilder` 接受变量上下限，`DSE_DesignFillBuilder.NumberOfDesigns` 和 `DSE_OptimizationStudy.RunEvaluateOnly` 填充和评估有限设计集。零件族及用户定义模板也保存具体实例和取值规则。`UF_UDOBJ_register_update_cb` 可在符合关联条件的 UDO 更新时查询当次模型。`NXOpen.GeometricAnalysis.DeviationChecking.Check` 依赖指定几何对象及检查点。见 [设计空间采样声明](C:/0sf/ug/UGOPEN/NXOpen/DSE_DesignFillBuilder.hxx:62)、[更新回调](C:/0sf/ug/UGOPEN/uf_udobj.h:637)、[偏差检查说明](C:/0sf/ug/NXBIN/managed/NXOpen.xml:623604)。

通过只读程序集元数据确认，已安装 Parasolid 37.01.180 的 `BODY.boolean_2` 接收目标实体、刀具和选项，选项具有 `default_tol` 和 `max_tol` 字段。`SESSION.ask_precision` 读取会话精度。`BODY.compare`、`EDGE.find_deviation_2` 和 `TOPOL.range` 接收已存在的实体、边或拓扑对象。`range` 的参数限制适用于这些已存在的几何。可访问的厂商公开 SDK 页面介绍建模、比较及开发资料。详细支持参考入口要求登录或授权。当前可核实的接口范围仍缺整个关联编辑区间的原生误差保证。见 [Siemens Parasolid SDK](https://www.siemens.com/en-us/products/plm-components/parasolid/)。

新版默认件已保存两个修正圆角公式。编辑复验入口 `run_edited_case.ps1` 改用该验收件创建独立副本，`prepare_edited_case.py` 只准备实际驱动编辑及几何核对数据。原有 `ResumeSavedBrep` 行为保留。离线核对 104 项输入、三组几何数据和 PowerShell 语法通过。

仓库根执行 `workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/run_edited_case.ps1`，参数 `-DriverValues` 指向同目录 `corrected-native-mixed-driver-values.json`，`-RunName corrected-native-mixed-brep`。104 个值都严格位于已证明的窗口内，NX 原生更新错误数和实体一致性故障数均为零。保存、重开及 218 个完整有限面对照通过，每向原生误差上界为 **0.0002470398765667749 mm**，合计 **0.0004940797531335498 mm**。有效入站阻断记录、最新版源件的独立副本和完整证书保留在案例目录。全区间验收仍待证。见 [本次完整验证](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/corrected-native-mixed-brep/complete-edited-boolean-evidence.json)、[五组汇总](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/assessment.json)。

## P4 阶段验收（修订 93）

用户确认按具体原生编辑件逐件验收，NX 连续全区间误差上界免验。已证明的 104 维理想区间继续作为编辑输入范围。完整原生连续域记录为 `unverified`。逐件仍核对对应编辑后的 P3 设计，每向误差不超过 0.0004 mm，两向上界合计不超过 0.0008 mm。见 [更新后的逐件验收汇总](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/assessment.json)。

T18 通过。104 个独立驱动量均有原生单项编辑记录，5 个实际组合的原生有限面和整件误差均通过。由新版默认件出发的完整案例覆盖 104 个驱动和 218 个有限面，每向上界为 **0.0002470398765667749 mm**，两向合计为 **0.0004940797531335498 mm**。见 [逐驱动证据](../../../workspace/v3/p4/P4-ACCEPTANCE-20261119/per-driver-edit-domain.json)、[新版编辑件证书](../../../workspace/v3/p4/P4-EDIT-CONTINUITY-20261119/corrected-native-mixed-brep/complete-edited-boolean-evidence.json)。

T20 通过。新版默认件经 88 组原生授权事务创建，逐组 fresh 核验通过，表达式、几何、历史及关联的保存重开检查均通过。整件 218 面及布尔边界相对 P3 的每向上界为 **0.00013877198722851017 mm**，与原参考件比较的整件上界为 **0.0009977719872285103 mm**。操作已安全归还并正常退出。见 [实机构造摘要](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/native-corrected/summary.json)、[新版默认件几何证书](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/default-finite-validation/corrected-default-boolean-bound.json)、[退出记录](../../../workspace/v3/p4/P4-HEAD-ALIAS-NATIVE-20261119/shutdown.json)。

按阶段规则使用现有证据完成一次独立高级出口评审，评审接受逐件范围，TL 接收，P4 标记 `DONE`。既有授权事务及静态证书的 `execution_approved=false` 继续适用。工作停在 P4。
