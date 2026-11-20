# P3 STOCK54 最终有限区域独立审查

2026-11-13，geometry_review_r68，独立于实施者。此文件独占写入，不改validation的stock旧评审、实现或state。继承旧stock carrier/事件/CSG、PHYSICAL16采集、TAIL TR401、HEAD H215、SR202及肩部各已接受叶证据，不运行旧矩阵或NX/Git/hash。

## 当前已完成结论

post-read新增原圆、v4/v5原弧、普通20源面、尾部stock5源面、s5及s6有限域补证和54面材料图已完成受限审查，未发现尚未修复的局部阻断。s7/s8的有限端域证明已按下列意见修正；其三个肩部叶证据现由validation正式接受，本审仅完成最后的新增组合核对后追加最终54面接收节。当前不是尚缺原边数据，不能再以泛native/kernel未知延后P3源定义。

## 本次发现及修复

- **STF01 CLOSED：FACE journal点不证明trim内点。** F0137的journal点(0,-26,0)实际在环孔内，否定通用“FACE点必在有限面内部”的用法。s7已移除该前提，改为完整简单六边环、无额外环及有界source face在展开圆柱上的唯一有界Jordan侧；历史代表点仅身份旁证。
- **STF02 CLOSED：周期chart必须选定切口。** s1—s3在已移除+Z槽内开角缝；s4源同柱两片联合后在远离槽的负Z母线开图，加相同方位辅助母线、按原v3/v4圈绑定端高后比较，再识别回去。该缝不是新物理边，避免近点出现2π坐标跳。
- **STF03 CLOSED：computed constant-V不是class10原边。** ordinary/s5已改为原3D EVAL＋carrier＋同树有向loop的有界角域投影，FIN只作方向/选支见证。s10的F0167原V=-π须按原3D子午弧展开到+π，不能字面走3π/2长路。实际63819/63715为R3、原limits[3π/2,2π]短quarter，source bbox排除补弧；s5同样由原R2子午EVAL及bbox选短quarter。源半片可按共同carrier联合比较，不伪造内部缝逐点对应。
- **STF04 CLOSED：s6不能把旧normalized patch界冒作原native有限边界。** 新 `root-cone-native-endpoints` 将24原class11的48同树native顶点直接径向投到原柱、再评价原正锥图，未求值转换样条。原front/rear角端比较实际消费这些native点；配合短支bbox排除/连通注入和两split点在区间内部，原有限图域得到具体绑定。组合明确继承RC602零轴项，不再以旧含axis_point同角图代替零轴全图。
- **STF05 已修，最终组合核对中：** s7不用“同u实出口总存在”作隐含前提，改走同relative-phi唯一C5根图及原start/transition端域collar；旧.000855 first-exit可作冗余保守项。s8补实际原顶点逆角及root minor-v端域延拓，不从仅端点空间近默推同参数有限域。root的Fu外延现使用完整 `PuᵀH Pv+gradF·Puv` 并取外延后>3998；s7混合欧氏图界的合成字段已改称Euclidean，未冒称L1。

## 已完成的新核对与可继承结果

新post-read的24个原缺边、26个表示（含6条head口弧）逐项以当前edge完整journal及两incident face journal独立匹配P1，均唯一；18个stock原边的20份表示，其完整geometry与本树匹配。全部实际arc_limits=evaluator_limits，水平轴Gram误差最大约2.1972e-16；最大carrier L1差约8.6046e-12 mm。额外圆心/半径运输、正交化及已有算术余量的保守需求<3.564e-11，明确小于1e-9预留。因而完整major/half/partial弧预算<2e-9可受限消费；P1中点仅消歧身份，误差来自原完整EVAL。

v4/v5为四个唯一原半圆、六个已有source表示，原单位帧及[0,πstored]完整域核对一致，新上界均<1.010e-9。source preview舍入/π端差由1e-9余量覆盖；原carrier规范化不重算。

s6新24边/48顶点与已审原提取逐项相同。只对新最坏E0481独立110位计算：原点到其真正柱/锥图L1约2.1071576562e-11，加1e-10算术余量被保存1.2107157656e-10界覆盖。新的完整链为native投影＋原front/rear角collar＋已审normalized有限patch到零轴C5，合约4.6249374183e-10 mm<6e-10，含完整axis位移，没有未知转换误差项被置零。

54面材料图已独立核：以H215实际F0196 +Y为锚，53个保存共享边路径均为真实互反P1 incidence，覆盖54/54。传播要求每共享物理边两侧同目标edge、同对应端点和保向参数，内部同carrier缝联合处理；有效一致定向BREP为明示源API输入，不冒称point-in-solid或body-validity实测。

上述均为项目根、既有隔离Python的只读内存增量核对，exit 0。初次读取s8输出误用了单数文件名，实际文件为 `s8-endpoint-collars.json`；仅文件读取报不存在，没有执行生成器/测试或影响几何结果。

## STF06：54源面P3区域正式受限接受

