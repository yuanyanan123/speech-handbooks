import asyncio, pathlib, sys
from playwright.async_api import async_playwright
JS = """(sid)=>{const el=document.getElementById(sid);const r=el.getBoundingClientRect();
return {y:r.y+window.scrollY,height:r.height,width:document.documentElement.scrollWidth};}"""
async def main():
    sid = sys.argv[1]; dark = len(sys.argv)>2 and sys.argv[2]=='dark'
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width':1100,'height':1400}, device_scale_factor=1.4,
                              color_scheme='dark' if dark else 'light')
        await pg.goto(pathlib.Path('sv-handbook.html').resolve().as_uri(), wait_until='load')
        await pg.wait_for_timeout(1200)
        box = await pg.evaluate(JS, sid)
        n = int(box['height']//2400)+1
        for k in range(n):
            y = box['y']+k*2400
            hgt = min(2400, box['y']+box['height']-y)
            if hgt < 20: continue
            t = f"{sid}{'_dk' if dark else ''}_{k}"
            await pg.screenshot(path=f'v_{t}.png', clip={'x':0,'y':y,'width':box['width'],'height':hgt}, full_page=True)
            print('✓ v_%s.png %dx%d' % (t, box['width'], hgt))
        await b.close()
asyncio.run(main())
