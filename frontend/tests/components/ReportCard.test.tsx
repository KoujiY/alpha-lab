import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ReportCard } from "@/components/reports/ReportCard";
import type { ReportMeta } from "@/api/types";

const sample: ReportMeta = {
  id: "portfolio-2026-04-15",
  type: "portfolio",
  title: "本次推薦組合 2026-04-15",
  symbols: ["2330", "2317"],
  tags: ["portfolio", "recommend"],
  date: "2026-04-15",
  path: "analysis/portfolio-2026-04-15.md",
  summary_line: "calc_date=2026-04-15，3 組風格、Top Pick: balanced",
  starred: false,
};

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("ReportCard", () => {
  it("renders title, type badge, date and symbols", () => {
    renderWithRouter(<ReportCard meta={sample} />);
    expect(screen.getByText("本次推薦組合 2026-04-15")).toBeInTheDocument();
    expect(screen.getByText("組合")).toBeInTheDocument();
    expect(screen.getByText("2026-04-15")).toBeInTheDocument();
    expect(screen.getByText("2330, 2317")).toBeInTheDocument();
  });

  it("renders summary line and tags", () => {
    renderWithRouter(<ReportCard meta={sample} />);
    expect(screen.getByText(/Top Pick: balanced/)).toBeInTheDocument();
    expect(screen.getByText("#portfolio")).toBeInTheDocument();
    expect(screen.getByText("#recommend")).toBeInTheDocument();
  });

  it("links to the detail route", () => {
    renderWithRouter(<ReportCard meta={sample} />);
    const link = screen.getByRole("link");
    expect(link.getAttribute("href")).toBe("/reports/portfolio-2026-04-15");
  });

  it("hides symbols/summary when empty", () => {
    renderWithRouter(
      <ReportCard
        meta={{ ...sample, symbols: [], summary_line: "", tags: [] }}
      />,
    );
    expect(screen.queryByText(/calc_date/)).not.toBeInTheDocument();
  });
});
