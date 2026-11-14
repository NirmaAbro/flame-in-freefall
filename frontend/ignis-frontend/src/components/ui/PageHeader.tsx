export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-3xl text-space-100">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm text-space-300">{description}</p>}
      </div>
      {actions}
    </header>
  );
}
