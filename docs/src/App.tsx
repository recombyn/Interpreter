import { Navigate, Route, Routes } from 'react-router-dom'
import { DocsLayout } from '@/layouts/DocsLayout'
import { DocPage } from '@/pages/DocPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/guide/getting-started" replace />} />

      <Route element={<DocsLayout />}>
        <Route path="/guide/:slug" element={<DocPage />} />
        <Route path="/rules/:slug" element={<DocPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/guide/getting-started" replace />} />
    </Routes>
  )
}
