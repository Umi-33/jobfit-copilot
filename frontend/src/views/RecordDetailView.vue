<script setup>
import { computed, ref, watch } from 'vue'
import { getJobRecord, updateJobRecordStatus } from '../api/jobfitApi'
import AnalysisSummary from '../components/AnalysisSummary.vue'
import InterviewPrepPanel from '../components/InterviewPrepPanel.vue'

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
})

const statusOptions = [
  { value: 'pending_confirmation', label: '待确认' },
  { value: 'not_suitable', label: '不合适' },
  { value: 'preparing_application', label: '准备申请' },
  { value: 'applied', label: '已投递' },
  { value: 'preparing_interview', label: '准备面试' },
  { value: 'archived', label: '已归档' },
]

const riskLabels = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
}

const record = ref(null)
const loading = ref(false)
const loadError = ref('')
const loadErrorType = ref('')
const selectedStatus = ref('')
const statusUpdating = ref(false)
const statusError = ref('')
const statusSuccess = ref('')

const normalizedRecordId = computed(() => {
  if (!/^\d+$/.test(props.id)) return null
  const value = Number(props.id)
  return Number.isSafeInteger(value) && value > 0 ? value : null
})

const statusChanged = computed(() => {
  return Boolean(record.value) && selectedStatus.value !== record.value.status
})

function displayMappedValue(value, labels) {
  if (!value) return '未知'
  return labels[value] || value
}

function displayStatus(value) {
  return displayMappedValue(
    value,
    Object.fromEntries(statusOptions.map((option) => [option.value, option.label])),
  )
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

function handleStatusSelection() {
  statusError.value = ''
  statusSuccess.value = ''
}

async function loadRecord() {
  record.value = null
  selectedStatus.value = ''
  statusError.value = ''
  statusSuccess.value = ''
  loadError.value = ''
  loadErrorType.value = ''

  if (normalizedRecordId.value === null) {
    loadErrorType.value = 'invalid'
    loadError.value = '记录编号无效'
    return
  }

  loading.value = true
  try {
    const result = await getJobRecord(normalizedRecordId.value)
    record.value = result
    selectedStatus.value = result.status || ''
  } catch (error) {
    if (error?.status === 404) {
      loadErrorType.value = 'not-found'
      loadError.value = '记录不存在或已不可用'
    } else {
      loadErrorType.value = 'request'
      loadError.value = error instanceof Error ? error.message : '记录详情加载失败，请稍后重试。'
    }
  } finally {
    loading.value = false
  }
}

async function saveStatus() {
  if (
    !record.value ||
    normalizedRecordId.value === null ||
    !statusChanged.value ||
    statusUpdating.value
  ) {
    return
  }

  statusUpdating.value = true
  statusError.value = ''
  statusSuccess.value = ''

  try {
    const result = await updateJobRecordStatus(normalizedRecordId.value, selectedStatus.value)
    record.value = {
      ...record.value,
      status: result.status,
      updated_at: result.updated_at,
    }
    selectedStatus.value = result.status
    statusSuccess.value = '状态更新成功'
  } catch (error) {
    statusError.value = error instanceof Error ? error.message : '状态更新失败，请稍后重试。'
  } finally {
    statusUpdating.value = false
  }
}

watch(() => props.id, loadRecord, { immediate: true })
</script>

<template>
  <div class="page detail-page">
    <RouterLink class="back-link" to="/records">← 返回历史记录</RouterLink>

    <section v-if="loading" class="panel records-state" aria-live="polite">
      <p>正在加载记录详情……</p>
    </section>

    <section v-else-if="loadError" class="panel records-state" aria-live="polite">
      <h1>{{ loadError }}</h1>
      <p v-if="loadErrorType === 'invalid'">请从历史记录列表进入有效的记录详情。</p>
      <p v-else-if="loadErrorType === 'not-found'">该记录可能不存在，或当前数据库中已无法找到。</p>
      <p v-else>请确认后端服务可用后重新加载。</p>
      <div v-if="loadErrorType !== 'invalid'" class="detail-error-actions">
        <button
          class="secondary-button"
          type="button"
          @click="loadRecord"
        >
          重新加载
        </button>
      </div>
    </section>

    <template v-else-if="record">
      <header class="detail-header">
        <div>
          <p class="eyebrow">记录 #{{ record.id }}</p>
          <h1>{{ record.job_title || '未命名岗位' }}</h1>
          <p class="page-description">
            {{ record.company_name || '未知公司' }} · {{ record.city || '未知城市' }}
          </p>
        </div>
        <div class="detail-score">
          <span>综合评级</span>
          <strong>{{ record.rating || '—' }}</strong>
        </div>
      </header>

      <section class="summary-strip" aria-label="岗位摘要">
        <div><span>判断</span><strong>{{ record.decision || '未知' }}</strong></div>
        <div>
          <span>风险等级</span>
          <strong>{{ displayMappedValue(record.risk_level, riskLabels) }}</strong>
        </div>
        <div><span>创建时间</span><strong>{{ formatLocalTime(record.created_at) }}</strong></div>
        <div><span>更新时间</span><strong>{{ formatLocalTime(record.updated_at) }}</strong></div>
      </section>

      <section class="panel status-panel" aria-labelledby="status-heading">
        <div class="section-heading">
          <h2 id="status-heading">求职状态</h2>
          <span>当前：{{ displayStatus(record.status) }}</span>
        </div>
        <div class="status-controls">
          <label>
            <span>选择状态</span>
            <select
              v-model="selectedStatus"
              :disabled="statusUpdating"
              @change="handleStatusSelection"
            >
              <option v-for="option in statusOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
          <button
            class="secondary-button"
            type="button"
            :disabled="statusUpdating || !statusChanged"
            @click="saveStatus"
          >
            {{ statusUpdating ? '正在保存……' : '保存状态' }}
          </button>
        </div>
        <p v-if="statusError" class="request-error" role="alert">{{ statusError }}</p>
        <p v-if="statusSuccess" class="save-success" role="status">{{ statusSuccess }}</p>
      </section>

      <section class="panel record-analysis-panel" aria-labelledby="analysis-heading">
        <div class="section-heading">
          <h2 id="analysis-heading">评分与行动建议</h2>
          <span>保存时的分析快照</span>
        </div>
        <AnalysisSummary :analysis="record.analysis" :action-plan="record.action_plan" />
      </section>

      <InterviewPrepPanel :record-id="record.id" />

      <section class="raw-inputs" aria-label="原始输入">
        <details class="panel raw-input-details">
          <summary>保存时的用户画像</summary>
          <pre>{{ record.profile_snapshot || '—' }}</pre>
        </details>
        <details class="panel raw-input-details">
          <summary>原始岗位 JD</summary>
          <pre>{{ record.jd_text || '—' }}</pre>
        </details>
      </section>
    </template>
  </div>
</template>
