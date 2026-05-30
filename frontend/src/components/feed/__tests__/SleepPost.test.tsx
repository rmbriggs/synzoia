import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SleepPost from '@/components/feed/SleepPost';
import type { FeedPost } from '@/api/posts';

const post: FeedPost = {
  id: 1,
  user_id: 1,
  username: 'alice',
  type: 'sleep',
  timestamp: '2026-05-28T12:32:00Z',
  details: { duration_min: 452, night_of: '2026-05-27' },
  body: 'slept 7h 32m',
};

describe('SleepPost', () => {
  it('renders the username and body', () => {
    render(
      <MemoryRouter>
        <SleepPost post={post} />
      </MemoryRouter>,
    );
    expect(screen.getByText('@alice')).toBeInTheDocument();
    expect(screen.getByText('slept 7h 32m')).toBeInTheDocument();
  });
});
