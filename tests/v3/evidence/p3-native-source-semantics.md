# P3 当前PRT源定义语义独立审查与局部证据合同建议

日期：2026-11-11。独立审查实例：`/root/p3_region_plan_review`。目标是用户提供的**现有PRT所保存的几何/拓扑**，不是未知版本的原STEP、原设计意图或实际加工件。本次只读安装头文件、采集/JSON传递源码、C5五条边及一个新根面的完整loop；不全量重审141个detail，不运行NX、旧测试、Git或hash。本文是供TL再派实现的合同建议，未修改任何门禁、采集代码或状态。

## 发现与最小纠正

1. **中等：把历史源精度与当前PRT定义混成一个永久未知项，会错误阻断P3。** 受影响的是“所有native/SP近似未知，因此现PRT局部区域不能定义”的解释规则，而不是已验采集代码。模型原有曲线或SP可能在建模/导入时已近似，但它们现在就是目标PRT的定义。若验收目标没有要求还原原STEP，则相对原STEP的历史差异不是本任务的新误差项。最小纠正：单列 `target=current_prt`、`historical_STEP_accuracy=not_required_for_this_target`，随后仅按当前PRT的存储表示及读取时转换分类；用户共享意图仍不替代几何定义。
2. **中等：仅看到返回type102或请求容差，不能判定它是原存曲线还是新近似。** 受影响字段为保存树的`geometry_class`、`geometry.type`、FIN和全局`mapping/options`。混用会把生成曲线误当源精确定义，或反过来把可直接使用的源SP永久视为未知。最小纠正：以每条边的**几何类10/11/12/13**、其源依附位置、适用映射和rc/state记录建立表示来源账。注意`edge_class=1`指OPEN拓扑边；10..13记录在`geometry_class`，两字段不可混淆。
3. **中等：`geometry_details_complete=false`是当前reader的保守固定输出，不能独自证明局部trim资料仍缺失。** [ReferenceGeometryNative.cpp](../../../src/bridge/V3/ReferenceGeometryNative.cpp:374)明确始终输出INCONCLUSIVE/false，因为reader未做完整裁剪判定。若下游把它当作任何离线数学证书均无法解除的条件，将形成无法推进的门禁。最小纠正：保持原字段不变，另建带来源、验证覆盖和具体未决项的派生局部证书；TL审核后再由SI显式接入。本文不授权直接忽略旧gate、改成true或宣称整件已验证。

未发现必须为这次语义澄清重读141面的理由。真实缺口必须落到某个源表示、状态、参数映射或有限域，而不是泛称“native精度未知”。

## 安装API合同：可以依赖什么

本次依据是 `C:/0sf/ug/UGOPEN` 内现有头文件；引用说明适用于所核安装/API组合，不自动扩展到任意版本。采集运行有效性、只读保全和源选择继承已接受证据。

| 依据 | 明确合同及对P3的含义 |
| --- | --- |
| [uf_brep.h:96](C:/0sf/ug/UGOPEN/uf_brep.h:96) | NX模型中的边可由3D曲线或附着FIN的SP曲线定义；容差边由FIN上的SP定义。几何/拓扑须联合解释。 |
| [uf_brep.h:123](C:/0sf/ug/UGOPEN/uf_brep.h:123) | 无论边是否tolerant均可请求SP、3D或两者；不存在的所请求数据会被计算，必要时近似。因此“返回了SP”不等于“该SP原已存于PRT”。 |
| [uf_brep.h:458](C:/0sf/ug/UGOPEN/uf_brep.h:458) | ask_geometry从模型查询几何；曲面geom_sense描述surface normal与face normal的方向关系。blend、intersection等不能直接以已有输出结构表示时，需要映射/容差。 |
| [uf_brep.h:482](C:/0sf/ug/UGOPEN/uf_brep.h:482) | 对tolerant edge请求FIN几何时，返回的是该边成为tolerant时产生的SP；调小本次读取容差不会改善它们的历史精度。它们仍是**当前PRT源定义**，不是必须追溯原STEP才能使用的数据。 |
| [uf_brep_types.h:863](C:/0sf/ug/UGOPEN/uf_brep_types.h:863) | BSURF_DIST为近似B面时的part-unit容差；CURVE_DIST为FIN/edge B曲线近似时的part-unit容差。这是有语义的API近似合同，不能降成完全无效的“任意数字”。 |
| [uf_brep_types.h:895](C:/0sf/ug/UGOPEN/uf_brep_types.h:895) | extraction mapping把模型类型映射为返回B曲线/B面；明确列出BLEND→BSURFACE、INTERSECTION→SPLINE。全局存在映射不代表每个普通样条或解析面都被近似。 |
| [uf_brep.h:165](C:/0sf/ug/UGOPEN/uf_brep.h:165) | 单面读取可产生该面自己的拓扑。未flatten时SP可能跨周期/平移一个period，仍可正确解释；UV矩形或简单端点相等不是完整trim判据。 |
| [uf_brep_types.h:920](C:/0sf/ug/UGOPEN/uf_brep_types.h:920) | states报告潜在问题，flag bit0表示fixed；不能仅以rc0忽略非空states。状态空间还含UF_CURVE、UF_MODL代码。 |

