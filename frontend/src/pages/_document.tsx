import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
        <meta name="description" content="IoT Device Monitor Dashboard" />
        <meta name="theme-color" content="#1F2937" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
} 