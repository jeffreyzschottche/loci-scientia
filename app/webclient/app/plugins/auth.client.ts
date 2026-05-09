export default defineNuxtPlugin(() => {
  const authStore = useAuthStore()

  authStore.loadFromLocalStorage()
})