对转换曲线，`CURVE_DIST`可作为P3的**声明性API提取容差依赖**，附有效调用、状态和具体表示来源；不是毫无承诺的未知。另一方面，这些头文件未给出一个由现有日志独立验证的双向Hausdorff/逐点同参数证书，也未说明任意两个提取表示共享参数。不能把“请求0.0001且rc0”写成已经实测全域最大误差0.0001，更不能直接写P6通过。需要的证据等级应明确为“依赖所列UF近似合同”，与“独立数学证明/实测误差”分开。

CURVE_DIST单位是part length unit；不得把同一个数直接当作FIN的无量纲UV偏差、角度容差或两曲线同参数距离。若要把它与C5界相加，必须先声明所用API距离含义及方向满足三角不等式的同一度量；不能自动把一侧载体距离提升为完整trim的双向几何误差。

## 按当前PRT存储表示分类

`UF_BREP_ask_edge_class`两个输出及枚举见 [uf_brep.h:436](C:/0sf/ug/UGOPEN/uf_brep.h:436)、[uf_brep_types.h:232](C:/0sf/ug/UGOPEN/uf_brep_types.h:232)。建议使用下列来源分类，避免一个`native_unknown`覆盖全部：

| geometry_class | 当前PRT中的主要定义 | 本次返回对象如何解释 |
| --- | --- | --- |
| 10 NORMAL | 边有3D曲线 | 未被适用映射转换的曲线描述，可作为当前模型曲线定义。另请求FIN SP时该SP可能为计算结果，不能仅因type102认定是原存SP。现有圆弧路径使用UF_EVAL返回模型圆弧/参数域，仍须解决它与FIN/拓扑方向的关系。 |
| 11 INTERSECTION | 两个曲面隐式定义3D交线 | 源定义是相邻曲面加有限拓扑分支。当前INTERSECTION_TO_SPLINE使返回3D type102成为转换表示；FIN亦可能为计算的SP。可以依赖API容差合同，或由已存曲面/FIN及分支做独立有界重建，不能把该样条说成原有3D控制网。 |
| 12 TOLERANT | FIN定义边曲线 | 该FIN原有SP可按ask_geometry特殊说明作为当前PRT的实际源trim表示；历史建模时准确度相对原STEP不另立缺口。请求3D曲线时可能从SP计算/近似。相邻两面各自SP的差别要按现PRT的容差拓扑解释，不强求未经证据的精确重合。 |
| 13 SP | 有SP，但不是tolerant edge | SP是源表示路线；请求3D曲线可能计算。仍须记录具体FIN、参数周期和适用映射，不从“非tolerant”推断所有返回对象原样无转换。 |

本次有限样例没有class12/13，故这里只确认其API语义，没有宣称已核模型中所有这两类实例。对原有解析面、回转/拉伸及其可直接描述的母线，当前请求没有SIMPLIFY或对应类型重映射；应按返回的模型定义使用，而不是无证地给每个原始控制点再附“STEP近似未知”误差。若某实体确属blend映射、状态修复、周期重参数或不支持的类型，则单独记该转换，不泛化至所有141面。

## 五条C5边的实际分类

本次读取的C5来源及边号见 [C5报告](../../../workspace/v3/p3/P3-SWEPT-ANALYSIS-01/shoulder-trim-correspondence-c5.json)。五条边实际均为`edge_class=1`（open）、`geometry_class=11`（intersection）、`edge_class_rc=0`；edge和FIN的`geometry_rc=0, states=[]`，返回几何均type102。

