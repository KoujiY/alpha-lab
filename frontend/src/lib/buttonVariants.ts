import { cva } from "class-variance-authority";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 disabled:cursor-not-allowed disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-sky-500 text-slate-950 hover:bg-sky-400",
        primary:
          "border border-sky-500 bg-sky-500/10 text-sky-300 hover:bg-sky-500/20",
        secondary:
          "border border-slate-700 bg-slate-900/60 text-slate-200 hover:border-slate-500",
        ghost:
          "text-slate-300 hover:bg-slate-800 hover:text-slate-100",
        outline:
          "border border-slate-600 text-slate-300 hover:bg-slate-800",
        destructive:
          "border border-red-500 bg-red-500/10 text-red-300 hover:bg-red-500/20",
        warn:
          "border border-amber-500 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20",
      },
      size: {
        default: "h-9 px-3 py-1.5",
        sm: "h-7 px-2 text-xs",
        lg: "h-10 px-4",
        icon: "h-8 w-8 p-0",
      },
    },
    defaultVariants: {
      variant: "secondary",
      size: "default",
    },
  },
);
