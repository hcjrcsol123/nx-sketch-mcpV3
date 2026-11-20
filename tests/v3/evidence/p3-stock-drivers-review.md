# STOCK-DRIVERS04 独立参数合同审查

2026-11-13，`/root/p3_acceptance`；独立于SI实施者，仅写本审核文件。对象为 `P3-STOCK-DRIVERS-04/README.md`、`build_drivers.py`、`stock-drivers.json`，及Q9原决定、C2 stock和既有C5接口。未改实现、运行生成脚本、调用NX或重跑旧测试；头部53driver/Q10由另一审查实例处理，本审不重复。

**受限接受为stock的P3工程参数及默认依赖合同，无阻塞性公式/默认分类错误。** 接受28个本地独立量+既有Dshaft一个外部独立量=29唯一工程driver，46个派生表达式及1个固定尾部基准。不是29个数值各获用户逐项确认的声明，不是native Driving绑定或全stock几何验收。

## 授权、身份和接口

[Q9原决定](../../../docs/v3/decisions/p3-stock-engineering-drivers-user-decision.json)明确采用直径、圆角半径、锥角、选定轴向长度独立驱动，接点派生，保留原相切、不新增其他相切。具体参数图是这一选择的工程实现；它明确区分源初始化默认与用户意图，没有扩为无限编辑或已达0.001 mm。

固定`stock.tail_datum_y=-158.6 mm`作为P1 ABS尾平面基准有理由，不额外计driver；若以后允许整体移动应共享一个放置变换，而不是每站独立移动。`shaft_outer_diameter_mm`沿用C5原ID和精确分数，后续明确编辑决定将原“未决分类”解决为独立；`stock.Rshaft=D/2`供s6/s7及两flank外端，未重复定义第二个D。

**口面唯一ID为`stock.Y_mouth=+17 mm`**，依赖tail datum与L19；stock.Y19/y19/ytop及head.Y_mouth仅别名。`stock.Y17=-1 mm`仍是s17/s18接头；`stock.Y16≈-2.7320508 mm`不是头内台阶y=-16。JSON中不存在独立stock.Y19节点，所有口面别名指向同一表达式。本次名字纠正未重算数值；已按实际最终JSON与脚本核对，原source路径上的历史编号不当成另一个driver。

stock的Y13/Y15、R45/R44与head内腔是共享边界/包含关系接口；不得将head自由输入另覆盖stock派生量，亦不得仅复制同一默认值而拆成两个互不关联的参数。该跨模块消费由SI在整合中落实，不能仅以本参数表存在关闭P3整体接口。

## 公式、相切与默认合法性

- 六锥角均用rad、0<α<π/2；升径锥站点按ΔR/tanα正向求解，s17降径段从Y17反算Y16，符号正确。两直径/角与连接点未同时独立驱动，避免显式过约束。
- s5：M5=R3+t5，Y5由s6与Rshaft交点反算，Y4=Y5−t5；源R3圆柱与s5相切得以保留，s5/s6不另加相切。其新规范化源误差仍须依赖SHOULDER05独立数学审，不能由本默认点检查替代。
- s8：中心半径Rshaft+t8，Y7由到R9的正根长度反算；s7/s8相切，s8/s9只按交点。默认明确满足0<M8−R9<t8，故选择内侧四分之一分支。
- s10：中心半径R9+t10、Y9=Y10−t10，保持R9圆柱及Y10台阶平面的两端相切；台阶外半径R11>M10。s14台阶R14>R13。
- s19：Y18取R17圆柱与圆的下交点，R19取口面与圆的外径分支；默认0<R17−M19<t19且Y18<Ycenter19<Y_mouth<Ycenter19+t19，分支与README一致。未强加s18/s19相切。

20个外轮廓顶点的预览与C2差最大轴向约9.6918e-12 mm、径向2.384185791015625e-7 mm；后者为保留的v5历史差，未抹零。两个附加轴闭合点v20=(Y_mouth,0)、v21=(tail_datum_y,0)是原stock辅助封口，应消费这些同一身份，不增加driver；源有限端面不是完整圆盘，仍须实际去料/trim构造。

派生图按拓扑顺序引用已定义输入，所有节点有声明消费者。消费者字符串是P3设计链接，不是原生特征已实际引用的证据。README/JSON把允许域列为finite正尺寸、角度范围、根号和源分支、严格站序、非零台阶、简单母线和工具/包含条件。实际消费时，“源分支”须落实为相应不等式；例如仅radicand>0并不能区分s8内外支，需保留M8−R9的符号。当前默认已逐项满足，未来不合域编辑应拒绝，不能静默改支路或夹根。

## 一次最小独立默认审计

cwd项目根；隔离Python `C:/0sf/1PROJECT/AI/design/.audit/temp-tools/windows-mcp/Scripts/python.exe -`、`PYTHONDONTWRITEBYTECODE=1`。仅读取新JSON，在内存独立解析46个expression（`^`按数学乘方），从实际AST变量集合核对每条declared dependencies、前置节点及唯一ID，再按已记录默认数值求值；未执行`build_drivers.py`、未写新模型或重算旧几何证书。exit 0：

```text
Independent expression parse/evaluation: 46 formulas, declared dependencies exact and preceding; 28 local + one external + one fixed; all defaults matched
Unique mouth=+17; stock Y17=-1; Rshaft=D/2; ordered stations and steps passed
Default inner s8 branch / s19 lower-to-upper branch guards passed
```

这项是表达式/依赖与默认配置检查，使用binary64预览运算，不是对几何误差作严格区间证明。没有执行任意编辑扫参；无测试失败或需要复验的实现缺陷。

接受范围止于参数规划。SHOULDER05规范化全域误差、stock真实有限面/材料包含、head/shoulder参数接口、后端约束和最终0.001 mm均由相应证据决定，不因29driver计数而关闭。
