import { useState, useRef, useEffect } from 'react'

// Source: useWatchEvents.ts (persistent) adapted for request-scoped SSE per D-08.
// Opens EventSource on trigger(), closes on result/unavailable/error/unmount.

export type AISummaryStatus =
  | 'idle'
  | 'loading'
  | 'result'
  | 'unavailable_no_extras'
  | 'unavailable_no_model'
  | 'error'

export interface UseAISummaryReturn {
  status: AISummaryStatus
  steps: string[]
  narrative: string | null
  risks: string[]
  errorDetail: string | null
  trigger: (folder: string, sha: string, file: string) => void
  reset: () => void
}

export function useAISummary(): UseAISummaryReturn {
  const [status, setStatus] = useState<AISummaryStatus>('idle')
  const [steps, setSteps] = useState<string[]>([])
  const [narrative, setNarrative] = useState<string | null>(null)
  const [risks, setRisks] = useState<string[]>([])
  const [errorDetail, setErrorDetail] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)

  // Cleanup on unmount to prevent leaked connections (RESEARCH Pitfall 4)
  useEffect(() => {
    return () => {
      esRef.current?.close()
      esRef.current = null
    }
  }, [])

  function trigger(folder: string, sha: string, file: string) {
    // Close any previous stream
    esRef.current?.close()
    esRef.current = null

    setStatus('loading')
    setSteps([])
    setNarrative(null)
    setRisks([])
    setErrorDetail(null)

    const url =
      `/api/ai/summary?folder=${encodeURIComponent(folder)}` +
      `&sha=${encodeURIComponent(sha)}` +
      `&file=${encodeURIComponent(file)}`

    const es = new EventSource(url)

    es.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data) as
          | { type: 'progress'; step: string }
          | { type: 'result'; narrative: string; risks?: string[] }
          | { type: 'unavailable'; reason: 'no_extras' | 'no_model' }
          | { type: 'error'; detail: string }

        if (payload.type === 'progress') {
          setSteps((prev) => [...prev, payload.step])
        } else if (payload.type === 'result') {
          setNarrative(payload.narrative)
          setRisks(payload.risks ?? [])
          setStatus('result')
          es.close()
          esRef.current = null
        } else if (payload.type === 'unavailable') {
          setStatus(
            payload.reason === 'no_extras'
              ? 'unavailable_no_extras'
              : 'unavailable_no_model',
          )
          es.close()
          esRef.current = null
        } else if (payload.type === 'error') {
          setErrorDetail(payload.detail)
          setStatus('error')
          es.close()
          esRef.current = null
        }
      } catch {
        // Ignore malformed events — do not crash the hook
      }
    }

    es.onerror = () => {
      setStatus('error')
      es.close()
      esRef.current = null
    }

    esRef.current = es
  }

  function reset() {
    esRef.current?.close()
    esRef.current = null
    setStatus('idle')
    setSteps([])
    setNarrative(null)
    setRisks([])
    setErrorDetail(null)
  }

  return { status, steps, narrative, risks, errorDetail, trigger, reset }
}
