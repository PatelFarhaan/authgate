import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
  site: 'https://gatesuite.github.io',
  base: '/authgate',
  integrations: [
    starlight({
      title: 'AuthGate',
      description: 'Lightweight, customizable OAuth login service for your apps.',
      logo: {
        src: './src/assets/logo.svg',
      },
      customCss: ['./src/styles/custom.css'],
      head: [
        {
          tag: 'script',
          content: `
            document.addEventListener('DOMContentLoaded', () => {
              document.querySelectorAll('.social-icons a[href^="http"]').forEach(a => {
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
              });
            });
          `,
        },
      ],
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/gatesuite/authgate' },
      ],
      editLink: {
        baseUrl: 'https://github.com/gatesuite/authgate/edit/main/docs/',
      },
      sidebar: [
        {
          label: 'Start here',
          items: [
            { label: 'Introduction', link: '/' },
            { label: 'Quick Start', slug: 'quickstart' },
          ],
        },
        {
          label: 'Guides',
          items: [
            { label: 'Configuration', slug: 'configuration' },
            { label: 'OAuth Providers', slug: 'providers' },
            { label: 'Integration Guide', slug: 'integration' },
            { label: 'Managing Users', slug: 'managing-users' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'API Reference', slug: 'api-reference' },
            { label: 'Deployment', slug: 'deployment' },
            { label: 'Architecture', slug: 'architecture' },
            { label: 'Security', slug: 'security' },
          ],
        },
      ],
    }),
  ],
});
