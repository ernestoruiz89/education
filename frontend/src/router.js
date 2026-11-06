import { createRouter, createWebHistory } from 'vue-router'
import { usersStore } from '@/stores/user'
import { sessionStore } from '@/stores/session'
import { studentStore } from '@/stores/student'

const routes = [
  { path: '/', redirect: '/schedule' },
  {
    path: '/profile-required',
    name: 'PortalStatus',
    component: () => import('@/pages/PortalStatus.vue'),
    meta: { portalStatus: true },
  },
  {
    path: '/schedule',
    name: 'Schedule',
    component: () => import('@/pages/Schedule.vue'),
  },
  {
    path: '/grades',
    name: 'Grades',
    component: () => import('@/pages/Grades.vue'),
  },
  {
    path: '/fees',
    name: 'Fees',
    component: () => import('@/pages/Fees.vue'),
  },
  {
    path: '/attendance',
    name: 'Attendance',
    component: () => import('@/pages/Attendance.vue'),
  },
  {
    path: '/:catchAll(.*)',
    redirect: '/schedule',
  },
]

let router = createRouter({
  history: createWebHistory('/student-portal'),
  routes,
})

router.beforeEach(async (to) => {
  const { isLoggedIn } = sessionStore()
  const { user } = usersStore()
  const portal = studentStore()

  if (!isLoggedIn) {
    const redirect = '/student-portal' + to.fullPath
    window.location.replace(
      '/login?redirect-to=' + encodeURIComponent(redirect)
    )
    return false
  }

  try {
    if (!user.data?.name) await user.reload()
    if (!portal.student.data) await portal.student.reload()
    if (!portal.studentInfo.name && to.name !== 'PortalStatus') {
      return { name: 'PortalStatus' }
    }
    if (portal.studentInfo.name && to.name === 'PortalStatus') {
      return { name: 'Schedule' }
    }
  } catch (error) {
    portal.loadError = true
    if (to.name !== 'PortalStatus') return { name: 'PortalStatus' }
  }
})

export default router
