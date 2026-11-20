# F0123 root-exit C3 独立审查

2026-11-12；独立高级审查实例 `p3_exit_review`，与 SI 实施实例分离。仅 P3。本文件由审查者独占；未修改实现、旧主审或状态台账。

## 发现与结论

**数学与实现未发现阻塞项；受限接受 C3 的有限 UV 窗及两条管内隐式支证明。** 这不是原始全部 trim、stock 有限面域、S0、材料侧、整件 0.001 mm 误差或 P3 阶段验收。执行门禁仍为 false。运行历史的核对见文末补记。

非阻塞验证局限 E01：`test_root_exit_certificate.py::test_rejects_unproven_inputs[reversed_v]` 将第一条 FIN 全部控制点反转，亦改变与第二条 FIN 的共同端点，因此会先触发 `root_exit_certificate.py:177` 的接缝拒绝；这个测试证明反向输入被拒绝，不能单独证明第 188—189 行严格递减守卫被实际执行。当前两个真实 quadratic 的完整方向可从精确控制点及代码直接核验，故不阻塞这个固定域结论。若以后独立宣称该守卫的动态覆盖，最小补项是保持接缝、仅改中间 v 控制点使导数不再严格递减的定向负例；无需重跑旧矩阵。

## 审查边界与依赖

- 已读仓库 AGENTS、阶段规则、开发清单和修订 59 台账。Z.2 接受的 `torus_trim_certificate` 作为来源、方向、完整 FIN span、派生连接环的已验依赖继承；只读其与新模块连接处及保存的 C2 数据，不重新验算或运行旧 verifier。
- 实际审查为 [实现](../../../src/nx_sketch_mcp/v3/root_exit_certificate.py)、[测试](../test_root_exit_certificate.py)、[入口](../run_root_exit_certificate.py)、[合同](../../../workspace/v3/p3/P3-ROOT-TRIM-02/README.md)及 [C3 制品](../../../workspace/v3/p3/P3-ROOT-TRIM-02/F0123-exit-certificate-c3.json)。C1/C2 是历史版本，未冒充 C3 上的一次全套运行。
- 公共 `build_certificate` 固定目标 F0123、调用可信 queue 与 fresh source verifier；私有 `_certify` 明确不接受自行断言的证书字典作为信任来源。支持域是这个来源中的两条单 quadratic，不能推广为任意 CAD、多 span 或任意父面。
- 两条 class-11 FIN 的 `source_interval` 与唯一 `nonzero_spans` 均为 `[0,1]`，控制点数各为 3；另外三条各为一个线性 span。F0126/F0169 的载体几何一致，但输出仍保留 parent、position 2/3、顶点 628→626 与 626→614 两条边。相同 torus 不会合并来源身份。

## 数值包围检查

`I.of(float)` 使用 `Decimal.from_float`，精确保留记录的 binary64；Fraction 的分子分母先精确转 Decimal，再分别向下/向上除。加、乘、除分别在 32 位 FLOOR/CEILING context 内求上下界；乘除枚举四端点，分母跨零即拒绝。负号使用 `copy_negate`，不经过默认精度取负；跨零平方下界置零，非跨零平方的乘法包络也成立。

`Decimal.sqrt` 的正确舍入并不随 directed rounding 改成有向 sqrt；实现已显式对结果调用相同 32 位 context 的 `next_minus/next_plus`，从而包住精确平方根。norm 的除数若跨零则失败。轴规范化、参考向量正交投影后规范化、叉积后规范化全部经过区间运算。表达的是以精确记录数定义的规范化正交框架，未把近似点计算当作刚体误差证据。

三角求值没有 π 常数、角度制转换或浮点模周期步骤。参数直接按弧度使用，域外 `[-5,5]` 拒绝。中点是端点的精确有理平均再向外转换；Taylor 的 sin 保留至 43 次、cos 至 42 次。cos 的 43 次系数为零，可统一使用 43 次 Taylor 及余项界 `5^44/44! = 2.138360105864343…e-24`；sin 也适用该共同界，严格小于实现的 `1e-15`。所有有限多项式运算有向包围，再以全局一 Lipschitz 常数乘区间半宽展宽，因此涵盖整区间而非仅中点。无需使用不可靠的“相邻浮点 trig”假设。

## 全参数域、根与空间界

`_bezier_box` 在 Fraction 域精确限制 quadratic：首尾点为 B(a)、B(b)，中点控制为 `B(a)+(b-a)B'(a)/2`。由限制段控制凸包获得整段 u/v 界。`i/512` 至 `(i+1)/512` 的闭区间无缝覆盖 `[0,1]`，包括端点；没有遗漏 knot span 或靠抽样替代全域。

两侧移位曲线分别为 `F(u_FIN(t) ± w,v_FIN(t))`。代码的完整管包住每个 t 的两条曲线；其中 `F_u u'(t)+F_v v'(t)` 包住整段链式导数，正负 displacement 包住 t 与区间中点的距离，故中点值加该乘积确为均值定理包络。无需、也没有假设 u 或 v 的依赖独立。偏导表达逐项符合 stock 四次隐式多项式对 P(u,v) 的链式求导。

两条 v 的相邻控制点差严格为负，故 B'_v 在全域严格为负，t 与 v 一一对应。每个 v 下左 F 严格正、右 F 严格负、管内 F_u 严格负，给出存在且唯一根；隐函数定理给出连续支。相邻 t 单元的共同端点覆盖且根唯一，故可接合。两条边共用精确派生 UV 端点、同一 stock 方程、相同管宽，其共同 v 的隐式根一致，仍不声称它就是 native 顶点。

stock 守卫要求 R>r>0。此时 `A=rho²+q²+R²-r²>0`，故四次式零点不能来自 `A=-2R rho` 的平方伪支。额外 `0<rho²<R²`、`q>=0` 选取内径上半支。该守卫不证明 stock 的有限 trim 归属。

