# P3 INTEGRATION03 独立软件审查

审查者 `/root/p3_acceptance`，2026-11-13。仅拥有本文件；未改被审实现、原输入、旧证书或台账。审查对象为 `src/nx_sketch_mcp/v3/p3_integration.py`、`tests/v3/test_p3_integration.py`、`tests/v3/run_p3_integration.py`，及 `P3-INTEGRATION-03/integrated-regional-ledger-c2.json`、`integrated-regional-ledger-c3.json`。SI确认C3暂冻结供最小反例。未执行NX、Git、hash、旧pytest矩阵或旧数学生成器。

## 结论

**CHANGES：C3不能作为P3阶段就绪验收器接受。** 当前输出可作为待修正的局部证据汇总。11项P3要求全部在代码内固定为open，因此真实输出仍 `p3_ready=false`、`execution_approved=false`，此次反例没有造成实际建模放行。这个固定false不关闭下列接受语义缺陷，也不构成完整P3整合实现。

直接读取C2/C3，两者唯一不同顶层部分为新 `decision_overlays`。新Dshaft及肩联动决定已逐字落盘；旧C5保持原样，新overlay保留源分类并给出D/2精确默认值，这一版本化方法可取。肩联动未直接加入同trim或G1；但决定本身的语义绑定仍缺校验。

## 集中发现及关闭标准

| ID / 严重性 | 位置、实际问题与影响 | 最小修复及复验标准 |
| --- | --- | --- |
| PI01 / 高 | `_gate`约63行仅检查state字符串和evidence真假；`test_gate_needs_every_reviewed_requirement_with_evidence`甚至以任意`independent review`字符串列表作为正例。`evidence='false'`同样放行。当前build没有传入accepted的真实路径，所以这是门禁合同缺陷，并非已发生执行批准 | 就绪必须消费已绑定的实际区域构造/参数/来源、所需要求集合及受限独立接受结果；不能以任意非空字符串、存在路径或孤立accepted布尔替代。新增有真实数据关联的最小正例及失配/字符串/缺项反例；execution仍与planning ready分离 |
| PI02 / 高（功能缺失） | `requirements`约194行全部硬编码open/空证据；`REGION_EVIDENCE`只读JSON后丢弃内容，输出path和固定scope；未消费HEAD02、SHOULDER-STOCK04、SHAFT02新区域闭合。construction仍直接复制旧节点、order unresolved。当前功能只汇总局部证书，不能交付用户要求的完整P3计划验收 | 接入实际区域成果及其具体构造、参数消费者、覆盖/接口和各自证明范围。未获证明部分仍open；新已证部分必须有真实消费路径而非永久false。验收应展示一个已证明要求可提升、缺失来源/几何前提不可提升。不能为凑ready降低区域数学证据标准，也不要求先实现P4/P5/P6 |
| PI03 / 中 | `build_decision_overlays`约74行只核两个decision_id，忽略D决定scope、answer/authority及source_binding；同ID改为fixed且未确认仍输出independent D/2。肩scope原样复制，也没有确保本次确认的own-axis/own-stock-trim/no-added-G1关系 | 对本次两决定的schema、明确确认语义、来源关系及允许scope作一致性绑定；输出只消费已确认关系。定向反例：同ID但冲突分类/错误源C5/同trim或G1扩权须拒绝；现有两个真实决定正例保留。无需另造密码学信任或修改旧C5 |
| PI04 / 中 | 根证书约132—158行只核snapshot匹配，然后无条件写`accepted_local_scope_M2`；将当前F0109证书status改为failed仍产生该接受标签。`REVIEWS`只是常量路径，未消费与所引用证书相符的限定接受结果 | 受限接受须与证书对象、schema/status、索引引用和独立审查具体范围一致；失败/不适用结果不可标accepted。只需覆盖本模块消费的已知证书合同，不重算22数学证明。复验失败status、错对象/引用与当前有效证书正例 |
| PI05 / 中 | 圆弧约140行检查`len==3`及edge集合是FIN集合子集，但不检查三条edge唯一及完整的class10预期集合。替换其中一条为同root另一条，仍输出3条accepted，实际只有2唯一边，漏一条边被计数掩盖 | 从已绑定root FIN/证书来源得到预期class10边集合，要求一一对应及恰当父面关联；重复替代/漏边拒绝。保留66条有效当前输入，不重跑圆弧数值生成器 |

