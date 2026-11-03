import { Route, Routes } from 'react-router-dom'
import { CharacterDetail, ComicDetail, Landing, RosterPage, Search, Shelves } from './pages'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/shelves" element={<Shelves />} />
      <Route path="/comics/:id" element={<ComicDetail />} />
      <Route path="/characters/:id" element={<CharacterDetail />} />
      <Route path="/roster" element={<RosterPage />} />
      <Route path="/search" element={<Search />} />
    </Routes>
  )
}
