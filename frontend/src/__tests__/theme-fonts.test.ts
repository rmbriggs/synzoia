import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../..');           // frontend/
const indexHtml = readFileSync(resolve(root, 'index.html'), 'utf8');
const indexCss = readFileSync(resolve(root, 'src/index.css'), 'utf8');

describe('coastal fonts are wired and old fonts are gone', () => {
  it('index.html loads the three mockup fonts', () => {
    expect(indexHtml).toContain('Cormorant+Garamond');
    expect(indexHtml).toContain('Plus+Jakarta+Sans');
    expect(indexHtml).toContain('Space+Mono');
  });
  it('no old font families remain anywhere in theme files', () => {
    for (const stale of ['Lora', 'DM Sans', 'DM+Sans', 'IBM Plex Mono', 'IBM+Plex+Mono']) {
      expect(indexHtml).not.toContain(stale);
      expect(indexCss).not.toContain(stale);
    }
  });
  it('index.css font tokens use the coastal families', () => {
    expect(indexCss).toContain('"Cormorant Garamond"');
    expect(indexCss).toContain('"Plus Jakarta Sans"');
    expect(indexCss).toContain('"Space Mono"');
  });
});
