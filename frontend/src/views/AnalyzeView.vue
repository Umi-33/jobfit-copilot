<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { analyzeJob, checkHealth } from '../api/jobfitApi'
import AnalysisSummary from '../components/AnalysisSummary.vue'

const form = reactive({
  companyName: '',
  jobTitle: '',
  city: '',
  profileText: '',
  jdText: '',
})

const fieldLabels = {
  companyName: '公司名称',
  jobTitle: '岗位名称',
  city: '城市',
  profileText: '用户画像',
  jdText: '岗位 JD',
}

const errors = ref({})
const requestError = ref('')
const loading = ref(false)
const analysis = ref(null)
const actionPlan = ref(null)
const healthState = ref('checking')

const healthLabel = computed(() => {
  if (healthState.value === 'online') return '后端已连接'
  if (healthState.value === 'offline') return '后端未连接'
  return '正在检查后端'
})

function clearFieldError(field) {
  if (!errors.value[field]) return
  const nextErrors = { ...errors.value }
  delete nextErrors[field]
  errors.value = nextErrors
}

function validateForm() {
  const nextErrors = {}
  for (const [field, label] of Object.entries(fieldLabels)) {
    if (!form[field].trim()) {
      nextErrors[field] = `请填写${label}`
    }
  }
  errors.value = nextErrors
  return Object.keys(nextErrors).length === 0
}

async function submitAnalysis() {
  if (loading.value || !validateForm()) return

  loading.value = true
  requestError.value = ''

  try {
    const result = await analyzeJob({
      profileText: form.profileText.trim(),
      jdText: form.jdText.trim(),
    })
    analysis.value = result.analysis
    actionPlan.value = result.action_plan
  } catch (error) {
    analysis.value = null
    actionPlan.value = null
    requestError.value = error instanceof Error ? error.message : '分析请求失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    await checkHealth()
    healthState.value = 'online'
  } catch {
    healthState.value = 'offline'
  }
})
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p class="eyebrow">岗位评估</p>
        <h1>岗位分析</h1>
        <p class="page-description">录入用户画像与岗位信息，查看匹配度和下一步建议。</p>
      </div>
      <span class="status-label" :class="`status-label--${healthState}`">{{ healthLabel }}</span>
    </header>

    <div class="analyze-grid">
      <section class="panel form-panel" aria-labelledby="input-heading">
        <div class="section-heading">
          <h2 id="input-heading">分析输入</h2>
          <span>公司信息暂不保存</span>
        </div>

        <form class="analysis-form" novalidate @submit.prevent="submitAnalysis">
          <div class="field-row field-row--meta">
            <label>
              <span>公司名称</span>
              <input
                v-model="form.companyName"
                type="text"
                placeholder="例如：示例科技"
                :aria-invalid="Boolean(errors.companyName)"
                @input="clearFieldError('companyName')"
              />
              <small v-if="errors.companyName" class="field-error">{{ errors.companyName }}</small>
            </label>
            <label>
              <span>岗位名称</span>
              <input
                v-model="form.jobTitle"
                type="text"
                placeholder="例如：AI 应用开发"
                :aria-invalid="Boolean(errors.jobTitle)"
                @input="clearFieldError('jobTitle')"
              />
              <small v-if="errors.jobTitle" class="field-error">{{ errors.jobTitle }}</small>
            </label>
            <label>
              <span>城市</span>
              <input
                v-model="form.city"
                type="text"
                placeholder="例如：上海，支持远程"
                :aria-invalid="Boolean(errors.city)"
                @input="clearFieldError('city')"
              />
              <small v-if="errors.city" class="field-error">{{ errors.city }}</small>
            </label>
          </div>

          <div class="text-field-grid">
            <label>
              <span>用户画像</span>
              <textarea
                v-model="form.profileText"
                rows="8"
                placeholder="粘贴脱敏后的用户画像文本"
                :aria-invalid="Boolean(errors.profileText)"
                @input="clearFieldError('profileText')"
              ></textarea>
              <small v-if="errors.profileText" class="field-error">{{ errors.profileText }}</small>
            </label>

            <label>
              <span>岗位 JD</span>
              <textarea
                v-model="form.jdText"
                rows="8"
                placeholder="粘贴岗位职责与任职要求"
                :aria-invalid="Boolean(errors.jdText)"
                @input="clearFieldError('jdText')"
              ></textarea>
              <small v-if="errors.jdText" class="field-error">{{ errors.jdText }}</small>
            </label>
          </div>

          <p v-if="requestError" class="request-error" role="alert">{{ requestError }}</p>
          <button class="primary-button" type="submit" :disabled="loading">
            {{ loading ? '正在分析...' : '开始分析' }}
          </button>
        </form>
      </section>

      <section class="panel result-panel" aria-labelledby="result-heading" aria-live="polite">
        <div class="section-heading">
          <h2 id="result-heading">分析结果</h2>
          <span>{{ analysis ? '分析完成' : '等待输入' }}</span>
        </div>

        <AnalysisSummary v-if="analysis && actionPlan" :analysis="analysis" :action-plan="actionPlan" />

        <div v-else class="result-placeholder">
          <div class="score-placeholder">{{ loading ? '...' : '--' }}</div>
          <h3>{{ loading ? '正在生成分析结果' : '结果将在这里展示' }}</h3>
          <p>{{ loading ? '规则引擎与 Agent Planner 正在处理，请勿重复提交。' : '提交后将显示评分、风险、待确认项和行动建议。' }}</p>
        </div>
      </section>
    </div>
  </div>
</template>
