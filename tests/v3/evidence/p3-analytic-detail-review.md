# P3 解析面读取C1及TAIL首四面前置独立审查

2026-11-13，审查者 `/root/p3_acceptance`，独立于SI实现者。仅写本文件；只读源码、安装SDK、冻结制品/构建记录、新测试和具体计划。无NX、init、dispatch、Git或hash；没有重跑已通过fake/旧测试。

## 结论

**受限接受解析reader C1的最小增量及TAIL首四面operator/计划作为首次受控读取的软件前置；未发现阻塞性代码或制品关联问题。** 接受不等于已经取得native结果，也不改变P3几何状态。实际启动/读取仍由TL唯一通道，在完成本次独立副本、隔离runtime/config、普通路径及源冻结实际核对后执行；本审没有提前宣称这些尚在准备的运行文件已通过。

允许范围仅F0116→F0059→F0119→F0001，首项单独执行；后续最多剩余三项，每项显式索引且前项完整clean/归还后才继续。没有5+41 fallback或默认补读其他圆柱、圆锥、平面。UF17/Conical仅获离线代码/fake与构建覆盖，本队列没有UF17实机项，不能称其已实测。

## Reader：代码与SDK

被冻结对象为 `workspace/build/v3-p3-analytic-detail-c1/`。对比已接受的`t13o-c2/source`及CARRIERS运行源，native差异仅为`geometry()`中三个解析类型的字段序列化；Python/C# selector及detail normalizer只增加配对域，未扩大请求数/预算或改变调用生命周期。

| UF selector / BREP输出 | 独立核对SDK及实现 | 边界 |
| --- | --- | --- |
| 16/Cylindrical →201 | `UF_BREP_cylinder_s.pt_on_axis/axis/u0_ref_direc/radius`逐字段输出；axis点定义v=0，v沿轴为part length | 不根据P1圆柱数据替代BREP参数帧；不自动证明有限trim |
| 17/Conical →202 | `UF_BREP_cone_s.pt_at_apex/axis/u0_ref_direc/half_apex_angle`逐字段输出；半角单位rad、apex为v=0 | 不把apex与P1轴上一点混用；不转换角度或把两半锥都当源面 |
| 22/Planar →209 | `UF_BREP_plane_s.pt_on_plane/normal/u0_ref_direc`逐字段输出 | SDK枚举208是OFFSET，209才是PLANE；首测误期待208已正确修为209 |

核对依据：安装 `C:/0sf/ug/UGOPEN/uf_brep_types.h` 的枚举与三个struct/参数语义；C++使用符号枚举而非自行猜值。数字仍经既有finite检查和17位输出，不改变轴/参考向量、不重参数化或解算FIN。

server运行验证、C#请求验证、explicit P1 selector及detail normalizer均核准确 `(UF,surface_type)` 配对；增加enum列表不替代运行时配对校验。synthetic normalizer测试只验证接收新表面类别并保留false，不能代表native根字段与几何有效性已验证。

`ReferenceDetail.cs`、Python bridge、托管/原生构建脚本与已接受t13o C2相同。dirty前后检查、第一次异常停止后只清理、edge白名单、同树遍历、rc及事件合同、expected_session_epoch、UNKNOWN/STOP、归还及双库存差异检查没有被本增量改写。native仍2 MiB/face、4096 events，拓扑921600 bytes门限沿用；`geometry_details_complete=false`仍保留。CLEAN_TRACE是调用/只读证据，不会把非空geometry state或未知材料含义变成几何通过。

## 构建与新测试证据

直接字节比较（不计算hash）确认当前72项源码/测试/构建输入与C1 `source/`一致；C1 `native/ReferenceGeometryNative.cpp`与冻结源码一致；根runtime native DLL与native构建DLL一致。`compiler-invocations.jsonl`记录4次托管编译，所有`.cs`输入均来自该C1冻结source目录，四个输出均存在；`build-exit-code.txt=0`。native记录指定冻结snapshot、安装UGOPEN头/库、实际cl命令及exit 0。未以时间/大小替代内容比较。

