export interface ProfileUpdatePayload {
  name: string;
  email: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  password: string;
  password_confirmation: string;
}