| P1边 | 来源面/已保存detail | 本次CURVE_DIST(mm) | 表示来源 |
| --- | --- | --- | --- |
| E0154 / session63535 | [F0004](../../../workspace/v3/p3/P3-SPHERE-01/native-02-f0004/detail-snapshot.json) | 0.001 | 隐式交线→3D spline；FIN可能为计算SP |
| E0410 / session63791 | 同一F0004 detail | 0.001 | 同上 |
| E0139 / session63520 | [F0022](../../../workspace/v3/p3/P3-REGIONS-02/native-c2-01-F0022/detail-snapshot.json) | 0.0001 | 同上 |
| E0503 / session63884 | 同一F0022 detail | 0.0001 | 同上 |
| E0549 / session63930 | [F0125](../../../workspace/v3/p3/P3-REGIONS-01/native-02-F0125/detail-snapshot.json) | 0.001 | 同上 |

三份来源均记录FINSP=1、EDGE3D=1、flatten=false、映射两项；`topology_state_count=0`，`incomplete_observed=false`。虽然`root_topology_states_omitted=true`且数组为null，此处count=0，不能把它解释成“存在未知非空root问题”。若其他记录count>0则不同：不能用本例替它消除缺口。

因此，C5的精确Bernstein界严格作用于这五条**已转换的保存表达式**；原审查对这一数学界的范围无需推翻。需要纠正的是将它们的转换关系写成“完全未知”：这里有明确class11、映射、容差、rc和空state证据可支撑API合同级输入。尚无FIN—3D同参数/方向证明，不能因为两者都返回type102就自动关联其参数。

### 既有相邻来源的复用与预算

同一P1边可能在两个相邻面的已保存detail中各有一份提取表示。可以选择已接受来源中请求容差更适用的一份，避免为相同目的重新调用NX，但必须保存各自完整source引用、options/state和当前树边身份，再以P1互反邻接、语义绑定及有界几何/参数对应建立关联。不得把一个snapshot的edge/FIN直接拼到另一个snapshot树中，或因为tag数值相同就继承更小容差。

具体事实纠正：本次另核 [F0169 STOCK01](../../../workspace/v3/p3/P3-STOCK-01/native-01-F0169/detail-snapshot.json)，snapshot为`P3-DETAIL-803b4a6a64d7416da9eed9b402260c8c`，其curve/surface tolerance**实际均为0.001 mm**，不是0.0001。其当前树63791/63930均class11，返回4/14控制点spline。因此这份现存F0169数据不能作为C5 E0410/E0549已获得0.0001提取合同的证据。F0022既有0.0001只适用于其各自对应边，不能借给其他边。

未来证书应按逐实体实际options选择来源：若已经存在更小请求容差且语义绑定成立的同边表示，可以复用；若不存在，则保留0.001的API合同依赖，或基于源隐式曲面交线/源SP作新的有限数学证明。不要虚构较紧预算，也不因旧容差较大就自动要求重新采集全部相关面。本次没有重算C5界。

对class11，若两个源父面定义已经取得，应优先评估“父面方程→交线唯一分支→源有限拓扑/端点/方向”的局部证明路线。它直接使用当前PRT的隐式交线定义，可以使旧0.001转换spline仅作为带明示预算的辅助观察，而不必把该近似表达式强制作为最终重建边。必须真正证明分支和完整有限域，不能挑选几处相近点便声称摆脱了转换误差；同时保留旧转换观察及其不一致说明。如果后续确需更细转换，应登记新的精度输入需求及影响范围，不称作“原成功证据失效所以重验”，更不自动新增原生调用。

## 一个新root完整loop：F0123

有限核查对象为 [P3-CARRIERS-01/native-23-F0123/detail-snapshot.json](../../../workspace/v3/p3/P3-CARRIERS-01/native-23-F0123/detail-snapshot.json)，不重审22根总账的数学结果。

- root为type204 torus，geometry_rc=0、states=[]；一个loop、五个FIN，edge_coverage_complete=true、incomplete_observed=false、topology_state_count=0。
- options为FINSP=1、EDGE3D=1、curve/surface tolerance均0.0001 mm、flatten=false；没有把两个stock半面接口合并成一条边。