继承[verification.md](../../../workspace/build/v3-p3-analytic-detail-c1/verification.md)列出的实际工具转录；它明确没有独立完整stdout日志文件，本审不补造日志或为补日志重跑：

- native新fake首测3通过/1失败，失败仅plane期待208；修正期待后该单case通过。随后为补真实FIN spline和同树edge遍历断言，仅三个root case通过。nonfinite/dirty-stop用例沿用首批已通过结果。
- selector三个精确配对、P1唯一选择、错配拒绝及synthetic normalization，加实际受影响旧拒绝case，7通过/6子项；不将synthetic改写库存当真实native证据。
- 新C1托管bridge实际DLL经fake adapter处理三配对并拒绝错配，1通过。它验证托管制品入口，不证明NX解析面调用。

首败复现路径是新native测试中plane variant=43曾期待208；复验标准为SDK209及字段完全一致、FIN/edge遍历和原false保留。以上定向结果满足该标准。native fake的新非有限/dirty例证明本增量进入既有停查/清理分支；更广泛旧异常、资源释放及epoch用例按未修改合同继承。

## TAIL四项计划与operator

对象：`workspace/v3/p3/P3-TAIL-READ-01/operator-one.py`、`read-queue.json`、四selectors及 `tests/v3/test_tail_operator.py`。已与原CARRIERS operator作直接文本差异审查；改变集中在固定目标、对应根类型、冻结来源/制品核对及最多4条外部账，原单步执行/STOP控制流保留。

- `_plan`固定四标签/顺序和源计划路径；每个selector与stock-tail具体描述、P1原对应face的UF/type/box/边数及唯一匹配核对。输出路径限定本实验的四个新目录，selector envelope必须与该项一致。初始请求一圆柱和三平面，期望根分别201/209/209/209；期望是读取后需核的候选，不是提前证明。
- 每次`operate`只能init或一个规范整数索引；`_run_one`只允许下一未dispatch项，范围1..4，没有批处理自动续行。计划中的最大显式batch=4不会产生第五项，首1之后实际只剩3；root仍逐项显式调用。
- 外部dispatch先落，再创建独立证据目录；完成必须先通过既有strict evidence validator和新的解析根字段校验，再写CLEAN/completion。validator核双库存/clean trace/HUMAN归还与实际runner退出约定，不能靠根类型正确跳过它。
- 新根后验核finite三向量、非退化axis/normal与reference；圆柱radius严格正。错root、dirty/不完整、未决dispatch、配置/源/runtime变化、非连续账或额外native目录均停队，不自动重放/清锁。expected_session_epoch进入实际命令及冻结context；不复用旧凭据。
- `_sources`要求冻结文件集合等于C1的72项与旧CARRIERS运行源36项的**集合并集**，不是声称108个互异文件；逐文件live/frozen直比，编译源再与C1 freeze比较。5个runtime文件均须与C1制品逐字节相同。operator和connection另外由init冻结；plan/当前context与外部anchor每次一致性核对。
- 旧controller单步、异常保留、lock及显式归还的已接受证据继承；新测试7项首fake覆盖四目标、扩项/顺序/root/selector/预算拒绝、逐项运行、错误根停队，另2项增量覆盖runtime漂移和clean validator失败不发下一项。该数量不与旧测试相加成一次总矩阵；测试中的fake context/source绕行仅是单元夹具，不是实际运行前置证明。

本审没有发现需要重复旧控制流矩阵的改动。新实际runtime准备仍应由TL在首次init前完成并留下记录：独立副本与指定当前PRT的直接来源关系、普通路径/无reparse、C1五制品/源码冻结、connection-only配置和新session身份。运行后以每个真实detail/summary/归还/保全证据判断成功；出现dirty、overflow、unsupported或未知即停止剩余项，原失败保留。不得因本前置接受自动归还未知会话、重试或放宽预算。

以上是首次读取前的软件/计划受限接受，不是四面数据已取得、源trim已闭合、0.001 mm达成或P3阶段完成。

## 实际隔离准备补核

