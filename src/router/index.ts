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
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Dashboard', component: () => import('@/views/dashboard/Dashboard.vue') },
      { path: 'chart/:market?/:symbol?', name: 'Chart', component: () => import('@/views/chart/Chart.vue') },
      { path: 'strategy', name: 'Strategy', component: () => import('@/views/strategy/Strategy.vue') },
      { path: 'backtest', name: 'Backtest', component: () => import('@/views/backtest/Backtest.vue') },
      { path: 'news', name: 'News', component: () => import('@/views/news/News.vue') },
    ],
  },
  // Catch-all: redirect unknown paths to dashboard (or login if unauthenticated)
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard: redirect unauthenticated users to login
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  const isAuthenticated = !!token

  if (to.path === '/login') {
    // Already logged in? Redirect to dashboard
    if (isAuthenticated) {
      next('/')
      return
    }
    next()
    return
  }

  if (to.matched.some((record) => record.meta.requiresAuth) && !isAuthenticated) {
    next('/login')
    return
  }

  next()
})

export default router
