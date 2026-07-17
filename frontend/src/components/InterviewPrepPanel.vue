<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { generateInterviewPrep } from '../api/jobfitApi'

const props = defineProps({
  recordId: {
    type: Number,
    required: true,
  },
})

const humanApproved = ref(false)
const interviewPrep = ref(null)
const generationLoading = ref(false)
const generationError = ref('')
const requestSequence = ref(0)

function errorMessage(error) {
  const messages = {
    403: '请先确认隐私说明并授权本次生成。',
    404: '该记录不存在或已不可用。',
    429: '请求过于频繁，请稍后再试。',
    502: '生成结果无效或上游服务请求失败，请重试。',
    503: '面试准备服务暂不可用或配置异常。',
    504: '生成超时，请稍后重试。',
  }

  if (messages[error?.status]) return messages[error.status]
  if (!error?.status && error instanceof Error) return error.message
  return '生成失败，请稍后重试。'
}

async function generate() {
  if (!humanApproved.value || generationLoading.value) return

  const sequence = requestSequence.value + 1
  requestSequence.value = sequence
  generationLoading.value = true
  generationError.value = ''

  try {
    const result = await generateInterviewPrep(props.recordId)
    if (sequence !== requestSequence.value) return
    interviewPrep.value = result.interview_prep
  } catch (error) {
    if (sequence !== requestSequence.value) return
    generationError.value = errorMessage(error)
  } finally {
    if (sequence === requestSequence.value) {
      generationLoading.value = false
    }
  }
}

watch(
  () => props.recordId,
  () => {
    requestSequence.value += 1
    humanApproved.value = false
    interviewPrep.value = null
    generationError.value = ''
    generationLoading.value = false
  },
)

onBeforeUnmount(() => {
  requestSequence.value += 1
})
</script>

<template>
  <section class="panel interview-prep-panel" aria-labelledby="interview-prep-heading">
    <div class="section-heading">
      <h2 id="interview-prep-heading">面试准备</h2>
      <span>由人工确认后生成</span>
    </div>

    <div class="interview-prep-controls">
      <p class="interview-prep-privacy">
        生成时会将本记录中的用户画像、岗位 JD、分析结果和行动计划发送给外部大模型服务。不会自动修改评分、求职状态或数据库记录；生成结果暂不保存，刷新页面后会消失。
      </p>

      <label class="interview-prep-consent">
        <input v-model="humanApproved" type="checkbox" :disabled="generationLoading" />
        <span>我已了解并同意发送上述内容，用于本次面试准备生成。</span>
      </label>

      <div class="interview-prep-actions">
        <button
          class="primary-button"
          type="button"
          :disabled="!humanApproved || generationLoading"
          @click="generate"
        >
          {{
            generationLoading
              ? '正在生成……'
              : interviewPrep
                ? '重新生成面试准备'
                : '生成面试准备'
          }}
        </button>
        <p v-if="generationLoading" class="interview-prep-loading" aria-live="polite">
          正在生成结构化面试准备，请稍候……
        </p>
      </div>

      <p v-if="generationError" class="request-error" aria-live="polite">
        {{ generationError }}
      </p>
    </div>

    <div v-if="interviewPrep" class="interview-prep-results">
      <section class="interview-prep-section">
        <h3>岗位重点</h3>
        <ul class="item-list">
          <li v-for="(item, index) in interviewPrep.job_focus" :key="`focus-${index}`">
            {{ item }}
          </li>
        </ul>
      </section>

      <section class="interview-prep-section">
        <h3>可能面试问题与回答提纲</h3>
        <ol class="interview-question-list">
          <li v-for="(item, index) in interviewPrep.likely_questions" :key="`question-${index}`">
            <strong>{{ item.question }}</strong>
            <p>回答提纲</p>
            <ul class="item-list interview-outline-list">
              <li
                v-for="(point, pointIndex) in item.answer_outline"
                :key="`answer-${index}-${pointIndex}`"
              >
                {{ point }}
              </li>
            </ul>
          </li>
        </ol>
      </section>

      <section class="interview-prep-section">
        <h3>项目表达要点</h3>
        <p v-if="interviewPrep.project_talking_points.length === 0" class="interview-prep-empty">
          当前画像中没有可用于展开的项目经历。
        </p>
        <div v-else class="interview-project-list">
          <article
            v-for="(project, index) in interviewPrep.project_talking_points"
            :key="`project-${index}`"
            class="interview-project"
          >
            <strong>{{ project.project_name }}</strong>
            <ul class="item-list">
              <li
                v-for="(point, pointIndex) in project.talking_points"
                :key="`project-point-${index}-${pointIndex}`"
              >
                {{ point }}
              </li>
            </ul>
          </article>
        </div>
      </section>

      <section class="interview-prep-section">
        <h3>诚实能力边界</h3>
        <ul class="item-list warning-list">
          <li v-for="(item, index) in interviewPrep.honest_boundaries" :key="`boundary-${index}`">
            {{ item }}
          </li>
        </ul>
      </section>

      <section class="interview-prep-section">
        <h3>可以向招聘方提出的问题</h3>
        <ul class="item-list">
          <li v-for="(item, index) in interviewPrep.questions_to_ask" :key="`ask-${index}`">
            {{ item }}
          </li>
        </ul>
      </section>

      <p class="interview-prep-ephemeral">本次生成结果仅保留在当前页面，刷新后会消失。</p>
    </div>
  </section>
</template>
