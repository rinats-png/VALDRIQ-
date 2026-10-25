const app = document.querySelector('#app');
const state = {csrf:'', projects:[], project:null, page:'overview', config:{}, lead:null, interview:null};
const fields = [
  ['name','Projektname'],['offer','Dein Angebot'],['target_industries','Zielbranchen'],
  ['target_customer','Entscheider'],['geography','Zielregion'],['customer_problem','Kundenproblem'],
  ['differentiator','Differenzierung'],['price_model','Preismodell'],['lead_source','Recherchequelle'],
  ['contact_strategy','Kontaktstrategie'],['tone','Sprachstil'],['sender_name','Absendername'],
  ['sender_company','Absenderfirma'],['sender_email','Absender-E-Mail'],
  ['sender_address','Geschäftsanschrift'],['sender_site','Website']
];

function esc(value='') {return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');}
function money(x) {return x==null?'–':esc(x);}
function tag(status){const labels={new:'Neu',qualified:'Qualifiziert',contacted:'Kontaktiert',replied:'Antwort',won:'Gewonnen',lost:'Verloren',draft:'Entwurf',approved:'Freigegeben',sent:'Versandt',failed:'Fehler',sending:'Wird versandt',running:'Läuft',queued:'Wartend',done:'Fertig'};return `<span class="tag ${['failed','lost'].includes(status)?'warn':'neutral'}">${esc(labels[status]||status)}</span>`;}
function notify(message,error=false){document.querySelector('.toast')?.remove();const n=document.createElement('div');n.className='toast'+(error?' error':'');n.textContent=message;document.body.append(n);setTimeout(()=>n.remove(),4800);}
async function api(path,method='GET',body){let response;
  try{response=await fetch('/api'+path,{method,credentials:'same-origin',headers:{...(body?{'Content-Type':'application/json'}:{}),...(method!=='GET'&&state.csrf?{'X-CSRF-Token':state.csrf}:{})},body:body?JSON.stringify(body):undefined});}
  catch(e){throw new Error('Server nicht erreichbar. Ist VALDRIQ gestartet?');}
  let data;const ct=response.headers.get('content-type')||'';
  if(ct.includes('application/json')){data=await response.json();}else{data=await response.text();}
  if(!response.ok)throw new Error(data?.error||'Anfrage fehlgeschlagen');
  return data;
}
function on(id,event,handler){document.getElementById(id)?.addEventListener(event,handler);}
function brand(){return `<div class="brand"><span class="mark">V</span><span>VALDRIQ<small>LEAD INTELLIGENCE</small></span></div>`;}

async function boot(){try{
  const health=await api('/health');const auth=await api('/auth');
  if(!health.initialized)return loginScreen('setup');
  if(!auth.authenticated)return loginScreen('login');
  state.csrf=auth.csrf;
  await loadProjects();state.config=await api('/config');renderShell();
}catch(error){app.innerHTML=`<div class="login-screen"><div class="card login-card"><h2>Verbindung fehlgeschlagen</h2><p>${esc(error.message)}</p><button class="btn" id="retry">Erneut versuchen</button></div></div>`;on('retry','click',boot);}}

function loginScreen(mode){const setup=mode==='setup';app.innerHTML=`<section class="login-screen"><div class="card login-card">
  ${brand()}<div class="eyebrow">${setup?'Ersteinrichtung':'Willkommen zurück'}</div>
  <h1>${setup?'Dein Workspace beginnt hier.':'Sicher anmelden.'}</h1>
  <p>${setup?'Lege deinen Admin-Zugang an. Alle Daten bleiben in deiner Installation. Verwende mindestens 12 Zeichen für dein Passwort.':'Melde dich mit deinem Admin-Konto an.'}</p>
  <form id="auth-form"><div class="field"><label>E-Mail-Adresse</label><input name="email" type="email" autocomplete="username" placeholder="du@unternehmen.de" required></div>
  <div class="field"><label>Passwort</label><input name="password" type="password" autocomplete="${setup?'new-password':'current-password'}" minlength="${setup?'12':'1'}" required></div>
  <button class="btn primary" style="width:100%" type="submit">${setup?'Workspace einrichten':'Anmelden'} →</button></form>
  <div class="divider"></div><p class="small">Private Lead-Recherche. Kontrollierter Versand. Transparente Datenquellen.</p>
  </div></section>`;
  on('auth-form','submit',async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.currentTarget));try{const response=await api(setup?'/setup':'/login','POST',d);state.csrf=response.csrf;await loadProjects();state.config=await api('/config');renderShell();}catch(err){notify(err.message,true);}});
}

