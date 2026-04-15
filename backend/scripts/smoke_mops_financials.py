"""MOPS 季報三表 collector 煙霧測試。"""

import asyncio

from alpha_lab.collectors.mops_financials import (
    fetch_balance_sheet,
    fetch_cashflow_statement,
    fetch_income_statement,
)


async def main() -> None:
    symbols = ["2330", "2317"]

    income = await fetch_income_statement(symbols=symbols)
    print(f"\n[Income] {len(income)} rows")
    for r in income:
        print(
            f"  {r.symbol} {r.period} rev={r.revenue:,} "
            f"ni={r.net_income:,} eps={r.eps}"
        )

    balance = await fetch_balance_sheet(symbols=symbols)
    print(f"\n[Balance] {len(balance)} rows")
    for r in balance:
        print(
            f"  {r.symbol} {r.period} assets={r.total_assets:,} "
            f"liab={r.total_liabilities:,} equity={r.total_equity:,}"
        )

    cashflow = await fetch_cashflow_statement(symbols=symbols)
    print(f"\n[Cashflow] {len(cashflow)} rows")
    for r in cashflow:
        print(
            f"  {r.symbol} {r.period} op={r.operating_cf:,} "
            f"inv={r.investing_cf:,} fin={r.financing_cf:,}"
        )


if __name__ == "__main__":
    asyncio.run(main())
