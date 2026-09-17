import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { SessionProvider } from "@/entities/session";
import { createQueryClient } from "@/shared/api/query";
import { I18nProvider } from "@/shared/i18n";
import { ThemeProvider } from "@/shared/lib/theme";
import { ToastProvider } from "@/shared/ui/toast";

const queryClient = createQueryClient();

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <I18nProvider>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <SessionProvider>
            <ToastProvider>{children}</ToastProvider>
          </SessionProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </I18nProvider>
  );
}
