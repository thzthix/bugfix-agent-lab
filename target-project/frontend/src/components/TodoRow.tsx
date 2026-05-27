type TodoRowProps = {
  id: string;
  title: string;
  completed: boolean;
  isFavorite: boolean;
  onToggle: (id: string) => void;
  onFavorite: (id: string) => void;
};

export function TodoRow({
  id,
  title,
  completed,
  isFavorite,
  onToggle,
  onFavorite,
}: TodoRowProps) {
  return (
    <article className="todo-row">
      <button
        aria-label={completed ? "Mark task as incomplete" : "Mark task as complete"}
        className={`toggle-button${completed ? " is-completed" : ""}`}
        onClick={() => onToggle(id)}
        type="button"
      >
        {completed ? "✓" : ""}
      </button>

      <span className={`todo-title${completed ? " is-completed" : ""}`}>{title}</span>

      <button
        aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
        className={`favorite-button${isFavorite ? " is-favorite" : ""}`}
        onClick={() => onFavorite(id)}
        type="button"
      >
        {isFavorite ? "★" : "☆"}
      </button>
    </article>
  );
}
