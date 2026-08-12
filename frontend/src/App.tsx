/**
 * POLIS shell — Week 1 scaffold only.
 *
 * Proves the toolchain and design tokens work end to end and that the backend
 * is reachable. Real pages arrive in Phase 6 (Weeks 7-12) per FLOW §4.
 */
import { useEffect, useState } from 'react';

type Health = 'checking' | 'ok' | 'unreachable';

export default function App() {
  const [health, setHealth] = useState<Health>('checking');

  useEffect(() => {
    fetch('/api/v1/health')
      .then((r) => (r.ok ? setHealth('ok') : setHealth('unreachable')))
      .catch(() => setHealth('unreachable'));
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-line px-6 py-4">
        <h1 className="text-h1 text-ink-primary">POLIS</h1>
        <p className="text-small text-ink-secondary">
          Political Open Source Language Intelligence System
        </p>
      </header>

      <main className="flex-1 px-6 py-8">
        <div className="max-w-2xl rounded-md border border-line bg-surface-card p-5">
          <h2 className="text-h2 text-ink-primary mb-2">Week 1 scaffold</h2>
          <p className="text-body text-ink-secondary mb-4">
            Toolchain and design tokens verified. Pages are built in Phase 6.
          </p>

          <dl className="text-body space-y-1">
            <div className="flex gap-2">
              <dt className="text-ink-muted w-32">Backend</dt>
              <dd className="text-ink-primary">
                {health === 'checking' && 'Checking…'}
                {health === 'ok' && 'Reachable'}
                {health === 'unreachable' && 'Not reachable — is uvicorn running on :8000?'}
              </dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-ink-muted w-32">Model</dt>
              <dd className="text-ink-primary">Stub (polis-stub-v0.0.1)</dd>
            </div>
          </dl>
        </div>
      </main>

      {/* PRIV-12 — present on every page, not dismissible. */}
      <footer className="border-t border-line px-6 py-3 text-small text-ink-muted">
        POLIS is a university Final Year Project prototype. Not affiliated with the United
        Nations.
      </footer>
    </div>
  );
}
