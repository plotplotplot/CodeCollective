function trimTrailingSlash(value) {
  return (value || "").replace(/\/+$/, "");
}

function buildTargetUrl(requestUrl, targetOrigin, stripPrefix = "") {
  const url = new URL(requestUrl);
  const normalizedPrefix = stripPrefix && url.pathname.startsWith(stripPrefix)
    ? url.pathname.slice(stripPrefix.length) || "/"
    : url.pathname;
  return `${trimTrailingSlash(targetOrigin)}${normalizedPrefix}${url.search}`;
}

async function proxyRequest(request, targetOrigin, env, options = {}) {
  const origin = trimTrailingSlash(targetOrigin);
  if (!origin) {
    return new Response("Upstream origin is not configured", { status: 502 });
  }

  const targetUrl = buildTargetUrl(request.url, origin, options.stripPrefix || "");
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-forwarded-host", new URL(request.url).host);
  requestHeaders.set("x-forwarded-proto", "https");

  const proxied = await fetch(targetUrl, {
    method: request.method,
    headers: requestHeaders,
    body: request.body,
    redirect: "manual",
    cf: { cacheEverything: false },
  });

  const responseHeaders = new Headers(proxied.headers);
  responseHeaders.set("access-control-allow-origin", "*");
  responseHeaders.set("access-control-allow-methods", "GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS");
  responseHeaders.set("access-control-allow-headers", "authorization,content-type,x-requested-with");

  return new Response(proxied.body, {
    status: proxied.status,
    statusText: proxied.statusText,
    headers: responseHeaders,
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS" && (url.pathname.startsWith("/api/governance") || url.pathname.startsWith("/pidp"))) {
      return new Response(null, {
        status: 204,
        headers: {
          "access-control-allow-origin": "*",
          "access-control-allow-methods": "GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS",
          "access-control-allow-headers": "authorization,content-type,x-requested-with",
        },
      });
    }

    if (url.pathname.startsWith("/api/governance")) {
      return proxyRequest(request, env.GOVERNANCE_API_ORIGIN, env);
    }

    if (url.pathname.startsWith("/pidp")) {
      return proxyRequest(request, env.PIDP_API_ORIGIN, env, { stripPrefix: "/pidp" });
    }

    const assetResponse = await env.ASSETS.fetch(request);
    if (assetResponse.status !== 404) {
      return assetResponse;
    }

    const acceptsHtml = request.headers.get("accept")?.includes("text/html");
    if (request.method === "GET" && acceptsHtml) {
      return env.ASSETS.fetch(new Request(`${url.origin}/index.html`, request));
    }

    return assetResponse;
  },
};
