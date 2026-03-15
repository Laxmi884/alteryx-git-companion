import { useState, useEffect } from 'react'

interface DiffViewerProps {
  sha: string
  file: string          // basename, e.g. "CustomerReport.yxmd"
  folder: string
  commitMessage: string
  onBack: () => void
}

export function DiffViewer({
  sha,
  file,
  folder,
  commitMessage,
  onBack,
}: DiffViewerProps) {
  const [loading, setLoading] = useState(true)
  const [iframeSrc, setIframeSrc] = useState<string | null>(null)
  const [isFirstCommit, setIsFirstCommit] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    let blobUrl: string | null = null
    let cancelled = false

    async function loadDiff() {
      setLoading(true)
      setIsFirstCommit(false)
      setError(null)
      setIframeSrc(null)

      try {
        const res = await fetch(
          `/api/history/${sha}/diff?folder=${encodeURIComponent(folder)}&file=${encodeURIComponent(file)}`
        )
        if (cancelled) return

        const contentType = res.headers.get('content-type') ?? ''
        if (contentType.includes('json')) {
          const data = await res.json() as { is_first_commit?: boolean }
          if (data?.is_first_commit) {
            setIsFirstCommit(true)
            setLoading(false)
            return
          }
        }

        if (!res.ok) {
          setError(`Failed to load diff (HTTP ${res.status})`)
          setLoading(false)
          return
        }

        let html = await res.text()
        if (cancelled) return

        // Blob URLs have a null origin, so localStorage access throws SecurityError
        // in some browsers. Inject a safe in-memory shim before any script runs so
        // vis.js graph initialisation doesn't abort due to a storage exception.
        const localStorageShim = `<script>
(function(){
  var _store = {};
  var _safe = {
    getItem: function(k){ return Object.prototype.hasOwnProperty.call(_store, k) ? _store[k] : null; },
    setItem: function(k, v){ _store[k] = String(v); },
    removeItem: function(k){ delete _store[k]; },
    clear: function(){ _store = {}; },
    key: function(i){ return Object.keys(_store)[i] || null; },
    get length(){ return Object.keys(_store).length; }
  };
  try { localStorage.getItem('__test__'); } catch(e) {
    Object.defineProperty(window, 'localStorage', { value: _safe, writable: true });
  }
})();
<\/script>`;
        // Insert shim immediately after <head> so it runs before any inline scripts
        html = html.replace(/<head>/i, '<head>' + localStorageShim)

        blobUrl = URL.createObjectURL(new Blob([html], { type: 'text/html' }))
        setIframeSrc(blobUrl)
        setLoading(false)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load diff report')
        setLoading(false)
      }
    }

    void loadDiff()

    return () => {
      cancelled = true
      if (blobUrl) URL.revokeObjectURL(blobUrl)
    }
  }, [sha, file, folder, retryCount])

  const truncatedMessage =
    commitMessage.length > 80
      ? commitMessage.slice(0, 80) + '…'
      : commitMessage

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="sticky top-0 border-b py-2 px-4 flex items-center gap-2 bg-background shrink-0">
        <button
          onClick={onBack}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← History
        </button>
        <span className="text-muted-foreground select-none">|</span>
        <span className="text-sm font-medium truncate">{truncatedMessage}</span>
      </div>

      {/* Content area */}
      <div className="flex-1 relative overflow-hidden">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="animate-spin border-4 border-primary/20 border-t-primary rounded-full w-8 h-8" />
          </div>
        )}

        {!loading && isFirstCommit && (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <p className="text-sm text-muted-foreground text-center">
              This is the first saved version — no previous version to compare.
            </p>
          </div>
        )}

        {!loading && error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6">
            <p className="text-sm text-muted-foreground text-center">{error}</p>
            <button
              onClick={() => setRetryCount((c) => c + 1)}
              className="text-sm text-primary hover:underline"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && iframeSrc && (
          <iframe
            src={iframeSrc}
            className="w-full h-full border-0"
            title="Diff report"
            onLoad={(e) => {
              // vis.js initialises the network graph inline during HTML parsing,
              // before the iframe has been laid out, so the canvas gets zero
              // dimensions. Dispatching a resize event after load triggers vis.js's
              // built-in _onResize handler which calls setSize() + _requestRedraw
              // with the now-correct container dimensions.
              try {
                const win = (e.currentTarget as HTMLIFrameElement).contentWindow
                win?.dispatchEvent(new Event('resize'))
              } catch {
                // Cross-origin blob URLs are same-origin — this should not throw
              }
            }}
          />
        )}
      </div>
    </div>
  )
}