| 当前树edge tag | geometry_class | 返回边几何 | FIN几何 | 对当前PRT的可用含义 |
| --- | --- | --- | --- | --- |
| 63634 | 10 | circular_evaluator | type102/order2/2点 | 模型已有圆弧的评价器表达；FIN是否原存不能由返回类型认定 |
| 63618 | 10 | circular_evaluator | type102/order2/2点 | 同上 |
| 63565 | 11 | type102 | type102/order3/3点 | 隐式交线的转换边/SP路线 |
| 63775 | 11 | type102 | type102/order3/3点 | 同上，独立保留 |
| 63645 | 10 | circular_evaluator | type102/order2/2点 | 模型已有圆弧的评价器表达 |

五个FIN调用rc0、states均空，两个spline边rc0/states空。三个圆弧边的`geometry_rc=null`是代码按已验路径走UF_EVAL而不调用该边的ask_geometry，不是自动失败；它们的class必须为10才会通过当前路径。三个arc仍带`direction_relation=unverified`，需要用源端点、角域、FIN和方向码建立具体关系，不能忽略，也不必为取得已经存在的圆弧定义再次读取。

这一树已包含有限trim的构造输入：root、loop/FIN连接、每条曲线和范围、两级方向及源状态。它没有自动完成数学解释；接下来应处理该一个五FIN域，而不是因为全局false就宣称其完整trim原则上不可知。

## 17位double传递的含义

[ReferenceGeometryNative.cpp:106](../../../src/bridge/V3/ReferenceGeometryNative.cpp:106)拒绝非有限值，并以`std::setprecision(17)`输出；stream使用classic locale。对IEEE binary64，17位有效十进制数字足以让正确的round-trip解析恢复原double，不能把这种序列化一概说成引入了未量化的机械精度损失。它也不会增加API返回值本身的精度。

当前桥接 [ReferenceGeometry.cs](../../../src/bridge/V3/ReferenceGeometry.cs:105) 使用StrictJson detail路径；[M2Bridge.cs:6492](../../../src/bridge/M2Bridge.cs:6492)启用数值解析，[M2Bridge.cs:6679](../../../src/bridge/M2Bridge.cs:6679)以InvariantCulture解析Double，再由 [M2Bridge.cs:6416](../../../src/bridge/M2Bridge.cs:6416)以`R`输出。源码没有故意截为固定小数位；不是把每个坐标四舍五入到0.001 mm。

这支持“保存binary64值为后续精确有理分析的数值语义”。它不是本次对所有运行时/141个payload进行的逐位验证。可机核合同应声明是否以原native JSON token或其无损double往返为依据；如果某条传递链确实重算、变成低精度float、格式化为短固定小数或发生坐标变换，那项要另计。不能把已发生的浮点旋转当作单纯序列化，也不能将17位文本当作十进制精确实物尺寸。符号零等编码差异应与几何数值差异分开。

## 状态、容差与具体阻塞条件

保存的`geometry_rc`、`edge_class_rc`、geometry states和topology count应同时进入合同。头文件明确的相关state包括220(vertex_not_on_curve)、222(vertex_not_on_surface)、223(edge_not_on_surface)、224(loop_inconsistent)、225(non_g1)、227(edge_tol_too_big)、228(inconsistent_geom)、229(invalid_geom)，以及共享UF_CURVE/UF_MODL代码；未知代码不能默认为成功。fixed标志也不能一概视作“源定义未经改变”，需要按该调用语义记录处理。

本次选取记录均空state，故可以依赖成功提取的API合同；未测得提取误差不等于API没有任何合同。若确有未保存非空state、参数源类不明、截断/overflow、曲线域缺段、source bind歧义、周期支路或方向不明，应给出实体级未决项。`CLEAN_TRACE`只继承只读/调用证据，不能代替这些几何条件。

## 建议的可机核局部证据合同（待TL派实现）

建议新增独立派生合同，例如 `p3-source-trim-local-region/1.0`，不改原snapshot，不写回PRT，不做P6整件比较器。每个有限区域至少包含以下记录：

