/**
 * Short messages at the bottom of the screen ("Course saved"), some with an
 * Undo button. A plain store rather than a React context, so any page or
 * helper can raise one without being wrapped in a provider.
 */

export interface Toast {
  id: number;
  text: string;
  kind: "success" | "error" | "info";
  action?: { label: string; onClick: () => void };
  /** Milliseconds on screen. */
  duration: number;
}

type Listener = (toasts: Toast[]) => void;

let toasts: Toast[] = [];
let nextId = 1;
const listeners = new Set<Listener>();

function emit() {
  for (const listener of listeners) listener(toasts);
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  listener(toasts);
  return () => {
    listeners.delete(listener);
  };
}

export function dismiss(id: number) {
  toasts = toasts.filter((toast) => toast.id !== id);
  emit();
}

export function toast(text: string, options: Partial<Omit<Toast, "id" | "text">> = {}): number {
  const id = nextId++;
  const entry: Toast = { id, text, kind: options.kind ?? "success", action: options.action, duration: options.duration ?? 3500 };
  // At most three at once; the oldest goes first.
  toasts = [...toasts.slice(-2), entry];
  emit();
  setTimeout(() => dismiss(id), entry.duration);
  return id;
}

const UNDO_MS = 5000;

/**
 * Remove something with a few seconds to change your mind. `hide` takes it
 * off the screen straight away; `commit` really deletes it once the Undo
 * button has gone; `restore` puts it back if Undo is pressed.
 */
export function undoable({
  text,
  hide,
  commit,
  restore,
}: {
  text: string;
  hide: () => void;
  commit: () => Promise<unknown>;
  restore: () => void;
}) {
  let undone = false;
  hide();
  const id = toast(text, {
    kind: "info",
    duration: UNDO_MS,
    action: {
      label: "Undo",
      onClick: () => {
        undone = true;
        dismiss(id);
        restore();
      },
    },
  });
  setTimeout(() => {
    if (undone) return;
    commit().catch(() => {
      restore();
      toast("That could not be removed. Please try again.", { kind: "error" });
    });
  }, UNDO_MS);
}