32×32 个有理矩形完整铺满 `[3.2,4.1]×[-0.77,0.77] rad²`；五 FIN 的全部控制点（连同 u 方向管宽）逐一在窗内，凸包性质保障整个派生环和终止管被覆盖。各格 F_u 上界严格负，C3 最坏上界约 `-4083.89291305702 mm⁴/rad`，故窗内固定 v 至多一根。窗外没有结论；未有管中根存在证明的 v，仅有“至多一根”，不能写作每个窗内 v 都存在交线。

在精确正交框架下固定 v 的 `||P_u||=R_root+r_root cos(v)<=R_root+r_root`。乘精确管半宽 0.0002 rad 并向上舍入，得到 `0.00077750000000006003197938753146446 mm`，README 的 `0.000777500000000061 mm` 是更宽上界。此界对应连接后 FIN 的解析复合与选定隐式支同 v 配对，不是 API 请求误差、原始 class-11 trim 误差、候选 S0 误差或整个区域 Hausdorff 预算。

## 来源、状态与剩余验证

单位为 mm，UV 为 rad，F 为 mm⁴，偏导为 mm⁴/rad。root 框架与 stock 轴向 Y 的固定框架分别处理。当前 PRT 与未知历史 STEP 没有混淆；跨快照源身份、状态、API 选项和方向依赖 Z.2 的可信来源链。代码公共入口重新验证该链，本审查未重跑它。frame 的物理含义仍依赖已记录 API/零件坐标合同。

C3 `status`、`closure`、`error_budget` 和 `conditions` 明确保持 source API association conditional、源顶点关联 conditional、execution false；没有改旧 reader `geometry_details_complete=false`。尚需的新证据为原始有限 edge/face 域与本解析支的完整关联、两 stock 面实际有限 trim、候选 S0 对应及材料有效性、总误差预算；后续区域接入不能把本有限域正结论直接提升为整件或阶段完成。

## 审查者独立微算例

为检查新数值原语而执行一次独立小脚本；没有运行 pytest、源 verifier、512×2 管网格、32×32 窗网格或旧矩阵。cwd=`C:\0sf\1PROJECT\AI\design\nx-sketch-mcp`，解释器 `C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe -B -`，环境 `PYTHONPATH=src`、`PYTHONDONTWRITEBYTECODE=1`，PowerShell here-string 传脚本 stdin。实际工具返回 exit 0：

```text
FIN 0 class 10 source_interval [0, 1] nonzero_spans [[0, 1]] Bezier_counts [2]
FIN 1 class 10 source_interval [0, 1] nonzero_spans [[0, 1]] Bezier_counts [2]
FIN 2 class 11 source_interval [0, 1] nonzero_spans [[0, 1]] Bezier_counts [3]
FIN 3 class 11 source_interval [0, 1] nonzero_spans [[0, 1]] Bezier_counts [3]
FIN 4 class 10 source_interval [0, 1] nonzero_spans [[0, 1]] Bezier_counts [2]
independent_checks_passed 29 common_Taylor_remainder_upper 2.1383601058643432e-24
```

29 个微检查的确切构成：区间 `[-7/11,-1/3]`、`[-2,3]`、`[1/3,7/11]` 各平方一次，并分别对 `[-5/3,-2/3]` 与 `[2/3,5/3]` 检查乘除的全部有理端点包围，共 15；sqrt 输入 Decimal `0,2,1e-80,1e80`，比较包络端点的精确有理平方，共 4；对 binary64 `-5,-0.77,0,3.7,5`，将新 trig 输出与独立 Fraction Taylor（sin 至 99 次、cos 至 100 次及各自 Lagrange 余项）比较，共 10。另以 Fraction 精确确认共同余项 `<1e-15`。这 29 项是审查微断言数量，不是 29 个项目测试，也不与 SI 历史通过数相加。读取保存的源 C2 只用于核对 span/geometry 元数据。

未调用 NX、Git 或 hash；没有改变任何被审查制品。完整网格的既有运行证据按下方补记继承。

## 既有执行证据补记与最终接收范围

SI 在本次审查询证后明确报告：**没有保存原始 pytest/CLI 日志文件**。下表来自 SI 对其实际工具转录的逐项答复，审查者未直接读到那些历史工具输出，不能称作独立复跑或原始日志核验。已保存的 C1/C2/C3 JSON、当前实现/测试与 README 可直接读取。本补记保存该来源限制及完整序列；不因换审查者重跑已有效运行。

| 当时版本与动作 | 实施者提供的实际结果 | 证据解释 |
| --- | --- | --- |
| 首次 `python -m pytest -q tests/v3/test_root_exit_certificate.py` | exit 1；`1 failed, 9 passed in 0.22s` | 真实正例在 cell 0 因保守区间过宽失败；9 pass 是 8 输入负例加 1 算术正例，不是 9 negative |
| 收紧 trig 后仅 `::test_f0123_real_finite_branch_positive` | exit 0；`1 passed in 5.48s` | 定向复验首败；未冒称首轮全部通过 |
| C2 均值形式与窄管后，仅 `::test_f0123_real_finite_branch_positive` 和 `::test_rejects_unproven_inputs` | exit 0；`9 passed in 6.32s` | 1 正例加 8 参数化拒绝例；基本算术原语未改，原算术测试继承 |
| C3 加窗后先运行 `::test_f0123_real_finite_branch_positive` | exit 0；`1 passed in 7.88s` | 此中间运行由 SI 补充，README 未逐项列出 |
| C3 增加窗断言与新负例后，仅 `::test_f0123_real_finite_branch_positive` 和 `::test_graph_window_rejects_uncovered_FIN` | exit 0；`2 passed in 7.92s` | 最终 C3 两项定向证据；覆盖实际正例和超窗拒绝 |
| C1/C2/C3 各一次 `python -B tests/v3/run_root_exit_certificate.py` | 均 exit 0；各 stdout 报告 `edges=2`、`execution_approved=false` | 分别生成 `F0123-exit-certificate.json`、`F0123-exit-certificate-c2.json`、`F0123-exit-certificate-c3.json`；未覆盖旧文件 |

