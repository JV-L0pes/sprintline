const KEY_MAX = 10;
const KEY_MIN = 2;

/**
 * Sugere a chave do projeto a partir do nome (ex.: "App Mobile" -> "APP"),
 * no mesmo espírito do prefixo automático do Linear/Jira. Evita colisões
 * com as chaves já existentes, sufixando 2, 3, ...
 */
export function suggestProjectKey(name: string, taken: ReadonlySet<string> = new Set()): string {
  const words =
    name
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toUpperCase()
      .match(/[A-Z0-9]+/g) ?? [];
  const first = words[0] ?? "";
  let base = first.length >= 2 ? first.slice(0, 4) : "";
  if (!base && words.length >= 2) {
    base = words
      .slice(0, 4)
      .map((word) => word[0] ?? "")
      .join("");
  }
  if (!base) {
    base = words.join("").slice(0, 4);
  }
  // a chave precisa começar com letra
  base = base.replace(/^[0-9]+/, "").slice(0, KEY_MAX);
  if (base.length < KEY_MIN) {
    return "";
  }
  let candidate = base;
  let counter = 2;
  while (taken.has(candidate)) {
    const suffix = String(counter);
    candidate = `${base.slice(0, KEY_MAX - suffix.length)}${suffix}`;
    counter += 1;
  }
  return candidate;
}
