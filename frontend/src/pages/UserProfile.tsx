import { useParams } from 'react-router-dom';

export default function UserProfile() {
  const { id } = useParams<{ id: string }>();
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">User {id}</h1>
      <p className="text-sm text-gray-500">/users/:id — owned by Teammate A</p>
    </main>
  );
}
