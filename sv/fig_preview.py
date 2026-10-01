import asyncio, pathlib, sys, json, io, re
from playwright.async_api import async_playwright

src, keys = sys.argv[1], sys.argv[2].split(',')
F = json.load(open(src))
h = io.open('_head.html', encoding='utf-8').read()
sty = ''.join(re.findall(r'<style>.*?</style>', h, re.S)[-1:])   # 页面 CSS
body = '\n'.join('<figure><div class="figbox scrollx">%s</div></figure>' % F[k] for k in keys)
page = ('<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        + sty + '</head><body><main style="max-width:760px;margin:20px auto;padding:0 16px">'
        + body + '</main></body></html>')
io.open('_prev.html', 'w', encoding='utf-8').write(page)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for mode in ('light', 'dark'):
            pg = await b.new_page(viewport={'width': 820, 'height': 900},
                                  device_scale_factor=2, color_scheme=mode)
            await pg.goto(pathlib.Path('_prev.html').resolve().as_uri(), wait_until='load')
            await pg.wait_for_timeout(400)
            await pg.screenshot(path=f'_prev_{mode}.png', full_page=True)
            print('✓ _prev_%s.png' % mode)
        await b.close()
asyncio.run(main())
