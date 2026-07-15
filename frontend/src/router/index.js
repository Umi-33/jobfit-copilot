import { createRouter, createWebHistory } from 'vue-router'
import AnalyzeView from '../views/AnalyzeView.vue'
import RecordDetailView from '../views/RecordDetailView.vue'
import RecordsView from '../views/RecordsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'analyze',
      component: AnalyzeView,
    },
    {
      path: '/records',
      name: 'records',
      component: RecordsView,
    },
    {
      path: '/records/:id',
      name: 'record-detail',
      component: RecordDetailView,
      props: true,
    },
  ],
})

export default router
