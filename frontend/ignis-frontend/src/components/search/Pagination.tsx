interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  if (pageCount === 1) return null;

  return (
    <nav aria-label="Pagination" className="mt-6 flex items-center justify-between text-sm">
      <button className="btn-secondary" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button>
      <span className="text-space-300">Page {page} of {pageCount}</span>
      <button className="btn-secondary" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>Next</button>
    </nav>
  );
}
