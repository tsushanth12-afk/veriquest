// Host-side session generation: delayed work cannot apply to a later login.
let generation = 0;
let identity: string | null = null;
export function changeSessionIdentity(id: string | null): number {
  identity = id;
  return ++generation;
}
export function sessionSnapshot() { return { generation, identity }; }
export function isCurrentSession(snapshot: ReturnType<typeof sessionSnapshot>) {
  return snapshot.generation === generation && snapshot.identity === identity;
}
export function requireCurrentSession(snapshot: ReturnType<typeof sessionSnapshot>) {
  if (!isCurrentSession(snapshot)) throw new Error('SESSION_CHANGED: Discarded response from a previous session.');
}
