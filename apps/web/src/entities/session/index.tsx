import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { apiRequest, setAccessToken, silentRefresh } from "@/shared/api/client";
import type { SessionResponse, User } from "@/shared/api/types";

interface SessionValue {
  user: User | null;
  status: "booting" | "anonymous" | "authenticated";
  login: (email: string, password: string) => Promise<User>;
  register: (input: {
    email: string;
    name: string;
    password: string;
    locale: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<SessionValue["status"]>("booting");

  useEffect(() => {
    let cancelled = false;
    void silentRefresh().then((session: SessionResponse | null) => {
      if (cancelled) {
        return;
      }
      setUser(session?.user ?? null);
      setStatus(session ? "authenticated" : "anonymous");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const session = await apiRequest<SessionResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
    });
    setAccessToken(session.access_token);
    setUser(session.user);
    setStatus("authenticated");
    return session.user;
  }, []);

  const register = useCallback(
    async (input: { email: string; name: string; password: string; locale: string }) => {
      await apiRequest<User>("/api/v1/auth/register", { method: "POST", body: input });
      await login(input.email, input.password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    try {
      await apiRequest<undefined>("/api/v1/auth/logout", { method: "POST" });
    } finally {
      setAccessToken(null);
      setUser(null);
      setStatus("anonymous");
    }
  }, []);

  const value = useMemo(
    () => ({ user, status, login, register, logout }),
    [user, status, login, register, logout],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession deve ser usado dentro de SessionProvider");
  }
  return context;
}
