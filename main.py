import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import secrets
import socket
import time
import urllib.parse

import aiofiles
import httpx
import uvicorn

from collections import deque, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, Depends, APIRouter
from fastapi.responses import Response, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Sadra-Sadra")

# ==============================================================================
# HTML Templates & Branding
# ==============================================================================

# لوگوی وکتور کلاه Sadra (بدون نیاز به base64 سنگین)
LOGO_SVG = """<svg viewBox="0 0 84 68" fill="none" style="width:100%;height:100%;background:#0c0c10">
  <ellipse cx="42" cy="52" rx="40" ry="11" fill="#C8900A" opacity=".85"/>
  <ellipse cx="42" cy="52" rx="40" ry="11" fill="none" stroke="#FFD700" stroke-width="1.4" opacity=".6"/>
  <path d="M19 50 Q21 22 42 17 Q63 22 65 50" fill="#D4960C" stroke="#FFD700" stroke-width="1.4"/>
  <ellipse cx="42" cy="17" rx="23" ry="5.5" fill="#C8900A" stroke="#FFD700" stroke-width="1"/>
  <path d="M20 45 Q21.5 41.5 42 39.5 Q62.5 41.5 64 45" fill="none" stroke="#CC2200" stroke-width="4.5" stroke-linecap="round" opacity=".92"/>
</svg>"""

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ورود · Sadra Panel</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700&family=Cinzel:wght@700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#060608;--card:#0c0c10;--accent:#FFD700;--text:rgba(255,255,255,0.92);--dim:rgba(255,255,255,0.4);--mid:rgba(255,215,0,0.7);--border:rgba(255,215,0,0.15)}
html,body{height:100%;overflow:hidden}
body{font-family:'Vazirmatn',sans-serif;background:var(--bg);display:flex;align-items:center;justify-content:center;padding:20px}
.bg{position:fixed;inset:0;background:radial-gradient(ellipse 80% 60% at 50% 0%,rgba(255,215,0,0.05),transparent 70%),var(--bg);z-index:0}
.grid{position:fixed;inset:0;background-image:linear-gradient(rgba(255,215,0,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,215,0,0.04) 1px,transparent 1px);background-size:44px 44px;z-index:0}
.wrap{position:relative;z-index:10;width:100%;max-width:400px}
.card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:38px 34px 34px;backdrop-filter:blur(24px);box-shadow:0 0 80px rgba(255,215,0,0.05),0 20px 60px rgba(0,0,0,.5)}
.brand{display:flex;align-items:center;gap:14px;margin-bottom:28px}
.brand-img{width:48px;height:48px;border-radius:50%;overflow:hidden;border:1px solid var(--border);box-shadow:0 0 20px rgba(255,215,0,0.15);flex-shrink:0}
.brand-name{font-size:18px;font-weight:700;font-family:'Cinzel',serif;color:var(--accent);letter-spacing:1px}
.brand-sub{font-size:11px;color:var(--dim);margin-top:2px}
h1{font-size:21px;font-weight:700;color:var(--text);margin-bottom:5px;letter-spacing:-.02em}
.sub{font-size:12px;color:var(--mid);margin-bottom:24px;line-height:1.6}
.hint{display:flex;align-items:center;gap:10px;background:rgba(255,215,0,0.05);border:1px solid rgba(255,215,0,0.15);border-radius:10px;padding:10px 14px;margin-bottom:20px}
.hint-label{font-size:11px;color:var(--dim);flex:1}
.hint-val{font-family:ui-monospace,monospace;font-size:14px;font-weight:700;color:var(--accent);background:rgba(255,215,0,0.1);border:1px solid rgba(255,215,0,0.25);padding:3px 11px;border-radius:7px;cursor:pointer;transition:.15s;letter-spacing:.08em}
.hint-val:hover{background:rgba(255,215,0,0.22)}
.field{margin-bottom:18px}
.field label{display:block;font-size:10.5px;font-weight:600;color:var(--mid);margin-bottom:7px;text-transform:uppercase;letter-spacing:.06em}
.inp-wrap{position:relative}
input[type=password]{width:100%;padding:13px 44px 13px 16px;border-radius:11px;border:1px solid var(--border);background:rgba(0,0,0,.3);color:var(--text);font-family:inherit;font-size:14px;outline:none;transition:.2s}
input[type=password]:focus{border-color:rgba(255,215,0,.55);background:rgba(0,0,0,.4);box-shadow:0 0 0 3px rgba(255,215,0,.1)}
.ic{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--dim);font-size:18px;pointer-events:none;transition:.2s}
input:focus+.ic{color:var(--accent)}
.err{display:none;background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2);border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:12px;color:#F87171;align-items:center;gap:8px}
.err.show{display:flex}
.btn{width:100%;padding:13px;border-radius:11px;border:none;cursor:pointer;background:linear-gradient(135deg,#FFD700,#C8900A);color:#000;font-family:inherit;font-size:14px;font-weight:700;display:flex;align-items:center;justify-content:center;gap:8px;box-shadow:0 4px 20px rgba(255,215,0,.15);transition:.2s}
.btn:hover{filter:brightness(1.1)}
.btn:disabled{opacity:.5;cursor:not-allowed}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="bg"></div><div class="grid"></div>
<div class="wrap">
  <div class="card">
    <div class="brand">
      <div class="brand-img">__LOGO_SVG__</div>
      <div><div class="brand-name">Sadra PANEL</div><div class="brand-sub">Powered by Sadra v9.5</div></div>
    </div>
    <h1>ورود به پنل</h1>
    <p class="sub">رمز عبور را برای دسترسی به داشبورد وارد کنید</p>
    <div class="err" id="err"><i class="ti ti-alert-circle"></i><span id="err-text"></span></div>
    <div class="hint">
      <span class="hint-label">رمز پیش‌فرض سیستم</span>
      <span class="hint-val" onclick="document.getElementById('pw').value='admin';document.getElementById('pw').focus()">admin</span>
    </div>
    <form id="form">
      <div class="field">
        <label>رمز عبور</label>
        <div class="inp-wrap">
          <input type="password" id="pw" placeholder="رمز عبور را وارد کنید" autofocus required>
          <i class="ti ti-lock ic"></i>
        </div>
      </div>
      <button class="btn" type="submit" id="btn"><i class="ti ti-login-2"></i> ورود به داشبورد</button>
    </form>
  </div>
</div>
<script>
document.getElementById('form').addEventListener('submit',async e=>{
  e.preventDefault();
  const btn=document.getElementById('btn'),err=document.getElementById('err'),et=document.getElementById('err-text');
  err.classList.remove('show');btn.disabled=true;
  btn.innerHTML='<i class="ti ti-loader-2" style="animation:spin 1s linear infinite"></i> در حال ورود...';
  try{
    const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:document.getElementById('pw').value})});
    if(!r.ok){const d=await r.json().catch(()=>({}));throw new Error(d.detail||'خطا');}
    location.href='/dashboard';
  }catch(e){
    et.textContent=e.message;err.classList.add('show');
    btn.disabled=false;btn.innerHTML='<i class="ti ti-login-2"></i> ورود به داشبورد';
  }
});
</script>
</body></html>"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sadra Panel</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800&family=Cinzel:wght@700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#060608;--bg2:#0a0a0e;--bg3:#121218;
  --card:#0c0c10;--card-b:rgba(255,215,0,0.15);--card-bh:rgba(255,215,0,0.35);
  --accent:#FFD700;--accent2:#C8900A;--accent-d:rgba(255,215,0,0.12);
  --green:#4ade80;--green-bg:rgba(74,222,128,0.1);--green-t:#4ade80;
  --red:#f87171;--red-bg:rgba(248,113,113,0.1);--red-t:#f87171;
  --amber:#F59E0B;--amber-bg:rgba(245,158,11,0.1);--amber-t:#FCD34D;
  --purple:#F59E0B;--purple-bg:rgba(245,158,11,0.1);
  --t1:rgba(255,255,255,0.95);--t2:rgba(255,215,0,0.8);--t3:rgba(255,255,255,0.4);
  --sidebar-w:248px;--radius:16px;
  --shadow:0 4px 24px rgba(255,215,0,0.05);
}
[data-theme="light"]{
  --bg:#f0f2f5;--bg2:#ffffff;--bg3:#e4e6eb;
  --card:#ffffff;--card-b:rgba(0,0,0,0.1);--card-bh:rgba(0,0,0,0.25);
  --accent:#DAA520;--accent2:#B8860B;--accent-d:rgba(218,165,32,0.15);
  --green:#059669;--green-bg:rgba(5,150,105,0.08);--green-t:#065F46;
  --red:#DC2626;--red-bg:rgba(220,38,38,0.08);--red-t:#991B1B;
  --amber:#D97706;--amber-bg:rgba(217,119,6,0.08);--amber-t:#92400E;
  --purple:#D97706;--purple-bg:rgba(217,119,6,0.08);
  --t1:#111827;--t2:#4b5563;--t3:#6b7280;
  --shadow:0 4px 20px rgba(0,0,0,0.1);
}
html,body{height:100%}
body{font-family:'Vazirmatn',sans-serif;background:var(--bg);color:var(--t1);min-height:100vh;display:flex;font-size:14px;transition:background .3s,color .3s}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--bg3);border-radius:3px}
a{color:inherit;text-decoration:none}
.sidebar{width:var(--sidebar-w);min-height:100vh;background:var(--bg2);border-left:1px solid var(--card-b);display:flex;flex-direction:column;flex-shrink:0;position:fixed;right:0;top:0;bottom:0;z-index:200;transition:transform .25s cubic-bezier(.4,0,.2,1),background .3s,border-color .3s}
.logo{display:flex;align-items:center;gap:12px;padding:20px 16px 16px;border-bottom:1px solid var(--card-b)}
.logo-img{width:38px;height:38px;border-radius:50%;overflow:hidden;border:1px solid var(--card-b);box-shadow:0 0 14px rgba(255,215,0,.15);flex-shrink:0}
.logo-name{font-size:16px;font-weight:900;font-family:'Cinzel',serif;color:var(--accent);letter-spacing:1px}
.logo-sub{font-size:10px;color:var(--t3);margin-top:1px}
.sb-close{display:none;position:absolute;left:12px;top:20px;background:var(--accent-d);border:1px solid var(--card-b);color:var(--t2);width:30px;height:30px;border-radius:8px;font-size:16px;align-items:center;justify-content:center;cursor:pointer}
.nav-wrap{flex:1;overflow-y:auto;padding:6px 0 8px}
.nav-sec{padding:14px 14px 4px;font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--t3);font-weight:700}
.nav-it{display:flex;align-items:center;gap:9px;padding:9px 14px;color:var(--t3);font-size:12.5px;cursor:pointer;border-right:2px solid transparent;transition:all .15s;margin:1px 6px}
.nav-it i{font-size:16px;width:18px;text-align:center;flex-shrink:0}
.nav-it:hover{background:var(--accent-d);color:var(--t2)}
.nav-it.on{background:var(--accent-d);color:var(--accent);border-right-color:var(--accent);font-weight:600}
.nav-badge{margin-right:auto;background:rgba(255,215,0,0.15);color:var(--accent);font-size:9px;padding:1px 6px;border-radius:20px;font-weight:700}
.sb-foot{padding:12px 14px;border-top:1px solid var(--card-b)}
.theme-btn{display:flex;align-items:center;justify-content:center;gap:7px;background:var(--accent-d);color:var(--t2);border-radius:9px;padding:8px;font-size:12px;font-weight:500;font-family:inherit;border:1px solid var(--card-b);cursor:pointer;width:100%;transition:.15s;margin-bottom:7px}
.theme-btn:hover{background:var(--card-b);color:var(--t1)}
.logout-btn{display:flex;align-items:center;justify-content:center;gap:7px;background:var(--red-bg);color:var(--red-t);border-radius:9px;padding:8px;font-size:12px;font-weight:500;font-family:inherit;border:1px solid rgba(239,68,68,0.2);cursor:pointer;width:100%;transition:.15s;margin-top:6px}
.logout-btn:hover{background:rgba(239,68,68,0.2)}
.mob-top{display:none;position:fixed;top:0;right:0;left:0;height:52px;background:var(--bg2);border-bottom:1px solid var(--card-b);z-index:150;align-items:center;justify-content:space-between;padding:0 14px;transition:background .3s}
.mob-top .ml{display:flex;align-items:center;gap:9px}
.mob-logo{width:28px;height:28px;border-radius:50%;overflow:hidden;box-shadow:0 0 8px rgba(255,215,0,.15)}
.mob-title{color:var(--accent);font-family:'Cinzel',serif;font-size:15px;font-weight:800}
.mob-right{display:flex;gap:6px}
.menu-btn,.theme-mob{background:var(--accent-d);border:1px solid var(--card-b);color:var(--t2);width:34px;height:34px;border-radius:8px;font-size:17px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:.15s}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:190;backdrop-filter:blur(3px)}
.overlay.show{display:block}
.main{margin-right:var(--sidebar-w);flex:1;padding:28px 28px 60px;min-width:0;transition:margin .25s}
.pg{display:none}
.pg.on{display:block;animation:fi .2s ease}
@keyframes fi{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.topbar{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:22px;flex-wrap:wrap;gap:12px}
.tb-title{font-size:18px;font-weight:700;color:var(--t1);display:flex;align-items:center;gap:8px;letter-spacing:-.02em}
.tb-title i{color:var(--accent);font-size:20px}
.tb-sub{font-size:11px;color:var(--t3);margin-top:4px}
.tb-right{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.badge{font-size:10px;padding:3px 10px;border-radius:20px;font-weight:700;display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
.bg-green{background:var(--green-bg);color:var(--green-t)}
.bg-blue{background:var(--accent-d);color:var(--accent)}
.bg-amber{background:var(--amber-bg);color:var(--amber-t)}
.bg-red{background:var(--red-bg);color:var(--red-t)}
.bg-purple{background:var(--purple-bg);color:var(--purple-t)}
.dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;display:inline-block}
.dg{background:var(--green)}.dr{background:var(--red)}.da{background:var(--amber)}.db{background:var(--accent)}
.pulse{animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin-bottom:18px}
.metric{background:var(--card);border:1px solid var(--card-b);border-radius:var(--radius);padding:17px 17px 14px;transition:all .2s;position:relative;overflow:hidden;cursor:default}
.metric::after{content:'';position:absolute;top:0;right:0;width:3px;height:100%;background:var(--accent);opacity:0;transition:.2s}
.metric:hover{border-color:var(--card-bh);transform:translateY(-2px);box-shadow:var(--shadow)}
.metric:hover::after{opacity:1}
.metric.suc::after{background:var(--green)}
.metric.dan::after{background:var(--red)}

.traf-hero{display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr;gap:13px;margin-bottom:18px}
.traf-main-stat{background:linear-gradient(155deg,var(--bg3) 0%,var(--card) 60%);border:1px solid var(--card-b);border-radius:20px;padding:22px 24px;position:relative;overflow:hidden}
.traf-main-stat::before{content:'';position:absolute;top:-50px;left:-50px;width:200px;height:200px;background:radial-gradient(circle,var(--accent-d),transparent 70%);pointer-events:none}
.traf-main-label{font-size:10.5px;color:var(--t3);font-weight:700;text-transform:uppercase;letter-spacing:.08em;display:flex;align-items:center;gap:6px;margin-bottom:10px;position:relative;z-index:1}
.traf-main-val{font-size:34px;font-weight:800;color:var(--t1);line-height:1;letter-spacing:-.02em;display:flex;align-items:baseline;gap:6px;position:relative;z-index:1}
.traf-main-val span{font-size:14px;font-weight:500;color:var(--t3)}
.traf-trend{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:700;padding:4px 10px;border-radius:20px;margin-top:12px;position:relative;z-index:1}
.traf-trend.up{background:var(--green-bg);color:var(--green-t)}
.traf-trend.down{background:var(--red-bg);color:var(--red-t)}
.traf-mini{background:var(--card);border:1px solid var(--card-b);border-radius:20px;padding:18px 19px;display:flex;flex-direction:column;justify-content:space-between;transition:.2s}
.traf-mini:hover{border-color:var(--card-bh);transform:translateY(-2px)}
.traf-mini-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.traf-mini-icon{width:32px;height:32px;border-radius:9px;background:var(--accent-d);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:15px}
.traf-mini-icon.pk{background:var(--amber-bg);color:var(--amber-t)}
.traf-mini-icon.lo{background:var(--purple-bg);color:var(--purple-t)}
.traf-mini-label{font-size:9.5px;color:var(--t3);font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.traf-mini-val{font-size:21px;font-weight:800;color:var(--t1);letter-spacing:-.01em}
.traf-mini-sub{font-size:9.5px;color:var(--t3);margin-top:3px}

.traf-chart-card{background:var(--card);border:1px solid var(--card-b);border-radius:22px;padding:22px 24px 18px;box-shadow:var(--shadow);margin-bottom:16px}
.traf-chart-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;flex-wrap:wrap;gap:10px}
.traf-chart-title{font-size:14px;font-weight:800;color:var(--t1);display:flex;align-items:center;gap:8px}
.traf-chart-title i{color:var(--accent);font-size:18px}
.traf-chart-sub{font-size:10.5px;color:var(--t3);margin-top:3px}
.traf-legend{display:flex;gap:14px;align-items:center}
.traf-legend-item{display:flex;align-items:center;gap:6px;font-size:10.5px;color:var(--t2);font-weight:600}
.traf-legend-dot{width:8px;height:8px;border-radius:3px}
.traf-chart-body{height:320px;margin-top:14px;position:relative}

@media(max-width:900px){.traf-hero{grid-template-columns:1fr 1fr}}
@media(max-width:520px){.traf-hero{grid-template-columns:1fr}.traf-chart-body{height:260px}}
.m-icon{width:34px;height:34px;border-radius:8px;background:var(--accent-d);display:flex;align-items:center;justify-content:center;margin-bottom:11px;color:var(--accent);font-size:17px}
.m-icon.suc{background:var(--green-bg);color:var(--green)}
.m-icon.dan{background:var(--red-bg);color:var(--red)}
.m-icon.pur{background:var(--purple-bg);color:var(--purple)}
.m-label{font-size:10px;color:var(--t3);margin-bottom:4px;font-weight:600;text-transform:uppercase;letter-spacing:.05em}
.m-val{font-size:25px;font-weight:700;color:var(--t1);line-height:1;letter-spacing:-.02em}
.m-unit{font-size:12px;font-weight:400;color:var(--t3)}
.m-sub{font-size:10px;color:var(--t3);margin-top:6px;display:flex;align-items:center;gap:3px}
.vless-box{background:linear-gradient(135deg,var(--bg3) 0%,var(--bg2) 100%);border:1px solid var(--card-b);border-radius:18px;padding:20px 22px;margin-bottom:18px;box-shadow:var(--shadow);position:relative;overflow:hidden;transition:background .3s}
.vless-box::before{content:'';position:absolute;top:-50px;left:-50px;width:180px;height:180px;background:radial-gradient(circle,var(--accent-d),transparent 70%);pointer-events:none}
.vl-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:13px;flex-wrap:wrap;gap:8px}
.vl-title{color:var(--t2);font-size:11px;display:flex;align-items:center;gap:6px;font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.vl-title i{color:var(--accent);font-size:15px}
.vl-code{background:rgba(0,0,0,.18);border:1px solid var(--card-b);border-radius:9px;padding:13px 15px;font-size:11px;font-family:ui-monospace,monospace;color:var(--accent);word-break:break-all;line-height:1.8;letter-spacing:.01em}
[data-theme="light"] .vl-code{background:rgba(0,0,0,.04)}
.vl-actions{display:flex;gap:8px;margin-top:13px;flex-wrap:wrap}
.btn{font-family:inherit;font-size:12px;font-weight:700;border-radius:9px;padding:8px 14px;cursor:pointer;display:inline-flex;align-items:center;gap:5px;border:none;transition:all .15s;white-space:nowrap}
.btn i{font-size:13px}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-p{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#000;box-shadow:0 2px 14px rgba(255,215,0,.15)}
.btn-p:hover{filter:brightness(1.1);box-shadow:0 4px 18px rgba(255,215,0,.25)}
.btn-o{background:transparent;border:1px solid var(--card-b);color:var(--t2)}
.btn-o:hover{background:var(--accent-d);border-color:var(--accent)}
.btn-g{background:var(--accent-d);color:var(--accent);border:1px solid var(--card-b)}
.btn-g:hover{background:rgba(255,215,0,.22)}
.btn-d{background:var(--red-bg);color:var(--red-t);border:1px solid rgba(239,68,68,.2)}
.btn-d:hover{background:rgba(239,68,68,.2)}
.btn-pur{background:var(--purple-bg);color:var(--purple-t);border:1px solid var(--card-b)}
.btn-pur:hover{background:rgba(245,158,11,.22)}
.btn-amber{background:var(--amber-bg);color:var(--amber-t);border:1px solid rgba(245,158,11,.2)}
.btn-amber:hover{background:rgba(245,158,11,.22)}
.btn-sm{padding:5px 9px;font-size:10.5px;border-radius:7px}
.btn-icon{width:30px;height:30px;padding:0;justify-content:center;border-radius:5px}
.card{background:var(--card);border:1px solid var(--card-b);border-radius:var(--radius);padding:18px 20px;transition:border-color .2s,background .3s}
.card:hover{border-color:var(--card-bh)}
.card-title{font-size:12.5px;font-weight:700;color:var(--t1);margin-bottom:15px;display:flex;align-items:center;gap:7px}
.card-title i{font-size:16px;color:var(--accent)}
.ml-auto{margin-right:auto}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin-bottom:16px}
.g3{display:grid;grid-template-columns:2fr 1fr;gap:13px;margin-bottom:16px}
.mb16{margin-bottom:16px}
.sr{display:flex;align-items:center;justify-content:space-between;padding:9px 0;border-bottom:1px solid rgba(255,215,0,0.05);font-size:12px}
.sr:last-child{border-bottom:none}
.sr-k{color:var(--t2);display:flex;align-items:center;gap:6px}
.sr-k i{font-size:13px;color:var(--t3)}
.sr-v{color:var(--t1);font-weight:600;font-size:11.5px}
.ch{position:relative;height:230px}
.ch-sm{position:relative;height:185px}
.exp-chip{font-size:9px;padding:3px 8px;border-radius:6px;font-weight:700;display:inline-flex;align-items:center;gap:3px}
.ec-ok{background:var(--green-bg);color:var(--green-t)}
.ec-warn{background:var(--amber-bg);color:var(--amber-t)}
.ec-exp{background:var(--red-bg);color:var(--red-t)}
.ec-inf{background:var(--accent-d);color:var(--accent)}
.tog{width:19px;height:34px;border-radius:19px;background:rgba(100,116,139,0.25);position:relative;cursor:pointer;transition:.2s;flex-shrink:0;border:none}
.tog::after{content:'';position:absolute;width:13px;height:13px;border-radius:50%;background:#fff;left:3px;bottom:3px;transition:.2s;box-shadow:0 1px 3px rgba(0,0,0,.3)}
.tog.on{background:var(--green)}
.tog.on::after{bottom:18px}
.form-row{display:flex;gap:9px;flex-wrap:wrap;align-items:flex-end}
.fg{display:flex;flex-direction:column;gap:5px}
.fg label{font-size:10px;color:var(--t3);font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.fi,.fs{padding:9px 12px;border-radius:9px;border:1px solid var(--card-b);background:rgba(0,0,0,.18);color:var(--t1);font-family:inherit;font-size:12px;outline:none;transition:.15s;min-width:100px}
[data-theme="light"] .fi,[data-theme="light"] .fs{background:rgba(0,0,0,.04)}
.fi::placeholder{color:var(--t3)}
.fi:focus,.fs:focus{border-color:rgba(255,215,0,.45);background:rgba(0,0,0,.25);box-shadow:0 0 0 3px rgba(255,215,0,.08)}
.fs option{background:var(--bg2)}
[data-theme="light"] .fs option{background:#fff}
.cl{background:var(--accent-d);border:1px solid var(--card-b);border-radius:10px;padding:11px 13px;font-size:11px;color:var(--t2);display:flex;gap:9px;align-items:flex-start;line-height:1.8;margin-top:12px}
.cl i{font-size:15px;color:var(--accent);margin-top:1px;flex-shrink:0}

.create-panel{background:linear-gradient(155deg,var(--bg3) 0%,var(--card) 55%);border:1px solid var(--card-b);border-radius:22px;padding:0;overflow:hidden;box-shadow:var(--shadow);margin-bottom:16px;position:relative}
.create-panel::before{content:'';position:absolute;top:-60px;left:-60px;width:220px;height:220px;background:radial-gradient(circle,var(--accent-d),transparent 70%);pointer-events:none}
.cp-head{display:flex;align-items:center;gap:13px;padding:22px 24px 18px;position:relative;z-index:1}
.cp-head-icon{width:44px;height:44px;border-radius:13px;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;color:#000;font-size:20px;flex-shrink:0;box-shadow:0 6px 18px rgba(255,215,0,.2)}
.cp-head-text{flex:1;min-width:0}
.cp-head-title{font-size:15px;font-weight:800;color:var(--t1);letter-spacing:-.01em}
.cp-head-sub{font-size:11px;color:var(--t3);margin-top:2px}
.cp-body{padding:2px 24px 22px;position:relative;z-index:1}
.cp-row{display:grid;grid-template-columns:1.3fr 1fr;gap:14px;margin-bottom:16px}
.cp-block{background:rgba(0,0,0,.14);border:1px solid var(--card-b);border-radius:14px;padding:14px 16px}
[data-theme="light"] .cp-block{background:rgba(218,165,32,.03)}
.cp-block-label{font-size:10px;font-weight:800;color:var(--t2);text-transform:uppercase;letter-spacing:.08em;display:flex;align-items:center;gap:6px;margin-bottom:11px}
.cp-block-label i{color:var(--accent);font-size:14px}
.cp-input-full{width:100%;padding:10px 13px;border-radius:10px;border:1px solid var(--card-b);background:rgba(0,0,0,.18);color:var(--t1);font-family:inherit;font-size:12.5px;outline:none;transition:.15s}
[data-theme="light"] .cp-input-full{background:#fff}
.cp-input-full:focus{border-color:rgba(255,215,0,.5);box-shadow:0 0 0 3px rgba(255,215,0,.1)}
.cp-input-full::placeholder{color:var(--t3)}
.cp-mini-row{display:flex;gap:8px;margin-top:9px}
.cp-quota-inputs{display:flex;gap:8px}
.cp-quota-inputs .cp-input-full{flex:1}
.cp-quota-inputs select.cp-input-full{flex:0 0 76px}
.chip-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}
.chip{font-size:10.5px;font-weight:700;padding:5px 12px;border-radius:8px;background:var(--accent-d);color:var(--t2);border:1px solid var(--card-b);cursor:pointer;transition:.15s;white-space:nowrap}
.chip:hover{background:rgba(255,215,0,.18);color:var(--accent)}
.chip.active{background:var(--accent);color:#000;border-color:var(--accent);box-shadow:0 3px 10px rgba(255,215,0,.25)}
.proto-cards{display:grid;grid-template-columns:repeat(auto-fit, minmax(105px, 1fr));gap:9px}
.proto-card{border:1.5px solid var(--card-b);border-radius:13px;padding:13px 10px;cursor:pointer;transition:.18s;text-align:center;position:relative;background:rgba(0,0,0,.1)}
[data-theme="light"] .proto-card{background:#fff}
.proto-card:hover{border-color:var(--card-bh);transform:translateY(-1px)}
.proto-card.active{border-color:var(--accent);background:var(--accent-d);box-shadow:0 0 0 3px rgba(255,215,0,.1)}
.proto-card.active .proto-card-check{opacity:1;transform:scale(1)}
.proto-card-check{position:absolute;top:7px;left:7px;width:16px;height:16px;border-radius:50%;background:var(--accent);color:#000;font-size:10px;display:flex;align-items:center;justify-content:center;opacity:0;transform:scale(.5);transition:.18s}
.proto-card-icon{width:32px;height:32px;border-radius:9px;background:var(--accent-d);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:16px;margin:0 auto 8px}
.proto-card.active .proto-card-icon{background:var(--accent);color:#000}
.proto-card-title{font-size:11px;font-weight:800;color:var(--t1)}
.proto-card-desc{font-size:9px;color:var(--t3);margin-top:3px;line-height:1.5}
.cp-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-top:16px;border-top:1px solid var(--card-b);flex-wrap:wrap}
.cp-footer-note{display:flex;align-items:center;gap:8px;font-size:10.5px;color:var(--t3);line-height:1.7;flex:1;min-width:220px}
.cp-footer-note i{color:var(--accent);font-size:15px;flex-shrink:0}
.cp-submit-btn{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#000;border:none;border-radius:13px;padding:13px 26px;font-family:inherit;font-size:13px;font-weight:800;cursor:pointer;display:flex;align-items:center;gap:8px;box-shadow:0 6px 20px rgba(255,215,0,.2);transition:.18s;white-space:nowrap}
.cp-submit-btn:hover{transform:translateY(-2px);box-shadow:0 10px 26px rgba(255,215,0,.3)}

.srv-panel{background:linear-gradient(155deg,var(--bg3) 0%,var(--card) 60%);border:1px solid var(--card-b);border-radius:22px;overflow:hidden;box-shadow:var(--shadow);position:relative}
.srv-panel::before{content:'';position:absolute;top:-60px;left:-60px;width:200px;height:200px;background:radial-gradient(circle,var(--accent-d),transparent 70%);pointer-events:none}
.srv-hero{display:flex;align-items:center;gap:14px;padding:22px 24px;position:relative;z-index:1;border-bottom:1px solid var(--card-b)}
.srv-hero-icon{width:50px;height:50px;border-radius:14px;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;color:#000;font-size:22px;flex-shrink:0;box-shadow:0 6px 18px rgba(255,215,0,.25)}
.srv-hero-text{flex:1;min-width:0}
.srv-hero-domain{font-size:15px;font-weight:800;color:var(--t1);word-break:break-all}
.srv-hero-sub{font-size:10.5px;color:var(--t3);margin-top:4px;display:flex;align-items:center;gap:6px}
.srv-tiles{display:grid;grid-template-columns:1fr 1fr;gap:11px;padding:20px 22px 22px;position:relative;z-index:1}
.srv-tile{display:flex;align-items:center;gap:11px;background:rgba(0,0,0,.14);border:1px solid var(--card-b);border-radius:13px;padding:12px 14px;transition:.18s}
[data-theme="light"] .srv-tile{background:rgba(218,165,32,.03)}
.srv-tile:hover{border-color:var(--card-bh);transform:translateY(-1px)}
.srv-tile-icon{width:34px;height:34px;border-radius:10px;background:var(--accent-d);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.srv-tile-text{min-width:0}
.srv-tile-label{font-size:9.5px;color:var(--t3);font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px}
.srv-tile-val{font-size:12px;font-weight:700;color:var(--t1);word-break:break-word}

.pw-panel{background:linear-gradient(155deg,var(--bg3) 0%,var(--card) 60%);border:1px solid var(--card-b);border-radius:22px;overflow:hidden;box-shadow:var(--shadow);position:relative}
.pw-panel::before{content:'';position:absolute;top:-60px;right:-60px;width:200px;height:200px;background:radial-gradient(circle,var(--purple-bg),transparent 70%);pointer-events:none}
.pw-hero{display:flex;align-items:center;gap:14px;padding:22px 24px 18px;position:relative;z-index:1}
.pw-hero-icon{width:50px;height:50px;border-radius:14px;background:linear-gradient(135deg,var(--purple),#B8860B);display:flex;align-items:center;justify-content:center;color:#000;font-size:22px;flex-shrink:0;box-shadow:0 6px 18px rgba(245,158,11,.25)}
.pw-hero-text{flex:1;min-width:0}
.pw-hero-title{font-size:15px;font-weight:800;color:var(--t1)}
.pw-hero-sub{font-size:10.5px;color:var(--t3);margin-top:3px}
.pw-body{padding:2px 24px 22px;position:relative;z-index:1}
.pw-field{position:relative;margin-bottom:13px}
.pw-field label{display:block;font-size:10px;font-weight:700;color:var(--t2);text-transform:uppercase;letter-spacing:.06em;margin-bottom:7px}
.pw-input{width:100%;padding:11px 42px 11px 14px;border-radius:11px;border:1px solid var(--card-b);background:rgba(0,0,0,.18);color:var(--t1);font-family:inherit;font-size:12.5px;outline:none;transition:.15s}
[data-theme="light"] .pw-input{background:#fff}
.pw-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-d)}
.pw-eye{position:absolute;left:12px;top:34px;background:none;border:none;color:var(--t3);cursor:pointer;font-size:16px;padding:4px;display:flex}
.pw-eye:hover{color:var(--accent)}
.pw-strength{height:4px;border-radius:3px;background:var(--accent-d);margin-top:8px;overflow:hidden;display:flex;gap:3px}
.pw-strength-seg{flex:1;height:100%;border-radius:3px;background:rgba(100,116,139,.2);transition:.25s}
.pw-strength-label{font-size:9.5px;color:var(--t3);margin-top:5px;display:flex;align-items:center;gap:5px}
.pw-reqs{display:flex;flex-wrap:wrap;gap:6px;margin-top:11px;margin-bottom:16px}
.pw-req{font-size:9.5px;padding:4px 10px;border-radius:7px;background:var(--accent-d);color:var(--t3);font-weight:600;display:flex;align-items:center;gap:4px;transition:.18s}
.pw-req.met{background:var(--green-bg);color:var(--green-t)}
.pw-submit{width:100%;justify-content:center;background:linear-gradient(135deg,var(--purple),#B8860B);color:#000;border:none;border-radius:12px;padding:12px;font-family:inherit;font-size:13px;font-weight:800;cursor:pointer;display:flex;align-items:center;gap:8px;box-shadow:0 6px 18px rgba(245,158,11,.22);transition:.18s}

.conn-hero{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}
.conn-hero-tile{background:var(--card);border:1px solid var(--card-b);border-radius:16px;padding:16px 18px;position:relative;overflow:hidden;transition:.2s}
.conn-hero-tile:hover{border-color:var(--card-bh);transform:translateY(-2px);box-shadow:var(--shadow)}
.conn-hero-tile::after{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--green),transparent)}
.conn-hero-icon{width:32px;height:32px;border-radius:9px;background:var(--green-bg);color:var(--green-t);display:flex;align-items:center;justify-content:center;font-size:15px;margin-bottom:10px}
.conn-hero-tile:nth-child(2) .conn-hero-icon{background:var(--accent-d);color:var(--accent)}
.conn-hero-tile:nth-child(3) .conn-hero-icon{background:var(--purple-bg);color:var(--purple-t)}
.conn-hero-tile:nth-child(4) .conn-hero-icon{background:var(--amber-bg);color:var(--amber-t)}
.conn-hero-label{font-size:9.5px;color:var(--t3);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}
.conn-hero-val{font-size:21px;font-weight:800;color:var(--t1);line-height:1;letter-spacing:-.02em}

.conn-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:14px;flex-wrap:wrap}
.conn-toolbar-title{font-size:12px;font-weight:800;color:var(--t2);display:flex;align-items:center;gap:7px;text-transform:uppercase;letter-spacing:.06em}
.conn-toolbar-title i{color:var(--green);font-size:15px}
.conn-live-badge{display:flex;align-items:center;gap:6px;font-size:10.5px;font-weight:700;color:var(--green-t);background:var(--green-bg);padding:5px 12px;border-radius:20px;border:1px solid rgba(74,222,128,.2)}
.conn-live-dot{width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 1.6s infinite}

.conn-grid-v2{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.conn-card-v2{background:var(--card);border:1px solid var(--card-b);border-radius:18px;padding:0;overflow:hidden;transition:all .22s cubic-bezier(.4,0,.2,1);position:relative}
.conn-card-v2:hover{border-color:var(--card-bh);transform:translateY(-3px);box-shadow:0 14px 32px rgba(255,215,0,.08)}
.conn-card-v2-glow{position:absolute;top:-40px;left:-40px;width:140px;height:140px;background:radial-gradient(circle,rgba(74,222,128,.1),transparent 70%);pointer-events:none}
.conn-card-v2-top{display:flex;align-items:center;gap:12px;padding:16px 17px 13px;position:relative;z-index:1}
.conn-avatar{width:42px;height:42px;border-radius:13px;background:linear-gradient(135deg,var(--green),#0D9668);display:flex;align-items:center;justify-content:center;color:#000;font-size:18px;flex-shrink:0;position:relative;box-shadow:0 4px 14px rgba(74,222,128,.2)}
.conn-card-v2-id{flex:1;min-width:0}
.conn-ip-v2{font-family:ui-monospace,monospace;font-size:14px;font-weight:800;color:var(--t1);display:flex;align-items:center;gap:6px}
.conn-ip-copy{background:none;border:none;color:var(--t3);cursor:pointer;font-size:12px;padding:2px;display:flex;transition:.15s}
.conn-ip-copy:hover{color:var(--accent)}
.conn-label-v2{font-size:10.5px;color:var(--t3);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.conn-status-pill{font-size:9px;font-weight:800;padding:4px 9px;border-radius:20px;background:var(--green-bg);color:var(--green-t);display:flex;align-items:center;gap:4px;white-space:nowrap;flex-shrink:0}
.conn-card-v2-divider{height:1px;background:linear-gradient(90deg,transparent,var(--card-b) 15%,var(--card-b) 85%,transparent);margin:0 17px}
.conn-card-v2-body{padding:14px 17px 16px}
.conn-proto-row{margin-bottom:12px}
.conn-stat-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.conn-stat-box{display:flex;align-items:center;gap:8px}
.conn-stat-icon{width:26px;height:26px;border-radius:8px;background:var(--accent-d);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0}
.conn-stat-icon.time{background:var(--purple-bg);color:var(--purple-t)}
.conn-stat-text-label{font-size:8.5px;color:var(--t3);font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.conn-stat-text-val{font-size:11.5px;font-weight:700;color:var(--t1);margin-top:1px}
.conn-duration-track{height:5px;border-radius:4px;background:var(--accent-d);overflow:hidden;position:relative}
.conn-duration-fill{height:100%;border-radius:4px;background:linear-gradient(90deg,var(--green),#3FD79C);position:relative;overflow:hidden}

.conn-empty-v2{text-align:center;padding:70px 20px;background:var(--card);border:1px dashed var(--card-b);border-radius:20px}
.conn-empty-v2-icon{width:64px;height:64px;border-radius:18px;background:var(--accent-d);display:flex;align-items:center;justify-content:center;font-size:28px;color:var(--t3);margin:0 auto 16px}

.sub-box{background:var(--purple-bg);border:1px solid rgba(245,158,11,.2);border-radius:10px;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-top:11px}
.sub-url{font-family:ui-monospace,monospace;font-size:10.5px;color:var(--purple-t);word-break:break-all;flex:1}
.empty{text-align:center;padding:50px 20px;color:var(--t3)}
.empty i{font-size:40px;opacity:.3;margin-bottom:12px;display:block}

.subs-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px;flex-wrap:wrap}
.subs-search{flex:1;min-width:200px;position:relative}
.subs-search input{width:100%;padding:11px 40px 11px 15px;border-radius:12px;border:1px solid var(--card-b);background:var(--card);color:var(--t1);font-family:inherit;font-size:12.5px;outline:none;transition:.15s}
.subs-search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-d)}
.subs-search i{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--t3);font-size:15px}

.sub-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px;margin-bottom:18px}
.sub-card{background:var(--card);border:1px solid var(--card-b);border-radius:20px;padding:0;overflow:hidden;transition:all .25s cubic-bezier(.4,0,.2,1);position:relative}
.sub-card:hover{border-color:var(--card-bh);transform:translateY(-4px);box-shadow:0 16px 36px rgba(255,215,0,.05)}
.sub-card-top{background:linear-gradient(155deg,var(--purple-bg) 0%,transparent 65%);padding:20px 20px 16px;position:relative}
.sub-card-top::before{content:'';position:absolute;top:-30px;left:-30px;width:130px;height:130px;background:radial-gradient(circle,rgba(245,158,11,.14),transparent 70%);pointer-events:none}
.sub-card-head-v2{display:flex;align-items:flex-start;gap:13px;position:relative;z-index:1}
.sub-card-icon{width:46px;height:46px;border-radius:14px;background:linear-gradient(135deg,var(--purple),#B8860B);display:flex;align-items:center;justify-content:center;color:#000;font-size:20px;flex-shrink:0;box-shadow:0 6px 16px rgba(245,158,11,.2)}
.sub-card-titles{flex:1;min-width:0}
.sub-card-name-v2{font-size:15.5px;font-weight:800;color:var(--t1);letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sub-card-desc-v2{font-size:11px;color:var(--t3);margin-top:3px;line-height:1.6;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.sub-card-lock-badge{flex-shrink:0;width:26px;height:26px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:12px}
.sub-card-lock-badge.locked{background:var(--amber-bg);color:var(--amber-t)}
.sub-card-lock-badge.open{background:var(--green-bg);color:var(--green-t)}

.sub-card-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:0;position:relative;z-index:1;margin-top:16px;background:rgba(0,0,0,.14);border:1px solid var(--card-b);border-radius:13px;overflow:hidden}
.sub-card-stat{padding:11px 8px;text-align:center;border-left:1px solid var(--card-b)}
.sub-card-stat:last-child{border-left:none}
.sub-card-stat-val{font-size:15px;font-weight:800;color:var(--t1);line-height:1.2}
.sub-card-stat-label{font-size:8.5px;color:var(--t3);font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-top:4px}
.sub-card-url-row{margin:14px 20px 0;background:var(--purple-bg);border:1px dashed rgba(245,158,11,.25);border-radius:11px;padding:9px 12px;display:flex;align-items:center;gap:8px}
.sub-card-url-text{font-family:ui-monospace,monospace;font-size:9.5px;color:var(--purple-t);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sub-card-url-copy{background:none;border:none;color:var(--purple-t);cursor:pointer;font-size:13px;padding:3px;display:flex;flex-shrink:0;transition:.15s}
.sub-card-url-copy:hover{color:var(--accent);transform:scale(1.1)}
.sub-card-bottom{padding:14px 20px 18px;display:flex;gap:7px;flex-wrap:wrap}
.sub-card-bottom .btn{flex:1;justify-content:center;min-width:fit-content}

.subs-empty-v2{text-align:center;padding:70px 20px;background:var(--card);border:1px dashed var(--card-b);border-radius:20px;grid-column:1/-1}
.subs-empty-v2-icon{width:64px;height:64px;border-radius:18px;background:var(--purple-bg);display:flex;align-items:center;justify-content:center;font-size:28px;color:var(--purple-t);margin:0 auto 16px}

.modal-v2{background:var(--card);border:1px solid var(--card-b);border-radius:22px;padding:0;max-width:430px;width:calc(100% - 32px);max-height:92vh;overflow-y:auto;position:relative;animation:fi .2s ease;box-shadow:0 24px 70px rgba(0,0,0,.5)}
.modal-v2-head{background:linear-gradient(155deg,rgba(245,158,11,.14) 0%,transparent 65%);padding:18px 22px 14px;position:relative;overflow:hidden}
.modal-v2-head::before{content:'';position:absolute;top:-50px;left:-50px;width:160px;height:160px;background:radial-gradient(circle,rgba(245,158,11,.2),transparent 70%);pointer-events:none}
.modal-v2-close{position:absolute;top:14px;left:14px;background:var(--accent-d);border:1px solid var(--card-b);color:var(--t2);width:30px;height:30px;border-radius:9px;font-size:15px;display:flex;align-items:center;justify-content:center;cursor:pointer;z-index:2;transition:.15s}
.modal-v2-close:hover{background:var(--red-bg);color:var(--red-t);border-color:rgba(239,68,68,.25)}
.modal-v2-icon{width:42px;height:42px;border-radius:13px;background:linear-gradient(135deg,var(--purple),#B8860B);display:flex;align-items:center;justify-content:center;color:#000;font-size:19px;margin-bottom:10px;position:relative;z-index:1;box-shadow:0 8px 18px rgba(245,158,11,.2)}
.modal-v2-title{font-size:15.5px;font-weight:800;color:var(--t1);position:relative;z-index:1;letter-spacing:-.01em}
.modal-v2-sub{font-size:10.5px;color:var(--t3);margin-top:3px;position:relative;z-index:1;line-height:1.6}
.modal-v2-body{padding:16px 22px 20px;border-top:1px solid var(--card-b)}
.modal-v2-field{margin-bottom:11px}
.modal-v2-field label{display:flex;align-items:center;gap:5px;font-size:9.5px;font-weight:800;color:var(--t2);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
.modal-v2-input-wrap{position:relative}
.modal-v2-input{width:100%;padding:9px 38px 9px 13px;border-radius:11px;border:1px solid var(--card-b);background:rgba(0,0,0,.2);color:var(--t1);font-family:inherit;font-size:12.5px;outline:none;transition:.18s}
[data-theme="light"] .modal-v2-input{background:rgba(245,158,11,.04)}
.modal-v2-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-d);background:rgba(0,0,0,.28)}
.modal-v2-hint{background:var(--accent-d);border:1px solid rgba(255,215,0,.18);border-radius:11px;padding:9px 12px;font-size:10px;color:var(--t2);display:flex;gap:7px;align-items:flex-start;line-height:1.6;margin-top:2px}
.modal-v2-footer{display:flex;gap:8px;margin-top:15px}
.modal-v2-btn-cancel{flex:.75;justify-content:center;padding:10px;border-radius:11px;background:transparent;border:1px solid var(--card-b);color:var(--t2);font-family:inherit;font-size:12px;font-weight:700;cursor:pointer;transition:.15s;display:flex;align-items:center}
.modal-v2-btn-cancel:hover{background:var(--accent-d);color:var(--t1)}
.modal-v2-btn-submit{flex:1;justify-content:center;padding:10px;border-radius:11px;background:linear-gradient(135deg,var(--purple),#B8860B);color:#000;border:none;font-family:inherit;font-size:12px;font-weight:800;cursor:pointer;display:flex;align-items:center;gap:6px;box-shadow:0 6px 18px rgba(245,158,11,.2);transition:.18s}

.lmodal-head{background:linear-gradient(155deg,var(--accent-d) 0%,transparent 70%);padding:22px 24px 18px;position:relative;border-bottom:1px solid var(--card-b)}
.lmodal-icon-row{display:flex;align-items:center;gap:12px;position:relative;z-index:1}
.lmodal-icon{width:44px;height:44px;border-radius:13px;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;color:#000;font-size:19px;flex-shrink:0;box-shadow:0 6px 16px rgba(255,215,0,.25)}
.lmodal-title-v2{font-size:14.5px;font-weight:800;color:var(--t1)}
.lmodal-sub-v2{font-size:10.5px;color:var(--t3);margin-top:2px}
.lmodal-search{margin-top:14px;position:relative}
.lmodal-search input{width:100%;padding:10px 38px 10px 13px;border-radius:11px;border:1px solid var(--card-b);background:rgba(0,0,0,.2);color:var(--t1);font-family:inherit;font-size:12px;outline:none}
.lmodal-search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-d)}
.lmodal-search i{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--t3);font-size:14px}
.lmodal-quickbar{display:flex;gap:8px;margin-top:11px;position:relative;z-index:1}
.lmodal-qbtn{font-size:10px;font-weight:700;padding:5px 11px;border-radius:8px;background:var(--accent-d);color:var(--accent);border:1px solid var(--card-b);cursor:pointer;transition:.15s;font-family:inherit}
.lmodal-count{margin-right:auto;font-size:10.5px;color:var(--t3);display:flex;align-items:center}
.lmodal-list{padding:10px 14px;max-height:360px;overflow-y:auto}
.lrow-v2{display:flex;align-items:center;gap:11px;padding:11px 12px;border-radius:13px;cursor:pointer;transition:.15s;margin-bottom:4px;border:1px solid transparent}
.lrow-v2:hover{background:var(--accent-d)}
.lrow-v2.checked{background:var(--accent-d);border-color:var(--accent)}
.lrow-v2-check{width:20px;height:20px;border-radius:7px;border:2px solid var(--card-b);flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:.15s;background:rgba(0,0,0,.14)}
.lrow-v2.checked .lrow-v2-check{background:var(--accent);border-color:var(--accent)}
.lrow-v2.checked .lrow-v2-check i{opacity:1;transform:scale(1);color:#000}
.lrow-v2-check i{opacity:0;transform:scale(.5)}
.lrow-v2-avatar{width:34px;height:34px;border-radius:10px;background:var(--accent-d);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.lrow-v2.checked .lrow-v2-avatar{background:var(--accent);color:#000}
.lrow-v2-info{flex:1;min-width:0}
.lrow-v2-name{font-size:12.5px;font-weight:700;color:var(--t1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lrow-v2-meta{font-size:9.5px;color:var(--t3);margin-top:2px;display:flex;align-items:center;gap:6px}
.lrow-v2-status{font-size:9px;font-weight:800;padding:3px 9px;border-radius:20px;flex-shrink:0;white-space:nowrap}
.lrow-v2-status.on{background:var(--green-bg);color:var(--green-t)}
.lrow-v2-status.off{background:var(--red-bg);color:var(--red-t)}
.lmodal-footer{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:16px 24px;border-top:1px solid var(--card-b)}
.lmodal-footer-info{font-size:10.5px;color:var(--t3);display:flex;align-items:center;gap:6px}
.lmodal-footer-info i{color:var(--accent)}
.lmodal-footer-btns{display:flex;gap:8px}

.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:500;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
.modal-bg.open{display:flex}
.modal{background:var(--card);border:1px solid var(--card-b);border-radius:20px;padding:28px 26px;max-width:520px;width:calc(100% - 32px);max-height:90vh;overflow-y:auto;position:relative;animation:fi .2s ease}
.modal-close{position:absolute;top:14px;left:14px;background:var(--accent-d);border:1px solid var(--card-b);color:var(--t2);width:30px;height:30px;border-radius:8px;font-size:16px;display:flex;align-items:center;justify-content:center;cursor:pointer;border:none}
.modal-title{font-size:16px;font-weight:700;color:var(--t1);margin-bottom:18px;display:flex;align-items:center;gap:8px}
.modal-title i{color:var(--accent)}

.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(40px);background:var(--card);border:1px solid var(--card-b);color:var(--t1);border-radius:10px;padding:10px 18px;font-size:12.5px;opacity:0;transition:all .25s;z-index:999;pointer-events:none;display:flex;align-items:center;gap:8px;box-shadow:var(--shadow);white-space:nowrap}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.toast.ok{border-color:rgba(74,222,128,.3);background:var(--green-bg);color:var(--green-t)}
.toast.err{border-color:rgba(248,113,113,.3);background:var(--red-bg);color:var(--red-t)}
.dash-footer{border-top:1px solid var(--card-b);margin-top:14px;padding-top:14px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.df-text{font-size:10px;color:var(--t3)}
.df-link{font-size:11.5px;color:var(--accent);display:flex;align-items:center;gap:5px;font-weight:600}

.cfg-grid{display:flex;flex-direction:column;gap:10px}
.cfg-card{background:var(--card);border:1px solid var(--card-b);border-radius:14px;padding:0;transition:all .2s cubic-bezier(.4,0,.2,1);position:relative;overflow:hidden}
.cfg-card:hover{border-color:var(--card-bh);box-shadow:0 6px 24px rgba(255,215,0,.05)}
.cfg-card.is-off{opacity:.6}
.cfg-card.is-exp{opacity:.78}
.cfg-row{display:flex;align-items:center;gap:16px;padding:14px 18px}
.cfg-status-dot{width:9px;height:9px;border-radius:50%;background:var(--green);flex-shrink:0;box-shadow:0 0 0 3px var(--green-bg)}
.cfg-card.is-off .cfg-status-dot{background:var(--red);box-shadow:0 0 0 3px var(--red-bg)}
.cfg-card.is-exp .cfg-status-dot{background:var(--amber);box-shadow:0 0 0 3px var(--amber-bg)}
.cfg-identity{display:flex;flex-direction:column;gap:3px;min-width:150px;flex-shrink:0}
.cfg-label{font-size:13.5px;font-weight:700;color:var(--t1);display:flex;align-items:center;gap:7px}
.cfg-sub-meta{display:flex;align-items:center;gap:8px;font-size:10px;color:var(--t3)}
.cfg-uuid-mini{font-family:ui-monospace,monospace;font-size:9.5px;color:var(--accent);background:var(--accent-d);padding:2px 7px;border-radius:5px;cursor:pointer;transition:.15s}
.cfg-divider-v{width:1px;align-self:stretch;background:var(--card-b);flex-shrink:0}
.cfg-usage-col{flex:1;min-width:160px;display:flex;flex-direction:column;gap:5px}
.ubar{height:5px;border-radius:4px;background:rgba(255,215,0,0.1);overflow:hidden}
.ubar-f{height:100%;border-radius:4px;transition:width .4s ease}
.utxt{font-size:10px;color:var(--t3);display:flex;justify-content:space-between}
.cfg-exp-col{flex-shrink:0;min-width:110px}
.cfg-badges-col{display:flex;flex-direction:column;gap:5px;flex-shrink:0;align-items:flex-end}
.cfg-actions{display:flex;gap:5px;flex-shrink:0}
.proto-chip{font-size:9px;padding:3px 8px;border-radius:6px;font-weight:700;white-space:nowrap}
.pc-ws{background:var(--accent-d);color:var(--accent)}
.pc-xhttp{background:var(--purple-bg);color:var(--purple-t)}
.pc-ultra{background:var(--green-bg);color:var(--green-t)}
.cfg-sub-tag{font-size:9.5px;color:var(--t3);display:flex;align-items:center;gap:4px;white-space:nowrap}
.cfg-sub-tag i{color:var(--accent);font-size:11px}

@media(max-width:880px){
  .cfg-row{flex-wrap:wrap}
  .cfg-divider-v{display:none}
  .cfg-usage-col{min-width:100%;order:5}
}
@media(max-width:768px){
  .cfg-grid{display:grid;grid-template-columns:1fr;gap:13px}
  .cfg-card{border-radius:16px}
  .cfg-row{flex-direction:column;align-items:stretch;gap:12px;padding:16px}
  .cfg-identity{min-width:0;flex:1}
  .cfg-usage-col{min-width:0}
  .cfg-exp-col{min-width:0}
  .cfg-badges-col{flex-direction:row;align-items:center;flex-wrap:wrap}
  .cfg-actions{flex-wrap:wrap;border-top:1px solid var(--card-b);padding-top:10px;margin-top:2px;width:100%}
}

.conn-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.conn-card{background:var(--card);border:1px solid var(--card-b);border-radius:16px;padding:15px 17px;transition:.2s;position:relative;overflow:hidden}
.conn-card:hover{border-color:var(--card-bh);transform:translateY(-1px)}
.conn-card::before{content:'';position:absolute;top:0;right:0;width:3px;height:100%;background:var(--green)}
.conn-ip-row{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.conn-ip-icon{width:32px;height:32px;border-radius:9px;background:var(--green-bg);color:var(--green-t);display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0}
.conn-ip{font-family:ui-monospace,monospace;font-size:13px;font-weight:700;color:var(--t1)}
.conn-label{font-size:10.5px;color:var(--t3);margin-top:1px}
.conn-meta{display:flex;justify-content:space-between;align-items:center;font-size:10px;color:var(--t3);padding-top:10px;border-top:1px solid var(--card-b)}

.log-timeline{display:flex;flex-direction:column}
.log-item{display:flex;gap:12px;padding:11px 0;border-bottom:1px solid rgba(255,215,0,0.05);position:relative}
.log-item:last-child{border-bottom:none}
.log-ic{width:30px;height:30px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.log-ic.ok{background:var(--green-bg);color:var(--green-t)}
.log-ic.err{background:var(--red-bg);color:var(--red-t)}
.log-ic.warn{background:var(--amber-bg);color:var(--amber-t)}
.log-ic.info{background:var(--accent-d);color:var(--accent)}
.log-body{flex:1;min-width:0}
.log-msg{font-size:12.5px;color:var(--t1);line-height:1.6}
.log-time{font-size:9.5px;color:var(--t3);margin-top:2px;display:flex;align-items:center;gap:5px}
.log-kind{font-size:8.5px;padding:1px 7px;border-radius:10px;background:var(--accent-d);color:var(--accent);font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.erow{padding:9px 0;border-bottom:1px solid rgba(255,215,0,0.05)}
.erow:last-child{border-bottom:none}
.etime{color:var(--t3);font-size:9.5px;margin-bottom:3px;display:flex;align-items:center;gap:4px}
.emsg{color:var(--red-t);font-family:ui-monospace,monospace;background:var(--red-bg);padding:6px 9px;border-radius:6px;word-break:break-all;font-size:10.5px}

@media(max-width:1050px){
  .sidebar{transform:translateX(100%)}
  .sidebar.open{transform:translateX(0);box-shadow:-10px 0 40px rgba(0,0,0,.4)}
  .sb-close{display:flex}
  .main{margin-right:0;padding-top:70px}
  .mob-top{display:flex}
  .metrics{grid-template-columns:1fr 1fr}
  .g2,.g3{grid-template-columns:1fr}
}
@media(max-width:500px){
  .metrics{grid-template-columns:1fr}
  .main{padding:62px 12px 50px}
  .sub-grid,.cfg-grid,.conn-grid{grid-template-columns:1fr}
}
.lrow-v2.half-checked {background:var(--accent-d)}
.lrow-v2.half-checked .lrow-v2-check {background:var(--accent-d);border-color:var(--accent)}
.lrow-v2.half-checked .lrow-v2-check i {opacity:1;transform:scale(1);color:var(--accent)}
</style>
</head>
<body>
<div class="toast" id="toast"></div>
<div class="modal-bg" id="modal-variations">
  <div class="modal" style="max-width:440px; padding: 22px;">
    <button class="modal-close" onclick="closeModal('modal-variations')"><i class="ti ti-x"></i></button>
    <div class="modal-title"><i class="ti ti-layers-linked"></i> لینک‌های اتصال</div>
    <div id="variations-list" style="display:flex;flex-direction:column;gap:10px;margin-top:10px;max-height:60vh;overflow-y:auto;padding-right:5px;"></div>
  </div>
</div>
<div class="modal-bg" id="modal-links">
  <div class="modal-v2" style="max-width:500px">
    <div class="lmodal-head">
      <button class="modal-v2-close" onclick="closeModal('modal-links')"><i class="ti ti-x"></i></button>
      <div class="lmodal-icon-row">
        <div class="lmodal-icon"><i class="ti ti-link-plus"></i></div>
        <div>
          <div class="lmodal-title-v2">مدیریت کانفیگ‌های <span id="modal-sub-name" style="color:var(--accent)">—</span></div>
          <div class="lmodal-sub-v2">کانفیگ‌هایی که می‌خواهید در این گروه باشند را انتخاب کنید</div>
        </div>
      </div>
      <div class="lmodal-search">
        <i class="ti ti-search"></i>
        <input type="text" id="lmodal-search-inp" placeholder="جستجوی کانفیگ..." oninput="filterLmodal(this.value)">
      </div>
      <div class="lmodal-quickbar">
        <button class="lmodal-qbtn" onclick="lmodalSelectAll(true)"><i class="ti ti-checks"></i> انتخاب همه</button>
        <button class="lmodal-qbtn" onclick="lmodalSelectAll(false)"><i class="ti ti-x"></i> لغو همه</button>
        <span class="lmodal-count" id="lmodal-count">۰ انتخاب شده</span>
      </div>
    </div>
    <div class="lmodal-list" id="modal-links-body">در حال بارگذاری...</div>
    <div class="lmodal-footer">
      <div class="lmodal-footer-info"><i class="ti ti-info-circle"></i> تغییرات بلافاصله اعمال می‌شود</div>
      <div class="lmodal-footer-btns">
        <button class="btn btn-o" onclick="closeModal('modal-links')">بستن</button>
        <button class="btn btn-p" id="modal-save-btn" onclick="saveSubLinks()"><i class="ti ti-check"></i> ذخیره</button>
      </div>
    </div>
  </div>
</div>
<div class="modal-bg" id="modal-create-sub">
  <div class="modal-v2">
    <div class="modal-v2-head">
      <button class="modal-v2-close" onclick="closeModal('modal-create-sub')"><i class="ti ti-x"></i></button>
      <div class="modal-v2-icon"><i class="ti ti-folder-plus"></i></div>
      <div class="modal-v2-title">ساخت گروه جدید</div>
      <div class="modal-v2-sub">یک صفحه پابلیک مجزا برای مدیریت کانفیگ‌ها بسازید</div>
    </div>
    <div class="modal-v2-body">
      <div class="modal-v2-field">
        <label><i class="ti ti-tag"></i> نام گروه</label>
        <input class="modal-v2-input" id="ns-name" placeholder="مثلاً: کانال تلگرام">
      </div>
      <div class="modal-v2-field">
        <label><i class="ti ti-align-left"></i> توضیحات (اختیاری)</label>
        <input class="modal-v2-input" id="ns-desc" placeholder="توضیح کوتاه درباره این گروه">
      </div>
      
      <div class="modal-v2-field">
        <label><i class="ti ti-world"></i> لینک‌های ساب کاستوم (دامنه/Worker/Pages)</label>
        <div id="ns-saved-customs" style="display:flex;gap:8px;overflow-x:auto;padding-bottom:8px;margin-top:6px"></div>
        <div id="ns-customs-list" style="display:flex;flex-direction:column;gap:8px;margin-bottom:8px;margin-top:6px"></div>
        <button class="btn btn-sm btn-g" type="button" onclick="addSubCustomField('ns')"><i class="ti ti-plus"></i> ایجاد لینک کاستوم دستی</button>
      </div>

      <div class="modal-v2-field" style="margin-bottom:0">
        <label><i class="ti ti-lock"></i> رمز صفحه پابلیک (اختیاری)</label>
        <input class="modal-v2-input" id="ns-pw" type="password" placeholder="خالی بگذارید = بدون رمز">
      </div>
      <div class="modal-v2-footer">
        <button class="btn btn-o" onclick="closeModal('modal-create-sub')" style="flex:.6">انصراف</button>
        <button class="btn btn-pur" onclick="createSub()"><i class="ti ti-folder-plus"></i> ساخت گروه</button>
      </div>
    </div>
  </div>
</div>
<div class="modal-bg" id="modal-edit-sub">
  <div class="modal-v2">
    <div class="modal-v2-head" style="background:linear-gradient(155deg,rgba(16,185,129,.14) 0%,transparent 65%);">
      <button class="modal-v2-close" onclick="closeModal('modal-edit-sub')"><i class="ti ti-x"></i></button>
      <div class="modal-v2-icon" style="background:linear-gradient(135deg,var(--green),#0D9668);box-shadow:0 8px 18px rgba(16,185,129,.2);"><i class="ti ti-edit"></i></div>
      <div class="modal-v2-title">ویرایش گروه ساب</div>
      <div class="modal-v2-sub">تغییر نام، توضیحات و لینک‌های کاستوم</div>
    </div>
    <div class="modal-v2-body">
      <input type="hidden" id="es-id">
      <div class="modal-v2-field">
        <label><i class="ti ti-tag"></i> نام گروه</label>
        <input class="modal-v2-input" id="es-name" placeholder="مثلاً: کانال تلگرام">
      </div>
      <div class="modal-v2-field">
        <label><i class="ti ti-align-left"></i> توضیحات (اختیاری)</label>
        <input class="modal-v2-input" id="es-desc" placeholder="توضیح کوتاه درباره این گروه">
      </div>
      
      <div class="modal-v2-field">
        <label><i class="ti ti-world"></i> لینک‌های ساب کاستوم (دامنه/Worker/Pages)</label>
        <div id="es-saved-customs" style="display:flex;gap:8px;overflow-x:auto;padding-bottom:8px;margin-top:6px"></div>
        <div id="es-customs-list" style="display:flex;flex-direction:column;gap:8px;margin-bottom:8px;margin-top:6px"></div>
        <button class="btn btn-sm btn-g" type="button" onclick="addSubCustomField('es')"><i class="ti ti-plus"></i> ایجاد لینک کاستوم دستی</button>
      </div>

      <div class="modal-v2-field" style="margin-bottom:0">
        <label><i class="ti ti-lock"></i> رمز جدید (اختیاری)</label>
        <input class="modal-v2-input" id="es-pw" type="password" placeholder="برای عدم تغییر، خالی بگذارید">
        <label style="margin-top:8px;display:flex;align-items:center;gap:6px;font-size:10px;text-transform:none">
            <input type="checkbox" id="es-remove-pw"> حذف رمز فعلی (عمومی شدن گروه)
        </label>
      </div>
      <div class="modal-v2-footer">
        <button class="btn btn-o" onclick="closeModal('modal-edit-sub')" style="flex:.6">انصراف</button>
        <button class="btn btn-p" onclick="saveEditSub()" style="background:var(--green);box-shadow:0 6px 18px rgba(16,185,129,.2)"><i class="ti ti-check"></i> ذخیره تغییرات</button>
      </div>
    </div>
  </div>
</div>
<div class="modal-bg" id="modal-edit-link">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('modal-edit-link')"><i class="ti ti-x"></i></button>
    <div class="modal-title"><i class="ti ti-edit"></i> ویرایش کانفیگ</div>
    <input type="hidden" id="el-uuid">
    <div class="fg" style="margin-bottom:13px"><label>عنوان</label><input class="fi" id="el-label" style="width:100%"></div>
    <div class="fg" style="margin-bottom:13px"><label>دامنه لینک ساب (اختیاری)</label><input class="fi" id="el-sub-domain" placeholder="مثلاً https://sub.domain.com" style="width:100%"></div>
    
    <div class="fg" style="margin-bottom:13px;width:100%">
      <label>گروه‌های ساب (تیک بزنید)</label>
      <div id="el-subs-list" style="max-height:110px;overflow-y:auto;background:rgba(0,0,0,.15);border:1px solid var(--card-b);border-radius:10px;padding:8px;display:flex;flex-direction:column;gap:5px;width:100%"></div>
    </div>

    <div class="fg" style="margin-bottom:13px;width:100%">
      <label>کانفیگ‌های کاستوم (CDN / IP)</label>
      <div id="el-saved-customs" style="display:flex;gap:8px;overflow-x:auto;padding-bottom:8px;margin-bottom:6px;width:100%"></div>
      <div id="el-customs-list" style="display:flex;flex-direction:column;gap:8px;margin-bottom:8px;width:100%"></div>
      <button class="btn btn-sm btn-g" type="button" onclick="addCustomField('el')"><i class="ti ti-plus"></i> ایجاد کاستوم جدید دستی</button>
    </div>

    <div class="form-row" style="margin-bottom:13px">
      <div class="fg" style="flex:1"><label>سهمیه (0 = نامحدود)</label><input class="fi" id="el-val" type="number" min="0" step="0.1" style="width:100%"></div>
      <div class="fg"><label>واحد</label><select class="fs" id="el-unit"><option value="GB">GB</option><option value="MB">MB</option></select></div>
    </div>
    <div class="fg" style="margin-bottom:13px"><label>انقضا (روز از الان، 0 = بدون تغییر/نامحدود)</label><input class="fi" id="el-exp" type="number" min="0" step="1" style="width:100%"></div>
    <div class="fg" style="margin-bottom:13px"><label>یادداشت</label><input class="fi" id="el-note" style="width:100%"></div>
    <div class="form-row" style="margin-bottom:13px">
      <div class="fg" style="flex:1"><label>Fingerprint (uTLS)</label>
        <select class="fs" id="el-fp" style="width:100%">
          <option value="chrome">chrome</option>
          <option value="firefox">firefox</option>
          <option value="safari">safari</option>
          <option value="ios">ios</option>
          <option value="android">android</option>
          <option value="edge">edge</option>
          <option value="360">360</option>
          <option value="qq">qq</option>
          <option value="random">random</option>
          <option value="randomized">randomized</option>
        </select>
      </div>
      <div class="fg" style="flex:1"><label>ALPN (خالی = پیش‌فرض)</label><input class="fi" id="el-alpn" placeholder="مثلاً: h2,http/1.1" style="width:100%"></div>
    </div>
    <div class="form-row" style="margin-bottom:16px">
      <div class="fg" style="flex:1"><label>پورت اتصال</label><input class="fi" id="el-port" type="number" min="1" max="65535" style="width:100%"></div>
      <div class="fg" style="flex:1"><label>محدودیت آی‌پی (0 = نامحدود)</label><input class="fi" id="el-iplimit" type="number" min="0" step="1" style="width:100%"></div>
    </div>
    <div class="form-row" style="margin-bottom:16px">
      <div class="fg" style="flex:1"><label>محدودیت سرعت (0 = نامحدود)</label><input class="fi" id="el-speed" type="number" min="0" step="0.5" style="width:100%"></div>
      <div class="fg"><label>واحد</label><select class="fs" id="el-speed-unit"><option value="MBIT">Mbps</option><option value="KB">KB/s</option><option value="MB">MB/s</option></select></div>
    </div>
    
    <div class="cl"><i class="ti ti-info-circle"></i><span>برای حفظ انقضای فعلی، فیلد انقضا را صفر بگذارید.</span></div>
    <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">
      <button class="btn btn-o" onclick="closeModal('modal-edit-link')">انصراف</button>
      <button class="btn btn-p" onclick="saveEditLink()"><i class="ti ti-check"></i> ذخیره تغییرات</button>
    </div>
  </div>
</div>
<div class="mob-top">
  <div class="ml">
    <div class="mob-logo">__LOGO_SVG__</div>
    <span class="mob-title">Sadra PANEL</span>
  </div>
  <div class="mob-right">
    <button class="theme-mob" id="theme-mob-btn" onclick="toggleTheme()"><i class="ti ti-sun" id="theme-mob-icon"></i></button>
    <button class="menu-btn" id="open-sb"><i class="ti ti-menu-2"></i></button>
  </div>
</div>
<div class="overlay" id="overlay"></div>
<aside class="sidebar" id="sb">
  <button class="sb-close" id="close-sb"><i class="ti ti-x"></i></button>
  <div class="logo">
    <div class="logo-img">__LOGO_SVG__</div>
    <div><div class="logo-name">Sadra PANEL</div><div class="logo-sub">Powered by Sadra v9.5</div></div>
  </div>
  <div class="nav-wrap">
    <div class="nav-sec">پنل</div>
    <div class="nav-it on" data-pg="overview"><i class="ti ti-layout-dashboard"></i> داشبورد</div>
    <div class="nav-it" data-pg="links"><i class="ti ti-link-plus"></i> کانفیگ‌ها <span class="nav-badge" id="links-nb">0</span></div>
    <div class="nav-it" data-pg="subgroups"><i class="ti ti-folders"></i> گروه‌های ساب <span class="nav-badge" id="subs-nb">0</span></div>
    <div class="nav-it" data-pg="subscriptions"><i class="ti ti-rss"></i> سابسکریپشن</div>
    <div class="nav-it" data-pg="connections"><i class="ti ti-plug-connected"></i> اتصالات <span class="nav-badge" id="conns-nb">0</span></div>
    <div class="nav-sec">سیستم</div>
    <div class="nav-it" data-pg="security"><i class="ti ti-shield-lock"></i> امنیت</div>
    <div class="nav-it" data-pg="logs"><i class="ti ti-history"></i> لاگ فعالیت‌ها</div>
    <div class="nav-it" data-pg="errors"><i class="ti ti-alert-triangle"></i> خطاها</div>
    <div class="nav-it" data-pg="testws"><i class="ti ti-wifi"></i> تست اتصال</div>
    <div class="nav-it" data-pg="settings"><i class="ti ti-settings"></i> تنظیمات</div>
  </div>
  <div class="sb-foot">
    <button class="theme-btn" onclick="toggleTheme()"><i class="ti ti-moon" id="theme-icon"></i> <span id="theme-label">تم روشن</span></button>
    <button class="logout-btn" id="logout-btn"><i class="ti ti-logout"></i> خروج</button>
  </div>
</aside>
<main class="main">
<section class="pg on" id="pg-overview">
  <div class="topbar">
    <div><div class="tb-title"><i class="ti ti-layout-dashboard"></i> داشبورد</div><div class="tb-sub" id="last-upd">در حال بارگذاری...</div></div>
    <div class="tb-right">
      <span class="badge bg-green"><span class="dot dg pulse"></span> فعال</span>
      <span class="badge bg-blue" id="uptime-badge">—</span>
      <button class="btn btn-p btn-sm" onclick="refreshAll()"><i class="ti ti-refresh"></i> رفرش</button>
    </div>
  </div>
  <div class="metrics">
    <div class="metric"><div class="m-icon"><i class="ti ti-plug-connected"></i></div><div class="m-label">اتصالات فعال</div><div class="m-val" id="m-conns">—</div><div class="m-sub"><span class="dot dg pulse"></span> اتصال زنده</div></div>
    <div class="metric"><div class="m-icon"><i class="ti ti-transfer"></i></div><div class="m-label">کل ترافیک</div><div class="m-val" id="m-traffic">—<span class="m-unit">MB</span></div><div class="m-sub">از راه‌اندازی</div></div>
    <div class="metric suc"><div class="m-icon suc"><i class="ti ti-link"></i></div><div class="m-label">کانفیگ فعال</div><div class="m-val" id="m-alinks">—</div><div class="m-sub" id="m-lsub">از کل</div></div>
    <div class="metric pur"><div class="m-icon pur"><i class="ti ti-folders"></i></div><div class="m-label">گروه‌های ساب</div><div class="m-val" id="m-subs">—</div><div class="m-sub">فعال</div></div>
  </div>
  <div class="vless-box">
    <div class="vl-header">
      <div class="vl-title"><i class="ti ti-link"></i> لینک پیش‌فرض (بدون محدودیت)</div>
      <span class="badge bg-blue"><span class="dot db"></span> TLS 443 · WS</span>
    </div>
    <div class="vl-code" id="vless-main">در حال دریافت...</div>
    <div class="vl-actions">
      <button class="btn btn-p" onclick="cpText('vless-main')"><i class="ti ti-copy"></i> کپی</button>
      <button class="btn btn-g" onclick="qrFor('vless-main')"><i class="ti ti-qrcode"></i> QR</button>
      <button class="btn btn-o" onclick="navTo('links')"><i class="ti ti-link-plus"></i> کانفیگ محدود</button>
      <button class="btn btn-pur" onclick="navTo('subgroups')"><i class="ti ti-folders"></i> گروه‌های ساب</button>
    </div>
  </div>
  <div class="g2">
    <div class="card">
      <div class="card-title"><i class="ti ti-activity"></i> وضعیت سرویس</div>
      <div class="sr"><span class="sr-k"><i class="ti ti-shield-check"></i> UUID Auth</span><span class="sr-v" style="color:var(--green-t)">● فعال</span></div>
      <div class="sr"><span class="sr-k"><i class="ti ti-network"></i> Protocols</span><span class="sr-v" style="color:var(--green-t)">● VLESS / XHTTP / HTTPUpgrade</span></div>
      <div class="sr"><span class="sr-k"><i class="ti ti-rss"></i> Subscription</span><span class="sr-v" style="color:var(--green-t)">● فعال</span></div>
      <div class="sr"><span class="sr-k"><i class="ti ti-clock"></i> آپتایم</span><span class="sr-v" id="uptime-inline">—</span></div>
    </div>
    <div class="card">
      <div class="card-title"><i class="ti ti-list"></i> خلاصه کانفیگ‌ها <span class="ml-auto badge bg-blue" id="lsummary-badge">۰</span></div>
      <div id="lsummary">—</div>
    </div>
  </div>
</section>
<section class="pg" id="pg-links">
  <div class="topbar">
    <div><div class="tb-title"><i class="ti ti-link-plus"></i> کانفیگ‌ها</div><div class="tb-sub">ساخت و مدیریت کانفیگ با سهمیه، انقضا و گروه‌بندی</div></div>
    <div class="tb-right"><span class="badge bg-blue" id="links-pg-cnt">۰ کانفیگ</span></div>
  </div>
  <div class="create-panel">
    <div class="cp-head">
      <div class="cp-head-icon"><i class="ti ti-square-rounded-plus"></i></div>
      <div class="cp-head-text">
        <div class="cp-head-title">ساخت کانفیگ جدید</div>
        <div class="cp-head-sub">UUID تصادفی · سهمیه، انقضا و پروتکل رو انتخاب کن</div>
      </div>
    </div>
    <div class="cp-body">
      <div class="cp-row">
        <div class="cp-block">
          <div class="cp-block-label"><i class="ti ti-id-badge-2"></i> شناسه کانفیگ</div>
          <input class="cp-input-full" id="nl-label" placeholder="مثلاً: کاربر علی">
          <div class="cp-mini-row">
            <input class="cp-input-full" id="nl-note" placeholder="یادداشت (اختیاری)">
          </div>
          <div class="cp-mini-row" style="margin-top:8px">
            <input class="cp-input-full" id="nl-sub-domain" placeholder="دامنه لینک ساب (اختیاری)">
          </div>
        </div>
        <div class="cp-block">
          <div class="cp-block-label"><i class="ti ti-folders"></i> گروه‌های ساب (چند انتخاب)</div>
          <div id="nl-subs-list" style="max-height:100px;overflow-y:auto;background:rgba(0,0,0,.15);border:1px solid var(--card-b);border-radius:10px;padding:8px;display:flex;flex-direction:column;gap:5px;margin-bottom:8px">
             <!-- لیست ساب‌ها اینجا لود میشه -->
          </div>
          <div class="cp-mini-row">
            <input class="cp-input-full" id="nl-exp" type="number" min="0" step="1" placeholder="انقضا (روز) · 0 = نامحدود">
          </div>
        </div>
      </div>

      <div class="cp-block mb16">
        <div class="cp-block-label" style="display:flex;justify-content:space-between">
          <span><i class="ti ti-world"></i> کانفیگ‌های کاستوم (CDN / IP)</span>
        </div>
        <!-- نوار کاستوم‌های ذخیره شده -->
        <div id="nl-saved-customs" style="display:flex;gap:8px;overflow-x:auto;padding-bottom:8px;margin-bottom:8px"></div>
        
        <div id="nl-customs-list" style="display:flex;flex-direction:column;gap:8px;margin-bottom:8px"></div>
        <button class="btn btn-sm btn-g" type="button" onclick="addCustomField('nl')"><i class="ti ti-plus"></i> ایجاد کاستوم جدید دستی</button>
      </div>

      <div class="cp-block mb16">
        <div class="cp-block-label"><i class="ti ti-gauge"></i> سهمیه ترافیک</div>
        <div class="cp-quota-inputs">
          <input class="cp-input-full" id="nl-val" type="number" min="0" step="0.1" placeholder="0 = نامحدود">
          <select class="cp-input-full fs" id="nl-unit"><option value="GB">GB</option><option value="MB" selected>MB</option></select>
        </div>
      </div>
      <div class="cp-block mb16">
        <div class="cp-block-label"><i class="ti ti-plug-connected"></i> پروتکل انتقال</div>
        <select id="nl-proto" style="display:none">
          <option value="vless-ws">VLESS / WebSocket</option>
          <option value="httpupgrade">HTTPUpgrade</option>
          <option value="xhttp-packet-up">XHTTP Ultra · packet-up</option>
          <option value="xhttp-stream-up">XHTTP Ultra · stream-up</option>
          <option value="xhttp-reality">XHTTP · REALITY</option>
        </select>
        <div class="proto-cards">
          <div class="proto-card active" data-val="vless-ws" onclick="selectProto('vless-ws',this)">
            <div class="proto-card-check"><i class="ti ti-check"></i></div>
            <div class="proto-card-icon"><i class="ti ti-link"></i></div>
            <div class="proto-card-title">VLESS / WS</div>
            <div class="proto-card-desc">پایدار و همه‌منظوره</div>
          </div>
          <div class="proto-card" data-val="httpupgrade" onclick="selectProto('httpupgrade',this)">
            <div class="proto-card-check"><i class="ti ti-check"></i></div>
            <div class="proto-card-icon"><i class="ti ti-arrow-up-circle"></i></div>
            <div class="proto-card-title">HTTPUpgrade</div>
            <div class="proto-card-desc">ارتقای استاندارد HTTP</div>
          </div>
          <div class="proto-card" data-val="xhttp-packet-up" onclick="selectProto('xhttp-packet-up',this)">
            <div class="proto-card-check"><i class="ti ti-check"></i></div>
            <div class="proto-card-icon"><i class="ti ti-bolt"></i></div>
            <div class="proto-card-title">XHTTP · packet</div>
            <div class="proto-card-desc">سازگار با CDN</div>
          </div>
          <div class="proto-card" data-val="xhttp-stream-up" onclick="selectProto('xhttp-stream-up',this)">
            <div class="proto-card-check"><i class="ti ti-check"></i></div>
            <div class="proto-card-icon"><i class="ti ti-rocket"></i></div>
            <div class="proto-card-title">XHTTP · stream</div>
            <div class="proto-card-desc">تاخیر پایین‌تر</div>
          </div>
          <div class="proto-card" data-val="xhttp-reality" onclick="selectProto('xhttp-reality',this)">
            <div class="proto-card-check"><i class="ti ti-check"></i></div>
            <div class="proto-card-icon"><i class="ti ti-shield-lock"></i></div>
            <div class="proto-card-title">XHTTP Reality</div>
            <div class="proto-card-desc">مشابه REALITY MLKEM</div>
          </div>
        </div>
      </div>
      <div class="cp-row">
        <div class="cp-block">
          <div class="cp-block-label"><i class="ti ti-fingerprint"></i> Fingerprint (uTLS)</div>
          <select class="cp-input-full fs" id="nl-fp">
            <option value="chrome" selected>chrome</option>
            <option value="firefox">firefox</option>
            <option value="safari">safari</option>
            <option value="ios">ios</option>
            <option value="android">android</option>
            <option value="edge">edge</option>
            <option value="360">360</option>
            <option value="qq">qq</option>
            <option value="random">random</option>
            <option value="randomized">randomized</option>
          </select>
        </div>
        <div class="cp-block">
          <div class="cp-block-label"><i class="ti ti-antenna-bars-5"></i> ALPN</div>
          <select class="cp-input-full fs" id="nl-alpn-preset" onchange="onAlpnPresetChange()">
            <option value="">پیش‌فرض پروتکل</option>
            <option value="h2,http/1.1">h2,http/1.1</option>
            <option value="http/1.1">http/1.1</option>
            <option value="h2">h2</option>
            <option value="__custom__">دستی...</option>
          </select>
          <div class="cp-mini-row">
            <input class="cp-input-full" id="nl-alpn" placeholder="مقدار دستی ALPN" style="display:none">
          </div>
        </div>
      </div>
      <div class="cp-row mb16">
        <div class="cp-block">
          <div class="cp-block-label"><i class="ti ti-route"></i> پورت اتصال</div>
          <input class="cp-input-full" id="nl-port" type="number" min="1" max="65535" placeholder="443" value="443">
        </div>
        <div class="cp-block">
          <div class="cp-block-label"><i class="ti ti-users"></i> محدودیت آی‌پی / کاربر هم‌زمان</div>
          <input class="cp-input-full" id="nl-iplimit" type="number" min="0" step="1" placeholder="0 = نامحدود" value="0">
        </div>
      </div>
      <div class="cp-row mb16">
        <div class="cp-block" style="flex:1">
          <div class="cp-block-label"><i class="ti ti-gauge"></i> محدودیت سرعت</div>
          <div class="form-row">
            <input class="cp-input-full" id="nl-speed" type="number" min="0" step="0.5" placeholder="0 = نامحدود" value="0" style="flex:1">
            <select class="fs" id="nl-speed-unit" style="flex:0 0 100px">
              <option value="MBIT" selected>Mbps</option>
              <option value="KB">KB/s</option>
              <option value="MB">MB/s</option>
            </select>
          </div>
        </div>
      </div>
      <div class="cp-footer">
        <div class="cp-footer-note"><i class="ti ti-info-circle"></i> UUID کاملاً رندوم تولید می‌شود · فقط UUID‌های ثبت‌شده اجازه اتصال دارند.</div>
        <button class="cp-submit-btn" onclick="createLink()"><i class="ti ti-link-plus"></i> ساخت کانفیگ</button>
      </div>
    </div>
  </div>
  <div class="cfg-grid" id="links-grid"></div>
  <div class="empty" id="links-empty" style="display:none"><i class="ti ti-link-off"></i><p>هنوز کانفیگی وجود ندارد</p></div>
</section>
<section class="pg" id="pg-subgroups">
  <div class="topbar">
    <div><div class="tb-title"><i class="ti ti-folders"></i> گروه‌های ساب</div><div class="tb-sub">هر گروه یک صفحه پابلیک مجزا با کانفیگ‌های خودش دارد</div></div>
    <div class="tb-right">
      <span class="badge bg-purple" id="subs-pg-cnt">۰ گروه</span>
      <button class="btn btn-pur" onclick="openModal('modal-create-sub')"><i class="ti ti-folder-plus"></i> گروه جدید</button>
    </div>
  </div>
  <div class="subs-toolbar">
    <div class="subs-search">
      <i class="ti ti-search"></i>
      <input type="text" id="subs-search-inp" placeholder="جستجو در گروه‌ها..." oninput="filterSubs(this.value)">
    </div>
  </div>
  <div class="sub-grid" id="subs-grid">
    <div class="subs-empty-v2"><div class="subs-empty-v2-icon"><i class="ti ti-folders"></i></div><div class="subs-empty-v2-title">هنوز گروهی وجود ندارد</div><div class="subs-empty-v2-sub">یک گروه جدید بسازید تا کانفیگ‌ها را دسته‌بندی کنید</div></div>
  </div>
</section>
<section class="pg" id="pg-subscriptions">
  <div class="topbar"><div><div class="tb-title"><i class="ti ti-rss"></i> سابسکریپشن</div><div class="tb-sub">لینک‌های اشتراک برای اپ‌های v2ray</div></div></div>
  <div class="g2">
    <div class="card">
      <div class="card-title"><i class="ti ti-rss"></i> سابسکریپشن تکی (هر کانفیگ)</div>
      <p style="font-size:11.5px;color:var(--t3);line-height:1.8;margin-bottom:12px">هر کانفیگ URL سابسکریپشن مخصوص دارد. از کارت کانفیگ روی آیکون <i class="ti ti-rss"></i> کلیک کنید.</p>
    </div>
    <div class="card">
      <div class="card-title"><i class="ti ti-database"></i> سابسکریپشن کامل (ادمین)</div>
      <p style="font-size:11.5px;color:var(--t3);line-height:1.8;margin-bottom:4px">شامل تمام کانفیگ‌های فعال.</p>
      <div class="sub-box"><span class="sub-url" id="sub-all-url">در حال دریافت...</span><div style="display:flex;gap:6px"><button class="btn btn-sm btn-g" onclick="cpSubAll()"><i class="ti ti-copy"></i></button><button class="btn btn-sm btn-g" onclick="window.open(location.protocol+'//'+location.host+'/sub-all')"><i class="ti ti-external-link"></i></button></div></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title"><i class="ti ti-folders"></i> لینک سابسکریپشن گروه‌ها</div>
    <div id="sub-groups-list">در حال بارگذاری...</div>
  </div>
</section>
<section class="pg" id="pg-connections">
  <div class="topbar">
    <div><div class="tb-title"><i class="ti ti-plug-connected"></i> اتصالات فعال</div><div class="tb-sub">مانیتورینگ زنده‌ی آی‌پی و ترافیک هر اتصال</div></div>
    <div class="tb-right"><span class="badge bg-green" id="conns-live">—</span><button class="btn btn-p btn-sm" onclick="refreshAll()"><i class="ti ti-refresh"></i> رفرش</button></div>
  </div>
  <div class="conn-hero">
    <div class="conn-hero-tile">
      <div class="conn-hero-icon"><i class="ti ti-plug-connected"></i></div>
      <div class="conn-hero-label">اتصالات زنده</div>
      <div class="conn-hero-val" id="ch-count">—</div>
    </div>
    <div class="conn-hero-tile">
      <div class="conn-hero-icon"><i class="ti ti-transfer"></i></div>
      <div class="conn-hero-label">مجموع ترافیک لحظه‌ای</div>
      <div class="conn-hero-val" id="ch-traffic">—</div>
    </div>
  </div>
  <div class="conn-toolbar">
    <div class="conn-toolbar-title"><i class="ti ti-list-details"></i> لیست اتصالات</div>
    <div class="conn-live-badge"><span class="conn-live-dot"></span> بروزرسانی خودکار هر ۵ ثانیه</div>
  </div>
  <div class="conn-grid-v2" id="conns-grid"></div>
  <div class="conn-empty-v2" id="conns-empty" style="display:none">
    <div class="conn-empty-v2-icon"><i class="ti ti-plug-off"></i></div>
    <div class="conn-empty-v2-title">هیچ اتصال فعالی نیست</div>
  </div>
</section>
<section class="pg" id="pg-security">
  <div class="topbar"><div><div class="tb-title"><i class="ti ti-shield-lock"></i> امنیت</div></div></div>
  <div class="g2">
    <div class="card">
      <div class="card-title"><i class="ti ti-lock"></i> رمزنگاری</div>
      <div class="sr"><span class="sr-k"><i class="ti ti-certificate"></i> TLS/HTTPS</span><span class="sr-v" style="color:var(--green-t)">● فعال (443)</span></div>
      <div class="sr"><span class="sr-k"><i class="ti ti-fingerprint"></i> Fingerprint</span><span class="sr-v">Chrome Spoof</span></div>
      <div class="sr"><span class="sr-k"><i class="ti ti-network"></i> پروتکل‌ها</span><span class="sr-v">VLESS/XHTTP/HTTPUpgrade</span></div>
      <div class="sr"><span class="sr-k"><i class="ti ti-key"></i> هش رمز</span><span class="sr-v">SHA-256+Salt</span></div>
    </div>
    <div class="card">
      <div class="card-title"><i class="ti ti-shield-check"></i> کنترل دسترسی</div>
      <div class="sr"><span class="sr-k"><i class="ti ti-id-badge"></i> UUID Auth سخت‌گیرانه</span><span class="sr-v" style="color:var(--green-t)">● فعال v9</span></div>
      <div class="sr"><span class="sr-k"><i class="ti ti-gauge"></i> سهمیه ترافیک</span><span class="sr-v" style="color:var(--green-t)">● فعال</span></div>
      <div class="sr"><span class="sr-k"><i class="ti ti-calendar-x"></i> تاریخ انقضا</span><span class="sr-v" style="color:var(--green-t)">● فعال</span></div>
    </div>
  </div>
</section>
<section class="pg" id="pg-logs">
  <div class="topbar"><div><div class="tb-title"><i class="ti ti-history"></i> لاگ فعالیت‌ها</div><div class="tb-sub">تاریخچه‌ی کامل رخدادهای پنل</div></div><div class="tb-right"><button class="btn btn-p btn-sm" onclick="loadActivity()"><i class="ti ti-refresh"></i></button></div></div>
  <div class="card"><div class="log-timeline" id="logs-list">—</div><div class="empty" id="logs-empty" style="display:none"><i class="ti ti-history-toggle"></i><p>هنوز لاگی ثبت نشده</p></div></div>
</section>
<section class="pg" id="pg-errors">
  <div class="topbar"><div><div class="tb-title"><i class="ti ti-alert-triangle"></i> خطاها</div></div><div class="tb-right"><span class="badge bg-red" id="errs-badge">۰</span><button class="btn btn-p btn-sm" onclick="refreshAll()"><i class="ti ti-refresh"></i></button></div></div>
  <div class="card"><div class="card-title"><i class="ti ti-bug"></i> لاگ خطاها</div><div id="errs-full">—</div></div>
</section>
<section class="pg" id="pg-testws">
  <div class="topbar"><div><div class="tb-title"><i class="ti ti-wifi"></i> تست اتصال</div></div></div>
  <div class="card" style="max-width:660px">
    <div class="cl amber" style="margin-top:0;margin-bottom:12px"><i class="ti ti-alert-triangle"></i><span>این فقط یک تست پایه‌ی VLESS/WS است.</span></div>
    <div class="form-row" style="margin-bottom:12px">
      <div class="fg" style="flex:1"><label>UUID (باید در کانفیگ‌ها وجود داشته باشد)</label><input class="fi" id="ws-uuid" placeholder="UUID یک کانفیگ فعال" style="width:100%"></div>
      <button class="btn btn-p" onclick="wsConn()"><i class="ti ti-plug-connected"></i> اتصال</button>
      <button class="btn btn-d" onclick="wsDisc()"><i class="ti ti-plug-x"></i> قطع</button>
    </div>
    <div class="form-row" style="margin-bottom:12px">
      <input class="fi" id="ws-msg" placeholder="پیام تست..." style="flex:1">
      <button class="btn btn-o" onclick="wsSend()"><i class="ti ti-send"></i> ارسال</button>
    </div>
    <div style="background:rgba(0,0,0,.3);border:1px solid var(--card-b);border-radius:10px;padding:14px;height:250px;overflow-y:auto;font-family:ui-monospace,monospace;font-size:10.5px;line-height:1.9" id="ws-log">
      <p style="color:var(--t3)">منتظر اتصال...</p>
    </div>
  </div>
</section>
<section class="pg" id="pg-settings">
  <div class="topbar"><div><div class="tb-title"><i class="ti ti-settings"></i> تنظیمات</div></div></div>
  <div class="g2">
    <div class="srv-panel">
      <div class="srv-hero">
        <div class="srv-hero-icon"><i class="ti ti-server-2"></i></div>
        <div class="srv-hero-text">
          <div class="srv-hero-domain" id="set-host">—</div>
          <div class="srv-hero-sub"><span class="dot dg pulse"></span> آنلاین · Python Backend</div>
        </div>
      </div>
      <div class="srv-tiles">
        <div class="srv-tile"><div class="srv-tile-icon"><i class="ti ti-route"></i></div><div class="srv-tile-text"><div class="srv-tile-label">پورت پیش‌فرض</div><div class="srv-tile-val">443 (TLS)</div></div></div>
        <div class="srv-tile"><div class="srv-tile-icon"><i class="ti ti-versions"></i></div><div class="srv-tile-text"><div class="srv-tile-label">نسخه</div><div class="srv-tile-val">v9.5 Sadra</div></div></div>
      </div>
    </div>
    <div class="pw-panel">
      <div class="pw-hero">
        <div class="pw-hero-icon"><i class="ti ti-key"></i></div>
        <div class="pw-hero-text">
          <div class="pw-hero-title">تغییر رمز عبور</div>
        </div>
      </div>
      <div class="pw-body">
        <div class="pw-field">
          <label>رمز فعلی</label>
          <input class="pw-input" type="password" id="cp-cur" placeholder="رمز فعلی را وارد کنید">
          <button class="pw-eye" type="button" onclick="togglePwField('cp-cur',this)"><i class="ti ti-eye"></i></button>
        </div>
        <div class="pw-field" style="margin-bottom:6px">
          <label>رمز جدید</label>
          <input class="pw-input" type="password" id="cp-new" placeholder="حداقل ۴ کاراکتر" oninput="checkPwStrength(this.value)">
          <button class="pw-eye" type="button" onclick="togglePwField('cp-new',this)"><i class="ti ti-eye"></i></button>
        </div>
        <div class="pw-strength" id="pw-strength-bar">
          <div class="pw-strength-seg"></div><div class="pw-strength-seg"></div><div class="pw-strength-seg"></div><div class="pw-strength-seg"></div>
        </div>
        <div class="pw-strength-label" id="pw-strength-label"><i class="ti ti-shield"></i> قدرت رمز</div>
        <div class="pw-field" style="margin-bottom:18px;margin-top:10px">
          <label>تکرار رمز جدید</label>
          <input class="pw-input" type="password" id="cp-cf" placeholder="تکرار رمز جدید">
          <button class="pw-eye" type="button" onclick="togglePwField('cp-cf',this)"><i class="ti ti-eye"></i></button>
        </div>
        <button class="pw-submit" onclick="changePw()"><i class="ti ti-shield-check"></i> ذخیره رمز جدید</button>
      </div>
    </div>

    <div class="pw-panel" style="margin-top:16px; grid-column: 1 / -1;">
      <div class="pw-hero" style="background: linear-gradient(135deg, rgba(74,222,128,0.1), transparent);">
        <div class="pw-hero-icon" style="background: linear-gradient(135deg, var(--green), #0D9668);"><i class="ti ti-cloud-upload"></i></div>
        <div class="pw-hero-text">
          <div class="pw-hero-title">تنظیمات همگام‌سازی ابری (Cloudflare)</div>
          <div class="pw-hero-sub">بدون قرار دادن رمز در کد، سرورها را به هم متصل کنید</div>
        </div>
      </div>
      <div class="pw-body">
        <div class="form-row" style="margin-bottom:12px">
          <div class="fg" style="flex:1">
            <label>آدرس ورکر واسط (Worker URL)</label>
            <input class="pw-input" id="cf-worker-url" placeholder="https://Sadra-kv-proxy.yourname.workers.dev">
          </div>
        </div>
        <div class="form-row" style="margin-bottom:12px">
          <div class="fg" style="flex:1">
            <label>توکن امنیتی (Secret Auth Token)</label>
            <input class="pw-input" type="password" id="cf-worker-token" placeholder="در صورت عدم تغییر، خالی بگذارید">
          </div>
        </div>
        <div class="cl" style="margin-top:0; margin-bottom:16px;">
          <i class="ti ti-info-circle"></i>
          <span>اطلاعات اتصال فقط روی این سرور ذخیره می‌شود و به هیچ وجه در گیت‌هاب پابلیک نمی‌شود.</span>
        </div>
        <div style="display:flex;gap:8px">
          <button class="pw-submit" style="background:var(--green);color:#000;flex:1" onclick="saveCfSync()"><i class="ti ti-check"></i> ذخیره در سرور</button>
          <button class="pw-submit" style="background:var(--accent-d);color:var(--accent);flex:1;box-shadow:none" onclick="testCfSync()"><i class="ti ti-wifi"></i> تست اتصال</button>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px;padding-top:12px;border-top:1px solid var(--card-b)">
          <button class="pw-submit" style="background:var(--accent);color:#000;flex:1;box-shadow:none" onclick="uploadToCf()"><i class="ti ti-cloud-upload"></i> ذخیره/آپلود در تلگرام و کلودفلر</button>
          <button class="pw-submit" style="background:var(--purple);color:#000;flex:1;box-shadow:none" onclick="downloadFromCf()"><i class="ti ti-cloud-download"></i> دریافت دیتا از کلودفلر</button>
        </div>
      </div>
    </div>

    <div class="pw-panel" style="margin-top:16px; grid-column: 1 / -1;">
      <div class="pw-hero" style="background: linear-gradient(135deg, rgba(59,130,246,0.1), transparent);">
        <div class="pw-hero-icon" style="background: linear-gradient(135deg, #3B82F6, #2563EB);box-shadow:0 6px 18px rgba(59,130,246,0.25)"><i class="ti ti-brand-telegram"></i></div>
        <div class="pw-hero-text">
          <div class="pw-hero-title">تنظیمات ربات تلگرام (بکاپ)</div>
          <div class="pw-hero-sub">فایل دیتابیس را به عنوان پشتیبان در تلگرام ذخیره کنید</div>
        </div>
      </div>
      <div class="pw-body">
        <div class="form-row" style="margin-bottom:12px">
          <div class="fg" style="flex:1.5">
            <label>توکن ربات تلگرام (Bot Token)</label>
            <input class="pw-input" id="tg-bot-token" type="password" placeholder="مثال: 123456:ABC-DEF1234ghIkl-zyx...">
          </div>
          <div class="fg" style="flex:1">
            <label>آیدی عددی ادمین (Admin ID)</label>
            <input class="pw-input" id="tg-admin-id" placeholder="مثال: 123456789">
          </div>
        </div>
        <div class="cl" style="margin-top:0; margin-bottom:16px; background:rgba(59,130,246,0.1); border-color:rgba(59,130,246,0.2); color:var(--t1)">
          <i class="ti ti-info-circle" style="color:#3B82F6"></i>
          <span style="font-size:10.5px">برای **دریافت بکاپ از تلگرام**، ابتدا در ربات خود فایل بکاپ را فوروارد/ارسال کنید، سپس دکمه دریافت زیر را بزنید.</span>
        </div>
        <div style="display:flex;gap:8px">
          <button class="pw-submit" style="background:var(--accent-d);color:var(--accent);flex:1;box-shadow:none" onclick="saveTgSettings()"><i class="ti ti-device-floppy"></i> ذخیره تنظیمات تلگرام</button>
          <button class="pw-submit" style="background:#3B82F6;color:#fff;flex:1" onclick="downloadFromTg()"><i class="ti ti-cloud-download"></i> دریافت دیتا از تلگرام</button>
        </div>
      </div>
    </div>

  </div>
</section>
</main>
<script>
let isDark=localStorage.getItem('Sadra-theme')!=='light';
function applyTheme(dark){
  document.documentElement.setAttribute('data-theme',dark?'dark':'light');
  const icon=dark?'ti-sun':'ti-moon',label=dark?'تم روشن':'تم تاریک';
  document.getElementById('theme-icon').className='ti '+icon;
  document.getElementById('theme-label').textContent=label;
  const mobI=document.getElementById('theme-mob-icon');if(mobI)mobI.className='ti '+icon;
}
function toggleTheme(){isDark=!isDark;localStorage.setItem('Sadra-theme',isDark?'dark':'light');applyTheme(isDark)}
applyTheme(isDark);
function toast(msg,type=''){
  const t=document.getElementById('toast');
  t.textContent=msg;t.className='toast show'+(type?' '+type:'');
  setTimeout(()=>t.classList.remove('show'),2400);
}
function fmtB(b){if(!b||b===0)return '0 B';if(b<1024)return b+' B';if(b<1024**2)return (b/1024).toFixed(1)+' KB';if(b<1024**3)return (b/1024**2).toFixed(2)+' MB';return (b/1024**3).toFixed(2)+' GB'}
function toFa(n){return String(n).replace(/\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d])}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function daysLeft(exp){if(!exp)return null;return Math.ceil((new Date(exp)-Date.now())/(864e5))}
function expChip(exp,expired){
  if(expired)return '<span class="exp-chip ec-exp"><i class="ti ti-calendar-x"></i> منقضی</span>';
  if(!exp)return '<span class="exp-chip ec-inf"><i class="ti ti-infinity"></i> نامحدود</span>';
  const d=daysLeft(exp);
  if(d<=0)return '<span class="exp-chip ec-exp"><i class="ti ti-calendar-x"></i> منقضی</span>';
  if(d<=3)return `<span class="exp-chip ec-warn"><i class="ti ti-alert-triangle"></i> ${toFa(d)} روز مانده</span>`;
  return `<span class="exp-chip ec-ok"><i class="ti ti-calendar-check"></i> ${toFa(d)} روز مانده</span>`;
}
function protoBadge(p){
  const m={'vless-ws':['VLESS · WS','pc-ws'], 'httpupgrade':['HTTPUpgrade','pc-ws'], 'xhttp-packet-up':['XHTTP · packet','pc-xhttp'],'xhttp-stream-up':['XHTTP · stream','pc-xhttp'], 'xhttp-reality':['XHTTP Reality','pc-ultra']};
  const v=m[p]||m['vless-ws'];
  return `<span class="proto-chip ${v[1]}">${v[0]}</span>`;
}
async function checkAuth(){try{const r=await fetch('/api/me');const d=await r.json();if(!d.authenticated)location.href='/sadra1491388191378';}catch(e){location.href='/sadra1491388191378'}}
async function logout(){try{await fetch('/api/logout',{method:'POST'})}catch(e){}location.href='/sadra1491388191378'}
document.getElementById('logout-btn').addEventListener('click',logout);
async function authF(url,opts={}){
  const r=await fetch(url,opts);
  if(r.status===401){location.href='/sadra1491388191378';throw new Error('unauthorized')}
  return r;
}
function selectProto(val,el){
  document.getElementById('nl-proto').value = val;
  document.querySelectorAll('.proto-card').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
}
function onAlpnPresetChange(){
  const p=document.getElementById('nl-alpn-preset').value;
  const inp=document.getElementById('nl-alpn');
  if(p==='__custom__'){inp.style.display='block';inp.value='';inp.focus();}
  else{inp.style.display='none';inp.value=p;}
}
const sb=document.getElementById('sb'),overlay=document.getElementById('overlay');
function openSb(){sb.classList.add('open');overlay.classList.add('show')}
function closeSb(){sb.classList.remove('open');overlay.classList.remove('show')}
document.getElementById('open-sb').addEventListener('click',openSb);
document.getElementById('close-sb').addEventListener('click',closeSb);
overlay.addEventListener('click',closeSb);
function navTo(name){
  document.querySelectorAll('.nav-it').forEach(n=>n.classList.toggle('on',n.dataset.pg===name));
  document.querySelectorAll('.pg').forEach(p=>p.classList.toggle('on',p.id==='pg-'+name));
  const loaders={links:loadLinks,connections:loadConns,errors:loadErrs,subscriptions:loadSubsPage,subgroups:loadSubs,logs:loadActivity};
  if(loaders[name])loaders[name]();
  closeSb();window.scrollTo({top:0,behavior:'smooth'});
}
document.querySelectorAll('.nav-it').forEach(el=>el.addEventListener('click',()=>navTo(el.dataset.pg)));
function openModal(id){document.getElementById(id).classList.add('open')}
function closeModal(id){document.getElementById(id).classList.remove('open')}
async function fetchStats(){
  try{
    const r=await authF('/stats'),d=await r.json();
    document.getElementById('m-conns').textContent=d.active_connections;
    document.getElementById('conns-nb').textContent=d.active_connections;
    document.getElementById('m-traffic').innerHTML=d.total_traffic_mb.toFixed(1)+'<span class="m-unit">MB</span>';
    document.getElementById('m-alinks').textContent=d.active_links??'—';
    document.getElementById('m-lsub').textContent='از '+d.links_count+' کانفیگ';
    document.getElementById('m-subs').textContent=d.subs_count??'—';
    document.getElementById('errs-badge').textContent=d.total_errors+' خطا';
    document.getElementById('uptime-inline').textContent=d.uptime;
    document.getElementById('uptime-badge').textContent='Sadra Engine · '+d.uptime;
    document.getElementById('last-upd').textContent='آخرین بروزرسانی: '+new Date().toLocaleTimeString('fa-IR');
    document.getElementById('conns-live').innerHTML='<span class="dot dg pulse"></span> '+d.active_connections+' اتصال';
    renderErrs(d.recent_errors||[]);
  }catch(e){console.error(e)}
}
function renderErrs(errs){
  const el=document.getElementById('errs-full');if(!el)return;
  if(!errs.length){el.innerHTML='<div style="color:var(--green-t);padding:10px;font-size:12px;display:flex;align-items:center;gap:5px"><i class="ti ti-circle-check"></i> هیچ خطایی نیست</div>';return}
  el.innerHTML=errs.slice().reverse().map(e=>`<div class="erow"><div class="etime"><i class="ti ti-clock"></i>${new Date(e.time).toLocaleString('fa-IR')}</div><div class="emsg">${esc(e.error)}${e.url?' — '+esc(e.url):''}</div></div>`).join('');
}
async function loadActivity(){
  try{
    const r=await authF('/api/activity'),d=await r.json();
    const logs=(d.logs||[]).slice().reverse();
    const el=document.getElementById('logs-list'),em=document.getElementById('logs-empty');
    if(!logs.length){el.innerHTML='';em.style.display='block';return}
    em.style.display='none';
    const icMap={ok:'ti-circle-check',err:'ti-circle-x',warn:'ti-alert-triangle',info:'ti-info-circle'};
    const kindFa={link:'کانفیگ',sub:'گروه',auth:'ورود',connection:'اتصال',system:'سیستم'};
    el.innerHTML=logs.map(l=>`
      <div class="log-item">
        <div class="log-ic ${l.level}"><i class="ti ${icMap[l.level]||'ti-info-circle'}"></i></div>
        <div class="log-body">
          <div class="log-msg">${esc(l.message)}</div>
          <div class="log-time"><i class="ti ti-clock"></i> ${new Date(l.time).toLocaleString('fa-IR')} <span class="log-kind">${kindFa[l.kind]||l.kind}</span></div>
        </div>
      </div>
    `).join('');
  }catch(e){console.error(e)}
}
let allSubsList=[],allLinksList=[];

// تابع را بیرون آوردیم تا در کل کد قابل دسترسی باشد
function renderSubCheckboxes(containerId, subsList, checkedSet = new Set()) {
    const container = document.getElementById(containerId);
    if(!container) return;
    const currentlyChecked = new Set([...container.querySelectorAll('input:checked')].map(cb => cb.value));
    const finalChecked = checkedSet.size > 0 ? checkedSet : currentlyChecked;
    
    container.innerHTML = subsList.map(s => `
        <label style="display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--t1);cursor:pointer;padding:6px;border-radius:8px;background:rgba(255,215,0,0.05);border:1px solid transparent;transition:.15s" onmouseover="this.style.borderColor='var(--card-b)'" onmouseout="this.style.borderColor='transparent'">
            <input type="checkbox" value="${esc(s.sub_id)}" class="sub-cb" ${finalChecked.has(s.sub_id) ? 'checked' : ''} style="width:16px;height:16px;accent-color:var(--accent)">
            <span>${esc(s.name)}</span>
        </label>
    `).join('');
}

async function loadLinks(){
  try{
    const [lr,sr]=await Promise.all([authF('/api/links'),authF('/api/subs')]);
    const {links=[]}=await lr.json();
    const {subs=[]}=await sr.json();
    allSubsList=subs;allLinksList=links;
    
    renderSubCheckboxes('nl-subs-list', subs);
    document.getElementById('links-nb').textContent=links.length;
    document.getElementById('links-pg-cnt').textContent=toFa(links.length)+' کانفیگ';
    document.getElementById('lsummary-badge').textContent=toFa(links.length);
    const grid=document.getElementById('links-grid'),empty=document.getElementById('links-empty');
    if(!links.length){grid.innerHTML='';empty.style.display='block';document.getElementById('lsummary').innerHTML='<div class="empty"><i class="ti ti-link-off"></i><p>کانفیگی وجود ندارد</p></div>';return}
    empty.style.display='none';
    grid.innerHTML=links.map(l=>{
  const lim=l.limit_bytes===0?'∞':fmtB(l.limit_bytes);
  const pct=l.limit_bytes===0?0:Math.min(100,l.used_bytes/l.limit_bytes*100);
  const bc=pct>90?'var(--red)':pct>70?'var(--amber)':'var(--accent)';
  const allowed=l.active&&!l.expired;
  const cardCls=!l.active?'is-off':(l.expired?'is-exp':'');
  return `<div class="cfg-card ${cardCls}">
    <div class="cfg-row">
      <span class="cfg-status-dot ${allowed?'pulse':''}"></span>
      <div class="cfg-identity">
        <div class="cfg-label">${esc(l.label)}</div>
        <div class="cfg-sub-meta">
          <span class="cfg-uuid-mini" onclick="navigator.clipboard.writeText('${l.uuid}').then(()=>toast('UUID کپی شد','ok'))" title="${l.uuid}"><i class="ti ti-fingerprint"></i> ${l.uuid.slice(0,10)}…</span>
        <span>${new Date(l.created_at).toLocaleDateString('fa-IR')}</span>
        ${l.connected_ips > 0 ? `<span style="color:var(--green-t);font-weight:700;background:var(--green-bg);padding:2px 6px;border-radius:4px"><i class="ti ti-users"></i> ${l.connected_ips} متصل</span>` : `<span style="color:var(--t3);"><i class="ti ti-users"></i> ۰ متصل</span>`}
        </div>
      </div>
      <div class="cfg-divider-v"></div>
      <div class="cfg-usage-col">
        <div class="ubar"><div class="ubar-f" style="width:${pct}%;background:${bc}"></div></div>
        <div class="utxt"><span>${fmtB(l.used_bytes)}</span><span>از ${lim}</span></div>
      </div>
      <div class="cfg-divider-v"></div>
      <div class="cfg-exp-col">${expChip(l.expires_at,l.expired)}</div>
      <div class="cfg-divider-v"></div>
      <div class="cfg-badges-col">
        ${protoBadge(l.protocol)}
        <span class="cfg-sub-tag" title="پورت اتصال"><i class="ti ti-route"></i> :${l.port||443}</span>
        ${l.address ? `<span class="cfg-sub-tag" title="آدرس اختصاصی"><i class="ti ti-world"></i> ${esc(l.address)}</span>` : ''}
        ${(l.sub_ids||[]).map(sid => {
            const sub = allSubsList.find(s=>s.sub_id===sid);
            return sub ? `<span class="cfg-sub-tag"><i class="ti ti-folder"></i> ${esc(sub.name)}</span>` : '';
        }).join('')}
      </div>
      <div class="cfg-divider-v"></div>
      <div class="cfg-actions">
        <button class="tog${allowed?' on':''}" onclick="toggleActive('${l.uuid}',${!l.active})" title="فعال/غیرفعال"></button>
        <button class="btn btn-sm btn-p btn-icon" style="width:auto;padding:0 10px" onclick="openVariations('${l.uuid}')" title="لینک‌ها"><i class="ti ti-layers-linked"></i> ${l.variations.length} لینک</button>
        <button class="btn btn-sm btn-g btn-icon" onclick="navigator.clipboard.writeText('${esc(l.sub_url)}').then(()=>toast('Sub کپی شد','ok'))" title="Sub URL"><i class="ti ti-rss"></i></button>
        <button class="btn btn-sm btn-amber btn-icon" onclick="openEditLink('${l.uuid}')" title="ویرایش"><i class="ti ti-edit"></i></button>
        <button class="btn btn-sm btn-g btn-icon" onclick="resetUsage('${l.uuid}')" title="ریست مصرف"><i class="ti ti-rotate"></i></button>
        <button class="btn btn-sm btn-d btn-icon" onclick="deleteLink('${l.uuid}')" title="حذف"><i class="ti ti-trash"></i></button>
      </div>
    </div>
  </div>`;
}).join('');
    document.getElementById('lsummary').innerHTML=links.slice(0,6).map(l=>`<div class="sr"><span class="sr-k" style="gap:5px"><i class="ti ${l.expired?'ti-calendar-x':l.active?'ti-circle-check':'ti-circle-x'}" style="color:${l.expired?'var(--amber)':l.active?'var(--green)':'var(--red)'}"></i>${esc(l.label)}</span><span class="sr-v" style="font-size:10px">${fmtB(l.used_bytes)} / ${l.limit_bytes===0?'∞':fmtB(l.limit_bytes)}</span></div>`).join('');
  }catch(e){console.error(e)}
}
async function createLink(){
  const label=document.getElementById('nl-label').value.trim()||'کانفیگ جدید';
  const val=document.getElementById('nl-val').value;
  const unit=document.getElementById('nl-unit').value;
  const exp=document.getElementById('nl-exp').value;
  const note=document.getElementById('nl-note').value.trim();
  const sub_domain=document.getElementById('nl-sub-domain').value.trim();
  const protocol=document.getElementById('nl-proto').value||'vless-ws';
  const fingerprint=document.getElementById('nl-fp').value||'chrome';
  const alpn=document.getElementById('nl-alpn').value.trim();
  const port=Number(document.getElementById('nl-port').value)||443;
  const ip_limit=Number(document.getElementById('nl-iplimit').value)||0;
  const speed_limit_value=Number(document.getElementById('nl-speed').value)||0;
  const speed_limit_unit=document.getElementById('nl-speed-unit').value;
  const customs=getCustomFields('nl');
  const sub_ids = Array.from(document.querySelectorAll('#nl-subs-list input:checked')).map(cb => cb.value);

  try{
    const r=await authF('/api/links',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label,limit_value:val||0,limit_unit:unit,expires_days:exp||0,note,protocol,fingerprint,alpn,port,ip_limit,speed_limit_value,speed_limit_unit,customs,custom_domain:sub_domain,sub_ids})});
    if(!r.ok)throw new Error('failed');
    ['nl-label','nl-val','nl-exp','nl-note','nl-alpn','nl-sub-domain'].forEach(id=>document.getElementById(id).value='');
    document.getElementById('nl-customs-list').innerHTML='';
    toast('کانفیگ ساخته شد ✓','ok');loadLinks();
  }catch(e){toast('خطا در ساخت','err')}
}
function openEditLink(uuid){
  const l=allLinksList.find(x=>x.uuid===uuid);
  if(!l)return;
  
  const varSubs = l.var_subs || {};
  renderSubCheckboxes('el-subs-list', allSubsList, new Set(varSubs['default'] || []));
  document.getElementById('el-uuid').value=uuid;
  document.getElementById('el-label').value=l.label;
  document.getElementById('el-note').value=l.note||'';
  document.getElementById('el-sub-domain').value=l.custom_domain||'';
  if(l.limit_bytes===0){document.getElementById('el-val').value='';document.getElementById('el-unit').value='GB';}
  else{document.getElementById('el-val').value=(l.limit_bytes/1024/1024).toFixed(0);document.getElementById('el-unit').value='MB';}
  document.getElementById('el-exp').value='';
  document.getElementById('el-fp').value=l.fingerprint||'chrome';
  document.getElementById('el-alpn').value=l.alpn||'';
  document.getElementById('el-port').value=l.port||443;
  document.getElementById('el-iplimit').value=l.ip_limit||0;
  if(!l.speed_limit_bytes){document.getElementById('el-speed').value='0';document.getElementById('el-speed-unit').value='MBIT';}
  else{document.getElementById('el-speed').value=(l.speed_limit_bytes*8/1024/1024).toFixed(2);document.getElementById('el-speed-unit').value='MBIT';}
  
  document.getElementById('el-customs-list').innerHTML = '';
  (l.customs || []).forEach((c, idx) => {
      const cSubs = varSubs[String(idx)] || [];
      addCustomField('el', c.name, c.address, c.host_sni, cSubs);
  });
  
  openModal('modal-edit-link');
}
async function saveEditLink(){
  const uuid=document.getElementById('el-uuid').value;
  const label=document.getElementById('el-label').value.trim();
  const note=document.getElementById('el-note').value.trim();
  const sub_domain=document.getElementById('el-sub-domain').value.trim();
  const val=document.getElementById('el-val').value;
  const unit=document.getElementById('el-unit').value;
  const exp=document.getElementById('el-exp').value;
  const fingerprint=document.getElementById('el-fp').value||'chrome';
  const alpn=document.getElementById('el-alpn').value.trim();
  const port=Number(document.getElementById('el-port').value)||443;
  const ip_limit=Number(document.getElementById('el-iplimit').value)||0;
  const speed_limit_value=Number(document.getElementById('el-speed').value)||0;
  const speed_limit_unit=document.getElementById('el-speed-unit').value;
  const customs=getCustomFields('el');
  const sub_ids = Array.from(document.querySelectorAll('#el-subs-list input:checked')).map(cb => cb.value);

  const body={label,note,limit_value:val||0,limit_unit:unit,fingerprint,alpn,port,ip_limit,speed_limit_value,speed_limit_unit,customs,custom_domain:sub_domain,sub_ids};
  if(exp !== '') body.expires_days=Number(exp);
  try{
    const r=await authF('/api/links/'+uuid,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r.ok)throw new Error();
    closeModal('modal-edit-link');
    toast('ویرایش شد ✓','ok');loadLinks();
  }catch(e){toast('خطا در ویرایش','err')}
}
async function toggleActive(uuid,newState){
  try{const r=await authF('/api/links/'+uuid,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({active:newState})});if(!r.ok)throw new Error();toast(newState?'فعال شد ✓':'غیرفعال شد','ok');loadLinks();}catch(e){toast('خطا','err')}
}
async function resetUsage(uuid){
  try{const r=await authF('/api/links/'+uuid,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({reset_usage:true})});if(!r.ok)throw new Error();toast('مصرف ریست شد ✓','ok');loadLinks();}catch(e){toast('خطا','err')}
}
async function deleteLink(uuid){
  if(!confirm('حذف این کانفیگ؟'))return;
  try{const r=await authF('/api/links/'+uuid,{method:'DELETE'});if(!r.ok)throw new Error();toast('حذف شد ✓','ok');loadLinks();}catch(e){toast('خطا','err')}
}
function showQR(link){window.open('https://api.qrserver.com/v1/create-qr-code/?size=300x300&data='+encodeURIComponent(link),'_blank')}
let allSubsRaw=[];
async function loadSubs(){
  try{
    const r=await authF('/api/subs'),d=await r.json();
    const subs=d.subs||[];
    allSubsRaw=subs;
    document.getElementById('subs-nb').textContent=subs.length;
    document.getElementById('subs-pg-cnt').textContent=toFa(subs.length)+' گروه';
    renderSubsGrid(subs);
  }catch(e){console.error(e)}
}
function renderSubsGrid(subs){
  const grid=document.getElementById('subs-grid');
  if(!subs.length){
    grid.innerHTML='<div class="subs-empty-v2"><div class="subs-empty-v2-icon"><i class="ti ti-folders"></i></div><div class="subs-empty-v2-title">هنوز گروهی وجود ندارد</div></div>';
    return;
  }
  grid.innerHTML=subs.map(s=>`
    <div class="sub-card">
      <div class="sub-card-top">
        <div class="sub-card-head-v2">
          <div class="sub-card-icon"><i class="ti ti-folder"></i></div>
          <div class="sub-card-titles">
            <div class="sub-card-name-v2">${esc(s.name)}</div>
            ${s.desc?`<div class="sub-card-desc-v2">${esc(s.desc)}</div>`:'<div class="sub-card-desc-v2" style="opacity:.5">بدون توضیحات</div>'}
          </div>
          <div class="sub-card-lock-badge ${s.has_password?'locked':'open'}" title="${s.has_password?'رمزدار':'پابلیک'}">
            <i class="ti ${s.has_password?'ti-lock':'ti-lock-open'}"></i>
          </div>
        </div>
        <div class="sub-card-stats">
          <div class="sub-card-stat"><div class="sub-card-stat-val">${toFa(s.links_count)}</div><div class="sub-card-stat-label">کانفیگ</div></div>
          <div class="sub-card-stat"><div class="sub-card-stat-val" style="color:var(--green-t)">${toFa(s.active_count)}</div><div class="sub-card-stat-label">فعال</div></div>
          <div class="sub-card-stat"><div class="sub-card-stat-val" style="font-size:12px">${esc(s.total_used_fmt)}</div><div class="sub-card-stat-label">مصرف</div></div>
        </div>
      </div>
      <div class="sub-card-url-row">
        <span class="sub-card-url-text">${esc(s.public_url)}</span>
        <button class="sub-card-url-copy" onclick="navigator.clipboard.writeText('${esc(s.public_url)}').then(()=>toast('لینک پابلیک کپی شد','ok'))" title="کپی"><i class="ti ti-copy"></i></button>
        <button class="sub-card-url-copy" onclick="window.open('${esc(s.public_url)}','_blank')" title="باز کردن"><i class="ti ti-external-link"></i></button>
      </div>
      <div class="sub-card-bottom">
        <button class="btn btn-sm btn-g" onclick="openSubLinks('${esc(s.sub_id)}','${esc(s.name)}')"><i class="ti ti-link-plus"></i> کانفیگ‌ها</button>
        <button class="btn btn-sm btn-p" onclick="openSubVariations('${esc(s.sub_id)}')"><i class="ti ti-layers-linked"></i> لینک‌ها</button>
        <button class="btn btn-sm btn-amber" onclick="openEditSub('${esc(s.sub_id)}')"><i class="ti ti-edit"></i></button>
        <button class="btn btn-sm btn-d btn-icon" onclick="deleteSub('${esc(s.sub_id)}')" title="حذف"><i class="ti ti-trash"></i></button>
      </div>
    </div>
  `).join('');
}
function filterSubs(q){
  q=q.trim().toLowerCase();
  if(!q){renderSubsGrid(allSubsRaw);return}
  renderSubsGrid(allSubsRaw.filter(s=>s.name.toLowerCase().includes(q)||(s.desc||'').toLowerCase().includes(q)));
}
let savedSubCustomsData = [];
async function loadSavedSubCustoms() {
    try {
        const r = await authF('/api/sub-customs');
        const d = await r.json();
        savedSubCustomsData = d.customs || [];
        renderSavedSubCustoms('ns');
        renderSavedSubCustoms('es');
    } catch(e) {}
}

function renderSavedSubCustoms(prefix) {
    const container = document.getElementById(`${prefix}-saved-customs`);
    if(!container) return;
    if(savedSubCustomsData.length === 0) {
        container.innerHTML = '<span style="font-size:10px;color:var(--t3);padding:8px">هیچ کاستومی ذخیره نشده است.</span>';
        return;
    }
    container.innerHTML = savedSubCustomsData.map(c => `
        <div style="background:var(--accent-d);border:1px solid var(--card-b);border-radius:10px;padding:8px 10px;cursor:pointer;flex-shrink:0;min-width:130px;position:relative;transition:.15s" onmouseover="this.style.borderColor='var(--accent)'" onmouseout="this.style.borderColor='var(--card-b)'" onclick="addSubCustomField('${prefix}', '${esc(c.name)}', '${esc(c.domain)}')">
            <div style="font-weight:800;font-size:11.5px;color:var(--t1);margin-bottom:2px">${esc(c.name)}</div>
            <div style="font-size:9.5px;color:var(--t3);line-height:1.4;font-family:ui-monospace,monospace" dir="ltr">
                ${esc(c.domain) || 'ندارد'}
            </div>
            <button onclick="event.stopPropagation(); deleteSavedSubCustom('${c.id}')" style="position:absolute;top:6px;left:6px;background:none;border:none;color:var(--red-t);cursor:pointer;padding:2px"><i class="ti ti-trash" style="font-size:13px"></i></button>
        </div>
    `).join('');
}

async function saveSubCustomFromRow(btn, prefix) {
    const row = btn.parentElement;
    const name = row.querySelector(`.${prefix}-c-name`).value.trim();
    const domain = row.querySelector(`.${prefix}-c-domain`).value.trim();
    if(!name && !domain) return toast('فیلدها خالی هستند', 'err');
    
    try {
        const r = await authF('/api/sub-customs', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name, domain})});
        if(r.ok) {
            toast('کاستوم ساب ذخیره شد ✓', 'ok');
            loadSavedSubCustoms();
        }
    } catch(e) { toast('خطا در ذخیره', 'err'); }
}

async function deleteSavedSubCustom(id) {
    if(!confirm('این کاستوم از لیست ذخیره‌ها حذف شود؟')) return;
    try {
        const r = await authF('/api/sub-customs/'+id, {method: 'DELETE'});
        if(r.ok) { toast('حذف شد ✓', 'ok'); loadSavedSubCustoms(); }
    } catch(e) { toast('خطا در حذف', 'err'); }
}

function addSubCustomField(prefix, name='', domain='') {
    const container = document.getElementById(`${prefix}-customs-list`);
    const div = document.createElement('div');
    div.style.cssText = 'display:flex;gap:6px;align-items:center;background:rgba(0,0,0,0.1);padding:6px 8px;border-radius:10px;border:1px solid var(--card-b)';
    div.innerHTML = `
        <input class="fi ${prefix}-c-name" placeholder="نام (مثل: کلودفلر)" style="width:35%" value="${esc(name)}">
        <input class="fi ${prefix}-c-domain" placeholder="دامنه (مثل: sub.site.com)" style="width:65%;direction:ltr" value="${esc(domain)}">
        <button class="btn btn-g btn-icon" style="flex-shrink:0;width:30px;height:30px;padding:0" onclick="saveSubCustomFromRow(this, '${prefix}')" title="ذخیره این کاستوم"><i class="ti ti-device-floppy"></i></button>
        <button class="btn btn-d btn-icon" style="flex-shrink:0;width:30px;height:30px;padding:0" onclick="this.parentElement.remove()"><i class="ti ti-trash"></i></button>
    `;
    container.appendChild(div);
}

function getSubCustomFields(prefix) {
    const customs = [];
    document.querySelectorAll(`#${prefix}-customs-list > div`).forEach(row => {
        const name = row.querySelector(`.${prefix}-c-name`).value.trim();
        const domain = row.querySelector(`.${prefix}-c-domain`).value.trim();
        if (name || domain) customs.push({name: name || 'کاستوم', domain: domain});
    });
    return customs;
}

async function createSub(){
  const name = document.getElementById('ns-name').value.trim() || 'گروه جدید';
  const desc = document.getElementById('ns-desc').value.trim();
  const pw = document.getElementById('ns-pw').value;
  const customs = getSubCustomFields('ns');
  
  try{
    const r=await authF('/api/subs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name, desc, password:pw, customs})});
    if(!r.ok)throw new Error('failed');
    ['ns-name','ns-desc','ns-pw'].forEach(id=>document.getElementById(id).value='');
    document.getElementById('ns-customs-list').innerHTML = '';
    closeModal('modal-create-sub');
    toast('گروه ساخته شد ✓','ok');
    loadSubs();
  }catch(e){toast('خطا در ساخت گروه','err')}
}

function openEditSub(sub_id) {
    const s = allSubsRaw.find(x => x.sub_id === sub_id);
    if (!s) return;
    document.getElementById('es-id').value = sub_id;
    document.getElementById('es-name').value = s.name;
    document.getElementById('es-desc').value = s.desc || '';
    document.getElementById('es-pw').value = '';
    document.getElementById('es-remove-pw').checked = false;
    
    const list = document.getElementById('es-customs-list');
    list.innerHTML = '';
    (s.customs || []).forEach(c => addSubCustomField('es', c.name, c.domain));
    
    openModal('modal-edit-sub');
}

async function saveEditSub() {
    const sub_id = document.getElementById('es-id').value;
    const name = document.getElementById('es-name').value.trim();
    const desc = document.getElementById('es-desc').value.trim();
    const pw = document.getElementById('es-pw').value.trim();
    const removePw = document.getElementById('es-remove-pw').checked;
    const customs = getSubCustomFields('es');
    
    const body = {name, desc, customs};
    if (pw) body.password = pw;
    if (removePw) body.remove_password = true;

    try{
        const r = await authF('/api/subs/'+sub_id, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        if(!r.ok)throw new Error();
        closeModal('modal-edit-sub');
        toast('تغییرات گروه ذخیره شد ✓','ok');
        loadSubs();
    }catch(e){toast('خطا در ویرایش','err')}
}

function openSubVariations(sub_id) {
    const s = allSubsRaw.find(x => x.sub_id === sub_id);
    if (!s) return;
    
    const list = document.getElementById('variations-list');
    list.innerHTML = s.variations.map(v => `
        <div style="background:var(--accent-d);border:1px solid var(--card-b);padding:14px;border-radius:12px;display:flex;flex-direction:column;gap:10px;margin-bottom:8px">
            <div style="font-weight:800;font-size:13.5px;color:var(--t1)"><i class="ti ti-world"></i> ${esc(v.name)}</div>
            
            <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;background:rgba(0,0,0,0.25);padding:8px 12px;border-radius:9px">
                <div style="flex:1;min-width:0">
                    <div style="font-size:10px;color:var(--t3);margin-bottom:3px;font-weight:700">لینک سابسکریپشن (Sub)</div>
                    <div style="font-size:11px;color:var(--accent);font-family:ui-monospace,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" dir="ltr">${esc(v.sub_url)}</div>
                </div>
                <div style="display:flex;gap:4px">
                    <button class="btn btn-sm btn-p btn-icon" onclick="navigator.clipboard.writeText('${esc(v.sub_url)}').then(()=>toast('لینک ساب کپی شد','ok'))"><i class="ti ti-copy"></i></button>
                    <button class="btn btn-sm btn-o btn-icon" onclick="showQR('${esc(s.name)} - ${esc(v.name)}', '${esc(v.sub_url)}')"><i class="ti ti-qrcode"></i></button>
                </div>
            </div>

            <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;background:rgba(0,0,0,0.25);padding:8px 12px;border-radius:9px">
                <div style="flex:1;min-width:0">
                    <div style="font-size:10px;color:var(--t3);margin-bottom:3px;font-weight:700">صفحه پابلیک اختصاصی (Pub)</div>
                    <div style="font-size:11px;color:var(--green-t);font-family:ui-monospace,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" dir="ltr">${esc(v.public_url)}</div>
                </div>
                <div style="display:flex;gap:4px">
                    <button class="btn btn-sm btn-g btn-icon" style="background:var(--green);color:#000;border:none" onclick="navigator.clipboard.writeText('${esc(v.public_url)}').then(()=>toast('لینک پابلیک کپی شد','ok'))"><i class="ti ti-copy"></i></button>
                    <button class="btn btn-sm btn-o btn-icon" onclick="window.open('${esc(v.public_url)}')"><i class="ti ti-external-link"></i></button>
                </div>
            </div>
        </div>
    `).join('');
    
    const titleEl = document.querySelector('#modal-variations .modal-title');
    if(titleEl) titleEl.innerHTML = `<i class="ti ti-layers-linked"></i> لینک‌های گروه <span style="color:var(--accent)">${esc(s.name)}</span>`;
    
    openModal('modal-variations');
}
async function deleteSub(sub_id){
  if(!confirm('حذف این گروه؟ کانفیگ‌ها حذف نمی‌شوند.'))return;
  try{const r=await authF('/api/subs/'+sub_id,{method:'DELETE'});if(!r.ok)throw new Error();toast('گروه حذف شد ✓','ok');loadSubs();loadLinks();}catch(e){toast('خطا','err')}
}
let lmodalLinks=[], lmodalInSub=new Set(), currentSubId=null;
let lmodalExpanded = new Set(); 

async function openSubLinks(sub_id,name){
  currentSubId=sub_id;
  document.getElementById('modal-sub-name').textContent=name;
  document.getElementById('modal-links-body').innerHTML='<div style="color:var(--t3);font-size:12px;padding:20px;text-align:center"><i class="ti ti-loader-2" style="animation:spin 1s linear infinite;font-size:20px"></i></div>';
  document.getElementById('lmodal-search-inp').value='';
  lmodalExpanded.clear(); 
  openModal('modal-links');
  try{
    const [lr,sr]=await Promise.all([authF('/api/links'),authF('/api/subs')]);
    const {links=[]}=await lr.json();
    const {subs=[]}=await sr.json();
    const thisSub=subs.find(s=>s.sub_id===sub_id);
    lmodalInSub=new Set(thisSub?.link_ids||[]);
    lmodalLinks=links;
    renderLmodalList(links);
  }catch(e){toast('خطا در بارگذاری','err')}
}

function renderLmodalList(links){
  const body=document.getElementById('modal-links-body');
  if(!links.length){body.innerHTML='<div class="empty" style="padding:30px"><i class="ti ti-link-off"></i><p>هنوز کانفیگی وجود ندارد</p></div>';updateLmodalCount();return}
  
  let html = '';
  links.forEach(l => {
      const selectedCount = l.variations.filter(v => lmodalInSub.has(v.id)).length;
      const totalCount = l.variations.length;
      const allSelected = selectedCount === totalCount && totalCount > 0;
      const someSelected = selectedCount > 0 && selectedCount < totalCount;
      
      const parentCheckedClass = allSelected ? 'checked' : (someSelected ? 'half-checked' : '');
      const isExpanded = lmodalExpanded.has(l.uuid);
      const chevron = isExpanded ? 'ti-chevron-down' : 'ti-chevron-left';
      const iconClass = allSelected ? 'ti-check' : (someSelected ? 'ti-minus' : 'ti-check');
      
      html += `
      <div class="lrow-group" data-name="${esc(l.label).toLowerCase()}">
          <div class="lrow-v2 ${parentCheckedClass}" style="margin-bottom:2px" onclick="toggleParentCheck('${l.uuid}', event)">
            <div class="lrow-v2-check"><i class="ti ${iconClass}"></i></div>
            <div class="lrow-v2-info" style="margin-right:8px; flex:1" onclick="toggleParentExpand('${l.uuid}', event)">
              <div class="lrow-v2-name">${esc(l.label)} <span style="font-size:10px;color:var(--t3);font-weight:normal">(${totalCount} لینک)</span></div>
              <div class="lrow-v2-meta"><i class="ti ti-database" style="font-size:10px"></i> ${fmtB(l.used_bytes)}</div>
            </div>
            <div onclick="toggleParentExpand('${l.uuid}', event)" style="padding:5px;cursor:pointer;color:var(--t3);display:flex;align-items:center"><i class="ti ${chevron}"></i></div>
          </div>
          
          <div id="children-${l.uuid}" style="display:${isExpanded ? 'block' : 'none'}; padding-right:24px; border-right:1px dashed var(--card-b); margin-right:10px; margin-bottom:8px">
      `;
      
      l.variations.forEach(v => {
          const checked = lmodalInSub.has(v.id);
          html += `<div class="lrow-v2 ${checked?'checked':''}" style="padding:6px 10px; margin-bottom:2px" onclick="toggleChildCheck('${v.id}')">
            <div class="lrow-v2-check" style="width:16px;height:16px;border-radius:5px"><i class="ti ti-check" style="font-size:10px"></i></div>
            <div class="lrow-v2-info" style="margin-right:8px">
              <div class="lrow-v2-name" style="font-size:11.5px;color:var(--t2)">${esc(v.name)}</div>
            </div>
          </div>`;
      });
      html += `</div></div>`;
  });
  body.innerHTML = html;
  updateLmodalCount();
}

function toggleParentExpand(uuid, event) {
    event.stopPropagation();
    if(lmodalExpanded.has(uuid)) lmodalExpanded.delete(uuid);
    else lmodalExpanded.add(uuid);
    renderLmodalList(lmodalLinks);
}

function toggleParentCheck(uuid, event) {
    event.stopPropagation();
    const l = lmodalLinks.find(x => x.uuid === uuid);
    if(!l) return;
    const selectedCount = l.variations.filter(v => lmodalInSub.has(v.id)).length;
    const totalCount = l.variations.length;
    const allSelected = selectedCount === totalCount && totalCount > 0;
    
    if(allSelected) l.variations.forEach(v => lmodalInSub.delete(v.id));
    else l.variations.forEach(v => lmodalInSub.add(v.id));
    renderLmodalList(lmodalLinks);
}

function toggleChildCheck(vid) {
  if(lmodalInSub.has(vid)) lmodalInSub.delete(vid);
  else lmodalInSub.add(vid);
  renderLmodalList(lmodalLinks);
}

function lmodalSelectAll(state){
  lmodalLinks.forEach(l=>{
      l.variations.forEach(v => {
          if(state) lmodalInSub.add(v.id);
          else lmodalInSub.delete(v.id);
      });
  });
  renderLmodalList(lmodalLinks);
}

function updateLmodalCount(){
  const el=document.getElementById('lmodal-count');
  if(el)el.textContent=toFa(lmodalInSub.size)+' انتخاب شده';
}

function filterLmodal(q){
  q=q.trim().toLowerCase();
  document.querySelectorAll('#modal-links-body .lrow-group').forEach(group=>{
    group.style.display = !q || group.dataset.name.includes(q) ? '' : 'none';
  });
}

async function saveSubLinks(){
  if(!currentSubId)return;
  const link_ids=[...lmodalInSub];
  try{
    const r=await authF('/api/subs/'+currentSubId,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({link_ids})});
    if(!r.ok)throw new Error();
    closeModal('modal-links');
    toast('کانفیگ‌های گروه ذخیره شدند ✓','ok');
    loadSubs();loadLinks();
  }catch(e){toast('خطا در ذخیره','err')}
}

async function loadSubsPage(){
  document.getElementById('sub-all-url').textContent=location.protocol+'//'+location.host+'/sub-all';
  try{
    const r=await authF('/api/subs'),d=await r.json();
    const subs=d.subs||[];
    const el=document.getElementById('sub-groups-list');
    if(!subs.length){el.innerHTML='<div class="empty"><i class="ti ti-rss-off"></i><p>هنوز گروهی ندارید</p></div>';return}
    el.innerHTML=subs.map(s=>`
      <div style="padding:13px 15px;background:var(--accent-d);border:1px solid var(--card-b);border-radius:10px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap">
        <div>
          <div style="font-weight:700;font-size:13px;margin-bottom:3px">${esc(s.name)}</div>
          <div style="font-family:ui-monospace,monospace;font-size:10px;color:var(--accent)">${esc(s.sub_url)}</div>
          <div style="font-size:10px;color:var(--t3);margin-top:3px">${toFa(s.links_count)} کانفیگ · ${esc(s.total_used_fmt)} مصرف ${s.has_password?'· 🔒 رمزدار':''}</div>
        </div>
        <div style="display:flex;gap:5px;flex-wrap:wrap">
          <button class="btn btn-sm btn-g" onclick="navigator.clipboard.writeText('${esc(s.sub_url)}').then(()=>toast('کپی شد','ok'))"><i class="ti ti-copy"></i> ساب</button>
          <button class="btn btn-sm btn-g" onclick="navigator.clipboard.writeText('${esc(s.public_url)}').then(()=>toast('کپی شد','ok'))"><i class="ti ti-globe"></i> پابلیک</button>
          <button class="btn btn-sm btn-o" onclick="showQR('${esc(s.sub_url)}')"><i class="ti ti-qrcode"></i></button>
        </div>
      </div>
    `).join('');
  }catch(e){}
}
function cpSubAll(){navigator.clipboard.writeText(location.protocol+'//'+location.host+'/sub-all').then(()=>toast('کپی شد ✓','ok'))}
function parseBytesFmt(s){
  if(!s)return 0;
  const m=String(s).match(/([\d.]+)\s*([A-Za-z]+)/);
  if(!m)return 0;
  const n=parseFloat(m[1]),u=m[2].toUpperCase();
  const mult={B:1,KB:1024,MB:1024**2,GB:1024**3,TB:1024**4};
  return n*(mult[u]||1);
}
async function loadConns(){
  try{
    const r=await authF('/api/connections'),d=await r.json();
    const grid=document.getElementById('conns-grid'),ce=document.getElementById('conns-empty');
    document.getElementById('conns-live').innerHTML='<span class="dot dg pulse"></span> '+d.count+' اتصال';
    document.getElementById('ch-count').textContent=toFa(d.count);
    const conns=d.connections||[];
    if(!d.count){
      grid.innerHTML='';ce.style.display='block';
      document.getElementById('ch-traffic').textContent='—';
      return;
    }
    ce.style.display='none';
    const totalBytes=conns.reduce((s,c)=>s+parseBytesFmt(c.bytes_fmt),0);
    document.getElementById('ch-traffic').textContent=fmtB(totalBytes);
    const maxDur=Math.max(...conns.map(c=>c.connected_at?Math.max(0,Math.floor((Date.now()-new Date(c.connected_at).getTime())/1000)):0),1);
    grid.innerHTML=conns.map(c=>{
      const secs=c.connected_at?Math.max(0,Math.floor((Date.now()-new Date(c.connected_at).getTime())/1000)):0;
      const dur=secs<60?secs+' ثانیه':secs<3600?Math.floor(secs/60)+' دقیقه':Math.floor(secs/3600)+' ساعت';
      const durPct=Math.min(100,Math.round((secs/maxDur)*100));
      const protoVal=c.transport==='vless-ws'?'vless-ws':(c.transport||'').replace('xhttp-','xhttp-');
      return `<div class="conn-card-v2">
        <div class="conn-card-v2-glow"></div>
        <div class="conn-card-v2-top">
          <div class="conn-avatar"><i class="ti ti-device-desktop"></i></div>
          <div class="conn-card-v2-id">
            <div class="conn-ip-v2">${esc(c.ip)}
              <button class="conn-ip-copy" onclick="navigator.clipboard.writeText('${esc(c.ip)}').then(()=>toast('IP کپی شد','ok'))" title="کپی IP"><i class="ti ti-copy"></i></button>
            </div>
            <div class="conn-label-v2">${esc(c.label)}</div>
          </div>
          <span class="conn-status-pill"><span class="dot dg pulse"></span> زنده</span>
        </div>
        <div class="conn-card-v2-divider"></div>
        <div class="conn-card-v2-body">
          <div class="conn-proto-row">${protoBadge(protoVal)}</div>
          <div class="conn-stat-row">
            <div class="conn-stat-box">
              <div class="conn-stat-icon"><i class="ti ti-transfer"></i></div>
              <div>
                <div class="conn-stat-text-label">ترافیک</div>
                <div class="conn-stat-text-val">${esc(c.bytes_fmt)}</div>
              </div>
            </div>
            <div class="conn-stat-box">
              <div class="conn-stat-icon time"><i class="ti ti-clock"></i></div>
              <div>
                <div class="conn-stat-text-label">مدت اتصال</div>
                <div class="conn-stat-text-val">${dur}</div>
              </div>
            </div>
          </div>
          <div class="conn-duration-track"><div class="conn-duration-fill" style="width:${durPct}%"></div></div>
        </div>
      </div>`;
    }).join('');
  }catch(e){console.error(e)}
}
async function fetchDefaultVless(){
  try{const r=await authF('/api/links'),d=await r.json();const links=d.links||[];const def=links.find(l=>l.limit_bytes===0&&l.active&&!l.expired)||links.find(l=>l.active&&!l.expired)||links[0];document.getElementById('vless-main').textContent=def?def.vless_link:'هنوز کانفیگی وجود ندارد';}catch(e){}
}
function cpText(id){navigator.clipboard.writeText(document.getElementById(id).textContent).then(()=>toast('کپی شد ✓','ok'))}
function qrFor(id){showQR(document.getElementById(id).textContent)}
function refreshAll(){fetchStats();fetchDefaultVless();loadLinks();if(document.getElementById('pg-subgroups').classList.contains('on'))loadSubs();if(document.getElementById('pg-subscriptions').classList.contains('on'))loadSubsPage();if(document.getElementById('pg-connections').classList.contains('on'))loadConns();if(document.getElementById('pg-logs').classList.contains('on'))loadActivity();toast('رفرش شد','ok')}
async function changePw(){
  const cur=document.getElementById('cp-cur').value,nw=document.getElementById('cp-new').value,cf=document.getElementById('cp-cf').value;
  if(!cur||!nw||!cf){toast('همه فیلدها را پر کنید','err');return}
  if(nw.length<4){toast('حداقل ۴ کاراکتر','err');return}
  if(nw!==cf){toast('تکرار رمز اشتباه','err');return}
  try{
    const r=await authF('/api/change-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_password:cur,new_password:nw})});
    const d=await r.json().catch(()=>({}));
    if(!r.ok)throw new Error(d.detail||'خطا');
    toast('رمز تغییر کرد ✓','ok');
    ['cp-cur','cp-new','cp-cf'].forEach(id=>document.getElementById(id).value='');
  }catch(e){toast('✗ '+e.message,'err')}
}
function togglePwField(id,btn){
  const inp=document.getElementById(id);
  const icon=btn.querySelector('i');
  const toText=inp.type==='password';
  inp.type=toText?'text':'password';
  icon.className='ti '+(toText?'ti-eye-off':'ti-eye');
}
function checkPwStrength(val){
  const segs=document.querySelectorAll('#pw-strength-bar .pw-strength-seg');
  const label=document.getElementById('pw-strength-label');
  const hasLen=val.length>=4,hasNum=/\d/.test(val),hasCase=/[a-z]/.test(val)&&/[A-Z]/.test(val),hasLong=val.length>=8;
  let score=0;if(hasLen)score++;if(hasNum)score++;if(hasCase)score++;if(hasLong)score++;
  const colors=['#EF4444','#F59E0B','#3B82F6','#10B981'],labels=['خیلی ضعیف','ضعیف','متوسط','قوی'];
  segs.forEach((s,i)=>{s.style.background=i<score?colors[Math.max(0,score-1)]:'rgba(100,116,139,.2)'});
  if(val.length===0){label.innerHTML='<i class="ti ti-shield"></i> قدرت رمز';return}
  label.innerHTML=`<i class="ti ti-shield-check" style="color:${colors[Math.max(0,score-1)]}"></i> ${labels[Math.max(0,score-1)]}`;
}
let ws;
function wsLog(c,m){const l=document.getElementById('ws-log'),p=document.createElement('p');const colors={ok:'#4ade80',err:'#f87171',info:'#FFD700',sent:'#C8900A'};p.style.color=colors[c]||'#fff';p.textContent='['+new Date().toLocaleTimeString('fa-IR')+'] '+m;l.appendChild(p);l.scrollTop=l.scrollHeight}
function wsConn(){const u=document.getElementById('ws-uuid').value.trim();if(!u){toast('UUID را وارد کنید','err');return}const url=(location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/ws/'+u;wsLog('info','اتصال: '+url);ws=new WebSocket(url);ws.onopen=()=>wsLog('ok','✓ متصل - UUID معتبر');ws.onerror=()=>wsLog('err','✗ خطا - UUID نامعتبر یا غیرفعال');ws.onmessage=m=>wsLog('info','دریافت '+(m.data.size||m.data.length)+' byte');ws.onclose=e=>wsLog('err','قطع ('+e.code+')'+(e.code===1008?' - دسترسی رد شد':''))}
function wsSend(){const m=document.getElementById('ws-msg').value;if(!m||!ws||ws.readyState!==1)return;ws.send(m);wsLog('sent','ارسال: '+m);document.getElementById('ws-msg').value=''}
function wsDisc(){if(ws)ws.close()}

async function loadCfSyncSettings() {
  try {
    const r = await authF('/api/settings/cf-sync');
    const d = await r.json();
    document.getElementById('cf-worker-url').value = d.worker_url || '';
    if (d.has_token) {
      document.getElementById('cf-worker-token').placeholder = '•••••••••••• (ذخیره شده در سرور)';
    }
  } catch(e) {}
}

async function saveCfSync() {
  const url = document.getElementById('cf-worker-url').value.trim();
  const token = document.getElementById('cf-worker-token').value.trim();
  try {
    const r = await authF('/api/settings/cf-sync', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ worker_url: url, token: token })
    });
    if (!r.ok) throw new Error();
    toast('تنظیمات ابری ذخیره شد ✓', 'ok');
    document.getElementById('cf-worker-token').value = '';
    loadCfSyncSettings();
  } catch(e) {
    toast('خطا در ذخیره', 'err');
  }
}

async function testCfSync() {
  toast('در حال تست ارتباط...', 'info');
  try {
    const r = await authF('/test-cf');
    const d = await r.json();
    if(d.success) toast(d.message, 'ok');
    else toast(d.error || 'ارتباط با ورکر برقرار نشد', 'err');
  } catch(e) { toast('خطا در برقراری ارتباط', 'err'); }
}

async function uploadToCf() {
  toast('در حال ارسال بکاپ به تلگرام/کلودفلر...', 'info');
  try {
    const r = await authF('/api/cf-sync/upload', {method: 'POST'});
    if(r.ok) toast('بکاپ با موفقیت آپلود شد ✓', 'ok');
    else throw new Error();
  } catch(e) { toast('خطا در آپلود اطلاعات (تنظیمات را چک کنید)', 'err'); }
}

async function downloadFromCf() {
  toast('در حال دریافت اطلاعات از کلودفلر...', 'info');
  try {
    const r = await authF('/api/cf-sync/download', {method: 'POST'});
    if(r.ok) {
      toast('اطلاعات دریافت شد. بارگذاری مجدد...', 'ok');
      setTimeout(() => location.reload(), 1500);
    } else throw new Error();
  } catch(e) { toast('خطا در دریافت اطلاعات کلودفلر', 'err'); }
}

async function loadTgSettings() {
  try {
    const r = await authF('/api/settings/telegram');
    const d = await r.json();
    document.getElementById('tg-bot-token').value = d.bot_token || '';
    document.getElementById('tg-admin-id').value = d.admin_id || '';
  } catch(e) {}
}

async function saveTgSettings() {
  const token = document.getElementById('tg-bot-token').value.trim();
  const admin_id = document.getElementById('tg-admin-id').value.trim();
  try {
    const r = await authF('/api/settings/telegram', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ bot_token: token, admin_id: admin_id })
    });
    if (r.ok) toast('تنظیمات تلگرام ذخیره شد ✓', 'ok');
  } catch(e) { toast('خطا در ذخیره تلگرام', 'err'); }
}

async function downloadFromTg() {
  toast('در حال جستجو و دریافت بکاپ از تلگرام...', 'info');
  try {
    const r = await authF('/api/tg-sync/download', {method: 'POST'});
    if(!r.ok) {
      const d = await r.json().catch(()=>({}));
      throw new Error(d.detail || 'خطا');
    }
    toast('اطلاعات با موفقیت از تلگرام بازگردانی شد! بارگذاری مجدد...', 'ok');
    setTimeout(() => location.reload(), 1500);
  } catch(e) { 
    toast(e.message || 'خطا در دریافت از تلگرام', 'err'); 
  }
}

let savedCustomsData = [];
async function loadSavedCustoms() {
    try {
        const r = await authF('/api/customs');
        const d = await r.json();
        savedCustomsData = d.customs || [];
        renderSavedCustoms('nl');
        renderSavedCustoms('el');
    } catch(e) {}
}

function renderSavedCustoms(prefix) {
    const container = document.getElementById(`${prefix}-saved-customs`);
    if(!container) return;
    if(savedCustomsData.length === 0) {
        container.innerHTML = '<span style="font-size:10px;color:var(--t3);padding:8px">هیچ کاستومی ذخیره نشده است.</span>';
        return;
    }
    container.innerHTML = savedCustomsData.map(c => `
        <div style="background:var(--accent-d);border:1px solid var(--card-b);border-radius:10px;padding:8px 10px;cursor:pointer;flex-shrink:0;min-width:130px;position:relative;transition:.15s" onmouseover="this.style.borderColor='var(--accent)'" onmouseout="this.style.borderColor='var(--card-b)'" onclick="addCustomField('${prefix}', '${esc(c.name)}', '${esc(c.address)}', '${esc(c.host_sni)}')">
            <div style="font-weight:800;font-size:11.5px;color:var(--t1);margin-bottom:2px">${esc(c.name)}</div>
            <div style="font-size:9.5px;color:var(--t3);line-height:1.4;font-family:ui-monospace,monospace">
                ADDR: ${esc(c.address) || 'ندارد'}<br>
                SNI: ${esc(c.host_sni) || 'ندارد'}
            </div>
            <button onclick="event.stopPropagation(); deleteSavedCustom('${c.id}')" style="position:absolute;top:6px;left:6px;background:none;border:none;color:var(--red-t);cursor:pointer;padding:2px"><i class="ti ti-trash" style="font-size:13px"></i></button>
        </div>
    `).join('');
}

async function saveCustomFromRow(btn, prefix) {
    const row = btn.parentElement;
    const name = row.querySelector(`.${prefix}-c-name`).value.trim();
    const address = row.querySelector(`.${prefix}-c-addr`).value.trim();
    const host_sni = row.querySelector(`.${prefix}-c-sni`).value.trim();
    if(!name && !address && !host_sni) return toast('فیلدها خالی هستند', 'err');
    
    try {
        const r = await authF('/api/customs', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name, address, host_sni})});
        if(r.ok) {
            toast('کاستوم ذخیره شد ✓', 'ok');
            loadSavedCustoms();
        }
    } catch(e) { toast('خطا در ذخیره', 'err'); }
}

async function deleteSavedCustom(id) {
    if(!confirm('این کاستوم از لیست ذخیره‌ها حذف شود؟')) return;
    try {
        const r = await authF('/api/customs/'+id, {method: 'DELETE'});
        if(r.ok) { toast('حذف شد ✓', 'ok'); loadSavedCustoms(); }
    } catch(e) { toast('خطا در حذف', 'err'); }
}

function addCustomField(prefix, name='', address='', sni='', preSelectedSubs=[]) {
    const container = document.getElementById(`${prefix}-customs-list`);
    const div = document.createElement('div');
    div.className = 'custom-field-row';
    div.style.cssText = 'display:flex;flex-direction:column;gap:6px;background:rgba(0,0,0,0.15);padding:8px;border-radius:10px;border:1px dashed var(--card-b)';
    
    const checkedSet = new Set(preSelectedSubs);
    const subCheckboxes = allSubsList.map(s => `
        <label style="display:inline-flex;align-items:center;gap:4px;font-size:10px;color:var(--t2);cursor:pointer;padding:4px 6px;border-radius:6px;background:rgba(255,215,0,0.05)">
            <input type="checkbox" value="${esc(s.sub_id)}" class="c-sub-cb" ${checkedSet.has(s.sub_id) ? 'checked' : ''} style="accent-color:var(--accent)">
            ${esc(s.name)}
        </label>
    `).join('');

    div.innerHTML = `
        <div style="display:flex;gap:6px;align-items:center">
            <input class="fi ${prefix}-c-name" placeholder="نام (مثل: ایرانسل)" style="width:25%" value="${esc(name)}">
            <input class="fi ${prefix}-c-addr" placeholder="آدرس IP یا دامنه" style="width:35%;direction:ltr" value="${esc(address)}">
            <input class="fi ${prefix}-c-sni" placeholder="SNI" style="width:30%;direction:ltr" value="${esc(sni)}">
            <button class="btn btn-g btn-icon" style="flex-shrink:0" onclick="saveCustomFromRow(this, '${prefix}')" title="ذخیره این کاستوم"><i class="ti ti-device-floppy"></i></button>
            <button class="btn btn-d btn-icon" style="flex-shrink:0" onclick="this.parentElement.parentElement.remove()"><i class="ti ti-trash"></i></button>
        </div>
        ${allSubsList.length > 0 ? `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:2px;border-top:1px dashed rgba(255,255,255,0.1);padding-top:6px">
            <span style="font-size:9.5px;color:var(--t3);display:flex;align-items:center">افزودن به:</span>
            ${subCheckboxes}
        </div>` : ''}
    `;
    container.appendChild(div);
}

function getCustomFields(prefix) {
    const customs = [];
    document.querySelectorAll(`#${prefix}-customs-list > .custom-field-row`).forEach(row => {
        const name = row.querySelector(`.${prefix}-c-name`).value.trim();
        const addr = row.querySelector(`.${prefix}-c-addr`).value.trim();
        const sni = row.querySelector(`.${prefix}-c-sni`).value.trim();
        const sub_ids = Array.from(row.querySelectorAll('.c-sub-cb:checked')).map(cb => cb.value);
        if (name || addr || sni) customs.push({name: name || 'کاستوم', address: addr, host_sni: sni, sub_ids});
    });
    return customs;
}

function openVariations(uuid) {
    const l = allLinksList.find(x=>x.uuid===uuid);
    if(!l) return;
    const list = document.getElementById('variations-list');
    list.innerHTML = l.variations.map(v => `
        <div style="background:var(--accent-d);border:1px solid var(--card-b);padding:12px 14px;border-radius:12px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap">
            <div style="flex:1;min-width:0">
                <div style="font-weight:700;font-size:13px;color:var(--t1)">${esc(v.name)}</div>
                <div style="font-size:10px;color:var(--t3);margin-top:4px;font-family:ui-monospace,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" dir="ltr">${esc(v.link).substring(0,40)}...</div>
            </div>
            <div style="display:flex;gap:6px">
                <button class="btn btn-sm btn-p" onclick="navigator.clipboard.writeText('${esc(v.link)}').then(()=>toast('کپی شد ✓','ok'))"><i class="ti ti-copy"></i></button>
                <button class="btn btn-sm btn-o" onclick="showQR('${esc(l.label)} - ${esc(v.name)}', '${esc(v.link)}')"><i class="ti ti-qrcode"></i></button>
            </div>
        </div>
    `).join('');
    openModal('modal-variations');
}

document.addEventListener('DOMContentLoaded',async()=>{
  await checkAuth();
  document.getElementById('set-host').textContent=location.host;
  document.getElementById('sub-all-url')&&(document.getElementById('sub-all-url').textContent=location.protocol+'//'+location.host+'/sub-all');
  fetchStats();fetchDefaultVless();loadLinks();loadSubs();loadCfSyncSettings();loadTgSettings();loadSavedCustoms();loadSavedSubCustoms();
  setInterval(fetchStats,4000);
  setInterval(()=>{
    if(document.getElementById('pg-links').classList.contains('on'))loadLinks();
    if(document.getElementById('pg-subgroups').classList.contains('on'))loadSubs();
    if(document.getElementById('pg-subscriptions').classList.contains('on'))loadSubsPage();
    if(document.getElementById('pg-connections').classList.contains('on'))loadConns();
    if(document.getElementById('pg-logs').classList.contains('on'))loadActivity();
  },5000);
});
</script>
</body></html>"""

PUBLIC_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Sadra Sub</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&family=Cinzel:wght@700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{
  --bg:#060608;--bg2:#0a0a0e;--bg3:#121218;
  --card:#0c0c10;--card-b:rgba(255,215,0,0.15);--card-bh:rgba(255,215,0,0.3);
  --accent:#FFD700;--accent2:#C8900A;--accent-d:rgba(255,215,0,0.12);
  --green:#4ade80;--green-bg:rgba(74,222,128,0.1);--green-t:#4ade80;
  --red:#f87171;--red-bg:rgba(248,113,113,0.1);--red-t:#f87171;
  --amber:#F59E0B;--amber-bg:rgba(245,158,11,0.1);--amber-t:#FCD34D;
  --t1:rgba(255,255,255,0.92);--t2:rgba(255,215,0,0.7);--t3:rgba(255,255,255,0.4);
  --radius:18px;--shadow:0 12px 40px rgba(0,0,0,0.45);
  --serif:'Vazirmatn',sans-serif;
}
[data-theme="light"]{
  --bg:#f0f2f5;--bg2:#ffffff;--bg3:#e4e6eb;
  --card:#ffffff;--card-b:rgba(0,0,0,0.1);--card-bh:rgba(0,0,0,0.25);
  --accent:#DAA520;--accent2:#B8860B;--accent-d:rgba(218,165,32,0.15);
  --green:#059669;--green-bg:rgba(5,150,105,0.08);--green-t:#065F46;
  --red:#DC2626;--red-bg:rgba(220,38,38,0.08);--red-t:#991B1B;
  --t1:#111827;--t2:#4b5563;--t3:#6b7280;
}
html,body{min-height:100%;background:var(--bg);font-family:var(--serif);color:var(--t1);font-size:14px;transition:background .35s,color .35s}
.bg-fx{position:fixed;inset:0;background:radial-gradient(ellipse 70% 45% at 50% -8%,rgba(255,215,0,0.05),transparent 62%),var(--bg);z-index:0;pointer-events:none}
.grid-fx{position:fixed;inset:0;background-image:linear-gradient(rgba(255,215,0,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,215,0,0.04) 1px,transparent 1px);background-size:46px 46px;z-index:0;pointer-events:none}
.wrap{position:relative;z-index:10;max-width:800px;margin:0 auto;padding:24px 16px 64px}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:26px;gap:10px}
.brand{display:flex;align-items:center;gap:11px;min-width:0}
.brand-img{width:40px;height:40px;border-radius:50%;overflow:hidden;border:1px solid var(--card-b);box-shadow:0 0 14px rgba(255,215,0,.15);flex-shrink:0}
.brand-name{font-size:16px;font-weight:900;font-family:'Cinzel',serif;color:var(--accent);letter-spacing:1px}
.brand-sub{font-size:9.5px;color:var(--t3);font-weight:500}
.top-actions{display:flex;align-items:center;gap:6px;flex-shrink:0}
.icon-btn{width:36px;height:36px;border-radius:11px;background:var(--card);border:1px solid var(--card-b);color:var(--t2);display:flex;align-items:center;justify-content:center;font-size:16px;cursor:pointer;transition:.18s}
.icon-btn:hover{background:var(--accent-d);color:var(--accent2);border-color:var(--card-bh)}

.sub-info{background:var(--card);border:1px solid var(--card-b);border-radius:22px;padding:24px 24px 22px;margin-bottom:16px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.sub-info::before{content:'';position:absolute;top:0;right:0;width:160px;height:160px;background:radial-gradient(circle at top right,rgba(255,215,0,.1),transparent 70%);pointer-events:none}
.sub-eyebrow{font-size:10px;font-weight:700;color:var(--accent2);text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.sub-name{font-size:23px;font-weight:800;color:var(--t1);margin-bottom:6px;letter-spacing:-.02em}
.sub-desc{font-size:12.5px;color:var(--t2);line-height:1.8;margin-bottom:14px}
.sub-meta-row{font-size:10.5px;color:var(--t3);margin-bottom:14px;display:flex;align-items:center;gap:6px}
.sub-sub-box{background:var(--accent-d);border:1px solid var(--card-b);border-radius:13px;padding:12px 14px;display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.sub-sub-url{font-family:ui-monospace,monospace;font-size:10px;color:var(--accent);word-break:break-all;flex:1;min-width:140px}

.stats-bar{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:18px}
.stat-card{background:var(--card);border:1px solid var(--card-b);border-radius:16px;padding:16px 17px;transition:.2s}
.stat-card:hover{border-color:var(--card-bh);transform:translateY(-1px)}
.stat-label{font-size:9px;color:var(--t3);font-weight:700;text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px}
.stat-val{font-size:22px;font-weight:800;color:var(--t1);line-height:1;letter-spacing:-.01em}
.stat-sub{font-size:9.5px;color:var(--t3);margin-top:6px}

.copy-all-bar{display:flex;align-items:center;gap:12px;background:linear-gradient(120deg,var(--accent) 0%,var(--accent2) 100%);border-radius:18px;padding:16px 19px;margin-bottom:18px;box-shadow:0 10px 30px rgba(255,215,0,.15);flex-wrap:wrap}
.copy-all-text{flex:1;min-width:160px}
.copy-all-title{font-size:13.5px;font-weight:800;color:#000;display:flex;align-items:center;gap:6px}
.copy-all-sub{font-size:10px;color:rgba(0,0,0,.7);margin-top:3px}
.copy-all-btn{background:#000;color:var(--accent);border:none;border-radius:12px;padding:10px 19px;font-family:inherit;font-size:12.5px;font-weight:800;cursor:pointer;display:flex;align-items:center;gap:6px;transition:.18s;white-space:nowrap}
.copy-all-btn:hover{transform:translateY(-1px);box-shadow:0 6px 16px rgba(0,0,0,.3)}

.cfg-title{font-size:12px;font-weight:800;color:var(--t2);margin-bottom:13px;display:flex;align-items:center;gap:6px;text-transform:uppercase;letter-spacing:.07em}
.cfg-grid{display:grid;gap:13px}

.cfg-card{background:var(--card);border:1px solid var(--card-b);border-radius:18px;transition:all .2s;position:relative;overflow:hidden}
.cfg-card:hover{border-color:var(--card-bh);box-shadow:var(--shadow)}
.cfg-top{padding:17px 19px 15px;position:relative}
.cfg-top::after{content:'';position:absolute;top:0;right:0;width:3px;height:100%;background:var(--green)}
.cfg-card.inactive .cfg-top::after{background:var(--red)}
.cfg-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.cfg-label{font-size:14.5px;font-weight:700;color:var(--t1)}
.cfg-badges{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}
.proto-chip{font-size:9px;padding:3px 8px;border-radius:7px;font-weight:800;letter-spacing:.02em;background:var(--accent-d);color:var(--accent)}
.cfg-status{display:flex;align-items:center;gap:5px;font-size:10px;font-weight:700;padding:4px 10px;border-radius:20px;white-space:nowrap}
.cfg-status.ok{background:var(--green-bg);color:var(--green-t)}
.cfg-status.no{background:var(--red-bg);color:var(--red-t)}
.cfg-usage{margin-bottom:4px}
.ubar{height:6px;border-radius:4px;background:rgba(255,215,0,0.1);overflow:hidden;margin-bottom:5px}
.ubar-f{height:100%;border-radius:4px;transition:width .5s ease}
.utxt{font-size:10px;color:var(--t3);display:flex;justify-content:space-between}

.cfg-tear{position:relative;height:0;border-top:1.5px dashed var(--card-b);margin:0 19px}
.cfg-tear::before,.cfg-tear::after{content:'';position:absolute;top:50%;width:18px;height:18px;border-radius:50%;background:var(--bg);transform:translateY(-50%);border:1px solid var(--card-b)}
.cfg-tear::before{right:-28px}
.cfg-tear::after{left:-28px}

.cfg-bottom{padding:15px 19px 18px}
.cfg-link-toggle{width:100%;display:flex;align-items:center;justify-content:space-between;gap:10px;background:transparent;border:1px dashed var(--card-b);border-radius:11px;padding:10px 13px;cursor:pointer;font-family:inherit;color:var(--t2);font-size:11.5px;font-weight:600;transition:.15s}
.cfg-link-toggle:hover{background:var(--accent-d);border-color:var(--card-bh);color:var(--accent)}
.cfg-link-toggle .ltl{display:flex;align-items:center;gap:7px}
.cfg-vless-wrap{display:grid;grid-template-rows:0fr;transition:grid-template-rows .25s ease}
.cfg-vless-wrap.open{grid-template-rows:1fr}
.cfg-vless-inner{overflow:hidden}
.cfg-vless{background:rgba(0,0,0,.22);border:1px solid var(--card-b);border-radius:10px;padding:11px 13px;font-size:9.8px;font-family:ui-monospace,monospace;color:var(--accent);word-break:break-all;line-height:1.7;margin-top:9px;max-height:90px;overflow-y:auto}
.cfg-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:11px}
.btn{font-family:inherit;font-size:11.5px;font-weight:700;border-radius:10px;padding:8px 15px;cursor:pointer;display:inline-flex;align-items:center;gap:5px;border:none;transition:all .15s;white-space:nowrap}
.btn-p{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#000;box-shadow:0 3px 14px rgba(255,215,0,.15)}
.btn-p:hover{filter:brightness(1.1)}
.btn-g{background:var(--accent-d);color:var(--accent);border:1px solid var(--card-b)}
.btn-g:hover{background:rgba(255,215,0,.22)}

.lock-stage{display:flex;align-items:center;justify-content:center;min-height:78vh;padding:20px 0}
.lock-card{background:var(--card);border:1px solid var(--card-b);border-radius:26px;padding:0;text-align:center;max-width:380px;width:100%;box-shadow:var(--shadow);overflow:hidden;position:relative}
.lock-banner{background:linear-gradient(150deg,rgba(255,215,0,.1),transparent 70%);padding:38px 30px 26px;position:relative}
.lock-shield{width:64px;height:64px;border-radius:18px;background:var(--accent-d);border:1px solid var(--card-bh);display:flex;align-items:center;justify-content:center;margin:0 auto 18px;position:relative}
.lock-title{font-size:18px;font-weight:800;color:var(--t1)}
.lock-sub{font-size:12px;color:var(--t3);line-height:1.7}
.lock-form{padding:24px 30px 30px}
.lock-inp{width:100%;padding:13px;border-radius:13px;border:1px solid var(--card-b);background:rgba(0,0,0,.2);color:var(--t1);font-family:inherit;font-size:14px;outline:none;text-align:center;letter-spacing:.1em;transition:.18s;margin-bottom:14px}
.lock-inp:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-d)}
.lock-btn{width:100%;justify-content:center;padding:13px;font-size:13px;border-radius:13px}

.empty-state{text-align:center;padding:80px 20px;color:var(--t3)}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(40px);background:var(--card);border:1px solid var(--card-b);color:var(--t1);border-radius:12px;padding:10px 20px;font-size:12.5px;font-weight:600;opacity:0;transition:all .25s;z-index:999;pointer-events:none}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}

.qr-modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:600;align-items:center;justify-content:center;backdrop-filter:blur(4px);padding:20px}
.qr-modal.open{display:flex}
.qr-box{background:var(--card);border:1px solid var(--card-b);border-radius:22px;padding:26px;text-align:center;max-width:340px;width:100%}
.qr-img{border-radius:14px;overflow:hidden;margin-bottom:15px}
.qr-img img{width:100%;display:block;background:#fff;padding:10px;border-radius:14px}

.footer{text-align:center;padding-top:28px;font-size:10.5px;color:var(--t3)}
</style>
</head>
<body>
<div class="bg-fx"></div><div class="grid-fx"></div>
<div class="toast" id="toast"></div>
<div class="qr-modal" id="qr-modal" onclick="this.classList.remove('open')">
  <div class="qr-box" onclick="event.stopPropagation()">
    <div style="font-size:13.5px;font-weight:800;margin-bottom:16px;color:var(--t1)" id="qr-label">QR Code</div>
    <div class="qr-img"><img id="qr-img" src="" alt="QR"></div>
    <button class="btn btn-g" style="width:100%;justify-content:center" onclick="document.getElementById('qr-modal').classList.remove('open')">بستن</button>
  </div>
</div>
<div class="wrap">
  <div class="top">
    <div class="brand">
      <div class="brand-img">__LOGO_SVG__</div>
      <div><div class="brand-name">Sadra PANEL</div><div class="brand-sub">Sub Group</div></div>
    </div>
    <div class="top-actions">
      <button class="icon-btn" id="theme-toggle" onclick="toggleTheme()"><i class="ti ti-sun" id="theme-icon"></i></button>
    </div>
  </div>
  <div id="root"><div class="empty-state">در حال بارگذاری...</div></div>
  <div class="footer">Sadra v9.5 Sadra Engine</div>
</div>
<script>
const UUID_KEY='__UUID_KEY__';
let savedPw='';

let isDark=localStorage.getItem('Sadra-pub-theme')!=='light';
function applyTheme(dark){
  document.documentElement.setAttribute('data-theme',dark?'dark':'light');
  document.getElementById('theme-icon').className='ti '+(dark?'ti-sun':'ti-moon');
}
function toggleTheme(){isDark=!isDark;localStorage.setItem('Sadra-pub-theme',isDark?'dark':'light');applyTheme(isDark)}
applyTheme(isDark);

function toast(msg){
  const t=document.getElementById('toast');
  t.textContent=msg;t.className='toast show';
  setTimeout(()=>t.classList.remove('show'),2400);
}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fmtB(b){if(!b||b===0)return '0 B';if(b<1024)return b+' B';if(b<1024**2)return (b/1024).toFixed(1)+' KB';if(b<1024**3)return (b/1024**2).toFixed(2)+' MB';return (b/1024**3).toFixed(2)+' GB'}

function showQR(label,link){
  document.getElementById('qr-label').textContent=label;
  document.getElementById('qr-img').src='https://api.qrserver.com/v1/create-qr-code/?size=260x260&data='+encodeURIComponent(link);
  document.getElementById('qr-modal').classList.add('open');
}

function toggleLink(i){
  const wrap=document.getElementById('vw-'+i);
  wrap.classList.toggle('open');
}

async function loadData(pw=''){
  const r=await fetch('/api/public/sub/'+UUID_KEY+(pw?'?pw='+encodeURIComponent(pw):''));
  return r.json();
}

function renderLock(name,errMsg=''){
  document.getElementById('root').innerHTML=`
    <div class="lock-stage">
      <div class="lock-card">
        <div class="lock-banner">
          <div class="lock-shield"><i class="ti ti-shield-lock" style="color:var(--accent)"></i></div>
          <div class="lock-title">${esc(name)}</div>
          <div class="lock-sub">این گروه با رمز محافظت شده است.</div>
        </div>
        <div class="lock-form">
          <div style="color:var(--red-t);font-size:11.5px;margin-bottom:10px">${esc(errMsg)}</div>
          <input class="lock-inp" type="password" id="lock-pw" placeholder="رمز عبور" autofocus>
          <button class="btn btn-p lock-btn" onclick="submitLock()"><i class="ti ti-lock-open"></i> ورود</button>
        </div>
      </div>
    </div>
  `;
}

async function submitLock(){
  const pw=document.getElementById('lock-pw').value;
  const data=await loadData(pw);
  if(data.locked){renderLock(data.name,'رمز اشتباه است');return}
  savedPw=pw;
  renderContent(data);
}

function renderContent(d){
  const activeCount=d.links.filter(l=>l.active).length;
  const baseSubUrl = d.sub_url || (window.location.protocol + '//' + window.location.host + '/sub-group/' + UUID_KEY);
  const subUrl = baseSubUrl + (savedPw ? '?pw=' + encodeURIComponent(savedPw) : '');

  window._SadraSubUrl  = subUrl;
  window._SadraLinks   = d.links.map(l => ({vless: l.vless_link, label: l.label}));

  document.getElementById('root').innerHTML=`
    <div class="sub-info">
      <div class="sub-eyebrow"><i class="ti ti-folders"></i> دسترسی اشتراک</div>
      <div class="sub-name">${esc(d.name)}</div>
      ${d.desc ? `<div class="sub-desc">${esc(d.desc)}</div>` : ''}
      <div class="sub-sub-box">
        <span class="sub-sub-url">${esc(subUrl)}</span>
        <button class="btn btn-g" style="padding:7px 12px;font-size:10.5px" onclick="navigator.clipboard.writeText(window._SadraSubUrl).then(()=>toast('کپی شد ✓'))">کپی لینک ساب</button>
        <button class="btn btn-o" style="padding:7px 12px;font-size:10.5px" onclick="showQR('${esc(d.name)}', window._SadraSubUrl)">QR</button>
      </div>
    </div>

    <div class="copy-all-bar">
      <div class="copy-all-text">
        <div class="copy-all-title"><i class="ti ti-copy"></i> کپی همه‌ی کانفیگ‌ها</div>
      </div>
      <button class="copy-all-btn" onclick="copyAllConfigs()"><i class="ti ti-clipboard-copy"></i> کپی همه (${activeCount})</button>
    </div>

    <div class="stats-bar">
      <div class="stat-card">
        <div class="stat-label">کانفیگ‌های فعال</div>
        <div class="stat-val">${activeCount}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">اتصالات زنده</div>
        <div class="stat-val">${d.active_connections}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">کل مصرف</div>
        <div class="stat-val">${esc(d.total_used_fmt)}</div>
      </div>
    </div>

    <div class="cfg-title"><i class="ti ti-link"></i> لیست کانفیگ‌ها</div>
    <div class="cfg-grid">
      ${d.links.map((l, i) => {
        const pct = l.limit_bytes === 0 ? 0 : Math.min(100, l.used_bytes / l.limit_bytes * 100);
        const bc  = pct > 90 ? 'var(--red)' : pct > 70 ? 'var(--amber)' : 'var(--green)';
        const lim = l.limit_bytes === 0 ? '∞' : fmtB(l.limit_bytes);
        return `
          <div class="cfg-card${l.active ? '' : ' inactive'}">
            <div class="cfg-top">
              <div class="cfg-head">
                <div>
                  <div class="cfg-label">${esc(l.label)}</div>
                  <div class="cfg-badges"><span class="proto-chip">${esc(l.protocol)}</span></div>
                </div>
                <span class="cfg-status ${l.active ? 'ok' : 'no'}">${l.active ? 'فعال' : 'غیرفعال'}</span>
              </div>
              <div class="cfg-usage">
                <div class="ubar"><div class="ubar-f" style="width:${pct}%;background:${bc}"></div></div>
                <div class="utxt"><span>${esc(l.used_fmt)}</span><span>${lim}</span></div>
              </div>
            </div>
            <div class="cfg-tear"></div>
            <div class="cfg-bottom">
              <button class="cfg-link-toggle" id="vt-${i}" onclick="toggleLink(${i})">
                <span class="ltl"><i class="ti ti-eye"></i> <span>نمایش لینک اتصال</span></span>
              </button>
              <div class="cfg-vless-wrap" id="vw-${i}">
                <div class="cfg-vless-inner"><div class="cfg-vless">${esc(l.vless_link)}</div></div>
              </div>
              <div class="cfg-actions">
                <button class="btn btn-p" onclick="navigator.clipboard.writeText(window._SadraLinks[${i}].vless).then(()=>toast('کپی شد ✓'))"><i class="ti ti-copy"></i> کپی</button>
                <button class="btn btn-g" onclick="showQR(window._SadraLinks[${i}].label, window._SadraLinks[${i}].vless)"><i class="ti ti-qrcode"></i> QR</button>
              </div>
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function copyAllConfigs(){
  const text=window._SadraLinks.map(l=>l.vless).join('\n');
  navigator.clipboard.writeText(text).then(()=>toast('همه‌ی کانفیگ‌ها کپی شد ✓'));
}

async function init(){
  try{
    const data = await loadData();
    if (data.locked) { renderLock(data.name); return; }
    renderContent(data);
  } catch(e) {
    document.getElementById('root').innerHTML = '<div class="empty-state">خطا در بارگذاری</div>';
  }
}
init();
</script>
</body></html>"""

LOGIN_HTML = LOGIN_HTML.replace("__LOGO_SVG__", LOGO_SVG)
DASHBOARD_HTML = DASHBOARD_HTML.replace("__LOGO_SVG__", LOGO_SVG)
PUBLIC_HTML = PUBLIC_HTML.replace("__LOGO_SVG__", LOGO_SVG)

def get_public_page_html(uuid_key: str) -> str:
    return PUBLIC_HTML.replace("__UUID_KEY__", uuid_key)

# ==============================================================================
# CORE -- App Setup, Config, State, Auth, Helpers
# ==============================================================================

IRAN_TZ = ZoneInfo("Asia/Tehran")

app = FastAPI(title="Sadra-Sadra", docs_url=None, redoc_url=None)

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DATA_FILE = DATA_DIR / "Sadra_Sadra_state.json"
SECRET_FILE = DATA_DIR / "Sadra_Sadra_secret.key"
SAVE_LOCK = asyncio.Lock()

def _load_or_create_secret() -> str:
    env_secret = os.environ.get("SECRET_KEY")
    if env_secret:
        return env_secret
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if SECRET_FILE.exists():
            existing = SECRET_FILE.read_text(encoding="utf-8").strip()
            if existing:
                return existing
        new_secret = secrets.token_urlsafe(32)
        SECRET_FILE.write_text(new_secret, encoding="utf-8")
        return new_secret
    except Exception as e:
        logger.warning(f"Could not persist SECRET_KEY, sessions may reset on restart: {e}")
        return secrets.token_urlsafe(32)

CONFIG = {
    "port": int(os.environ.get("PORT", 8000)),
    "secret": _load_or_create_secret(),
    "host": os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost"),
}

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# فریب دادن ربات‌ها برای تمام آدرس‌های نامعتبر (404 Not Found و 405 Method Not Allowed)
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    fake_404 = "<html><head><title>404 Not Found</title></head><body bgcolor='white'><center><h1>404 Not Found</h1></center><hr><center>nginx</center></body></html>"
    return Response(content=fake_404, status_code=404, media_type="text/html")

@app.exception_handler(405)
async def custom_405_handler(request: Request, exc):
    fake_404 = "<html><head><title>404 Not Found</title></head><body bgcolor='white'><center><h1>404 Not Found</h1></center><hr><center>nginx</center></body></html>"
    return Response(content=fake_404, status_code=404, media_type="text/html")

# ── State Management ──────────────────────────────────────────────────────────
# ── Cloudflare KV Config (Smart & Dynamic) ──────────────────────────────────
CF_SYNC_CONFIG = {
    # اگر فایل تنظیمات خام باشد، از این مقادیر پیش‌فرض استفاده می‌کند
    "worker_url": os.environ.get("DEFAULT_KV_URL", "https://da-base.ali1-personal.workers.dev"),
    "token": os.environ.get("DEFAULT_KV_TOKEN", "Sadra")
}

TG_CONFIG = {
    "bot_token": "",   # توکن ربات خود را اینجا بگذارید (اختیاری، از پنل هم قابل تنظیم است)
    "admin_id": ""     # آیدی عددی تلگرام خود را اینجا بگذارید
}

async def get_cf_kv(key: str):
    url = CF_SYNC_CONFIG["worker_url"]
    token = CF_SYNC_CONFIG["token"]
    if not http_client or not url or not token: return None
    
    endpoint = f"{url.rstrip('/')}/{key}"
    try:
        resp = await http_client.get(endpoint, headers={"X-Custom-Auth": token})
        if resp.status_code == 200: return resp.text
        elif resp.status_code != 404: logger.error(f"Worker GET Error: {resp.status_code}")
    except Exception as e: logger.error(f"Worker GET Exception: {e}")
    return None

async def put_cf_kv(key: str, value: str):
    url = CF_SYNC_CONFIG["worker_url"]
    token = CF_SYNC_CONFIG["token"]
    if not http_client or not url or not token: return False
    
    endpoint = f"{url.rstrip('/')}/{key}"
    try:
        resp = await http_client.put(endpoint, content=value, headers={"X-Custom-Auth": token})
        if resp.status_code == 200: return True
        else:
            logger.error(f"Worker PUT Error: {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"Worker PUT Exception: {e}")
        return False

# ── State Management (Smart Cluster Sync) ─────────────────────────────────────
LAST_MODIFIED = "2000-01-01T00:00:00"
LAST_TS = 0.0

async def sync_with_cf(skip_structure=False, force_pull=False):
    global LAST_MODIFIED, LAST_TS, AUTH, CONFIG, CF_SYNC_CONFIG
    raw = await get_cf_kv("Sadra_Sadra_state")
    if not raw: return
    
    try:
        remote = json.loads(raw)
    except Exception as e:
        logger.error(f"Sync parse error: {e}")
        return
        
    remote_ts = remote.get("saved_ts", 0.0)
    remote_time = remote.get("saved_at", "2000-01-01T00:00:00")
    
    is_newer = False
    if remote_ts > 0 and LAST_TS > 0:
        is_newer = remote_ts > LAST_TS
    else:
        is_newer = remote_time > LAST_MODIFIED

    # قفل ایمنی: اگر سرور ما خام است (صفر یا ۱ کانفیگ دارد) اما کلودفلر پر است، همیشه کلودفلر برنده است!
    remote_link_count = len(remote.get("links", {}))
    if remote_link_count > 1 and len(LINKS) <= 1:
        force_pull = True

    async with LINKS_LOCK:
        remote_links = remote.get("links", {})
        
        # 1. همیشه مصرف ترافیک را ترکیب کن (اولویت با عدد بزرگتر)
        for uid, r_link in remote_links.items():
            if uid in LINKS:
                LINKS[uid]["used_bytes"] = max(LINKS[uid].get("used_bytes", 0), r_link.get("used_bytes", 0))
        
        # 2. در صورتی که ساختار تغییر کرده یا دستور اجباری داریم، اطلاعات جدید را بگیر
        if (is_newer or force_pull) and not skip_structure:
            for uid in list(LINKS.keys()):
                if uid not in remote_links: del LINKS[uid]
            for uid, r_link in remote_links.items():
                if uid not in LINKS: LINKS[uid] = r_link
                else:
                    for k, v in r_link.items():
                        if k != "used_bytes": LINKS[uid][k] = v
                        
            async with SUBS_LOCK:
                SUBS.clear()
                SUBS.update(remote.get("subs", {}))
                
            if "password_hash" in remote: AUTH["password_hash"] = remote["password_hash"]
            if "secret" in remote: CONFIG["secret"] = remote["secret"]
            if "tg_config" in remote:
                tg = remote["tg_config"]
                if tg.get("bot_token"): tg["bot_token"] = deobf_secret(tg["bot_token"])
                if tg.get("admin_id"): tg["admin_id"] = deobf_secret(tg["admin_id"])
                TG_CONFIG.update(tg)
            if "saved_customs" in remote:
                SAVED_CUSTOMS.clear()
                SAVED_CUSTOMS.extend(remote["saved_customs"])
            if "saved_sub_customs" in remote:
                SAVED_SUB_CUSTOMS.clear()
                SAVED_SUB_CUSTOMS.extend(remote["saved_sub_customs"])
            
            LAST_TS = remote_ts
            LAST_MODIFIED = remote_time

async def load_state():
    global LINKS, AUTH, SUBS, CONFIG, LAST_MODIFIED, LAST_TS, CF_SYNC_CONFIG
    try:
        if DATA_FILE.exists():
            async with aiofiles.open(DATA_FILE, "r", encoding="utf-8") as f:
                raw = await f.read()
                data = json.loads(raw)
                LINKS.update(data.get("links", {}))
                SUBS.update(data.get("subs", {}))
                if "password_hash" in data: AUTH["password_hash"] = data["password_hash"]
                if "secret" in data: CONFIG["secret"] = data["secret"]
                if "cf_sync" in data:
                    cf = data["cf_sync"]
                    if cf.get("token"): cf["token"] = deobf_secret(cf["token"])
                    if cf.get("worker_url"): cf["worker_url"] = deobf_secret(cf["worker_url"])
                    CF_SYNC_CONFIG.update(cf)
                if "tg_config" in data:
                    tg = data["tg_config"]
                    if tg.get("bot_token"): tg["bot_token"] = deobf_secret(tg["bot_token"])
                    if tg.get("admin_id"): tg["admin_id"] = deobf_secret(tg["admin_id"])
                    TG_CONFIG.update(tg)
                if "saved_customs" in data:
                    SAVED_CUSTOMS.clear()
                    SAVED_CUSTOMS.extend(data["saved_customs"])
                if "saved_sub_customs" in data:
                    SAVED_SUB_CUSTOMS.clear()
                    SAVED_SUB_CUSTOMS.extend(data["saved_sub_customs"])
                LAST_MODIFIED = data.get("saved_at", "2000-01-01T00:00:00")
                LAST_TS = data.get("saved_ts", 0.0)
                
        # --- Auto Migrate Old Formats ---
        for uid, l in LINKS.items():
            if "address" in l or "host_sni" in l:
                addr = l.pop("address", "")
                sni = l.pop("host_sni", "")
                if addr or sni:
                    l["customs"] = [{"name": "کاستوم قدیمی", "address": addr, "host_sni": sni}]
        for sid, s in SUBS.items():
            if "custom_domain" in s:
                cd = s.pop("custom_domain", "")
                if cd and "customs" not in s:
                    s["customs"] = [{"name": "دامنه قدیمی", "domain": cd}]
            if "custom_links" in s:
                old_customs = set(s.pop("custom_links", []))
                new_ids = []
                for uid in s.get("link_ids", []):
                    new_ids.append(f"{uid}#0" if uid in old_customs else uid)
                s["link_ids"] = new_ids
        # --------------------------------
        
        await sync_with_cf()
    except Exception as e: logger.warning(f"Could not load state: {e}")

async def save_state(mutate=False):
    global LAST_MODIFIED, LAST_TS
    async with SAVE_LOCK:
        try:
            now_ts = time.time()
            import datetime as dt
            now_str = dt.datetime.now(dt.timezone.utc).isoformat()
            
            LAST_TS = now_ts
            LAST_MODIFIED = now_str
            
            cf_copy = dict(CF_SYNC_CONFIG)
            if cf_copy.get("token"): cf_copy["token"] = obf_secret(cf_copy["token"])
            if cf_copy.get("worker_url"): cf_copy["worker_url"] = obf_secret(cf_copy["worker_url"])

            tg_copy = dict(TG_CONFIG)
            if tg_copy.get("bot_token"): tg_copy["bot_token"] = obf_secret(tg_copy["bot_token"])
            if tg_copy.get("admin_id"): tg_copy["admin_id"] = obf_secret(tg_copy["admin_id"])

            data = {
                "links": dict(LINKS),
                "subs": dict(SUBS),
                "saved_customs": SAVED_CUSTOMS,
                "saved_sub_customs": SAVED_SUB_CUSTOMS,
                "password_hash": AUTH["password_hash"],
                "secret": CONFIG["secret"],
                "cf_sync": cf_copy,
                "tg_config": tg_copy,
                "saved_ts": now_ts,
                "saved_at": now_str,
            }
            raw_data = json.dumps(data, ensure_ascii=False, indent=2)

            DATA_DIR.mkdir(parents=True, exist_ok=True)
            tmp = DATA_FILE.with_suffix(".tmp")
            async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
                await f.write(raw_data)
            tmp.replace(DATA_FILE)
        except Exception as e: logger.warning(f"Save error: {e}")

# ── In-memory state ───────────────────────────────────────────────────────────
connections: dict = {}
stats = {"total_bytes": 0, "total_requests": 0, "total_errors": 0, "start_time": time.time()}
error_logs: deque = deque(maxlen=50)
activity_logs: deque = deque(maxlen=200)
hourly_traffic: dict = defaultdict(int)
http_client: httpx.AsyncClient | None = None
LINKS: dict = {}
LINKS_LOCK = asyncio.Lock()
SUBS: dict = {}
SUBS_LOCK = asyncio.Lock()
SAVED_CUSTOMS: list = []
SAVED_SUB_CUSTOMS: list = []
XHTTP_LOCK = asyncio.Lock()
SESSIONS_LOCK = asyncio.Lock()

PROTOCOLS = ("vless-ws", "xhttp-packet-up", "xhttp-stream-up", "httpupgrade", "xhttp-reality")
DEFAULT_PROTOCOL = "vless-ws"
FINGERPRINTS = ("chrome", "firefox", "safari", "ios", "android", "edge", "360", "qq", "random", "randomized")
DEFAULT_FINGERPRINT = "chrome"
DEFAULT_ALPN_BY_PROTOCOL = {"vless-ws": "http/1.1", "httpupgrade": "http/1.1", "xhttp-packet-up": "h2,http/1.1", "xhttp-stream-up": "h2,http/1.1", "xhttp-reality": "h2,http/1.1"}
DEFAULT_PORT = 443
MIN_PORT, MAX_PORT = 1, 65535
DEFAULT_SPEED_LIMIT = 0

def log_activity(kind: str, message: str, level: str = "info"):
    activity_logs.append({"kind": kind, "level": level, "message": message, "time": datetime.now().isoformat()})

# ── Auth ──────────────────────────────────────────────────────────────────────
SESSION_COOKIE = "Sadra_session"
SESSION_TTL = 60 * 60 * 24 * 365

def hash_password(pw: str) -> str:
    return hashlib.sha256(f"{pw}{CONFIG['secret']}".encode()).hexdigest()

AUTH = {"password_hash": hash_password(os.environ.get("ADMIN_PASSWORD", "admin"))}
SESSIONS: dict = {}

# توابع رمزنگاری اطلاعات حساس در فایل بکاپ
def obf_secret(text: str) -> str:
    if not text or text.startswith("ENC:"): return text
    key = os.environ.get("MASTER_KEY", AUTH.get("password_hash", "SadraEngine"))
    k = hashlib.sha256(key.encode()).digest()
    b = text.encode('utf-8')
    res = bytearray(b[i] ^ k[i % len(k)] for i in range(len(b)))
    return "ENC:" + base64.urlsafe_b64encode(res).decode('utf-8')

def deobf_secret(text: str) -> str:
    if not text or not text.startswith("ENC:"): return text
    try:
        key = os.environ.get("MASTER_KEY", AUTH.get("password_hash", "SadraEngine"))
        k = hashlib.sha256(key.encode()).digest()
        b = base64.urlsafe_b64decode(text[4:])
        res = bytearray(b[i] ^ k[i % len(k)] for i in range(len(b)))
        return res.decode('utf-8')
    except:
        return text

async def create_session() -> str:
    token = secrets.token_urlsafe(32)
    async with SESSIONS_LOCK:
        SESSIONS[token] = time.time() + SESSION_TTL
    return token

async def is_valid_session(token: str | None) -> bool:
    if not token:
        return False
    async with SESSIONS_LOCK:
        exp = SESSIONS.get(token)
        if exp is None:
            return False
        if exp < time.time():
            SESSIONS.pop(token, None)
            return False
        return True

async def destroy_session(token: str | None):
    if not token:
        return
    async with SESSIONS_LOCK:
        SESSIONS.pop(token, None)

async def require_auth(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not await is_valid_session(token):
        raise HTTPException(status_code=401, detail="unauthorized")
    return token

@app.on_event("startup")
async def startup():
    global http_client
    limits = httpx.Limits(max_connections=500, max_keepalive_connections=100)
    timeout = httpx.Timeout(30.0, connect=10.0)
    http_client = httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True)
    await load_state()
    log_activity("system", "سرور Sadra-Sadra راه‌اندازی شد", "ok")

@app.on_event("shutdown")
async def shutdown():
    await save_state(mutate=True)
    if http_client:
        await http_client.aclose()

# ── Helpers & IP Detection (Sadra Advanced Logic) ─────────────────────────────
def get_host(request: Request | None = None) -> str:
    if request is not None:
        h = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if h:
            h = h.split(":")[0]
            CONFIG["host"] = h
            return h
    return os.environ.get("RAILWAY_PUBLIC_DOMAIN", CONFIG["host"])

def generate_uuid() -> str:
    h = secrets.token_hex(16)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    
def now_ir() -> datetime:
    return datetime.now(IRAN_TZ)

def client_ip(request: Request | WebSocket) -> str:
    # 1. کلودفلر (دقیق‌ترین آی‌پی در صورت استفاده از CDN)
    if cf := request.headers.get("cf-connecting-ip"):
        return cf.split(",")[0].strip()
    
    # 2. آروان‌کلود و سایر CDNها
    if true_ip := request.headers.get("true-client-ip"):
        return true_ip.split(",")[0].strip()
    
    # 3. هدر استاندارد فوروارد (اولین آی‌پی، آی‌پی واقعی کاربر است)
    if fwd := request.headers.get("x-forwarded-for"):
        ip = fwd.split(",")[0].strip()
        if ip: return ip
        
    # 4. آی‌پی واقعی ثبت شده توسط Nginx/Envoy
    if real := request.headers.get("x-real-ip"):
        return real.split(",")[0].strip()
        
    # 5. حالت بازگشتی (پیش‌فرض لوفی)
    ip = request.client.host if request.client else "نامشخص"
    # پاک کردن فرمت اضافی IPv6 در پایتون
    if ip and ip.startswith("::ffff:"):
        ip = ip.replace("::ffff:", "")
    return ip

def unique_ips_for_uuid(uuid: str) -> set:
    return {c.get("ip") for c in connections.values() if c.get("uuid") == uuid and c.get("ip")}

def is_ip_allowed(link: dict | None, uuid: str, ip: str) -> bool:
    if link is None:
        return False
    limit = int(link.get("ip_limit", 0) or 0)
    if limit <= 0:
        return True
    ips = unique_ips_for_uuid(uuid)
    if ip in ips:
        return True
    return len(ips) < limit

def is_link_expired(link: dict) -> bool:
    exp = link.get("expires_at")
    if not exp:
        return False
    try:
        return datetime.now() > datetime.fromisoformat(exp)
    except Exception:
        return False

def is_link_allowed(link: dict | None) -> bool:
    if link is None:
        return False
    if not link.get("active", True):
        return False
    if is_link_expired(link):
        return False
    lb = link.get("limit_bytes", 0)
    if lb > 0 and link.get("used_bytes", 0) >= lb:
        return False
    return True

# ── Link Generation ───────────────────────────────────────────────────────────
def generate_vless_link(
    uuid: str,
    host: str,
    remark: str = "Sadra",
    protocol: str = DEFAULT_PROTOCOL,
    fingerprint: str | None = None,
    alpn: str | None = None,
    port: int | None = None,
    custom: dict | None = None
) -> str:
    fp = (fingerprint or DEFAULT_FINGERPRINT).strip() or DEFAULT_FINGERPRINT
    alpn_val = (alpn or "").strip() or DEFAULT_ALPN_BY_PROTOCOL.get(protocol, "http/1.1")
    port_val = port or DEFAULT_PORT
    
    target_addr = host
    sni_val = host
    host_val = host

    if custom:
        if custom.get("address"): target_addr = custom["address"].strip()
        if custom.get("host_sni"):
            sni_val = custom["host_sni"].strip()
            host_val = sni_val

    if protocol == "vless-ws":
        path = f"/ws/{uuid}"
        params = {"encryption": "none", "security": "tls", "type": "ws", "host": host_val, "path": path, "sni": sni_val, "fp": fp, "alpn": alpn_val}
    elif protocol == "httpupgrade":
        path = f"/upgrade/{uuid}"
        params = {"encryption": "none", "security": "tls", "type": "httpupgrade", "host": host_val, "path": path, "sni": sni_val, "fp": fp, "alpn": alpn_val}
    elif protocol == "xhttp-reality":
        path = f"/xhttp/reality/{uuid}"
        params = {
            "encryption": "mlkem768x25519plus.native.0rtt.n1a9RbIgBybbaQwHxJ8-giS2m2sZofWP-_p66B5m9RM",
            "security": "reality",
            "type": "xhttp", "mode": "auto", "host": host_val, "path": path, "sni": sni_val, "fp": fp,
            "pbk": "Z2V6uOrJEwdR4WefmJJm03JLocLztknxETJMaQTO9DM", "sid": uuid[:8],
        }
        if alpn_val: params["alpn"] = alpn_val
    else:
        mode = protocol.replace("xhttp-", "")
        path = f"/xhttp-siz10/{mode}/{uuid}"
        params = {"encryption": "none", "security": "tls", "type": "xhttp", "mode": mode, "host": host_val, "path": path, "sni": sni_val, "fp": fp, "alpn": alpn_val}

    query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    return f"vless://{uuid}@{target_addr}:{port_val}?{query}#{quote(remark)}"

def vless_link_for_link(link: dict, uid: str, host: str, custom: dict = None) -> str:
    var_name = custom.get("name", "") if custom else ""
    remark = f"{link.get('label','')}" + (f" ({var_name})" if var_name else "")
    return generate_vless_link(
        uid, host, remark=remark,
        protocol=link.get("protocol", DEFAULT_PROTOCOL),
        fingerprint=link.get("fingerprint"), alpn=link.get("alpn"), port=link.get("port"),
        custom=custom
    )

def parse_size_to_bytes(value: float, unit: str) -> int:
    unit = unit.upper()
    if unit == "GB": return int(value * 1024 ** 3)
    if unit == "MB": return int(value * 1024 ** 2)
    if unit == "KB": return int(value * 1024)
    return int(value)

def parse_speed_to_bytes(value: float, unit: str) -> int:
    if value <= 0: return 0
    unit = (unit or "MBIT").upper()
    if unit == "MBIT": return int(value * 1024 * 1024 / 8)
    if unit == "KB": return int(value * 1024)
    if unit == "MB": return int(value * 1024 * 1024)
    return int(value)

def fmt_bytes(b: int) -> str:
    if b < 1024: return f"{b} B"
    if b < 1024**2: return f"{b/1024:.1f} KB"
    if b < 1024**3: return f"{b/1024**2:.2f} MB"
    return f"{b/1024**3:.2f} GB"

def format_sub_url(domain: str, path: str, default_host: str) -> str:
    domain = domain.strip() if domain else ""
    if not domain:
        domain = default_host
    if not domain.startswith("http://") and not domain.startswith("https://"):
        domain = "https://" + domain
    return f"{domain.rstrip('/')}{path}"

def uptime() -> str:
    secs = int(time.time() - stats["start_time"])
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

async def ensure_default_link():
    async with LINKS_LOCK:
        if not any(l.get("is_default") for l in LINKS.values()):
            uid = hashlib.sha256(f"default{CONFIG['secret']}".encode()).hexdigest()
            uid = f"{uid[:8]}-{uid[8:12]}-{uid[12:16]}-{uid[16:20]}-{uid[20:32]}"
            if uid not in LINKS:
                LINKS[uid] = {
                    "label": "لینک پیش‌فرض",
                    "limit_bytes": 0,
                    "used_bytes": 0,
                    "created_at": datetime.now().isoformat(),
                    "active": True,
                    "expires_at": None,
                    "note": "",
                    "is_default": True,
                    "sub_id": None,
                    "protocol": DEFAULT_PROTOCOL,
                    "fingerprint": DEFAULT_FINGERPRINT,
                    "alpn": "",
                    "port": DEFAULT_PORT,
                    "ip_limit": 0,
                    "speed_limit_bytes": 0,
                    "address": ""
                }
                asyncio.create_task(save_state(mutate=True))

# ── API Endpoints ─────────────────────────────────────────────────────────────
@app.post("/api/cf-sync/upload")
async def manual_cf_upload(_=Depends(require_auth)):
    import datetime as dt
    cf_copy = dict(CF_SYNC_CONFIG)
    if cf_copy.get("token"): cf_copy["token"] = obf_secret(cf_copy["token"])
    if cf_copy.get("worker_url"): cf_copy["worker_url"] = obf_secret(cf_copy["worker_url"])

    tg_copy = dict(TG_CONFIG)
    if tg_copy.get("bot_token"): tg_copy["bot_token"] = obf_secret(tg_copy["bot_token"])
    if tg_copy.get("admin_id"): tg_copy["admin_id"] = obf_secret(tg_copy["admin_id"])

    data = {
        "links": dict(LINKS),
        "subs": dict(SUBS),
        "saved_customs": SAVED_CUSTOMS,
        "saved_sub_customs": SAVED_SUB_CUSTOMS,
        "password_hash": AUTH["password_hash"],
        "secret": CONFIG["secret"],
        "cf_sync": cf_copy,
        "tg_config": tg_copy,
        "saved_ts": time.time(),
        "saved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    raw_data = json.dumps(data, ensure_ascii=False, indent=2)
    
    # 1. آپلود در کلودفلر (اگر تنظیم شده باشد)
    cf_success = False
    if CF_SYNC_CONFIG.get("worker_url") and CF_SYNC_CONFIG.get("token"):
        cf_success = await put_cf_kv("Sadra_Sadra_state", raw_data)
    
    # 2. آپلود فایل در تلگرام (اگر تنظیم شده باشد)
    tg_success = False
    tg_token = TG_CONFIG.get("bot_token")
    tg_chat = TG_CONFIG.get("admin_id")
    if tg_token and tg_chat and http_client:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendDocument"
            file_name = f"Sadra_Backup_{dt.datetime.now().strftime('%Y-%m-%d_%H-%M')}.json"
            files = {"document": (file_name, raw_data.encode('utf-8'), "application/json")}
            caption = "📦 بکاپ پنل صدرا\n\nبرای بازگردانی اطلاعات، این فایل را دوباره به همین ربات فوروارد کنید و در پنل دکمه «دریافت از تلگرام» را بزنید."
            payload = {"chat_id": tg_chat, "caption": caption}
            res = await http_client.post(url, data=payload, files=files)
            if res.status_code == 200: tg_success = True
        except Exception as e:
            logger.error(f"TG Upload Error: {e}")

    if not cf_success and not tg_success:
        raise HTTPException(status_code=500, detail="Upload failed to both CF and TG. Check settings.")
    return {"ok": True, "cf": cf_success, "tg": tg_success}

@app.post("/api/cf-sync/download")
async def manual_cf_download(_=Depends(require_auth)):
    await sync_with_cf(skip_structure=False, force_pull=True)
    await save_state(mutate=True)
    return {"ok": True}

@app.post("/api/tg-sync/download")
async def manual_tg_download(_=Depends(require_auth)):
    tg_token = TG_CONFIG.get("bot_token")
    tg_chat = TG_CONFIG.get("admin_id")
    if not tg_token or not tg_chat or not http_client:
        raise HTTPException(status_code=400, detail="تنظیمات تلگرام ناقص است")
        
    try:
        # دریافت آخرین پیام‌های ارسال شده به ربات
        url = f"https://api.telegram.org/bot{tg_token}/getUpdates"
        res = await http_client.get(url)
        updates = res.json().get("result", [])
        
        file_id = None
        # جستجو از آخر به اول برای پیدا کردن آخرین فایلی که ادمین فرستاده
        for u in reversed(updates):
            msg = u.get("message", {})
            if str(msg.get("chat", {}).get("id", "")) == str(tg_chat):
                if "document" in msg:
                    file_id = msg["document"]["file_id"]
                    break
                    
        if not file_id:
            raise HTTPException(status_code=404, detail="فایلی در ربات یافت نشد! ابتدا فایل بکاپ را به ربات ارسال کنید.")
            
        # دریافت مسیر دانلود فایل
        file_res = await http_client.get(f"https://api.telegram.org/bot{tg_token}/getFile?file_id={file_id}")
        file_path = file_res.json().get("result", {}).get("file_path")
        if not file_path: raise HTTPException(status_code=500, detail="خطا در تلگرام")
        
        # دانلود فایل
        dl_res = await http_client.get(f"https://api.telegram.org/file/bot{tg_token}/{file_path}")
        remote = json.loads(dl_res.text)
        
        # اعمال تنظیمات مشابه کلودفلر
        global LAST_TS, LAST_MODIFIED
        async with LINKS_LOCK:
            LINKS.clear()
            LINKS.update(remote.get("links", {}))
        async with SUBS_LOCK:
            SUBS.clear()
            SUBS.update(remote.get("subs", {}))
        AUTH["password_hash"] = remote.get("password_hash", AUTH["password_hash"])
        CONFIG["secret"] = remote.get("secret", CONFIG["secret"])
        if "tg_config" in remote:
            tg = remote["tg_config"]
            if tg.get("bot_token"): tg["bot_token"] = deobf_secret(tg["bot_token"])
            if tg.get("admin_id"): tg["admin_id"] = deobf_secret(tg["admin_id"])
            TG_CONFIG.update(tg)
        LAST_TS = remote.get("saved_ts", time.time())
        LAST_MODIFIED = remote.get("saved_at", "2000-01-01T00:00:00")
        
        await save_state(mutate=True)
        return {"ok": True}
    except HTTPException: raise
    except Exception as e:
        logger.error(f"TG Download Error: {e}")
        raise HTTPException(status_code=500, detail="فایل نامعتبر یا خطا در ارتباط")

@app.get("/api/settings/telegram")
async def get_tg_settings(_=Depends(require_auth)):
    return {"bot_token": TG_CONFIG.get("bot_token", ""), "admin_id": TG_CONFIG.get("admin_id", "")}

@app.post("/api/settings/telegram")
async def update_tg_settings(request: Request, _=Depends(require_auth)):
    body = await request.json()
    TG_CONFIG["bot_token"] = body.get("bot_token", "").strip()
    TG_CONFIG["admin_id"] = str(body.get("admin_id", "")).strip()
    await save_state(mutate=True)
    return {"ok": True}

@app.get("/test-cf")
async def test_cloudflare():
    url = CF_SYNC_CONFIG.get("worker_url", "").strip()
    token = CF_SYNC_CONFIG.get("token", "").strip()
    
    if not url or not token:
        return {"error": "آدرس ورکر یا توکن در تنظیمات پنل وارد نشده است."}
        
    if not url.startswith("http"):
        url = "https://" + url
        
    endpoint = f"{url.rstrip('/')}/connection_test"
    
    if not http_client:
        return {"error": "سیستم اتصال سرور لود نشده است."}
    
    try:
        put_resp = await http_client.put(endpoint, content="ok", headers={"X-Custom-Auth": token})
        if put_resp.status_code != 200:
            # این خط مچ سرور را می‌گیرد و رمز ارسالی را فاش می‌کند!
            return {"error": f"ارور 401: پنل شما دقیقاً در حال ارسال این توکن است: «{token}». آیا این توکن درست است؟"}
            
        get_resp = await http_client.get(endpoint, headers={"X-Custom-Auth": token})
        if get_resp.status_code != 200:
            return {"error": f"خطای دیتابیس (کد {get_resp.status_code}): آیا دیتابیس KV را Bind کردید؟"}
            
        return {"success": True, "message": "ارتباط با ورکر با موفقیت برقرار شد!"}
    except Exception as e:
        return {"error": f"خطای سرور شما: {str(e)}"}

@app.get("/api/customs")
async def get_customs(_=Depends(require_auth)):
    return {"customs": SAVED_CUSTOMS}

@app.post("/api/customs")
async def add_custom(request: Request, _=Depends(require_auth)):
    body = await request.json()
    new_id = secrets.token_hex(4)
    SAVED_CUSTOMS.append({
        "id": new_id,
        "name": (body.get("name") or "کاستوم").strip(),
        "address": (body.get("address") or "").strip(),
        "host_sni": (body.get("host_sni") or "").strip()
    })
    asyncio.create_task(save_state(mutate=True))
    return {"ok": True, "id": new_id}

@app.delete("/api/customs/{cid}")
async def del_custom(cid: str, _=Depends(require_auth)):
    global SAVED_CUSTOMS
    SAVED_CUSTOMS = [c for c in SAVED_CUSTOMS if c.get("id") != cid]
    asyncio.create_task(save_state(mutate=True))
    return {"ok": True}

@app.get("/api/sub-customs")
async def get_sub_customs(_=Depends(require_auth)):
    return {"customs": SAVED_SUB_CUSTOMS}

@app.post("/api/sub-customs")
async def add_sub_custom(request: Request, _=Depends(require_auth)):
    body = await request.json()
    new_id = secrets.token_hex(4)
    SAVED_SUB_CUSTOMS.append({
        "id": new_id,
        "name": (body.get("name") or "کاستوم").strip(),
        "domain": (body.get("domain") or "").strip()
    })
    asyncio.create_task(save_state(mutate=True))
    return {"ok": True, "id": new_id}

@app.delete("/api/sub-customs/{cid}")
async def del_sub_custom(cid: str, _=Depends(require_auth)):
    global SAVED_SUB_CUSTOMS
    SAVED_SUB_CUSTOMS = [c for c in SAVED_SUB_CUSTOMS if c.get("id") != cid]
    asyncio.create_task(save_state(mutate=True))
    return {"ok": True}

@app.get("/api/settings/cf-sync")
async def get_cf_sync_settings(_=Depends(require_auth)):
    return {
        "worker_url": CF_SYNC_CONFIG.get("worker_url", ""),
        "has_token": bool(CF_SYNC_CONFIG.get("token", ""))
    }

@app.post("/api/settings/cf-sync")
async def update_cf_sync_settings(request: Request, _=Depends(require_auth)):
    body = await request.json()
    CF_SYNC_CONFIG["worker_url"] = body.get("worker_url", "").strip()
    if body.get("token"):
        CF_SYNC_CONFIG["token"] = body.get("token", "").strip()
    
    await save_state(mutate=True)
    return {"ok": True}

@app.get("/")
async def root():
    # صفحه فیک خطای ۴۰۴ برای فریب دادن ربات‌های فیلترینگ
    fake_404 = "<html><head><title>404 Not Found</title></head><body bgcolor='white'><center><h1>404 Not Found</h1></center><hr><center>nginx</center></body></html>"
    return Response(content=fake_404, status_code=404, media_type="text/html")

@app.post("/api/login")
async def api_login(request: Request):
    body = await request.json()
    ip = client_ip(request)
    if hash_password(str(body.get("password", ""))) != AUTH["password_hash"]:
        log_activity("auth", f"تلاش ورود ناموفق از {ip}", "err")
        raise HTTPException(status_code=401, detail="رمز عبور اشتباه است")
    token = await create_session()
    log_activity("auth", f"ورود موفق به پنل از {ip}", "ok")
    resp = JSONResponse({"ok": True})
    resp.set_cookie(SESSION_COOKIE, token, max_age=SESSION_TTL, httponly=True, samesite="lax", path="/")
    return resp

@app.post("/api/logout")
async def api_logout(request: Request):
    await destroy_session(request.cookies.get(SESSION_COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp

@app.get("/api/me")
async def api_me(request: Request):
    return {"authenticated": await is_valid_session(request.cookies.get(SESSION_COOKIE))}

@app.post("/api/change-password")
async def api_change_password(request: Request, token=Depends(require_auth)):
    body = await request.json()
    if hash_password(str(body.get("current_password", ""))) != AUTH["password_hash"]:
        raise HTTPException(status_code=400, detail="رمز فعلی اشتباه است")
    new = str(body.get("new_password", ""))
    if len(new) < 4:
        raise HTTPException(status_code=400, detail="رمز جدید حداقل ۴ کاراکتر باشد")
    AUTH["password_hash"] = hash_password(new)
    async with SESSIONS_LOCK:
        SESSIONS.clear()
        SESSIONS[token] = time.time() + SESSION_TTL
    await save_state(mutate=True)
    log_activity("auth", "رمز عبور پنل تغییر کرد", "ok")
    return {"ok": True}

@app.get("/stats")
async def get_stats(_=Depends(require_auth)):
    async with LINKS_LOCK:
        snap = dict(LINKS)
    return {
        "active_connections": len(connections),
        "total_traffic_mb": round(stats["total_bytes"] / (1024 ** 2), 2),
        "total_requests": stats["total_requests"],
        "total_errors": stats["total_errors"],
        "uptime": uptime(),
        "timestamp": datetime.now().isoformat(),
        "hourly": dict(hourly_traffic),
        "recent_errors": list(error_logs)[-10:],
        "links_count": len(snap),
        "active_links": sum(1 for l in snap.values() if is_link_allowed(l)),
        "expired_links": sum(1 for l in snap.values() if is_link_expired(l)),
        "subs_count": len(SUBS),
    }

@app.get("/api/activity")
async def get_activity(_=Depends(require_auth)):
    return {"logs": list(activity_logs)[-150:]}

@app.get("/api/connections")
async def get_connections(_=Depends(require_auth)):
    async with LINKS_LOCK:
        snap = dict(LINKS)
    grouped: dict[str, dict] = {}
    for conn_id, c in connections.items():
        ip = c.get("ip", "نامشخص")
        link = snap.get(c.get("uuid"))
        label = link.get("label") if link else "نامشخص"
        g = grouped.get(ip)
        if g is None:
            g = {"ip": ip, "sessions": 0, "bytes": 0, "labels": set(), "transports": set(), "first_connected_at": c.get("connected_at"), "last_connected_at": c.get("connected_at")}
            grouped[ip] = g
        g["sessions"] += 1
        g["bytes"] += c.get("bytes", 0)
        g["labels"].add(label)
        g["transports"].add(c.get("transport", "vless-ws"))
    result = []
    for ip, g in grouped.items():
        result.append({
            "ip": ip, "sessions": g["sessions"], "labels": sorted(g["labels"]),
            "label": " · ".join(sorted(g["labels"])) if g["labels"] else "نامشخص",
            "transports": sorted(g["transports"]), "bytes": g["bytes"], "bytes_fmt": fmt_bytes(g["bytes"]),
            "connected_at": g["first_connected_at"], "last_connected_at": g["last_connected_at"],
        })
    result.sort(key=lambda x: x.get("last_connected_at") or "", reverse=True)
    return {"connections": result, "count": len(result), "raw_count": len(connections)}

# ── Link Endpoints ────────────────────────────────────────────────────────────
@app.post("/api/links")
async def create_link(request: Request, _=Depends(require_auth)):
    body = await request.json()
    lv, lu = float(body.get("limit_value") or 0), body.get("limit_unit") or "GB"
    limit_bytes = 0 if lv <= 0 else parse_size_to_bytes(lv, lu)
    exp_days = int(body.get("expires_days") or 0)
    expires_at = (datetime.now() + timedelta(days=exp_days)).isoformat() if exp_days > 0 else None
    
    port = int(body.get("port") or DEFAULT_PORT)
    ip_limit = int(body.get("ip_limit") or 0)
    sv, su = float(body.get("speed_limit_value") or 0), body.get("speed_limit_unit") or "MBIT"
    speed_limit_bytes = 0 if sv <= 0 else parse_speed_to_bytes(sv, su)
    protocol = body.get("protocol") or DEFAULT_PROTOCOL
    fingerprint = (body.get("fingerprint") or DEFAULT_FINGERPRINT).strip().lower()
    custom_domain = (body.get("custom_domain") or "").strip()
    
    uid = generate_uuid()
    async with LINKS_LOCK:
        LINKS[uid] = {
            "label": (body.get("label") or "لینک جدید").strip()[:60],
            "limit_bytes": limit_bytes, "used_bytes": 0, "created_at": datetime.now().isoformat(),
            "active": True, "expires_at": expires_at, "note": (body.get("note") or "").strip()[:200],
            "protocol": protocol, "fingerprint": fingerprint, "alpn": (body.get("alpn") or "").strip()[:100],
            "port": port, "ip_limit": ip_limit, "speed_limit_bytes": speed_limit_bytes,
            "customs": body.get("customs", []), "custom_domain": custom_domain
        }
    sub_ids = body.get("sub_ids", [])
    customs = body.get("customs", [])
    
    clean_customs = [{"name": c.get("name",""), "address": c.get("address",""), "host_sni": c.get("host_sni","")} for c in customs]
    LINKS[uid]["customs"] = clean_customs
    
    async with SUBS_LOCK:
        for sid in sub_ids:
            if sid in SUBS and uid not in SUBS[sid].get("link_ids", []):
                SUBS[sid]["link_ids"].append(uid)
        
        for idx, c in enumerate(customs):
            c_sub_ids = c.get("sub_ids", [])
            uid_idx = f"{uid}#{idx}"
            for sid in c_sub_ids:
                if sid in SUBS and uid_idx not in SUBS[sid].get("link_ids", []):
                    SUBS[sid]["link_ids"].append(uid_idx)
                
    asyncio.create_task(save_state(mutate=True))
    log_activity("link", f"کانفیگ «{LINKS[uid]['label']}» ساخته شد", "ok")
    return {"uuid": uid, **LINKS[uid]}

@app.get("/api/links")
async def list_links(request: Request, _=Depends(require_auth)):
    host = get_host(request)
    async with LINKS_LOCK: snap = dict(LINKS)
    async with SUBS_LOCK: subs_snap = dict(SUBS)
    result = []
    for uid, d in snap.items():
        belong_subs = []
        var_subs = {"default": []}
        for sid, s in subs_snap.items():
            found = False
            for lid in s.get("link_ids", []):
                if lid == uid:
                    var_subs["default"].append(sid)
                    found = True
                elif lid.startswith(uid + "#"):
                    idx = lid.split("#")[1]
                    var_subs.setdefault(idx, []).append(sid)
                    found = True
            if found:
                belong_subs.append(sid)
        
        variations = [{"id": uid, "name": "پیش‌فرض (Default)", "link": vless_link_for_link(d, uid, host)}]
        for i, c in enumerate(d.get("customs", [])):
            variations.append({"id": f"{uid}#{i}", "name": c.get("name", f"Custom {i+1}"), "link": vless_link_for_link(d, uid, host, c)})
            
        result.append({
            "uuid": uid, **d, "sub_ids": belong_subs, "var_subs": var_subs, "expired": is_link_expired(d),
            "variations": variations, "sub_url": format_sub_url(d.get("custom_domain"), f"/sub/{uid}", host),
            "connected_ips": len(unique_ips_for_uuid(uid)),
        })
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return {"links": result}

@app.patch("/api/links/{uid}")
async def update_link(uid: str, request: Request, _=Depends(require_auth)):
    body = await request.json()
    async with LINKS_LOCK:
        if uid not in LINKS: raise HTTPException(status_code=404, detail="link not found")
        link = LINKS[uid]
        if "active" in body: link["active"] = bool(body["active"])
        if "label" in body: link["label"] = str(body["label"])[:60]
        if "note" in body: link["note"] = str(body["note"])[:200]
        if "customs" in body:
            clean_customs = [{"name": c.get("name",""), "address": c.get("address",""), "host_sni": c.get("host_sni","")} for c in body["customs"]]
            link["customs"] = clean_customs
        if "custom_domain" in body: link["custom_domain"] = str(body["custom_domain"]).strip()
        if "reset_usage" in body and body["reset_usage"]: link["used_bytes"] = 0
        if "limit_value" in body:
            lv, lu = float(body.get("limit_value") or 0), body.get("limit_unit") or "GB"
            link["limit_bytes"] = 0 if lv <= 0 else parse_size_to_bytes(lv, lu)
        if "expires_days" in body:
            ed = int(body["expires_days"] or 0)
            link["expires_at"] = (datetime.now() + timedelta(days=ed)).isoformat() if ed > 0 else None
        if "fingerprint" in body: link["fingerprint"] = str(body.get("fingerprint") or DEFAULT_FINGERPRINT).strip().lower()
        if "alpn" in body: link["alpn"] = str(body.get("alpn") or "").strip()[:100]
        if "port" in body: link["port"] = int(body.get("port") or DEFAULT_PORT)
        if "ip_limit" in body: link["ip_limit"] = int(body.get("ip_limit") or 0)
        if "speed_limit_value" in body:
            sv, su = float(body.get("speed_limit_value") or 0), body.get("speed_limit_unit") or "MBIT"
            link["speed_limit_bytes"] = 0 if sv <= 0 else parse_speed_to_bytes(sv, su)
            reset_bucket(uid)
            
    if "sub_ids" in body:
        target_subs = set(body["sub_ids"])
        async with SUBS_LOCK:
            for sid, s in SUBS.items():
                if sid in target_subs and uid not in s.get("link_ids", []):
                    s["link_ids"].append(uid)
                elif sid not in target_subs and uid in s.get("link_ids", []):
                    s["link_ids"].remove(uid)

    if "customs" in body:
        async with SUBS_LOCK:
            for sid, s in SUBS.items():
                s["link_ids"] = [lid for lid in s.get("link_ids", []) if not lid.startswith(f"{uid}#")]
            
            for idx, c in enumerate(body["customs"]):
                c_sub_ids = c.get("sub_ids", [])
                uid_idx = f"{uid}#{idx}"
                for sid in c_sub_ids:
                    if sid in SUBS and uid_idx not in SUBS[sid].get("link_ids", []):
                        SUBS[sid]["link_ids"].append(uid_idx)
                        
    asyncio.create_task(save_state(mutate=True))
    return {"ok": True}

@app.delete("/api/links/{uid}")
async def delete_link(uid: str, _=Depends(require_auth)):
    async with LINKS_LOCK:
        if uid not in LINKS: raise HTTPException(status_code=404)
        label = LINKS[uid]["label"]
        del LINKS[uid]
    async with SUBS_LOCK:
        for s in SUBS.values():
            if uid in s.get("link_ids", []):
                s["link_ids"].remove(uid)
    asyncio.create_task(save_state(mutate=True))
    log_activity("link", f"کانفیگ «{label}» حذف شد", "err")
    return {"ok": True}

# ── Sub Groups API ────────────────────────────────────────────────────────────
@app.post("/api/subs")
async def create_sub(request: Request, _=Depends(require_auth)):
    body = await request.json()
    name = (body.get("name") or "گروه جدید").strip()[:60]
    desc = (body.get("desc") or "").strip()[:200]
    password = (body.get("password") or "").strip()
    customs = body.get("customs", [])
    
    sub_id = generate_uuid()
    uuid_key = secrets.token_urlsafe(16)
    async with SUBS_LOCK:
        SUBS[sub_id] = {
            "name": name, "desc": desc, 
            "password_hash": hash_password(password) if password else None, 
            "uuid_key": uuid_key, "created_at": datetime.now().isoformat(), 
            "link_ids": [], "customs": customs
        }
    asyncio.create_task(save_state(mutate=True))
    log_activity("sub", f"گروه «{name}» ساخته شد", "ok")
    return {"ok": True}

@app.get("/api/subs")
async def list_subs(request: Request, _=Depends(require_auth)):
    host = get_host(request)
    async with SUBS_LOCK: snap_subs = dict(SUBS)
    async with LINKS_LOCK: snap_links = dict(LINKS)
    result = []
    for sid, s in snap_subs.items():
        link_ids = s.get("link_ids", [])
        active_count = sum(1 for lid in link_ids if is_link_allowed(snap_links.get(lid.split("#")[0])))
        total_used = sum(snap_links[lid.split("#")[0]].get("used_bytes", 0) for lid in link_ids if lid.split("#")[0] in snap_links)
        
        uuid_key = s["uuid_key"]
        base_path = f"/sub-group/{uuid_key}"
        pub_path = f"/p/{uuid_key}"

        variations = [{"id": sid, "name": "پیش‌فرض (آی‌پی سرور)", "sub_url": format_sub_url("", base_path, host), "public_url": format_sub_url("", pub_path, host)}]
        for i, c in enumerate(s.get("customs", [])):
            variations.append({
                "id": f"{sid}#{i}",
                "name": c.get("name", f"Custom {i+1}"),
                "sub_url": format_sub_url(c.get("domain", ""), base_path, host),
                "public_url": format_sub_url(c.get("domain", ""), pub_path, host)
            })

        result.append({
            "sub_id": sid, **s, "password_hash": None, "has_password": s.get("password_hash") is not None,
            "links_count": len(link_ids), "active_count": active_count, "total_used_fmt": fmt_bytes(total_used),
            "public_url": variations[0]["public_url"], "sub_url": variations[0]["sub_url"],
            "variations": variations
        })
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return {"subs": result}

@app.patch("/api/subs/{sub_id}")
async def update_sub(sub_id: str, request: Request, _=Depends(require_auth)):
    body = await request.json()
    async with SUBS_LOCK:
        if sub_id not in SUBS: raise HTTPException(status_code=404)
        s = SUBS[sub_id]
        if "name" in body: s["name"] = str(body["name"]).strip()[:60]
        if "desc" in body: s["desc"] = str(body["desc"]).strip()[:200]
        if "customs" in body: s["customs"] = body["customs"]
        if "password" in body and str(body["password"]).strip() != "":
            s["password_hash"] = hash_password(str(body["password"]).strip())
        if body.get("remove_password"):
            s["password_hash"] = None
        if "link_ids" in body: s["link_ids"] = list(body["link_ids"])
    asyncio.create_task(save_state(mutate=True))
    return {"ok": True}

@app.delete("/api/subs/{sub_id}")
async def delete_sub(sub_id: str, _=Depends(require_auth)):
    async with SUBS_LOCK:
        if sub_id not in SUBS: raise HTTPException(status_code=404)
        name = SUBS[sub_id]["name"]
        del SUBS[sub_id]
    asyncio.create_task(save_state(mutate=True))
    log_activity("sub", f"گروه «{name}» حذف شد", "warn")
    return {"ok": True}

@app.get("/sub/{uuid}")
async def subscription_single(uuid: str, request: Request):
    async with LINKS_LOCK: link = LINKS.get(uuid)
    if not link or not is_link_allowed(link): raise HTTPException(status_code=404)
    host = get_host(request)
    
    lines = [vless_link_for_link(link, uuid, host)]
    for c in link.get("customs", []):
        lines.append(vless_link_for_link(link, uuid, host, c))
        
    raw_text = "\n".join(lines)
    if request.query_params.get("plain") == "1":
        return Response(content=raw_text, media_type="text/plain", headers={"profile-title": quote(link["label"])})
    content = base64.b64encode(raw_text.encode("utf-8")).decode("utf-8")
    return Response(content=content, media_type="text/plain", headers={"profile-title": quote(link["label"])})

@app.get("/sub-all")
async def subscription_all(request: Request, _=Depends(require_auth)):
    host = get_host(request)
    lines = []
    async with LINKS_LOCK:
        for uid, d in LINKS.items():
            if is_link_allowed(d):
                lines.append(vless_link_for_link(d, uid, host))
                for c in d.get("customs", []):
                    lines.append(vless_link_for_link(d, uid, host, c))
                    
    raw_text = "\n".join(lines)
    if request.query_params.get("plain") == "1": return Response(content=raw_text, media_type="text/plain")
    content = base64.b64encode(raw_text.encode("utf-8")).decode("utf-8")
    return Response(content=content, media_type="text/plain")

@app.get("/sub-group/{uuid_key}")
async def sub_group_subscription(uuid_key: str, request: Request):
    async with SUBS_LOCK:
        sub = next((s for s in SUBS.values() if s.get("uuid_key") == uuid_key), None)
    if not sub: raise HTTPException(status_code=404)
    if sub.get("password_hash") and hash_password(request.query_params.get("pw", "")) != sub["password_hash"]:
        raise HTTPException(status_code=403, detail="wrong password")
    host = get_host(request)
    lines = []
    async with LINKS_LOCK:
        for lid_str in sub.get("link_ids", []):
            parts = lid_str.split("#")
            uid = parts[0]
            if lk := LINKS.get(uid):
                if is_link_allowed(lk):
                    if len(parts) > 1:
                        idx = int(parts[1])
                        customs = lk.get("customs", [])
                        if idx < len(customs): lines.append(vless_link_for_link(lk, uid, host, customs[idx]))
                    else:
                        lines.append(vless_link_for_link(lk, uid, host))
    
    raw_text = "\n".join(lines)
    if request.query_params.get("plain") == "1":
        return Response(content=raw_text, media_type="text/plain", headers={"profile-title": quote(sub["name"])})
    content = base64.b64encode(raw_text.encode("utf-8")).decode("utf-8")
    return Response(content=content, media_type="text/plain", headers={"profile-title": quote(sub["name"])})

# ── Speed Limit Logic ─────────────────────────────────────────────────────────
_buckets: dict = {}
MIN_RATE = 1024
MIN_BURST = 16 * 1024

class _Bucket:
    __slots__ = ("rate", "capacity", "tokens", "last")
    def __init__(self, rate: float):
        self.rate = max(rate, MIN_RATE)
        self.capacity = max(self.rate, MIN_BURST)
        self.tokens = self.capacity
        self.last = time.monotonic()
    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last
        if elapsed > 0:
            self.last = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
    async def consume(self, n: int):
        while True:
            self._refill()
            if self.tokens >= n:
                self.tokens -= n
                return
            await asyncio.sleep(min(max((n - self.tokens) / self.rate, 0.004), 0.5))

def _get_bucket(uuid: str, rate: int) -> _Bucket:
    b = _buckets.get(uuid)
    if b is None or b.rate != max(rate, MIN_RATE):
        b = _Bucket(rate)
        _buckets[uuid] = b
    return b

async def throttle(uuid: str, nbytes: int):
    if nbytes <= 0: return
    link = LINKS.get(uuid)
    rate = int((link or {}).get("speed_limit_bytes", 0) or 0)
    if rate <= 0: return
    await _get_bucket(uuid, rate).consume(nbytes)

def reset_bucket(uuid: str): _buckets.pop(uuid, None)

# ── Speed & Traffic Optimizer ─────────────────────────────────────────────────
current_hour_str = datetime.now(IRAN_TZ).strftime("%H:00")

async def update_time_loop():
    """آپدیت زمان در پس‌زمینه (جلوگیری از محاسبه زمان به ازای هر کیلوبایت ترافیک)"""
    global current_hour_str
    while True:
        current_hour_str = datetime.now(IRAN_TZ).strftime("%H:00")
        await asyncio.sleep(60)

@app.on_event("startup")
async def start_time_loop():
    asyncio.create_task(update_time_loop())

# ── WS / Core Tunnels (Ultra Optimized) ───────────────────────────────────────
RELAY_BUF = 65536  # کاهش به 64KB برای استریم به شدت روان (جلوگیری از گیرکردن ویدیوها)

def _tune_socket(writer: asyncio.StreamWriter):
    """تنظیمات سوکت برای کاهش پینگ و جلوگیری از تاخیر بسته‌ها (TCP_NODELAY)"""
    try:
        sock = writer.transport.get_extra_info("socket")
        if sock:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass

async def parse_vless_header(chunk: bytes):
    if len(chunk) < 24: raise ValueError("chunk too small")
    pos = 17
    addon_len = chunk[pos]; pos += 1 + addon_len
    command = chunk[pos]; pos += 1
    port = int.from_bytes(chunk[pos:pos+2], "big"); pos += 2
    addr_type = chunk[pos]; pos += 1
    if addr_type == 1: address = ".".join(str(b) for b in chunk[pos:pos+4]); pos += 4
    elif addr_type == 2: dlen = chunk[pos]; pos += 1; address = chunk[pos:pos+dlen].decode("utf-8", errors="ignore"); pos += dlen
    elif addr_type == 3: ab = chunk[pos:pos+16]; pos += 16; address = ":".join(f"{ab[i]:02x}{ab[i+1]:02x}" for i in range(0, 16, 2))
    else: raise ValueError(f"unknown addr type: {addr_type}")
    return command, address, port, chunk[pos:]

async def check_and_use(uid: str, n: int) -> bool:
    link = LINKS.get(uid)
    if not link or not is_link_allowed(link): return False
    link["used_bytes"] += n
    stats["total_bytes"] += n
    hourly_traffic[current_hour_str] += n
    return True

async def relay_ws_to_tcp(ws: WebSocket, writer: asyncio.StreamWriter, conn_id: str, uid: str):
    conn_info = connections.get(conn_id)
    local_bytes = 0
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect": break
            data = msg.get("bytes") or (msg.get("text") or "").encode()
            if not data: continue
            
            size = len(data)
            local_bytes += size
            
            if local_bytes >= 262144: 
                if not await check_and_use(uid, local_bytes):
                    await ws.close(code=1008); break
                if conn_info: conn_info["bytes"] += local_bytes
                local_bytes = 0
            
            if link := LINKS.get(uid):
                rate = link.get("speed_limit_bytes", 0)
                if rate > 0: await _get_bucket(uid, rate).consume(size)
                
            stats["total_requests"] += 1
            writer.write(data)
            
            # درین کردنِ زودهنگام روی 64KB تا جریان آپلود پیوسته (Smooth) بماند
            if writer.transport.get_write_buffer_size() > 65536: 
                await writer.drain()
    except Exception: pass
    finally:
        if local_bytes > 0:
            await check_and_use(uid, local_bytes)
            if conn_info: conn_info["bytes"] += local_bytes
        try: writer.write_eof()
        except: pass

async def relay_tcp_to_ws(ws: WebSocket, reader: asyncio.StreamReader, conn_id: str, uid: str):
    first = True
    conn_info = connections.get(conn_id)
    local_bytes = 0
    try:
        while True:
            data = await reader.read(65536) # خواندن نرم و پیوسته
            if not data: break
            
            size = len(data)
            local_bytes += size
            
            if local_bytes >= 262144: 
                if not await check_and_use(uid, local_bytes):
                    await ws.close(code=1008); break
                if conn_info: conn_info["bytes"] += local_bytes
                local_bytes = 0
            
            if link := LINKS.get(uid):
                rate = link.get("speed_limit_bytes", 0)
                if rate > 0: await _get_bucket(uid, rate).consume(size)
                
            await ws.send_bytes((b"\x00\x00" + data) if first else data)
            first = False
            
            # خط جادویی: اجازه می‌دهد رویدادهای زنده نگه‌داشتنِ WebSocket نفس بکشند
            await asyncio.sleep(0)
            
    except Exception: pass
    finally:
        if local_bytes > 0:
            await check_and_use(uid, local_bytes)
            if conn_info: conn_info["bytes"] += local_bytes
    
@app.websocket("/ws/{uuid}")
@app.websocket("/upgrade/{uuid}")
async def websocket_tunnel(ws: WebSocket, uuid: str):
    await ws.accept()
    link = LINKS.get(uuid)
    if not is_link_allowed(link):
        await ws.close(code=1008); return

    ip = client_ip(ws)
    if not is_ip_allowed(link, uuid, ip):
        log_activity("connection", f"اتصال {ip} (محدودیت IP)", "warn")
        await ws.close(code=1008); return

    proto = "httpupgrade" if "upgrade" in ws.url.path else "vless-ws"
    conn_id = secrets.token_urlsafe(6)
    connections[conn_id] = {"uuid": uuid, "ip": ip, "transport": proto, "connected_at": datetime.now().isoformat(), "bytes": 0}
    writer = None

    try:
        first_msg = await asyncio.wait_for(ws.receive(), timeout=15.0)
        first_chunk = first_msg.get("bytes") or (first_msg.get("text") or "").encode()
        if not first_chunk: return
        
        command, address, port, payload = await parse_vless_header(first_chunk)
        
        await check_and_use(uuid, len(first_chunk))
        connections[conn_id]["bytes"] += len(first_chunk)
        
        reader, writer = await asyncio.wait_for(asyncio.open_connection(address, port), timeout=10.0)
        
        _tune_socket(writer)
        
        if payload:
            writer.write(payload)
            await writer.drain()

        done, pending = await asyncio.wait(
            {asyncio.create_task(relay_ws_to_tcp(ws, writer, conn_id, uuid)), asyncio.create_task(relay_tcp_to_ws(ws, reader, conn_id, uuid))},
            return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending: t.cancel()
    except Exception as exc:
        stats["total_errors"] += 1
    finally:
        if writer:
            try: writer.close()
            except: pass
        connections.pop(conn_id, None)

# ── XHTTP Core Tunnels (Ultra Optimized) ──────────────────────────────────────
router = APIRouter()
xhttp_sessions: dict = {}

async def _open_tcp_from_header(first_chunk: bytes):
    command, address, port, payload = await parse_vless_header(first_chunk)
    reader, writer = await asyncio.wait_for(asyncio.open_connection(address, port), timeout=10.0)
    _tune_socket(writer)
    if payload:
        writer.write(payload)
        await writer.drain()
    return reader, writer

async def _teardown_xhttp(session_id: str):
    async with XHTTP_LOCK: sess = xhttp_sessions.pop(session_id, None)
    if not sess: return
    sess["closed"] = True
    for t in ("uplink_task", "downlink_task"):
        if sess.get(t): sess[t].cancel()
    if sess.get("writer"):
        try: sess["writer"].close()
        except: pass
    connections.pop(sess.get("conn_id"), None)
    if sess.get("down_q"):
        try: sess["down_q"].put_nowait(None)
        except: pass

async def _pump_tcp_to_queue(session_id: str, uuid: str, reader: asyncio.StreamReader, down_q: asyncio.Queue):
    first = True
    sess = xhttp_sessions.get(session_id)
    conn_info = connections.get(sess["conn_id"]) if sess else None
    try:
        while True:
            data = await reader.read(65536) # استفاده از بافر 64KB
            if not data: break
            if not await check_and_use(uuid, len(data)): break
            
            if link := LINKS.get(uuid):
                rate = link.get("speed_limit_bytes", 0)
                if rate > 0: await _get_bucket(uuid, rate).consume(len(data))
                
            if conn_info: conn_info["bytes"] += len(data)
            await down_q.put((b"\x00\x00" + data) if first else data)
            first = False
    except Exception: pass
    finally:
        await _teardown_xhttp(session_id)

async def _get_or_create_xhttp(uuid: str, mode: str, session_id: str, ip: str) -> dict:
    async with XHTTP_LOCK:
        if session_id in xhttp_sessions: return xhttp_sessions[session_id]
        link = LINKS.get(uuid)
        if not is_ip_allowed(link, uuid, ip): raise HTTPException(status_code=403, detail="ip limit")
        conn_id = secrets.token_urlsafe(6)
        connections[conn_id] = {"uuid": uuid, "ip": ip, "connected_at": datetime.now().isoformat(), "bytes": 0, "transport": f"xhttp-{mode}"}
        sess = {"uuid": uuid, "mode": mode, "writer": None, "down_q": asyncio.Queue(maxsize=1024), "conn_id": conn_id, "closed": False, "seq_buf": {}, "next_seq": 0}
        xhttp_sessions[session_id] = sess
        return sess

def _downstream_gen(sess: dict):
    async def gen():
        try:
            while True:
                chunk = await sess["down_q"].get()
                if chunk is None: break
                yield chunk
        finally: pass
    return gen()

@router.get("/xhttp-siz10/{mode}/{uuid}/{session_id}")
@router.get("/xhttp/reality/{uuid}/{session_id}")
async def xhttp_downlink(uuid: str, session_id: str, request: Request, mode: str = "auto"):
    ip = client_ip(request)
    sess = await _get_or_create_xhttp(uuid, mode, session_id, ip)
    if sess.get("closed"): raise HTTPException(status_code=404)
    return StreamingResponse(_downstream_gen(sess), media_type="application/octet-stream")

@router.post("/xhttp-siz10/packet-up/{uuid}/{session_id}/{seq}")
async def packet_up_upload(uuid: str, session_id: str, seq: int, request: Request):
    ip = client_ip(request)
    sess = await _get_or_create_xhttp(uuid, "packet-up", session_id, ip)
    if sess.get("closed"): raise HTTPException(status_code=404)
    body = await request.body()
    if not body: return {"ok": True}
    if not await check_and_use(uuid, len(body)):
        await _teardown_xhttp(session_id)
        raise HTTPException(status_code=403)
        
    if link := LINKS.get(uuid):
        rate = link.get("speed_limit_bytes", 0)
        if rate > 0: await _get_bucket(uuid, rate).consume(len(body))
        
    connections[sess["conn_id"]]["bytes"] += len(body)

    try:
        if sess["writer"] is None:
            if seq != 0:
                sess["seq_buf"][seq] = body; return {"ok": True}
            reader, writer = await _open_tcp_from_header(body)
            sess["writer"] = writer
            sess["downlink_task"] = asyncio.create_task(_pump_tcp_to_queue(session_id, uuid, reader, sess["down_q"]))
            sess["next_seq"] = 1
            return {"ok": True}
        
        if seq == sess["next_seq"]:
            sess["writer"].write(body)
            sess["next_seq"] += 1
            while sess["next_seq"] in sess["seq_buf"]:
                sess["writer"].write(sess["seq_buf"].pop(sess["next_seq"]))
                sess["next_seq"] += 1
            await sess["writer"].drain()
        else:
            sess["seq_buf"][seq] = body
    except Exception:
        await _teardown_xhttp(session_id)
        raise HTTPException(status_code=502)
    return {"ok": True}

@router.post("/xhttp-siz10/stream-up/{uuid}/{session_id}")
@router.post("/xhttp/reality/{uuid}/{session_id}")
async def stream_up_upload(uuid: str, session_id: str, request: Request):
    mode = "reality" if "reality" in request.url.path else "stream-up"
    ip = client_ip(request)
    sess = await _get_or_create_xhttp(uuid, mode, session_id, ip)
    if sess.get("closed"): raise HTTPException(status_code=404)
    
    conn_info = connections.get(sess["conn_id"])
    try:
        async for chunk in request.stream():
            if not chunk: continue
            if not await check_and_use(uuid, len(chunk)): raise HTTPException(status_code=403)
            
            if link := LINKS.get(uuid):
                rate = link.get("speed_limit_bytes", 0)
                if rate > 0: await _get_bucket(uuid, rate).consume(len(chunk))
                
            if conn_info: conn_info["bytes"] += len(chunk)

            if sess["writer"] is None:
                reader, writer = await _open_tcp_from_header(chunk)
                sess["writer"] = writer
                sess["downlink_task"] = asyncio.create_task(_pump_tcp_to_queue(session_id, uuid, reader, sess["down_q"]))
                continue
            
            sess["writer"].write(chunk)
            if sess["writer"].transport.get_write_buffer_size() > 524288:
                await sess["writer"].drain()
    except Exception:
        await _teardown_xhttp(session_id)
        raise HTTPException(status_code=502)
    return {"ok": True}

app.include_router(router)

# ── GUI Routes ────────────────────────────────────────────────────────────────
@app.get("/p/{uuid_key}", response_class=HTMLResponse)
async def public_sub_page(uuid_key: str, request: Request):
    async with SUBS_LOCK:
        sub = next(({"sub_id": sid, **s} for sid, s in SUBS.items() if s.get("uuid_key") == uuid_key), None)
    if not sub:
        return HTMLResponse("<h2 style='font-family:sans-serif;padding:40px'>گروه پیدا نشد</h2>", status_code=404)
    return HTMLResponse(content=get_public_page_html(uuid_key))

@app.get("/api/public/sub/{uuid_key}")
async def public_sub_data(uuid_key: str, request: Request):
    async with SUBS_LOCK:
        sub_entry = next(((sid, s) for sid, s in SUBS.items() if s.get("uuid_key") == uuid_key), None)
    if not sub_entry: raise HTTPException(status_code=404)
    sub_id, sub = sub_entry

    if sub.get("password_hash") and hash_password(request.query_params.get("pw", "")) != sub["password_hash"]:
        return JSONResponse({"locked": True, "name": sub["name"]})

    host = get_host(request)
    link_ids = sub.get("link_ids", [])
    async with LINKS_LOCK: snap = dict(LINKS)

    links_out = []
    active_conns = 0
    for lid_str in link_ids:
        parts = lid_str.split("#")
        uid = parts[0]
        link = snap.get(uid)
        if not link: continue
        
        active_conns += sum(1 for c in connections.values() if c.get("uuid") == uid)
        
        custom = None
        var_name = "پیش‌فرض"
        if len(parts) > 1:
            idx = int(parts[1])
            customs = link.get("customs", [])
            if idx < len(customs):
                custom = customs[idx]
                var_name = custom.get("name", f"Custom {idx+1}")
                
        links_out.append({
            "uuid": lid_str, "label": f"{link['label']} ({var_name})", "active": is_link_allowed(link),
            "protocol": link.get("protocol", DEFAULT_PROTOCOL),
            "used_fmt": fmt_bytes(link.get("used_bytes", 0)),
            "limit_bytes": link.get("limit_bytes", 0),
            "vless_link": vless_link_for_link(link, uid, host, custom)
        })

    return {
        "locked": False, "name": sub["name"], "desc": sub.get("desc", ""),
        "sub_url": format_sub_url(sub.get("custom_domain"), f"/sub-group/{uuid_key}", host),
        "active_connections": active_conns,
        "total_used_fmt": fmt_bytes(sum(snap.get(lid_str.split("#")[0], {}).get("used_bytes", 0) for lid_str in link_ids)),
        "links": links_out,
    }

@app.get("/sadra1491388191378", response_class=HTMLResponse)
async def login_page(request: Request):
    if await is_valid_session(request.cookies.get(SESSION_COOKIE)):
        return RedirectResponse(url="/dashboard")
    return HTMLResponse(content=LOGIN_HTML)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # اگر سشن معتبر نبود، به جای ریدایرکت، وانمود میکنیم این صفحه اصلا وجود ندارد!
    if not await is_valid_session(request.cookies.get(SESSION_COOKIE)):
        fake_404 = "<html><head><title>404 Not Found</title></head><body bgcolor='white'><center><h1>404 Not Found</h1></center><hr><center>nginx</center></body></html>"
        return Response(content=fake_404, status_code=404, media_type="text/html")
        
    await ensure_default_link()
    return HTMLResponse(content=DASHBOARD_HTML)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=CONFIG["port"], log_level="info", workers=1, loop="uvloop")
