import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRenderProps {
  source: string;
  className?: string;
}

export function MarkdownRender({ source, className }: MarkdownRenderProps) {
  return (
    <div
      className={`prose prose-invert max-w-none text-slate-200 ${
        className ?? ""
      }`}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (props) => (
            <h1 className="mt-0 mb-4 text-2xl font-bold text-slate-100" {...props} />
          ),
          h2: (props) => (
            <h2 className="mt-6 mb-3 text-xl font-semibold text-slate-100" {...props} />
          ),
          h3: (props) => (
            <h3 className="mt-4 mb-2 text-lg font-semibold text-slate-200" {...props} />
          ),
          p: (props) => <p className="mb-3 leading-relaxed" {...props} />,
          ul: (props) => <ul className="mb-3 list-disc pl-6 space-y-1" {...props} />,
          ol: (props) => <ol className="mb-3 list-decimal pl-6 space-y-1" {...props} />,
          code: (props) => (
            <code
              className="rounded bg-slate-800 px-1 py-0.5 text-sm text-sky-300"
              {...props}
            />
          ),
          table: (props) => (
            <table className="my-3 w-full border-collapse text-sm" {...props} />
          ),
          th: (props) => (
            <th
              className="border-b border-slate-700 py-1 text-left font-semibold"
              {...props}
            />
          ),
          td: (props) => (
            <td className="border-b border-slate-800 py-1" {...props} />
          ),
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
