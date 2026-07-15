<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  items: {
    type: Array,
    default: () => [],
  },
  emptyText: {
    type: String,
    default: '暂无',
  },
  tone: {
    type: String,
    default: 'neutral',
  },
})

function itemTitle(item) {
  if (typeof item === 'string') return item
  return item?.item || item?.name || item?.question || item?.type || item?.step || '未命名项目'
}

function itemDetail(item) {
  if (!item || typeof item === 'string') return ''
  if (item.observation && item.reason) return `${item.observation}；${item.reason}`
  return item.reason || item.summary || ''
}

function itemMeta(item) {
  if (!item || typeof item === 'string') return ''
  if (typeof item.points === 'number') return `${item.points > 0 ? '+' : ''}${item.points} 分`
  if (typeof item.penalty === 'number') return `${item.penalty} 分`
  if (item.required === true) return '需要确认'
  return ''
}
</script>

<template>
  <section class="result-group" :class="`result-group--${tone}`">
    <div class="result-group-heading">
      <h3>{{ title }}</h3>
      <span>{{ items.length }}</span>
    </div>

    <p v-if="items.length === 0" class="empty-list">{{ emptyText }}</p>
    <ul v-else class="result-list">
      <li v-for="(item, index) in items" :key="`${title}-${index}`">
        <div>
          <strong>{{ itemTitle(item) }}</strong>
          <p v-if="itemDetail(item)">{{ itemDetail(item) }}</p>
        </div>
        <span v-if="itemMeta(item)" class="result-meta">{{ itemMeta(item) }}</span>
      </li>
    </ul>
  </section>
</template>