async function loadProjects(){state.projects=await api('/projects');const selected=Number(localStorage.getItem('valdriq-project'))||0;state.project=state.projects.find(p=>p.id===selected)||state.projects[0]||null;}
function pageTitle(){return {overview:['Übersicht','Deine Pipeline auf einen Blick'],guide:['Strategie-Assistent','Schritt für Schritt zur vollständigen Zielgruppenstrategie'],discover:['Lead-Recherche','Entdecke passende Unternehmen und importiere Kontaktdaten'],leads:['Lead-Management','Kontakte, Bewertung, Nachrichten und Status'],settings:['Projekteinstellungen','Strategie, Schnittstellen und Compliance']}[state.page];}
function renderShell(){app.innerHTML=`<div class="shell"><aside class="sidebar">${brand()}<div class="side-label">Workspace</div>
  <nav class="nav" id="nav">${[['overview','◫','Übersicht'],['guide','◇','Strategie-Assistent'],['discover','⌕','Lead-Recherche'],['leads','▤','Alle Leads'],['settings','⚙','Einstellungen']].map(([id,ico,label])=>`<button class="nav-btn ${state.page===id?'active':''}" data-page="${id}"><span class="nav-icon">${ico}</span>${label}</button>`).join('')}</nav>
  <div class="sidebar-bottom"><p class="footer-brand">VALDRIQ v0.1 · Local-first<br>Research → Qualify → Connect</p><button class="btn ghost mini" id="logout">Abmelden</button></div>
  </aside><main class="main"><div class="topline"><div><div class="eyebrow">WORKSPACE / ${esc(pageTitle()[0].toUpperCase())}</div><h1>${esc(pageTitle()[0])}</h1><p>${esc(pageTitle()[1])}</p></div>
  <div class="actionbar"><select class="project-select" id="project-select" aria-label="Projekt wählen"><option value="">${state.project?'Projekt wählen':'Noch kein Projekt'}</option>${state.projects.map(p=>`<option value="${p.id}" ${state.project?.id===p.id?'selected':''}>${esc(p.name)}</option>`).join('')}</select><button class="btn ghost" id="new-project">+ Projekt</button></div></div><div id="content"></div></main></div>`;
  document.querySelectorAll('[data-page]').forEach(b=>b.addEventListener('click',()=>{state.page=b.dataset.page;renderShell();}));
  on('new-project','click',()=>{state.project=null;state.page='guide';renderShell();});
  on('project-select','change',e=>{state.project=state.projects.find(x=>x.id===Number(e.target.value))||null;if(state.project)localStorage.setItem('valdriq-project',state.project.id);renderShell();});
  on('logout','click',async()=>{try{await api('/logout','POST',{});}catch(e){}state.csrf='';state.projects=[];state.project=null;loginScreen('login');});
  if(!state.project){state.page='guide';return renderWizard();}
  ({overview:renderOverview,guide:renderWizard,discover:renderDiscover,leads:renderLeads,settings:renderSettings}[state.page]||renderOverview)();
}
const content=(html)=>{document.querySelector('#content').innerHTML=html;};

