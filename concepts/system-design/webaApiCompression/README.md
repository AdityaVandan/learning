# Compression in Web APIs

## Understanding Compression Types
### Gzip (most common)
- Best compression ratio for text-based content (JSON, HTML, CSS)
- Widely supported by all browsers and clients
- Moderate CPU usage
- Typical compression: 70-90% for JSON/text

### Brotli (modern alternative)
- 15-20% better compression than gzip for static content
- Better for static assets, similar to gzip for dynamic content
- Slightly higher CPU cost but faster decompression
- Growing browser support (90%+ modern browsers)

### Deflate (legacy)
- Underlying algorithm used by gzip
- Less commonly used directly
- Mostly for backward compatibility

## When to use what:
- APIs serving JSON: Gzip (universal support)
- Static files (JS/CSS): Brotli (pre-compress at build time)
- High-traffic dynamic content: Gzip (CPU efficiency)

## Compression example: 
```bash
python3 brotli_compression_example.py
```


Production Reality Check
In production, compression is rarely handled by application code. Here's the actual hierarchy:

- Client Request
- CDN (Cloudflare/CloudFront) ← Pre-compressed static files
- Load Balancer (AWS ALB/nginx) ← Compression layer
- Application Server (Node/Python) ← Minimal/no compression
- Response

Let me break down exactly how this works in real production systems.

**Part 1: Static Websites (HTML/CSS/JS)**

- Developer Machine
- Build Process (webpack/vite) (generates .gz and .br files)
- CI/CD Pipeline
- Upload to S3/Storage
- CDN (CloudFront/Cloudflare)
- End User

**Part 2: Dynamic Content (APIs)**

- Client Request
- CDN (Cloudflare/CloudFront)
- Load Balancer (AWS ALB/nginx) ← Compression layer
- Application Server (Node/Python) ← Minimal/no compression
- Response

**Key Takeaways**

- Static content is usually pre-compressed by the CDN and served directly
- For dynamic content, the load balancer handles compression before hitting the application server
- Gzip/Brotli is a compression algorithm, not a library
- Compression should be handled at the edge of the network, not in the application server
- Modern CDNs can handle compression for static content
- Compression is not a silver bullet and should be used judiciously

### Webpack and Vite compression configuration example

```bash

// webpack.config.js
const CompressionPlugin = require('compression-webpack-plugin');
const BrotliPlugin = require('brotli-webpack-plugin');

module.exports = {
  mode: 'production',
  
  optimization: {
    minimize: true,
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10
        }
      }
    }
  },

  plugins: [
    // Generate .gz files
    new CompressionPlugin({
      filename: '[path][base].gz',
      algorithm: 'gzip',
      test: /\.(js|css|html|svg)$/,
      threshold: 10240, // Only compress > 10KB
      minRatio: 0.8,
      compressionOptions: { level: 9 } // Max compression
    }),

    // Generate .br files (brotli - better compression)
    new BrotliPlugin({
      asset: '[path].br[query]',
      test: /\.(js|css|html|svg)$/,
      threshold: 10240,
      minRatio: 0.8
    })
  ]
};
```

**What this produces:**
```
dist/
  ├── main.js (500 KB)
  ├── main.js.gz (150 KB)  ← Pre-compressed
  ├── main.js.br (120 KB)  ← Even better compression
  ├── main.css (100 KB)
  ├── main.css.gz (20 KB)
  └── main.css.br (15 KB)
```

```bash
// vite.config.js
import { defineConfig } from 'vite';
import viteCompression from 'vite-plugin-compression';

export default defineConfig({
  plugins: [
    // Gzip compression
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
      threshold: 10240,
      deleteOriginFile: false
    }),
    
    // Brotli compression
    viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
      threshold: 10240,
      deleteOriginFile: false
    })
  ],
  
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['react', 'react-dom'],
          'ui': ['@mui/material']
        }
      }
    }
  }
});

```
