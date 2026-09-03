const SENTRY_FETCH_PATCHED = Symbol.for("sentry.absolute-fetch-patched");

export function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") {
    return;
  }

  const globalState = globalThis as typeof globalThis & {
    [SENTRY_FETCH_PATCHED]?: boolean;
  };

  if (globalState[SENTRY_FETCH_PATCHED]) {
    return;
  }

  const originalFetch = globalThis.fetch.bind(globalThis);
  const configuredOrigin = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();
  const productionOrigin = process.env.VERCEL_URL
    ? `https://${process.env.VERCEL_URL}`
    : null;
  const localOrigin = "http://127.0.0.1:8000";
  const origin = configuredOrigin || productionOrigin || localOrigin;

  globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
    if (typeof input === "string" && input.startsWith("/")) {
      return originalFetch(new URL(input, origin), init);
    }

    if (input instanceof URL && input.pathname.startsWith("/")) {
      return originalFetch(new URL(input.pathname + input.search, origin), init);
    }

    return originalFetch(input, init);
  }) as typeof fetch;

  globalState[SENTRY_FETCH_PATCHED] = true;
}
