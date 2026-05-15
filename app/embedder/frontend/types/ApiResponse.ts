import type { User } from './User';

export interface LoginResponse {
  token: string;
  user: User;
}

export interface MessageResponse {
  message: string;
}
