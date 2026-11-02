"""Local visual launcher for keep-data-sim.

Only the trusted local simulator module is launched. User values are passed as
an argv list to subprocess.Popen; no shell command is constructed or parsed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
HOST, PORT = "127.0.0.1", 8765

HTML = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Keep Data Simulator · 本地控制台</title>
<style>
:root{--bg:#f4f7f9;--card:#fff;--ink:#14232c;--muted:#62717b;--brand:#007f70;--line:#dce5e8;--danger:#a83d3d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink)}
.wrap{max-width:1120px;margin:0 auto;padding:26px}.head{display:flex;justify-content:space-between;gap:20px;align-items:flex-end;margin-bottom:20px}.eyebrow{color:var(--brand);font-weight:700;letter-spacing:.14em;font-size:12px}.head h1{margin:5px 0 0;font-size:30px}.head p{color:var(--muted);margin:5px 0 0}.badge{background:#e2f2ef;color:#006d60;padding:6px 11px;border-radius:99px;font-size:12px;font-weight:700;white-space:nowrap}
.grid{display:grid;grid-template-columns:minmax(0,1fr) 350px;gap:18px}.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 7px 22px #18333d0b}.card h2{font-size:18px;margin:0 0 15px}.section{border-top:1px solid var(--line);padding-top:15px;margin-top:18px}.section h3{font-size:14px;margin:0 0 10px;color:var(--brand)}.fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.field label{display:block;font-size:12px;color:var(--muted);margin-bottom:4px}.field input,.field select{width:100%;padding:9px 10px;border:1px solid #cbd8dc;border-radius:9px;font:inherit;background:white}.wide{grid-column:1/-1}.hint{font-size:12px;color:var(--muted);margin:12px 0}.check{display:flex;gap:8px;align-items:center}.check input{width:auto}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}button{border:0;border-radius:9px;padding:10px 15px;background:var(--brand);color:white;font-weight:700;cursor:pointer}button.secondary{background:#e7eeee;color:#13554d}button:disabled{opacity:.55;cursor:wait}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:15px 0}.metric{background:#f1f7f6;border-radius:10px;padding:10px}.metric b{display:block;font-size:19px}.metric small{color:var(--muted)}pre{white-space:pre-wrap;overflow:auto;background:#15252a;color:#d8f5eb;border-radius:10px;padding:13px;font:12px/1.45 ui-monospace,monospace;min-height:62px}.status{border-radius:10px;padding:12px;background:#eef4f5;color:#36505a;white-space:pre-wrap}.status.error{background:#fff0f0;color:var(--danger)}.audit{font-size:13px;color:#52636b}.audit strong{color:var(--ink)}.footer{color:var(--muted);font-size:12px;margin-top:16px}@media(max-width:820px){.grid{grid-template-columns:1fr}.fields{grid-template-columns:1fr}.wide{grid-column:auto}.head{display:block}.badge{display:inline-block;margin-top:10px}}
</style></head><body><main class="wrap">
<header class="head"><div><div class="eyebrow">KEEP DATA SIMULATOR · LOCAL ONLY</div><h1>运动数据生成控制台</h1><p>按配置生成 GPX / FIT 文件，并显示将要执行的安全参数。</p></div><div class="badge">仅本机执行 · 不改写 Keep</div></header>
<div class="grid"><section class="card"><h2>活动配置</h2><form id="form">
<div class="fields"><div class="field"><label>运动类型</label><select name="sport"><option value="running">跑步</option><option value="cycling">骑行</option></select></div>
<div class="field"><label>目标距离（米）</label><input name="distance" type="number" min="1" step="1" value="5000"></div>
<div class="field"><label>跑步配速（分/公里）</label><input name="pace" value="5:30" pattern="[0-9]+(:[0-5][0-9])?" title="例如 5:30"></div>
<div class="field"><label>骑行速度（km/h）</label><input name="speed" type="number" min="5" max="60" step="0.1" value="25"></div>
<div class="field"><label>开始时间（UTC，可选）</label><input name="start-time" placeholder="2026-10-26 06:00:00"></div>
<div class="field"><label>时区</label><input name="timezone" value="Asia/Shanghai"></div>
<div class="field"><label>起点纬度</label><input name="start-lat" type="number" min="-90" max="90" step="0.000001" value="39.9042"></div>
<div class="field"><label>起点经度</label><input name="start-lon" type="number" min="-180" max="180" step="0.000001" value="116.4074"></div>
<div class="field"><label>活动标题</label><input name="title" value="Morning Run"></div><div class="field"><label>随机种子（可选）</label><input name="seed" type="number" step="1" value="42"></div></div>
<div class="section"><h3>路线与节奏</h3><div class="fields"><div class="field"><label>路线类型</label><select name="route-type"><option>circular</option><option>out_and_back</option><option>waypoint</option><option>gpx_import</option><option>coord_file</option><option>hand_drawn</option></select></div>
<div class="field"><label>环形半径（米）</label><input name="route-radius" type="number" min="1" value="2000"></div><div class="field"><label>GPS 噪声（米）</label><input name="gps-noise" type="number" min="0" value="3"></div><div class="field"><label>点间距（米）</label><input name="point-spacing" type="number" min="1" value="10"></div>
<div class="field"><label>配速策略</label><select name="pace-strategy"><option>constant</option><option>negative_split</option><option>positive_split</option><option>interval</option></select></div><div class="field"><label>步频/踏频平均值</label><input name="cadence-avg" type="number" min="1" value="170"></div>
<div class="field"><label>途经点（lat,lon;lat,lon）</label><input name="waypoints" placeholder="可选"></div><div class="field"><label>导入路线文件</label><input name="import-file" placeholder="可选，本地绝对路径"></div></div></div>
<div class="section"><h3>生理指标与输出</h3><div class="fields"><div class="field"><label>平均心率</label><input name="hr-avg" type="number" min="30" max="240" value="145"></div><div class="field"><label>最大心率</label><input name="hr-max" type="number" min="40" max="250" value="190"></div><div class="field"><label>总爬升（米）</label><input name="elevation-gain" type="number" min="0" value="50"></div><div class="field"><label>输出目录</label><input name="output-dir" value="outputs"></div><div class="field"><label>输出格式</label><select name="format"><option value="">GPX + FIT</option><option value="gpx">仅 GPX</option><option value="fit">仅 FIT</option></select></div></div><p class="hint check"><input name="treadmill" type="checkbox">跑步机模式（仅 FIT，无 GPS）</p><p class="hint check"><input name="dry-run" type="checkbox">只预览，不写文件</p></div>
<div class="actions"><button type="button" id="preview">预览命令</button><button type="submit" id="run">生成文件</button><button type="button" class="secondary" id="clear">清空日志</button></div></form></section>
<aside><section class="card"><h2>命令预览</h2><pre id="command">填写配置后点击预览。</pre><div class="summary"><div class="metric"><b id="distanceOut">5.00</b><small>公里</small></div><div class="metric"><b id="durationOut">45:50</b><small>预计时长</small></div><div class="metric"><b id="formatOut">GPX + FIT</b><small>输出</small></div></div><div class="status" id="status">等待操作。生成前会在此显示摘要和结果。</div></section><section class="card"><h2>安全审查</h2><div class="audit"><p><strong>已检查：</strong>项目核心源码未发现 shell 命令执行、网络客户端、socket、动态 eval/exec、凭据读取、混淆或删除文件逻辑。</p><p><strong>运行边界：</strong>界面只调用项目的 <code>python -m keep_data_sim</code>，使用参数数组，不经 shell；输出写入你指定的本地目录。</p><p><strong>依赖：</strong>gpxpy、garmin-fit-sdk、numpy、tzdata。依赖安装前应查看其来源；本界面不会自动安装。</p><p><strong>用途：</strong>生成通用测试文件，是否能被 Keep 导入取决于 Keep 当前版本的导入支持与校验。手绘地图工具另外会加载 Leaflet 和 OpenStreetMap 地图资源。</p></div></section></aside></div><div class="footer">本地地址 127.0.0.1 · 不上传配置和运动数据</div></main>
<script>
const f=document.querySelector('#form'),cmd=document.querySelector('#command'),status=document.querySelector('#status');
const esc=v=>{v=String(v??'');return /[\s"]/.test(v)?'"'+v.replaceAll('"','\\"')+'"':v};
function vals(){return Object.fromEntries(new FormData(f).entries())}
function argv(){const v=vals(), a=['python','-m','keep_data_sim','--sport',v.sport,'--distance',v.distance,'--timezone',v.timezone,'--start-lat',v['start-lat'],'--start-lon',v['start-lon'],'--route-type',v['route-type'],'--route-radius',v['route-radius'],'--gps-noise',v['gps-noise'],'--point-spacing',v['point-spacing'],'--pace-strategy',v['pace-strategy'],'--hr-avg',v['hr-avg'],'--hr-max',v['hr-max'],'--elevation-gain',v['elevation-gain'],'--output-dir',v['output-dir']];
if(v.sport==='running')a.push('--pace',v.pace);else a.push('--speed',v.speed);
if(v['start-time'])a.push('--start-time',v['start-time']);if(v.title)a.push('--title',v.title);if(v.seed)a.push('--seed',v.seed);if(v['cadence-avg'])a.push('--cadence-avg',v['cadence-avg']);if(v.waypoints)a.push('--waypoints',v.waypoints);if(v['import-file'])a.push('--import-file',v['import-file']);if(v.format)a.push('--format',v.format);if(v.treadmill)a.push('--treadmill');if(v['dry-run'])a.push('--dry-run');return a}
function preview(){const v=vals(),a=argv();cmd.textContent=a.map(esc).join(' ');let km=Number(v.distance)/1000;let pace=v.sport==='running'?v.pace.split(':').reduce((x,n,i)=>x+(i?Number(n)/60:Number(n)),0):60/Number(v.speed);let sec=km*pace*60;document.querySelector('#distanceOut').textContent=Number.isFinite(km)?km.toFixed(2):'—';document.querySelector('#durationOut').textContent=Number.isFinite(sec)&&sec>=0&&sec<86400000?new Date(sec*1000).toISOString().slice(11,19):'—';document.querySelector('#formatOut').textContent=v.treadmill?'FIT':(v.format==='gpx'?'GPX':v.format==='fit'?'FIT':'GPX + FIT');}
f.addEventListener('input',preview);document.querySelector('#preview').onclick=()=>{preview();status.className='status';status.textContent='命令已生成，检查参数后点击“生成文件”。'};document.querySelector('#clear').onclick=()=>{status.textContent='日志已清空。';cmd.textContent='';};f.onsubmit=async e=>{e.preventDefault();preview();const b=document.querySelector('#run');b.disabled=true;status.className='status';status.textContent='正在本地执行，请稍候…';try{const r=await fetch('/api/run',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({argv:argv().slice(3),dryRun:!!vals()['dry-run']})});const j=await r.json();status.textContent=(j.ok?'完成\n':'失败\n')+(j.output||j.error||'无输出');if(!j.ok)status.className='status error';}catch(x){status.className='status error';status.textContent='无法连接本地服务：'+x}finally{b.disabled=false}};preview();
</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[gui]", fmt % args)

    def do_GET(self):
        if urlparse(self.path).path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/run": self.send_error(404); return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 20000: raise ValueError("请求过大")
            payload = json.loads(self.rfile.read(size))
            args = payload.get("argv")
            if not isinstance(args, list) or not all(isinstance(x, str) for x in args): raise ValueError("参数格式无效")
            allowed = {"--sport","--distance","--pace","--speed","--timezone","--start-time","--start-lat","--start-lon","--title","--seed","--route-type","--route-radius","--gps-noise","--point-spacing","--waypoints","--import-file","--pace-strategy","--cadence-avg","--hr-avg","--hr-max","--elevation-gain","--output-dir","--format","--treadmill","--dry-run"}
            if any(x.startswith("--") and x not in allowed for x in args): raise ValueError("包含不支持的选项")
            if any(x.startswith("-") and x not in allowed and x not in {"running","cycling","circular","out_and_back","waypoint","gpx_import","coord_file","hand_drawn","constant","negative_split","positive_split","interval"} for x in args): raise ValueError("包含异常参数")
            # Dry-run is always available as a safe preview; output is captured and bounded.
            command = [sys.executable, "-m", "keep_data_sim", *args]
            safe_env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"}}
            safe_env["PYTHONNOUSERSITE"] = "1"
            proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180, shell=False, env=safe_env)
            output = (proc.stdout + ("\n" + proc.stderr if proc.stderr else "")).strip()
            result = {"ok": proc.returncode == 0, "output": output[-12000:], "returncode": proc.returncode}
        except subprocess.TimeoutExpired:
            result = {"ok": False, "error": "执行超过 180 秒，已终止"}
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        data=json.dumps(result, ensure_ascii=False).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

def main():
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    print(f"Keep Data Simulator GUI: http://{HOST}:{PORT}")
    threading.Timer(.35, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == "__main__": main()
