import type { InputHTMLAttributes } from 'react';

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
  error?: string;
}

export default function FormField({ id, label, error, className, ...inputProps }: FormFieldProps) {
  const baseInput = 'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed';
  const inputClass = className ? `${baseInput} ${className}` : baseInput;
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 mb-1">
        {label}
      </label>
      <input id={id} className={inputClass} {...inputProps} />
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  );
}
