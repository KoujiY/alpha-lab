import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { HeaderSearch } from "@/components/HeaderSearch";

function renderWithRouter() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<HeaderSearch />} />
        <Route path="/stocks/:symbol" element={<p>stock page {":symbol"}</p>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("HeaderSearch", () => {
  it("submits symbol and navigates to /stocks/:symbol", async () => {
    renderWithRouter();
    const input = screen.getByRole("textbox", { name: /股票代號/i });
    await userEvent.type(input, "2330{enter}");
    expect(await screen.findByText(/stock page/i)).toBeInTheDocument();
  });

  it("rejects empty input (stays on same page)", async () => {
    renderWithRouter();
    const input = screen.getByRole("textbox", { name: /股票代號/i });
    await userEvent.type(input, "{enter}");
    expect(screen.queryByText(/stock page/i)).not.toBeInTheDocument();
  });
});
