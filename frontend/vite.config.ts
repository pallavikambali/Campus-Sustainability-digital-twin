import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '..', '');

  return {
    envDir: '..',
    plugins: [react(), tailwindcss()],
    server: {
      host: '0.0.0.0',
      port: 5000,
      strictPort: true,
      allowedHosts: true,
      proxy: {
        '/api/v1': {
          target:
            env.VITE_API_PROXY_TARGET ||
            'https://campus-sustainability-backend-flg0.onrender.com',
          changeOrigin: true,
          secure: true,
        },
      },
    },
  };
});