async function renderWizard(){let guide=state.project?await api(`/projects/${state.project.id}/interview`):{percent:0,answered:0,total:16,next:{field:'name',question:'Wie heißt dein Vertriebsprojekt?',hint:'z. B. EIRA – B2B Vertrieb'},missing:[],recommendations:[]};state.interview=guide;
  if(guide.complete){content(`<div class="wizard"><div class="card"><div class="eyebrow">Strategie vollständig</div><h2>Bereit für qualifizierte Leads.</h2><p>Alle ${guide.total} Strategieangaben sind hinterlegt. Du kannst sie jederzeit ändern.</p><div class="progress"><div style="width:100%"></div></div><div class="divider"></div><div class="actionbar"><button class="btn primary" id="to-discover">Leads recherchieren →</button><button class="btn" id="to-settings">Strategie bearbeiten</button></div></div></div>`);
    on('to-discover','click',()=>{state.page='discover';renderShell();});on('to-settings','click',()=>{state.page='settings';renderShell();});return;}
  const question=guide.next;content(`<div class="wizard"><div class="steps"><span class="dot done"></span><span>Strategie</span><span>·</span><span>${guide.answered} von ${guide.total} beantwortet</span><span style="margin-left:auto">${guide.percent}%</span></div>
  <div class="progress"><div style="width:${guide.percent}%"></div></div><div class="card" style="margin-top:19px"><div class="eyebrow">FRAGE ${guide.answered+1} / ${guide.total}</div>
  <h2>${esc(question.question)}</h2><p>Je präziser deine Angaben, desto besser lassen sich passende Unternehmen priorisieren und Nachrichten erstellen.</p>
  <form id="wizard-form"><div class="field"><label>${esc(fields.find(f=>f[0]===question.field)?.[1]||question.field)}</label>
  ${['offer','customer_problem','differentiator','contact_strategy'].includes(question.field)?`<textarea id="wizard-value" required placeholder="${esc(question.hint)}"></textarea>`:
    question.field==='lead_source'?`<select id="wizard-value"><option value="google_places">Google Places API</option><option value="scraper_kit">Google Maps Scraper Kit</option><option value="csv">CSV-Import</option><option value="manual">Manuelle Erfassung</option></select>`:
    `<input id="wizard-value" ${question.field==='sender_email'?'type="email"':'type="text"'} required placeholder="${esc(question.hint)}" maxlength="600">`}
  <p class="helper">${esc(question.hint)}</p></div><div class="actionbar"><button class="btn primary" type="submit">Speichern & weiter →</button><button class="btn ghost" type="button" id="wizard-later">Später fortsetzen</button></div></form></div>
  ${guide.recommendations.length?`<div class="callout" style="margin-top:20px">${guide.recommendations.map(esc).join('<br>')}</div>`:''}</div>`);
  on('wizard-form','submit',async e=>{e.preventDefault();const answer=document.querySelector('#wizard-value').value.trim();if(!answer)return notify('Bitte beantworte diese Frage.',true);try{
      if(!state.project){const v=await api('/projects','POST',{name:answer});localStorage.setItem('valdriq-project',v.id);await loadProjects();}else{await api(`/projects/${state.project.id}`,'PATCH',{[question.field]:answer});state.project[question.field]=answer;}
      renderWizard();}catch(e){notify(e.message,true);}});
  on('wizard-later','click',()=>{state.page='overview';renderShell();});
}

