export async function register() {
  if (process.env.NODE_ENV !== "production") {
    try { await import("brakit"); } catch {}
  }
}
