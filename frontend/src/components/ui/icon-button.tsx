import * as React from "react";

import { Button, type ButtonProps } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface IconButtonProps extends Omit<ButtonProps, "children"> {
  label: string;
  children: React.ReactNode;
  tooltipSide?: "top" | "right" | "bottom" | "left";
}

export const IconButton = React.forwardRef<
  HTMLButtonElement,
  IconButtonProps
>(
  (
    { label, children, tooltipSide = "top", variant = "ghost", size = "icon", ...props },
    ref,
  ) => (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            ref={ref}
            variant={variant}
            size={size}
            aria-label={label}
            {...props}
          >
            {children}
          </Button>
        </TooltipTrigger>
        <TooltipContent side={tooltipSide}>{label}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  ),
);
IconButton.displayName = "IconButton";