准确 cwd、解释器与环境见前节及 README；上述 pytest 节点均位于同一个 `tests/v3/test_root_exit_certificate.py`。当前测试源码为 1 真实正例、1 基本算术正例、8 输入拒绝参数例、1 超窗负例，共 11 个节点，其中负例共 9；没有声称这 11 项在最后版本一次重跑。此处只接受已有执行记录的有限含义，统计不跨版本相加。

最终意见：**ACCEPTED WITH SCOPE LIMITS（受限接受，无阻塞改码请求）**。接受的是 fresh Z.2 来源依赖下，F0123 两条单 quadratic 返回 FIN 与选定解析隐式支的有限管存在性/唯一性/连续性、同 v 空间界，以及声明 UV 窗内至多一根。E01 的特定守卫动态覆盖限制、历史日志未单独保存、API 来源合同、native 有限域/端点、S0、材料侧及总预算限制均保留。本结论交 TL 决定接收，不授权 P3 完成、P4—P7 或模型执行。

## 增量 M1：四 FIN 多段支持与 22 根首次批次

2026-11-12，原 C3 已获 TL 受限接收后，独立审查新增 `_exact_num`、`_exact_pair`、`_prepare_multispan`、`_prove_multispan`、`build_multispan_certificate`（`root_exit_certificate.py:248` 起），以及 [新增测试](../test_root_exit_multispan.py)、[批次入口](../run_root_exit_multispan.py)、[合同](../../../workspace/v3/p3/P3-ROOT-TRIM-03/README.md)、[22 根制品](../../../workspace/v3/p3/P3-ROOT-TRIM-03/22-root-exit-certificates.json)。原 C3 的区间原语、公式、均值形式及窗证明继承；Z.2 source verifier 和 R29 的 mm/绝对坐标守卫继承。本次没有重审旧算法、重跑旧 C3 或修改被审实现。

**M1 未发现阻塞项；受限接受新增多段实现对本批 18 个实际来源的局部结论，以及另外 1 项继承/3 项 blocked 的完整报告。** 不能将批次 exit 0 理解为 22 根均已通过。源有限 trim、S0、材料侧、总预算及 P3 完成门禁继续开放。

### M1.1 完整原域、方向与连续性

`_prepare_multispan` 要求四 FIN 中恰有一个 class-11、三个 class-10，仅一个绑定的 F0126 或 F0169 父面，且固定轴向 Y stock 框架满足半径要求。其来源仍必须来自公共入口 fresh source verifier；这些私有函数不能用人工拼装字典替代来源验证。

原参数域与各非零 span 的端点由 `_exact_num` 精确保留 binary64，拒绝非数、非有限值和 bool。检查原域严格递增、首尾精确等于原域边界、每段长度为正、相邻原参数端点精确相等、span 数与控制数组长度相等，因此不允许漏段、间隙或重叠。完整源 knot→Bezier 分解及控制点方向依赖已验 verifier，不由本模块重新推断。

来源的 `nonzero_spans` 按原参数递增排列，而 controls 已由 verifier 按遍历方向排列。正向时保留原 intervals；反向时同时倒排 interval 列表并倒置每个 interval 的端点，即代码第 301 行的 `[[b,a] for a,b in reversed(intervals)]`，正好与现有 controls 一一配对。没有再次反转已经有向的控制点。每个段局部参数 s∈[0,1] 对应 `t=t_start+(t_end-t_start)s`；均值证明使用的是控制曲线对局部 s 的导数，因此不缺原参数长度因子，也不应在同一局部步长上重复乘原域缩放。

本批 18 个通过项都是两个 quadratic 非零段，原域 `[0,1]`，遍历为反向，实际输出均为 `[1,1/2]` 接 `[1/2,0]`；每段 128 个有理闭区间覆盖完整局部域，共 256 个段内区间。内部 FIN 接点要求二维精确相等，没有把近似接点差静默忽略。外部 FIN 接点仍是 Z.2 已声明的中点识别，不能提升为 native 顶点精确关联。

新增 v 单调判据允许相邻控制点差为零，但要求所有差符号一致且每段端点严格不同。对 quadratic，这使一阶导数在开区间严格同号，最多在段端点为零，仍是整个闭段严格单调；不是导数处处严格非零。连续相接的段按同一方向严格单调，故整个 FIN 的 v 映射一一对应。即使 v'(s) 在 knot 为零，已证明 F_u≠0 的隐式支仍可作为 v 的连续函数；不需要除以 v'(s)。本批实际方向全部是 v decreasing；没有正向原参数或 v increasing 的实源运行证据，不宣称这些组合已获实源验证。

每段 `_prove_multispan` 沿用区间链式导数 `F_u u'(s)+F_v v'(s)`、移位两侧异号、管内负 F_u 和内径上半支守卫。全部段的共同 UV 接点产生相同管及相同方程，因根唯一而得到同一个接点根；全窗负 F_u 又排除窗内另一根，因此段间连续接合。窗仅证明固定 v 至多一根，存在性仍限于已证明的整段 v 范围。连续性与覆盖结论没有依赖有限抽样。

### M1.2 来源与逐项计数核对

审查者进行一次只读制品检查，未调用 source verifier 或任何数值网格：比较批次 label 顺序与 ledger 的 22 根顺序；核对各通过项 source snapshot ID、源路径、root geometry、mm/绝对坐标；核对 parent snapshot ID/路径/geometry；核对源 options 的实际曲线容差；核对有向原参数区间及已保存各界的正负号和保守距离上界。输出为 exit 0，`READ_ONLY_ARTIFACT_CHECKS_PASS; distinct validated source snapshots = 18`。这不是新增曲面读取或重算证明。

