export default defineNuxtRouteMiddleware((to) => {
  if (import.meta.server) return

  const authStore = useAuthStore()

  // The SPA is always served by FastAPI (same origin), so /setup is obsolete.
  if (to.path === '/setup') {
    return navigateTo(authStore.isAuthenticated ? '/' : '/login')
  }

  if (!authStore.isAuthenticated && to.path !== '/login') {
    return navigateTo('/login')
  }

  if (authStore.isAuthenticated && to.path === '/login') {
    return navigateTo('/')
  }
})
