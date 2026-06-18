import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import UserAvatar, { initials, coastalGradientIndex } from '@/components/ui/UserAvatar';

describe('UserAvatar helpers', () => {
  it('initials: first two alphanumerics, uppercased', () => {
    expect(initials('micah')).toBe('MI');
    expect(initials('a')).toBe('A');
    expect(initials('sierra_walker')).toBe('SI');
    expect(initials('')).toBe('?');
  });
  it('coastalGradientIndex is deterministic and in range', () => {
    const a = coastalGradientIndex('micah');
    const b = coastalGradientIndex('micah');
    expect(a).toBe(b);
    expect(a).toBeGreaterThanOrEqual(0);
    expect(a).toBeLessThan(5);
  });
});

describe('UserAvatar render', () => {
  it('renders the initials fallback for a username', () => {
    render(<UserAvatar username="micah" />);
    expect(screen.getByText('MI')).toBeInTheDocument();
  });
});
