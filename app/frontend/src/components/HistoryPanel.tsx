import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Cloud } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface CommitEntry {
  sha: string
  message: string
  author: string
  timestamp: string        // ISO-8601 string
  files_changed: string[]  // workflow file basenames
  has_parent: boolean
  is_pushed: boolean
}

interface RemoteStatus {
  ahead: number
  behind: number
  github_connected: boolean
  gitlab_connected: boolean
  repo_url: string | null
}

interface HistoryPanelProps {
  entries: CommitEntry[]
  projectId: string
  projectPath: string
  onSelectEntry: (entry: CommitEntry, file: string) => void
  onUndo: () => void
  lastPushTimestamp?: number
  onNavigate?: (view: 'remote') => void
  onPushComplete?: () => void
}

function formatRelativeTime(isoTimestamp: string): string {
  const diffMs = Date.now() - new Date(isoTimestamp).getTime()
  const diffSec = Math.floor(diffMs / 1000)
  if (diffSec < 60) return 'just now'
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin} min ago`
  const diffHours = Math.floor(diffMin / 60)
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
  return new Date(isoTimestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function buildTooltip(remoteStatus: RemoteStatus | null): string {
  if (!remoteStatus) return 'Backed up'
  const remotes: string[] = []
  if (remoteStatus.github_connected) remotes.push('GitHub')
  if (remoteStatus.gitlab_connected) remotes.push('GitLab')
  if (remotes.length === 0) return 'Backed up'
  return `Backed up to ${remotes.join(' · ')}`
}

function EntryRow({
  entry,
  isLatest,
  onSelectEntry,
  remoteConnected,
  remoteStatus,
}: {
  entry: CommitEntry
  isLatest: boolean
  onSelectEntry: (entry: CommitEntry, file: string) => void
  remoteConnected: boolean
  remoteStatus: RemoteStatus | null
}) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const fileCount = entry.files_changed.length

  function handleRowClick() {
    if (fileCount === 0) {
      onSelectEntry(entry, '')
    } else if (fileCount === 1) {
      onSelectEntry(entry, entry.files_changed[0])
    }
    // For multiple files: selection is handled by inline file selector
  }

  function handleTabClick(file: string, e: React.MouseEvent) {
    e.stopPropagation()
    setSelectedFile(file)
    onSelectEntry(entry, file)
  }

  function handleSelectChange(e: React.ChangeEvent<HTMLSelectElement>) {
    e.stopPropagation()
    const file = e.target.value
    setSelectedFile(file)
    onSelectEntry(entry, file)
  }

  const truncatedMessage =
    entry.message.length > 60
      ? entry.message.slice(0, 60) + '…'
      : entry.message

  return (
    <div
      className={cn(
        'rounded-md px-3 py-2 cursor-pointer hover:bg-muted/60 transition-colors',
        fileCount <= 1 ? '' : 'cursor-default'
      )}
      onClick={fileCount <= 1 ? handleRowClick : undefined}
      role={fileCount <= 1 ? 'button' : undefined}
      tabIndex={fileCount <= 1 ? 0 : undefined}
      onKeyDown={
        fileCount <= 1
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') handleRowClick()
            }
          : undefined
      }
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{truncatedMessage}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {entry.author} · {formatRelativeTime(entry.timestamp)}
          </p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
          {remoteConnected && entry.is_pushed && (
            <span
              title={buildTooltip(remoteStatus)}
              aria-label="Backed up to remote"
            >
              <Cloud className="h-3.5 w-3.5 text-blue-500" />
            </span>
          )}
          {isLatest && (
            <Badge variant="secondary">
              Latest
            </Badge>
          )}
        </div>
      </div>

      {/* Inline file selector for 2-4 files */}
      {fileCount >= 2 && fileCount <= 4 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {entry.files_changed.map((file) => (
            <button
              key={file}
              onClick={(e) => handleTabClick(file, e)}
              className={cn(
                'text-xs px-2 py-1 rounded-md border transition-colors',
                selectedFile === file
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background hover:bg-muted border-input'
              )}
            >
              {file}
            </button>
          ))}
        </div>
      )}

      {/* Native select for 5+ files */}
      {fileCount >= 5 && (
        <div className="mt-2" onClick={(e) => e.stopPropagation()}>
          <select
            value={selectedFile ?? ''}
            onChange={handleSelectChange}
            className="w-full text-xs rounded-md border border-input bg-background px-2 py-1.5 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="" disabled>
              Select a file…
            </option>
            {entry.files_changed.map((file) => (
              <option key={file} value={file}>
                {file}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}

export function HistoryPanel({
  entries,
  projectId,
  projectPath,
  onSelectEntry,
  onUndo,
  lastPushTimestamp,
  onNavigate,
  onPushComplete,
}: HistoryPanelProps) {
  const [remoteStatus, setRemoteStatus] = useState<RemoteStatus | null>(null)
  const [pushState, setPushState] = useState<'idle' | 'pushing' | 'error'>('idle')
  const [pushError, setPushError] = useState<string | null>(null)

  async function fetchRemoteStatus() {
    if (!projectId || !projectPath) return
    try {
      const res = await fetch(
        `/api/remote/status?project_id=${encodeURIComponent(projectId)}&folder=${encodeURIComponent(projectPath)}`
      )
      if (!res.ok) return
      setRemoteStatus(await res.json())
    } catch { /* ignore */ }
  }

  useEffect(() => { fetchRemoteStatus() }, [projectId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!lastPushTimestamp) return
    fetchRemoteStatus()
  }, [lastPushTimestamp]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handlePush() {
    if (!projectId || !projectPath || !remoteStatus) return
    // If not connected: navigate to remote panel
    if (!remoteStatus.github_connected && !remoteStatus.gitlab_connected) {
      onNavigate?.('remote')
      return
    }
    setPushState('pushing')
    setPushError(null)
    const providers: Array<'github' | 'gitlab'> = []
    if (remoteStatus.github_connected) providers.push('github')
    if (remoteStatus.gitlab_connected) providers.push('gitlab')
    try {
      await Promise.all(
        providers.map((provider) =>
          fetch('/api/remote/push', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: projectId, folder: projectPath, provider }),
          }).then((res) => res.json()).then((data) => {
            if (!data.success) throw new Error(data.error ?? 'push failed')
          })
        )
      )
      setPushState('idle')
      // Re-fetch to update is_pushed flags and ahead count
      await fetchRemoteStatus()
      // Signal parent to re-fetch history entries with updated is_pushed
      onPushComplete?.()
    } catch {
      setPushState('error')
      setPushError('Backup failed. Check your connection and try again.')
      setTimeout(() => { setPushState('idle'); setPushError(null) }, 4000)
    }
  }

  const remoteConnected = !!(remoteStatus?.github_connected || remoteStatus?.gitlab_connected)
  const aheadCount = remoteStatus?.ahead ?? 0

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
        <h2 className="text-sm font-semibold">Saved Versions</h2>
        <div className="flex items-center gap-2">
          {remoteConnected && aheadCount > 0 && (
            <Button
              variant="default"
              size="sm"
              onClick={handlePush}
              disabled={pushState === 'pushing'}
              className="shrink-0"
            >
              {pushState === 'pushing' ? 'Backing up...' : `↑ Back up ${aheadCount} version${aheadCount !== 1 ? 's' : ''}`}
            </Button>
          )}
          {entries.length > 0 && (
            <Button variant="outline" size="sm" onClick={onUndo}>
              Undo last save
            </Button>
          )}
        </div>
      </div>

      {pushError && (
        <p className="text-xs text-red-500 px-4 pb-1">{pushError}</p>
      )}

      {/* Scrollable entry list */}
      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-0.5">
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No saved versions yet.
          </p>
        ) : (
          entries.map((entry, index) => (
            <EntryRow
              key={entry.sha}
              entry={entry}
              isLatest={index === 0}
              onSelectEntry={onSelectEntry}
              remoteConnected={remoteConnected}
              remoteStatus={remoteStatus}
            />
          ))
        )}
      </div>
    </div>
  )
}
