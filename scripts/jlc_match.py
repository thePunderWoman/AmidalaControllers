#!/usr/bin/env python3
"""Match SnipsControllers BOM parts to JLCPCB/LCSC part numbers.

Groups the Stackup parts by manufacturer, MPN, Value and footprint, then looks
each group up against JLCPCB's public component-search endpoint -- the same
one jlcpcb.com's own website search box uses. No API key
needed; it's the unauthenticated site-search API, not the registered OpenAPI.

This only produces a report. Review the output, then a separate step writes
confirmed matches into Stackup and the PCB's LCSC fields.

Usage:
    python3 scripts/jlc_match.py
    python3 scripts/jlc_match.py --out /tmp/jlc_match.csv
"""
import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.request
from stackup_parts import read_bom_rows

JLC_SEARCH_URL = (
    "https://jlcpcb.com/api/overseas-pcb-order/v1/"
    "shoppingCart/smtGood/selectSmtComponentList/v2"
)
FIELDNAMES = [
    "Refs", "Value", "Footprint", "MF", "MPN", "LCSC", "LibraryType", "BasicAlt", "Status",
]

# JLC's "Extended" library carries a per-unique-part setup fee on top of unit
# price; "Basic" doesn't. That fee doesn't amortize well on a board with many
# distinct low-quantity parts, so it's worth flagging a cheaper Basic-library
# equivalent whenever the real match landed on Extended.
PACKAGE_RE = re.compile(
    r"(0201|0402|0603|0805|1206|1210|1812|2010|2512|"
    r"SOT-?23-?\d*|SOD-?\d+|SOIC-?\d*|SOP-?\d*|QFN-?\d*|TO-?\d+|SMA|SMB|SMC)",
    re.IGNORECASE,
)


def export_bom():
    return [
        {key: row[key] for key in ("Refs", "Value", "Footprint", "MF", "MPN", "DNP")}
        for row in read_bom_rows()
    ]


