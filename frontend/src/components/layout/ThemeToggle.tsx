import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';

type Props = {
  className?: string;
};

export default function ThemeToggle({ className = '' }: Props) {
  const { theme, toggle } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      onClick={toggle}
      className={`text-muted-foreground hover:text-foreground transition-colors p-2 -m-2 ${className}`}
    >
      {isDark ? <Sun size={16} strokeWidth={1.75} /> : <Moon size={16} strokeWidth={1.75} />}
    </button>
  );
}
