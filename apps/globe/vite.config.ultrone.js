// ULTRONE-owned Vite config: wraps the upstream standalone config with
// ULTRONE integration needs. Upstream files are untouched.
//
//   1. Prepends the ULTRONE geo proxy (/api/ultrone/* -> the Python geo API,
//      default http://127.0.0.1:8001, override with ULTRONE_GEO_URL). It must
//      be a pre-enforced plugin (not server.proxy): upstream provider
//      middlewares, including the catch-all api-not-found 404, run before
//      Vite's built-in proxy and would swallow the route.
//   2. Relaxes the upstream anti-framing headers so the console can embed in
//      the ULTRONE shell / sandboxed preview iframe. (Upstream keeps DENY.)
//
// Run with:  npm run dev:ultrone   (or: vite --config vite.config.ultrone.js)
import baseConfig from './server/standalone/vite.config.js';
import { ultroneProxyPlugin } from './server/standalone/vite.ultrone-proxy.js';

export default async function ultroneConfig(env) {
  const base =
    typeof baseConfig === 'function' ? await baseConfig(env) : baseConfig;
  const server = { ...(base.server || {}) };

  const headers = { ...(server.headers || {}) };
  delete headers['X-Frame-Options'];
  delete headers['Content-Security-Policy'];
  server.headers = Object.keys(headers).length ? headers : undefined;

  return {
    ...base,
    plugins: [ultroneProxyPlugin(), ...(base.plugins || [])],
    server,
  };
}
