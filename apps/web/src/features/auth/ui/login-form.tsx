import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";
import { useSession } from "@/entities/session";
import { translateErrorCode, useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Field, Input } from "@/shared/ui/input";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

type LoginValues = z.infer<typeof schema>;

export function LoginForm() {
  const { t } = useI18n();
  const { login } = useSession();
  const navigate = useNavigate();
  const form = useForm<LoginValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await login(values.email, values.password);
      await navigate("/");
    } catch (error) {
      const apiError = error as { code?: string; detail?: string };
      form.setError("root", {
        message: translateErrorCode(t, apiError.code, apiError.detail),
      });
    }
  });

  return (
    <form onSubmit={(event) => void onSubmit(event)} className="grid gap-5" noValidate>
      <div className="fade on grid gap-5">
        <Field label={t("auth.email")} htmlFor="login-email">
          <Input id="login-email" type="email" autoComplete="email" {...form.register("email")} />
        </Field>
        <Field
          label={t("auth.password")}
          htmlFor="login-password"
          error={form.formState.errors.password ? t("errors.REQUEST_VALIDATION_ERROR") : undefined}
        >
          <Input
            id="login-password"
            type="password"
            autoComplete="current-password"
            {...form.register("password")}
          />
        </Field>
      </div>
      {form.formState.errors.root?.message ? (
        <p className="error-text" role="alert">
          {form.formState.errors.root.message}
        </p>
      ) : null}
      <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
        {t("auth.loginCta")}
      </Button>
      <p className="text-sm text-ash">
        {t("auth.noAccount")}{" "}
        <Link to="/register" className="plain">
          {t("auth.signUp")}
        </Link>
      </p>
    </form>
  );
}
