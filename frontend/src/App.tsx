import { Route, Routes } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import Landing from '@/pages/Landing';
import Join from '@/pages/Join';
import StyleGuide from '@/pages/StyleGuide';
import DbExplorer from '@/pages/DbExplorer';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/join" element={<Join />} />
      <Route path="/style-guide" element={<StyleGuide />} />
      <Route element={<AppLayout />}>
        <Route path="/db" element={<DbExplorer />} />
      </Route>
    </Routes>
  );
}