TL准备文件落盘后，审查者另作一次只读直接字节核对，exit 0：104个冻结文件恰为72编译/相关源与36运行源集合并集，无重复；104项live与本实验freeze相等，72项再与C1 freeze相等。五个runtime制品全部与C1对应文件相等。根据配置中的实际startup目录定位`isolated/profile/startup/M2Startup.dll`，内容与C1相等；startup目录及helper路径都落在本实验隔离区。未输出配置凭据。

指定参考`tests/外球叉.prt`、`source-before.prt`及`reference-readonly.prt`三者直接bytes一致，长度430553；来源/运行复制记录存在。配置可解析。检查时尚无LEDGER-STARTED、operator-ledger、OPERATOR-LOCK或STOP，不把这一时点观察外推为后续现场状态。最初按`isolated/startup`猜路径未找到启动DLL，随即读取实际配置目录完成上述核对；没有修改目录或文件。

接受这批实际复制/冻结关联。新会话启动前的最后进程/普通路径检查、真正PID/epoch及connection-only运行配置由TL随后建立并记录；本审不预先填入未发生的会话或所有权信息。该补核不重复fake或native测试，不启动NX。

## TAIL首四项实际采集受限接受

四项现已由root首次读取并正常关闭。独立原始收证见[p3-tail-read-index.md](p3-tail-read-index.md)：F0116根201，F0059/F0119/F0001根209，事件80/89/89/63共321；229返回rc0、92void/null，所有dirty样本false、四完整库存diff空、逐项summary确认实际HUMAN归还。归还前status为AI_OWNED，记录顺序已与受审runner核对，不虚构归还后status。

接受新四面采集及正常窗口Close/无相关进程的收尾记录；原件/before/copy字节、原件mtime、104源、operator/connection及5制品保全经独立直比。副本初始mtime未记录，不作该声明。PID7968/epoch7968:639301552881734459仅历史，禁止复用或重放已完成队列。可交机械分析这批新输入；UF17仍未native验证，完整几何、材料和P3状态不因采集成功提升。

## CONE-READ01 两项最小补读方案审查

2026-11-13，重启后独立审查实例 `/root/validation_r68`，承接上述已接受范围；本次只读新计划及所复用runner/validator，不重跑既有测试、生成器或NX。对象为 `P3-SHOULDER-STOCK-05/two-cone-query-plan.json` 和TL明确提出的两次手工串行单项流程；实际CONE-READ01准备文件尚待提交，本节不是其预先验收。

**受限接受新两锥的必要范围与具体最小采集流程，不要求为两项新增通用operator。** F0026、F0067各48条边均为计划中已明确的完整面读取；它们补充22根柱24条后交边和两个共同接缝所缺的geometry class、完整边与FIN方向。两锥未在已接受旧145源中完成相应detail采集，本次不是重读根柱、旧TORUS或TAIL。

独立只读P1原库存核对，隔离Python `-B -`、cwd项目根，一次exit 0：两selector的UF17/Conical、六坐标bbox、48条互异边与其P1逻辑面精确一致；按0.001 mm识别阈值分别只有一个候选。24个后边ID互异，覆盖22根柱，每条在所列柱/锥两父面中确实出现且P1类型为Intersection；F0064/F0129各保留两条，不合并。两个锥面实际共有边集合恰为E0059/E0234，均为Linear。此核对只证计划与P1库存关联，不提前把P1标签或旧Tag作为新会话身份。

实际流程限定F0026后F0067、总共最多2次detail，每次runner只给一个selector。TL先持久记录准确命令、cwd、当次PID/startticks epoch及dispatch，再执行既有 `run_reference_detail_once.py`；记录实际exit、原始stdout/stderr，调用既有 `run_swept_queue.validate_evidence` 并核root202字段之后才能写completion。该validator本身接受明确传入的selector/context，并不要求调用旧Swept队列生成器。预期runner退出1表示已记录INCONCLUSIVE响应，不是几何通过；不能用固定1代替真实退出码。strict校验确认本次session/binding/revision关联、双库存/empty diff、clean及真实HUMAN归还；root202后验另核apex/axis/u0有限、轴/参考非退化不共线、半锥角有效及无geometry states/unsupported。apex不替代P1轴上一点。

