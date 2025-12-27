import type { AppProps } from 'next/app';
import Head from 'next/head';
import { useEffect } from 'react';
import '../styles/responsive.css';
import ErrorBoundary from '../components/ui/ErrorBoundary';
import ConnectionStatus from '../components/ui/ConnectionStatus';
// Force WebSocket client initialization
import wsClient from '../services/websocketClient';

export default function App({ Component, pageProps }: AppProps) {
  // Force WebSocket client initialization on app start
  useEffect(() => {
    console.log('App started, WebSocket client should be initialized');
    // This will trigger the WebSocket client singleton to initialize if it hasn't already
    if (typeof window !== 'undefined') {
      console.log('Checking WebSocket client status...');
      // Access wsClient to ensure it's initialized
      const isConnected = wsClient.isConnected();
      console.log('WebSocket client isConnected:', isConnected);
    }
  }, []);

  return (
    <ErrorBoundary>
      <Head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <style jsx global>{`
        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }
        
        html {
          font-size: 16px;
          scroll-behavior: smooth;
        }
        
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
          line-height: 1.6;
          color: var(--color-text-primary);
          background-color: var(--color-bg-primary);
          overflow-x: hidden;
        }
        
        html, body, #__next {
          height: 100%;
          width: 100%;
        }

        /* Scrollbar styles */
        ::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        
        ::-webkit-scrollbar-track {
          background: transparent;
          border-radius: var(--radius-md);
        }
        
        ::-webkit-scrollbar-thumb {
          background: var(--color-border-secondary);
          border-radius: var(--radius-md);
          transition: all 0.3s ease;
        }
        
        ::-webkit-scrollbar-thumb:hover {
          background: var(--color-text-tertiary);
        }

        /* Firefox scrollbar */
        * {
          scrollbar-width: thin;
          scrollbar-color: var(--color-border-secondary) transparent;
        }

        /* Focus styles */
        *:focus {
          outline: 2px solid var(--color-accent-blue);
          outline-offset: 2px;
        }

        /* Text selection styles */
        ::selection {
          background-color: var(--color-accent-blue);
          color: var(--color-text-primary);
        }

        /* Animations */
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes slideIn {
          from { transform: translateX(-100%); }
          to { transform: translateX(0); }
        }

        /* Animation utility classes */
        .animate-spin {
          animation: spin 1s linear infinite;
        }

        .animate-pulse {
          animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }

        .animate-slideIn {
          animation: slideIn 0.3s ease-out;
        }

        /* Responsive visibility utilities */
        @media (max-width: 640px) {
          .hidden-mobile { display: none !important; }
        }

        @media (min-width: 641px) {
          .hidden-desktop { display: none !important; }
        }

        /* Accessibility support */
        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
          }
        }
      `}</style>
      <Component {...pageProps} />
      <ConnectionStatus showText position="top-right" />
    </ErrorBoundary>
  );
} 