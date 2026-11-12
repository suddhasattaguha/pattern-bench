"""Pattern Bench — ripple of contract changes, calling application, ripple forecast, start from a description.
Run: python3 tests/test_ripple.py"""
import json, os, tempfile
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'file:///' + ROOT.replace(os.sep, '/').lstrip('/') + '/pattern-bench.html'
D = tempfile.mkdtemp() + '/'
res = []
def check(name, cond):
    res.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name)

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1400, 'height': 900}, accept_downloads=True)
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    ev = pg.evaluate
    def flow(*tpls, versioning=True):
        pg.goto(URL)
        for t in tpls:
            ev(f"(()=>{{window.__debug.append('{t}'); window.__debug.recordHistory();}})()")
        pg.mouse.click(1300, 860)          # empty click: also answers an open caller question with "no"
        if versioning: pg.click('#tabVersioned')
    def drop(vid, i):
        r = ev(f"(()=>{{const r=window.__debug.chainOrder()[{i}].getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()")
        ev(f"window.__debug.dropVersion('{vid}',{r[0]},{r[1]})")
    dec = lambda: ev("window.__debug.decisions()")
    rip = lambda: ev("window.__debug.ripples()")
    click = lambda sel: ev(f"document.querySelector({json.dumps(sel)}).click()")   # no scrolling of the pane
    deltas = lambda: pg.locator('#vworld .dbadge').count()
    impacts = lambda: pg.locator('#vworld .ibadge').count()

    # ---------- downstream ripple: two topic versions into the same queue and process ----------
    flow('process-to-publish', 'consume-to-process', 'process-to-api')
    drop('c2p-contract-dual', 1)
    r = [d for d in dec() if d.get('kind') == 'ripple']
    check('same Queue subscribes to both: Process-to-API is asked about the change reaching the shared process',
          len(r) == 1 and r[0]['index'] == 2 and r[0]['side'] == 'downstream')
    check('the card offers absorb here / pass on', pg.locator('#vworld .ripple-card [data-ripple]').count() == 2
          and 'end application' in pg.inner_text('#vworld .ripple-card [data-ripple=pass]'))
    click('#vworld .ripple-card [data-ripple=absorb]')
    check('absorb: the shared process shows a code change in the same version (v1 Δ)', deltas() == 1
          and pg.text_content('#vworld .dbadge text') == 'v1 Δ')
    check('absorb: the ripple stops, nothing flagged on the end application', impacts() == 0)
    check('absorb: the question is resolved and shown as a pill', not any(d.get('kind') == 'ripple' for d in dec())
          and 'Absorbed' in pg.inner_text('#vworld .ripple-pill'))
    click('#vworld .ripple-pill')
    check('clicking the pill reopens the question', pg.locator('#vworld .ripple-card').count() == 1 and deltas() == 0)
    click('#vworld .ripple-card [data-ripple=pass]')
    check('pass on asks whether the process needs a code change', pg.locator('#vworld .ripple-card [data-code]').count() == 2)
    check('…and is still pending until answered', any(d.get('kind') == 'ripple' for d in dec()))
    click('#vworld .ripple-card [data-code=no]')
    check('passed on untouched: no code change marker', deltas() == 0)
    check('the end application\'s API is flagged: dependent logic may be impacted', impacts() == 1
          and '⚠ dependent logic' in pg.text_content('#vworld .ibadge text') and pg.locator('#vworld rect.pcont.impact').count() == 1)
    check('pill says passed on untouched', 'untouched' in pg.inner_text('#vworld .ripple-pill'))
    click('#vworld .ripple-pill'); click('#vworld .ripple-card [data-ripple=pass]'); click('#vworld .ripple-card [data-code=yes]')
    check('passed on with a code change: v1 Δ and ⚠ together', deltas() == 1 and impacts() == 1)
    with pg.expect_download() as dl: pg.click('#exportBtn')
    dl.value.save_as(D + 'r.json'); f = json.load(open(D + 'r.json'))
    check('export includes the ripple choice', f['ripples'] == [{'block': 1, 'choice': 'pass', 'code': True}])
    pg.keyboard.press('Control+z')
    check('undo goes back one ripple step', any(d.get('kind') == 'ripple' for d in dec()) and impacts() == 0)
    pg.keyboard.press('Control+y')
    check('redo re-applies it', deltas() == 1 and impacts() == 1)
    pg.click('#clearCanvas'); pg.click('#confirmOk')
    pg.set_input_files('#importFile', D + 'r.json'); pg.wait_for_timeout(300)
    check('import restores the ripple markers', deltas() == 1 and impacts() == 1)
    removed = ev("(()=>{const c=window.__debug.chainOrder(); window.__debug.removeVersion(c[1].dataset.id); return window.__debug.ripples().asks.length})()")
    check('removing the source version removes the ripple', removed == 0)

    # ---------- upstream ripple ----------
    flow('api-to-process', 'process-to-api')
    drop('p2a-contract-switch', 1)
    r = [d for d in dec() if d.get('kind') == 'ripple']
    check('Target API v2 · same Process ripples upstream to API-to-Process', len(r) == 1 and r[0]['index'] == 0 and r[0]['side'] == 'upstream')
    check('passing it on upstream lands on the API\'s callers', 'callers' in pg.inner_text('#vworld .ripple-card [data-ripple=pass]'))
    click('#vworld .ripple-card [data-ripple=pass]'); click('#vworld .ripple-card [data-code=yes]')
    check('the exposed API is flagged (its consumers are impacted)', impacts() == 1 and ev("[...window.__debug.ripples().impact]") == [ev("window.__debug.chainOrder()[0].dataset.id") + ':in'])

    flow('process-to-publish', 'consume-to-process', 'process-to-api')
    drop('p2a-contract-switch', 2)
    click('#vworld .ripple-card [data-ripple=pass]'); click('#vworld .ripple-card [data-code=no]')
    forced = [d for d in dec() if d.get('passed')]
    check('passed on upstream to a topic: Consume-to-Process must version its topic',
          len(forced) == 1 and forced[0]['index'] == 1 and forced[0]['options'] == ['c2p-contract-parallel', 'c2p-contract-dual', 'c2p-contract-switch'])
    check('…and its card says the change was passed on', 'passed on' in pg.inner_text('#vworld .decision-card:not(.ripple-card)'))

    flow('api-to-process', 'process-to-publish')
    drop('a2p-contract-shared', 0)
    click('#vworld .ripple-card [data-ripple=pass]'); click('#vworld .ripple-card [data-code=yes]')
    forced = [d for d in dec() if d.get('passed')]
    check('API v2 · shared Process passed on downstream: Process-to-Publish offers its topic versions (schema ripple)',
          len(forced) == 1 and forced[0]['options'] == ['p2t-contract-parallel', 'p2t-contract-switch'])

    # ---------- calling application of an exposed API ----------
    pg.goto(URL)
    ev("window.__debug.append('api-to-process')")
    check('placing an exposed API at the start asks whether an end application calls it',
          pg.locator('#world .caller-card').count() == 1 and pg.locator('#world .caller-card [data-caller]').count() == 2)
    pg.click('#world .caller-card [data-caller=no]')
    check('No: nothing added, card closes', pg.locator('.caller-card').count() == 0 and pg.locator('#world .caller-node').count() == 0)
    ev("window.__debug.append('process-to-api')")
    check('not asked again when building on', pg.locator('.caller-card').count() == 0)
    pg.locator('#world .flow-layer .node[data-type=api]').first.click()
    check('clicking the API\'s open left side asks again (add a caller later)', pg.locator('#world .caller-card').count() == 1)
    pg.click('#world .caller-card .dc-close')
    check('× closes it', pg.locator('.caller-card').count() == 0)
    pg.locator('#world .flow-layer .node[data-type=api]').first.click()
    pg.click('#world .caller-card [data-caller=yes]')
    check('Yes: a calling application joins the API in its own CALLER container', pg.locator('#world .caller-node').count() == 1
          and 'CALLER' in ev("[...document.querySelectorAll('#world .pcont-type')].map(t=>t.textContent)"))
    check('the caller is joined to the API by a link', ev("(()=>{const c=document.querySelector('#world .caller-node').transform.baseVal.consolidate().matrix.e; return [...document.querySelectorAll('#world .flow-layer .link')].some(l=>+l.getAttribute('x1')===c)})()"))
    pg.locator('#world .pcont-label.editable').first.click()
    pg.fill('.label-editor input[name=platform]', 'Salesforce'); pg.keyboard.press('Enter')
    with pg.expect_download() as dl: pg.click('#exportBtn')
    dl.value.save_as(D + 'c.json'); f = json.load(open(D + 'c.json'))
    check('export keeps the caller and its name', f['caller'] is True and {'block': 0, 'at': 'caller', 'platform': 'Salesforce', 'asset': ''} in f['containers'])
    pg.click('#tabVersioned')
    drop('a2p-contract-parallel', 0)
    check('a new version of the exposed API flags the calling application', impacts() == 1
          and pg.locator('#vworld .caller-node.impact').count() == 1)
    pg.click('#clearCanvas'); pg.click('#confirmOk')
    pg.set_input_files('#importFile', D + 'c.json'); pg.wait_for_timeout(300)
    check('import restores the caller without asking again', pg.locator('#world .caller-node').count() == 1 and pg.locator('.caller-card').count() == 0)
    pg.click('#tabBaseFlow')
    l = ev("parseFloat(window.__debug.chainOrder()[0].style.left)")
    ev(f"window.__debug.attachToChain(window.__debug.templatesById['process-to-api'], {l - 300}, 300)")
    check('a block added in front of the API removes the caller', pg.locator('#world .caller-node').count() == 0 and ev("Object.keys(window.__debug.callers()).length") == 0)
    check('…and the new start (a process) is not asked about', pg.locator('.caller-card').count() == 0)

    pg.goto(URL)
    ev("window.__debug.append('api-to-process')")
    pg.mouse.click(1300, 860)
    check('clicking empty canvas closes the question (counts as no)', pg.locator('.caller-card').count() == 0 and pg.locator('#world .caller-node').count() == 0)

    # ---------- ripple forecast ----------
    flow('process-to-publish', 'consume-to-process', 'process-to-api')
    check('no forecast before a contract change', not pg.is_visible('#forecastToggle'))
    drop('c2p-contract-dual', 1)
    check('a contract change shows the forecast toggle, best case first', pg.is_visible('#forecastToggle')
          and 'on' in pg.get_attribute('#forecastToggle [data-mode=best]', 'class') and pg.locator('#vworld .fc-band.best').count() == 1)
    fc = ev("window.__debug.forecasts()")[0]
    check('best case: absorbed at the first process, 1 block', fc['best']['stopsAtProcess'] and fc['best']['blocks'] == 1)
    check('worst case: reaches the end application, 2 blocks, 3 assets', fc['worst']['reachesEnd'] and fc['worst']['blocks'] == 2 and fc['worst']['assets'] == 3)
    check('best-case band text', 'absorbed at the first process' in pg.inner_text('#vworld .fc-band'))
    click('#forecastToggle [data-mode=worst]')
    check('toggle: only the worst case shows', pg.locator('#vworld .fc-band.worst').count() == 1 and pg.locator('#vworld .fc-band.best').count() == 0
          and 'reaches the end application' in pg.inner_text('#vworld .fc-band'))
    check('the worst case reaches further than the best case', fc['worst']['x2'] > fc['best']['x2'])
    click('#vworld .fc-band .fc-dismiss')
    check('worst case validated as not happening: only the best case stays', pg.locator('#vworld .fc-band.worst').count() == 0
          and 'worst dismissed' in pg.inner_text('#vworld .fc-band .fc-kind').lower())
    with pg.expect_download() as dl: pg.click('#exportBtn')
    dl.value.save_as(D + 'fc.json'); f = json.load(open(D + 'fc.json'))
    check('export keeps the dismissal', f['dismissedWorstCase'] == [1])
    pg.keyboard.press('Control+z')
    check('undo brings the worst case back', pg.locator('#vworld .fc-band.worst').count() == 1)
    flow('api-to-process', 'process-to-api')
    drop('p2a-contract-switch', 1)
    check('a target API change forecasts upstream', ev("window.__debug.forecasts()[0].dir") == 'up')
    drop('p2a-process-shared', 1)
    check('a process change has no forecast', not pg.is_visible('#forecastToggle'))

    # ---------- start from a description ----------
    pg.goto(URL)
    prompt = lambda t: (pg.fill('#flowPromptInput', t), pg.keyboard.press('Enter'))
    visible = lambda: ev("[...document.querySelectorAll('#quadrantGrid .palette-block:not(.off-route) .pb-label')].map(e=>e.textContent)")
    order = lambda: ev("window.__debug.chainOrder().map(b=>b.dataset.tpl)")
    prompt('file to API')
    check('"file to API": the one possible start step is placed', order() == ['file-to-process'])
    check('the library shows only the blocks on its routes', sorted(visible()) == ['File-to-Process', 'Process-to-API'])
    check('the route hint says so', pg.is_visible('#routeHint') and 'File to API' in pg.inner_text('#routeHintText'))
    pg.click('#routeHintClear')
    check('"Show all" clears the narrowing', len(visible()) == 8 and not pg.is_visible('#routeHint'))
    pg.goto(URL)
    prompt('API to API via event')
    check('"API to API via event": two blocks can start it, so nothing is placed', order() == [] and 'More than one block' in pg.inner_text('#flowPromptMsg'))
    check('…the library is narrowed to the blocks on those routes', sorted(visible()) == sorted(
          ['API-to-Process', 'API-to-Publish', 'Process-to-Publish', 'Consume-to-Process', 'Process-to-API', 'Consume-to-API']))
    prompt('hello there')
    check('gibberish: nothing changes, clickable end-to-end examples are offered',
          order() == [] and 'Couldn' in pg.inner_text('#flowPromptMsg') and pg.locator('.fp-example').count() == 6)
    exs = ev("[...document.querySelectorAll('.fp-example')].map(e=>e.textContent.toLowerCase())")
    check('examples are only end-to-end scenarios (never a topic as start or end)', all(' to ' in e and 'topic' not in e for e in exs))
    pg.locator('.fp-example', has_text='API to file').first.click()
    check('clicking an example runs it', pg.input_value('#flowPromptInput') == 'API to file' and order() == ['api-to-process'])
    pg.mouse.click(1300, 860)
    prompt('file')
    check('only a source: asks where it should go, with matching examples', 'Where should it go' in pg.inner_text('#flowPromptMsg')
          and all(e.lower().startswith('file') for e in ev("[...document.querySelectorAll('.fp-example')].map(e=>e.textContent)")))
    prompt('API to topic')
    check('a topic is never an end: "API to topic" asks where to', 'Where should it go' in pg.inner_text('#flowPromptMsg'))
    prompt('file to file')
    check('canvas already has a flow: nothing placed, library narrowed', order() == ['api-to-process'] and 'nothing was placed' in pg.inner_text('#flowPromptMsg'))
    ev("window.__debug.chainOrder()[0].click()")
    pg.click('#flowPromptInput'); pg.keyboard.press('Delete')
    check('typing in the description box never deletes blocks', len(order()) == 1)
    pg.click('#tabVersioned')
    check('the description box belongs to Base Flow Design only', not pg.is_visible('#flowPrompt') and not pg.is_visible('#routeHint'))

    check('no page errors', not errs); print(errs)
    br.close()
print(sum(res), '/', len(res))