| 记录组 | 必须可核的内容 |
| --- | --- |
| target/source绑定 | 当前PRT目标、接受的snapshot路径/ID、选体、单位/帧、P1语义到当次对象的绑定证据；同树节点路径、局部ID/tag及scope。禁止把tag跨会话当稳定ID。历史STEP准确度仅在确为目标要求时进入预算。 |
| 每实体表示来源 | 原geometry_class、拓扑edge_class、输出type、原/转换/计算表示类别、适用mapping、options、读取rc/states。FIN来源无法仅由class推断时明确`computed_or_unresolved`，不能随意升为raw。保存原基、权重和完整参数域。 |
| 数值语义 | binary64-as-recorded或其他明确语义；无损序列化依据；单位/坐标变换和所用舍入包络。API提取容差、独立计算误差、候选拟合差必须分列，不混为一个“native未知”。 |
| 源有限trim | 全部loop/FIN/edge/vertex连接和方向；曲面参数约定、周期lift/接缝/奇点处理；FIN参数域全覆盖；简单性、孔/外环归属和域内侧。允许采用周期曲面上的闭环，不强迫raw UV端点数值等于同一周期。 |
| 源表示间关系 | 原存SP用曲面复合`S(u(t),v(t))`作为该面源边界；原存3D曲线按其范围；隐式交线按两面和拓扑分支。生成SP/3D曲线写明API依赖或独立全域关联证书，参数映射、orientation、端点与中间域一并覆盖，不以有限样点代替。 |
| 候选局部区域 | 采用的参数/关系、carrier、有限工具、stock角色、每段退出/封口条件、材料侧、布尔顺序；每个源patch到候选patch的映射及不漏面/不多面证据。单个载体距离小不能代替这些内容。 |
| 结果与未决项 | 分别列`source_definition_classified`、`source_trim_domain_validated`、`candidate_local_region_defined`、`candidate_to_source_relation`和明确API依赖/误差范围。缺项指向具体实体、证明命题或最小补证，不能只写全局false。保留`execution_approved=false`及后端门禁。 |

建议分三个独立接受层级，避免一次要求完成P6才允许P3进展：

1. **源定义可用**：当前PRT绑定、表示来源及成功提取合同完整，输入足以定义局部参考域。即使reader原字段仍false，也可有这一派生结论；若使用转换表达式，明确API合同依赖。
2. **有限数学区域已定义/有条件相容**：完整trim域、方向/材料侧和候选有限工具已有可审查定义，具体剩余假设列明。用精确/区间/解析方法覆盖需要的全区间；不将141条read成功当覆盖结果。
3. **局部对应证据满足P3约定**：逐源patch的有界对应、无遗漏/额外分支和参数消费满足本阶段合同，经独立审查及TL接收后，才由实施者更新局部DAG状态。它仍不是原生构造或P6几何验收，也不能绕开现有执行gate。

可直接推进的最小实例是上述F0123：按一个五FIN loop分类3条原圆弧/2条隐式交线路线，继承已读torus/邻面定义和states，解参数方向、周期和两条stock交线的有限域，验证候选区域与该域的关系。若已有数据足够，则只补有界数学；若某个生成SP/方向依赖确实无法确定，再仅提出该实体的最小补证，而非重读全体或追索与当前目标无关的STEP历史。

### 具体schema外形及判定要求

以下为建议的必填结构，不是已经生成的证书，也不是让实现填写固定false的占位层。数组必须列出该区域的全部相关对象，`assertions`须引用可重算的算术/拓扑证据，而不能仅由字符串“已验证”判定通过。

