import { afterEach, describe, expect, it } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useCurrentUser } from '@/hooks/useCurrentUser';

const KEY = 'synzoia.currentUser';

afterEach(() => {
  window.localStorage.clear();
});

describe('useCurrentUser', () => {
  it('returns null when nothing is stored', () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.currentUser).toBeNull();
  });

  it('reads an existing stored value on mount', () => {
    window.localStorage.setItem(KEY, 'alice');
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.currentUser).toBe('alice');
  });

  it('setCurrentUser persists and updates the value', () => {
    const { result } = renderHook(() => useCurrentUser());
    act(() => result.current.setCurrentUser('bob'));
    expect(result.current.currentUser).toBe('bob');
    expect(window.localStorage.getItem(KEY)).toBe('bob');
  });

  it('clearCurrentUser resets to null and removes the key', () => {
    window.localStorage.setItem(KEY, 'alice');
    const { result } = renderHook(() => useCurrentUser());
    act(() => result.current.clearCurrentUser());
    expect(result.current.currentUser).toBeNull();
    expect(window.localStorage.getItem(KEY)).toBeNull();
  });

  it('syncs a second hook instance via the custom event', () => {
    const a = renderHook(() => useCurrentUser());
    const b = renderHook(() => useCurrentUser());
    act(() => a.result.current.setCurrentUser('carol'));
    expect(b.result.current.currentUser).toBe('carol');
  });
});
