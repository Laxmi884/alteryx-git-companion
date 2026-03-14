import { useProjectStore } from '@/store/useProjectStore'
import Sidebar from '@/components/Sidebar'
import EmptyState from '@/components/EmptyState'
import { GitIdentityCard } from '@/components/GitIdentityCard'

interface AppShellProps {
  onAddFolder?: () => void
  showIdentityCard?: boolean
  onIdentitySaved?: () => void
}

export default function AppShell({ onAddFolder, showIdentityCard, onIdentitySaved }: AppShellProps) {
  const { projects, activeProjectId } = useProjectStore()
  const activeProject = projects.find((p) => p.id === activeProjectId)

  function renderMainContent() {
    if (showIdentityCard && onIdentitySaved) {
      return (
        <div className="flex h-full items-center justify-center">
          <GitIdentityCard onSaved={onIdentitySaved} />
        </div>
      )
    }
    if (activeProjectId) {
      return <EmptyState projectName={activeProject?.name} />
    }
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Select a project from the left panel
      </div>
    )
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