首项只有上述证据完整通过才能由TL另一次显式派第二项。任何异常、错根、缺项、overflow、dirty、未知归还或未决dispatch先持久STOP，停止剩余项，保留首次证据，不重放、不自动清锁/解冻。若主进程中断，已有未完成dispatch同样不得当作“未执行”重发。两项不授权第三项或预算扩张。

预算沿用C1：每面2 MiB输出、4096事件、921600 bytes拓扑门限及既有元素上限；48边仅说明库存规模，不证明完整曲线/FIN输出一定低于门限。不以较少边的TAIL成功推出本两面容量保证；触限须按原合同停止。match_linear=0.001 mm、angular=0.0001 rad和curve/surface请求0.0001 mm分别保持识别/请求语义，均不是已实现的几何误差证据。

首次运行前仍需实际普通独立copy、source-before与当前参考的来源直比、隔离C1制品/运行源码冻结、connection-only配置、新会话身份及当前无冲突通道证据。结束按既有授权正常退出保全；不得沿用TAIL PID7968或旧epoch。采集接受只能将输入交机械解释，完整有限域、FIN到边参数对应、材料、误差预算和P3出口仍由各自证据判断。

### CONE-READ01 实际准备补核

TL提交 `P3-CONE-READ-01/execution-plan.json`、两个selector及复制记录后，独立只读直接bytes审计exit 0：当前原件、新before、新工作副本与已接受TAIL before四者430553 bytes一致；新copy与原件/before不是同一文件，原件mtime及新copy初始mtime与本次记录相符。104文件集合与TAIL接受集合相同且无重复，104项live/new-freeze/TAIL-freeze逐字节一致，72编译输入又与C1 freeze相同；五runtime和独立profile内startup DLL均与C1字节一致。没有用时间/大小替代内容核对，没有hash。

新实验目录及已存在子项、其父路径均无reparse。计划恰两个按序目标，descriptor及selector envelope、12+12必需后边、两个共同接缝与受审query-plan一致；两个native输出目录尚不存在，检查时无dispatch或STOP。配置可解析，helper/token引用在本次isolated内，未输出其值。此时 `isolated/mcp-config.json` 是含launch段的启动配置；**实际runner所用connection-only配置及新现场PID/epoch尚待TL启动后建立**，本次不提前声明已存在或审过。

受限接受这批新复制/冻结和具体两项计划，允许TL按已授权唯一通道继续建立新会话及connection-only配置，随后执行首项。第二项仍严格依赖首项真实completion，以上准备核对不替代逐项后验、归还与最终保全；所有时点事实仅针对检查当时。

### 首次UF17实际采集接受

两项现已完成，独立原始证据审见[p3-cone-read-index.md](p3-cone-read-index.md)。F0026/F0067各root202、48边、679事件，全1358 clean；970 rc0及388 void/null如实区分。每面36 class10、12 class11，完整库存diff空，逐项实际HUMAN归还；第一completion后才第二dispatch。两次runner真实exit1表示INCONCLUSIVE响应已记录，不是几何通过。axis/apex/u0/half-angle、状态及调用清理独立核对。

接受本次UF17采集及正常窗口Close、17:06:43无相关进程、原件/copy/before字节和双mtime、104源码、五runtime、connection/plan冻结的保全证据。新before与TAIL before直接来源关联及两snapshot ABS毫米字段支持共同源帧新增两记录，不扩为相同UV/边参数。PID3580/epoch3580:639301573270396084仅历史，禁止重放。此前“UF17未native验证”是历史时点记录，现由本次两面受限实证补充；其他圆锥输入/全域/材料及P3验收不自动提升。

## LOWER-STEP 单一新F0137计划审查

独立受限接受HEAD02的 `f0137-read-proposal.json` / `selectors-F0137-proposed.json`，及TL提出的新独立副本/session、手工单次C1/read_once流程。实际准备文件尚未提交，本节不预先验收它们，也未运行NX。

