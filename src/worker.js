/**
 * AI-LINK v1.0.0 Official Website & Release Portal Worker
 * Compatible with Cloudflare Workers (Static Assets) & Cloudflare Pages
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/version" || url.pathname === "/api/release") {
      return new Response(
        JSON.stringify({
          name: "AI-LINK (ai-link-openwrt)",
          version: "v1.0.0",
          release_date: "2026-10-26",
          core: "sing-box 1.12+ / 1.14+ & fw4 nftables",
          highlights: [
            "Always-On Auto Node Pool (1~5 Priority Groups + Sticky Lock + Dual-Group Probing)",
            "Single-Arm Side Router Symmetric NAT & Domestic Hardware Bypass (@cn_ip4/@cn_ip6)",
            "Cert-Free HomeLink (VLESS-Reality & Hysteria2 Dynamic pinSHA256)",
            "17/17 Byte-Identical Backup/Restore & 0-Residue Lifecycle"
          ]
        }, null, 2),
        {
          headers: {
            "content-type": "application/json; charset=utf-8",
            "access-control-allow-origin": "*"
          }
        }
      );
    }

    if (env.ASSETS) {
      return env.ASSETS.fetch(request);
    }

    return new Response("AI-LINK v1.0.0 Official Site Worker Active", { status: 200 });
  }
};
