<script setup>
import { computed } from 'vue'

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
})

const records = {
  1: { company: '澄明科技', title: 'AI 应用开发助理', city: '上海', rating: 'A-' },
  2: { company: '远见数据', title: 'Vue 前端工程师', city: '杭州', rating: 'B+' },
  3: { company: '启程智能', title: 'Agent 平台工程师', city: '北京', rating: 'C+' },
}

const record = computed(() => records[props.id] ?? records[1])
</script>

<template>
  <div class="page detail-page">
    <RouterLink class="back-link" to="/records">返回历史记录</RouterLink>

    <header class="detail-header">
      <div>
        <p class="eyebrow">记录 #{{ id }}</p>
        <h1>{{ record.title }}</h1>
        <p class="page-description">{{ record.company }} · {{ record.city }}</p>
      </div>
      <div class="detail-score">
        <span>综合评级</span>
        <strong>{{ record.rating }}</strong>
      </div>
    </header>

    <section class="summary-strip" aria-label="岗位摘要">
      <div><span>决策</span><strong>可投但需确认</strong></div>
      <div><span>风险等级</span><strong>中低风险</strong></div>
      <div><span>当前状态</span><strong>待确认</strong></div>
    </section>

    <div class="detail-grid">
      <section class="panel detail-section">
        <div class="section-heading"><h2>匹配概览</h2></div>
        <ul class="item-list positive-list">
          <li>前端技术栈与岗位主要方向匹配</li>
          <li>具备 AI API 集成和结构化输出经验</li>
          <li>项目可用于说明 Human-in-the-loop 流程</li>
        </ul>
      </section>

      <section class="panel detail-section">
        <div class="section-heading"><h2>风险与待确认项</h2></div>
        <ul class="item-list warning-list">
          <li>工作制未在 JD 中明确说明</li>
          <li>需要确认岗位技术与运营职责占比</li>
          <li>生产环境要求和团队带教情况未知</li>
        </ul>
      </section>

      <section class="panel detail-section action-section">
        <div class="section-heading"><h2>行动建议</h2></div>
        <p class="action-name">先向招聘方确认关键信息</p>
        <p>准备项目介绍与岗位相关案例，确认工作制和职责边界后，再由人工决定是否投递。</p>
        <div class="approval-note">所有关键动作均需人工确认</div>
      </section>
    </div>
  </div>
</template>