**无未闭新增几何阻断，接受完整54个stock source faces到默认数学剩余区域的双向欧氏界 `<0.000859 mm`。** 上文STF05的最后组合现已核清并关闭。validation已在肩部独立评审中正式接受native-start-seams、native-edge-inverse、native-vertex-roll-inverse三个叶，以及C5唯一根/有限limits、原root-exit直接顶点和上圆弧直接路线；本审查只核新消费者引用和组合，不重复其求根/求逆。

本接收按明确source API的有效定向BREP、原class10三维边/原class11双父有限交支、共同ABS及有界carrier投影解释进行。它关闭当前P3的具体源有限域解释与预算，不将源或目标native/kernel未知误差暗置零，也不把未来执行验收作为拖延已完成数学区域的泛化门槛。尚未宣称全工件235面/最终P3综合验收、原生参数件创建、制造精度或任意编辑域。

### 普通20面、尾部5面及s5

18个新stock原圆的实际完整长弧/半圆/部分弧由原EVAL参数域确定；v1/v2选保留的长弧，v3两片选其各自半平面的部分弧，其余物理站位对应半圆。原端点和中点用于身份/支的唯一选择，实际误差来自原EVAL。完整参数配对及小端角延拓覆盖双向全域，不把三点距当全弧误差。以原3D圆及parent graph定义边域，v9 source精确父面代数交点的另一较大界不替换原class10圆对象。

ordinary s9..s19的20源面按11个meridian段分组：柱/锥用轴向端域与affine meridian，平面环用径向插值；s10/s19采用真实原短子午弧、完整两物理圆和正确展开的管角。computed constant-V只是支持/方向见证，原3D圈到source carrier角域的投影成本由<2e-9原圈界、<1.8e-10 carrier界和<1e-8端圈包络控制。内部分半缝可联合，未量化原缝的逐面复制不作为结论。所有新角/端域成本远小于每组保守 `<1e-6 mm`；源simple有限域与有界侧由原边、native loop/BREP和bbox排除补长支共同确定。

尾部s1..s4共5面，物理边集包含TAIL04已接受的原线/圆/四条原class10样条/两条真实柱柱交支，以及新v1..v3和继承v4圆。最大边界项<2e-6。采用已补好的周期chart切口，`u=9 theta` 的逆角投影因r≥6.9增幅<1.31；提升对y的母线斜率≤sqrt(3)，保守norm<sqrt(5)。填充界连carrier归一化严格小于1e-5。尾槽原class11转换样条的约2.4e-5表达误差没有混入真实双父图，TAIL四面和stock五面各自责任不重复。

s5的两source tori由原R2子午quarter、v4/v5原半圈、正确周期展开选出有限短带；source/candidate carrier平移已审<9.701e-12。尾刀已在更低处终止，22成员Q的s>11.1124而s5 r≤11，故候选无遗漏cut裁片。接受s5两面（可按同carrier联合） `<1e-6 mm`。

### s6有限域闭合

两个原cone树各一完整48-FIN环，source/candidate暴露边由v5两半圆、22条s6/s7原弧、44原class10背边、24拆分root/cone真实双父边及内部同cone缝组成。24后边的原顶点/短角域新链见STF04；旧normalized patch界仍按其原scope消费，并明确包括RC602零轴平移。

对于true cylinder/cone图，每个原短角有唯一正nappe高度。实际原vertex投影、原front/rear角collar和已审零轴C5 patch的完整链约4.62494e-10 mm；与原44背边最大<1.189e-5及其他圆边/角点组合，1.3e-5边界homotopy半径保守。它不使用转换样条作为源曲线，也不从requested tolerance推native误差。

在适当打开的cone chart `(11 theta,y)` 中，半径11..12.17、母线斜率约sqrt(3)，原/候选近点投影增幅<1.11、提升norm<2.01。源完整有向48边环及选定物理支给一致有界组件；内部同carrier缝联合后不产生额外目标面。边界同伦和绕数给完整source/candidate有限面双向覆盖，保守 `<4e-5 mm`，不是仅以边界附近采样代替填充。

### s7、s8真实有限端域与根唯一性

C5每侧t/t′/s′控制网符号及新seam guard给固定roll的s7唯一根，member-center的0.1 mm条带位于cut内部。s8的

`F_u=2 t t′+2[n cos(phi)+H H′ sin(phi)]s′`

在H′≥0、n>0、0≤phi<π/2时同样严格定号；完整C5窗/finite limit证据另由validation接受。原class11边仍以其真实双父连通分支及原有限拓扑选定，computed FIN只识别支持域，不能用其表示误差充当源边误差。

s7采用同relative-phi连续图配对。已审44条source/candidate根管最大8.58454e-7；新source原start曲线到source SOR逆像及88原顶点逆角，直接控制有限两端。微负roll用圆柱F的even-phi延拓再夹到0，不无依据假设同u候选总有实出口。用 `|Fphi|<120, |Fu|>21.7` 及新导数控制网，C5图世界L1速度<26 mm/rad；实际组合边界欧氏界为 **1.1846760650709582e-6 mm <1.2e-6 mm**。旧.000855 first-exit可以保留为冗余保守预算，不承担这条配对的存在性。