一次只读P1审计exit 0：F0137确为库存第137面，UF22/Planar、六坐标bbox及4边与selector精确相同，0.001 mm匹配唯一；四Circular边63673/63675/63713/63849及父面/原journal逐对象一致。当前lower-circular-original-inventory明确63675 present=false，原P1只保留三点journal/类型，它属于F0096/F0137；选一个F0137可同时补缺内半圆EVAL和本环形平面的两环/方向，不需要因此读取9球面或重读旧面。

限总共1次单目标detail，新root期望209而非208。复用既有C1制品、runner及strict validator，使用真实新epoch、普通独立copy/冻结源和connection-only配置；事前命令/dispatch、事后实际exit/rawstdout/stderr、strict clean/完整空diff/HUMAN及root209有限plane point/normal/u0、非退化帧核查，全部完成后才记completion。另核实际两loops、四完整边、所需原EVAL/有限limits及FIN方向确已返回；预期不等于采到。保留2MiB/4096events/921600拓扑预算，任何异常/unsupported/缺项先持久STOP，不重放、不扩队、不自动恢复；正常归还退出保全按既有受审路径。

R40同carrier两片若走联合many-to-one，只能在其外环/有限域证明成立后省略内部非物理分缝重建，同时保留两个source ID及覆盖。这是区域构造选择，不是本次读取成功自动证明的事实。F0137实际frame/sense也只在有效源solid/UF语义条件下支持材料方向；四边取得不推出完整头部或P3接受。

### LOWER-STEP-READ01实际准备补核

新准备提交后，一次只读直接bytes/JSON核对exit 0：execution-plan恰一个F0137、209根/两环/4边预期，与已审selector逐对象一致；原件、新before/new-copy及已接受CONE before完整430553 bytes相等，copy与原件/before不同文件，双mtime基线相符。104源集合及live/new/CONE freeze一致，72编译源与C1一致，五runtime及startup与C1相同；新树和父路径均普通无reparse。配置可解析，helper/token引用仅本次isolated；未输出私有值。

检查时无dispatch、STOP或native输出目录。现有mcp-config是含launch的启动配置，实际runner connection-only及新PID/epoch待TL建立；本审不提前宣称其已存在。受限接受该准备，允许唯一TL通道按上述单次后验流程继续首次读取；仍不授权重试、扩目标或以期望替代实际两环/EVAL证据。

### F0137实际采集接受

独立新收证见[p3-lower-step-read-index.md](p3-lower-step-read-index.md)：一次实际root209、两loops各两FIN、四个唯一原class10 circular evaluator，包括此前缺失的63675。76事件clean（57 rc0、19 void/null），完整库存相等/diff空，真实exit1及HUMAN归还；已正常窗口关闭、17:44:06无相关进程，双mtime和原件/copy/before bytes、104源码、五制品、connection/plan冻结保全核通过。

新before↔CONE before来源关系和实际mm ABS字段支持共同源帧追加此一记录。root plane Y=−26与四圆心Y=−26.000000000000004保留为不同原始数值，不当作无误差等式。PID2592/epoch2592:639301595458933613仅历史，禁止复用/重放；本接受只关闭该次输入采集缺口，不改变完整头部/P3几何验收状态。

## PHYSICAL-EDGES-READ01 固定16新面前置审

独立受限接受新 `P3-PHYSICAL-EDGES-READ-01/operator-one.py`、read-queue、16 selectors及 `test_physical_edges_operator.py`，作为后续实际准备/首次读取的软件与范围前置。实际新copy/runtime/config尚未提交补核，本节不预先验收现场，也未运行init、dispatch或NX。

固定顺序为F0196；F0131/F0157/F0171/F0177/F0203/F0232六R32；F0031/F0115/F0021/F0048/F0035/F0020/F0044/F0056/F0206九stock。根期望依次209、六203、202/201/202/202/209/201/201/202/202。首项14边，F0031五边，其余四边；原2MiB/4096events/921600拓扑预算不变，计数小不预先保证完整数据一定落在预算内。

