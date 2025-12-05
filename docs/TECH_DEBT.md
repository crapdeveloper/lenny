## MarketDashboard pagination / duplicate-order issue

Date: 2025-12-03

Summary:
- Users reported React console warnings about duplicate keys in the Market Dashboard (example key: `911329313`). Investigation showed duplicates arise when paginated API responses overlap or when the client performs overlapping fetches for the same page.

Root causes identified:
- Client-side concurrent fetches (virtual scroller + state updates triggered multiple fetches for the same page).
- Non-deterministic pagination boundaries on the server (ORDER BY only by `issued` allowed items with identical timestamps to shift between pages).
- Offset/limit pagination combined with data churn can also cause items to move between pages.

Short-term fixes applied (safe, fast):
- Frontend:
	- Added `seenIdsRef` (a Set) to `MarketDashboard.jsx` to track already-present `order_id`s and only append incoming items that are new. This makes deduplication O(pageSize) instead of O(totalItems).
	- Added `inFlightPagesRef` to prevent duplicate concurrent fetches for the same page while a request is in-flight.
	- Added lightweight logging when an incoming page contains IDs already present locally to make tracing easier in development.
- Backend:
	- Made ordering deterministic by adding a tie-breaker to the query: `ORDER BY issued DESC, order_id ASC` to reduce boundary shifting across pages.

Why these fixes:
- The frontend changes prevent UI-level duplication and avoid expensive array scans, keeping the UI responsive with large result sets.
- The backend deterministic ordering reduces the chance of page overlap due to identical `issued` timestamps.

Recommended next steps (medium/long-term):
1. Implement cursor-based (seek) pagination for `/api/market/orders` returning a stable cursor (e.g. last (issued, order_id)). This eliminates overlap and scales well for very large datasets.
2. Add optional server-side snapshot or version tokens for consistent paging through a dataset snapshot if exact stability over long paging sessions is required.
3. Add server-side monitoring/logging around pagination responses (only in dev or behind a debug flag) to capture cases of overlapping page results in production for further diagnosis.
4. Consider moving heavy dedupe or list processing to a Web Worker if pages grow large and client-side processing becomes noticeable.

Notes:
- The short-term changes were implemented in `frontend/src/MarketDashboard.jsx` and `backend/routers/market.py` on 2025-12-03. Keep the duplicate-logging pieces gated behind a dev flag or remove them after a verification period.

