import { useSearchParams } from 'react-router-dom';

interface Tab {
  key: string;
  label: string;
}

interface TabStripProps {
  tabs: Tab[];
  defaultKey: string;
  paramName?: string;
}

export default function TabStrip({ tabs, defaultKey, paramName = 'tab' }: TabStripProps) {
  const [params, setParams] = useSearchParams();
  const active = params.get(paramName) ?? defaultKey;

  return (
    <div className="border-b border-slate-200 flex gap-6">
      {tabs.map((tab) => {
        const isActive = tab.key === active;
        const className = isActive
          ? 'pb-3 -mb-px border-b-2 border-indigo-600 text-slate-900 text-sm font-medium'
          : 'pb-3 -mb-px border-b-2 border-transparent text-slate-500 hover:text-slate-900 text-sm font-medium';
        return (
          <button
            key={tab.key}
            type="button"
            className={className}
            onClick={() => {
              const next = new URLSearchParams(params);
              next.set(paramName, tab.key);
              setParams(next, { replace: false });
            }}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
