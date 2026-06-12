#!/usr/bin/env python3
"""
AT Hot Deals Price Monitor
Fetches live prices for all tracked deals, records history, updates tokens.
Designed to run in GitHub Actions (no external dependencies beyond stdlib).
"""

import json, math, re, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE      = Path(__file__).parent.parent
STATE_F   = BASE / "data" / "state.json"
HISTORY_F = BASE / "data" / "history.json"
TOKENS_D  = BASE / "tokens"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def clean_url(url):
    """Strip leaseOption param — always fetch AT's default offer."""
    if not url:
        return url
    base = url.split("?")[0]
    # Keep leaseContractType=personal if present, drop leaseOption
    if "leaseContractType=personal" in url:
        return base + "?leaseContractType=personal"
    return base


def fetch_car(url):
    url = clean_url(url)
    req  = urllib.request.Request(url, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    m    = re.search(
        r'window\.__staticRouterHydrationData\s*=\s*JSON\.parse\("(.*?)"\);\s*</script>',
        html, re.DOTALL
    )
    if not m:
        raise ValueError("No hydration data — deal may have expired")
    data  = json.loads(json.loads('"' + m.group(1) + '"'))
    pdp   = data["loaderData"]["cars-leasing-pdp"]
    offer = pdp["selectedLeaseOffer"]
    spec  = pdp["leasingTechnicalSpecification"]["specification"]
    return {
        "headline":    f"{spec['make'].strip()} {spec['model'].strip()}",
        "subheadline": spec["derivative"].strip(),
        "monthly":     float(offer["monthlyPrice"]),
        "initial":     float(offer["initialPrice"]),
        "months":      int(offer["termMonths"]),
        "miles":       int(offer["totalMileage"]),
        "leaseprice":  math.ceil(float(offer["monthlyPrice"])),
    }


def build_terms(monthly, initial, months, miles):
    return (
        f"*Personal Contract Hire (PCH). Initial rental £{initial:,.2f}, "
        f"followed by {months - 1} monthly rentals of £{monthly:.2f} (inc. VAT). "
        f"{miles:,} miles p.a. You will not own the car. "
        f"Excess mileage charges and return conditions apply. "
        f"Subject to availability and credit status. T&Cs apply. 18+. "
        f"Autotrader Limited is a credit broker, not a lender"
    )


def write_token(deal, live):
    slug       = deal["slug"]
    figma_mode = deal.get("figma_car_mode", live["headline"])
    token = {
        "leaseprice":    {"$type": "string", "$value": str(live["leaseprice"])},
        "headline":      {"$type": "string", "$value": live["headline"]},
        "subheadline":   {"$type": "string", "$value": live["subheadline"]},
        "terms":         {"$type": "string", "$value": build_terms(
                            live["monthly"], live["initial"], live["months"], live["miles"])},
        "$url":          clean_url(deal["url"]),
        "$extensions":   {"com.figma.modeName": figma_mode},
        "$cars_variant": figma_mode,
        "$pmax_slug":    slug,
    }
    path = TOKENS_D / f"{slug}.tokens.json"
    path.write_text(json.dumps(token, indent=2, ensure_ascii=False))


def append_history(history, slug, headline, old_price, new_price, ts):
    if slug not in history:
        history[slug] = {"headline": headline, "prices": []}
    history[slug]["prices"].append({
        "timestamp": ts,
        "price":     new_price,
        "previous":  old_price,
        "direction": "up" if new_price > old_price else "down",
    })


# ── Main ───────────────────────────────────────────────────────────────────────

def run():
    state   = json.loads(STATE_F.read_text())
    history = json.loads(HISTORY_F.read_text()) if HISTORY_F.exists() else {}
    ts      = datetime.now(timezone.utc).isoformat()

    price_changes = []
    errors        = []
    checked       = 0

    print(f"\n{'='*60}")
    print(f"AT Hot Deals Monitor — {ts}")
    print(f"{'='*60}\n")

    for deal in state["deals"]:
        if not deal.get("has_pmax") or not deal.get("slug"):
            continue   # only check deals with PMAX designs

        slug     = deal["slug"]
        headline = deal["headline"]
        stored   = deal["leaseprice"]
        url      = deal.get("url", "")

        try:
            live      = fetch_car(url)
            new_price = live["leaseprice"]
            checked  += 1

            if new_price != stored:
                direction = "↑" if new_price > stored else "↓"
                price_changes.append({
                    "headline":  headline,
                    "slug":      slug,
                    "old":       stored,
                    "new":       new_price,
                    "direction": direction,
                })
                deal["leaseprice"]   = new_price
                deal["monthly_exact"] = live["monthly"]
                write_token(deal, live)
                append_history(history, slug, headline, stored, new_price, ts)
                print(f"  💰 {headline}: £{stored} → £{new_price} {direction}  [token updated]")
            else:
                print(f"  ✓  {headline}: £{stored}")

        except Exception as e:
            errors.append({"headline": headline, "error": str(e)})
            print(f"  ⚠️  {headline}: {e}")

    # Save state + history
    state["last_checked"] = ts
    STATE_F.write_text(json.dumps(state, indent=2))
    HISTORY_F.write_text(json.dumps(history, indent=2))

    print(f"\n{'─'*60}")
    print(f"Checked {checked} | Changed {len(price_changes)} | Errors {len(errors)}")

    # Exit 0 always — let the workflow decide whether to commit
    return len(price_changes) > 0


if __name__ == "__main__":
    changed = run()
    sys.exit(0)
