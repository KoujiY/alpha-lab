"""教學系統 L2 詳解（Phase 4）。

L2 內容以 markdown 檔儲存於 `education/l2/<topic>.md`，frontmatter 定義 id、title、
related_terms；body 為自由 markdown。Loader 啟動時掃檔、cache 為 dict[id, L2Topic]。
"""
