import asyncio, pathlib, sys
from playwright.async_api import async_playwright
JS = """() => {
  const bad = [];
  if (document.documentElement.scrollWidth > window.innerWidth + 1)
    bad.push(['PAGE', document.documentElement.scrollWidth, window.innerWidth]);
  document.querySelectorAll('.fml-body .katex-html, .katex-display').forEach((e,i)=>{
    if (e.scrollWidth > e.clientWidth + 2 && e.clientWidth > 0)
      bad.push([(e.closest('.fml')?.querySelector('.fml-name')?.textContent)||('#'+i),
                e.scrollWidth, e.clientWidth]);
  });
  document.querySelectorAll('table').forEach((e,i)=>{
    const w = e.closest('.tw');
    if (w && e.scrollWidth > w.clientWidth + 2) bad.push(['TABLE#'+i, e.scrollWidth, w.clientWidth]);
  });
  return bad;
}"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w in (1280, 420):
            for mode in ('light','dark'):
                pg = await b.new_page(viewport={'width': w, 'height': 900}, color_scheme=mode)
                await pg.goto(pathlib.Path('enh-handbook.html').resolve().as_uri(), wait_until='load')
                await pg.wait_for_timeout(900)
                bad = await pg.evaluate(JS)
                print('%4d %-5s  %s' % (w, mode, '✓ 无溢出' if not bad else '✗ %d 处: %s' % (len(bad), bad[:6])))
                await pg.close()
        await b.close()
asyncio.run(main())
