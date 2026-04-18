import { Button } from "@/components/ui/button";
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
    <Button
      variant="secondary"
      size="sm"
      onClick={cycle}
      title={`教學密度：${text}（點擊切換）`}
      aria-label={`切換教學密度，目前：${text}`}
      data-testid="tutorial-mode-toggle"
      data-mode={mode}
    >
      <span aria-hidden>{icon}</span>
      {text}
    </Button>
  );
}
