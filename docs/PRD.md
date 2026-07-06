# AI 岗位筛选与面试准备助手 V0 PRD

## 目标

V0 做一个可在命令行运行的核心原型，用固定用户画像文本和岗位 JD 文本完成岗位解析、规则评分、风险识别、项目推荐和面试准备建议。

本阶段只验证核心判断逻辑，不做 Vue 前端、不做数据库、不接真实 LLM API。

## 用户场景

用户希望快速判断一个 AI 应用、前端、AIGC 或数据可视化相关岗位是否适合自己，并获得可解释的投递建议与面试准备方向。

## V0 输入

- 固定用户画像文本
- 固定岗位 JD 文本

## V0 输出

规则引擎输出：

- `total_score`
- `rating`
- `skill_score`
- `experience_score`
- `project_score`
- `basic_score`
- `bonus_score`
- `risk_score`
- `matched_items`
- `missing_items`
- `risk_items`
- `recommended_projects`

Mock LLM 输出：

- `greeting_message`
- `interview_talking_points`
- `weakness_reminders`
- `possible_questions`

## 核心能力

1. 解析岗位 JD 中的城市、薪资、经验要求、学历要求、技术关键词和风险关键词。
2. 用可解释规则计算岗位匹配度。
3. 对硬性风险优先处理，例如单休、纯销售、培训贷、薪资低于 8000。
4. 推荐适合在面试中展开的真实项目方向。
5. 生成面试表达建议，但不让 mock LLM 参与最终评分。

## 明确不做

- 不做 Vue 前端
- 不做数据库
- 不接真实 LLM API
- 不生成虚假经历
- 不把用户包装成成熟 Agent/RAG 工程师
- 不做登录、权限、简历文件上传、在线投递

## 验收标准

1. 运行 `python backend/demo_analyze.py` 可以打印完整分析结果。
2. 运行 `python -m unittest discover -s backend/tests` 可以通过 V0 测试。
3. 至少覆盖高匹配 AI 应用岗位、普通 Vue 前端岗位、RAG/Agent 高要求岗位、单休/销售/运营风险岗位、薪资低于底线岗位。

