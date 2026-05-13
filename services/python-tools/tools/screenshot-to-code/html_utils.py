from config import FONT_INJECT, logger


def _clean_html(raw: str) -> str:
    import re as _re
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    lower = raw.lower()
    for tag in ("<!doctype", "<html"):
        idx = lower.find(tag)
        if idx != -1:
            raw = raw[idx:]
            lower = raw.lower()
            break
    # Issue 15: locate </head> safely — only match the real tag, not one inside
    # a <script> block or string literal. Strategy: find the first </head> that
    # appears BEFORE any <script> opener, which is where the real head closes.
    script_start = lower.find("<script")
    head_close   = lower.find("</head>")
    if head_close != -1 and (script_start == -1 or head_close < script_start):
        raw = raw[:head_close] + FONT_INJECT + raw[head_close:]
    elif "<head>" in lower:
        insert_at = lower.find("<head>") + len("<head>")
        raw = raw[:insert_at] + FONT_INJECT + raw[insert_at:]
    return raw


def _stitch_html_sections(sections: list[str]) -> str:
    if len(sections) == 1:
        return sections[0]
    first      = sections[0]
    head_start = first.lower().find("<head>")
    head_end   = first.lower().find("</head>")
    shared_head = first[head_start:head_end + len("</head>")] if head_start != -1 else "<head></head>"
    body_parts = []
    for i, html in enumerate(sections):
        body_start = html.lower().find("<body")
        body_end   = html.lower().rfind("</body>")
        if body_start != -1 and body_end != -1:
            inner_start = html.find(">", body_start) + 1
            body_parts.append(
                f'<!-- SECTION {i+1} -->\n<div class="slice-section">\n'
                + html[inner_start:body_end].strip()
                + "\n</div>"
            )
        else:
            body_parts.append(f'<!-- SECTION {i+1} -->\n{html}')
    stitched = (
        '<!DOCTYPE html>\n<html lang="en">\n'
        + shared_head + "\n"
        + "<body>\n"
        + "\n".join(body_parts)
        + "\n</body>\n</html>"
    )
    logger.info("[Stitch] Merged %d sections (%d chars)", len(sections), len(stitched))
    return stitched


def _inject_upload_script(html: str) -> str:
    script = """
<script>
(function(){
  var swaps=window.__imageSwaps=window.__imageSwaps||{};
  var hist=window.__imageHistory=window.__imageHistory||[];
  var tip=null;
  function showTip(e){
    if(!tip){tip=document.createElement('div');
      tip.style.cssText='position:fixed;z-index:99999;background:#1e293b;color:#fff;font-size:11px;padding:3px 8px;border-radius:4px;pointer-events:none;white-space:nowrap;transition:opacity .1s';
      document.body.appendChild(tip);}
    tip.textContent=e.currentTarget._tipText||'Click to replace';
    tip.style.display='block';
  }
  function moveTip(e){if(tip){tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY-28)+'px';}}
  function hideTip(){if(tip)tip.style.display='none';}
  function openPicker(cb){
    var inp=document.createElement('input');inp.type='file';inp.accept='image/*';
    inp.onchange=function(e){var f=e.target.files[0];if(!f)return;
      var r=new FileReader();r.onload=function(ev){cb(ev.target.result);};r.readAsDataURL(f);};
    inp.click();
  }
  function pushHist(el,prev){hist.push({el:el,prev:prev});if(hist.length>20)hist.shift();}
  document.addEventListener('keydown',function(e){
    if((e.ctrlKey||e.metaKey)&&e.key==='z'){e.preventDefault();
      var entry=hist.pop();if(!entry)return;
      if(entry.el.tagName==='IMG')entry.el.src=entry.prev;
      else entry.el.style.backgroundImage=entry.prev;}
  });
  function wireImg(img,idx){
    if(img.dataset.wired)return;img.dataset.wired='1';
    img.style.cursor='pointer';
    img._tipText='Click to replace image';
    img.addEventListener('mouseenter',function(e){img.style.outline='2px solid #3b82f6';img.style.outlineOffset='2px';showTip(e);});
    img.addEventListener('mousemove',moveTip);
    img.addEventListener('mouseleave',function(){img.style.outline='';img.style.outlineOffset='';hideTip();});
    img.addEventListener('click',function(e){
      e.stopPropagation();
      var prev=img.src;
      openPicker(function(d){
        pushHist(img,prev);
        img.src=d;
        swaps[idx]=d;
        // Strip rigid Tailwind size classes that distort product images
        img.className=img.className.replace(/\b(w-\d+|h-\d+|w-full|h-full)\b/g,'').trim();
        // Bulletproof scaling so any image fits its container
        img.style.objectFit='contain';
        img.style.objectPosition='center';
        img.style.maxWidth='100%';
        img.style.maxHeight='100%';
        // Immediately sync the updated DOM (with new Base64) to the React parent
        // Issue 3 fix: use restricted origin same as edit script
        var _upOrigin = window.__allowedOrigin ||
          (document.referrer ? new URL(document.referrer).origin : '*');
        window.parent.postMessage({type:'html-snapshot',html:document.documentElement.outerHTML}, _upOrigin);
      });
    });
  }
  function wireBg(el){
    if(el.dataset.bgWired)return;
    var bg=el.style.backgroundImage||getComputedStyle(el).backgroundImage;
    if(!bg||bg==='none'||bg.indexOf('url(')<0)return;
    el.dataset.bgWired='1';
    if(getComputedStyle(el).position==='static')el.style.position='relative';
    var btn=document.createElement('button');
    btn.innerHTML='&#128247;';
    btn.style.cssText='position:absolute;bottom:4px;right:4px;z-index:10;width:24px;height:24px;background:rgba(0,0,0,.6);border:none;border-radius:4px;cursor:pointer;font-size:13px;line-height:1;';
    btn._tipText='Click to replace background';
    btn.addEventListener('mouseenter',showTip);btn.addEventListener('mousemove',moveTip);btn.addEventListener('mouseleave',hideTip);
    btn.addEventListener('click',function(e){e.stopPropagation();
      var prev=el.style.backgroundImage;
      openPicker(function(d){pushHist(el,prev);el.style.backgroundImage='url('+d+')';});});
    el.appendChild(btn);
  }
  function scanAll(){
    document.querySelectorAll('img').forEach(function(img,i){wireImg(img,i);});
    document.querySelectorAll('*').forEach(wireBg);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',scanAll);else scanAll();
  new MutationObserver(function(muts){
    muts.forEach(function(m){
      m.addedNodes.forEach(function(n){
        if(!n.querySelectorAll)return;
        if(n.tagName==='IMG')wireImg(n,Date.now());
        n.querySelectorAll('img').forEach(function(img,i){wireImg(img,i+10000);});
        wireBg(n);n.querySelectorAll('*').forEach(wireBg);
      });
    });
  }).observe(document.body,{childList:true,subtree:true});
})();
</script>"""
    if '</body>' in html.lower():
        idx = html.lower().rfind('</body>')
        return html[:idx] + script + html[idx:]
    return html + script