这些问题先集中提交，实施者自查不计独立关闭；修后只复验实际改动所涉新反例及必要正例，不运行已有数学或广泛测试矩阵。

## 已执行的最小独立反例

环境：cwd为项目根目录 `C:/0sf/1PROJECT/AI/design/nx-sketch-mcp`；PowerShell；设置 `PYTHONPATH=src`、`PYTHONDONTWRITEBYTECODE=1`。使用 `C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe -` 接收UTF-8 here-string脚本。只导入新整合模块并在内存改其`_read`结果，不调用任何证书生成器；原始文件全部只读。实际一次命令exit 0。基线及每项变异重新调用的是新纯汇总函数，不是旧测试/数学重跑。

复现公共准备：

```python
from copy import deepcopy
from pathlib import Path
from nx_sketch_mcp.v3 import p3_integration as m
root = Path.cwd()
original = m._read
cache = {}
def cached(root, path):
    key = str(path).replace('\\', '/')
    if key not in cache:
        cache[key] = original(root, path)
    return deepcopy(cache[key])
```

各独立变异（每次设`m._read`为以cached读取的包装函数，调用`m.build_integration(root)`；变异间恢复只读基线，不串接变异）：

1. 直接调用 `_gate([{'state':'accepted','evidence':'false'}])`。
2. D决定保持ID，改`scope.shaft_outer_diameter='fixed; not editable'`、`scope.outer_endpoint_radius='unrelated independent radius'`及`answer='not confirmed'`。
3. 取`idx=cached(root,m.PATHS['exits'])['results'][0]`；读该certificate_path后对`m._resolve_pointer(doc,idx['json_pointer'])['status']='failed'`。
4. 读`m.PATHS['arcs']`，取第一root的三记录索引，以第一记录deepcopy替换第二记录，保持数组长度和root匹配。

原始命令输出：

```text
GATE fabricated string: True
baseline counts: {'responsible_faces': 235, 'local_root_exit_certificates': 22, 'local_class10_arcs': 66, 'local_shoulder_seams': 44, 'fully_explained_faces': 'not_established'} ready: False
conflicting decision yields: independent shaft_outer_diameter_mm/2
failed certificate accepted labels: [('F0109', 'accepted_local_scope_M2')]
duplicate arc retained as 3: [('F0109', 3, 2)]
```

PI02为静态数据流事实，不需另造一个重复失败测试。没有对新证书数学正确性作数值复验；这些反例检查的是整合器如何解释已知来源与局部接受状态。

## 正面核对及适用限制

- 库存使用`normalize_snapshot`，责任集合与实际P1集合比较，并拒绝责任重复；因此235是责任核对，代码正确保留`fully_explained_faces=not_established`，不能改称235面几何验收。
- 成员、placement和source-map的成员集合/顺序及flank集合有核对；root证书快照与root来源快照核对有效，但不能替代PI04所述证书状态和限定范围。
- 局部FIN、图窗、各圆弧参数域及肩seam记录有实际提取，scope显式保留“非完整trim/材料”；预算没有把异域局部界盲加成全件界。
- CLI用新输出路径及`open('x')`保护既有产物，不调用NX；C3没有改旧C5默认值或证据。当前六旧决定列表与两新overlay分开，不自行承诺原生传播、无限编辑域、同trim或G1。
- `f0093-fin-unit-investigation.md`明确区分观察到的1000比例与已证明规则；本审没有将其变为一般单位换算。有限面域问题须由对应几何/API证据处理，不由整合器字符串补证。

最终软件接受待PI01—PI05集中修复及定向独立复核补记；P3阶段整体接受另见[p3-stage-acceptance-20261113.md](p3-stage-acceptance-20261113.md)。

## C4 集中修复复核