async function renderOverview(){const p=state.project;const [metrics,guide,jobs,leads]=await Promise.all([api(`/projects/${p.id}/metrics`),api(`/projects/${p.id}/interview`),api(`/projects/${p.id}/jobs`),api(`/projects/${p.id}/leads`)]);
  const stat=[['Erfasste Leads',metrics.leads,'In deiner Datenbank'],['Top-Matches',metrics.qualified,'Score ab 60'],['Versandte E-Mails',metrics.sent,'Nur nach Freigabe'],['Antworten',metrics.replied,'Manuell markiert']];
  content(`<div class="grid stats">${stat.map(([label,note,hint])=>`<div class="card metric"><div class="label">${label}</div><div class="value">${note}</div><div class="change">${hint}</div></div>`).join('')}</div>
  <div class="card hero"><div><div class="eyebrow">DEIN NÄCHSTER SCHRITT</div><h2>${guide.complete?'Starte eine präzise, nachvollziehbare Lead-Recherche.':'Deine Vertriebsstrategie braucht noch einige Angaben.'}</h2>
  <p>${guide.complete?'Suche Unternehmen nach Branche und Standort. Prüfe die Ergebnisse, bevor du Nachrichten erstellst.':`${guide.answered} von ${guide.total} Fragen beantwortet. Der Assistent führt dich durch die fehlenden Details.`}</p>
  <button class="btn primary" id="next-step">${guide.complete?'Recherche öffnen':'Strategie vervollständigen'} →</button></div><div class="orb">⌕</div></div>
  <div class="grid two" style="margin-top:20px"><div class="card"><div class="section-title" style="margin:0 0 15px"><h2>Strategie-Check</h2><span class="tag ${guide.complete?'':'warn'}">${guide.percent}% vollständig</span></div><div class="progress"><div style="width:${guide.percent}%"></div></div>
  <p style="margin-top:15px">${guide.complete?'Alle Grundlagen sind hinterlegt.':'Nächste Frage: '+esc(guide.next?.question)}</p><button class="btn mini" id="edit-strategy">Strategie ansehen</button></div>
  <div class="card"><h2>Letzte Recherche</h2>${jobs.length?jobs.slice(0,3).map(j=>`<p style="margin:8px 0">${tag(j.status)} <strong>${esc(j.query)}</strong> · ${esc(j.city)}<br><span class="small">${j.imported} importiert ${j.error?'· '+esc(j.error):''}</span></p>`).join(''):'<p>Noch keine Recherche gestartet.</p>'}<button class="btn mini" id="research">Neue Recherche</button></div></div>
  <div class="section-title"><h2>Leads mit dem höchsten Potenzial</h2><button class="btn mini ghost" id="all-leads">Alle Leads anzeigen →</button></div>${leadTable(leads.slice(0,5))}`);
  on('next-step','click',()=>{state.page=guide.complete?'discover':'guide';renderShell();});on('edit-strategy','click',()=>{state.page='settings';renderShell();});on('research','click',()=>{state.page='discover';renderShell();});on('all-leads','click',()=>{state.page='leads';renderShell();});bindLeadRows();
}
function leadTable(leads){if(!leads.length)return `<div class="card empty"><div class="glyph">⌕</div><h3>Hier erscheinen deine Leads.</h3><p>Starte eine Recherche oder importiere eine CSV-Datei.</p></div>`;
  return `<div class="table-wrap"><table><thead><tr><th>Unternehmen</th><th>Branche / Ort</th><th>Kontakt</th><th>Score</th><th>Status</th><th>Quelle</th></tr></thead><tbody>
  ${leads.map(l=>`<tr data-lead="${l.id}"><td><strong>${esc(l.business)}</strong><br><span class="small">${esc(l.website||'Website nicht bekannt')}</span></td>
  <td>${esc(l.industry||'–')}<br><span class="small">${esc(l.address||'–')}</span></td><td>${esc(l.contact_name||l.email||l.phone||'–')}</td>
  <td><span class="score ${l.score<40?'low':l.score<60?'mid':''}">${l.score}/100</span></td><td>${tag(l.status)}</td><td><span class="small">${esc(l.source)}</span></td></tr>`).join('')}</tbody></table></div>`;
}
function bindLeadRows(){document.querySelectorAll('[data-lead]').forEach(row=>row.addEventListener('click',()=>showLead(Number(row.dataset.lead))));}