def normalize(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def search_jlc(keyword):
    payload = {
        "currentPage": 1,
        "pageSize": 25,
        "keyword": keyword,
        "searchSource": "search",
        "searchType": 2,
        "componentBrandList": [],
        "componentSpecificationList": [],
        "componentAttributeList": [],
        "paramList": [],
    }
    req = urllib.request.Request(
        JLC_SEARCH_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://jlcpcb.com/parts",
            "User-Agent": "Mozilla/5.0 (compatible; SnipsControllers-jlc-match/1.0)",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    if data.get("code") != 200:
        return []
    return (data.get("data") or {}).get("componentPageInfo", {}).get("list", []) or []


def best_match(mf, candidates):
    """Pick the right candidate among exact-MPN hits.

    The search is keyword-based, so every candidate already has a matching
    MPN by construction -- what's left is picking the right manufacturer
    when more than one brand sells a part under the same part number.

    JLC's own "JLCPCB Assembly" brand shows up as a zero-stock placeholder
    SKU alongside the real listing for some parts (seen on the USB-C
    connector) -- it's not a real manufacturer, so it's discarded before
    disambiguating on brand.
    """
    real = [c for c in candidates if normalize(c.get("componentBrandEn")) != "JLCPCBASSEMBLY"]
    pool = real or candidates

    mf_n = normalize(mf)
    exact = [c for c in pool if normalize(c.get("componentBrandEn")) == mf_n]
    if len(exact) == 1:
        return exact[0], "matched"

    # JLC sometimes prefixes/suffixes the brand (e.g. "Korean Hroparts Elec"
    # for our "Hroparts Elec") -- fall back to substring containment.
    contains = [c for c in pool if mf_n in normalize(c.get("componentBrandEn")) or
                normalize(c.get("componentBrandEn")) in mf_n]
    if len(contains) == 1:
        return contains[0], "matched (brand name is a variant of schematic's MF field)"

    if len(pool) == 1:
        return pool[0], "matched (brand name differs from schematic's MF field)"
    if exact:
        return exact[0], "matched (multiple brands sell this MPN, picked ours)"
    if contains:
        return contains[0], "matched (multiple brands sell this MPN, picked closest brand match)"
    return pool[0], "AMBIGUOUS: multiple brands sell this MPN, none match our MF field"


def match_row(mf, mpn):
    exact_mpn = normalize(mpn)
    candidates = [c for c in search_jlc(mpn) if normalize(c.get("componentModelEn")) == exact_mpn]
    if not candidates:
        return None, "no LCSC listing found for this MPN"
    return best_match(mf, candidates)


def extract_package(footprint):
    m = PACKAGE_RE.search(footprint or "")
    return m.group(1) if m else None


def clean_value(value):
    return (value or "").replace("Ω", "").replace("µ", "u").strip()


UNIT_MULTIPLIERS = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "M": 1e6}
# \b requires the number to start on a word boundary, so it won't latch onto
# a digit embedded mid-word -- but JLC descriptions often carry a Chinese
# prefix (e.g. "厚膜电阻 10kΩ ±1%" -- "thick film resistor 10kΩ ±1%") before
# the value, so this searches anywhere in the string rather than anchoring
# to the start.
VALUE_RE = re.compile(r"\b([\d.]+)\s*([pnumkM]?)([FΩR]|ohm)\b", re.IGNORECASE)


def parse_numeric_value(text):
    """Parse a '10kΩ' / '100nF' / '47pF' style value into (magnitude, unit).

    Returns None if no such value/unit pattern is found -- e.g. a generic
    part name like '1N4148W' used as the Value field, which needs exact
    model-name matching instead, not numeric comparison.
    """
    if not text:
        return None
    # Only normalize the micro-prefix here -- clean_value() strips the unit
    # symbols entirely (useful for building search keywords), which would
    # leave nothing for this regex's required unit group to match.
    m = VALUE_RE.search(text.replace("µ", "u"))
    if not m or not m.group(1):
        return None
    magnitude = float(m.group(1)) * UNIT_MULTIPLIERS.get(m.group(2), 1)
    unit = "F" if (m.group(3) or "").upper() == "F" else "R"
    return magnitude, unit


def find_basic_alternative(value, footprint, exclude_lcsc):
    """Best-effort search for a Basic-library part with the same value/package.

    Only meaningful for generic passives (resistors/caps/etc.) where JLC's
    Basic library commonly stocks an equivalent -- for branded/mechanical
    parts (connectors, modules, specific ICs) this will usually just find
    nothing, which is the correct answer to report.

    The search is keyword-based full-text matching, which can misfire on
    numeric values that share digits (e.g. a "100" search matching a "1001"
    EIA-code part that's actually 1kΩ, not 100R) -- so every candidate's
    actual value is re-verified before being accepted, not just trusted
    from the search hit.
    """
    package = extract_package(footprint)
    if not package:
        return None
    keyword = f"{clean_value(value)} {package}".strip()
    if not keyword:
        return None
    candidates = [
        c for c in search_jlc(keyword)
        if normalize(c.get("componentLibraryType")) == "BASE"
        and c.get("componentCode") != exclude_lcsc
        and package.upper() in (c.get("componentSpecificationEn") or "").upper()
    ]
    if not candidates:
        return None

    wanted = parse_numeric_value(value)
    if wanted is not None:
        verified = []
        for c in candidates:
            got = parse_numeric_value(c.get("erpComponentName"))
            if got and got[1] == wanted[1] and abs(got[0] - wanted[0]) <= 0.01 * wanted[0]:
                verified.append(c)
        candidates = verified
    else:
        # Non-numeric value -- for a generic/family part name (e.g. "1N4148W",
        # "2N7002" in the Value field, as opposed to a manufacturer-specific
        # MPN like "1N4148W-7-F"), require the candidate's model number to
        # match that generic name exactly rather than trust a keyword hit.
        value_n = normalize(value)
        candidates = [c for c in candidates if normalize(c.get("componentModelEn")) == value_n]

    if not candidates:
        return None
    return max(candidates, key=lambda c: c.get("stockCount", 0))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", default=None, help="Write results CSV here")
    parser.add_argument("--delay", type=float, default=0.4, help="Seconds between API requests")
    args = parser.parse_args()

    rows = export_bom()

    results = []
    for row in rows:
        mf, mpn, dnp = row["MF"].strip(), row["MPN"].strip(), row.get("DNP", "").strip()
        if dnp:
            results.append({**row, "LCSC": "", "LibraryType": "", "BasicAlt": "", "Status": "DNP, skipped"})
            continue
        if not mf or not mpn:
            results.append({**row, "LCSC": "", "LibraryType": "", "BasicAlt": "", "Status": "missing MF/MPN"})
            continue
        try:
            match, status = match_row(mf, mpn)
        except (urllib.error.URLError, TimeoutError) as e:
            results.append({**row, "LCSC": "", "LibraryType": "", "BasicAlt": "", "Status": f"lookup failed: {e}"})
            continue
        time.sleep(args.delay)

        lcsc = (match or {}).get("componentCode", "")
        library_type = (match or {}).get("componentLibraryType", "")
        basic_alt = ""
        if match and normalize(library_type) != "BASE":
            try:
                alt = find_basic_alternative(row["Value"], row["Footprint"], lcsc)
            except (urllib.error.URLError, TimeoutError):
                alt = None
            if alt:
                basic_alt = alt.get("componentCode", "")
                status += f" | ALERT: Basic-library alternative available ({basic_alt}, stock={alt.get('stockCount', 0)}) -- review before ordering"
            else:
                status += " | Extended library, no Basic-library alternative found"
            time.sleep(args.delay)

        results.append({
            **row,
            "LCSC": lcsc,
            "LibraryType": library_type,
            "BasicAlt": basic_alt,
            "Status": status,
        })

    width = {k: max(len(k), *(len(r.get(k, "")) for r in results)) for k in FIELDNAMES}
    header = "  ".join(k.ljust(width[k]) for k in FIELDNAMES)
    print(header)
    print("-" * len(header))
    for r in results:
        print("  ".join(r.get(k, "").ljust(width[k]) for k in FIELDNAMES))

    if args.out:
        with open(args.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDNAMES)
            w.writeheader()
            for r in results:
                w.writerow({k: r.get(k, "") for k in FIELDNAMES})
        print(f"\nWrote {args.out}", file=sys.stderr)

    matched = sum(1 for r in results if r["LCSC"])
    print(f"\n{matched}/{len(results)} parts matched to an LCSC part number.", file=sys.stderr)


if __name__ == "__main__":
    main()