SI提交当前 `p3_integration.py`、原测试及新`test_p3_decision_overlays.py`、CLI与`integrated-regional-ledger-c4.json`。独立复核只读改动及新产物，继承SI本次定向8 passed的实际工具转录，不再执行相同反例或旧数学。

**PI01、PI03、PI04、PI05关闭；受限接受C4为局部证据索引与已确认意图叠加。PI02仍OPEN，完整P3整合功能未交付。** 本结论与实施者主动限定的交付范围一致，不以移除就绪计算冒充阶段完成。

- PI01：移除`_gate`，输出不再有`p3_ready`，明确`readiness_assessment=not_assessed_by_evidence_index`；CLI相应调整。这样关闭任意非空文字产生就绪结论的路径，但没有实现完整区域就绪判定。执行仍false。
- PI03：两决定逐项绑定schema、authority、实际答复、完整scope及C5/前置决定/shoulder比较来源；Dshaft fixed、未确认答复、错误C5来源、追加G1都会被新的分支拒绝。原C5不改，默认D/2仍精确派生。真实C4保持各自roll轴/各自stock trim、同trim=false、追加相切=false。
- PI04：证书schema限三种已审合同，要求确切受限status、P1快照、detail快照ID/路径及execution严格false；原failed反例到此抛ValueError。M2审查正文也需包含最终受限接受和全部22根混合索引的文字。后者是受控当前工作区中的人审引用辅助核对，**不是可认证任意改写文档的通用信任机制**；本接受只覆盖所列实际来源/证书的索引，不把它升级成自动几何验收器。
- PI05：预期三圆弧来自该root FIN中实际circular evaluator边及邻面；新记录必须恰三条、edge/neighbor对唯一、字典与预期完全相等。因此重复边替代另一边或错邻面不能再由计数掩盖。直接读C4，22组均有3个唯一p1_edge，66责任与旧数值证书范围保持。

C4读回显示235仍仅责任、22局部退出、66圆弧、44seam，`fully_explained_faces=not_established`，11要求仍open。全部引用根status为已接受的conditional tube graph；本审未重新计算其数值。新区域source、实际有限构造/参数消费者、顺序和完整P3覆盖的真实消费仍按PI02继续，不能仅通过文件存在、两句accepted文字或固定false关闭。

## 真实候选构造 C1—C4 增量审查

2026-11-13，独立实例 `/root/validation_r68`；本节的C1—C4指 `regional-construction-c*.json`，与上一节的旧局部索引版本C4不是同一产物。审查 `regional_construction.py`、`construction_domain.py`、`flank_construction.py`、`p3_integration.build_regional_construction`，相关新测试、只写新文件的CLI及实际产物；没有修改实现、运行旧测试、重算C5或NX。

**受限接受最终regional-construction-c4为实际求值的默认/编辑候选、显式局部证据消费和顺序图；PI06修复关闭。PI02完整P3整合仍OPEN。** 135节点中113为stock/尾槽及22组五步候选CSG，22为头部显式carrier；头部尚无有限闭实体，stock/肩/根柱材料和统一总预算仍未完成。当前whole_part_bound_mm=null、execution_approved=false与这些实际缺口一致，不作为完整P3就绪结论。

### PI06：stock轮廓在整合时丢失，已关闭

首次C1的 `stock_revolve.profile='stock_profile'`，但返回物只含section6，求值后的22顶点/22段stock_profile未透传。实际只读C1即可复现，不依赖伪造输入或运行建模；参数数值不能替代该有限轮廓对象。最小修复要求包含两个实际profile并检查所有节点profile引用可解析。

SI保留C1，C2增加profiles映射（stock_profile与section6）及引用检查，单独默认正例1 passed，新增missing_profile负例1 passed；后续C3/C4保留修复。独立实际产物审计确认45个profile引用全部可解析、22顶点/22曲线按起终点形成闭环、section6六边保留。复验标准满足，PI06关闭，无须重复旧CSG或C5测试。

### 数值、编辑和依赖核对

