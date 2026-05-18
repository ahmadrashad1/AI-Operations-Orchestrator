type ModuleCardProps = {
  title: string;
  summary: string;
  tags: string[];
};

export function ModuleCard({ title, summary, tags }: ModuleCardProps) {
  return (
    <article className="module-card">
      <h3>{title}</h3>
      <p>{summary}</p>
      <div className="badge-row">
        {tags.map((tag) => (
          <span className="badge" key={tag}>
            {tag}
          </span>
        ))}
      </div>
    </article>
  );
}

