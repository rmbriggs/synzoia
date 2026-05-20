import { useSearchParams } from 'react-router-dom';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

type Tab = { key: string; label: string };

type Props = {
  tabs: Tab[];
  paramName?: string;
  defaultKey?: string;
};

export function TabStrip({ tabs, paramName = 'tab', defaultKey }: Props) {
  const [params, setParams] = useSearchParams();
  const active = params.get(paramName) ?? defaultKey ?? tabs[0]?.key;

  function setActive(key: string) {
    const next = new URLSearchParams(params);
    next.set(paramName, key);
    setParams(next, { replace: true });
  }

  return (
    <Tabs value={active} onValueChange={setActive}>
      <TabsList>
        {tabs.map((t) => (
          <TabsTrigger key={t.key} value={t.key}>
            {t.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}

export default TabStrip;
