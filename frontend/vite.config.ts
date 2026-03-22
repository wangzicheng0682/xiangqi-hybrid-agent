import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import type { ProxyOptions } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',  // 使用 127.0.0.1，与后端保持一致，避免跨域
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        ws: true,
        // 禁用代理缓冲，确保 SSE 立即转发
        configure: (proxy, options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            proxyReq.setHeader('Cache-Control', 'no-cache');
            proxyReq.setHeader('X-Accel-Buffering', 'no');
            proxyReq.setHeader('Accept', 'text/event-stream');
          });
          proxy.on('proxyRes', (proxyRes, req, res) => {
            proxyRes.headers['cache-control'] = 'no-cache';
            proxyRes.headers['x-accel-buffering'] = 'no';
            // 强制立即发送响应头
            res.setHeader('Cache-Control', 'no-cache');
            res.setHeader('X-Accel-Buffering', 'no');
          });
        }
      } as ProxyOptions,
      '/health': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true
      } as ProxyOptions
    }
  }
})