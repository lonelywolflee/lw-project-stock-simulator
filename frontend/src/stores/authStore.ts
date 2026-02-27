import { create } from "zustand";
import { fetchMe, loginApi, logoutApi, type User } from "@/api/auth";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,

  login: async (username, password) => {
    set({ error: null });
    try {
      const user = await loginApi(username, password);
      set({ user, isAuthenticated: true, error: null });
    } catch {
      set({ error: "아이디 또는 비밀번호가 올바르지 않습니다." });
      throw new Error("login failed");
    }
  },

  logout: async () => {
    await logoutApi();
    set({ user: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    set({ isLoading: true });
    try {
      const user = await fetchMe();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
