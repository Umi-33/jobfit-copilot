<script setup>
const records = [
  {
    id: 1,
    company: '澄明科技',
    title: 'AI 应用开发助理',
    city: '上海',
    rating: 'A-',
    decision: '可投但需确认',
    risk: '低风险',
    updatedAt: '2026-07-14',
  },
  {
    id: 2,
    company: '远见数据',
    title: 'Vue 前端工程师',
    city: '杭州',
    rating: 'B+',
    decision: '建议先确认信息',
    risk: '中风险',
    updatedAt: '2026-07-12',
  },
  {
    id: 3,
    company: '启程智能',
    title: 'Agent 平台工程师',
    city: '北京',
    rating: 'C+',
    decision: '谨慎推进',
    risk: '中风险',
    updatedAt: '2026-07-09',
  },
]
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p class="eyebrow">分析档案</p>
        <h1>历史记录</h1>
        <p class="page-description">查看已分析岗位的摘要和当前判断。</p>
      </div>
      <span class="record-count">{{ records.length }} 条记录</span>
    </header>

    <section class="records-panel" aria-label="岗位记录列表">
      <div class="records-header" aria-hidden="true">
        <span>岗位</span>
        <span>评分</span>
        <span>判断</span>
        <span>风险</span>
        <span>更新时间</span>
      </div>

      <RouterLink
        v-for="record in records"
        :key="record.id"
        class="record-row"
        :to="`/records/${record.id}`"
      >
        <span class="record-job">
          <strong>{{ record.title }}</strong>
          <small>{{ record.company }} · {{ record.city }}</small>
        </span>
        <span class="rating-badge">{{ record.rating }}</span>
        <span>{{ record.decision }}</span>
        <span class="risk-text">{{ record.risk }}</span>
        <span class="record-date">{{ record.updatedAt }}</span>
      </RouterLink>
    </section>
  </div>
</template>
