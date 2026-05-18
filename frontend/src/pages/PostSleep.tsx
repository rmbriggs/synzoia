import { useParams } from 'react-router-dom';

export default function PostSleep() {
  const { id } = useParams<{ id: string }>();
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">Post sleep for crew {id}</h1>
      <p className="text-sm text-gray-500">/crews/:id/post — owned by Teammate A</p>
    </main>
  );
}
