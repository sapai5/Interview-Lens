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
      'scripting',
      'camera'  // Add camera permission
    ],
    host_permissions: [
      'wss://your-backend-url/*',
      '<all_urls>'  // Add this for camera access
    ],
    web_accessible_resources: [{
      resources: ['index.html'],
      matches: ['<all_urls>']
    }]
  }
});