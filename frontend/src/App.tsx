import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import Join from '@/pages/Join';
import Login from '@/pages/Login';
import StyleGuide from '@/pages/StyleGuide';
import DbExplorer from '@/pages/DbExplorer';
import Feed from '@/pages/Feed';
import Leaderboard from '@/pages/Leaderboard';
import Profile from '@/pages/Profile';
import Users from '@/pages/Users';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/feed" replace />} />
      <Route path="/join" element={<Join />} />
      <Route path="/login" element={<Login />} />
      <Route path="/style-guide" element={<StyleGuide />} />
      <Route element={<AppLayout />}>
        <Route path="/feed" element={<Feed />} />
        <Route path="/users" element={<Users />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/u/:username" element={<Profile />} />
        <Route path="/db" element={<DbExplorer />} />
      </Route>
    </Routes>
  );
}
