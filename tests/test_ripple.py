"""Pattern Bench — ripple of contract changes, calling application, v1 Δ marks, print, start from a description.
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
    pg.fill('.label-editor input[name=name]', 'Salesforce'); pg.keyboard.press('Enter')
    with pg.expect_download() as dl: pg.click('#exportBtn')
    dl.value.save_as(D + 'c.json'); f = json.load(open(D + 'c.json'))
    check('export keeps the caller and its name', f['caller'] is True and {'block': 0, 'at': 'caller', 'name': 'Salesforce', 'process': ''} in f['containers'])
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

    # ---------- non-breaking change marked by hand (v1 Δ, no parallel version) ----------
    flow('api-to-process', 'process-to-api')
    pg.locator('#world .flow-layer .node[data-type=api]').nth(1).click()
    check('the version card offers to mark a non-breaking change', pg.locator('#world .target-card .dc-mark').count() == 1)
    pg.click('#world .target-card .dc-mark')
    check('marking opens the copy and shows v1 Δ on that connector, no parallel version', pg.is_visible('#versionPane') and deltas() == 1
          and ev("Object.keys(window.__debug.versionOverrides()).length") == 0)
    pg.locator('#vworld .flow-layer .node[data-type=process]').first.click()
    pg.click('#vworld .target-card .dc-mark')
    check('any symbol can be marked (a process too)', deltas() == 2 and len(ev("window.__debug.marks()")) == 2)
    with pg.expect_download() as dl: pg.click('#exportBtn')
    dl.value.save_as(D + 'm.json'); f = json.load(open(D + 'm.json'))
    check('export keeps the marks', sorted(m['at'] for m in f['marks']) == ['out', 'out'])
    pg.keyboard.press('Control+z')
    check('undo removes the last mark', deltas() == 1)
    pg.locator('#vworld .flow-layer .node[data-type=api]').nth(1).click()
    check('a marked connector offers to remove the mark', 'Remove' in pg.inner_text('#vworld .target-card .dc-mark'))
    pg.click('#vworld .target-card .dc-mark')
    check('removing the last mark closes the copy', not pg.is_visible('#versionPane') and deltas() == 0)
    pg.click('#clearCanvas'); pg.click('#confirmOk')
    pg.set_input_files('#importFile', D + 'm.json'); pg.wait_for_timeout(300)
    check('import restores the marks', deltas() == 2)
    check('no forecast bands or toggle any more', pg.locator('.fc-band, #forecastToggle').count() == 0)

    # ---------- one-page print ----------
    ev("(()=>{ window.__restore = window.__debug.printAssessment(true); return 1; })()")
    check('print sheet holds the base flow, the copy and the four lists', pg.locator('.print-host .ps-pic').count() == 2
          and pg.locator('.print-host .ps-cols h2').count() == 4 and 'non-breaking change, marked' in pg.inner_text('.print-host .ps-cols'))
    pg.emulate_media(media='print')
    pg.pdf(path=D + 'a.pdf', format='A4', landscape=True, print_background=True)
    pdf = open(D + 'a.pdf', 'rb').read()
    check('it prints on exactly one A4 page', pdf.count(b'/Type /Page') - pdf.count(b'/Type /Pages') == 1)
    pg.emulate_media(media='screen'); ev("window.__restore()")
    check('after printing, the sheet is gone and the theme is back', pg.locator('.print-host .print-sheet').count() == 0
          and not ev("document.body.classList.contains('light-theme')"))

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
    check('"Show all" clears the narrowing', len(visible()) == 9 and not pg.is_visible('#routeHint'))
    pg.goto(URL)
    prompt('API to API via event')
    check('"API to API via event": two blocks can start it, so nothing is placed', order() == [] and 'More than one block' in pg.inner_text('#flowPromptMsg'))
    check('…the library is narrowed to the blocks on those routes', sorted(visible()) == sorted(
          ['API-to-Process', 'API-to-Publish', 'API-to-API', 'Process-to-Publish', 'Consume-to-Process', 'Process-to-API', 'Consume-to-API']))
    prompt('hello there')
    check('gibberish: nothing changes, clickable end-to-end examples are offered',
          order() == [] and 'Couldn' in pg.inner_text('#flowPromptMsg') and pg.locator('.fp-example').count() == 6)
    exs = ev("[...document.querySelectorAll('.fp-example')].map(e=>e.textContent.toLowerCase())")
    check('examples are only end-to-end scenarios (never a topic as start or end)', all(' to ' in e and 'topic' not in e for e in exs))
    pg.locator('.fp-example', has_text='file to file').first.click()
    check('clicking an example runs it', pg.input_value('#flowPromptInput') == 'file to file' and order() == ['file-to-process'])
    pg.mouse.click(1300, 860)
    prompt('file')
    check('only a source: asks where it should go, with matching examples', 'Where should it go' in pg.inner_text('#flowPromptMsg')
          and all(e.lower().startswith('file') for e in ev("[...document.querySelectorAll('.fp-example')].map(e=>e.textContent)")))
    prompt('API to topic')
    check('a topic is never an end: "API to topic" asks where to', 'Where should it go' in pg.inner_text('#flowPromptMsg'))
    prompt('file to API')
    check('canvas already has a flow: nothing placed, library narrowed', order() == ['file-to-process'] and 'nothing was placed' in pg.inner_text('#flowPromptMsg'))
    ev("window.__debug.chainOrder()[0].click()")
    pg.click('#flowPromptInput'); pg.keyboard.press('Delete')
    check('typing in the description box never deletes blocks', len(order()) == 1)
    pg.click('#tabVersioned')
    check('the description box belongs to Base Flow Design only', not pg.is_visible('#flowPrompt') and not pg.is_visible('#routeHint'))

    check('no page errors', not errs); print(errs)
    br.close()
print(sum(res), '/', len(res))
