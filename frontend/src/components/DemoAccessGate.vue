<script setup>
import { onMounted, ref } from 'vue'
import { checkDemoAccess } from '../api/jobfitApi'
import {
  clearDemoAccessCode,
  getDemoAccessCode,
  storeDemoAccessCode,
} from '../utils/demoAccess'

const emit = defineEmits(['granted'])

const accessCode = ref('')
const checking = ref(false)
const accessError = ref('')

async function verify(code, restoring = false) {
  const normalizedCode = code.trim()
  if (!normalizedCode || checking.value) return

  checking.value = true
  accessError.value = ''

  try {
    await checkDemoAccess(normalizedCode)
    storeDemoAccessCode(normalizedCode)
    accessCode.value = ''
    emit('granted')
  } catch {
    clearDemoAccessCode()
    accessCode.value = ''
    accessError.value = restoring
      ? '已保存的演示访问已失效，请重新输入访问码。'
      : '访问码无效或暂时无法验证，请重试。'
  } finally {
    checking.value = false
  }
}

function submit() {
  verify(accessCode.value)
}

onMounted(() => {
  const storedCode = getDemoAccessCode()
  if (storedCode) verify(storedCode, true)
})
</script>

<template>
  <main class="demo-access-page">
    <section class="demo-access-card" aria-labelledby="demo-access-heading">
      <p class="eyebrow">受控访问</p>
      <h1 id="demo-access-heading">JobFit Copilot 受控演示</h1>
      <p class="demo-access-description">
        请输入随演示链接提供的访问码。该访问码仅用于限制公开 Demo 的访问，不代表正式账号系统。
      </p>

      <form class="demo-access-form" @submit.prevent="submit">
        <label>
          <span>演示访问码</span>
          <input
            v-model="accessCode"
            type="password"
            autocomplete="current-password"
            spellcheck="false"
            :disabled="checking"
            aria-describedby="demo-access-help"
          />
        </label>
        <button class="primary-button" type="submit" :disabled="checking || !accessCode.trim()">
          {{ checking ? '正在验证……' : '进入演示' }}
        </button>
      </form>

      <p id="demo-access-help" class="demo-access-help">
        访问码仅保存在当前标签页的会话存储中，关闭标签页后失效。
      </p>
      <p v-if="accessError" class="request-error" role="alert">{{ accessError }}</p>
    </section>
  </main>
</template>
