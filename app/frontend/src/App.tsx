import { useEffect } from 'react'
import { useProjectStore } from '@/store/useProjectStore'
import WelcomeScreen from '@/components/WelcomeScreen'
import AppShell from '@/components/AppShell'
import './index.css'

export default function App() {
  const { projects, isLoading, setProjects } = useProjectStore()

  useEffect(() => {
    fetch('/api/projects')
      .then((r) => r.json())
      .then((data) => setProjects(data))
      .catch(() => setProjects([]))  // on error, treat as empty → show welcome screen
  }, [])

  if (isLoading) return null  // prevents welcome screen flash on reload
  if (projects.length === 0) return <WelcomeScreen onAddFolder={() => {/* TODO Plan 04 */}} />
  return <AppShell onAddFolder={() => {/* TODO Plan 04 */}} />
}