独立一次只读核16描述符的P1逻辑face、UF/type、完整bbox、边数及selector envelope，全部精确且0.001 mm匹配唯一。六球contract的12原P1 Circular边逐项父面/journal对应，另与已审stock24缺边无重叠；36个物理边缺口被所选16全部覆盖。现有完整empty-diff/唯一MATCHED/clean/full-edge记录共148个逻辑面，16均不在该集合；这次不重读已接受面。P1 Circular仅是类型记录，未预先声称原BREP class10或EVAL必然得到。

联合stock覆盖约束与12球边后，独立按连通分量组合穷举：14/19/5节点分量分别最少7/7/2面，总最少16；恰20套最优集合，TL所选固定集合在其中。头部19节点分量的7面最优解唯一为F0196＋六R32，既补六sphere/step与六sphere/cone边，也补六cone/mouth边。该结论仅为明确36边和可读父面的最少面数，不是所有未读几何的通用最优或stock/头部已完成。

对已接受TAIL operator作直接文本diff：改动限固定labels/根映射、两份source-plan合同、4类解析root检查和外账/索引上限4→16；既有一次只允下一整数index、事前外置dispatch、真实runner退出/stdout、strict完整clean/归还、源/runtime/operator/connection冻结、未决锁/STOP不重放逻辑保持。球核有限center/axis/u0与正radius，锥核有限apex/axis/u0及0<half-angle<π/2，平面/圆柱沿用字段；frame非退化核在strict通过后，不能用root对就跳过strict。

尽管plan允许每个显式batch最多4，operator仍一次只执行一个index，首F0196须完整clean/HUMAN后TL才显式下一项；总计最多16，无默认fallback或第17项。源码不把未来面中某一边的计划class当作实际结果，采集后须另审实际class、原几何/转换、父面和两环/方向。特别是同面相反半圆可能共两端点，不能沿用盘点中的非空匹配就宣称身份唯一。

继承SI新fake实际3 passed及错误root新增1 passed：固定P1计划/乱序拒绝、16次显式连续单项和四类root、clean失败STOP与错误rootSTOP均有证据；fixture绕过现场source/context只作控制流单元测试，不是实际复制或session验证。未重跑旧TAIL/reader矩阵、未编译新reader。下一步仅实际新普通copy、104源/C1制品、新session/connection和计划冻结补核后由TL唯一通道执行；任何异常停止余项，不自动重试或换目标。

### PHYSICAL16实际准备补核

TL提交同目录实际准备后，独立一次只读bytes/JSON审计exit0：原件、新before、新copy及已接受LOWER before完整430553 bytes一致，原件/copy双mtime基线相符，copy与原件/before为不同文件；新目录、子项与父路径均无reparse。104 live/new/LOWER freeze源相同，72编译输入与C1相同，五runtime及startup与C1一致。16 selector envelope与受审plan相符，输出全为本实验下未存在目录。

启动配置可解析，helper/token仅引用本次isolated；未输出私有值。检查时无operator-ledger/LEDGER-STARTED、dispatch、STOP或native输出。实际connection-only及新PID/startticks须TL启动后建立，init再将operator/config/plan与新context冻结；本次不替代这些未发生事实或逐项实读后验。受限接受这批实际准备，TL可按已审首F0196、随后显式单项/小批上限的固定队列执行；全部完成或首异常按原合同停止收尾。

### PHYSICAL16实际采集接受

独立新收证见[p3-physical-edges-read-index.md](p3-physical-edges-read-index.md)：16项实际2plane/6sphere/5cone/3cylinder、1253 clean事件（919 rc0、334 void/null）、16完整empty diff及逐项HUMAN归还。独立以每条新边的两current-session父面唯一映射P1逻辑对，确认计划36缺物理边全取得，共38树使用，实际皆class10 finite circular evaluator；没有凭Tag相等或共享端点认领半圆。其余class11边保持转换/双父语义。

接受正常窗口Close、18:20:41无相关进程及双mtime、原件/copy/before bytes、104源、五runtime、operator/connection/plan冻结保全。前置已证new-before↔LOWER-before及16实际ABS毫米字段支持共同源帧追加。PID11548/epoch11548:639301617236063699仅历史，16项禁止重放；采集接受不替代36原边到候选的全域数学、有限面/材料或P3阶段验收。
