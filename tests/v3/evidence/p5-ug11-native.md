# P5 实际 UG11 建模记录

本轮范围为 T21～T24。工作目录为项目根，宿主 Python 使用 `PYTHONPATH=src`。设计输入沿用 [P3 最终计划](../../../workspace/v3/p3/P3-FINAL-PLAN-01/final-plan.json)、[P4 逐驱动映射](../../../workspace/v3/p4/P4-ACCEPTANCE-20261119/per-driver-edit-domain.json) 及 [P4 修订 93 验收](p4-error-and-edit-domain.md#p4-阶段验收修订-93)。实机使用已安装的 NX V11.0、11.0.0.33、简体中文和 C# Journal，在独立会话中新建毫米件。软件许可沿用当前安装。

## 实际后槽的首项验证

从真实计划生成尾槽表达式和截面，取同一实现构造独立刀具体。T21-01 的 NX Journal 编译器报告缺少 System.Core，未进入 Main，无模型，进程退出。首次常规 csc 编译使用了默认程序集，未暴露该差异。修正源码中的 LINQ 和集合依赖，同时把带编辑的调用改为 NX11 的 EditWithUnits。保留[首次编译诊断](../../../workspace/v3/p5/T21-01/runner-stdout.txt)。

在新编号、新空白件重试修改影响的同一截面。命令如下。

```powershell
./tests/v3/ug11_native_cases/Run-Native.ps1 -RunId T21-02 -Journal workspace/v3/p5/T21-input-02/journal.cs -Manifest workspace/v3/p5/T21-input-02/manifest.json -AuthorizedForNative
```

已知正 Z、负 Y 的尾槽采用 YZ 基准面、一个固定基准点和一个圆。实机检查三项 Driving、各自的原生圆使用者和求解自由度 0。宽度 5→5.1 mm 时拉伸起止为 −2.55/+2.55 mm。圆心 Y 从 −162.6→−162.61 mm、Z 从 42→42.01 mm、半径从 37.5→37.51 mm，每次分别编辑、更新、检查圆几何并恢复默认。模型保存、关闭、重开、最终关闭通过。记录含新建刀具体、编辑值及阶段顺序。[Journal 和原生输出](../../../workspace/v3/p5/T21-02/)，[逐项 TSV](../../../workspace/v3/p5/T21-02/native-evidence.tsv)，[隔离和退出](../../../workspace/v3/p5/T21-02/claim.txt)。

本次截面验证限于实际尾槽。完整目标体布尔、端到端消费、轮廓及关联的重定位由整件实机记录说明。P4 几何误差证书只适用于原已验收的 NX2506 件。

## 整件首次尝试及角度单位

FULL-01 执行了前 24 项表达式，第 25 项 `stock.expression.stock.alpha1` 查询 NX2506 用名 `Radians`，UG11 返回 3520016。无保存件，批处理已退出。随后仅用独立空白件 UNITS-01 枚举角度量纲，确认本机 NX11 的对象名为 `Radian`。输入 π/6 rad 时，表达式单位值 0.523598775598299，基础单位值 30°，原生 sin 值 0.5。改用该版本实测名称。见 [FULL-01 原始检查点](../../../workspace/v3/p5/FULL-01/native-evidence.tsv) 和 [UNITS-01 单位/三角实证](../../../workspace/v3/p5/UNITS-01/native-evidence.tsv)。

FULL-02 准备过程中，PowerShell 的 JSON 对象转换不能同时表示头部参数 `RA` 和 `ra`，在创建运行目录、启动 Journal 之前拒绝。修复范围为测试启动器的清单读取；两项工程参数保留独立身份。

FULL-02 使用修复后的启动器及 Radian 建出实际 stock，在毛坯被布尔消费前完成轴径编辑并恢复。首个直翼已创建 EXTRUDE(29)，读取样条极点时，NX11 的坐标表达式未直接将 Studio Spline 列为使用者，断言停在 `member_00_straight_tool`。未保存；所有相关批处理进程均已结束，再核对该编号目录无 PRT。这两次失败都保留了原始目录，后续写入从新会话及新编号开始。[FULL-02 原始证据](../../../workspace/v3/p5/FULL-02/native-evidence.tsv)

当前实现用 UFSo 的 Ask3ScalarsOfPoint 与 AskExpOfScalar 核验每一坐标的原生依赖，连同 Studio Spline builder 选点、实际极点及节点向量检查。T24 先用已有 P3 组装器从已接受的上游证据校验计划，逐节点核对目标、工具和保留策略，输出 104 项驱动至实体特征的传递消费映射。未获支持的操作、未确认的输入和窗口外编辑均被拒绝。[编译器](../../../src/nx_sketch_mcp/v3/ug11/compiler.py)、[操作映射](../../../src/nx_sketch_mcp/v3/ug11/operation_map.py)、[驱动映射](../../../src/nx_sketch_mcp/v3/ug11/driver_map.py)

## 整件编译与验证入口

仓库根目录执行以下命令。输出目录与运行编号只使用一次。日常编译省略 `--verify-edits`；本次取证通过该开关在相应特征创建后做六个临时编辑并恢复。

```powershell
$env:PYTHONPATH = 'src'
python -B -m nx_sketch_mcp.v3.ug11.compiler --root . --plan workspace/v3/p3/P3-FINAL-PLAN-01/final-plan.json --output workspace/v3/p5/full-input-03 --verify-edits
./tests/v3/ug11_native_cases/Run-Native.ps1 -RunId FULL-03 -Journal workspace/v3/p5/full-input-03/journal.cs -Manifest workspace/v3/p5/full-input-03/manifest.json -AuthorizedForNative
```

离线证据包括 4 项真实截面输入及拒绝用例、4 项拉伸/布尔用例、3 项回转用例与最终 10 项整合用例。整合定向检查入口为 `python -B -m unittest discover -s tests/v3 -p test_ug11_compiler.py -v`，其中一项以 NX11 三个托管程序集、mscorlib 和 System 显式编译含 overrides 的完整 Journal，匹配真 runner 的引用约束。未重新运行 P1～P4 的原生验收。

### FULL-03 保存件与原始收尾失败

2016 个构造步骤执行完成，其中有 1841 个表达式、47 个回转、41 个拉伸和 87 个布尔。161 个数学节点和 104 个工程驱动均在清单中给出使用者。布尔调用逐项核对目标、工具及保留关系。轴径编辑时，实际毛坯回转的截面、轴、360° 范围和圆柱面半径通过检查。F0002 的 P2 横向坐标在窗口内单独编辑后，第一个直拉伸与第一个滚转截面中，对应样条的最大极点位移各为 0.0000091560876864588461 mm，恢复后分别核对极点和两项特征的 Section。实际整件上的槽宽、圆心 Y/Z 和半径四项编辑也分别验证并恢复。[映射清单](../../../workspace/v3/p5/FULL-03/manifest.json)、[原生记录](../../../workspace/v3/p5/FULL-03/native-evidence.tsv)

默认状态保存成功。该会话在关闭并重开后核对了单实体、218 面、562 边、持久逻辑标识、原生命名表达式的公式和值，以及重新定位的后槽草图、三个 Driving 尺寸、拉伸父特征和实际 Section。最后发现重开核验后内存件的 modified 标志为真，旧收尾判据在调用最终关闭前拒绝。Journal 进程随后退出。原始 FULL-03 保留失败状态，没有终态 PASS。[已保存整件](../../../workspace/v3/p5/FULL-03/blank.prt)、[原始收尾](../../../workspace/v3/p5/FULL-03/claim.txt)

### 专项关闭与最终验收

对 FULL-03 已保存件取新的独立副本，只打开副本并执行相同的重开检查及修正后的关闭函数。实际命令如下。

```powershell
python -B tests/v3/ug11_native_cases/prepare_full03_close.py --output workspace/v3/p5/close-input-01
./tests/v3/ug11_native_cases/Run-Native.ps1 -RunId FULL-03-CLOSE-01 -Journal workspace/v3/p5/close-input-01/journal.cs -Manifest workspace/v3/p5/close-input-01/manifest.json -SavedPart workspace/v3/p5/FULL-03/blank.prt -AuthorizedForNative
```

读回前 dirty=False，读回后 dirty=True。正常关闭时未保存，Work/Display 均为空，Journal 退出，独占锁已释放。启动器在运行前后把独立副本与只读锁定的 FULL-03 件逐字节比较，3,817,472 字节一致。专项检查以唯一 PASS 结束。当前编译器重新生成的 manifest 与 FULL-03 一致，Journal 从建模、编辑到首次保存逐行一致；差异限于三行重开/关闭流程与新增的共享关闭函数。专项 Journal 与当前编译器使用相同的重开检查与关闭函数。[专项记录](../../../workspace/v3/p5/FULL-03-CLOSE-01/native-evidence.tsv)、[复制及进程收尾](../../../workspace/v3/p5/FULL-03-CLOSE-01/claim.txt)、[验收核对](../../../workspace/v3/p5/T24-ACCEPTANCE/evidence.json)

T21～T24 在上述输入和 UG11 版本范围通过独立评审及 TL 验收。104 个驱动都有映射，其中六项在本轮做了原生编辑。UG11 的整件误差、全驱动系统验收及正式交付包分别保留给后续指定任务。[独立评审](p5-t21-t24-independent-review.md)、[实时台账](../../../docs/V3-state.md)

交接保留了由修正后编译器生成的[常规建模 Journal](../../../workspace/v3/p5/T24-ACCEPTANCE/generated/journal.cs) 与[对应清单](../../../workspace/v3/p5/T24-ACCEPTANCE/generated/manifest.json)。该入口使用相同的构造步骤和安全关闭函数，默认省略六个临时编辑检查，通过了 NX11 限定程序集静态编译。实机证据按上文的整件构造及独立收尾专项合并，未对常规入口重复运行整件。
