import { Route, Routes } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import Home from '@/pages/Home';
import Auth from '@/pages/Auth';
import Crews from '@/pages/Crews';
import CrewDetail from '@/pages/CrewDetail';
import PostSleep from '@/pages/PostSleep';
import UserProfile from '@/pages/UserProfile';
import Settings from '@/pages/Settings';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/auth" element={<Auth />} />
      <Route element={<AppLayout />}>
        <Route path="/crews" element={<Crews />} />
        <Route path="/crews/:id" element={<CrewDetail />} />
        <Route path="/crews/:id/post" element={<PostSleep />} />
        <Route path="/users/:id" element={<UserProfile />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