| 结果 | 实际来源及数量 |
| --- | --- |
| 新有条件局部证书，父面 F0169 | F0109、F0061、F0125、F0209、F0104、F0132、F0092、F0019、F0007，共 9 |
| 新有条件局部证书，父面 F0126 | F0188、F0060、F0230、F0049、F0195、F0120、F0212、F0233、F0075，共 9 |
| 继承已接受 C3 | F0123，共 1；批次在该 label 分支直接引用已有路径，不调用旧证明 |
| source graph conservative block | F0219、F0053，共 2；`simple non-self-intersecting graph not certified`，不等于真实图有自交 |
| 本次模式不支持 | F0229，共 1；五 FIN、两 class-11，未合并父面或借用其它根替代 |

合计 22 个不同根、18 个不同的新通过 source snapshots；保留每源 FIN、方向、geometry sense、原 options/mapping、拓扑状态计数、父面路径及原始 `reader_geometry_details_complete=false`。F0125 实际 `api_curve_tolerance_mm=0.001` 与源快照一致；其余 17 个新通过项为 0.0001。未把旧源请求改写成更小容差，也未将请求值加到管界后冒称已证明的总预算。

18 项全部 36 个 span 的输出左 F 下界>0、右 F 上界<0、F_u 上界<0；每源 graph_window 的 F_u 上界<0。所有空间界均不大于 README 的 `0.000777500000000061 mm`。这些是读取已计算制品的符号/范围核对，没有重算 18 个网格。实际结论仍是各源解析返回 FIN 与选定隐式支同 v 配对；相同母形或相同父载体没有被用来替换不同源的数据。

### M1.3 直接可读的首次运行证据

本批与原 C3 的历史转录不同，存在可直接读取的日志：[pytest-first.txt](../../../workspace/v3/p3/P3-ROOT-TRIM-03/pytest-first.txt) 为 `13 passed in 3.65s`、`EXIT_CODE=0`；[batch-first.txt](../../../workspace/v3/p3/P3-ROOT-TRIM-03/batch-first.txt) 保存全部 22 label 的上述状态与产物路径，`EXIT_CODE=0`。命令与环境在 P3-ROOT-TRIM-03 README：项目根 cwd，隔离 Python，`PYTHONPATH=src`、禁用 pytest 插件自动加载及字节码；分别运行新 `test_root_exit_multispan.py` 与 `run_root_exit_multispan.py`。

13 项为 F0007 完整两段正例、F0125 实际容差保留检查及 11 个限定输入负例（缺 span、gap、overlap、错 domain、内部断接、非单调、sense 冲突、错父面、错父框架、错误 FIN 分区、错单位）。只将该证据用于实际覆盖的条件；它不证明任意多段 CAD、任意 knot 重数、有理曲线或全部方向组合。批次入口只捕获限定证明错误并记录 blocked；unexpected error 会使执行失败，不被吞作通过。产物用独占创建模式写出，execution 始终 false。

最终增量意见：**M1 ACCEPTED WITH SCOPE LIMITS**。可将 18 项新正结论、1 项 C3 继承、3 项具体阻塞登记为本阶段局部进展；F0219/F0053 的失败原因需后续限定诊断，F0229 需独立模式支持及证据。没有要求重跑现有证据，没有改变已验 source verifier，没有推进 P4—P7 或授予源完整 trim/S0/材料有效性/整件误差证明。

## 增量 M2：两个精确图判据、三根补证及公共来源坐标

2026-11-12，仍由同一独立审查实例承担，仅追加本文件。范围是 `torus_trim_certificate.py` 新相邻直线判据与斜左边内点候选、新 `build_double_fin_certificate`、[17 项测试](../test_root_exit_remaining3.py)、[混合索引入口](../run_root_exit_mixed_index.py)、[P3-ROOT-TRIM-04](../../../workspace/v3/p3/P3-ROOT-TRIM-04/README.md) 的三个新证书/运行日志及 [frame-contract](../../../workspace/v3/p3/P3-SOURCE-FRAME-01/frame-contract.json)。原 19 项继承，不重算。第六项用户决定涉及四个连接角独立，其参数实现不在本次审查范围。

### M2 初审发现（修复状态见后续补记）

**M2-E01，中等严重度：精确内点转换为 binary64 后可能落在边界，新增内点输出保证不完整。** 受影响的是 `_graph` 构造 `interior_uv=[float((uleft+right_min)/2),0.0]` 的返回步骤（初审第 417 行）。新斜边充分判据保证精确有理中点在严格间隔内，但未保证返回的浮点坐标仍在内。下游将其作为内部点计算法向/材料方向；边界点不能冒充所声明的内点。两项几何引理本身正确，错误位于最终表示转换。

独立最小反例已执行一次、exit 0：令 `l0=Fraction(1)`、`l1=Fraction(math.nextafter(1.0,2.0))`、`r=Fraction(math.nextafter(float(l1),2.0))`，四 FIN 为左直线 `(l0,-1)→(l1,1)`、上直线到 `(r,1)`、class11 quadratic `(r,1),(r,0),(r,-1)`、下直线回起点。此输入来自精确 binary64 控制值、非零有限曲线，满足新 fallback 和已有简单环检查；`_graph` 实际通过并返回：

```text
new_fallback unique linear side strictly crosses v=0 and lies strictly left of the continuous monotone intersection chain; other two sides do not meet v=0
interior_uv [1.0000000000000004, 0.0] right_boundary 1.0000000000000004 on_boundary True
```

最小修正是对转成 float 的返回 u 再按精确 Fraction 检查 `uleft < u < right_min`，不满足则保守拒绝，或提供明确的精确坐标接口。最小验证为这个新增拒绝例及现有 slanted 正例，实际三源只需核对已保存点严格在间隔内；无需重算任何旧或新完整管网格。已集中通知 root，由 SI 修复，审查者没有改实现。

实际 F0219、F0053、F0229 的保存返回点已分别用精确 Fraction 对上下界只读核对，三项均严格在内；其间隔分别约 `0.7574105303868954`、`0.7574105303868932`、`0.7574105303878436 rad`，故本反例不否定已生成三份数值证书。M2 实现接收暂待 M2-E01 最小修复；三源既有事实与以下 frame 合同不因此作废。

