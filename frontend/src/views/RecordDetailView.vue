<script setup>
defineProps({
  id: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <div class="page detail-page">
    <RouterLink class="back-link" to="/records">返回历史记录</RouterLink>

    <header class="page-header">
      <div>
        <p class="eyebrow">记录 #{{ id }}</p>
        <h1>历史记录详情</h1>
        <p class="page-description">真实记录详情将在下一步接入。</p>
      </div>
    </header>

    <section class="panel detail-placeholder">
      <h2>详情暂未加载</h2>
      <p>当前页面仅保留记录编号，不展示与该记录无关的静态岗位、评分或风险信息。</p>
      <RouterLink class="records-state-link" to="/records">返回历史记录</RouterLink>
    </section>
  </div>
</template>
