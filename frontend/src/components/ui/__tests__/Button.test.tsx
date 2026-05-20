import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Button from '@/components/ui/AppButton';

describe('Button', () => {
  it('renders a <button> by default', () => {
    render(<Button variant="primary">Click</Button>);
    expect(screen.getByRole('button', { name: 'Click' })).toBeInTheDocument();
  });

  it('renders secondary variant as a button', () => {
    render(<Button variant="secondary">Cancel</Button>);
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
  });

  it('renders ghost variant as a button', () => {
    render(<Button variant="ghost">Skip</Button>);
    expect(screen.getByRole('button', { name: 'Skip' })).toBeInTheDocument();
  });

  it('applies disabled attribute when disabled prop is true', () => {
    render(<Button variant="primary" disabled>Send</Button>);
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
  });

  it('fires onClick when clicked', () => {
    const handler = vi.fn();
    render(<Button variant="primary" onClick={handler}>Click me</Button>);
    fireEvent.click(screen.getByRole('button', { name: 'Click me' }));
    expect(handler).toHaveBeenCalledOnce();
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
    expect(link?.textContent).toBe('Go');
  });

  it('does not render an <a> when disabled with `to` prop', () => {
    const { container } = render(
      <MemoryRouter>
        <Button variant="primary" to="/somewhere" disabled>Go</Button>
      </MemoryRouter>,
    );
    expect(container.querySelector('a')).toBeNull();
    expect(screen.getByRole('button', { name: 'Go' })).toBeDisabled();
  });
});
