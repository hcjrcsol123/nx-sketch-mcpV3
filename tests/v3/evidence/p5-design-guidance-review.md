# P5 T24.a 规划引导独立评审

## 发现与关闭依据

1. **高，圆周布局的确认曾可套用到另一快照。** 首版以决定中自报的成员数、面号和非空路径作为依据。真实样件的两个快照 ID 不同，两个快照内的 22 个面标签集合却完全相同。单凭集合相等会把错误快照也识别为已确认布局。修正后，已知跨快照决定必须核对受控源图中的决定 ID、路径、观测快照、分析来源、范围和成员记录，再按成员索引核对当前 P1 的面。定向反例覆盖替换面、分析路径、外来快照及把观测快照改成当前 P1 ID。该项关闭。[判断实现](../../../src/nx_sketch_mcp/v3/design_guidance.py) · [源图](../../../workspace/v3/p3/P3-SWEPT-ANALYSIS-01/source-map.json) · [反例](../test_design_guidance.py)
2. **中，初版 MCP 客户端只能从初始化说明获知应去查看清单。** 对仅能读 MCP 消息的客户端，该文字不足以判断默认同值的独立驱动应如何处理。当前 stdio 初始化响应直接说明保留独立驱动、共享截面的意图与证据要求、等角布局仅触发阵列评估，以及目标版本能力门禁。每份计划的具体对象、收益和依据通过关联预览及 UG11 编译清单返回。空配置 stdio 实录与当前源码相符。该项关闭。[原始发现响应](../../../workspace/v3/p5/T24a-DESIGN-GUIDANCE-01/mcp-discovery.json) · [服务入口](../../../src/nx_sketch_mcp/server.py)

3. **低，阵列候选文案对面号所属快照的表述有歧义。** 先前的依据文字把列出的标签描述为旧观测快照所用，实际 `applicable_to` 返回当前计划的 P1 面号。现有生成物分别标明确认等角布局的观测快照和适用成员所属的 P1 快照，并列出采用复杂阵列前的目标版本、布尔次序、再生和保存重开验证。最终文案的 5 项定向测试通过，该项关闭。[最终候选](../../../workspace/v3/p5/T24a-DESIGN-GUIDANCE-01/design-guidance.json) · [定向结果](p5-t24a-guidance-scope-unittest.txt)

**T24.a 在执行前提供建议的范围内通过独立评审，无阻断项。**

## 验收范围

- 共享截面的判断检查来源截面身份、坐标框架、完整有序边和逐点驱动表达式的身份。初值相同而命名驱动不同，或来源截面身份不同，指引为保留独立编辑；框架不同、缺少驱动或单次消费不构成共享建议。即使代码识别出候选，仍须确认所有消费者应联动，并核对目标版本的实际复用行为。[规则与正反例](../test_design_guidance.py)
- 真实计划得到 22 组双消费者共享候选。每组涉及 6 条关联轮廓边。132 是按每组可少建一次轮廓、每条边产生一个 UG11 曲线特征的条件估计；不包含实体特征、点、表达式或 Section。另有一项已确认等角布局的阵列评估，收益未知。规则的数量来自成员与边集合，测试另含两个成员、单边及初值相同的独立驱动。[候选明细](../../../workspace/v3/p5/T24a-DESIGN-GUIDANCE-01/design-guidance.json) · [UG11 曲线创建](../../../src/nx_sketch_mcp/v3/ug11/templates/SketchBinding.cs)
- 项目根目录以 `PYTHONPATH=src;tests/v3` 运行 `python -m unittest test_design_guidance test_ug11_compiler test_nx2506_composition`，实现方留证 23 项通过。本评审审阅产物、源码和原始来源，未重复运行这些测试。CLI 对照记录显示常规 UG11 Journal 与 T24 接收件逐字节相同；清单移除新增建议字段后与基线相同，保留 2016 个构造步骤、驱动映射及 `execution_approved=false`。桥接写入、所有权和 UNKNOWN 门禁未由建议模块调用。[测试输出](p5-t24a-guidance-unittest.txt) · [基线比较](../../../workspace/v3/p5/T24a-DESIGN-GUIDANCE-01/baseline-comparison.json) · [编译器](../../../src/nx_sketch_mcp/v3/ug11/compiler.py)

## 剩余验证边界

本项仅接受执行前的规划建议与上述工具入口。若将来采用建议，需在相应目标版本上验证截面消费者、独立与联动编辑、材料与裁剪、布尔次序及保存重开，再统计实测特征收益。已有 F18/F19 的受限、分离 box 种子实证不能证明当前复杂特征可作原生阵列。此轮未启动 NX。正式安装后的整件产品入口验证归属 T31。[F18 能力范围](../../../docs/F18.md) · [开发清单](../../../docs/V3-development-checklist.md)