### M2 两个图引理的独立核查

`_adjacent_linear_only_join` 只对各两个控制点、非零且共同端点精确相等的两段返回正结论。以 J 为共同点，两个远端向量叉积非零时，两支所在直线只能在 J 相交；叉积为零而点积负时，它们从 J 沿相反射线伸出，也只共享 J。同向共线、零段及非线性不会由此接受。调用点受 `adjacent` 布尔门控，非相邻分离保持原有严格凸包检查；首尾邻接会按遍历顺序换位后检查。运算均为源 binary64 的精确 Fraction，没有对小叉积设容差，也没有把极小斜率抹成零。

新左边候选只在恒 U 候选数量为零时启用；多个恒 U 候选仍拒绝。新候选必须是完整单线性 span，两端严格跨 v=0，且整段 u 凸包严格小于全部 class11 控制 u 下界；必须唯一。随后保留简单闭环、每 span 单射、全部非相邻分离、非零面积及周期图限制。其两侧拓扑邻边控制凸包须分别严格 v>0、v<0；右 class11 链精确连续、同向严格单调且整体跨零。因此水平线 v=0 只与左、右各交一次，二者之间严格间隔位于简单闭环内部。这个论证适用于精确中点；返回 float 的额外条件由 M2-E01 处理。

F0219/F0053 的全部原 graph 检查已在三源首次测试中通过，两项采用新 `interior_proof`；它们原保守失败不是实际自交，新增判据也没有扩大 UV 接合阈值或改写原始源控制点。原先 M1 的 blocked 记录保留为历史事实，以本次新证据更新其局部数学状态。

### M2 三源、双边及混合索引核查

三份新证书的 source snapshot ID/path、root geometry、父面 snapshot/geometry 以及 API options 与对应保存源逐项一致，实际 curve tolerance 都为 0.0001 mm。F0219/F0053 分别保留自己的两段完整反向原域 `[1,1/2]`、`[1/2,0]`，沿用 M1 的每段 128 区间及全部守卫；没有借用另一根或共享母形替代输入。

新 `build_double_fin_certificate` 入口仅接受 F0229，调用该源 fresh verifier；检查五 FIN/两 class11、每边唯一非零 span 覆盖完整严格原域、bool 遍历方向和 FIN sense。随后只对这个新源调用已验双边 `_certify` 数学，原 F0123 没有重算。F0229 两边按环顺序分别为 F0169 的 528→624 与 F0126 的 624→622，两个 source interval 都反向 `[1,0]`；其单 quadratic 控制、shared UV 接点、载体相等、父身份/独立边都继续由原守卫检查。输出为每边追加精确有向原域和独立 parent detail，没有合并两片面。

三源仍只有窗内根唯一性、管内存在/连续性及连接后 FIN 与解析支的同 v 界 `<=0.000777500000000061 mm`。两段/两边的全域结论不替代有限 stock trim、native 顶点精确关联或材料有效性。输出中的 API/source association conditional 和 execution false 保留。

已直接读取 `pytest-first.txt`：`17 passed in 15.18s`、`EXIT_CODE=0`。17 项构成为相邻线段 helper 7 例、非相邻相交拒绝 1 例、斜边图正例 1 例、斜边候选负例 4 例、真实三源 3 例、双边入口拒绝其它目标 1 例。该次运行排他保存三个证书，没有为了生成文件重复证明。初始 17 项未覆盖 M2-E01 的极窄浮点间隔反例，故不能据此跳过新发现。

`index-first.txt` 为索引组装 exit 0；审查者只读解析所有 22 个 `certificate_path/json_pointer`，确认全部可解析、source snapshot ID 与对应 ledger/行一致、各证书 execution false。混合索引完整引用旧 M1 的 18 项、旧 C3 的 1 项、新三项；当前三项的索引状态仍为 `new_proof_pending_independent_review`，没有偷偷改成全域接受。索引程序不调用数学证明。

### M2-F 公共保存零件与坐标合同：受限接受

**frame-contract 的受限共同坐标结论可接受。** 审查者检查记录方法为全文件 bytes 直接比较而非摘要，并执行一次只读 `Path.read_bytes()` 相等性核查：CARRIERS01、STOCK01、REGIONS01 三个 `source-before.prt` 及当前 `tests/外球叉.prt` 全部相同，长度均 430553 bytes。未调用 NX、未重新读取几何、未运行 native 验证或 hash。这是本次新跨运行文件关系的审查，不是重复旧采集。

记录所引用的三个代表快照分别对应 F0123、F0169、F0125；snapshot IDs 与合同一致，均为 `Millimeters`、`absolute_part_coordinates`，inventory 的 `part_path` 与各自 summary 的独立副本路径精确一致。三个已接收 shutdown-preservation 记录均确认受控读取后正常退出、不保存、source 与工作副本 bytes 保全。结合已验逐运行 capture/保全及 reader 坐标语义，这条链支持“同一保存零件内容下的共同绝对零件毫米坐标”，对这些局部 root/stock 解析组合无需再笼统写作 frame unknown。

该接收是明确依赖保存内容和 API 坐标合同的几何关系，不是独立坐标计量；不授予跨实体同一 U/V 或边参数、跨会话 native Tag 身份、有效 BREP/材料占据、超过记录选项的 API 误差界或整件重建准确性。旧证书 `frame_correspondence=semantic_candidate_not_independent_frame_proof` 是历史描述，可在后续结论中引用本合同补充其共同零件坐标依据，不需要重写旧证书或重复数学证明。其余 source finite-domain、端点、材料、S0、总预算条件不因共同 frame 已有据而消失。

### M2-E01 闭环及最终限定接收

