/** Simulates network latency for the API modules that are still mocked. */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
