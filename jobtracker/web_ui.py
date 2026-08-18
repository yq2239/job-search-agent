DASHBOARD_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Job Tracker</title>
<style>
:root{--ink:#172b3a;--muted:#647687;--line:#dbe4ea;--paper:#f5f8fa;--blue:#1769d2;--navy:#173650;--green:#087f6b;--amber:#a45a00;--shadow:0 12px 34px rgba(23,54,80,.08)}
*{box-sizing:border-box}body{margin:0;background:#eef3f6;color:var(--ink);font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
button,input,select,textarea{font:inherit}button,a,select{touch-action:manipulation}
.shell{width:min(1160px,calc(100% - 32px));margin:auto;padding:34px 0 70px}
.top{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:22px}
h1{font-size:clamp(28px,5vw,44px);line-height:1.05;margin:0;color:var(--navy);letter-spacing:-.03em}.lede{color:var(--muted);margin:8px 0 0}
.privacy{background:#e3f4ef;color:#066556;border:1px solid #b8ded3;border-radius:999px;padding:7px 11px;font-size:12px;font-weight:750;white-space:nowrap}
.metrics{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:0 0 18px}
.metric{background:white;border:1px solid var(--line);border-radius:14px;padding:15px 17px;box-shadow:var(--shadow)}
.metric-review{grid-column:span 2;padding:17px 18px}
.metric-discovered{--company-bg:#f2f8ff;--company-border:#c9e1f5;--company-count:#dceeff;--company-count-text:#1769a8}
.metric-interested,.metric-applied,.metric-referred{--company-bg:#f0faf7;--company-border:#c9e7de;--company-count:#dcefe9;--company-count-text:#066556}
.metric b{display:block;font-size:25px;color:var(--navy)}
.metric #review{color:#8d5200}.metric #discovered{color:#1769a8}.metric #interested,.metric #applied,.metric #referred{color:#066556}
.metric span{font-size:12px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.metric-companies{display:grid;gap:5px;margin-top:10px}
.metric-company{display:flex;align-items:center;gap:5px;width:100%;min-width:0;border:1px solid var(--company-border,#dbe6ed);background:var(--company-bg,#f7fafb);color:var(--navy);border-radius:9px;padding:4px 6px 4px 5px;cursor:pointer;font:inherit;font-size:11px;font-weight:750;transition:.15s ease}
.metric-company:hover{filter:brightness(.97);transform:translateY(-1px)}
.metric-company .company-mark{width:20px;height:20px;border-radius:6px;box-shadow:none;flex:0 0 20px}
.metric-company .company-mark svg,.metric-company .company-mark img{width:13px;height:13px}
.metric-company .metric-company-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--navy);font-size:11px;text-transform:none;letter-spacing:0}
.metric-company .metric-company-count{display:grid;place-items:center;min-width:18px;height:18px;margin-left:auto;padding:0 4px;border-radius:999px;background:var(--company-count,#e7eef2);color:var(--company-count-text,#40596b);font-size:10px;text-transform:none;letter-spacing:0}
.metric-review .metric-companies{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px}
.metric-review .metric-company{width:auto;gap:7px;border-color:#edce95;background:#fff9ed;border-radius:999px;padding:6px 9px 6px 7px;font-size:12px}
.metric-review .metric-company:hover{background:#fff1d6;border-color:#d8a446;filter:none}
.metric-review .metric-company .company-mark{width:24px;height:24px;border-radius:7px;flex-basis:24px}
.metric-review .metric-company .company-mark svg,.metric-review .metric-company .company-mark img{width:16px;height:16px}
.metric-review .metric-company .metric-company-name{font-size:12px}
.metric-review .metric-company .metric-company-count{min-width:20px;height:20px;background:#f4dfb7;color:#7b4700;font-size:11px}
.metric-empty{display:block;margin-top:10px;text-transform:none!important;letter-spacing:0!important;font-weight:600!important;font-size:11px!important}
.toolbar{display:grid;grid-template-columns:minmax(240px,1fr) 180px 180px 170px;gap:10px;background:white;border:1px solid var(--line);border-radius:16px;padding:12px;position:sticky;top:10px;z-index:5;box-shadow:var(--shadow);margin-bottom:16px}
.control{width:100%;border:1px solid #cbd8e1;border-radius:10px;padding:10px 12px;background:white;color:var(--ink);outline:none}
.control:is(select){appearance:none;-webkit-appearance:none;padding-right:40px;background-color:white;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 20 20' fill='none'%3E%3Cpath d='m6 8 4 4 4-4' stroke='%2351687a' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center;background-size:18px}
.control:focus{border-color:var(--blue);box-shadow:0 0 0 3px #dceaff}
.results{display:grid;gap:14px}.empty{background:white;border:1px solid var(--line);border-radius:16px;padding:40px;text-align:center;color:var(--muted)}
.card{background:white;border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);overflow:hidden}.card-main{padding:20px 22px}.job-head{display:flex;gap:16px;justify-content:space-between;align-items:flex-start}
.company-line{display:flex;align-items:center;gap:10px;margin-bottom:7px}.company-mark{width:38px;height:38px;display:grid;place-items:center;border-radius:10px;background:white;border:1px solid #dce5eb;box-shadow:0 3px 10px rgba(23,54,80,.07);overflow:hidden}.company-mark svg,.company-mark img{display:block;width:24px;height:24px;object-fit:contain}.company-mark.deepmind svg{width:29px;height:29px}.company-name{font-size:18px;line-height:1.1;color:var(--navy);font-weight:850;letter-spacing:-.01em}.job-id{font-size:10px;color:var(--muted);font-weight:700;letter-spacing:.04em;margin-top:3px}.role-line{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin:3px 0 7px}.job-title{font-size:21px;line-height:1.25;color:var(--navy);margin:0}.role-line .status-chip{flex:0 0 auto}
.score{width:58px;height:58px;border-radius:50%;display:grid;place-items:center;background:#e9f2ff;color:var(--blue);font-size:18px;font-weight:800;flex:0 0 auto}.score small{display:block;font-size:8px;line-height:1;text-align:center}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}.chip{padding:4px 8px;border-radius:999px;background:var(--paper);color:#51687a;font-size:12px;border:1px solid #e3eaef}.status-chip{font-size:13px;font-weight:850;letter-spacing:.01em;padding:6px 11px}.status-recommended,.status-interested,.status-applied{background:#e3f4ef;color:#066556;border-color:#b8ded3}.status-discovered{background:#e8f3ff;color:#1769a8;border-color:#b9d8f2}.status-manual_review{background:#fff3dc;color:#8d5200;border-color:#f0d29b}.status-skipped,.status-rejected,.status-closed,.status-withdrawn{background:#fde8e8;color:#a12a2a;border-color:#f0bcbc}
.evidence{margin:12px 0 0;color:#354b5c}.actions{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin-top:17px}.btn{border:0;border-radius:10px;padding:9px 12px;font-weight:750;cursor:pointer}.btn.primary{background:var(--blue);color:white}.btn.secondary{background:#e9eff3;color:var(--navy)}.btn:disabled{opacity:.55;cursor:wait}
.posting{color:var(--blue);font-weight:750;text-decoration:none;margin-right:auto}.posting:hover{text-decoration:underline}
.editor{display:grid;grid-template-columns:170px minmax(180px,1fr) auto;gap:8px;width:100%;margin-top:8px}.editor input,.editor select{min-width:0}.notes{border-top:1px solid var(--line);background:#fafcfd;padding:16px 22px}.notes summary{cursor:pointer;color:var(--navy);font-weight:780}
.note-list{display:grid;gap:8px;margin:12px 0}.note{background:white;border:1px solid var(--line);border-radius:10px;padding:10px 12px}.note time{display:block;color:var(--muted);font-size:11px;margin-bottom:3px}.note-form{display:grid;grid-template-columns:1fr auto;gap:8px}.note-form textarea{min-height:46px;resize:vertical}
.status-history{border-top:1px solid var(--line);background:#f5f8fa;padding:14px 22px}.status-history summary{cursor:pointer;color:var(--navy);font-weight:800}.history-list{display:grid;gap:8px;margin-top:11px}.history-entry{display:grid;grid-template-columns:auto 1fr;gap:9px;align-items:start}.history-entry time{color:var(--muted);font-size:11px;padding-top:4px}.history-entry p{margin:0;background:white;border:1px solid var(--line);border-radius:9px;padding:8px 10px}.history-entry .status-chip{display:inline-block;margin-right:7px;font-size:11px;padding:3px 7px}
.toast{position:fixed;right:20px;bottom:20px;background:var(--navy);color:white;padding:11px 14px;border-radius:10px;box-shadow:var(--shadow);display:none}.toast.error{background:#9a2f2f}
@media(max-width:760px){.shell{width:min(100% - 20px,1160px);padding-top:22px}.top{display:block}.privacy{display:inline-block;margin-top:12px}.metrics{grid-template-columns:repeat(2,1fr)}.toolbar{grid-template-columns:1fr;position:static}}
@media(max-width:760px){.editor,.note-form{grid-template-columns:1fr}.job-title{font-size:18px}.card-main,.notes{padding-left:15px;padding-right:15px}}
</style></head><body><main class="shell">
<header class="top"><div><h1>Smart Job Tracker</h1><p class="lede">Review opportunities, record decisions, and keep application context in one place.</p></div><span class="privacy">Local only</span></header>
<section class="metrics" id="statusMetrics" aria-label="Jobs by status">
<div class="metric metric-review"><b id="review">-</b><span>Pending review</span><div id="pendingCompanies" class="metric-companies" aria-label="Companies with jobs pending review"></div></div>
<div class="metric metric-discovered"><b id="discovered">-</b><span>Discovered</span><div id="discoveredCompanies" class="metric-companies" aria-label="Companies with discovered jobs"></div></div>
<div class="metric metric-interested"><b id="interested">-</b><span>Interested</span><div id="interestedCompanies" class="metric-companies" aria-label="Companies with interested jobs"></div></div>
<div class="metric metric-applied"><b id="applied">-</b><span>Applied</span><div id="appliedCompanies" class="metric-companies" aria-label="Companies with applied jobs"></div></div>
<div class="metric metric-referred"><b id="referred">-</b><span>Referred</span><div id="referredCompanies" class="metric-companies" aria-label="Companies with referred jobs"></div></div>
</section>
<section class="toolbar" aria-label="Job filters">
<input class="control" id="search" type="search" placeholder="Search title, company, location..." aria-label="Search jobs">
<select class="control" id="companyFilter" aria-label="Filter by company"><option value="">All companies</option></select>
<select class="control" id="statusFilter" aria-label="Filter by status"><option value="">All statuses</option></select>
<select class="control" id="sort" aria-label="Sort jobs"><option value="score">Highest fit</option><option value="updated">Recently updated</option><option value="title">Title A-Z</option></select>
</section>
<section id="results" class="results" aria-live="polite"></section>
</main><div id="toast" class="toast" role="status"></div>
<script>
const state={jobs:[],statuses:[]};
const labels={manual_review:'Pending review',discovered:'Discovered',recommended:'Referred',interested:'Interested',applied:'Applied',skipped:'Not applying',rejected:'Rejected',closed:'Closed',withdrawn:'Withdrawn'};
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const when=value=>value?new Date(value).toLocaleString():'Unknown time';
function toast(message,error=false){const el=$('toast');el.textContent=message;el.className='toast'+(error?' error':'');el.style.display='block';setTimeout(()=>el.style.display='none',2600)}
async function load(){
  const response=await fetch('/api/jobs');
  if(!response.ok)throw new Error('Could not load jobs');
  const data=await response.json();state.jobs=data.jobs;state.statuses=data.statuses;
  const companies=[...new Set(state.jobs.map(job=>job.company))].sort((a,b)=>a.localeCompare(b));
  $('companyFilter').innerHTML='<option value="">All companies</option>'+companies.map(company=>`<option value="${esc(company)}">${esc(company)}</option>`).join('');
  $('statusFilter').innerHTML='<option value="">All statuses</option>'+state.statuses.map(s=>`<option value="${esc(s)}">${esc(labels[s]||s)}</option>`).join('');
  render();
}
function renderStatusMetric(status,countId,companiesId){
  const jobs=state.jobs.filter(job=>job.status===status);$(countId).textContent=jobs.length;
  const byCompany=new Map();jobs.forEach(job=>byCompany.set(job.company,(byCompany.get(job.company)||0)+1));
  const companies=[...byCompany.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
  $(companiesId).innerHTML=companies.length?companies.map(([company,count])=>`<button type="button" class="metric-company" data-company="${esc(company)}" title="Show all ${esc(company)} jobs"><span class="company-mark ${company==='Google DeepMind'?'deepmind':''}" aria-hidden="true">${companyMark(company)}</span><span class="metric-company-name">${esc(company)}</span><span class="metric-company-count">${count}</span></button>`).join(''):'<span class="metric-empty">No companies</span>';
}
function metrics(){
  renderStatusMetric('manual_review','review','pendingCompanies');
  renderStatusMetric('discovered','discovered','discoveredCompanies');
  renderStatusMetric('interested','interested','interestedCompanies');
  renderStatusMetric('applied','applied','appliedCompanies');
  renderStatusMetric('recommended','referred','referredCompanies');
}
function visibleJobs(){
  const q=$('search').value.trim().toLowerCase();
  const company=$('companyFilter').value,status=$('statusFilter').value,sort=$('sort').value;
  const jobs=state.jobs.filter(j=>(!company||j.company===company)&&(!status||j.status===status)&&(!q||[j.title,j.company,j.location,j.evidence].join(' ').toLowerCase().includes(q)));
  jobs.sort((a,b)=>sort==='title'?a.title.localeCompare(b.title):sort==='updated'?String(b.updated_at).localeCompare(String(a.updated_at)):b.fit_score-a.fit_score);
  return jobs;
}
function statusOptions(job){
  return state.statuses.map(s=>`<option value="${esc(s)}" ${s===job.status?'selected':''}>${esc(labels[s]||s)}</option>`).join('');
}
const statusClass=status=>`status-${String(status||'unknown').replace(/[^a-z0-9_-]/gi,'-')}`;
function companyFallback(company){
  const initials=String(company||'').trim().split(/\s+/).map(part=>part[0]||'').join('').slice(0,2).toUpperCase()||'?';
  return `<svg viewBox="0 0 24 24" role="img" aria-label="${esc(company)}"><rect width="24" height="24" rx="5" fill="#eef3f6"/><text x="12" y="15.5" text-anchor="middle" fill="#40596b" font-size="9" font-weight="800" font-family="system-ui,sans-serif">${esc(initials)}</text></svg>`;
}
function automaticCompanyIcon(company){
  let iconUrl=state.company_icons?.[company]||'';
  if(!iconUrl){
    const job=state.jobs.find(item=>item.company===company);
    try{const posting=new URL(job?.url||'');if(posting.protocol==='https:')iconUrl=`${posting.origin}/favicon.ico`}catch(error){}
  }
  return iconUrl?`<img class="company-logo-auto" alt="" src="${esc(iconUrl)}" data-company="${esc(company)}">`:companyFallback(company);
}
function companyMark(company){
  const logos={
    Google:`<svg viewBox="0 0 24 24" role="img"><path fill="#4285F4" d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"/></svg>`,
    'Google DeepMind':`<img alt="" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAMAAABlApw1AAACxFBMVEUAAABFg/FBhfVChPNChfRChfRBhvRChfRChfRChfRChfRBhfVChfNChfNChfVDhvVEg/RFifVDhvJBhvNChfRChfVChfRChfRDhfRChfRDhfRChPJNgP8A//9BhPNChvRChfRChfRBhfVChPZEiO5BiPRChfRDhfRChfRBhvZAgP9BhfVChPRBhfRChvVDhfOAgP88h/BChfNChfRChfRDhfRDhvJChPNChfRChfVChfRJkv9Vqv9ChPVChfRChfRGf/NChfRAh/dChfRChfRChfVEh/VChfRChfRBhvQ9hvNBhPNDhvVVgP9EhPJDhvM5jv9ChPRChfRBhfRDhfRDhfNDhfRDhfRChfRChvRChfVChfVChvNChfRChfNEgvRChvRChPRCh/RChfREg/NAifZChfRChfRGg/dGhPZChPRDhvVJgO1ChvRChfNDhfRChvRChfRChPRChfVChfNDhfRBhfNBhvRGi/9AgO9ChPRDhvVDhvVChfQ7ietChfRHgPFChfVChfRChfRChfNAhPVChvVDhvZChvRChPNAhPZDhvJChfRAh/FDhfNChPNChfRBhvU9hfVAivRChvVChPZCg/NChfVEiPdBhvRChfRChfRChfVBhvVDhfRChfRChfRChfRChfNChfRChvRAgOpChfRChPdBhPNDhPNAgPJChfRChfVDhvVChfRAgP9ChfRBhfNChfRChfNChPRChPRBhPNChfRChfRChfRDhfNBhfRChfVBhPVBhfRDhfVChfRDhfREh/hDhfRBhfQzmf9ChfRDhvRDhfRDhfNBhfRBh/VDhfVDhPRAhfNChfRChfRDhvRChPRBhvREg/NChPZChfRDhfRBhvNBhPRBhPRDhfNBhfVBhfVChPNBhPRDh/VBhfRChvRChfRDhfNBg/JChvVCg/BChfNAhfRBhvJChPSz3uePAAAA7HRSTlMAJUtsjqm/1t/s/8Ovm39nRBoTUpDE8fTPpW86CgGF0v3RlFEPL4zmyjcIYs7ik0ECEYDr5IYmg/DFYAcDaOroFvgg/PmWMdf3jRVuegY8Kgmi2EOdWBfLp2Fk3GmyhC3ps0b+KRzM7iEd50wO1Je0j9mHSa64mLsLENBjUNMN4xKSyLrGNKo5XT44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">`,
    Snowflake:`<svg viewBox="0 0 24 24" role="img"><path fill="#29B5E8" d="M7.602 12.4c.038-.151.076-.304.076-.456 0-.114-.038-.228-.038-.342-.114-.343-.304-.647-.646-.838l-4.87-2.777c-.685-.38-1.56-.152-1.94.533-.381.685-.153 1.56.532 1.94l2.701 1.56-2.701 1.56c-.685.38-.913 1.256-.533 1.94.38.685 1.256.914 1.94.533l4.832-2.777c.343-.267.571-.533.647-.876zm1.332 2.626c-.266-.038-.57.038-.837.19l-4.832 2.777c-.685.38-.913 1.256-.532 1.94.38.686 1.255.914 1.94.533l2.701-1.56v3.12c0 .8.647 1.408 1.446 1.408.799 0 1.407-.647 1.407-1.408v-5.592c0-.761-.57-1.37-1.293-1.408zm4.946-6.088c.266.038.57-.038.837-.19l4.832-2.777c.685-.38.913-1.256.532-1.94-.38-.686-1.255-.914-1.94-.533l-2.701 1.56V1.975c0-.799-.647-1.408-1.446-1.408-.799 0-1.446.609-1.446 1.408V7.53c0 .76.609 1.37 1.332 1.407zM3.265 5.97l4.832 2.777c.266.152.533.19.837.19.723-.038 1.331-.684 1.331-1.407V1.975c0-.799-.646-1.408-1.407-1.408-.799 0-1.446.647-1.446 1.408v3.12l-2.701-1.56c-.685-.38-1.56-.152-1.94.533-.419.646-.19 1.521.494 1.902zm16.284 11.984-4.832-2.777c-.266-.152-.57-.19-.837-.152-.723.038-1.332.684-1.332 1.408v5.554c0 .8.647 1.408 1.408 1.408.799 0 1.446-.647 1.446-1.408v-3.12l2.7 1.56c.686.38 1.561.152 1.941-.533.419-.646.19-1.521-.494-1.94zm2.549-7.533-2.701 1.56 2.7 1.56c.686.38.914 1.256.533 1.94-.38.685-1.255.913-1.94.533l-4.832-2.778a1.644 1.644 0 01-.647-.798c-.037-.153-.076-.305-.076-.457 0-.114.039-.228.039-.342.114-.343.342-.647.646-.837l4.832-2.778c.685-.38 1.56-.152 1.94.533.457.609.19 1.484-.494 1.864"/></svg>`,
    Airbnb:`<svg viewBox="0 0 24 24" role="img"><path fill="#FF5A5F" d="M12.001 18.275c-1.353-1.697-2.148-3.184-2.413-4.457-.263-1.027-.16-1.848.291-2.465.477-.71 1.188-1.056 2.121-1.056s1.643.345 2.12 1.063c.446.61.558 1.432.286 2.465-.291 1.298-1.085 2.785-2.412 4.458zm9.601 1.14c-.185 1.246-1.034 2.28-2.2 2.783-2.253.98-4.483-.583-6.392-2.704 3.157-3.951 3.74-7.028 2.385-9.018-.795-1.14-1.933-1.695-3.394-1.695-2.944 0-4.563 2.49-3.927 5.382.37 1.565 1.352 3.343 2.917 5.332-.98 1.085-1.91 1.856-2.732 2.333-.636.344-1.245.558-1.828.609-2.679.399-4.778-2.2-3.825-4.88.132-.345.395-.98.845-1.961l.025-.053c1.464-3.178 3.242-6.79 5.285-10.795l.053-.132.58-1.116c.45-.822.635-1.19 1.351-1.643.346-.21.77-.315 1.246-.315.954 0 1.698.558 2.016 1.007.158.239.345.557.582.953l.558 1.089.08.159c2.041 4.004 3.821 7.608 5.279 10.794l.026.025.533 1.22.318.764c.243.613.294 1.222.213 1.858zm1.22-2.39c-.186-.583-.505-1.271-.9-2.094v-.03c-1.889-4.006-3.642-7.608-5.307-10.844l-.111-.163C15.317 1.461 14.468 0 12.001 0c-2.44 0-3.476 1.695-4.535 3.898l-.081.16c-1.669 3.236-3.421 6.843-5.303 10.847v.053l-.559 1.22c-.21.504-.317.768-.345.847C-.172 20.74 2.611 24 5.98 24c.027 0 .132 0 .265-.027h.372c1.75-.213 3.554-1.325 5.384-3.317 1.829 1.989 3.635 3.104 5.382 3.317h.372c.133.027.239.027.265.027 3.37.003 6.152-3.261 4.802-6.975z"/></svg>`,
    DoorDash:`<svg viewBox="0 0 24 24" role="img"><path fill="#FF3008" d="M23.071 8.409a6.09 6.09 0 00-5.396-3.228H.584A.589.589 0 00.17 6.184L3.894 9.93a1.752 1.752 0 001.242.516h12.049a1.554 1.554 0 11.031 3.108H8.91a.589.589 0 00-.415 1.003l3.725 3.747a1.75 1.75 0 001.242.516h3.757c4.887 0 8.584-5.225 5.852-10.413"/></svg>`,
    Roblox:`<svg viewBox="0 0 24 24" role="img"><path fill="#111" d="M18.926 23.998 0 18.892 5.075.002 24 5.108ZM15.348 10.09l-5.282-1.453-1.414 5.273 5.282 1.453z"/></svg>`
  };
  // Use inline vector markup for DeepMind so the real mark cannot be blocked by
  // image loading, CSP, browser cache, or a network failure.
  logos['Google DeepMind']=`<svg viewBox="0 0 119 119" role="img" aria-label="Google DeepMind"><path fill="#0053d6" d="M84.63 5.647C77.209 2.144 68.384 0 60.004 0 34.71 0 19.58 20.935 21.208 41.399c.738 9.256 5.283 18.212 12.798 25.215a42.56 42.56 0 0 0 8.95 6.43 21.285 21.285 0 0 1-4.701-10.239c-1.681-10.285 5.11-25.413 22.456-25.413 18.655 0 39.192 17.735 40.929 39.542 1.062 13.34-3.995 25.35-12.545 33.74 17.683-10.271 29.574-29.416 29.574-51.34 0-23.721-13.92-44.192-34.039-53.687z"/><path fill="#0053d6" d="M97.46 77.269c-.738-9.256-5.283-18.212-12.798-25.215a42.56 42.56 0 0 0-8.95-6.43 21.285 21.285 0 0 1 4.701 10.239c1.681 10.285-5.11 25.413-22.456 25.413-18.654 0-39.192-17.735-40.928-39.544-1.062-13.34 3.995-25.35 12.545-33.74C11.891 18.265 0 37.41 0 59.334c0 23.722 13.92 44.192 34.038 53.687 7.421 3.503 16.246 5.647 24.626 5.647 25.294 0 40.424-20.935 38.796-41.4z"/></svg>`;
  logos.Waymo=`<svg viewBox="80 0 1030 540" role="img" aria-label="Waymo"><path fill="#0078ff" d="M670 132 518 44 316 397l151 87 203-352zm51 265 152 87 203-353-152-87-203 353z"/><path fill="#00b878" d="M1088 88a88 88 0 1 1-176 0 88 88 0 0 1 176 0zM392 528c-31 0-60-16-77-44L113 132C89 90 103 36 145 12s96-10 120 32l202 353c24 42 10 95-32 119-14 8-28 12-43 12zm405 0c-30 0-60-16-76-44L518 132c-24-42-10-96 32-120s96-10 120 32l203 353c24 42 9 95-32 119-14 8-29 12-44 12z"/></svg>`;
  logos.Snap=`<svg viewBox="0 0 24 24" role="img" aria-label="Snap"><path fill="#111" d="M12.2.8c1 0 4.4.3 5.9 3.8.5 1.2.4 3.2.3 5.4.4.2.9 0 1.4-.2.8-.4 1.7 0 1.7.8 0 .5-.4.9-1.2 1.2-.5.2-1.5.4-1.7.9-.1.2 0 .5.1.9.1.1 1.6 3.5 4.8 4 .3 0 .4.3.4.5 0 .7-1.1 1.1-3.2 1.4-.1.2-.1.6-.3 1-.1.3-.3.4-.6.4-.5 0-1.5-.3-2.8-.1-1.5.3-2.9 2.2-5.2 2.2s-3.7-1.9-5.1-2.2c-1.4-.2-2.3.1-2.8.1-.4 0-.5-.2-.6-.4-.1-.4-.2-.9-.3-1C1.1 19.3 0 18.9 0 18.3c-.1-.3.1-.6.4-.7 3.3-.5 4.7-3.9 4.8-4 .2-.4.2-.7.1-.9-.2-.5-1.2-.8-1.7-.9-1.1-.4-1.3-.9-1.2-1.3.1-.5.7-.8 1.2-.8.6 0 1.1.6 2 .4l-.1-.6c-.1-1.6-.2-3.7.3-4.8C7.4 1.1 10.7.8 12.2.8z"/></svg>`;
  logos.Microsoft=`<svg viewBox="0 0 24 24" role="img" aria-label="Microsoft"><path fill="#f25022" d="M1 1h10v10H1z"/><path fill="#7fba00" d="M13 1h10v10H13z"/><path fill="#00a4ef" d="M1 13h10v10H1z"/><path fill="#ffb900" d="M13 13h10v10H13z"/></svg>`;
  logos.Reddit=`<svg viewBox="0 0 24 24" role="img" aria-label="Reddit"><circle cx="12" cy="12" r="12" fill="#ff4500"/><path fill="#fff" d="M19.5 11.8c0-1.05-.86-1.9-1.91-1.9-.52 0-.99.21-1.34.55-1.15-.78-2.68-1.28-4.37-1.35l.74-3.45 2.4.51a1.53 1.53 0 1 0 .18-.82l-2.86-.61a.43.43 0 0 0-.51.33l-.86 4.03c-1.75.05-3.33.55-4.51 1.35a1.9 1.9 0 1 0-2.1 3.08c-.03.2-.05.4-.05.6 0 2.78 3.44 5.03 7.69 5.03s7.69-2.25 7.69-5.03c0-.2-.02-.39-.05-.58.57-.33.96-.98.96-1.74zm-11.9 1.4a1.2 1.2 0 1 1 2.4 0 1.2 1.2 0 0 1-2.4 0zm7.55 3.33c-.91.91-2.65.98-3.15.98s-2.24-.07-3.15-.98a.43.43 0 0 1 .61-.61c.58.58 1.82.73 2.54.73s1.96-.15 2.54-.73a.43.43 0 1 1 .61.61zm-.35-2.13a1.2 1.2 0 1 1 0-2.4 1.2 1.2 0 0 1 0 2.4z"/></svg>`;
  logos.NVIDIA=`<svg viewBox="0 0 24 24" role="img" aria-label="NVIDIA"><path fill="#76b900" d="M8.67 8.06v-1.7c.55-.04 1.1-.07 1.66-.07 4.65 0 7.69 3.8 7.69 3.8s-3.28 4.56-6.8 4.56c-.88 0-1.72-.2-2.54-.61v-5.1c1.81.22 2.18 1.02 3.27 2.84l2.42-2.04s-1.77-2.32-4.75-2.32c-.32 0-.63.02-.95.06m0-5.63V4.4l.95-.06c6.47-.22 10.68 5.31 10.68 5.31s-4.84 5.89-9.87 5.89c-.58 0-1.16-.06-1.73-.16v1.08c.48.06.97.1 1.45.1 4.68 0 8.07-2.39 11.35-5.22.54.43 2.75 1.49 3.2 1.94-3.12 2.62-10.39 4.74-14.48 4.74-.51 0-1.01-.03-1.51-.08v2.27H6.75V8.22c-2.6.9-3.15 3.03-3.15 3.03s1.52 2.63 3.15 3.51v1.28C4.33 14.96 0 11.35 0 11.35s3.85-3.8 6.75-4.72V4.56c-3.21 1.04-5.29 2.96-6.75 4.21 0 0 3.49-4.85 8.67-5.82z"/></svg>`;
  logos.TikTok=`<svg fill="#111" role="img" aria-label="TikTok" viewBox="0 0 24 24"><path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/></svg>`;
  logos.ByteDance=`<svg fill="#3C8CFF" role="img" aria-label="ByteDance" viewBox="0 0 24 24"><path d="M19.8772 1.4685 24 2.5326v18.9426l-4.1228 1.0563V1.4685zm-13.3481 9.428 4.115 1.0641v8.9786l-4.115 1.0642v-11.107zM0 2.572l4.115 1.0642v16.7354L0 21.428V2.572zm17.4553 5.6205v11.107l-4.1228-1.0642V9.2568l4.1228-1.0642z"/></svg>`;
  logos.Adobe=`<svg fill="#EB1000" role="img" aria-label="Adobe" viewBox="0 0 24 24"><path d="M15.1 0H24v24L15.1 0zM8.9 0H0v24L8.9 0zM12 7.7 17.6 22h-3.8l-1.6-4.1H8.1L12 7.7z"/></svg>`;
  return logos[company]||automaticCompanyIcon(company);
}
function noteList(job){
  const notes=[...(job.notes||[])].reverse();
  return notes.length?notes.map(n=>`<div class="note"><time>${esc(when(n.at))}</time>${esc(n.body)}</div>`).join(''):'<p class="lede">No notes yet.</p>';
}
function historyList(job){
  const history=[...(job.history||[])].reverse();
  return history.length?history.map(entry=>`<div class="history-entry"><time>${esc(when(entry.at))}</time><p><span class="status-chip ${statusClass(entry.status)}">${esc(labels[entry.status]||entry.status)}</span>${esc(entry.note||'No status note')}</p></div>`).join(''):'<p class="lede">No status history yet.</p>';
}
function jobCard(job){
  const reasons=(job.eligibility_reasons||[]).join('; ');
  const mark=companyMark(job.company);
  return `<article class="card" data-id="${esc(job.id)}"><div class="card-main">
    <div class="job-head"><div><div class="company-line"><span class="company-mark ${job.company==='Google DeepMind'?'deepmind':''}" aria-hidden="true">${mark}</span><div><div class="company-name">${esc(job.company)}</div><div class="job-id">${esc(job.id)}</div></div></div><div class="role-line"><h2 class="job-title">${esc(job.title)}</h2><span class="status-chip ${statusClass(job.status)}">${esc(labels[job.status]||job.status)}</span></div></div><div class="score"><span>${esc(job.fit_score)}<small>FIT</small></span></div></div>
    <div class="chips"><span class="chip">${esc(job.location)}</span><span class="chip">${esc(job.minimum_education)} minimum</span><span class="chip">${esc(job.availability)} · verified ${esc(when(job.last_verified_at))}</span></div>
    <p class="evidence">${esc(job.evidence)}</p>
    ${reasons?`<p class="lede"><strong>Review:</strong> ${esc(reasons)}</p>`:''}
    <div class="actions"><a class="posting" href="${esc(job.url)}" target="_blank" rel="noopener noreferrer">Open official posting ↗</a></div>
    <div class="editor">
      <select class="control status-select" aria-label="Status for ${esc(job.title)}">${statusOptions(job)}</select>
      <input class="control status-note" maxlength="300" placeholder="Optional status note">
      <button class="btn primary save-status">Save status</button>
    </div>
  </div>
  <details class="status-history"><summary>Status history (${(job.history||[]).length})</summary>
    <div class="history-list">${historyList(job)}</div>
  </details>
  <details class="notes"><summary>Notes (${(job.notes||[]).length})</summary>
    <div class="note-list">${noteList(job)}</div>
    <div class="note-form"><textarea class="control note-body" maxlength="4000" placeholder="Add referral context, follow-up details, or application notes..."></textarea><button class="btn secondary add-note">Add note</button></div>
  </details></article>`;
}
function render(){
  metrics();const jobs=visibleJobs();
  $('results').innerHTML=jobs.length?jobs.map(jobCard).join(''):'<div class="empty">No jobs match these filters.</div>';
}
async function send(url,method,payload){
  const response=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data=await response.json();
  if(!response.ok)throw new Error(data.error||'Update failed');
  const index=state.jobs.findIndex(job=>job.id===data.job.id);
  state.jobs[index]=data.job;render();return data.job;
}
$('results').addEventListener('click',async event=>{
  const card=event.target.closest('.card');if(!card)return;
  const id=card.dataset.id;
  if(event.target.matches('.save-status')){
    event.target.disabled=true;
    try{await send(`/api/jobs/${encodeURIComponent(id)}/status`,'PATCH',{status:card.querySelector('.status-select').value,note:card.querySelector('.status-note').value});toast('Status saved')}
    catch(error){toast(error.message,true)}finally{event.target.disabled=false}
  }
  if(event.target.matches('.add-note')){
    const field=card.querySelector('.note-body');event.target.disabled=true;
    try{await send(`/api/jobs/${encodeURIComponent(id)}/notes`,'POST',{body:field.value});toast('Note added')}
    catch(error){toast(error.message,true)}finally{event.target.disabled=false}
  }
});
$('statusMetrics').addEventListener('click',event=>{
  const button=event.target.closest('.metric-company');if(!button)return;
  const company=button.dataset.company;
  $('companyFilter').value=company;$('statusFilter').value='';$('search').value='';render();
  $('results').scrollIntoView({behavior:'smooth',block:'start'});toast(`Showing all ${company} jobs`);
});
document.addEventListener('error',event=>{
  const image=event.target;
  if(!(image instanceof HTMLImageElement)||!image.matches('.company-logo-auto'))return;
  image.outerHTML=companyFallback(image.dataset.company||'');
},true);
['search','companyFilter','statusFilter','sort'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',render));
load().catch(error=>{$('results').innerHTML=`<div class="empty">${esc(error.message)}</div>`;toast(error.message,true)});
</script></body></html>"""