**M2-E01 CLOSED。** SI 在共同返回步骤先保存 `interior_u=float((uleft+right_min)/2)`，随后严格要求 `uleft < Fraction.from_float(interior_u) < right_min`，否则抛出 `TrimCertificateError('binary64 interior point is not strictly inside the proven interval')`；返回值直接使用已检查的 `interior_u`。精确转换守卫同时覆盖恒 U 与新斜左边路径，没有通过更大容差或换代表点绕过反例。

已读取 [新增测试](../test_root_exit_float_guard.py) 与 [定向日志](../../../workspace/v3/p3/P3-ROOT-TRIM-04/pytest-interior-guard.txt)：`2 passed in 0.02s`、`EXIT_CODE=0`。新增 1 ULP 恒 U 间隔负例证明中点舍入到端点时由指定新守卫拒绝；斜左边正例以 Fraction 复核返回点严格在间隔内。它们验证共享转换守卫的拒绝及正常路径；不将这两项谎称为原三个实际源重算。审查者没有再次执行测试。三份实际证书的已存 float 点已在本次初审逐一通过同一精确间隔条件，因此保留首次证明，不重算其管/窗，也不重复旧 19 项。

**M2 ACCEPTED WITH SCOPE LIMITS，无剩余阻塞实现发现。** 新两个精确图充分判据及浮点内点守卫、F0219/F0053 各自完整两段局部证书、F0229 独立双边证书均可受限接收；结合旧 M1 十八项与旧 C3 一项，混合索引覆盖全部 22 根的此类局部管/窗证据。索引文件中的 `new_proof_pending_independent_review` 是其生成时的历史状态，最终审查状态由本节补充，不能把引用目录当作自动全域验收。

M2-F 的共同保存零件/绝对毫米坐标合同也可受限接收，故不再将这些来源的共同 part frame 笼统列为 unknown；相应历史字段可由该合同和本审查解释补充。仍未证明原始有限 stock/根面 trim 域、native 顶点完整关联、源曲线抽取误差、候选 S0、材料占据或整件总误差。各局部空间界也不构成整个区域 0.001 mm 误差预算。execution false、P3 未完成、P4—P7 未获授权的边界全部保留。本次没有 NX、Git、hash、旧测试矩阵或任何完整数值证明重跑。

## 增量 FP：四连接角参数表达 C4 集中审查

2026-11-12。被审查的是 [flank_parameters.py](../../../src/nx_sketch_mcp/v3/flank_parameters.py)、[新测试](../test_flank_parameters.py)、[CLI](../run_flank_parameters.py)、[C4 产物](../../../workspace/v3/p3/P3-PARAMETERS-01/flank-parameter-expression-c4.json)、[合同与历史日志](../../../workspace/v3/p3/P3-PARAMETERS-01/README.md)及[第六项用户决定](../../../docs/v3/decisions/p3-independent-flank-connection-angles-user-decision.json)。FDRV 的固定 basis、2×2 消元、默认源参考候选和数学充分条件继承此前机械独立审查，不重跑其算法。审查者仍只写本文件，与 SI 实施实例分离。

### FP 集中发现（关闭状态见后续补记）

**FP02，中等，权重未绑定到所声明的固定 basis/FIN，可接受不闭合的端点表达。** `_load_inputs` 核对 knots 和 FIN interval 元数据，`build_parameters` 仅检查 A/B 行和为 1、det 非零且与文件内 det 相等，未核对 A/B 正是这些 knots 在 `[a,b]` 的基函数值，也没有明确机核已审权重内容的冻结见证。因此权重被局部替换后，输出仍宣称原 basis、共同 CircleEvaluate 端点及简单闭环，但实际原样条在 a/b 的值可以不等于声明目标。增加非负性检查本身不能关闭此问题。

审查者执行一次新的内存反例，没有改磁盘输入：在已验 F0002 A 行仅令 `A2+=1/10^6`、`A3-=1/10^6`；所有权重仍非负、行和及 det 均保持不变。通过临时替换 `_read` 的 weights 返回值调用 `build_parameters`，结果仍返回 `simple_four_segment_loop='sufficient strict interval guards passed'`。再用未修改的真实 A 与返回 pole 区间求原样条外端，与声明的 outer CircleEvaluate 区间相减，得到：

```text
t: [-3.429551119258249514132344E-7, -3.429551119258249514132318E-7] mm
r: [-2.66372613272150005059312E-7,  -2.66372613272150005059291E-7] mm
```

两坐标严格不含 0。该反例针对新模块的来源/代数契约验证，不否定已审 FDRV 文件当前存值。最小修正为依照固定原 basis 与 FIN 参数精确核 A/B，或逐项核对明确的已审冻结权重见证；不接受仅同一文件中的 sum/det 自洽。只需集中新增错误权重拒绝及相关真实默认节点，无需旧数学矩阵复跑。

**FP01，中等，`active_support_witness` 不是消元后实际驱动见证，且没有合法自由坐标编辑传播测试。** C4 第 293—299 行选择原 `N_j(a)` 或 `N_j(b)` 非零作为“active support”；但 P1/P5 已为保持两端点解出，最终曲线对 Pj 的有效响应为 `H_j(u)=N_j(u)-[N1(u),N5(u)] M^-1 [A_j,B_j]^T`，所以 `H_j(a)=H_j(b)=0`。原非零权重能证明原基函数有支持，不能证明受约束最终曲线在所给见证位置受到驱动。当前测试只对四角、Rp 和轴径验证合法编辑，十二个自由 t/r 坐标只检查元数据或非法范围，没有实际合法编辑的消费者证据。

最小修正为提供 FIN 内部的精确非零有效系数（若保留原权重须标作 raw），并集中覆盖十二个自由坐标的小幅合法编辑：本侧内部曲线及派生 pole 响应、共享两端点保持不变、另一侧不变。独立性本身没有被反例否定：本审查使用已接受 knots、A/B，在 u=1/4、1/2、3/4 新计算有效 3×3 响应矩阵，其两侧行列式精确非零，近似分别 `0.10319810392027219`、`0.10321431138906145`。三个点严格在各自 FIN 内，足以作为三个有效形状坐标线性独立的存在见证；不是全域几何误差采样。t/r 分量各自独立复用该线性矩阵。SI 也在冻结 C4 后主动报告了同一见证缺口，已由 root 统筹一次修复。

