import { useState, useEffect, useCallback } from 'react'
import { useProjectStore, type LastSave } from '@/store/useProjectStore'
import Sidebar from '@/components/Sidebar'
import EmptyState from '@/components/EmptyState'
import { GitIdentityCard } from '@/components/GitIdentityCard'
import { ChangesPanel } from '@/components/ChangesPanel'
import { SuccessCard } from '@/components/SuccessCard'

interface AppShellProps {
  onAddFolder?: () => void
  showIdentityCard?: boolean
  onIdentitySaved?: () => void
}

export default function AppShell({ onAddFolder, showIdentityCard, onIdentitySaved }: AppShellProps) {
  const { projects, activeProjectId, lastSave, setLastSave } = useProjectStore()
  const activeProject = projects.find((p) => p.id === activeProjectId)

  // Watch status state — fetched on project activation and after undo
  const [hasCommits, setHasCommits] = useState(false)
  const [changedFiles, setChangedFiles] = useState<string[]>([])
  const [totalWorkflows, setTotalWorkflows] = useState(0)

  const fetchWatchStatus = useCallback(async () => {
    if (!activeProject) return
    try {
      const res = await fetch(
        `/api/watch/status?project_id=${activeProject.id}&folder=${encodeURIComponent(activeProject.path)}`
      )
      if (!res.ok) return
      const data = await res.json()
      setHasCommits(data.has_any_commits ?? false)
      setChangedFiles(data.changed_files ?? [])
      setTotalWorkflows(data.total_workflows ?? 0)
    } catch {
      // Network error — keep existing state
    }
  }, [activeProject])

  // Fetch on project change
  useEffect(() => {
    setLastSave(null)  // clear last save when switching projects
    setChangedFiles([])
    setHasCommits(false)
    fetchWatchStatus()
  }, [activeProjectId, fetchWatchStatus, setLastSave])

  function handleSaved(save: LastSave) {
    setLastSave(save)
    // Badge clears automatically via SSE (watcher_manager.clear_count called in router)
  }

  function handleDiscarded() {
    // Badge clears via SSE — changedFiles will update when watcher rescans
    // Fetch status immediately to get updated state
    fetchWatchStatus()
  }

  function handleUndo(undoHasAnyCommits: boolean) {
    setLastSave(null)
    setHasCommits(undoHasAnyCommits)
    // Watcher will rescan and push badge_update — changedFiles will update via SSE
    fetchWatchStatus()
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
    // State machine: changedCount > 0 → ChangesPanel; lastSave → SuccessCard; else → EmptyState
    if ((activeProject.changedCount ?? 0) > 0) {
      return (
        <ChangesPanel
          projectId={activeProject.id}
          projectPath={activeProject.path}
          changedFiles={changedFiles}
          hasAnyCommits={hasCommits}
          totalWorkflows={totalWorkflows}
          onSaved={handleSaved}
          onDiscarded={handleDiscarded}
        />
      )
    }
    if (lastSave) {
      return (
        <SuccessCard
          lastSave={lastSave}
          projectId={activeProject.id}
          projectPath={activeProject.path}
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
