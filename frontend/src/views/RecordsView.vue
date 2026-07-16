<script setup>
import { onMounted, ref } from 'vue'
import { listJobRecords } from '../api/jobfitApi'

const records = ref([])
const loading = ref(false)
const loadError = ref('')

const riskLabels = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
}

const statusLabels = {
  pending_confirmation: '待确认',
  not_suitable: '不合适',
  preparing_application: '准备申请',
  applied: '已投递',
  preparing_interview: '准备面试',
  archived: '已归档',
}

function displayMappedValue(value, labels) {
  if (!value) return '未知'
  return labels[value] || value
}

function formatLocalTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

async function loadRecords() {
  if (loading.value) return

  loading.value = true
  loadError.value = ''

  try {
    records.value = await listJobRecords()
  } catch (error) {
    records.value = []
    loadError.value = error instanceof Error ? error.message : '历史记录加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

onMounted(loadRecords)
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p class="eyebrow">分析档案</p>
        <h1>历史记录</h1>
        <p class="page-description">查看已保存岗位的分析摘要和当前状态。</p>
      </div>
      <span class="record-count">{{ records.length }} 条记录</span>
    </header>

    <section v-if="loading" class="records-panel records-state" aria-live="polite">
      <p>正在加载历史记录……</p>
    </section>

    <section v-else-if="loadError" class="records-panel records-state" aria-live="polite">
      <h2>历史记录加载失败</h2>
      <p>{{ loadError }}</p>
      <button class="secondary-button records-state-action" type="button" @click="loadRecords">
        重新加载
      </button>
    </section>

    <section v-else-if="records.length === 0" class="records-panel records-state">
      <h2>暂无历史记录</h2>
      <p>完成岗位分析并保存后，记录会显示在这里。</p>
      <RouterLink class="records-state-action records-state-link" to="/">前往岗位分析</RouterLink>
    </section>

    <section v-else class="records-panel" aria-label="岗位记录列表">
      <div class="records-header" aria-hidden="true">
        <span>岗位</span>
        <span>评分</span>
        <span>判断</span>
        <span>风险</span>
        <span>状态</span>
        <span>更新时间</span>
      </div>

      <RouterLink
        v-for="record in records"
        :key="record.id"
        class="record-row"
        :to="`/records/${record.id}`"
      >
        <span class="record-job">
          <strong>{{ record.job_title || '未命名岗位' }}</strong>
          <small>{{ record.company_name || '未知公司' }} · {{ record.city || '未知城市' }}</small>
        </span>
        <span class="rating-badge">{{ record.rating || '—' }}</span>
        <span class="record-decision">{{ record.decision || '未知' }}</span>
        <span class="risk-text">{{ displayMappedValue(record.risk_level, riskLabels) }}</span>
        <span class="record-status">{{ displayMappedValue(record.status, statusLabels) }}</span>
        <span class="record-date">{{ formatLocalTime(record.updated_at) }}</span>
      </RouterLink>
    </section>
  </div>
</template>