s8肩侧使用同一已接受88点逆角。`|t_u|<1.15, |s_u|<1` 给 `sqrt(3)*|P_u|2<3.2`、`sqrt(3)*|Pphi|2<8`；quartic包络 `|Fphi|<286080<287000`、`|Fu|>6204`，故世界L1路径速度<160。这明确处理了L1与欧氏/旋转的关系，未将旧欧氏根管改称L1。

root侧44个直接事件原顶点经原torus radial/axial投影，source minor-v到C5事件的角差由真实残差、既有carrier map及直接点界控制。原carrier的平移、最小转轴和半径变更可选为**保持signed minor v**的映射；不假设major u0相同。独立核44点均逐位等于原root/s8边自己的native vertex，且新引用的P1 root-edge就是该点所属的24个拆分边之一。各root的major+minor<4、.7<minor<.74，支持所有使用的速度常数。

新的原vertex→已覆盖FIN-end minor-v对照最大<1.095e-11 rad，仅用于确定真实图域需要的极薄延拓。扩1e-9时 `|ΔF|<9.62e-5`；预审修正后的完整导数式

`dFu/dv=Puᵀ Hess(F) Pv + grad(F)·Puv`

即使对Hessian逐元取3倍，仍给 `|ΔFu|<0.00017612<.0002`。旧端号margin>1及|Fu|>3999因此外延后仍有margin和|Fu|>3998，唯一根延拓成立，无需重跑22图。新root速度用3998分母仍<102；旧无参数carrier Hausdorff没有被直接偷换成有参V对应。

合肩端collar、root端collar、source径向残差及原同角图，s8完整有限边界界为 **7.978173589045872e-6 mm <8.1e-6 mm**。源真实有限端域与候选域的拼接已量化，未把原顶点/转换曲线关系设为零。root源FIN到隐式曲线的0.0007776 mm另属表示对象，不加入本源双父图预算。

### 边界到面域、材料及全54合并

s7展开圆柱图的短角逆投影增幅<1.001，提升不放大欧氏长度；即使使用原较宽0.000858边界预算也得到 `<0.000859 mm`。新更小边界界无需改变对外保守阈值。source六边单环、无额外环的有效BREP及原完整边集给有界Jordan组件；source face沿y有界，不能取无界补集。0.1 mm seam间隔远大所有homotopy误差，排除了展开坐标的周跳。

s8用 `(12 theta,5v)` 的内侧torus chart，实际r≤13、管半径5；逆局部投影<1.01、提升<13/12。各原48边环/已选有限支对应同一有界带；source torus补长支由其有限物理圈、原域和bbox排除，源分半缝联合不增加物理边。有限边界同伦给完整两面联合 `<2e-5 mm`。source/candidate loop中共边须保留同端点/一致参数方向，仅无向入射不足。

source材料方向由已核54节点、53共享边路径从H215的F0196 +Y锚传播，在明确有效定向BREP及上述共同边映射条件下唯一；不把FACE journal点、bbox或is_solid代替材料证明。候选S0与tail/head/22 cutters的分离、cap隐藏、单次退出和保留材料连通直接继承独立stock CSG审，不重算。

最终packet逐段核与P1 plan完全一致：

| source分组 | 面数 | 双向欧氏保守界（mm） |
| --- | ---: | ---: |
| s1..s4尾部外stock | 5 | <1e-5 |
| s5短torus带 | 2 | <1e-6 |
| s6 cone剩余域 | 2 | <4e-5 |
| s7柱面剩余域 | 22 | <0.000859 |
| s8 torus剩余域 | 2 | <2e-5 |
| s9..s19普通区域 | 20 | <1e-6 |
| s20/F0196共享口面 | 1 | <1e-6（H215） |

54 source IDs互异、20meridian责任段无漏，F0196由stock只计一次、head仅引用共享接口。同carrier联合界不得拆成未经证明的逐源内部缝对应；该联合不丢source ID。每个比较链内部已先相加，覆盖后的有限区域并集取max，故packet `<0.000859 mm` 接受；`.001-.000859=.000141 mm` 是本stock数学预算的保守余量，不是已测/保证的后续内核误差或全工件最终裕量。

最后新核对：44 root原点/covered-v边身份、三leaf消费值、C5导数/完整Fu外延有理不等式、s7/s8新组合、所有chart倍率与各阈值、54/20去重及max/余量精确算术均exit 0。没有重跑任何已接受的carrier、root矩阵、capture或肩求逆。

STF01—STF05均关闭，STF06正式受限接受。可供SI消费 `stock-54-packet.json` 的54 source责任、各有限source region引用、默认数学CSG域及上述预算；冻结文件中的旧pending review字段由本节与所引独立叶接受按本scope解除，实施者可另出接受汇总。原生重建/布尔、参数编辑、全件其他源区域和P3总集成接受仍归各自任务，不自动进入P4。
