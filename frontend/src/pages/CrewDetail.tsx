import { useParams } from 'react-router-dom';

export default function CrewDetail() {
  const { id } = useParams<{ id: string }>();
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">Crew {id}</h1>
      <p className="text-sm text-gray-500">
        /crews/:id — shell + leaderboard tab owned by Micah; feed tab by Teammate A;
        chat tab by Teammate B
      </p>
    </main>
  );
}