- Stock实际消费29driver合同及46派生公式，辅助封口使用同一个Y_mouth和tail基准；Y_mouth默认+17、Y17默认−1没有别名冲突。受限AST算术仅处理合同中的加减乘除幂/tan/sqrt；未知独立输入、非有限值、正尺寸/角范围、严格站序及弧端点不相容拒绝。1e-7弧端检查是binary64候选检查，不作为源误差证书。
- Head实际重算mouth、两fillet和六sector分支的半径/接触量，shared mouth消费stock.Y_mouth；输入正性、锥正nappe、内切根号/分支等必要条件有检查。这些是显式无限carrier/参数图，不能称头部完整有限域、全部参数已被最终实体消费或全部编辑合法。
- C5相关编辑会调用既有build_parameters重新解与区间守卫，Dshaft同时传入stock和C5。每member轴由phase+i·2π/22实际求值，22索引及44面来源成员对应检查；所有非空overrides均使默认直翼chart界及尾部源对应界失效。未变化的默认输入不为换评审者重解旧C5。
- 给定六边截面在辅助Rcap=13.1、roll=15内，简单环及pole/端点范围守卫保留。straight→roll∩stock→union→subtract的实际对象依赖顺序完整。共同理想轴和−71站是候选辅助构造，源自身轴差/有限trim及不过切仍需其独立证据，不能由一个true字段推成全区域。
- 尾槽截面、s10/s14台阶、s19分支和s8内侧等为**必要条件**；domain明确not_established，限制列表保留简单母线、完整退出、头/stock/股间clearance等未闭事项。因此本审不把通过这些守卫提升为任意编辑有效性。
- 44默认chart预算只加C5源轴点到候选stock轴的L1平移，两个项属同一载体图→理想默认C5对象链。按精确binary64分数独立核44项，保存的nextafter总界均覆盖源chart界加真实两坐标绝对值和；最大1.2226886813475792e-5 mm。没有把有限域边差、头/stock或其他局部界盲加，未计native trim/表示/布尔的限制明确保留。

独立只读最终产物核135个唯一、前置引用完整的节点，target/tool/left/right均已存在并在depends_on中；stock参数图依赖可解析，实际slot刀具为±2.5 mm、R37.5、轴y=−162.6/z=42，与所引用尾部默认数学对象一致。这里接受的是这批实际对象的求值/关联，不是面对任意被篡改JSON的通用信任或完整拓扑验证器。

### TAIL04的新实际消费

C3首次实际透传已由[TR401](p3-tail-region-review.md)接受的definitions、四有限区域、四原有向环和CSG；保存条件四面双向界4e-6 mm，与审查的严格小于该数相容。原有限trim/carrier/共同ABS语义和source stock occupancy条件保留，未将尾部条件界提升为完整stock或全件结果。任何编辑时default_source_correspondence_applies=false、该界null；旧默认定义仍以at_default明确标识。

审查期间tail owner将已接受说明中的y1/y2及四段R_C2(y)同步到源JSON，y3从展开式改为相同y2表达式；这使C3与当前源definitions的直接相等检查首先停止。没有区域/数值改变。SI保留C3，生成C4原样消费补全定义；独立最后只核新差分：C4较已核C3仅tail definitions变化，当前definitions/regions/loops/CSG均逐对象相同，y3代入y2与旧式完全相同。无需重算旧尾部数学。

### 测试及审计证据

继承SI实际工具转录，cwd项目根、PYTHONPATH=src、PYTHONDONTWRITEBYTECODE=1、隔离Python `-m pytest -q`：首次新integration三项及edited_diameter共4 passed；新增phase传播单项1 passed；PI06修复默认正例1 passed、missing_profile新负例1 passed；TAIL消费修改仅默认/编辑两项2 passed；尾定义补全的单项最初误将R_C2当list失败，纠正为实际分号字符串后1 passed。未额外保存stdout日志，本审不为补日志重跑，也不将这些逐增量计数当一次独立完整矩阵。

独立审计只读原始JSON和内存Fraction算术：C1悬空引用有据；C3图/profile/44新预算和默认接口核通过，随后在开发中尾definitions相等断言停止；排查时一次漏指定UTF-8发生GBK解码失败，明确编码后确认仅等价定义补全。C4最终差分核exit 0，原图/预算不变。未运行候选生成器或修改源证据。

