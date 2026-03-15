import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Card, CardContent } from '@/components/ui/card'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useProjectStore } from '@/store/useProjectStore'

interface ChangesPanelProps {
  projectId: string
  projectPath: string
  changedFiles: string[]
  hasAnyCommits: boolean
  onSaved: () => Promise<void>
  onDiscarded: () => Promise<void>
  onBranchSwitch: () => void
}

export function ChangesPanel({
  projectId,
  projectPath,
  changedFiles,
  hasAnyCommits,
  onSaved,
  onDiscarded,
  onBranchSwitch,
}: ChangesPanelProps) {
  const [checkedFiles, setCheckedFiles] = useState<string[]>(changedFiles)
  const [commitMessage, setCommitMessage] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [confirmDiscard, setConfirmDiscard] = useState(false)

  const { activeBranch, setActiveBranch } = useProjectStore()
  const currentBranch = activeBranch[projectId] ?? 'main'
  const isExperiment = currentBranch.startsWith('experiment/')
  const [branches, setBranches] = useState<{ name: string; is_current: boolean }[]>([])
  const [popoverOpen, setPopoverOpen] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [newBranchDesc, setNewBranchDesc] = useState('')
  const [switchStatus, setSwitchStatus] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  // Keep checkedFiles in sync when the file list changes (e.g. after a partial commit)
  useEffect(() => {
    setCheckedFiles(changedFiles)
  }, [changedFiles])

  async function loadBranches() {
    const res = await fetch(`/api/branch/${projectId}?folder=${encodeURIComponent(projectPath)}`)
    if (res.ok) setBranches(await res.json())
  }

  function formatBranchName(description: string): string {
    const today = new Date().toISOString().slice(0, 10)
    const slug = description.toLowerCase().trim()
      .replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '').replace(/-+/g, '-')
    return `experiment/${today}-${slug}`
  }

  async function handleSwitch(branch: string) {
    const res = await fetch(`/api/branch/${projectId}/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: projectPath, branch }),
    })
    const data = await res.json()
    if (data.success) {
      setActiveBranch(projectId, branch)
      setPopoverOpen(false)
      setSwitchStatus(`Switched to ${branch}`)
      setTimeout(() => setSwitchStatus(null), 3000)
      onBranchSwitch()
    }
  }

  async function handleCreate() {
    if (!newBranchDesc.trim()) return
    setIsCreating(true)
    const res = await fetch(`/api/branch/${projectId}/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: projectPath, description: newBranchDesc }),
    })
    const data = await res.json()
    setIsCreating(false)
    if (data.success && data.branch_name) {
      setActiveBranch(projectId, data.branch_name)
      setPopoverOpen(false)
      setShowCreate(false)
      setNewBranchDesc('')
      setSwitchStatus(`Switched to ${data.branch_name}`)
      setTimeout(() => setSwitchStatus(null), 3000)
      onBranchSwitch()
    }
  }

  async function handleDelete(branch: string, force = false) {
    const res = await fetch(`/api/branch/${projectId}/delete`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: projectPath, branch, force }),
    })
    const data = await res.json()
    setDeleteTarget(null)
    if (data.success) {
      await loadBranches()
    } else {
      alert(data.error)
    }
  }

  function toggleFile(file: string, checked: boolean) {
    setCheckedFiles((prev) =>
      checked ? [...prev, file] : prev.filter((f) => f !== file)
    )
  }

  async function handleSave() {
    if (checkedFiles.length === 0 || isSaving) return
    setIsSaving(true)
    try {
      const res = await fetch('/api/save/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          folder: projectPath,
          files: checkedFiles,
          message: commitMessage,
        }),
      })
      if (res.ok) {
        await onSaved()
      }
    } finally {
      setIsSaving(false)
    }
  }

  async function handleDiscardConfirm() {
    try {
      await fetch('/api/save/discard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          folder: projectPath,
          files: checkedFiles,
        }),
      })
    } finally {
      setConfirmDiscard(false)
      onDiscarded()
    }
  }

  const displayFiles =
    !hasAnyCommits && changedFiles.length > 5
      ? changedFiles.slice(0, 5)
      : changedFiles

  const hiddenCount =
    !hasAnyCommits && changedFiles.length > 5 ? changedFiles.length - 5 : 0

  const textareaPlaceholder = hasAnyCommits
    ? 'What changed? e.g. Updated filter logic'
    : 'e.g. Initial version of project workflows'

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* Branch chip */}
      <div className="flex items-center justify-between mb-2">
        <Popover
          open={popoverOpen}
          onOpenChange={(open) => {
            setPopoverOpen(open)
            if (open) loadBranches()
          }}
        >
          <PopoverTrigger asChild>
            <button
              className={cn(
                'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono border cursor-pointer',
                isExperiment
                  ? 'bg-amber-100 text-amber-800 border-amber-300'
                  : 'bg-muted text-muted-foreground border-border'
              )}
            >
              &#x2387; {currentBranch.length > 22 ? currentBranch.slice(0, 20) + '\u2026' : currentBranch} &#x25BE;
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-72 p-2" align="start">
            {/* Dirty warning */}
            {changedFiles.length > 0 && (
              <p className="text-xs text-amber-700 mb-2">
                &#x26A0; Save changes before switching ({changedFiles.length} files)
              </p>
            )}
            {/* Branch list */}
            <div className="flex flex-col gap-1">
              {branches.map((b) => (
                <div key={b.name} className="flex items-center justify-between">
                  <button
                    disabled={changedFiles.length > 0 || b.is_current}
                    className={cn(
                      'flex-1 text-left text-sm px-2 py-1 rounded hover:bg-accent',
                      (changedFiles.length > 0 || b.is_current) && 'opacity-50 cursor-not-allowed'
                    )}
                    onClick={() => handleSwitch(b.name)}
                  >
                    {b.is_current && <span className="mr-1">&#x2713;</span>}
                    {b.name}
                  </button>
                  {b.name !== 'main' && b.name !== 'master' && !b.is_current && (
                    <button
                      className="p-1 text-muted-foreground hover:text-destructive"
                      onClick={() => setDeleteTarget(b.name)}
                      title="Delete experiment copy"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            {/* New experiment section */}
            {!showCreate ? (
              <button
                className="mt-2 w-full text-left text-sm text-muted-foreground hover:text-foreground px-2 py-1 rounded hover:bg-accent"
                onClick={() => setShowCreate(true)}
              >
                + New experiment
              </button>
            ) : (
              <div className="mt-2 flex flex-col gap-1">
                <input
                  autoFocus
                  className="w-full text-sm border rounded px-2 py-1"
                  placeholder="e.g. price-calc-test"
                  value={newBranchDesc}
                  onChange={(e) => setNewBranchDesc(e.target.value)}
                />
                {newBranchDesc && (
                  <p className="text-xs text-muted-foreground">
                    Will be: {formatBranchName(newBranchDesc)}
                  </p>
                )}
                <div className="flex gap-1">
                  <button
                    disabled={!newBranchDesc.trim() || isCreating}
                    className="flex-1 text-xs bg-primary text-primary-foreground rounded px-2 py-1 disabled:opacity-50"
                    onClick={handleCreate}
                  >
                    {isCreating ? 'Creating\u2026' : 'Create'}
                  </button>
                  <button
                    className="text-xs text-muted-foreground px-2 py-1"
                    onClick={() => {
                      setShowCreate(false)
                      setNewBranchDesc('')
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </PopoverContent>
        </Popover>
        {switchStatus && (
          <span className="text-xs text-muted-foreground italic">{switchStatus}</span>
        )}
      </div>

      {!hasAnyCommits && (
        <Card className="border-amber-400 bg-amber-50 dark:bg-amber-950">
          <CardContent className="pt-4">
            <p className="text-sm text-amber-800 dark:text-amber-200">
              <strong>First version save</strong> &mdash; This will save{' '}
              {checkedFiles.length} workflow{checkedFiles.length !== 1 ? 's' : ''} as your starting
              point.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-medium">Changed files</h3>
        <div className={cn('flex flex-col gap-1.5')}>
          {displayFiles.map((file) => {
            const basename = file.split('/').pop() ?? file
            return (
              <div key={file} className="flex items-center gap-2">
                <Checkbox
                  id={`file-${file}`}
                  checked={checkedFiles.includes(file)}
                  onCheckedChange={(checked) =>
                    toggleFile(file, checked === true)
                  }
                />
                <label
                  htmlFor={`file-${file}`}
                  className="text-sm cursor-pointer select-none"
                >
                  {basename}
                </label>
              </div>
            )
          })}
          {hiddenCount > 0 && (
            <p className="text-xs text-muted-foreground">
              ...and {hiddenCount} more
            </p>
          )}
        </div>
      </div>

      <Textarea
        placeholder={textareaPlaceholder}
        value={commitMessage}
        onChange={(e) => setCommitMessage(e.target.value)}
        rows={3}
        className="resize-none"
      />

      <div className="flex items-center gap-2">
        <Button
          onClick={handleSave}
          disabled={checkedFiles.length === 0 || isSaving}
          className="flex-1"
        >
          {isSaving ? 'Saving...' : 'Save Version'}
        </Button>
        <Button
          variant="outline"
          onClick={() => setConfirmDiscard(true)}
          disabled={checkedFiles.length === 0}
        >
          Discard
        </Button>
      </div>

      <AlertDialog
        open={confirmDiscard}
        onOpenChange={(open) => !open && setConfirmDiscard(false)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Discard changes?</AlertDialogTitle>
            <AlertDialogDescription>
              Discard changes to these {checkedFiles.length} workflow(s)? They&apos;ll
              be moved to .acd-backup &mdash; you can recover them from there.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setConfirmDiscard(false)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleDiscardConfirm}>
              Discard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete experiment copy?</AlertDialogTitle>
            <AlertDialogDescription>
              Deleting this experiment copy removes the branch. Files on main are not affected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteTarget && handleDelete(deleteTarget)}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
