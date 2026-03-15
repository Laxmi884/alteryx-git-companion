import { useState, useEffect, useCallback } from 'react'
import { useProjectStore } from '@/store/useProjectStore'
import Sidebar from '@/components/Sidebar'
import EmptyState from '@/components/EmptyState'
import { GitIdentityCard } from '@/components/GitIdentityCard'
import { ChangesPanel } from '@/components/ChangesPanel'
import { HistoryPanel, type CommitEntry } from '@/components/HistoryPanel'
import { DiffViewer } from '@/components/DiffViewer'

interface AppShellProps {
  onAddFolder?: () => void
  showIdentityCard?: boolean
  onIdentitySaved?: () => void
}

export default function AppShell({ onAddFolder, showIdentityCard, onIdentitySaved }: AppShellProps) {
  const { projects, activeProjectId } = useProjectStore()
  const activeProject = projects.find((p) => p.id === activeProjectId)

  // Watch status state — fetched on project activation and after undo
  const [hasCommits, setHasCommits] = useState(false)
  const [changedFiles, setChangedFiles] = useState<string[]>([])
  const [totalWorkflows, setTotalWorkflows] = useState(0)
  const [history, setHistory] = useState<CommitEntry[]>([])
  const [selectedDiff, setSelectedDiff] = useState<{ sha: string; file: string } | null>(null)

  const fetchWatchStatus = useCallback(async (): Promise<string[]> => {
    if (!activeProject) return []
    try {
      const res = await fetch(
        `/api/watch/status?project_id=${activeProject.id}&folder=${encodeURIComponent(activeProject.path)}`
      )
      if (!res.ok) return []
      const data = await res.json()
      const files: string[] = data.changed_files ?? []
      setHasCommits(data.has_any_commits ?? false)
      setChangedFiles(files)
      setTotalWorkflows(data.total_workflows ?? 0)
      return files
    } catch {
      return []
    }
  }, [activeProject])

  const fetchHistory = useCallback(async () => {
    if (!activeProject) return
    try {
      const res = await fetch(
        `/api/history/${activeProject.id}?folder=${encodeURIComponent(activeProject.path)}`
      )
      if (!res.ok) return
      const data: CommitEntry[] = await res.json()
      setHistory(data ?? [])
      setHasCommits((data ?? []).length > 0)
    } catch { /* ignore */ }
  }, [activeProject])

  // Fetch on project change
  useEffect(() => {
    setChangedFiles([])
    setHasCommits(false)
    setHistory([])
    setSelectedDiff(null)
    fetchWatchStatus()
    fetchHistory()
  }, [activeProjectId, fetchWatchStatus, fetchHistory])

  async function handleSaved() {
    await fetchWatchStatus()
    await fetchHistory()
  }

  async function handleDiscarded() {
    await fetchWatchStatus()
  }

  async function handleUndo(undoHasAnyCommits: boolean) {
    setHasCommits(undoHasAnyCommits)
    await fetchWatchStatus()
    await fetchHistory()
  }

  function renderMainContent() {
    if (showIdentityCard && onIdentitySaved) {
      return (
        <div className="flex h-full items-center justify-center">
          <GitIdentityCard onSaved={onIdentitySaved} />
        </div>
      )
    }
    if (!activeProjectId || !activeProject) {
      return (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          Select a project from the left panel
        </div>
      )
    }
    // State machine: changedFiles > 0 → ChangesPanel; hasCommits + selectedDiff → DiffViewer; hasCommits → HistoryPanel; else → EmptyState
    if (changedFiles.length > 0) {
      return (
        <ChangesPanel
          projectId={activeProject.id}
          projectPath={activeProject.path}
          changedFiles={changedFiles}
          hasAnyCommits={hasCommits}
          onSaved={handleSaved}
          onDiscarded={handleDiscarded}
        />
      )
    }
    if (hasCommits && selectedDiff) {
      return (
        <DiffViewer
          sha={selectedDiff.sha}
          file={selectedDiff.file}
          folder={activeProject.path}
          commitMessage={history.find(e => e.sha === selectedDiff.sha)?.message ?? ''}
          onBack={() => setSelectedDiff(null)}
        />
      )
    }
    if (hasCommits) {
      return (
        <HistoryPanel
          entries={history}
          projectId={activeProject.id}
          projectPath={activeProject.path}
          onSelectEntry={(entry, file) => setSelectedDiff({ sha: entry.sha, file })}
          onUndo={handleUndo}
        />
      )
    }
    return <EmptyState projectName={activeProject.name} />
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-[220px] flex-shrink-0 border-r bg-muted/40 flex flex-col p-2">
        <Sidebar onAddFolder={onAddFolder} />
      </aside>
      <main className="flex-1 overflow-auto p-6">
        {renderMainContent()}
      </main>
    </div>
  )
}