async function renderDiscover(){const p=state.project;const [jobs,guide]=await Promise.all([api(`/projects/${p.id}/jobs`),api(`/projects/${p.id}/interview`)]);
  content(`<div class="grid two"><div class="card"><div class="eyebrow">01 / DATEN FINDEN</div><h2>Unternehmen recherchieren</h2><p>Suche nach Branche und Standort. Ergebnisse werden dedupliziert und bewertet.</p>
  <form id="discover-form"><div class="field"><label>Quelle</label><select name="provider"><option value="google_places">Google Places API ${state.config.google_places?'●':'(nicht konfiguriert)'}</option><option value="scraper_kit">Google Maps Scraper Kit ${state.config.scraper_kit?'●':'(nicht konfiguriert)'}</option></select></div>
  <div class="field"><label>Branche / Suchbegriff</label><input name="query" placeholder="z. B. Zahnarztpraxis" value="${esc(p.target_industries.split(',')[0]||'')}" required maxlength="140"></div>
  <div class="field"><label>Stadt / Region</label><input name="city" value="${esc(p.geography.split(',')[0]||'')}" placeholder="z. B. Frankfurt am Main" required maxlength="120"></div>
  <div class="form-grid"><div class="field"><label>Max. Treffer</label><input name="limit" type="number" min="1" max="200" value="20"></div><div class="field"><label>Scraper-Raster</label><select name="grid"><option value="1">1 × 1</option><option value="2">2 × 2</option><option value="3">3 × 3</option></select></div></div>
  <button class="btn primary" type="submit">Recherche starten →</button></form><div class="divider"></div>
  <div class="callout">Google Places benötigt einen API-Key und unterliegt Nutzungs-/Speicherbedingungen. Der externe Scraper ist optional, unterliegt ebenfalls den Plattformbedingungen und muss separat installiert werden. Gefundene E-Mail-Adressen sind keine Werbeeinwilligung.</div></div>
  <div class="card"><div class="eyebrow">02 / BESTEHENDE KONTAKTE</div><h2>CSV importieren</h2><p>Für bereits vorhandene, rechtmäßig erfasste Geschäftskontakte oder Exporte aus dem Google Maps Scraper Kit.</p>
  <form id="csv-form"><div class="field"><label>CSV-Datei</label><input type="file" id="csv-file" accept=".csv,text/csv" required></div><p class="small">Unterstützte Spalten: business/title, email/emails, phone, website, industry/category, address, contact_name, notes, evidence. Max. 2 MB bzw. 1000 Datensätze.</p><button class="btn" type="submit">CSV importieren</button></form>
  <div class="divider"></div><h3>Rechercheübersicht</h3><div id="job-list">${renderJobList(jobs)}</div><button class="btn mini ghost" id="refresh-jobs">Status aktualisieren</button></div></div>
  ${!guide.complete?`<div class="callout" style="margin-top:18px">Deine Strategie ist erst zu ${guide.percent}% vollständig. Die Recherche ist möglich, aber dein Lead-Scoring und E-Mail-Entwürfe werden erst mit vollständigem Profil wirklich aussagekräftig.</div>`:''}`);
  on('discover-form','submit',async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.currentTarget));try{const res=await api(`/projects/${p.id}/discover`,'POST',{...d,limit:Number(d.limit),grid:Number(d.grid)});notify('Recherche gestartet (Job '+res.job_id+').');await refreshJobs();}catch(err){notify(err.message,true);}});
  on('csv-form','submit',async e=>{e.preventDefault();const file=document.querySelector('#csv-file').files?.[0];if(!file)return;if(file.size>2000000)return notify('Maximal 2 MB pro CSV.',true);try{const result=await api(`/projects/${p.id}/import`,'POST',{csv:await file.text()});notify(`${result.imported} importiert, ${result.duplicates} Duplikate.`);e.currentTarget.reset();}catch(err){notify(err.message,true);}});
  on('refresh-jobs','click',refreshJobs);
}
function renderJobList(jobs){return jobs.length?jobs.slice(0,6).map(j=>`<p style="font-size:12px;margin:10px 0">${tag(j.status)} <strong>${esc(j.query)}</strong> · ${esc(j.city)}<br><span class="text-muted">${j.imported} neue Leads ${j.error?'· '+esc(j.error):''}</span></p>`).join(''):'<p class="small">Noch keine Jobs.</p>';}
async function refreshJobs(){document.querySelector('#job-list').innerHTML=renderJobList(await api(`/projects/${state.project.id}/jobs`));}

