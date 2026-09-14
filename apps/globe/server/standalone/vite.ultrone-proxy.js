// ULTRONE-owned Vite plugin: proxy /api/ultrone/* to the Python geo API.
//
// Runs with enforce:'pre' so it registers before the upstream provider
// middlewares (incl. the catch-all api-not-found 404). Zero dependencies —
// plain node:http forwarding. The browser always talks same-origin; only
// this dev-server middleware dials the backend host.
import http from 'node:http';
import https from 'node:https';

export const ULTRONE_API_PREFIX = '/api/ultrone';

export function ultroneProxyPlugin({ prefix = ULTRONE_API_PREFIX, target } = {}) {
  const targetUrl = new URL(
    target || process.env.ULTRONE_GEO_URL || 'http://127.0.0.1:8001',
  );
  const proxyLib = targetUrl.protocol === 'https:' ? https : http;
  const defaultPort = targetUrl.protocol === 'https:' ? 443 : 80;
  return {
    name: 'ultrone-geo-proxy',
    enforce: 'pre',
    configureServer(server) {
      server.middlewares.use(prefix, (req, res) => {
        const proxyReq = proxyLib.request(
          {
            hostname: targetUrl.hostname,
            port: Number(targetUrl.port) || defaultPort,
            path: req.originalUrl || req.url,
            method: req.method,
            headers: { ...req.headers, host: targetUrl.host },
          },
          (proxyRes) => {
            res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
            proxyRes.pipe(res);
          },
        );
        proxyReq.on('error', () => {
          if (!res.headersSent) {
            res.writeHead(502, { 'Content-Type': 'application/json' });
            res.end(
              JSON.stringify({ error: 'ULTRONE geo backend unavailable' }),
            );
          }
        });
        req.pipe(proxyReq);
      });
    },
  };
}
