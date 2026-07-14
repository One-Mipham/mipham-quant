import { createRouter, createWebHistory } from 'vue-router'
import BasicLayout from '@/layouts/BasicLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
  },
  {
    path: '/',
    component: BasicLayout,
    children: [
      { path: '', name: 'Dashboard', component: () => import('@/views/dashboard/Dashboard.vue') },
      { path: 'chart/:market?/:symbol?', name: 'Chart', component: () => import('@/views/chart/Chart.vue') },
      { path: 'strategy', name: 'Strategy', component: () => import('@/views/strategy/Strategy.vue') },
      { path: 'backtest', name: 'Backtest', component: () => import('@/views/backtest/Backtest.vue') },
      { path: 'news', name: 'News', component: () => import('@/views/news/News.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
