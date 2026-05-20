import { useEffect, useState } from 'react';

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'synzoia.theme';

function readStored(): Theme | null {
  if (typeof window === 'undefined') return null;
  try {
    const v = window.localStorage?.getItem?.(STORAGE_KEY);
    return v === 'light' || v === 'dark' ? v : null;
  } catch {
    return null;
  }
}

function writeStored(theme: Theme) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage?.setItem?.(STORAGE_KEY, theme);
  } catch {
    /* swallow — feature-detect, don't throw */
  }
}

function clearStored() {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage?.removeItem?.(STORAGE_KEY);
  } catch {
    /* swallow */
  }
}

function readOsPreference(): Theme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

function readCurrentClass(): Theme {
  if (typeof document === 'undefined') return 'light';
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

function applyTheme(theme: Theme) {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

/**
 * Theme state, persisted to localStorage. Default = OS preference.
 * The `.dark` class on <html> is set synchronously in index.html before
 * React mounts, so this hook's job is just to track + update.
 */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Trust the class the inline script already set (avoids flash + drift)
    return readCurrentClass();
  });

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // If the user is on "follow OS" mode (no stored value) and the OS changes,
  // mirror it. Once they pick explicitly, this side-effect no-ops.
  useEffect(() => {
    if (readStored() !== null) return;
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    function onChange(e: MediaQueryListEvent) {
      if (readStored() === null) {
        setThemeState(e.matches ? 'dark' : 'light');
      }
    }
    mq.addEventListener?.('change', onChange);
    return () => mq.removeEventListener?.('change', onChange);
  }, []);

  function setTheme(next: Theme) {
    writeStored(next);
    setThemeState(next);
  }

  function toggle() {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  }

  function resetToSystem() {
    clearStored();
    setThemeState(readOsPreference());
  }

  return { theme, setTheme, toggle, resetToSystem };
}
