import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";
import { useSession } from "@/entities/session";
import { translateErrorCode, useI18n } from "@/shared/i18n";
import { Button } from "@/shared/ui/button";
import { Field, Input } from "@/shared/ui/input";

const schema = z.object({
  name: z.string().min(1).max(120),
  email: z.string().email(),
  password: z.string().min(10).max(128),
});

type RegisterValues = z.infer<typeof schema>;

export function RegisterForm({
  inviteToken,
  redirectTo = "/",
}: {
  inviteToken?: string;
  redirectTo?: string;
}) {
  const { t, language } = useI18n();
  const { register: registerUser } = useSession();
  const navigate = useNavigate();
  const form = useForm<RegisterValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", email: "", password: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await registerUser({ ...values, locale: language, inviteToken });
      await navigate(redirectTo);
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
        <Field label={t("auth.name")} htmlFor="register-name">
          <Input id="register-name" autoComplete="name" {...form.register("name")} />
        </Field>
        <Field label={t("auth.email")} htmlFor="register-email">
          <Input
            id="register-email"
            type="email"
            autoComplete="email"
            {...form.register("email")}
          />
        </Field>
        <Field
          label={t("auth.password")}
          htmlFor="register-password"
          hint={t("auth.passwordHint")}
          error={form.formState.errors.password ? t("errors.WEAK_PASSWORD") : undefined}
        >
          <Input
            id="register-password"
            type="password"
            autoComplete="new-password"
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
        {t("auth.registerCta")}
      </Button>
      <p className="text-sm text-ash">
        {t("auth.hasAccount")}{" "}
        <Link to="/login" className="plain">
          {t("auth.signIn")}
        </Link>
      </p>
    </form>
  );
}
