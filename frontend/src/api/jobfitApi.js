import {
  clearDemoAccessCode,
  getDemoAccessCode,
  isDemoAccessRequired,
} from '../utils/demoAccess'

const API_BASE_URL = String(import.meta.env.VITE_API_BASE_URL || '')
  .trim()
  .replace(/\/+$/, '')
const API_PREFIX = API_BASE_URL ? `${API_BASE_URL}/api` : '/api'
const DEMO_ACCESS_HEADER = 'X-Demo-Access-Code'

const FIELD_LABELS = {
  company_name: '公司名称',
  job_title: '岗位名称',
  city: '城市',
  profile_text: '用户画像',
  jd_text: '岗位 JD',
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isStringArray(value) {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
}

function formatErrorDetail(detail, status) {
  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      const field = Array.isArray(item?.loc) ? item.loc.at(-1) : ''
      const label = FIELD_LABELS[field] || field || '请求字段'
      const message = typeof item?.msg === 'string' ? item.msg : '格式不正确'
      return `${label}：${message}`
    })
    if (messages.length > 0) return messages.join('；')
  }

  return `请求失败（HTTP ${status}）`
}

async function requestJson(path, options = {}) {
  let response
  const demoAccessCode = getDemoAccessCode()
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  if (demoAccessCode && !headers[DEMO_ACCESS_HEADER]) {
    headers[DEMO_ACCESS_HEADER] = demoAccessCode
  }

  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      ...options,
      headers,
    })
  } catch {
    throw new Error('无法连接后端服务，请稍后重试。')
  }

  let payload = null
  try {
    payload = await response.json()
  } catch {
    // Keep null so callers can handle an empty or non-JSON response consistently.
  }

  if (!response.ok) {
    if (response.status === 401 && isDemoAccessRequired()) {
      clearDemoAccessCode({ notify: true })
    }
    const error = new Error(formatErrorDetail(payload?.detail, response.status))
    error.status = response.status
    throw error
  }

  return payload
}

function ensureAnalysisResult(payload) {
  if (!isObject(payload) || !isObject(payload.analysis) || !isObject(payload.action_plan)) {
    throw new Error('后端返回的分析结果不完整。')
  }
  return payload
}

export async function checkHealth() {
  const payload = await requestJson('/health')
  if (payload?.status !== 'ok') {
    throw new Error('后端健康检查返回异常。')
  }
  return payload
}

export async function checkDemoAccess(code) {
  const payload = await requestJson('/access-check', {
    headers: {
      [DEMO_ACCESS_HEADER]: code,
    },
  })
  if (payload?.status !== 'ok') {
    throw new Error('演示访问检查返回异常。')
  }
  return payload
}

export async function analyzeJob({ profileText, jdText }) {
  const payload = await requestJson('/analyze', {
    method: 'POST',
    body: JSON.stringify({
      profile_text: profileText,
      jd_text: jdText,
    }),
  })

  return ensureAnalysisResult(payload)
}

export async function createJobRecord({ companyName, jobTitle, city, profileText, jdText }) {
  const record = await requestJson('/records', {
    method: 'POST',
    body: JSON.stringify({
      company_name: companyName,
      job_title: jobTitle,
      city,
      profile_text: profileText,
      jd_text: jdText,
    }),
  })

  ensureAnalysisResult(record)
  if (record.id === undefined || record.id === null) {
    throw new Error('后端返回的保存记录不完整。')
  }
  return record
}

export async function listJobRecords() {
  const records = await requestJson('/records')
  if (!Array.isArray(records)) {
    throw new Error('后端返回的历史记录列表格式不正确。')
  }
  return records
}

export async function getJobRecord(recordId) {
  const record = await requestJson(`/records/${recordId}`)
  if (
    !isObject(record) ||
    record.id === undefined ||
    record.id === null ||
    !isObject(record.analysis) ||
    !isObject(record.action_plan)
  ) {
    throw new Error('后端返回的记录详情不完整。')
  }
  return record
}

export async function updateJobRecordStatus(recordId, status) {
  const result = await requestJson(`/records/${recordId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })

  if (
    !isObject(result) ||
    result.id === undefined ||
    result.id === null ||
    typeof result.status !== 'string' ||
    typeof result.updated_at !== 'string'
  ) {
    throw new Error('后端返回的状态更新结果不完整。')
  }
  return result
}

export async function generateInterviewPrep(recordId) {
  const result = await requestJson(`/records/${recordId}/interview-prep`, {
    method: 'POST',
    body: JSON.stringify({
      human_approved: true,
    }),
  })

  const prep = result?.interview_prep
  const validQuestions = Array.isArray(prep?.likely_questions) && prep.likely_questions.every(
    (item) =>
      isObject(item) &&
      typeof item.question === 'string' &&
      item.question.trim().length > 0 &&
      isStringArray(item.answer_outline),
  )
  const validProjects =
    Array.isArray(prep?.project_talking_points) &&
    prep.project_talking_points.every(
      (item) =>
        isObject(item) &&
        typeof item.project_name === 'string' &&
        item.project_name.trim().length > 0 &&
        isStringArray(item.talking_points),
    )

  if (
    !isObject(result) ||
    result.record_id !== recordId ||
    !isObject(prep) ||
    !isStringArray(prep.job_focus) ||
    !validQuestions ||
    !validProjects ||
    !isStringArray(prep.honest_boundaries) ||
    !isStringArray(prep.questions_to_ask)
  ) {
    throw new Error('后端返回的面试准备结果不完整。')
  }

  return result
}
