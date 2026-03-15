import { create } from 'zustand'

export interface Project {
  id: string
  path: string
  name: string
  changedCount?: number
}

interface ProjectStore {
  projects: Project[]
  activeProjectId: string | null
  isLoading: boolean
  setProjects: (projects: Project[]) => void
  setActiveProject: (id: string) => void
  addProject: (project: Project) => void
  removeProject: (id: string) => void
  setChangedCount: (id: string, count: number) => void
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  activeProjectId: null,
  isLoading: true,
  setProjects: (projects) => set({ projects, isLoading: false }),
  setActiveProject: (id) => set({ activeProjectId: id }),
  addProject: (project) => set((state) => ({ projects: [...state.projects, project] })),
  removeProject: (id) =>
    set((state) => ({
      projects: state.projects.filter((p) => p.id !== id),
      activeProjectId: state.activeProjectId === id ? null : state.activeProjectId,
    })),
  setChangedCount: (id, count) =>
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === id ? { ...p, changedCount: count } : p
      ),
    })),
}))
