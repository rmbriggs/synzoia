import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Button from '@/components/ui/AppButton';

describe('Button', () => {
  it('renders a <button> by default with primary variant classes', () => {
    const { container } = render(<Button variant="primary">Click</Button>);
    const btn = container.querySelector('button');
    expect(btn).not.toBeNull();
    expect(btn?.className).toContain('bg-indigo-600');
    expect(btn?.textContent).toBe('Click');
  });

  it('renders secondary variant with border + white background', () => {
    const { container } = render(<Button variant="secondary">Cancel</Button>);
    const btn = container.querySelector('button');
    expect(btn?.className).toContain('border-slate-200');
    expect(btn?.className).toContain('bg-white');
  });

  it('renders ghost variant', () => {
    const { container } = render(<Button variant="ghost">Skip</Button>);
    const btn = container.querySelector('button');
    expect(btn?.className).toContain('text-slate-600');
  });

  it('applies disabled styling when disabled prop is true', () => {
    const { container } = render(
      <Button variant="primary" disabled>Send</Button>,
    );
    const btn = container.querySelector('button');
    expect(btn?.disabled).toBe(true);
    expect(btn?.className).toContain('opacity-50');
    expect(btn?.className).toContain('cursor-not-allowed');
  });

  it('renders a react-router Link when `to` prop is provided', () => {
    const { container } = render(
      <MemoryRouter>
        <Button variant="primary" to="/somewhere">Go</Button>
      </MemoryRouter>,
    );
    const link = container.querySelector('a');
    expect(link).not.toBeNull();
    expect(link?.getAttribute('href')).toBe('/somewhere');
    expect(link?.className).toContain('bg-indigo-600');
    expect(container.querySelector('button')).toBeNull();
  });
});
