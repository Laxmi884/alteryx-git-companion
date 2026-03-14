import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export interface CommitEntry {
  sha: string
  message: string
  author: string
  timestamp: string        // ISO-8601 string
  files_changed: string[]  // workflow file basenames
  has_parent: boolean
}

interface HistoryPanelProps {
  entries: CommitEntry[]
  projectId: string
  projectPath: string
  onSelectEntry: (entry: CommitEntry, file: string) => void
  onUndo: () => void
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

function EntryRow({
  entry,
  isLatest,
  onSelectEntry,
}: {
  entry: CommitEntry
  isLatest: boolean
  onSelectEntry: (entry: CommitEntry, file: string) => void
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
        {isLatest && (
          <Badge variant="secondary" className="shrink-0 mt-0.5">
            Latest
          </Badge>
        )}
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
  projectId: _projectId,
  projectPath: _projectPath,
  onSelectEntry,
  onUndo,
}: HistoryPanelProps) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
        <h2 className="text-sm font-semibold">Saved Versions</h2>
        {entries.length > 0 && (
          <Button variant="outline" size="sm" onClick={onUndo}>
            Undo last save
          </Button>
        )}
      </div>

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
            />
          ))
        )}
      </div>
    </div>
  )
}
