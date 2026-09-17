export const TRELLO_PENDING_KEY = "cadencia.trello.connect";
export const TRELLO_CONSUMED_KEY = "cadencia.trello.consumed";

/** Extrai o token devolvido pelo Trello no fragmento da URL de callback. */
export function parseTrelloToken(hash: string): string | null {
  const normalized = hash.startsWith("#") ? hash.slice(1) : hash;
  if (normalized === "") {
    return null;
  }
  const params = new URLSearchParams(normalized);
  const token = params.get("token");
  return token && token.length > 0 ? token : null;
}

export function jobStateLabelKey(state: string): string {
  switch (state) {
    case "DONE":
      return "integrations.done";
    case "RUNNING":
      return "integrations.running";
    case "FAILED":
      return "integrations.failed";
    default:
      return "integrations.pending";
  }
}
