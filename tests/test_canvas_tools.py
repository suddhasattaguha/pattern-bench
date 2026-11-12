"""Pattern Bench — build tools, platform containers, click-to-version, Consume-to-Process versions.
Run: python3 tests/test_canvas_tools.py"""
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
    def flow(*tpls):
        pg.goto(URL)
        for t in tpls:
            ev(f"(()=>{{window.__debug.append('{t}'); window.__debug.recordHistory();}})()")
        pg.mouse.click(1300, 860)
    order = lambda: ev("window.__debug.chainOrder().map(b=>b.dataset.tpl)")
    edges = lambda: ev("(()=>{const c=window.__debug.chainOrder(); const f=c[0], l=c[c.length-1]; return [parseFloat(f.style.left), parseFloat(l.style.left)+parseFloat(l.style.width)]})()")
    click_block = lambda i: pg.mouse.click(*ev(f"(()=>{{const c=window.__debug.chainOrder(); const r=c[{i}<0?c.length+{i}:{i}].getBoundingClientRect();return [r.x+r.width/2,r.y+r.height-14]}})()"))
    avail = lambda: ev("[...document.querySelectorAll('#quadrantGrid .palette-block:not(.unavailable) .pb-label')].map(e=>e.textContent)")
    sugg = lambda: sorted(ev("[...document.querySelectorAll('.version-card.suggested .pb-label')].map(e=>e.textContent)"))

    # ---------- drop side ----------
    base = ('process-to-publish', 'consume-to-process', 'process-to-api')
    flow(*base); l, r = edges()
    ev(f"window.__debug.attachToChain(window.__debug.templatesById['api-to-process'],{l-60},300)")
    check('block that fits both ends attaches to the start when dropped near it', order() == ['api-to-process', *base])
    flow(*base); l, r = edges()
    ev(f"window.__debug.attachToChain(window.__debug.templatesById['api-to-process'],{r+60},300)")
    check('…and to the end when dropped near the end', order() == [*base, 'api-to-process'])

    # ---------- select an end, then drag ----------
    flow(*base)
    normal = avail()
    check('Consume-to-Publish is no longer in the library', ev("[...document.querySelectorAll('#quadrantGrid .pb-label')].every(e=>e.textContent!=='Consume-to-Publish')") and not ev("!!window.__debug.templatesById['consume-to-publish']"))
    click_block(0)
    check('selecting the first block narrows the library to what fits the start', avail() == ['API-to-Process', 'Consume-to-Process', 'File-to-Process'])
    check('library says which end it is showing', pg.is_visible('#endHint') and 'start' in pg.inner_text('#endHintText'))
    ev("window.__debug.attachToChain(window.__debug.templatesById['api-to-process'],5000,300)")
    check('dragged block attaches to the selected end, wherever it is dropped', order()[0] == 'api-to-process')
    check('the new block stays the selected end, so building continues there', pg.is_visible('#endHint') and 'start' in pg.inner_text('#endHintText'))
    click_block(-1)
    check('selecting the last block narrows to what fits the end', avail() == ['API-to-Process', 'API-to-Publish', 'API-to-API'])
    click_block(1)
    check('selecting a middle block leaves the library unfiltered', not pg.is_visible('#endHint'))
    pg.mouse.click(1300, 860)
    check('clicking empty canvas clears the end filter', not pg.is_visible('#endHint'))
    click_block(0); pg.click('#endHintClear')
    check('"Show all" clears the end filter', not pg.is_visible('#endHint'))

    # ---------- platform containers ----------
    flow('file-to-process', 'process-to-publish', 'consume-to-process', 'process-to-api')
    types = ev("[...document.querySelectorAll('#world .pcont-label .pcont-type')].map(t=>t.textContent)")
    check('one container per asset: source file, publisher iPaaS, broker, subscriber iPaaS, target API',
          types == ['END APPLICATION', 'IPAAS', 'MESSAGE BROKER', 'IPAAS', 'END APPLICATION'])
    check('end applications have their own style', pg.locator('#world .pcont.own-external').count() == 2)
    cont = ev("[...document.querySelectorAll('#world rect.pcont')].map(r=>[+r.getAttribute('y'), +r.getAttribute('y')+ +r.getAttribute('height')])")
    tile = ev("(()=>{const b=window.__debug.chainOrder()[0]; return [parseFloat(b.style.top), parseFloat(b.style.top)+parseFloat(b.style.height)]})()")
    check('containers frame the tiles from outside (above and below)', all(c[0] < tile[0] and c[1] > tile[1] for c in cont))
    check('containers start without default names', ev("[...document.querySelectorAll('#world .pcont-name')].every(t=>t.classList.contains('empty'))"))
    pg.locator('#world .pcont-label.editable').nth(1).click()
    pg.fill('.label-editor input[name=platform]', 'SAP BTP'); pg.fill('.label-editor input[name=asset]', 'order-publisher')
    pg.keyboard.press('Enter')
    names = lambda: ev("[...document.querySelectorAll('#world .pcont-name')].map(t=>t.textContent)")
    check('naming a container shows platform · asset', names()[1] == 'SAP BTP · order-publisher')
    check('typing in the editor does not trigger canvas shortcuts', len(order()) == 4)
    pg.keyboard.press('Control+z')
    check('undo removes the name', names()[1] == '+ name')
    pg.keyboard.press('Control+y')
    check('redo restores it', names()[1] == 'SAP BTP · order-publisher')
    pg.locator('#world .pcont-label.editable').nth(1).click(); pg.keyboard.press('Escape')
    check('Escape closes the editor without changes', pg.locator('.label-editor').count() == 0 and names()[1] == 'SAP BTP · order-publisher')
    with pg.expect_download() as dl: pg.click('#exportBtn')
    dl.value.save_as(D + 'f.json'); f = json.load(open(D + 'f.json'))
    check('export includes container names', f['containers'] == [{'block': 0, 'at': 'out', 'platform': 'SAP BTP', 'asset': 'order-publisher'}])
    pg.click('#clearCanvas'); pg.click('#confirmOk')
    pg.set_input_files('#importFile', D + 'f.json'); pg.wait_for_timeout(300)
    check('import restores container names', names()[1] == 'SAP BTP · order-publisher')
    ev("window.__debug.attachToChain(window.__debug.templatesById['api-to-process'],-5000,300)")
    pg.mouse.click(1300, 860)
    check('a name survives adding a block in front of its asset', 'SAP BTP · order-publisher' in names())

    # ---------- click a connector to version it ----------
    flow('file-to-process', 'process-to-publish', 'consume-to-process', 'process-to-api')
    pg.locator('#world .flow-layer .node[data-type=topic]').click(force=True)
    check('in Base Flow Design, clicking a connector does not start versioning', ev("window.__debug.versionTarget()") is None and not pg.is_visible('#modeBanner'))
    pg.click('#tabVersioned')
    check('Versioned Artifacts tab turns versioning mode on (banner shown)', pg.is_visible('#modeBanner'))
    pg.locator('#world .flow-layer .node[data-type=topic]').click()
    check('clicking a shared topic highlights topic versions from both blocks', sugg() == sorted([
        'New Topic v2 · own Process v2', 'New Topic v2 · same Process', 'Topic v2 · own Queue + Process v2',
        'Topic v2 · same Queue subscribes to both', 'Topic v2 · same Queue switches']))
    check('the clicked connector is marked', pg.locator('#world .node.targeted').count() == 1)
    check('pop-up offers upstream and downstream', pg.locator('#world .target-card .dc-side button').count() == 2)
    pg.locator('#world .target-card .dc-side button').nth(0).click()
    check('choosing upstream narrows to Process-to-Publish', sugg() == ['New Topic v2 · own Process v2', 'New Topic v2 · same Process'])
    check('the pop-up closes once a side is chosen; the connector stays marked', pg.locator('.target-card').count() == 0 and pg.locator('#world .node.targeted').count() == 1)
    pg.locator('#world .flow-layer .node[data-type=topic]').click()
    check('clicking the connector again reopens the pop-up to switch sides', pg.locator('#world .target-card').count() == 1)
    pg.locator('#world .target-card .dc-side button').nth(0).click()
    ev("window.__debug.dropVersion('p2t-contract-switch',10,10)")
    check('a highlighted version dropped anywhere lands on that block', ev("Object.values(window.__debug.versionOverrides())") == ['p2t-contract-switch']
          and ev("window.__debug.versionOverrides()[window.__debug.chainOrder()[1].dataset.id]") == 'p2t-contract-switch')
    check('the target clears after applying', ev("window.__debug.versionTarget()") is None)
    check('the copy is now the big view; connectors are clicked there', pg.is_visible('#versionPane'))
    pg.locator('#vworld .flow-layer .node[data-type=queue]').click()
    check('a queue offers the versions where it changes with its process', sugg() == ['New Process v2 · own Queue v2', 'Topic v2 · own Queue + Process v2'])
    pg.click('#vworld .target-card .dc-close')
    check('the × closes the pop-up and clears the selection', ev("window.__debug.versionTarget()") is None and pg.locator('.target-card').count() == 0)
    pg.locator('#vworld .flow-layer .node[data-type=queue]').click()
    pg.keyboard.press('Escape')
    check('Escape clears the target', ev("window.__debug.versionTarget()") is None and pg.locator('.target-card').count() == 0)
    pg.locator('#vworld .flow-layer .node[data-type=file]').click()
    check('a connector at the edge has one block and no side choice', pg.locator('#vworld .target-card .dc-side').count() == 0
          and sugg() == ['New File v2 · own Process v2', 'New File v2 · shared Process'])
    pg.mouse.click(950, 170)
    check('clicking empty canvas clears the target', ev("window.__debug.versionTarget()") is None)
    pg.click('#tabBaseFlow')
    check('back in Base Flow Design, versioning mode is off', not pg.is_visible('#modeBanner'))
    pg.click('#tabVersioned')
    pg.locator('#vworld .flow-layer .node[data-type=process]').nth(0).click()
    check('connectors in the versioned copy are clickable too', ev("window.__debug.versionTarget() && window.__debug.versionTarget().pane") == 'copy'
          and pg.locator('#vworld .target-card').count() == 1)

    # ---------- Consume-to-Process versions ----------
    flow('process-to-publish', 'consume-to-process', 'process-to-api')
    for vid, queues in [('c2p-contract-parallel', 2), ('c2p-contract-dual', 1), ('c2p-contract-switch', 1),
                        ('c2p-process-switch', 1), ('c2p-process-parallel', 2)]:
        rr = ev("(()=>{const r=window.__debug.chainOrder()[1].getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()")
        ev(f"window.__debug.dropVersion('{vid}',{rr[0]},{rr[1]})")
        q = pg.locator('#vworld .versioned').count() == 1 and ev("document.querySelectorAll('#vworld .flow-layer .node[data-type=queue]').length")
        check(f'{vid} applies with {queues} queue lane(s)', q == queues)
    d = ev("window.__debug.decisions()")
    check('new process with own queue asks the downstream Process-to-API', [x['index'] for x in d] == [2])

    check('no page errors', not errs); print(errs)
    br.close()
print(sum(res), '/', len(res))
