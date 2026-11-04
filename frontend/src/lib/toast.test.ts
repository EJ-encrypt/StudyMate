import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { subscribe, Toast, undoable } from "./toast";

describe("undoable", () => {
  let shown: Toast[] = [];
  let unsubscribe: () => void;

  beforeEach(() => {
    vi.useFakeTimers();
    unsubscribe = subscribe((toasts) => (shown = toasts));
  });
  afterEach(() => {
    unsubscribe();
    vi.useRealTimers();
  });

  it("deletes for real only after the Undo button has gone", async () => {
    const hide = vi.fn();
    const restore = vi.fn();
    const commit = vi.fn(() => Promise.resolve());
    undoable({ text: "Lecture removed.", hide, restore, commit });

    expect(hide).toHaveBeenCalled();
    expect(shown[shown.length - 1]?.action?.label).toBe("Undo");
    vi.advanceTimersByTime(4000);
    expect(commit).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1500);
    expect(commit).toHaveBeenCalledTimes(1);
    expect(restore).not.toHaveBeenCalled();
  });

  it("puts it back, and deletes nothing, when Undo is pressed", () => {
    const restore = vi.fn();
    const commit = vi.fn(() => Promise.resolve());
    undoable({ text: "Friend removed.", hide: vi.fn(), restore, commit });

    shown[shown.length - 1]!.action!.onClick();
    vi.advanceTimersByTime(10_000);
    expect(restore).toHaveBeenCalledTimes(1);
    expect(commit).not.toHaveBeenCalled();
  });
});
