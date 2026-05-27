import { afterEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';

function renderLayout() {
  return render(
    <MemoryRouter initialEntries={['/feed']}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/feed" element={<div>feed body</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  window.localStorage.clear();
});

describe('AppLayout profile icon', () => {
  it('links to /users when no current user is set', () => {
    renderLayout();
    const links = screen.getAllByRole('link', { name: /your profile/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
    for (const link of links) {
      expect(link).toHaveAttribute('href', '/users');
    }
  });

  it('links to /u/<name> when a current user is set', () => {
    window.localStorage.setItem('synzoia.currentUser', 'alice');
    renderLayout();
    const links = screen.getAllByRole('link', { name: /your profile/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
    for (const link of links) {
      expect(link).toHaveAttribute('href', '/u/alice');
    }
  });
});