**FP03，轻微，README 的共同来源坐标引用超出所引合同的来源清单。** F0002 实际来自 `P3-CIRCLE-01/native-01/detail-snapshot.json`，F0024 来自 `P3-REGIONS-01/native-01-F0024/detail-snapshot.json`；当前 `P3-SOURCE-FRAME-01/frame-contract.json` 只列 CARRIERS01、STOCK01、REGIONS01。README 声称两源共同 ABS 可依赖该合同，但它还没有为 CIRCLE01 给出同一保存 part 的直接关联。最小关闭项为补充 CIRCLE01 已接收保全与共同 before 的明确关系，或将 README 的合同覆盖说法收窄。不能据这一文档缺口谎称本地数学失败；输出已明确不包原世界→本地数值变换误差，也不授予独立计量。

上述三项已集中交 root；审查者没有修改实现、来源或测试，也没有逐项派发修复。当前 C4 实现接收为 **CHANGES REQUIRED（FP01/FP02，FP03 为来源说明补齐）**；下面无问题的数学与证据边界不因此作废。

### FP 正面核查及限界

第六决定的原话为“四个连接角独立可编辑”，明确两模板独立、同侧跨 22 成员共享并保留原阶和 knots；不授权 G1、无限编辑域或全形状正确。模块核对该 decision ID/范围及既有绑定、模板决定、FDRV 路径；原五项决定未被重写。C4 确实采用 C2 的 `Rp=11.848889841783512 mm`、`rho=0.7363898417823 mm`、`phase=0.2855921266687233 rad`，没有使用 FDRV 的不同源参考 Rp/phase 替代。

各侧保留 order 4、原 11 knots、完整 `[0,1]`、原 FIN、非有理七 pole；P0/P6 fixed_not_counted，P1/P5 派生，P2/P3/P4 的 t/r 为十二个独立长度输入。两 root/outer 角共四个独立角输入。`shaft_outer_diameter_mm/2` 是外部 stock 依赖，由 stock C2 v6/v7 的相同 r 给默认值，输出分类明确 `external_stock_dependency_editability_unresolved`，没有把本次四角选择说成另授权独立外端半径。

默认角是相对于 C2 默认圆心的精确源端点方向 `atan2(t,r)` 定义；编辑当前 Rp 不重新定义初始角。默认 CircleEvaluate 用同一精确方向的归一化投影，和理想 atan2/sin/cos 表达数学等价。编辑角则使用有向 trig 包络。根/外点表达 ID 同时供样条端点与圆弧端点使用；F0002 a/b 为 outer/root，F0024 为 root/outer。它们仍是离线表达契约，不是已经创建的原生消费者或 solver 约束。

新 atan 算术检查：40 项 atan 幂级数在 |x|≤1/2 内，首遗漏项界 `0.5^81/81 < 1e-26`，实现统一展宽 ±1e-25 足够；负号与运算沿用已验有向 I。π 用 Machin 公式，象限与 reciprocal/pi/4 分支按区间符号和严格区间条件选择，模糊分支保守拒绝。审查者用独立 Fraction 100 项及精确余项检查 π 与四个实际默认 atan2，五项均被 C4 包络包含，脚本 exit 0；没有重跑原 trig 或 FDRV 矩阵。

2×2 公式与矩阵行列式使用原精确权重，默认归一化端点、派生 pole、形状域均通过区间求值；问题 FP02 是未检来源权重被更改，公式本身未发现错误。`_preview` 单独计算返回 binary64 到包络两端的最大误差，默认定义和显示 double 没有混为一体。全部 pole 的同号 t、正 r、逐 pole t/r 单调、cap 凸包、root 下半圆以及 root 位于 shaft 圆内的检查使用包络，并给出严格正余量。Rp/rho/shaft/cap/roll 的精确条件支持已验四段局部简单环和理想六段封口条件；cap=13.1、roll=15 是指定理想辅助选择，不是实测全件间隙。

默认源→候选 L1 上界用完整原 `[0,1]` 的非负基函数凸包给出，实际两侧约 `1.558843285e-8 mm`、`1.603518671e-12 mm`。F0064 锚角与 C2 `phase+10·2π/22` 的差另外按区间包围，约 `9.2202068e-15 rad`；源 pole 的最大 L1 半径乘该差给保守旋转位移界，再与形变界按三角不等式相加。它不包世界→本地转换误差，也不包其余 21 成员的源观测偏差。绝对角差乘半径界即使跨周期也仍保守，不要求先把差折返到主值；但本模块 phase 及连接角有明确有限支持域，不宣称任意 2π 重参数化编辑均接受。

新局部坐标映射使用绝对 `theta_i=phase_rad+i·2π/22`，C2 原 `rotation_expression` 则作用于源 world 模板，两者在字段中明确区分。C4 保留 22 个 member_index 的固定原顺序和每项对应 face/template 引用，没有按角值重新排序。成员角度、局部→ABS 和消费者仍以表达/引用给出，未数值求值 22 套 native 变换，故本审查不将“22 个引用”称为 22 套真实几何编辑传播验证。轴向坐标也属于后续三维使用约定，当前局部二维数学与原生闭合分开。

### FP 历史验证证据

已直接读取首次 `21 passed`、C2 `9 passed`、C3 `7 passed`、C4 `11 passed` 的独立日志和全部 CLI exit 0。首版、来源/原支持见证补充、严格余量/关系补充、frame/domain 补充分别为不同代码版本上的运行；不相加为 48 个独立用例或最终版本的一次全部覆盖。C4 的 11 项是默认正例和十个来源/单位/frame/domain 等拒绝例；它并不补足 FP01 的十二坐标合法传播或 FP02 的正权重替换拒绝。

