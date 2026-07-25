import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import AnalyzeView from '../views/AnalyzeView.vue'
import RecordDetailView from '../views/RecordDetailView.vue'
import RecordsView from '../views/RecordsView.vue'

const history =
  import.meta.env.VITE_ROUTER_MODE === 'hash'
    ? createWebHashHistory()
    : createWebHistory()

const router = createRouter({
  history,
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
