import { defineConfig } from 'wxt';

export default defineConfig({
  manifest: {
    name: 'InterviewLens',
    description: 'AI-powered interview practice assistant',
    version: '1.0.0',
    manifest_version: 3,
    permissions: [
      'activeTab',
      'storage',
      'scripting'
    ],
    host_permissions: [
      "wss://your-backend-url/*"
    ],
    action: {
      default_popup: 'entrypoints/popup/index.html'
    }
  }
});