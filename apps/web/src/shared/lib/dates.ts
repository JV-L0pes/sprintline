const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function parseIsoDate(value: string): Date {
  if (!ISO_DATE.test(value)) {
    throw new Error(`Data ISO inválida: ${value}`);
  }
  const [year, month, day] = value.split("-").map(Number) as [number, number, number];
  return new Date(Date.UTC(year, month - 1, day));
}

export function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setUTCDate(result.getUTCDate() + days);
  return result;
}

export function diffInDays(start: Date, end: Date): number {
  return Math.round((end.getTime() - start.getTime()) / 86_400_000);
}

export function isValidSprintRange(startDate: string, endDate: string): boolean {
  if (!ISO_DATE.test(startDate) || !ISO_DATE.test(endDate)) {
    return false;
  }
  const duration = diffInDays(parseIsoDate(startDate), parseIsoDate(endDate)) + 1;
  return duration >= 7 && duration <= 28;
}

export function sprintDayCount(startDate: string, endDate: string): number {
  return diffInDays(parseIsoDate(startDate), parseIsoDate(endDate)) + 1;
}

export function daysRemaining(endDate: string, todayIso: string): number {
  return Math.max(0, diffInDays(parseIsoDate(todayIso), parseIsoDate(endDate)));
}

export function formatDate(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale === "pt-BR" ? "pt-BR" : "en-US", {
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  }).format(parseIsoDate(iso));
}

export function formatDateFull(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale === "pt-BR" ? "pt-BR" : "en-US", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(parseIsoDate(iso));
}

export function formatNumber(value: number, locale: string, digits = 1): string {
  return new Intl.NumberFormat(locale === "pt-BR" ? "pt-BR" : "en-US", {
    maximumFractionDigits: digits,
  }).format(value);
}