def _inject_edit_script(html: str) -> str:
    script = """
<script>
(function(){
  // Issue 3 fix: restrict postMessage to the parent origin, not wildcard.
  // The parent sets window.__allowedOrigin via a one-time init message before
  // any toolbar interaction.  Fall back to the referrer origin as a safe default.
  var _allowedOrigin = window.__allowedOrigin ||
    (document.referrer ? new URL(document.referrer).origin : '*');
  window.addEventListener('message', function(e) {
    if (e.origin !== window.location.origin) return;
    if (e.data && e.data.type === '__init_origin__') {
      _allowedOrigin = e.origin;
      window.__allowedOrigin = e.origin;
    }
  }, { once: false });
  function _postToParent(data) { window.parent.postMessage(data, _allowedOrigin); }
  var sel=null;
  document.addEventListener('click',function(e){
    // deselect previous
    if(sel){sel.style.boxShadow='';sel.removeAttribute('data-edit-sel');}
    sel=e.target;
    sel.setAttribute('data-edit-sel','1');
    sel.style.boxShadow='inset 0 0 0 2px #8b5cf6';
    var r=sel.getBoundingClientRect();
    _postToParent({type:'element-select',
      tag:sel.tagName.toLowerCase(),
      classes:(sel.getAttribute('class')||''),
      text:(sel.textContent||'').trim().slice(0,300),
      rect:{top:r.top,left:r.left,width:r.width,height:r.height}});
  },true);
  window.addEventListener('message',function(e){
    if (e.origin !== window.location.origin) return;
    var m=e.data;if(!m||!m.type)return;
    if(m.type==='apply-style'&&sel){sel.style[m.property]=m.value;}
    else if(m.type==='apply-text'&&sel){
      // Use TreeWalker to target only text nodes — never destroys embedded SVGs/icons
      var walker=document.createTreeWalker(sel,NodeFilter.SHOW_TEXT,null,false);
      var firstText=walker.nextNode();
      if(firstText){firstText.nodeValue=m.value;}else{sel.textContent=m.value;}
    }
    else if(m.type==='get-html'){_postToParent({type:'html-snapshot',html:document.documentElement.outerHTML});}
    else if(m.type==='reset'){window.location.reload();}
  });
})();
</script>"""
    if '</body>' in html.lower():
        idx = html.lower().rfind('</body>')
        return html[:idx] + script + html[idx:]
    return html + script
