const API_PREFIX = '/api'

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

  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })
  } catch {
    throw new Error('无法连接后端服务，请确认 FastAPI 已在 127.0.0.1:8000 启动。')
  }

  let payload = null
  try {
    payload = await response.json()
  } catch {
    // Keep null so callers can handle an empty or non-JSON response consistently.
  }

  if (!response.ok) {
    throw new Error(formatErrorDetail(payload?.detail, response.status))
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