CLI 使用独占文件创建模式，产物保留 C1—C4，没有覆盖历史。所有版本 `geometry_proven=false`、`native_binding_verified=false`、`execution_approved=false`。本轮独立新算例只含有效响应矩阵、π/四 atan2 包络及错误权重最小反例；未运行 pytest、NX、Git/hash 或旧权重/几何证明。当前默认数据的数值界与已验 FDRV 充分条件可继承，最终实现接收等待上述集中修复闭环。

### FP 集中 C5 闭环与最终受限接收

2026-11-12；只审 C4→C5 修复差异及[新产物](../../../workspace/v3/p3/P3-PARAMETERS-01/flank-parameter-expression-c5.json)，未重复前述整体审查或旧算法测试。

**FP02 CLOSED。** 新 `_basis_and_effective_witness` 使用已经接受的 `restrict_bspline` 精确依赖行契约，从当前已绑定原 order=4、knots 和 FIN `[a,b]` 构造限制曲线；首末依赖行分别就是原曲线在 a/b 的基函数权重，逐项要求与 FDRV A/B 精确相等，并拒绝负权重。用于查询依赖行的零 dummy pole 不影响 basis 权重。该检查在端点、默认角、消元及候选有效性声明之前执行，消除了“sum/det 自洽但不是原 basis 权重”的漏洞，不是仅附加非负性判断。C5 定向正权重同和同 det 篡改例沿用本审查的 `A2+=1e-6,A3-=1e-6`，并明确匹配新的 weights-not-match 拒绝；另有负权重变体。没有修改或重新审查已验限制算法。

**FP01 CLOSED。** C5 在各自 FIN 内精确检查 u=1/4、1/2、3/4 的位置合法性，使用同一已验依赖行求 N，再形成 `ψk=Nk−N1*c1−N5*c5`，其中 `[c1,c5]^T=M^-1[Ak,Bk]^T`。查询时三个 u 转 float 均精确可表示，不损失有理位置。输出完整三个见证的 N、有效 ψ 矩阵和精确非零行列式；其数值与本审查先前独立 Cox 递推所得响应一致。每个自由 t/r 参数现在引用内部 `effective_weight_exact` 非零项并明确是 P1/P5 消元后的响应，旧错误的端点见证已替换。非零 3×3 行列式证明各侧三个坐标响应线性独立，t/r 两分量分别适用；不将三个见证点当作全域误差界。

新 [test_flank_parameters_review_fix.py](../test_flank_parameters_review_fix.py) 对全部十二个自由坐标各作 `+1e-5 mm` 的合法编辑。其判定比较内部求值区间严格分离及至少一个派生 pole 区间严格分离，故不是仅检查 JSON 文本或浮点显示变化；两端 CircleEvaluate 条目保持相同、另一侧完整模板保持相同。端点权重绑定加正确消元式保证实际原 basis 的两个端点对应同一目标，不能再用未绑定权重伪造这一关系。该测试证明这十二个指定小幅编辑的传播，允许域仍是函数全部严格守卫通过的输入，不据此外推任意编辑幅度。

**FP03 CLOSED。** 新 [frame-contract-c2](../../../workspace/v3/p3/P3-SOURCE-FRAME-01/frame-contract-c2.json) 保留原三条代表记录，并显式新增 CIRCLE/F0002 与 REGIONS/F0024 的 snapshot path/ID、mm/absolute_part_coordinates、独立副本路径和既有 capture 接受依据。审查只读核对新增两行与真实快照、summary 相符，并对新增 CIRCLE `source-before.prt` 与已接受共同 before 做全 bytes 相等检查，结果 true；原 REGIONS/CARRIERS 公共关系直接继承，未重跑 native。C5 加载时要求来源合同的有限状态及每个模板 snapshot ID/path 恰有唯一匹配行、bytes/副本一致布尔与单位/坐标语义；删除 CIRCLE 行的新负例被拒绝。README 已改为准确引用 C2 合同，仍明确不授予独立计量或源世界→本地变换误差界。

已直接读取 [pytest-c5.txt](../../../workspace/v3/p3/P3-PARAMETERS-01/pytest-c5.txt)：`16 passed in 0.60s`、`EXIT_CODE=0`。构成为十二坐标合法编辑、两个权重替换拒绝、一个缺 frame 来源拒绝、一个真实权重及有效响应记录检查；[cli-c5.txt](../../../workspace/v3/p3/P3-PARAMETERS-01/cli-c5.txt) 为两个模板/22 成员、execution false、exit 0。命令是 README 记录的仅新 `test_flank_parameters_review_fix.py` 一次定向运行及 C5 CLI 一次产物生成。本审查没有重新执行这些测试，不将 16 与 C1—C4 历史计数相加。

审查者只读比较保存的 C4/C5 JSON：每侧原 poles、角、端点、basis、严格余量、完整曲线源→候选界逐字段相同，anchor placement 与旋转/组合界也相同；C5 仅增加真实有效响应/内部见证点、替换自由坐标见证及新增 frame 来源引用。默认数值因此继续沿用前述 C4 核验，未因新元数据声称精度变好或完整三维覆盖。

**FP C5 ACCEPTED WITH SCOPE LIMITS；FP01—FP03 全部关闭，无剩余阻塞发现。** 接受范围是这两个固定源 basis 的离线 P3 参数表达、四个已确认独立连接角、十二个有效形状坐标、源权重绑定、守卫内的局部数学候选及默认局部/锚布置数值界。外轴径仍是编辑分类未决的外部 stock 依赖；22 成员保持原顺序和引用契约。源本地变换误差、其余成员观测残差、真实有限 trim、材料侧、native 消费者/solver、G1 和全几何预算仍未证明。`geometry_proven=false`、`native_binding_verified=false`、`execution_approved=false` 保持；本接收不表示 P3 完成，也不授权 P4—P7 或 NX 执行。
