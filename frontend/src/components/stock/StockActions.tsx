import { FolderPlus, Star } from "lucide-react";
import { useEffect, useState } from "react";

import type { StockMeta } from "@/api/types";
import { AddToPortfolioWizard } from "@/components/portfolio/AddToPortfolioWizard";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { isFavorite, toggleFavorite } from "@/lib/favorites";

interface StockActionsProps {
  meta: StockMeta;
}

export function StockActions({ meta }: StockActionsProps) {
  const [fav, setFav] = useState(false);
  useEffect(() => {
    setFav(isFavorite(meta.symbol));
  }, [meta.symbol]);

  const [wizardOpen, setWizardOpen] = useState(false);

  return (
    <div
      className="relative flex items-center gap-2"
      data-testid="stock-actions"
    >
      <IconButton
        label={fav ? "取消收藏" : "加入收藏"}
        data-testid="favorite-toggle"
        aria-pressed={fav}
        onClick={() => {
          toggleFavorite(meta.symbol);
          setFav((v) => !v);
        }}
      >
        <Star
          className={
            fav ? "fill-amber-300 text-amber-300" : "text-slate-400"
          }
        />
      </IconButton>
      <Button
        variant="primary"
        size="sm"
        onClick={() => setWizardOpen(true)}
        data-testid="add-to-portfolio"
        aria-expanded={wizardOpen}
      >
        <FolderPlus />
        加入組合
      </Button>
      <AddToPortfolioWizard
        meta={meta}
        open={wizardOpen}
        onOpenChange={setWizardOpen}
      />
    </div>
  );
}