```json
{
  "schema": "p3-source-trim-local-region/1.0",
  "target": {
    "kind": "current_prt",
    "reference_snapshot": "accepted snapshot path and id",
    "body_binding": "source-selected body record",
    "units": "mm",
    "frame_binding_evidence": "artifact JSON pointer",
    "historical_step_accuracy": "not_a_target_requirement"
  },
  "region_id": "stable P3 region id",
  "sources": [{
    "source_id": "unique certificate-local id",
    "snapshot_path": "existing accepted detail path",
    "snapshot_id": "actual saved id",
    "entity_pointer": "/detail/0/diagnostic/topology/...",
    "source_binding_evidence": "P1/session-local association pointer",
    "representation_role": "stored_definition|implicit_definition|api_derived|unresolved",
    "geometry_class": 11,
    "topology_edge_class": 1,
    "returned_geometry_type": 102,
    "active_mapping": "INTERSECTION_TO_SPLINE",
    "api_contract_reference": "uf_brep_types.h CURVE_DIST_OPTION",
    "requested_curve_tolerance": 0.0001,
    "tolerance_unit": "part_length_unit",
    "state_evidence_pointer": "rc, geometry states and topology count",
    "numeric_semantics": "binary64_as_recorded"
  }],
  "source_trim": {
    "surface_source_id": "source reference",
    "loops": [{
      "loop_id": "local loop id",
      "ordered_fins": ["all local fin ids"],
      "periodic_lift_evidence": "proof pointer or not_applicable",
      "orientation_and_inside_evidence": "proof pointer"
    }],
    "boundary_representation_links": ["source/API/parameter-map evidence pointers"]
  },
  "candidate_region": {
    "definition_pointer": "bounded construction record",
    "parameter_decision_refs": ["accepted decisions"],
    "source_patch_mapping": ["all source patches and candidate partners"],
    "stock_and_material_role_evidence": "source-normal/occupancy or explicit condition"
  },
  "error_budget": {
    "metric_and_domain": "explicit metric, direction and covered domains",
    "api_extraction_dependencies": ["source ids and applicable contracts"],
    "numeric_and_construction_bounds": ["exact/interval proof pointers"],
    "excluded_from_target": ["historical STEP deviation"],
    "unresolved_terms": []
  },
  "assertions": [{
    "id": "stable assertion id",
    "verifier": "bounded offline verifier id/version",
    "inputs": ["exact source and candidate pointers"],
    "domain": "complete parameter intervals or topology component",
    "result_evidence": "recomputable proof record"
  }],
  "result": {
    "source_definition": "accepted|blocked",
    "source_trim": "validated|conditional|blocked",
    "candidate_local_region": "defined|conditional|blocked",
    "candidate_source_relation": "validated|api_contract_conditional|blocked",
    "conditions": ["specific unresolved propositions, not global slogans"],
    "independent_review_reference": "review artifact",
    "tl_acceptance_reference": "decision artifact",
    "execution_approved": false
  }
}
```

实现验收至少须检查这些条件，条件是否满足来自实际证据而非固定状态模板：

1. **来源集合闭合**：每个source_id唯一、引用对象存在且与接受的采集证据一致；所有源patch及FIN必须被枚举。另一个snapshot仅可作为带独立绑定证据的另一source，不能替换树内对象。
2. **表示类别相容**：几何类、返回type及实际mapping决定来源类别；class11转换spline不能标stored_definition；class12原SP不能被统一降为“未知STEP近似”。surface、edge、FIN分别记录，正常圆弧的UF_EVAL成功路径不能因ask_geometry rc为null而误判缺失。
3. **API状态可接受**：必须核调用rc和所需state完整性。topology count=0且数组省略可解释为空；count>0而数组缺失、未知state、overflow或源绑定歧义不能通过。非空fixed state需专门处分记录，不能统一吞掉。
4. **参数/数值可解释**：单位、基、完整域、权重、周期及方向明确；binary64传递和后续浮点变换分别记账。任何参数映射都要证明其覆盖域和方向，不默认FIN与3D边同t，不把part-unit容差当UV距离。
5. **trim域真的封闭并选对内侧**：核周期等价下的loop连接、全部非零span、外环/孔、奇点处理、无未解释自交/分支；有向面与材料侧使用API定义及现树证据。只检查端点或bbox不够，但可以用现有解析/区间资料完成，无需默认再读native。
6. **候选局部区域真的对应**：核每个有限patch、截断、封口和退出分支，无遗漏或额外暴露边；对依赖的误差项用声明度量和全域证明组合。仅载体成员残差小或用户关系已确认不能通过此项。
7. **状态可取得正结论**：满足来源条件即可接受`source_definition`；满足全部有限域和局部对应要求后，允许派生source_trim/candidate关系得到validated或明确API合同条件接受。原reader false不是这七项之外的永久否决项。若尚有关键条件，则仅阻塞对应region/层级并列最小命题，不把全体141面统一保持不可解释。

独立审查及TL接受仍是提升派生结论的前置；后端执行批准另行处理。建议首个实现直接服务真实22根区域证书，使用现有完整树和上述具体判据；不增加仅复制旧false、没有可达到通过条件的新层。

本建议不批准release、不认定G/native精度达标，不替换旧数据或门禁。它纠正的是证据语义与推进粒度：当前PRT中已有定义应作为目标使用，读取时转换应按具体API合同处理，完整trim和局部构造关系应由可复核的有界数学补齐。