本节不关闭PI02。后续需要把已接受有限区域和真实材料/参数/预算接口继续接成完整P3覆盖，不能仅以135节点或“全部false”完成阶段，也不要求提前运行P4/P6。

## C5头部有限谓词及数值成员预览增量

SI明确冻结本批 `p3_integration.py`、`regional_construction.py`、`flank_construction.py`、定向测试和regional-construction-c5后审查。**受限接受C5的头部候选操作图接入、四新增派生量、成员预览函数与seam次序守卫；没有新阻塞性软件发现。PI02及头部H208-1/H208-2仍OPEN。**

已由[H208](p3-head-review-20261113.md)接受初始数学移除集U及连续域人为帽隐藏的公式，可以作为当前有限谓词候选；它没有接受45原面有限域/材料对应或整头预算。本审只检查软件怎样保留及消费该候选，不重做H208的射线/不等式或旧局部支证明。

C5原135节点、profiles、22member、尾部和44chart预算与已核C4逐对象不变；追加24 bounded_set、一个regularized_union及一个regularized_difference，共161节点。head.result把source占位target改为实际member_21_result，depends_on同时包含该target与head.removal_tool；未知head参数在生成时拒绝。独立只读核24谓词、binding及其参数集合与来源whole-head-csg-dag逐对象一致，仅添加空对象依赖；原参数值不变，新增上下fillet中心Y和sphere接触Y共4个实际派生量，公式/依赖与球内切关系正确。所有节点引用及参数引用可解析。

`evaluate_head_removal`是专用于该冻结候选的binary64组件成员预览：R31/上下fillet/R40/R32/正cone的轴向截限，六sector局部s/t/rho及A、B的半空间/环面不等式逐式匹配24有限谓词；返回匹配组件及其并集inside，未声称通过实际stock差体或native完整几何验证。只作数值边界判断，明确不是区间证明。分支0须contact_s>0、分支1须contact_s<0的新guard与s≥seam/s≤seam方向一致，拒绝编辑穿越该选支事件；它仍不足以证明全部编辑后的外露/分离/材料条件。

继承SI已发生的新定向结果：C5默认/编辑影响项2 passed；mouth从17变17.01时y=17.005的cone成员变化与seam越界拒绝2 passed；另在内存取六sector的A/B内部点共18组件均识别，exit 0。该18点仅软件求值正例，不作为18张面的全域证据。独立只读C4→C5差分、161节点依赖、所有binding及4新增公式核对exit 0，未重跑测试或重新生成工件。

候选U在初值下的有限数学定义现在已接入实际顺序，不能再笼统说SI只有22无限头carrier。但45原source loop及材料对应、stock/先前去料交域、整头双向误差和总预算仍未闭合；C5保持conditional和execution=false，本接受不把这些缺口转交P6，也不释放P4。

### C6限定审查事实标注

受限接受regional-construction-c6的新head_csg标注。与C5只读逐对象差分，仅head_csg增加H208引用、默认适用布尔及已审连续域/指定帽隐藏/mouth嵌套范围，并将旧“exposure under review”改为“source finite-domain/material remain open”；图、公式、参数、预算和其他对象不变。代码以任何非空overrides使initial_candidate_review_applies=false，与H208初值限定一致，未添加完整原面或整头预算通过声明。

独立首次把该变化预期为“仅添加字段”而对原status不变断言失败；随后只读具体差分确认上面的必要文义更新，非实现缺陷或额外几何运行。SI只复验默认/编辑两影响项2 passed；本审不重跑。此接受仍不关闭H208-1/H208-2或PI02。

### C7根柱/锥载体预算接入

受限接受regional-construction-c7新增22项root_carrier_graph_budgets。与C6只读差分仅budget增加该来源路径/条目，原图和所有旧预算条目不变；源码要求22条、22唯一index恰0..21，且每项member与实际C5成员相符。消费ROOT-CONE06已接受的同世界方位角、声明径区间内source双父carrier→含C5 axis_point候选图界，不消费转换3D样条作为原边误差，也不消费尚未审的有限源面推导。

