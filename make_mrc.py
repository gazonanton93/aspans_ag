import re
import io

with open('c:/DISK_DATA/antigravity/tests_vinkom/mrc_prototype.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace demo data
data_start = "// ═══════════════════════════════════════\n// HARDCODED DEMO DATA"
data_end = "// ═══════════════════════════════════════\n// CHART DEFAULTS"

data_new = """// ═══════════════════════════════════════
// DATA LOADING
// ═══════════════════════════════════════
const MONTHS = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];
let DATA = [];

const API_BASE = window.location.origin + '/api/v1';

function getAuthHeaders() {
    const user = localStorage.getItem('personCode') || 'anonymous';
    const str = user + ':19451945';
    const utf8Bytes = encodeURIComponent(str).replace(/%([0-9A-F]{2})/g,
        (_, p1) => String.fromCharCode('0x' + p1));
    return {
        'X-Requested-With': 'XMLHttpRequest',
        'Authorization': 'Basic ' + btoa(utf8Bytes)
    };
}

async function fetchJSON(url) {
    const res = await fetch(url, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) ? data : (data.items || []);
}

async function initData() {
    try {
        const queryObj = {
            "limit": 10000,
            "columns": "ilc_skv,ilt_skv,ilc_rvr,i00_reg,i00_posle,ilc_rez_rvr,ilc_gorizont,i0d_caldate"
        };
        const url = `${API_BASE}/doc_daily_rvr?_format=json&query=${encodeURIComponent(JSON.stringify(queryObj))}`;
        const rawData = await fetchJSON(url);

        DATA = rawData.map(r => {
            const dateStr = r.i0d_caldate ? r.i0d_caldate.split(' ')[0] : '2024-01-01';
            const mParts = dateStr.split('-');
            const monthNum = mParts.length === 3 ? parseInt(mParts[1], 10) : 1;

            return {
                well: r.ilc_skv || 'Отсутствует',
                type: r.ilt_skv || 'Отсутствует',
                rvr: r.ilc_rvr || 'Отсутствует',
                reg: r.i00_reg !== null && r.i00_reg !== undefined && r.i00_reg !== '' ? parseFloat(r.i00_reg) : null,
                after: r.i00_posle !== null && r.i00_posle !== undefined && r.i00_posle !== '' ? parseFloat(r.i00_posle) : null,
                result: r.ilc_rez_rvr || '',
                horiz: r.ilc_gorizont || 'Отсутствует',
                date: dateStr,
                month: monthNum
            };
        });
        
        // Remove empty records or handle defaults
        DATA = DATA.filter(d => d.well !== 'Отсутствует' || d.result !== '');
        
        renderAll();
    } catch (err) {
        console.error(err);
        alert("Ошибка загрузки данных: " + err.message);
    }
}

function updateKpis() {
    if(!DATA.length) return;
    const kpis = document.querySelectorAll('.kpi');
    // Function to calculate unique values safely
    const uniqueVals = (arr, key) => new Set(arr.map(d=>(d[key]||'')).filter(Boolean)).size;
    
    if(kpis.length >= 6) {
        kpis[0].querySelector('.kpi-val').textContent = DATA.length;
        const horizs = uniqueVals(DATA, 'horiz');
        kpis[0].querySelector('.kpi-tag').textContent = `${horizs} горизонтов`;
        
        const wells = uniqueVals(DATA, 'well');
        kpis[1].querySelector('.kpi-val').textContent = wells;

        const pos = DATA.filter(d=>d.result==='Положительный').length;
        const posPct = Math.round(pos / DATA.length * 100) || 0;
        kpis[2].querySelector('.kpi-val').textContent = posPct + '%';
        kpis[2].querySelector('.kpi-unit').textContent = `${pos} из ${DATA.length}`;

        let intervals = [];
        const bwAll=grp(DATA,r=>r.well);
        Object.values(bwAll).forEach(evs=>{
            const sorted=evs.filter(e=>e.date).sort((a,b)=>a.date.localeCompare(b.date));
            for(let i=1;i<sorted.length;i++){
                const diff=Math.round((new Date(sorted[i].date)-new Date(sorted[i-1].date))/86400000);
                if(diff>0&&diff<400) intervals.push(diff);
            }
        });
        const avgGap = intervals.length ? Math.round(intervals.reduce((a,b)=>a+b,0)/intervals.length) : 0;
        kpis[3].querySelector('.kpi-val').textContent = avgGap;

        const maxDateRaw = Math.max(...DATA.map(d=>new Date(d.date)));
        const maxDate = new Date(maxDateRaw);
        const lastRvr=Object.entries(bwAll).map(([w,evs])=>{
            const sorted=evs.sort((a,b)=>b.date.localeCompare(a.date));
            const gap=Math.round((maxDate-new Date(sorted[0].date))/86400000);
            return gap;
        });
        const crit = lastRvr.filter(g=>g>120).length;
        kpis[4].querySelector('.kpi-val').textContent = crit;

        const withDeltas = DATA.filter(d=>d.after!==null && d.reg!==null);
        const avgDelta = withDeltas.length ? parseFloat((withDeltas.reduce((acc,d)=>acc+(d.after-d.reg),0)/withDeltas.length).toFixed(2)) : 0;
        kpis[5].querySelector('.kpi-val').textContent = (avgDelta > 0 ? '+' : '') + avgDelta;
    }
    
    // Result Donut Split
    const pos = DATA.filter(d=>d.result==='Положительный').length;
    const neg = DATA.filter(d=>d.result==='Отрицательный').length;
    const tot = pos + neg || 1;
    const pp = Math.round(pos/tot*100);
    const np = 100 - pp;
    const splitLab = document.querySelector('.split-labels');
    if (splitLab) {
        splitLab.innerHTML = `<span style="color:var(--green)">✓ Положительный — ${pos} (${pp}%)</span>
          <span style="color:var(--red)">✗ Отрицательный — ${neg} (${np}%)</span>`;
    }
    const sPos = document.querySelector('.s-pos');
    if (sPos) {
        sPos.style.width = pp + '%';
        sPos.textContent = pp + '%';
    }
    const sNeg = document.querySelector('.s-neg');
    if (sNeg) {
        sNeg.style.width = np + '%';
        sNeg.textContent = np + '%';
    }
    
    // Total table records label
    const tableSpan = document.querySelector('#pg-table .card-head span');
    if (tableSpan) {
        tableSpan.textContent = DATA.length + ' записей';
    }
    
    const hPeriod = document.querySelector('.h-period');
    if(hPeriod) hPeriod.textContent = 'Live Data';
}

function renderAll() {
    renderOverview();
    renderAnalysis();
    renderTimeline();
    renderHeatmap();
    renderAlerts();
    renderTable();
    updateKpis();
}
"""

split1 = html.split(data_start)
if len(split1) > 1:
    split2 = split1[1].split(data_end)
    html = split1[0] + data_new + data_end + split2[1]

html = html.replace("(function(){\n  const byMonth", "function renderOverview() {\n  if(!DATA.length) return;\n  const byMonth")
html = html.replace("})();\n\n// ═══════════════════════════════════════\n// RVR ANALYSIS", "}\n\n// ═══════════════════════════════════════\n// RVR ANALYSIS")

html = html.replace("(function(){\n  const rvrG=grp(DATA,r=>r.rvr);", "function renderAnalysis() {\n  if(!DATA.length) return;\n  const rvrG=grp(DATA,r=>r.rvr);")
html = html.replace("})();\n\n// ═══════════════════════════════════════\n// TIMELINE", "}\n\n// ═══════════════════════════════════════\n// TIMELINE")

html = html.replace("(function(){\n  const TOTAL=366", "function renderTimeline() {\n  if(!DATA.length) return;\n  const TOTAL=366")
html = html.replace("})();\n\n// ═══════════════════════════════════════\n// HEATMAP", "}\n\n// ═══════════════════════════════════════\n// HEATMAP")

html = html.replace("(function(){\n  const horizs=", "function renderHeatmap() {\n  if(!DATA.length) return;\n  const horizs=")
html = html.replace("})();\n\n// ═══════════════════════════════════════\n// ALERTS", "}\n\n// ═══════════════════════════════════════\n// ALERTS")

html = html.replace("(function(){\n  const byWell=grp(DATA,r=>r.well);\n  const lastRvr", "function renderAlerts() {\n  if(!DATA.length) return;\n  const byWell=grp(DATA,r=>r.well);\n  const lastRvr")
html = html.replace("})();\n\n// ═══════════════════════════════════════\n// TABLE", "}\n\n// ═══════════════════════════════════════\n// TABLE")

html = html.replace("(function(){\n  const sorted=", "function renderTable() {\n  if(!DATA.length) return;\n  const tbody=document.getElementById('tbl-body');\n  tbody.innerHTML='';\n  const sorted=")
html = html.replace("})();\n\n// ═══════════════════════════════════════\n// TABS", "}\n\n// ═══════════════════════════════════════\n// TABS")

def repl_analysis(m):
    return 'Результативность по горизонту</div>\n      <div id="horiz-res-list" style="display:flex;flex-direction:column;gap:9px;margin-top:2px">\n      </div>\n    </div>\n  </div>\n\n</div>\n\n<!-- ══════════════════════════════════ ТАЙМЛАЙН'

html = re.sub(r'Результативность по горизонту</div>.*?<!-- ══════════════════════════════════ ТАЙМЛАЙН', repl_analysis, html, flags=re.DOTALL)

analysis_inject = """  const deltas=rk.map(k=>{ const g=rvrG[k].filter(r=>r.after!==null&&r.reg!==null); return g.length?+(g.reduce((s,r)=>s+(r.after-r.reg),0)/g.length).toFixed(3):0; });
  new Chart(document.getElementById('c-rvr-delta'),{
    type:'bar',
    data:{
      labels:rk,
      datasets:[{ data:deltas,
        backgroundColor:deltas.map(v=>v>=0?'rgba(15,113,68,.2)':'rgba(185,28,28,.18)'),
        borderColor:deltas.map(v=>v>=0?'#0f7144':'#b91c1c'), borderWidth:1.5, borderRadius:5 }],
    },
    options:{ ...bo(), plugins:{ legend:{display:false}, tooltip:{...TT,callbacks:{label:d=>`Δ ${d.raw>=0?'+':''}${d.raw}`}} } },
  });
  
  const hl=document.getElementById('horiz-res-list');
  if(hl) {
      hl.innerHTML = '';
      const hG=grp(DATA,r=>r.horiz);
      Object.keys(hG).forEach(hName=>{
          const g=hG[hName];
          const pos = g.filter(r=>r.result==='Положительный').length;
          const neg = g.filter(r=>r.result==='Отрицательный').length;
          const pct = Math.round(pos/g.length*100)||0;
          let bdgCls = 'bdg-neu'; let barColor = 'var(--red-m)';
          if(pct>60) { bdgCls='bdg-ok'; barColor='var(--green-m)'; }
          else if(pct>40) { bdgCls='bdg-warn'; barColor='var(--amber-m)'; }
          hl.innerHTML += `<div class="horiz-card">
          <div class="hc-row"><span class="hc-name">${hName}</span><span class="bdg ${bdgCls}">${pct}%</span></div>
          <div class="hc-meta">${g.length} РВР · <span style="color:var(--green)">${pos} положит.</span> · <span style="color:var(--red)">${neg} отрицат.</span></div>
          <div class="mini-bar"><div class="mini-fill" style="width:${pct}%;background:${barColor}"></div></div>
        </div>`;
      });
  }"""

html = html.replace("""  const deltas=rk.map(k=>{ const g=rvrG[k].filter(r=>r.after!==null&&r.reg!==null); return g.length?+(g.reduce((s,r)=>s+(r.after-r.reg),0)/g.length).toFixed(3):0; });
  new Chart(document.getElementById('c-rvr-delta'),{
    type:'bar',
    data:{
      labels:rk,
      datasets:[{ data:deltas,
        backgroundColor:deltas.map(v=>v>=0?'rgba(15,113,68,.2)':'rgba(185,28,28,.18)'),
        borderColor:deltas.map(v=>v>=0?'#0f7144':'#b91c1c'), borderWidth:1.5, borderRadius:5 }],
    },
    options:{ ...bo(), plugins:{ legend:{display:false}, tooltip:{...TT,callbacks:{label:d=>`Δ ${d.raw>=0?'+':''}${d.raw}`}} } },
  });""", analysis_inject)


html = html.replace("</script>\n</body>", "\n// Initialize\ndocument.addEventListener('DOMContentLoaded', initData);\n</script>\n</body>")
html = html.replace("2024-01-01 → 2024-12-31", "Live Data")

with open('c:/DISK_DATA/antigravity/tests_vinkom/mrc.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Conversion successful")
