export const COMMON_TIMEZONES = [
  ["America/Sao_Paulo", "Brasília"],
  ["America/Bahia", "Salvador"],
  ["America/Fortaleza", "Fortaleza"],
  ["America/Recife", "Recife"],
  ["America/Belem", "Belém"],
  ["America/Manaus", "Manaus"],
  ["America/Cuiaba", "Cuiabá"],
  ["America/Rio_Branco", "Rio Branco"],
  ["America/Noronha", "Fernando de Noronha"],
  ["America/New_York", "Nova York"],
  ["America/Los_Angeles", "Los Angeles"],
  ["Europe/Lisbon", "Lisboa"],
  ["Europe/London", "Londres"],
  ["Europe/Madrid", "Madri"],
  ["Europe/Berlin", "Berlim"],
  ["UTC", "UTC"],
] as const;

const FALLBACK = "America/Sao_Paulo";

/** Fuso detectado do navegador, se for um IANA válido; senão, o padrão. */
export function detectTimezone(): string {
  try {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (zone && (zone.includes("/") || zone === "UTC")) {
      return zone;
    }
  } catch {
    // ambiente sem Intl: usa o padrão
  }
  return FALLBACK;
}

/** Lista fixa; se o fuso detectado não estiver nela, ele entra no topo. */
export function timezoneOptions(detected: string): [string, string][] {
  const options = COMMON_TIMEZONES.map(([value, label]) => [value, label] as [string, string]);
  if (!options.some(([value]) => value === detected)) {
    options.unshift([detected, detected]);
  }
  return options;
}
