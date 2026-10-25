#!/usr/bin/env python3
"""Collapse nested/overlapping CIDRs in nft interval sets.

nftables rejects a set whose elements overlap (e.g. 240.0.0.0/4 together with
255.255.255.255/32, or 59.108.0.0/14 together with 59.111.0.0/16, or single-line
node_server_v4 elements) with "Error: conflicting intervals specified".

Usage: normalize_nft_sets.py /var/run/ai-link/ai-link.nft
"""
import ipaddress
import re
import sys

PATTERN = re.compile(r"(\n[ \t]*elements[ \t]*=[ \t]*)\{(.*?)\}", re.S)


def collapse_block(match):
    prefix, body = match.group(1), match.group(2)
    items = [x for x in re.split(r"[,\s]+", body) if x.strip()]
    if not items:
        return match.group(0)
    try:
        nets = [ipaddress.ip_network(x, strict=False) for x in items]
    except Exception:
        return match.group(0)
    if len({n.version for n in nets}) != 1:
        return match.group(0)
    merged = list(ipaddress.collapse_addresses(nets))
    rendered = ",\n\t\t\t".join(str(n) for n in merged)
    return "%s{\n\t\t\t%s\n\t\t}" % (prefix, rendered)


def main(path):
    src = open(path, encoding="utf-8").read()
    new = PATTERN.sub(collapse_block, src)
    if new != src:
        open(path, "w", encoding="utf-8").write(new)
    print("prefixes: %d -> %d" % (src.count("/"), new.count("/")))


if __name__ == "__main__":
    main(sys.argv[1])
