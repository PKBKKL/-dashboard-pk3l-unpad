export function PageHeader({
  title,
  description,
  period,
}: {
  title: string;
  description?: string;
  period?: string;
}) {
  return (
    <header className="mb-8">
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-2xl font-semibold text-ink-900">{title}</h1>
        {period && (
          <span className="text-sm text-ink-400 bg-ink-100 rounded-full px-3 py-1">
            {period}
          </span>
        )}
      </div>
      {description && (
        <p className="mt-2 text-ink-600 leading-relaxed max-w-3xl">{description}</p>
      )}
    </header>
  );
}
