import {
  useTutorialMode,
  type TutorialMode,
} from "@/contexts/TutorialModeContext";

const LABELS: Record<TutorialMode, { icon: string; text: string }> = {
  full: { icon: "📖", text: "完整教學" },
  compact: { icon: "📗", text: "精簡" },
  off: { icon: "📕", text: "關閉" },
};

export function TutorialModeToggle() {
  const { mode, cycle } = useTutorialMode();
  const { icon, text } = LABELS[mode];
  return (
    <button
      type="button"
      onClick={cycle}
      className="rounded border border-slate-700 bg-slate-900/60 px-2.5 py-1 text-xs text-slate-200 hover:bg-slate-800"
      title={`教學密度：${text}（點擊切換）`}
      aria-label={`切換教學密度，目前：${text}`}
      data-testid="tutorial-mode-toggle"
      data-mode={mode}
    >
      <span className="mr-1" aria-hidden>
        {icon}
      </span>
      {text}
    </button>
  );
}
