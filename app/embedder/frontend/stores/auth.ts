import { defineStore } from 'pinia';
import type { User } from '~/types/User';
import type {
  LoginResponse,
  MessageResponse,
} from '~/types/ApiResponse';

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null);
  const user = ref<User | null>(null);
  const adminImpersonating = ref(false);

  const isLoggedIn = computed(() => !!token.value);
  const isPremium = computed(() => !!user.value?.premium);

  function setSession(newToken: string, newUser: User) {
    token.value = newToken;
    user.value = newUser;
    if (import.meta.client) {
      localStorage.setItem('auth_token', newToken);
      localStorage.setItem('auth_user', JSON.stringify(newUser));
    }
  }

  function setAdminImpersonation(isImpersonating: boolean) {
    adminImpersonating.value = isImpersonating;
    if (import.meta.client) {
      if (isImpersonating) {
        localStorage.setItem('admin_impersonating', '1');
      } else {
        localStorage.removeItem('admin_impersonating');
      }
    }
  }

  function logout() {
    token.value = null;
    user.value = null;
    adminImpersonating.value = false;
    if (import.meta.client) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      localStorage.removeItem('admin_impersonating');
    }
  }

  async function restore() {
    if (import.meta.client) {
      const storedToken = localStorage.getItem('auth_token');
      const storedUser = localStorage.getItem('auth_user');
      if (storedToken && storedUser) {
        token.value = storedToken;
        user.value = JSON.parse(storedUser);
      }
      adminImpersonating.value = localStorage.getItem('admin_impersonating') === '1';
    }
  }

  async function login(email: string, password: string) {
    const api = useApi();
    const response = await api.post<LoginResponse>('/login', { email, password });
    setSession(response.token, response.user);
    return response.user;
  }

  async function forgotPassword(email: string) {
    const api = useApi();
    return await api.post<MessageResponse>('/forgot-password', { email });
  }

  async function resetPassword(
    resetToken: string,
    email: string,
    password: string,
    password_confirmation: string
  ) {
    const api = useApi();
    return await api.post<MessageResponse>('/reset-password', {
      token: resetToken,
      email,
      password,
      password_confirmation,
    });
  }

  async function resendVerification() {
    const api = useApi();
    return await api.post<MessageResponse>('/email/resend');
  }

  return {
    token,
    user,
    isLoggedIn,
    adminImpersonating,
    setSession,
    setAdminImpersonation,
    logout,
    restore,
    login,
    forgotPassword,
    resetPassword,
    resendVerification,
    isPremium,
  };
});
