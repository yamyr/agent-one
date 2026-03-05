import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: () => import('../pages/LandingPage.vue'),
    },
    {
      path: '/app',
      name: 'simulation',
      component: () => import('../pages/SimulationPage.vue'),
    },
    {
      path: '/replay',
      name: 'replay',
      component: () => import('../pages/ReplayPage.vue'),
    },
  ],
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
})

export default router
