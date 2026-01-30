import type { User } from './User';

export interface LoginResponse {
  token: string;
  user: User;
}

export interface RegisterResponse {
  token: string;
  user: User;
}

export interface MessageResponse {
  message: string;
}

export interface ProfileResponse {
  message: string;
  user: User;
}
