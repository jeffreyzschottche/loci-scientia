export default defineNuxtRouteMiddleware((to) => {
  if (import.meta.server) return

  const authStore = useAuthStore()

  if (to.path === '/setup') {
    if (authStore.isAuthenticated && authStore.isDeviceConfigured && to.query.changeDevice !== '1') {
      return navigateTo('/')
    }
    return
  }

  if (!authStore.isDeviceConfigured) {
    return navigateTo('/setup')
  }

  if (!authStore.isAuthenticated && to.path !== '/login') {
    return navigateTo('/login')
  }

  if (authStore.isAuthenticated && to.path === '/login') {
    return navigateTo('/')
  }
})
