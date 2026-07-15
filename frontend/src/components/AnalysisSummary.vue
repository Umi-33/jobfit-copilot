<script setup>
import ResultList from './ResultList.vue'

defineProps({
  analysis: {
    type: Object,
    required: true,
  },
  actionPlan: {
    type: Object,
    required: true,
  },
})

function asList(value) {
  return Array.isArray(value) ? value : []
}
</script>

<template>
  <div class="analysis-summary">
    <div class="score-summary">
      <div class="score-value">
        <strong>{{ analysis.total_score ?? '--' }}</strong>
        <span>总分</span>
      </div>
      <div class="score-facts">
        <div><span>评级</span><strong>{{ analysis.rating || '未提供' }}</strong></div>
        <div><span>决策</span><strong>{{ analysis.decision || '未提供' }}</strong></div>
        <div><span>风险等级</span><strong>{{ analysis.risk_level || '未提供' }}</strong></div>
      </div>
    </div>

    <div class="result-groups">
      <ResultList title="匹配项" :items="asList(analysis.matched_items)" empty-text="暂无明确匹配项" tone="positive" />
      <ResultList title="缺失项" :items="asList(analysis.missing_items)" empty-text="暂无明确缺失项" />
      <ResultList title="硬风险" :items="asList(analysis.hard_risks)" empty-text="未识别到硬风险" tone="danger" />
      <ResultList title="软风险" :items="asList(analysis.soft_risks)" empty-text="未识别到软风险" tone="warning" />
      <ResultList title="待确认项" :items="asList(analysis.unknown_items)" empty-text="暂无待确认项" tone="warning" />
      <ResultList title="推荐项目" :items="asList(analysis.recommended_projects)" empty-text="暂无可推荐项目" tone="positive" />
    </div>

    <section class="action-plan-summary">
      <div class="result-group-heading">
        <h3>主要行动</h3>
        <span>需人工确认</span>
      </div>
      <p class="primary-action">{{ actionPlan.primary_action || '未提供行动建议' }}</p>
      <ResultList
        title="人工确认节点"
        :items="asList(actionPlan.human_checkpoints)"
        empty-text="暂无人工确认节点"
      />
    </section>

    <details class="agent-trace">
      <summary>查看 Agent Trace</summary>
      <ResultList title="规则轨迹" :items="asList(actionPlan.agent_trace)" empty-text="暂无规则轨迹" />
    </details>
  </div>
</template>
