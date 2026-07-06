# V0 Mock LLM 表达模板

V0 不接真实 LLM API，`mock_llm_generator.py` 只基于规则评分结果生成固定结构的表达建议。

## greeting_message

用途：用一句话解释岗位整体建议。

模板：

```text
这个岗位整体判断为「{rating}」，规则分数是 {total_score}。建议重点看匹配项、缺口和风险项后再决定是否投递。
```

## interview_talking_points

用途：帮助用户准备面试中的项目表达。

要求：

- 只能围绕推荐项目和已匹配能力展开。
- 不夸大成生产级 Agent/RAG 工程经验。
- 强调问题背景、实现方式、结果和复盘。

## weakness_reminders

用途：提醒用户不要过度包装能力。

要求：

- 对 React、Next.js、TypeScript、Docker、Linux、LangChain、RAG、Agent 框架等能力保持谨慎表达。
- 如果只是了解，表达为“可补充了解”。
- 如果没有真实项目，不能说成“主导生产级落地”。

## possible_questions

用途：生成面试可能追问。

方向：

- 为什么选择这个技术方案？
- 如何处理 JSON/CSV 数据清洗？
- 如何设计 Prompt 并评估输出质量？
- 如何用 Vue3/ECharts 展示数据？
- 如果岗位要求 RAG/Agent，如何说明自己目前的边界和学习计划？

