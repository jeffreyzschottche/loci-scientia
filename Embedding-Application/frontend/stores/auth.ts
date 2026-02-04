import { defineStore } from 'pinia';
import type { User } from '~/types/User';
import type {
  LoginResponse,
  RegisterResponse,
  MessageResponse,
  ProfileResponse,
} from '~/types/ApiResponse';
import type { ProfileUpdatePayload, ChangePasswordPayload } from '~/types/Account';

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null);
  const user = ref<User | null>(null);

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

  function logout() {
    token.value = null;
    user.value = null;
    if (import.meta.client) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
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
    }
  }

  async function login(email: string, password: string) {
    const api = useApi();
    const response = await api.post<LoginResponse>('/login', { email, password });
    setSession(response.token, response.user);
    return response.user;
  }

  async function register(
    name: string,
    email: string,
    password: string,
    password_confirmation: string
  ) {
    const api = useApi();
    const response = await api.post<RegisterResponse>('/register', {
      name,
      email,
      password,
      password_confirmation,
    });
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

  async function updateProfile(data: ProfileUpdatePayload) {
    const api = useApi();
    const response = await api.patch<ProfileResponse>('/profile', data);
    user.value = response.user;
    if (import.meta.client) {
      localStorage.setItem('auth_user', JSON.stringify(response.user));
    }
    return response;
  }

  async function changePassword(data: ChangePasswordPayload) {
    const api = useApi();
    return await api.patch<MessageResponse>('/password', {
      current_password: data.current_password,
      password: data.password,
      password_confirmation: data.password_confirmation,
    });
  }

  return {
    token,
    user,
    isLoggedIn,
    setSession,
    logout,
    restore,
    login,
    register,
    forgotPassword,
    resetPassword,
    resendVerification,
    isPremium,
    updateProfile,
    changePassword,
  };
});
