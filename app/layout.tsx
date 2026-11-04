import type { Metadata } from 'next';
import './globals.css';
import {BRAND_FULL} from '../lib/brand';
import './studio-theme.css';
import './studio-layers.css';
import './editor-workspace.css';
import './creator-platform.css';
export const metadata: Metadata = { title: `${BRAND_FULL} · Creator workspace`, description: 'Turn long videos into stories worth sharing. Local, open-source video clipping.' };
export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) { return <html lang="en"><body>{children}</body></html>; }
