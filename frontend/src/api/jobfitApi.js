const API_PREFIX = '/api'

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

async function requestJson(path, options = {}) {
  let response

  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
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
    const detail = typeof payload?.detail === 'string' ? payload.detail : `请求失败（HTTP ${response.status}）`
    throw new Error(detail)
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

  if (!isObject(payload) || !isObject(payload.analysis) || !isObject(payload.action_plan)) {
    throw new Error('后端返回的分析结果不完整。')
  }

  return payload
}
