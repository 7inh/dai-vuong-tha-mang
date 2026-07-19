// Import and inject Vercel Analytics
import { inject } from './node_modules/@vercel/analytics/dist/index.mjs';

inject({
  mode: 'auto',
  debug: false
});