零轴增量为精确binary64 `2*(|axis_point.x|+|axis_point.z|)`：同方位点水平平移界加规范锥的<1斜率传播被该系数覆盖。源码先Fraction精确相加再向上float；独立对实际22项逐一核源值、身份、偏移分数及输出覆盖，exit0。任意非空编辑使source_to_zero_axis_graph_upper_mm=null，旧初值scope保留，未求全件上界。继承该新定向测试1 passed，不重跑。PI02继续开放。

### C8/C9局部stock/head证据容器

受限接受最终regional-construction-c9的两个局部证据容器。C7→C9独立只读差分仅budget新增stock_regional_evidence和head_regional_evidence，既有节点/参数及每个旧预算项均不变。stock20 carrier、15最近解析event、10原有限半圆及20普通候选patch分别透传，逐对象等于本批[stock审](p3-stock-region-review.md)来源；没有将15代数根说成原边或把半圆界变成相邻整面界。

头部45项逐对象等于whole-head-reviewed-face-budgets：18torus条带、H207其余局部组、R40的F0003/F0108联合域及7个lower_face_pending保留。18torus的0.000262已含其来源投影/同s/端点项，不重复相加；R40一份联合域界不能误当两个source分片各自已证明同一个整面。七个pending的数值仍null，未由45计数提升全头。H207/H209的数学由对应[头部审](p3-head-review-20261113.md)继承，本审只核消费与范围，不重算。

C8曾仅以default_bounds_apply=false控制编辑适用性，而来源对象仍含candidate_y/r/domain等默认字段；本审要求给整个容器明确限定，以避免读者误作当前编辑几何。C9增加source_records_scope，原记录/数字完整保留用于来源追踪，所有非空编辑下默认适用布尔为false；这不等于把来源数字从记录删除，也不代表其可用于当前编辑预算。该最小标注修正无需旧数学复验。SI新容器定向测试1 passed，标注/编辑记录保持测试1 passed；独立来源对象/45唯一ID/18与7分类/未设whole_part_bound核对exit0。PI02继续开放。

此快照中“63675未匹配/下部pending”等是原head预算来源表的当时状态；之后的F0137采集和H212几何接受可由下一真实增量补入，不为更新状态重跑旧证书。本节不把一个旧pending永久当新源失败，也不凭新采集自动补下部面填充预算。

### C10/C11肩部已审对象及H213实际更新

受限接受最终regional-construction-c11。C9→C11仅budget增加肩部容器并更新真实head来源；原构造/参数等对象不变。肩部44 source_loops、88双父carrier根集、44转接和44同实支首退逐对象等于SS501/SS502修正后已接受来源。源码按(member,shoulder)核四集合一致、88三元键唯一，再逐侧核C5 straight_faces与实际straight_flank父面；独立实际产物核全部关联、数值/原scope保持，exit0。

该容器明确default_bounds_apply、冻结默认证据范围和禁止异域相加；首退公共0.000855没有与88图管直接合成全肩界，native选支、原边、有限填充、材料仍open。后续另出的直接顶点/完整patch证书不因这些早期来源接受而提前进入C11。

头部七个原pending现实际替换为H213受限组界，source45记录与当前head表完整相同。R31/R6/R40按相应source对的**联合域**解释，H206事件及H210圆弧项已经包含，不重复相加；H207上部sphere/step/cone行新增原圆几何及有限域绑定前提，未因给出了数字就称这些前提已关闭。物理边随后实读取到与其几何绑定/填充接受分开，后续具体新证据再更新。whole_part_bound_mm仍null。

继承SI新肩关联测试1 passed、H213来源更新测试1 passed，未重跑数学或旧编辑矩阵。当前源码只在C5独立输入改变时重解C5，其余编辑沿依赖图复用不变C5但仍做跨域守卫、使旧source对应不适用；曾拟“所有无关编辑都重解”的增量已撤回，未被本审计入接受或验收证据。PI02尚未关闭。
