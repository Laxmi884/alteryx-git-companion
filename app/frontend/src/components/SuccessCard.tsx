import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import { type LastSave } from '@/store/useProjectStore'

interface SuccessCardProps {
  lastSave: LastSave
  projectId: string
  projectPath: string
  onUndo: (hasAnyCommits: boolean) => void
}

function computeRelativeTime(savedAt: Date): string {
  const diffMs = Date.now() - savedAt.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  if (diffSec < 60) return 'just now'
  const diffMin = Math.floor(diffSec / 60)
  return `${diffMin} min ago`
}

export function SuccessCard({
  lastSave,
  projectId,
  projectPath,
  onUndo,
}: SuccessCardProps) {
  const [confirmUndo, setConfirmUndo] = useState(false)
  const [isUndoing, setIsUndoing] = useState(false)
  const [relativeTime, setRelativeTime] = useState('just now')

  useEffect(() => {
    const interval = setInterval(() => {
      setRelativeTime(computeRelativeTime(lastSave.savedAt))
    }, 30000)
    return () => clearInterval(interval)
  }, [lastSave.savedAt])

  async function handleUndoConfirm() {
    setIsUndoing(true)
    try {
      const res = await fetch('/api/save/undo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          folder: projectPath,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        onUndo(data.has_any_commits)
      }
    } finally {
      setIsUndoing(false)
      setConfirmUndo(false)
    }
  }

  const fileSuffix = lastSave.fileCount === 1 ? 'file' : 'files'

  return (
    <>
      <Card className="w-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-base text-green-700 dark:text-green-400">
            Saved successfully
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {lastSave.message && lastSave.message !== 'Save' && (
            <p className="text-sm">{lastSave.message}</p>
          )}
          <p className="text-xs text-muted-foreground">
            {lastSave.fileCount} {fileSuffix} &bull; {relativeTime}
          </p>
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfirmUndo(true)}
              disabled={isUndoing}
            >
              {isUndoing ? 'Undoing...' : 'Undo last save'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <AlertDialog
        open={confirmUndo}
        onOpenChange={(open) => !open && setConfirmUndo(false)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Undo this save?</AlertDialogTitle>
            <AlertDialogDescription>
              Your workflow files won't change — only this saved version will be
              removed from the history.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setConfirmUndo(false)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleUndoConfirm}>
              Undo Save
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
