# AT Hot Deals — Price Monitor

Hourly price monitoring for Autotrader leasing hot deals. Auto-updates token files and records price history. Dashboard served via GitHub Pages.

## Setup (one-time, ~5 mins)

### 1. Create the repo
- Push this folder to a new GitHub repo (public)
- `git init` → `git add .` → `git commit -m "init"` → push to GitHub

### 2. Enable GitHub Pages
- Repo → Settings → Pages
- Source: **Deploy from a branch** → branch: `main` → folder: `/ (root)`
- Save. Your dashboard will be live at `https://<username>.github.io/<repo-name>/`

### 3. Enable Actions
- Repo → Actions → "I understand my workflows" → enable
- The `price_monitor.yml` workflow will run automatically every hour

### 4. Test it
- Actions → "AT Hot Deals Price Monitor" → "Run workflow" → Run
- Check the Actions log to confirm it ran
- Refresh the GitHub Pages URL to see the dashboard

---

## How it works

```
Every hour → GitHub Actions runs scripts/monitor.py
           → Fetches live prices from AT for all has_pmax deals
           → Compares with data/state.json
           → If changed: updates token file + appends to data/history.json
           → Commits everything → GitHub Pages serves updated dashboard
```

## Adding a new car

Edit `data/state.json` and add an entry:

```json
{
  "headline":      "Make Model",
  "subheadline":   "trim string from AT",
  "leaseprice":    999,
  "monthly_exact": 999.99,
  "listing_id":    "202XXXXXXXXX",
  "url":           "https://www.autotrader.co.uk/cars/leasing/product/202XXXXXXXXX",
  "frame_name":    "PMAX_Hotdeals_MakeModel_Trim",
  "slug":          "MakeModel_Trim",
  "figma_car_mode":"Make Model",
  "has_pmax":      true
}
```

The monitor will start tracking it on the next hourly run.

## Token files

`tokens/` always contains the latest `.tokens.json` for every tracked deal.
Import these into the PMAX Hot Deals Importer Figma plugin when prices update.