async function renderLeads(search=''){const p=state.project;const leads=await api(`/projects/${p.id}/leads?q=${encodeURIComponent(search)}`);content(`<div class="card" style="margin-bottom:20px"><div class="actionbar" style="justify-content:space-between"><div><h2 style="margin-bottom:5px">${leads.length} Leads</h2><p style="margin-bottom:0">Sortiert nach transparenter Relevanzbewertung</p></div><div class="actionbar"><button class="btn" id="export-leads">CSV exportieren</button><button class="btn primary" id="add-lead">+ Lead hinzufügen</button></div></div><div class="field" style="margin:20px 0 0"><input id="lead-search" placeholder="Unternehmen, Branche oder Stadt filtern …" value="${esc(search)}"></div></div>${leadTable(leads)}`);
  on('lead-search','input',e=>{clearTimeout(window._leadSearch);const value=e.target.value;window._leadSearch=setTimeout(()=>renderLeads(value),350);});on('add-lead','click',()=>showLead(null));on('export-leads','click',()=>{window.location.href=`/api/projects/${p.id}/export`;});bindLeadRows();}

function drawer(html){document.querySelector('.overlay')?.remove();const div=document.createElement('div');div.className='overlay';div.innerHTML=`<div class="drawer"><header><div><div class="eyebrow">VALDRIQ / CRM</div><h2>${state.lead?esc(state.lead.business):'Neuer Lead'}</h2></div><button class="close" aria-label="Schließen" id="close-drawer">×</button></header>${html}</div>`;document.body.appendChild(div);on('close-drawer','click',()=>div.remove());div.addEventListener('click',e=>{if(e.target===div)div.remove();});}
async function showLead(id){const l=id?await api(`/leads/${id}`):{business:'',contact_name:'',email:'',phone:'',website:'',industry:'',address:'',notes:'',evidence:'',permission:'none',permission_evidence:'',permission_date:'',status:'new'};state.lead=l;
  const messages=id?await api(`/leads/${id}/messages`):[];
  drawer(`<form id="lead-form"><div class="form-grid"><div class="field"><label>Unternehmen *</label><input name="business" required value="${esc(l.business)}"></div><div class="field"><label>Branche</label><input name="industry" value="${esc(l.industry)}"></div>
  <div class="field"><label>Ansprechpartner</label><input name="contact_name" value="${esc(l.contact_name)}"></div><div class="field"><label>E-Mail</label><input name="email" type="email" value="${esc(l.email)}"></div>
  <div class="field"><label>Telefon</label><input name="phone" value="${esc(l.phone)}"></div><div class="field"><label>Website</label><input name="website" value="${esc(l.website)}"></div></div>
  <div class="field"><label>Adresse</label><input name="address" value="${esc(l.address)}"></div><div class="field"><label>Öffentliche Quelle / Beleg</label><textarea name="evidence">${esc(l.evidence)}</textarea></div>
  <div class="field"><label>Notizen / verifizierte Verkaufssignale</label><textarea name="notes">${esc(l.notes)}</textarea></div>
  <div class="field"><label>Pipeline-Status</label><select name="status">${[['new','Neu'],['qualified','Qualifiziert'],['contacted','Kontaktiert'],['replied','Hat geantwortet'],['won','Gewonnen'],['lost','Verloren']].map(([v,t])=>`<option value="${v}" ${l.status===v?'selected':''}>${t}</option>`).join('')}</select></div>
  <div class="detail-section"><h3>Rechtliche Kontaktgrundlage</h3><div class="callout">Eine veröffentlichte E-Mail-Adresse ist keine Einwilligung. Bitte nur belegbare, tatsächlich anwendbare Optionen auswählen. Das System ersetzt keine rechtliche Prüfung.</div>
  <div class="field" style="margin-top:15px"><label>Grundlage für Werbe-E-Mail</label><select name="permission"><option value="none">Keine – Versand gesperrt</option><option value="consent" ${l.permission==='consent'?'selected':''}>Ausdrückliche Einwilligung</option><option value="existing_customer" ${l.permission==='existing_customer'?'selected':''}>Geprüfte Bestandskundenausnahme (§ 7 Abs. 3 UWG)</option></select></div>
  <div class="field"><label>Dokumentierter Nachweis / Quelle</label><textarea name="permission_evidence" placeholder="z. B. Opt-in-Protokoll oder dokumentierte Prüfung der vier Voraussetzungen">${esc(l.permission_evidence)}</textarea></div>
  <div class="field"><label>Datum der Einwilligung / Prüfung</label><input name="permission_date" type="date" value="${esc(l.permission_date)}"></div></div>
  <div class="actionbar"><button class="btn primary" type="submit">Lead speichern</button>${id?`<button class="btn danger mini" id="delete-lead" type="button">Löschen</button>`:''}</div></form>
  ${id?`<div class="detail-section"><h3>Nachrichten & Kontakt</h3><p class="small">Wähle eine von vier Vorlagen. Jede E-Mail benötigt eine individuelle Freigabe.</p><div class="field"><label>Vorlage</label><select id="draft-kind"><option value="intro">Erstkontakt – sachlich</option><option value="value">Nutzenorientiert</option><option value="demo">Termin / Produktdemo</option><option value="followup">Follow-up (nur nach Erstkontakt)</option></select></div><button class="btn" id="draft-lead">✦ Persönlichen Entwurf erstellen</button>
  <div id="message-list" class="stack" style="margin-top:16px">${messages.length?messages.map(m=>messageCard(m)).join(''):'<p class="small">Noch keine Nachrichten.</p>'}</div></div>`:''}`);
  on('lead-form','submit',async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.currentTarget));try{if(id)await api(`/leads/${id}`,'PATCH',data);else{const res=await api(`/projects/${state.project.id}/leads`,'POST',data);id=res.id;}notify('Lead gespeichert.');await renderLeads();await showLead(id);}catch(err){notify(err.message,true);}});
  if(!id)return;
  on('delete-lead','click',async()=>{if(!confirm('Lead und alle Nachrichten unwiderruflich löschen?'))return;try{await api(`/leads/${id}`,'DELETE',{});document.querySelector('.overlay')?.remove();renderLeads();notify('Lead gelöscht.');}catch(err){notify(err.message,true);}});
  on('draft-lead','click',async()=>{try{const kind=document.querySelector('#draft-kind').value;const result=await api(`/leads/${id}/draft`,'POST',{kind});notify(result.mode==='ai'?'KI-Entwurf erstellt.':'Vorlagenentwurf erstellt.');showLead(id);}catch(err){notify(err.message,true);}});
  for(const msg of messages){bindMessage(msg,id);}
}
function messageCard(m){return `<div class="card muted" style="padding:17px"><div class="actionbar" style="justify-content:space-between;margin-bottom:12px"><strong>Nachricht #${m.id}</strong>${tag(m.state)}</div>
  ${['draft','failed'].includes(m.state)?`<div class="field"><label>Betreff</label><input id="subject-${m.id}" value="${esc(m.subject)}"></div><div class="field"><label>Mailtext</label><textarea id="body-${m.id}" style="min-height:240px">${esc(m.body)}</textarea></div><div class="actionbar"><button class="btn mini" id="save-${m.id}">Entwurf speichern</button><button class="btn mini primary" id="approve-${m.id}">Freigeben</button></div>`:
    `<p style="white-space:pre-wrap;font-size:12px">${esc(m.subject)}\n\n${esc(m.body)}</p>${m.state==='approved'?`<button class="btn primary mini" id="send-${m.id}">Jetzt verbindlich versenden</button>`:''}`}
  ${m.error?`<div class="callout" style="margin-top:12px">${esc(m.error)}</div>`:''}</div>`;}
