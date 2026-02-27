import axios from "axios";

const api = axios.create({
  baseURL: "/api/auth",
  headers: { "Content-Type": "application/json" },
});

export interface User {
  id: number;
  username: string;
  is_staff: boolean;
}

export async function loginApi(
  username: string,
  password: string,
): Promise<User> {
  const { data } = await api.post<User>("/login", { username, password });
  return data;
}

export async function logoutApi(): Promise<void> {
  await api.post("/logout");
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>("/me");
  return data;
}
