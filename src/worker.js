/**
 * AI-LINK v1.0.1 Official Website & Release Portal Worker
 * Compatible with Cloudflare Workers (Static Assets) & Cloudflare Pages
 *
 * /api/version 与 /api/release 直接转发静态清单 /version.json，
 * 保证「插件 OTA 读到的版本」与「官网展示的版本」永远同源，不会各写一份。
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/version" || url.pathname === "/api/release") {
      if (env.ASSETS) {
        const assetUrl = new URL("/version.json", url.origin);
        const res = await env.ASSETS.fetch(new Request(assetUrl.toString(), { method: "GET" }));
        if (res.ok) {
          return new Response(res.body, {
            status: 200,
            headers: {
              "content-type": "application/json; charset=utf-8",
              "access-control-allow-origin": "*",
              "cache-control": "public, max-age=60, must-revalidate"
            }
          });
        }
      }
      return new Response(
        JSON.stringify({ ok: false, error: "manifest_unavailable", message: "version.json 暂不可用" }),
        { status: 503, headers: { "content-type": "application/json; charset=utf-8", "access-control-allow-origin": "*" } }
      );
    }

    if (env.ASSETS) {
      return env.ASSETS.fetch(request);
    }

    return new Response("AI-LINK v1.0.1 Official Site Worker Active", { status: 200 });
  }
};