function bindMessage(message,leadId){const id=message.id;
  on('save-'+id,'click',async()=>{try{await api(`/messages/${id}`,'PATCH',{subject:document.querySelector('#subject-'+id).value,body:document.querySelector('#body-'+id).value});notify('Gespeichert.');showLead(leadId);}catch(err){notify(err.message,true);}});
  on('approve-'+id,'click',async()=>{try{await api(`/messages/${id}`,'PATCH',{subject:document.querySelector('#subject-'+id).value,body:document.querySelector('#body-'+id).value});await api(`/messages/${id}/approve`,'POST',{});notify('Nachricht freigegeben. Noch nicht versandt.');showLead(leadId);}catch(err){notify(err.message,true);}});
  on('send-'+id,'click',async()=>{if(!confirm('Diese Nachricht jetzt tatsächlich an den hinterlegten Empfänger versenden? Ein Versand ist nicht rückgängig zu machen.'))return;try{await api(`/messages/${id}/send`,'POST',{});notify('E-Mail versandt.');showLead(leadId);}catch(err){notify(err.message,true);}});
}

async function renderSettings(){const p=state.project;content(`<div class="grid two"><div class="card"><div class="eyebrow">STRATEGIE</div><h2>Projektprofil bearbeiten</h2><p>Änderungen beeinflussen die Qualität von Scoring und Nachrichten.</p><form id="settings-form">
  ${fields.map(([key,label])=>`<div class="field"><label>${esc(label)}</label>${['offer','customer_problem','differentiator','contact_strategy'].includes(key)?`<textarea name="${key}">${esc(p[key])}</textarea>`:`<input name="${key}" value="${esc(p[key])}">`}</div>`).join('')}
  <button class="btn primary" type="submit">Strategie speichern</button></form></div>
  <div class="stack"><div class="card"><div class="eyebrow">INTEGRATIONEN</div><h2>Verbindungsstatus</h2>
  ${[['Google Places API','google_places'],['Google Maps Scraper Kit','scraper_kit'],['OpenAI-Entwürfe','ai'],['SMTP-E-Mail-Versand','smtp']].map(([label,key])=>`<div class="actionbar" style="justify-content:space-between;padding:10px 0;border-bottom:1px solid #28384f"><span>${label}</span><span class="tag ${state.config[key]?'':'warn'}">${state.config[key]?'Konfiguriert':'Nicht eingerichtet'}</span></div>`).join('')}
  <p class="small" style="margin-top:18px">Zugangsdaten werden ausschließlich serverseitig über Umgebungsvariablen hinterlegt. Anleitung: docs/INTEGRATIONS.md.</p></div>
  <div class="card"><div class="eyebrow">COMPLIANCE</div><h2>Globale Sperrliste</h2><p>Einträge werden unabhängig vom Projekt vom Versand ausgeschlossen.</p>
  <form id="suppress-form"><div class="field"><label>E-Mail-Adresse sperren</label><input name="email" type="email" required placeholder="kontakt@example.de"></div><div class="field"><label>Grund</label><input name="reason" value="Widerspruch"></div><button class="btn" type="submit">Zur Sperrliste hinzufügen</button></form><div id="suppress-list" style="margin-top:14px"></div></div>
  <div class="card"><h2>Export und Datenhoheit</h2><p>Du kannst alle Leads als CSV exportieren oder einzelne Datensätze löschen. Ein vollständiger Backup ist die SQLite-Datenbank.</p><button class="btn" id="settings-export">Leads exportieren</button></div></div></div>`);
  on('settings-form','submit',async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.currentTarget));try{await api(`/projects/${p.id}`,'PATCH',data);await loadProjects();notify('Strategie gespeichert.');}catch(err){notify(err.message,true);}});
  on('suppress-form','submit',async e=>{e.preventDefault();try{await api('/suppression','POST',Object.fromEntries(new FormData(e.currentTarget)));notify('Adresse gesperrt.');e.currentTarget.reset();loadSuppression();}catch(err){notify(err.message,true);}});
  on('settings-export','click',()=>window.location.href=`/api/projects/${p.id}/export`);
  loadSuppression();
}
async function loadSuppression(){const rows=await api('/suppression');const target=document.querySelector('#suppress-list');if(target)target.innerHTML=rows.length?rows.slice(0,20).map(r=>`<p class="small">✕ ${esc(r.email)} · ${esc(r.reason)}</p>`).join(''):'<p class="small">Sperrliste noch leer.</p>';}

boot();
