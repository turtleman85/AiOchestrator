import os
import sys
import asyncio
import json
import re
import subprocess

# Force stdout/stderr to UTF-8 to prevent UnicodeEncodeError on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import shutil
import requests
import pandas as pd
import base64
import email
import email.utils
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import contextvars
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pptx import Presentation
from pptx.util import Inches, Pt
from dotenv import load_dotenv
from google import genai

# 💡 .env 보안 파일 로드
load_dotenv()

import logging
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.args and len(record.args) >= 3 and record.args[2] != "/api/v1/orchestrate/auto/status"

logging.getLogger("uvicorn.access").addFilter(EndpointFilter())


def convert_markdown_to_html(markdown_text: str, title: str = "AI Orchestrator Report") -> str:
    lines = markdown_text.split('\n')
    html_lines = []
    
    in_code = False
    in_mermaid = False
    in_list = False
    in_table = False
    
    def replace_inline(text):
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        text = re.sub(r'\*\*(.*?)\*\*|__(.*?)__', r'<strong>\1\2</strong>', text)
        text = re.sub(r'\*(.*?)\*|_(.*?)_', r'<em>\1\2</em>', text)
        text = re.sub(r'`(.*?)`', r'<code class="px-1.5 py-0.5 rounded bg-slate-950/80 border border-slate-800/80 font-mono text-emerald-400 text-xs">\1</code>', text)
        return text

    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('```'):
            if in_code:
                if in_mermaid:
                    html_lines.append('</pre>')
                    in_mermaid = False
                else:
                    html_lines.append('</code></pre></div>')
                in_code = False
            else:
                in_code = True
                lang = stripped[3:].strip().lower()
                if lang == 'mermaid':
                    in_mermaid = True
                    html_lines.append('<pre class="mermaid bg-slate-950 border border-slate-800 rounded-xl p-6 my-4 shadow-inner flex justify-center overflow-x-auto">')
                else:
                    html_lines.append(f'<div class="relative bg-slate-950 border border-slate-800 rounded-xl p-4 my-4 shadow-inner font-mono text-xs text-slate-300 overflow-x-auto"><pre><code>')
            continue
            
        if in_code:
            if in_mermaid:
                html_lines.append(line)
            else:
                escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_lines.append(escaped_line)
            continue
            
        if stripped.startswith('|'):
            if not in_table:
                in_table = True
                html_lines.append('<div class="overflow-x-auto my-6 border border-slate-800 rounded-xl bg-slate-950/20 shadow-lg"><table class="min-w-full divide-y divide-slate-800 text-sm font-medium">')
            
            cols = [col.strip() for col in stripped.split('|')[1:-1]]
            
            if all(re.match(r'^:?-+:?$', col) for col in cols):
                continue
                
            if len(html_lines) > 0 and html_lines[-1] == '<div class="overflow-x-auto my-6 border border-slate-800 rounded-xl bg-slate-950/20 shadow-lg"><table class="min-w-full divide-y divide-slate-800 text-sm font-medium">':
                html_lines.append('<thead class="bg-slate-900/50"><tr>')
                for col in cols:
                    html_lines.append(f'<th class="px-4 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">{replace_inline(col)}</th>')
                html_lines.append('</tr></thead><tbody class="divide-y divide-slate-800">')
            else:
                html_lines.append('<tr class="hover:bg-slate-900/30 transition-colors">')
                for col in cols:
                    html_lines.append(f'<td class="px-4 py-3 text-slate-300 text-xs whitespace-nowrap">{replace_inline(col)}</td>')
                html_lines.append('</tr>')
            continue
        else:
            if in_table:
                html_lines.append('</tbody></table></div>')
                in_table = False

        if stripped.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            title_text = replace_inline(stripped[3:])
            html_lines.append(f'<h2 class="text-xl font-black text-slate-100 border-b border-slate-800 pb-2 mt-8 mb-4 tracking-tight flex items-center gap-2 drop-shadow-sm"><span class="w-1.5 h-6 bg-emerald-500 rounded-full"></span>{title_text}</h2>')
            continue
            
        if stripped.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            title_text = replace_inline(stripped[4:])
            html_lines.append(f'<h3 class="text-base font-extrabold text-emerald-400 mt-6 mb-3 tracking-tight flex items-center gap-1.5"><span class="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span>{title_text}</h3>')
            continue
            
        if stripped.startswith('#### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            title_text = replace_inline(stripped[5:])
            html_lines.append(f'<h4 class="text-sm font-bold text-slate-300 mt-4 mb-2">{title_text}</h4>')
            continue

        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                in_list = True
                html_lines.append('<ul class="list-disc pl-5 space-y-1.5 text-xs text-slate-300 font-semibold mb-4 leading-relaxed">')
            item_text = replace_inline(stripped[2:])
            html_lines.append(f'<li>{item_text}</li>')
            continue
        elif in_list and not stripped.startswith('- ') and not stripped.startswith('* ') and stripped != "":
            item_text = replace_inline(stripped)
            html_lines.append(f'<span class="block text-slate-400 mt-1">{item_text}</span>')
            continue
        elif in_list and stripped == "":
            html_lines.append('</ul>')
            in_list = False
            continue

        if stripped == '---':
            html_lines.append('<hr class="my-6 border-slate-800" />')
            continue

        if stripped == "":
            html_lines.append('<div class="h-3"></div>')
            continue

        html_lines.append(f'<p class="text-xs text-slate-300 leading-relaxed font-semibold mb-4">{replace_inline(stripped)}</p>')

    if in_code:
        if in_mermaid:
            html_lines.append('</pre>')
        else:
            html_lines.append('</code></pre></div>')
    if in_table:
        html_lines.append('</tbody></table></div>')
    if in_list:
        html_lines.append('</ul>')

    body_html = '\n'.join(html_lines)
    
    full_html = f"""<!DOCTYPE html>
<html lang="ko" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    }}
                }}
            }}
        }}
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,100..800;1,100..800&family=Outfit:wght@100..900&display=swap" rel="stylesheet">
    
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'dark',
            securityLevel: 'loose',
            themeVariables: {{
                background: '#0f172a',
                primaryColor: '#1e293b',
                primaryTextColor: '#f8fafc',
                primaryBorderColor: '#334155',
                lineColor: '#10b981',
                secondaryColor: '#020617',
                tertiaryColor: '#1e1b4b'
            }},
            flowchart: {{
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            }}
        }});
    </script>
    
    <style>
        body {{
            background: linear-gradient(135deg, #020617 0%, #0f172a 100%);
            scrollbar-width: thin;
            scrollbar-color: #334155 #0f172a;
        }}
        body::-webkit-scrollbar {{
            width: 8px;
        }}
        body::-webkit-scrollbar-track {{
            background: #0f172a;
        }}
        body::-webkit-scrollbar-thumb {{
            background-color: #334155;
            border-radius: 4px;
            border: 2px solid #0f172a;
        }}
        .glass-card {{
            background: rgba(15, 23, 42, 0.45);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }}
        .mermaid svg {{
            max-height: 400px !important;
            width: auto !important;
        }}
    </style>
</head>
<body class="text-slate-200 font-sans p-6 md:p-8 min-h-screen">
    <div class="max-w-4xl mx-auto glass-card border border-slate-800/80 rounded-2xl p-6 md:p-10 shadow-2xl">
        <header class="border-b border-slate-850 pb-6 mb-8 flex justify-between items-start">
            <div>
                <div class="text-[10px] uppercase font-bold tracking-widest text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 w-fit mb-3">
                    SYSTEM ANALYTICS REPORT
                </div>
                <h1 class="text-2xl md:text-3xl font-black text-white tracking-tight leading-none drop-shadow-md">
                    {title}
                </h1>
            </div>
            <div class="text-right font-mono text-[10px] text-slate-500">
                <div>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                <div>Format: HTML Visual Report</div>
            </div>
        </header>

        <main class="prose prose-invert max-w-none">
            {body_html}
        </main>
    </div>
</body>
</html>
"""
    return full_html

def create_pptx_from_text(markdown_text: str, filename: str) -> str:
    prs = Presentation()
    
    # Split text into slides based on markdown headings or horizontal rules
    # We will encourage the LLM to output sections like "## [Slide 1] Title"
    slides_content = re.split(r'(?m)^##\s+\[Slide|^#\s+\[Slide|^\-\-\-', markdown_text)
    
    for idx, content in enumerate(slides_content):
        content = content.strip()
        if not content:
            continue
            
        lines = content.split('\n')
        # If it was split by '## [Slide', the title might just be '1] Title'
        title_raw = lines[0].strip('# ').strip()
        if ']' in title_raw:
            title_text = title_raw.split(']', 1)[-1].strip()
        else:
            title_text = title_raw
            
        body_text = '\n'.join([line.strip() for line in lines[1:] if line.strip()]).strip()
        
        # Use Title Slide layout for the first slide, Title and Content for the rest
        layout_idx = 0 if idx == 0 else 1
        try:
            slide_layout = prs.slide_layouts[layout_idx]
        except IndexError:
            slide_layout = prs.slide_layouts[1]
            
        slide = prs.slides.add_slide(slide_layout)
        
        if slide.shapes.title:
            slide.shapes.title.text = title_text
            
        if layout_idx == 1:
            for shape in slide.placeholders:
                if shape.placeholder_format.idx == 1:
                    tf = shape.text_frame
                    tf.text = body_text
                    break
                    
    # Make sure public/reports directory exists
    os.makedirs(os.path.join(os.getcwd(), "public", "reports"), exist_ok=True)
    filepath = os.path.join(os.getcwd(), "public", "reports", filename)
    prs.save(filepath)
    return f"/reports/{filename}"

app = FastAPI(title="AI Agent Orchestrator API")
app.mount("/reports", StaticFiles(directory=os.path.join(os.getcwd(), "public", "reports")), name="reports")

# ContextVar to accumulate token usage for the current request
request_token_usage = contextvars.ContextVar("request_token_usage", default=None)

# React 프론트엔드 통신을 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- [💡 지식 자원 동적 일괄 수집 함수] ---
# 📊 토큰 예산 상한선 (1 토큰 ≈ 4글자 기준)
MAX_CHARS_PER_MD_FILE = 3000      # 마크다운 파일 1개당 최대 3,000자
MAX_CHARS_MD_TOTAL = 15000        # 마크다운 전체 합산 최대 15,000자
MAX_CHARS_DB_TOTAL = 10000        # DB 엑셀 전체 합산 최대 10,000자
MAX_CHARS_NAVI_TOTAL = 5000       # 내비게이션 엑셀 전체 최대 5,000자
MAX_DB_ROWS = 100                 # DB 엑셀 파일당 최대 100행

def get_smart_context(all_projects, log_text, db_filter=None):
    project_md_ctx = ""

    # 1. 활성화된 프로젝트 폴더 순회 및 마크다운 지침서 (.claude/skills) 자동 로드
    for proj in all_projects:
        proj_path = f"../{proj}"
        proj_has_doc = False

        # ① 최상위 글로벌 가이드 (CLAUDE.md)
        claude_path = f"{proj_path}/CLAUDE.md"
        if os.path.exists(claude_path):
            proj_has_doc = True
            with open(claude_path, "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) > MAX_CHARS_PER_MD_FILE:
                    print(f"✂️ [{proj}/CLAUDE.md] {len(content)}자 → {MAX_CHARS_PER_MD_FILE}자로 절삭")
                    content = content[:MAX_CHARS_PER_MD_FILE] + "\n...(이하 토큰 예산 초과로 절삭)..."
                project_md_ctx += f"\n[{proj} 프로젝트 글로벌 아키텍처 - CLAUDE.md]\n{content}\n"

        # ② 하위 세부 지식 가이드 (.claude/skills/) 재귀적 로드
        skills_path = f"{proj_path}/.claude/skills"
        if os.path.exists(skills_path):
            proj_has_doc = True
            for root_dir, dirs, files in os.walk(skills_path):
                for file in files:
                    if file.endswith(".md"):
                        # 전체 합산 한도 도달 시 더 이상 로드하지 않음
                        if len(project_md_ctx) >= MAX_CHARS_MD_TOTAL:
                            print(f"🛑 마크다운 전체 예산({MAX_CHARS_MD_TOTAL}자) 도달 - 이후 스킬 파일 로드 중단")
                            break
                        file_full_path = os.path.join(root_dir, file)
                        rel_path = os.path.relpath(file_full_path, skills_path).replace("\\", "/")
                        with open(file_full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if len(content) > MAX_CHARS_PER_MD_FILE:
                                print(f"✂️ [{proj}/skills/{rel_path}] {len(content)}자 → {MAX_CHARS_PER_MD_FILE}자로 절삭")
                                content = content[:MAX_CHARS_PER_MD_FILE] + "\n...(이하 토큰 예산 초과로 절삭)..."
                            project_md_ctx += f"\n[{proj} 프로젝트 세부 스킬 - {rel_path}]\n{content}\n"
                else:
                    continue  # inner loop가 정상 종료되면 외부 loop 계속 진행
                break  # inner loop가 break로 끝나면 외부 loop도 중단

        # ③ 문서가 전혀 없는 경우 소스코드 직접 스캔 (Gemini Fallback 및 기본 소스 주입용)
        if not proj_has_doc:
            src_path = f"{proj_path}/src"
            if not os.path.exists(src_path):
                src_path = proj_path
                
            for root_dir, dirs, files in os.walk(src_path):
                if 'node_modules' in dirs: dirs.remove('node_modules')
                if '.git' in dirs: dirs.remove('.git')
                if 'dist' in dirs: dirs.remove('dist')
                if 'build' in dirs: dirs.remove('build')
                if '.idea' in dirs: dirs.remove('.idea')
                
                for file in files:
                    if file.endswith((".java", ".xml", ".ts", ".tsx", ".js", ".py", ".sql", ".jsp", ".html")):
                        if len(project_md_ctx) >= MAX_CHARS_MD_TOTAL:
                            break
                        file_full_path = os.path.join(root_dir, file)
                        rel_path = os.path.relpath(file_full_path, proj_path).replace("\\", "/")
                        try:
                            with open(file_full_path, "r", encoding="utf-8") as f:
                                content = f.read()
                                if len(content) > MAX_CHARS_PER_MD_FILE:
                                    content = content[:MAX_CHARS_PER_MD_FILE] + "\n...(이하 토큰 예산 초과로 절삭)..."
                                project_md_ctx += f"\n[{proj} 소스코드 - {rel_path}]\n```\n{content}\n```\n"
                        except:
                            pass
                else:
                    continue
                break

    # 전체 마크다운 최종 캡 적용
    if len(project_md_ctx) > MAX_CHARS_MD_TOTAL:
        print(f"✂️ 마크다운 전체 합산 {len(project_md_ctx)}자 → {MAX_CHARS_MD_TOTAL}자로 최종 절삭")
        project_md_ctx = project_md_ctx[:MAX_CHARS_MD_TOTAL] + "\n...(이하 토큰 예산 초과로 절삭)..."

    # 2. 🎯 '핀포인트 DB 타겟팅' 엑셀 로드
    db_ctx = ""
    if any("db_meta" in proj for proj in all_projects) and os.path.exists("../db_meta"):
        target_db = None
        # 1순위: 자동 분석된 db_filter가 있는 경우 우선 적용
        if db_filter:
            target_db = db_filter.strip().upper()
            print(f"🎯 파이썬 서버 - 자동 할당 타겟 DB 필터링 적용: {target_db}")
        else:
            # 2순위: 사용자 프롬프트 내 수동 DB : [이름] 필터 파싱
            match = re.search(r'DB\s*:\s*([A-Za-z0-9_]+)', log_text, re.IGNORECASE)
            if match:
                target_db = match.group(1).upper()
                print(f"🎯 파이썬 서버 - 수동 타겟 DB 필터링 감지됨: {target_db}")

        for file in os.listdir("../db_meta"):
            if file.startswith("~$"): continue
            if file.endswith((".xlsx", ".xls")):

                if target_db and target_db not in file.upper():
                    continue

                # DB 전체 합산 한도 체크
                if len(db_ctx) >= MAX_CHARS_DB_TOTAL:
                    print(f"🛑 DB 엑셀 전체 예산({MAX_CHARS_DB_TOTAL}자) 도달 - 이후 파일 로드 중단")
                    break

                try:
                    df = pd.read_excel(f"../db_meta/{file}")
                    chunk = f"\n[DB Meta File: {file}]\n"
                    chunk += df.to_string(index=False, max_rows=MAX_DB_ROWS)
                    db_ctx += chunk
                except Exception as e:
                    print(f"Excel Load Error ({file}): {e}")

        # DB 전체 최종 캡 적용
        if len(db_ctx) > MAX_CHARS_DB_TOTAL:
            print(f"✂️ DB 엑셀 합산 {len(db_ctx)}자 → {MAX_CHARS_DB_TOTAL}자로 절삭")
            db_ctx = db_ctx[:MAX_CHARS_DB_TOTAL] + "\n...(이하 토큰 예산 초과로 절삭)..."

    # 3. 프론트엔드 메뉴 내비게이션 엑셀 로드
    frontend_navi_ctx = ""
    if "echo-frontend" in all_projects and os.path.exists("../echo-frontend/menuNavi"):
        navi_path = "../echo-frontend/menuNavi"
        for file in os.listdir(navi_path):
            if file.startswith("~$"): continue
            if file.endswith((".xlsx", ".xls")):
                try:
                    df = pd.read_excel(f"{navi_path}/{file}")
                    frontend_navi_ctx += f"\n[Frontend Navigation Map File: {file}]\n"
                    frontend_navi_ctx += df.to_string(index=False, max_rows=MAX_DB_ROWS)
                except Exception as e:
                    print(f"Navi Excel Load Error ({file}): {e}")

        # 내비게이션 최종 캡 적용
        if len(frontend_navi_ctx) > MAX_CHARS_NAVI_TOTAL:
            print(f"✂️ 내비게이션 엑셀 {len(frontend_navi_ctx)}자 → {MAX_CHARS_NAVI_TOTAL}자로 절삭")
            frontend_navi_ctx = frontend_navi_ctx[:MAX_CHARS_NAVI_TOTAL] + "\n...(이하 토큰 예산 초과로 절삭)..."

    total_chars = len(project_md_ctx) + len(db_ctx) + len(frontend_navi_ctx)
    print(f"📊 [토큰 예산 리포트] 마크다운: {len(project_md_ctx)}자 | DB: {len(db_ctx)}자 | 내비: {len(frontend_navi_ctx)}자 | 총합: {total_chars}자 (≈{total_chars // 4} 토큰)")
    return project_md_ctx, db_ctx, frontend_navi_ctx


# --- [🔧 엔진 매핑 상수] ---
ENGINE_MAP = {
    "Gemini-Flash": "gemini-2.5-flash",
    "Gemini-Pro": "gemini-2.5-pro",
    "Claude-CLI": "claude-cli",  # 🆕 로컬 Claude Code CLI 하네스
}

# --- [🔒 Claude CLI 동시 실행 제한 (최대 3개)] ---
CLAUDE_SEMAPHORE = asyncio.Semaphore(3)

# --- [🔒 MCP 역할별 설정 파일 경로] ---
MCP_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_ROLE_CONFIG = {
    "backend": os.path.join(MCP_CONFIG_DIR, "mcp_backend.json"),
    "frontend": os.path.join(MCP_CONFIG_DIR, "mcp_frontend.json"),
}


# --- [🚀 Claude CLI 비동기 호출 래퍼] ---
CLAUDE_TIMEOUT_SECONDS = 600  # Claude CLI 최대 대기 시간 (10분 — 대형 프로젝트 분석 대응)

def decode_output(data):
    """Windows 환경에서 cp949/utf-8/euc-kr 인코딩을 안전하게 디코딩하는 헬퍼 함수"""
    if not data:
        return ""
    for encoding in ["utf-8", "cp949", "euc-kr"]:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")

async def call_claude_cli_async(prompt, cwd=None, role="backend"):
    cmd = ["claude.cmd" if os.name == "nt" else "claude", "-p", "--output-format", "text", "--dangerously-skip-permissions"]

    # 💡 역할별 MCP 설정 파일로 필요한 서버만 로드 (7개 전부 → 1~2개)
    mcp_config_path = MCP_ROLE_CONFIG.get(role)
    if mcp_config_path and os.path.exists(mcp_config_path):
        cmd.extend(["--mcp-config", mcp_config_path])
        print(f"📋 [Claude CLI] MCP 설정: {os.path.basename(mcp_config_path)}")

    full_prompt = prompt
    work_dir = cwd or r"C:\Users\LEEJAEJUN\IdeaProjects\aiOrchestrator"

    async with CLAUDE_SEMAPHORE:
        print(f"🔵 [Claude CLI] 프로세스 시작 (cwd: {work_dir}, role: {role})")
        
        loop = asyncio.get_event_loop()
        def _run_subprocess():
            import subprocess
            return subprocess.run(
                cmd,
                input=full_prompt.encode("utf-8"),
                capture_output=True,
                cwd=work_dir,
                timeout=CLAUDE_TIMEOUT_SECONDS
            )

        try:
            proc = await loop.run_in_executor(None, _run_subprocess)
        except subprocess.TimeoutExpired:
            print(f"🔴 [Claude CLI] {CLAUDE_TIMEOUT_SECONDS}초 타임아웃 → 프로세스 강제 종료")
            raise Exception(f"Claude CLI 타임아웃 ({CLAUDE_TIMEOUT_SECONDS}초 초과)")

        if proc.returncode != 0:
            err_stdout = decode_output(proc.stdout)
            err_stderr = decode_output(proc.stderr)
            error_msg = f"stdout: {err_stdout}\nstderr: {err_stderr}"
            print(f"🔴 [Claude CLI] 에러 발생 (exit code {proc.returncode}): {error_msg[:1000]}")
            raise Exception(f"Claude CLI 에러 (exit code {proc.returncode}): {error_msg[:1000]}")

        result = decode_output(proc.stdout)
        print(f"🟢 [Claude CLI] 프로세스 완료 (결과 {len(result)}자)")

        # 💡 Claude CLI 토큰 추정치 누적 (1토큰 ≈ 3글자 기준)
        usage = request_token_usage.get()
        if usage is not None:
            estimated_prompt = len(prompt) // 3
            estimated_completion = len(result) // 3
            usage["prompt_tokens"] += estimated_prompt
            usage["completion_tokens"] += estimated_completion
            usage["total_tokens"] += (estimated_prompt + estimated_completion)
            print(f"📊 [Claude CLI Token Estimate] Prompt: {estimated_prompt} | Completion: {estimated_completion} | Total: {estimated_prompt + estimated_completion}")

        return result


# --- [🧠 에이전트별 역할 특화 프롬프트 빌더] ---
def build_agent_prompt(agent, md_ctx, db_ctx, navi_ctx, jira_info, log_text, engine_label="Gemini"):
    """에이전트의 role에 따라 전문 분야 특화 프롬프트를 생성합니다. (Gemini API용 - 컨텍스트 삽입)"""
    agent_name = agent.get("name", "에이전트")
    agent_role = agent.get("role", "backend")
    projects = agent.get("assignedProjects", [])
    agent_persona = agent.get("persona", "").strip()
    
    is_standard_role = agent_role.lower() in ["backend", "frontend", "leader"]

    common_context = f"""
    [담당 에이전트] {agent_name}
    [담당 프로젝트] {', '.join(projects)}

    [사용자 요청 사항 및 로그 데이터]
    {log_text}
    """
    
    if is_standard_role:
        common_context += f"""
    [지라 티켓 연동 정보]
    {jira_info}

    [프로젝트별 아키텍처 및 도메인 가이드 (CLAUDE.md / SKILL.md)]
    {md_ctx if md_ctx else '해당 프로젝트의 가이드 문서가 없습니다.'}
    """
    else:
        if jira_info:
            common_context += f"""
    [지라 티켓 연동 정보]
    {jira_info}
    """
            
    if agent_persona:
        return f"""
        {agent_persona}

        {common_context}
        """

    if agent_role == "frontend":
        return f"""
        당신은 GS Retail의 프론트엔드 UI/UX 전문 분석 에이전트 '{agent_name}'입니다.
        오직 당신에게 배정된 프로젝트({', '.join(projects)})만을 범위로 분석하십시오.

        🔍 [프론트엔드 전문 분석 지침]
        1. 먼저 사용자가 첨부한 화면/코드 캡처 이미지나 입력 로그를 샅샅이 분석하십시오.
        2. 특히 캡처된 소스 코드 내부에 팝업 호출 공통 함수인 'gfn_OpenWindow'나 'gfn_Dialog'가 사용된 경우, 인자로 전달되는 XML 파일명(예: 'cst::CST_CustAddrMng_P.xml')을 무조건 타겟 파일로 확정하십시오. (이 경우 엑셀 매핑 정보가 없어도 됩니다)
        3. 캡처에 명확한 파일명이 없다면, 제공된 [프론트엔드 메뉴 내비게이션 지도]에서 사용자 요청과 일치하는 SCREN_ID와 FILE_NM을 찾으십시오.
        4. 실무에서 즉시 열어볼 수 있는 마이플랫폼 XML 파일 경로와 파일명을 기술하십시오.
        5. ⚠️ **중요: 추정하거나 짐작하여 소스 경로 또는 흐름을 기재하지 마십시오.** 실제 검증되지 않은 경로나 파일명은 보고서에 아예 포함하지 말고 생략하거나 "확인 불가능"으로 처리하십시오.
        6. 당신의 분석 범위 밖(백엔드/DB/배치)은 절대 언급하지 마십시오.

        {common_context}

        [프론트엔드 메뉴 내비게이션 지도 (menuNavi)]
        {navi_ctx if navi_ctx else '내비게이션 맵 데이터가 로드되지 않았습니다.'}

        ## 출력 양식 (마크다운)
        ### 🖥️ 프론트엔드 분석 결과 ({agent_name}) - {engine_label}
        #### 관련 화면 매핑 (SCREN_ID / FILE_NM)
        #### XML 파일 경로 및 호출 흐름
        #### 공통 모듈 연동 패턴
        """
    else:  # backend (기본값)
        return f"""
        당신은 GS Retail의 백엔드/DB 전문 분석 에이전트 '{agent_name}'입니다.
        오직 당신에게 배정된 프로젝트({', '.join(projects)})만을 범위로 분석하십시오.

        🔍 [백엔드/DB 전문 분석 지침]
        1. 임의로 테이블 명을 추정하거나 지어내지 마십시오. 제공된 DB 스키마에서 '정확히 일치하는' 테이블만 제시하십시오.
        2. 컨트롤러(Controller) → 서비스(Service) → DAO/Mapper 순으로 데이터 흐름을 추적하십시오.
        3. JSP 화면 구조는 메인(_M.jsp), 상세(_D.jsp), 인클루드(.jspinclude) 관계를 추적하십시오.
        4. ⚠️ **중요: 실제 소스 코드가 제공되지 않거나 확인되지 않으면, 일반적인 로직 흐름이나 구조를 상상(Hallucination)해서 답변하지 마십시오.** 소스 코드 경로, JSP 구조, API 호출 흐름 등을 절대 추정하거나 임의로 작성하지 마십시오. 직접 명백하게 확인되지 않은 내용은 "확인된 소스 코드가 없어 분석할 수 없습니다"라고 명시하고 임의의 설명을 덧붙이지 마십시오.
        5. ⚠️ **중요:** 배정되지 않은 프로젝트나 제공되지 않은 데이터베이스 정보(ERD 포함)에 대해서는 굳이 분석하거나 언급하지 마십시오. "제공된 ERD에서 정확한 테이블을 찾을 수 없습니다"와 같은 기계적인 문구를 적지 말고, 관련 정보가 없으면 해당 항목의 작성을 생략하거나 배제하십시오.
        6. 당신의 분석 범위 밖(프론트엔드 UI/배치)은 절대 언급하지 마십시오.
        7. 💡 **만약 로그 분석 도구(OpenSearch 등)가 대시보드 바로가기 링크(URL)를 반환했다면, 분석 리포트의 맨 마지막에 반드시 해당 링크를 마크다운 형식으로 제공하십시오.**

        {common_context}

        [데이터베이스 스키마 정보]
        {db_ctx if db_ctx else '데이터베이스 스키마가 로드되지 않았습니다.'}

        ## 출력 양식 (마크다운)
        ### ⚙️ 백엔드/DB 분석 결과 ({agent_name}) - {engine_label}
        #### 주요 원인 분석 (Root Cause)
        #### Controller/Service 경로 및 로직 흐름
        #### JSP/Include 구조 (해당 시)
        #### 물리 테이블 및 가이드 SQL (해당 시)
        """


# --- [🧠 Claude CLI용 경량 프롬프트 빌더] ---
def build_claude_cli_prompt(agent, jira_info, log_text, engine_label="Claude-CLI"):
    """Claude CLI 에이전트용 경량 프롬프트. MCP가 직접 파일/DB에 접근하므로 컨텍스트 삽입 불필요."""
    agent_name = agent.get("name", "에이전트")
    agent_role = agent.get("role", "backend")
    projects = agent.get("assignedProjects", [])
    agent_persona = agent.get("persona", "").strip()

    project_paths = ", ".join([f"C:\\Users\\LEEJAEJUN\\IdeaProjects\\{p}" for p in projects if p != "db_meta"])

    if agent_persona:
        return f"""
        {agent_persona}
        
        📁 담당 프로젝트 경로: {project_paths}
        위 프로젝트의 소스코드를 filesystem MCP를 활용하여 직접 탐색하고 분석하십시오.
        
        [사용자 요청 사항 및 로그 데이터]
        {log_text}
        
        [지라 티켓 정보]
        {jira_info}
        """

    if agent_role == "frontend":
        return f"""당신은 GS Retail의 프론트엔드 UI/UX 전문 분석 에이전트 '{agent_name}'입니다.

📁 담당 프로젝트 경로: {project_paths}
위 프로젝트의 소스코드를 filesystem MCP를 활용하여 직접 탐색하고 분석하십시오.
CLAUDE.md 파일이 있다면 반드시 먼저 읽고 아키텍처를 파악하십시오.

🔍 [프론트엔드 전문 분석 지침]
1. 사용자 요청과 관련된 마이플랫폼 XML 파일을 직접 찾아 분석하십시오.
2. 'gfn_OpenWindow', 'gfn_Dialog' 등 공통 함수가 사용된 경우 호출 대상 XML을 추적하십시오.
3. menuNavi 폴더의 엑셀 파일에서 SCREN_ID / FILE_NM 매핑 정보를 확인하십시오.
4. ⚠️ **중요: 추정하거나 짐작하여 소스 경로 또는 호출 흐름을 기재하지 마십시오.** 실제 직접 파일 시스템을 탐색하여 검증하지 못한 경로나 파일명은 보고서에 절대 기재하지 말고 생략하십시오.
5. 당신의 분석 범위 밖(백엔드/DB/배치)은 절대 언급하지 마십시오.

[사용자 요청 사항 및 로그 데이터]
{log_text}

[지라 티켓 연동 정보]
{jira_info}

## 출력 양식 (마크다운)
### 🖥️ 프론트엔드 분석 결과 ({agent_name}) - {engine_label}
#### 관련 화면 매핑 (SCREN_ID / FILE_NM)
#### XML 파일 경로 및 호출 흐름
#### 공통 모듈 연동 패턴"""
    else:  # backend
        db_hint = ""
        if "db_meta" in projects:
            db_hint = "\n📊 DB 스키마 엑셀 경로: C:\\Users\\LEEJAEJUN\\IdeaProjects\\db_meta"
            db_hint += "\nDB Assistant MCP를 활용하여 실제 데이터베이스를 직접 조회할 수도 있습니다."

        return f"""당신은 GS Retail의 백엔드/DB 전문 분석 에이전트 '{agent_name}'입니다.

📁 담당 프로젝트 경로: {project_paths}{db_hint}
위 프로젝트의 소스코드를 filesystem MCP를 활용하여 직접 탐색하고 분석하십시오.
CLAUDE.md 파일이 있다면 반드시 먼저 읽고 아키텍처를 파악하십시오.

🔍 [백엔드/DB 전문 분석 지침]
1. 임의로 테이블 명을 추정하거나 지어내지 마십시오. DB 스키마 엑셀이나 DB MCP로 확인된 테이블만 제시하십시오.
2. 컨트롤러(Controller) → 서비스(Service) → DAO/Mapper 순으로 데이터 흐름을 추적하십시오.
3. JSP 화면 구조는 메인(_M.jsp), 상세(_D.jsp), 인클루드(.jspinclude) 관계를 추적하십시오.
4. ⚠️ **중요: 실제 소스 코드가 제공되지 않거나 확인되지 않으면, 일반적인 로직 흐름이나 구조를 상상(Hallucination)해서 답변하지 마십시오.** 소스 코드 경로, JSP 구조, API 호출 흐름 등을 절대 추정하거나 임의로 기재하지 마십시오. 직접 100% 명확히 찾아내지 못한 정보는 "확인된 소스 코드가 없어 분석할 수 없습니다"라고 명시하고 임의의 설명을 덧붙이지 마십시오.
5. ⚠️ **중요:** 배정되지 않은 프로젝트나 제공되지 않은 데이터베이스 정보(ERD 포함)에 대해서는 굳이 분석하거나 언급하지 마십시오. "제공된 ERD에서 정확한 테이블을 찾을 수 없습니다"와 같은 기계적인 문구를 적지 말고, 관련 정보가 없으면 해당 항목의 작성을 생략하거나 배제하십시오.
6. 당신의 분석 범위 밖(프론트엔드 UI/배치)은 절대 언급하지 마십시오.

[사용자 요청 사항 및 로그 데이터]
{log_text}

[지라 티켓 정보]
{jira_info}

## 출력 양식 (마크다운)
### ⚙️ 백엔드/DB 분석 결과 ({agent_name}) - {engine_label}
#### 주요 원인 분석 (Root Cause)
#### Controller/Service 경로 및 로직 흐름
#### JSP/Include 구조 (해당 시)
#### 물리 테이블 및 가이드 SQL (해당 시)"""


# --- [🔗 취합 프롬프트 빌더] ---
def build_synthesis_prompt(agent_results):
    """각 에이전트의 독립 분석 결과를 하나의 통합 리포트로 취합하는 프롬프트를 생성합니다."""
    results_text = ""
    for agent_name, result in agent_results:
        results_text += f"\n{'='*60}\n[{agent_name}의 독립 분석 결과]\n{'='*60}\n{result}\n"

    return f"""
    당신은 여러 전문 에이전트들의 독립 분석 결과를 통합하는 '오케스트레이터 총괄관'입니다.
    아래 각 에이전트의 분석 결과를 하나의 최종 통합 리포트로 병합하십시오.

    {results_text}

    [취합 지침]
    1. 각 에이전트의 분석 결과를 도메인별(프론트엔드/백엔드/DB/배치)로 정리하여 하나의 마크다운 리포트로 통합하십시오.
    2. 에이전트 간 데이터 흐름, 호출 관계, 혹은 처리 파이프라인의 아키텍처를 직관적인 **Mermaid.js flowchart** (예: flowchart TD / flowchart LR) 로 도식화하여 리포트 첫 머리에 반드시 포함하십시오 (코드 블록 ```mermaid ... ``` 사용).
    3. 에이전트 간 분석 결과에 모순이나 불일치가 있으면 '⚠️ 교차 검증 알림' 항목으로 지적하십시오.
    4. 중복된 내용은 한 번만 기술하되, 각 에이전트가 제공한 고유 인사이트는 보존하십시오.
    5. 추측이나 새로운 분석을 추가하지 마십시오. 에이전트들이 제공한 내용만 취합하십시오.

    ## 최종 통합 리포트 출력 양식
    ### 📊 시스템 데이터 흐름도 (Mermaid.js Flowchart)
    [여기에 ```mermaid 로 시작하는 flowchart를 작성하여 시각화해주세요]

    ### 1. 주요 원인 분석 (Root Cause)
    ### 2. 영향 범위 및 타겟 소스 경로 (Target Source)
    ### 3. 데이터베이스 영향도 (Database Meta)
    ### 4. 배치 시스템 권고사항 (Batch System Guide)
    ### ⚠️ 교차 검증 알림 (에이전트 간 모순 사항)
    """


# --- [👔 팀장 기획 프롬프트 빌더] ---
def build_leader_planning_prompt(available_agents, available_projects, jira_info, log_text):
    """팀장이 에이전트 배정 계획을 JSON으로 수립하는 프롬프트. 팀원 명단과 프로젝트 목록을 기반으로 배정."""
    agent_roster = "\n".join([
        f"- 이름: {a['name']} | 역할: {a['role']} | 엔진: {a['engine']}"
        for a in available_agents
    ])
    project_list = "\n".join([f"- ID: {p['id']} | 설명: {p['name']}" for p in available_projects])

    return f"""당신은 GS Retail AI 개발팀의 팀장입니다.
아래 팀원 목록과 프로젝트 목록을 보고, 사용자 요청을 분석하여 최적의 업무 배정 계획을 수립하세요.

[팀원 명단 (에이전트 로스터)]
{agent_roster}

[사용 가능한 프로젝트 목록]
{project_list}

[사용자 요청 및 로그]
{log_text}

[지라 티켓 정보]
{jira_info}

[지시사항]
1. 사용자 요청이 어떤 도메인(백엔드/프론트엔드/DB/배치)과 관련 있는지 분석하세요.
2. 관련 프로젝트를 파악하고, 각 팀원의 역할에 맞게 배정하세요. 불필요한 팀원은 배정하지 않아도 됩니다.
3. ⚠️ **[가장 중요]** 사용자 요청(log_text) 내에 특정 프로젝트 이름 또는 힌트(예: "안나푸르나", "마나스루", "chooyu", "고객배치", "유효기간제 배치", "member-batch", "echo-frontend" 등)가 명시적으로 언급되어 있는 경우, 해당 프로젝트를 배정 계획(`assignments` -> `projects`)에 **반드시 최우선적으로 포함**하여 담당 팀원들에게 적절히 할당하십시오. (예: "안나푸르나, 마나스루에서 확인해줘"라고 언급했다면 `annapurna`와 `manaslu` 프로젝트를 반드시 할당에 포함해야 합니다.)
4. 배정 프로젝트 목록에 "db_meta"가 포함되어 있을 경우, 사용자 요청 내용을 분석하여 가장 깊게 연관된 DB 스키마 엑셀 파일을 매핑하기 위한 "db_filter" 필드를 반드시 판별하여 기재해 주세요:
   - 고객 / 회원 / 로그인 정보와 관련된 내용인 경우: "CST"
   - 문의 / SR / 상담 / 접수 정보와 관련된 내용인 경우: "SR"
   - 자산 / 적립금 / 포인트 / 예산 정보와 관련된 내용인 경우: "AST"
   - 그 외에 구체적인 도메인이 없거나 구분이 불명확한 경우: null 또는 빈 문자열
5. 반드시 아래 JSON 형식으로만 응답하세요. JSON 외의 다른 텍스트는 포함하지 마세요.

응답 JSON 형식:
{{{{
  "reasoning": "배정 계획 수립 근거 요약 (200자 이내)",
  "analysis_focus": "이번 분석의 핵심 포인트 (100자 이내)",
  "assignments": [
    {{{{
      "agent_name": "팀원 이름 (팀원 명단의 이름과 동일하게)",
      "role": "backend 또는 frontend",
      "projects": ["프로젝트 ID 목록 (위 목록의 ID 값)"],
      "db_filter": "CST 또는 SR 또는 AST 또는 null (db_meta가 배정되었을 때 분석 내용 기반 분류)"
    }}}}
  ]
}}}}"""


# --- [👔 팀장 결과 성찰/피드백 프롬프트 빌더] ---
def build_leader_reflection_prompt(plan, agent_results, jira_info, log_text):
    """팀장이 에이전트의 1차 결과를 검토하고 피드백을 결정하는 프롬프트."""
    results_str = ""
    for name, res in agent_results:
        results_str += f"\n=== [{name} 에이전트 1차 분석 결과] ===\n{res}\n"
        
    return f"""당신은 GS Retail의 프로젝트 개발 및 분석 팀의 총괄 팀장 에이전트입니다.
아래의 [사용자 요청 및 지라 정보]와 팀장님이 수립하셨던 [업무 배정 기획], 그리고 각 팀원들이 제출한 [1차 분석 결과]를 검토하십시오.

[지라 티켓 정보]
{jira_info}

[사용자 원본 요청]
{log_text}

[팀장의 업무 배정 기획]
분석 초점: {plan.get('analysis_focus', '')}

[팀원들의 1차 분석 결과]
{results_str}

각 팀원의 분석 결과가 충분히 상세하고 정확한지, 누락된 소스 코드나 물리 테이블이 없는지 검토하십시오.
팀원의 결과물에 보완이 필요한 경우 구체적인 1~2문장의 피드백을 작성해 주십시오.

반드시 아래와 같은 순수 JSON 형식으로만 응답해 주십시오. markdown 코드 블록(```json ... ```)이나 서론, 결론 같은 텍스트는 절대 포함하지 말고 오직 JSON 자체만 출력해야 합니다.
{{
  "에이전트이름": {{
    "needs_revision": true,
    "feedback": "구체적인 피드백 내용 (예: 어떤 XML 파일 호출 부분을 더 추적해야 합니다 등)"
  }}
}}
만약 보완할 점이 없거나 분석이 완벽하다면 "needs_revision": false, "feedback": "" 로 작성하십시오.
"""


# --- [👔 팀장 검토/통합 프롬프트 빌더] ---
def build_leader_review_prompt(plan, agent_results, jira_info, log_text, generate_pt=False):
    """팀장이 에이전트 결과를 교차 검토하고 최종 통합 리포트를 작성하는 프롬프트."""
    assignments = plan.get("assignments", [])
    assignment_summary = "\n".join([
        f"- {a['agent_name']} ({a['role']}): {', '.join(a.get('projects', []))} 담당"
        for a in assignments
    ])
    results_text = ""
    for agent_name, result in agent_results:
        results_text += f"\n{'='*60}\n[{agent_name}의 분석 결과]\n{'='*60}\n{result}\n"

    if generate_pt:
        return f"""당신은 GS Retail AI 기획팀의 수석 기획자(팀장)입니다.
아래 팀원(에이전트)들의 독립 아이디어 분석 결과를 교차 검토하고, 최종 파워포인트(PT) 기획서 대본을 작성하세요.

[원본 사용자 요청]
{log_text}

[팀원 배정 현황 및 분석 결과]
{results_text}

[PT 작성 지침]
1. 각 에이전트가 제시한 의견을 종합하여 하나의 일관된 스토리라인으로 구성하십시오.
2. 결과물은 반드시 파워포인트 슬라이드 구조로 분할되어야 합니다.
3. 각 슬라이드의 시작은 반드시 `## [Slide N] 슬라이드 제목` 형태로 작성하십시오. (예: `## [Slide 1] 프로젝트 개요`)
4. 각 슬라이드의 내용은 간결한 개조식(Bullet points)으로 작성하십시오.
5. 5~10장 내외로 구성하되, 추측성 발언은 배제하고 확정된 아이디어만 담으십시오.
6. 이 결과물은 자동 파싱되어 실제 `.pptx` 파일로 생성되므로 형식을 엄격히 지켜주십시오.
"""
    else:
        return f"""당신은 GS Retail AI 개발팀의 팀장입니다.
아래 팀원들의 독립 분석 결과를 교차 검토하고, 최종 통합 리포트를 작성하세요.

[원본 사용자 요청]
{log_text}

[지라 티켓 정보]
{jira_info}

[팀장 배정 계획 요약]
- 분석 포인트: {plan.get('analysis_focus', '')}
- 배정 근거: {plan.get('reasoning', '')}

[팀원 배정 현황]
{assignment_summary}

[각 팀원 분석 결과]
{results_text}

[팀장 검토 지침]
1. 각 팀원의 분석 결과를 교차 검증하세요. 상충되거나 모순된 내용은 반드시 '⚠️ 교차 검증 알림'으로 표시하세요.
2. 시스템 데이터 흐름, 호출 관계, 혹은 처리 파이프라인의 아키텍처를 직관적인 **Mermaid.js flowchart** (예: flowchart TD / flowchart LR) 로 도식화하여 최종 리포트에 반드시 포함하십시오 (코드 블록 ```mermaid ... ``` 사용).
3. 누락된 분석 영역이 있으면 명시하세요.
4. ⚠️ **중요: 팀원(에이전트)들의 분석 결과 중 '추정', '추측', '미검증'으로 언급된 소스 코드 경로, DB 테이블, API 호출 등의 불확실한 내용은 최종 통합 리포트에서 '완전히 배제하고 삭제'하십시오.** 최종 통합 리포트는 오직 100% 실제로 탐색하여 검증된 내용만 담아야 합니다. 어떠한 형태의 추측성 발송 경로나 추정 정보도 최종 보고서에 싣지 마십시오.
5. 팀원들의 확실한 인사이트를 종합하여 최종 통합 리포트를 작성하세요. 새로운 추측은 추가하지 마세요.

## 👔 팀장 최종 통합 리포트

### 1. 팀장 배정 총평

### 📊 시스템 데이터 흐름도 (Mermaid.js Flowchart)
[여기에 ```mermaid 로 시작하는 flowchart를 작성하여 시각화해주세요]

### 2. 주요 원인 분석 (Root Cause)

### 3. 영향 범위 및 타겟 소스 경로 (Target Source)
*(실제 파일 시스템에서 직접 찾아낸 파일 경로와 연동 로직만 작성하며, 확인되지 않은 추정 경로는 절대 적지 마십시오.)*

### 4. 데이터베이스 영향도 (Database Meta)
*(DB 메타 데이터나 실제 스키마에서 확인된 확실한 테이블 정보만 작성하십시오.)*

### 5. 조치 가이드 및 권고사항

### ⚠️ 교차 검증 알림 (모순/누락 사항)"""


# --- [🚀 비동기 Gemini API 호출 래퍼] ---
async def call_gemini_async(client, model_name, prompt, base64_images=None):
    """동기 Gemini SDK 호출을 asyncio 비동기로 래핑하고, 멀티모달 이미지를 지원합니다. (503/429 오류 시 재시도 및 1.5 모델 폴백 적용)"""
    contents = [prompt]
    if base64_images:
        for b64_str in base64_images:
            if "," in b64_str:
                mime_type, b64_data = b64_str.split(",", 1)
                mime_type = mime_type.split(";")[0].split(":")[1]
            else:
                mime_type = "image/png"
                b64_data = b64_str
            image_bytes = base64.b64decode(b64_data)
            contents.append(
                genai.types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                )
            )

    loop = asyncio.get_event_loop()
    
    # 1.5 계열 LTS 폴백 모델 매핑
    FALLBACK_MAP = {
        "gemini-2.5-flash": "gemini-flash-latest",
        "gemini-2.5-pro": "gemini-pro-latest"
    }

    current_model = model_name
    use_fallback = False

    while True:
        max_retries = 3
        delay = 2.0  # 초기 대기 시간 (초)
        
        for attempt in range(max_retries + 1):
            try:
                resp = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(model=current_model, contents=contents)
                )
                if use_fallback:
                    print(f"🟢 [Gemini API] 폴백 모델({current_model}) 호출 성공!")

                # 💡 토큰 사용량 ContextVar 누적
                usage = request_token_usage.get()
                if usage is not None and hasattr(resp, 'usage_metadata') and resp.usage_metadata:
                    p_tokens = getattr(resp.usage_metadata, "prompt_token_count", 0) or 0
                    c_tokens = getattr(resp.usage_metadata, "candidates_token_count", 0) or 0
                    t_tokens = getattr(resp.usage_metadata, "total_token_count", 0) or 0
                    usage["prompt_tokens"] += p_tokens
                    usage["completion_tokens"] += c_tokens
                    usage["total_tokens"] += t_tokens
                    print(f"📊 [Gemini Token Usage] {current_model} -> Prompt: {p_tokens} | Completion: {c_tokens} | Total: {t_tokens}")

                return resp.text
            except Exception as e:
                err_str = str(e)
                is_temp_error = any(
                    keyword in err_str.lower() or keyword in err_str 
                    for keyword in ["503", "429", "unavailable", "exhausted", "demand", "rate limit", "limit exceeded", "quota", "overloaded"]
                )
                if attempt < max_retries and is_temp_error:
                    print(f"⚠️ [Gemini API] 모델 {current_model} 호출 중 일시적 오류 발생 ({err_str[:200]}). {delay}초 후 재시도 합니다... (재시도 {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    delay *= 2.0
                else:
                    # 모든 재시도 실패 후 폴백 모델이 지정되어 있으면 전환
                    if not use_fallback and current_model in FALLBACK_MAP:
                        fallback_model = FALLBACK_MAP[current_model]
                        print(f"🔴 [Gemini API] 모델 {current_model} 최종 실패. 폴백 모델 {fallback_model}(으)로 전환하여 호출을 재시도합니다.")
                        current_model = fallback_model
                        use_fallback = True
                        break  # inner loop 탈출하여 outer while 루프로 폴백 모델 시도
                    else:
                        print(f"🔴 [Gemini API] 최종 호출 실패 (모델: {current_model}, 시도 {attempt + 1}/{max_retries}): {err_str}")
                        raise e


def git_checkout_new_branch_sync(projects: list, jira_key: str) -> str:
    """
    지정된 프로젝트들의 master/main 브랜치를 최신으로 가져온 후, jira_key를 이름으로 하는 새 브랜치를 생성합니다.
    """
    if not jira_key:
        return "브랜치 생성 실패: Jira Key(그릿번호)가 입력되지 않았습니다."
        
    branch_name = jira_key if jira_key.startswith("feature/") else f"feature/{jira_key}"
    base_dir = r"C:\Users\LEEJAEJUN\IdeaProjects"
    log_messages = []
    
    for proj in projects:
        if proj == "db_meta":
            continue
        proj_path = os.path.join(base_dir, proj)
        if not os.path.isdir(proj_path):
            log_messages.append(f"[{proj}] 폴더가 존재하지 않아 건너뜁니다.")
            continue
            
        git_dir = os.path.join(proj_path, ".git")
        if not os.path.exists(git_dir):
            log_messages.append(f"[{proj}] Git 저장소가 아닙니다. (.git 폴더 없음)")
            continue
            
        try:
            print(f"🌿 [{proj}] 새 브랜치 생성 프로세스 시작 (Branch: {branch_name})")
            
            # 1. 안전을 위해 변경사항 임시 저장
            subprocess.run(["git", "stash"], cwd=proj_path, capture_output=True, text=True, check=False)
            
            # 2. 기본 브랜치 결정 (master, main, 혹은 현재 브랜치)
            default_branch = "master"
            checkout_res = subprocess.run(["git", "checkout", "master"], cwd=proj_path, capture_output=True, text=True)
            if checkout_res.returncode != 0:
                checkout_res = subprocess.run(["git", "checkout", "main"], cwd=proj_path, capture_output=True, text=True)
                if checkout_res.returncode == 0:
                    default_branch = "main"
                else:
                    # master/main 모두 없을 경우 현재 활성화된 브랜치 사용
                    branch_res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=proj_path, capture_output=True, text=True)
                    if branch_res.returncode == 0:
                        default_branch = branch_res.stdout.strip()
                    else:
                        raise Exception("기본 브랜치(master/main) 확인 및 현재 브랜치 획득에 실패했습니다.")
            
            # 3. Pull 최신화
            pull_res = subprocess.run(["git", "pull", "origin", default_branch], cwd=proj_path, capture_output=True, text=True)
            pull_msg = "pull 성공" if pull_res.returncode == 0 else "pull 건너뜀/실패 (로컬 전용)"
            
            # 4. 브랜치 존재 확인
            check_branch = subprocess.run(["git", "show-ref", f"refs/heads/{branch_name}"], cwd=proj_path, capture_output=True, text=True)
            if check_branch.returncode == 0:
                # 이미 존재하면 checkout
                checkout_existing = subprocess.run(["git", "checkout", branch_name], cwd=proj_path, capture_output=True, text=True)
                if checkout_existing.returncode == 0:
                    log_messages.append(f"[{proj}] 이미 존재하는 브랜치 '{branch_name}'로 전환하였습니다. ({pull_msg})")
                else:
                    raise Exception(f"기존 브랜치 '{branch_name}'로의 전환에 실패했습니다.")
            else:
                # 신규 브랜치 생성 및 checkout
                checkout_new = subprocess.run(["git", "checkout", "-b", branch_name], cwd=proj_path, capture_output=True, text=True)
                if checkout_new.returncode == 0:
                    log_messages.append(f"[{proj}] 기본 브랜치 '{default_branch}'에서 새 브랜치 '{branch_name}'를 생성하고 전환하였습니다. ({pull_msg})")
                    # Push to origin (타임아웃 15초 - 인증 팝업 블로킹 방지)
                    try:
                        push_res = subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=proj_path, capture_output=True, text=True, timeout=15)
                        if push_res.returncode == 0:
                            log_messages[-1] += " (원격 저장소에 Push 완료)"
                        else:
                            log_messages[-1] += f" (원격 Push 실패 - 수동 push 필요: {push_res.stderr.strip()[:100]})"
                    except subprocess.TimeoutExpired:
                        log_messages[-1] += " (원격 Push 타임아웃 - 인증 필요 시 수동 push 해주세요)"
                        print(f"⏰ [{proj}] git push 타임아웃 (15초) - Bitbucket 인증 필요. 로컬 브랜치는 정상 생성됨.")
                else:
                    raise Exception(f"새 브랜치 '{branch_name}' 생성에 실패했습니다.")
                    
        except Exception as git_err:
            log_messages.append(f"[{proj}] Git 에러: {str(git_err)}")
            print(f"🔴 [{proj}] Git 에러: {git_err}")
            
    return "\n".join(log_messages)


async def git_checkout_new_branch(projects: list, jira_key: str) -> str:
    """git_checkout_new_branch_sync를 비동기 실행하도록 래핑"""
    return await asyncio.to_thread(git_checkout_new_branch_sync, projects, jira_key)


async def run_development_agents(projects: list, final_report: str, jira_info: str, log_text: str, use_verify_loop: bool = False) -> str:
    """
    분석 보고서를 기반으로 지정된 프로젝트들의 자동 코드 개발을 수행합니다.
    """
    base_dir = r"C:\Users\LEEJAEJUN\IdeaProjects"
    log_messages = []
    
    for proj in projects:
        if proj == "db_meta":
            continue
            
        proj_path = os.path.join(base_dir, proj)
        if not os.path.isdir(proj_path) or not os.path.exists(os.path.join(proj_path, ".git")):
            continue
            
        print(f"💻 [{proj}] 분석 보고서 기반 개발 가동 시작...")
        
        dev_prompt = f"""
GS 리테일 개발 에이전트로서, 아래의 [통합 분석 보고서]와 [사용자 요청]을 바탕으로 실제 코드 수정 및 개발을 진행하십시오.

[지라 티켓 정보]
{jira_info}

[사용자 원본 요청]
{log_text}

[통합 분석 보고서]
{final_report}

[개발 지침]
1. 분석 보고서의 설계 및 가이드를 면밀히 검토하고, 해당하는 소스 코드를 찾아서 직접 수정하십시오.
2. 필요하다면 새로운 파일이나 코드를 생성하십시오.
3. 수정 완료 후 컴파일 또는 검증을 수행하여 에러가 없는지 확인하십시오.
4. 불필요한 추정이나 짐작으로 코드를 작성하지 말고, 확실하지 않은 경우 프로젝트의 CLAUDE.md 또는 SKILL.md 지침을 따르십시오.
5. 코드 수정이 완료되면 어떤 파일들이 수정되었는지 최종 요약을 작성해 주십시오.
"""
        try:
            result = await call_claude_cli_async(dev_prompt, cwd=proj_path, role="backend")
            print(f"🟢 [{proj}] 1차 개발 완료!")
            
            # 빌드 검증 및 자가 수정 루프
            if use_verify_loop:
                for iteration in range(1, 3):
                    build_cmd = None
                    if os.path.exists(os.path.join(proj_path, "gradlew.bat")):
                        build_cmd = ["cmd.exe", "/c", "gradlew.bat compileJava"]
                    elif os.path.exists(os.path.join(proj_path, "pom.xml")):
                        build_cmd = ["mvn.cmd", "compile"]
                    elif os.path.exists(os.path.join(proj_path, "package.json")):
                        build_cmd = ["npm.cmd", "run", "build"]
                        
                    if not build_cmd:
                        print(f"ℹ️ [{proj}] 빌드 시스템을 감지할 수 없어 검증 단계를 건너뜁니다.")
                        break
                        
                    print(f"🔄 [{proj}] 빌드 검증 중 (시도 {iteration}/2) -> {build_cmd}")
                    proc = await asyncio.create_subprocess_exec(
                        *build_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=proj_path
                    )
                    
                    try:
                        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
                        exit_code = proc.returncode
                        stdout_str = decode_output(stdout)
                        stderr_str = decode_output(stderr)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                        print(f"🔴 [{proj}] 빌드 검증 타임아웃 (3분 초과)")
                        log_messages.append(f"[{proj}] 빌드 검증 타임아웃 (3분 초과)")
                        break
                        
                    if exit_code == 0:
                        print(f"🟢 [{proj}] 빌드 검증 성공! 컴파일 오류 없음.")
                        log_messages.append(f"[{proj}] 빌드 검증 성공 (시도 {iteration}회차에 성공)")
                        break
                    else:
                        error_log = f"--- STDOUT ---\n{stdout_str[:3000]}\n--- STDERR ---\n{stderr_str[:2000]}"
                        print(f"⚠️ [{proj}] 빌드 실패 (exit code: {exit_code})")
                        log_messages.append(f"[{proj}] 빌드 검증 실패 (시도 {iteration}/2)")
                        
                        fix_prompt = f"""
[개발 에이전트 수정 코드 빌드 오류 피드백]
방금 전 작성하거나 수정하신 코드를 컴파일/빌드한 결과, 아래와 같은 에러 로그가 수집되었습니다.
프로젝트 소스코드를 분석하여 오류가 발생한 지점(Java 파일 등)을 직접 찾아내고 에러를 수습하도록 코드를 다시 올바르게 수정해주십시오.

[빌드 에러 로그]
{error_log}

[개발 지침]
1. 에러 로그에 나타난 패키지명, 클래스명, 라인번호를 참고하십시오.
2. 컴파일러가 지적한 문법적 에러(타입 불일치, import 누락, 변수/메서드 선언 오류 등)를 완벽하게 고쳐주십시오.
3. 수정 완료 후 최종 수정 파일 및 작업 요약을 작성해 주십시오.
"""
                        try:
                            print(f"🔄 [{proj}] 에러 피드백을 전달하여 자동 재수정 요청 중...")
                            result = await call_claude_cli_async(fix_prompt, cwd=proj_path, role="backend")
                            print(f"🟢 [{proj}] {iteration}차 재수정 완료!")
                        except Exception as fix_err:
                            print(f"🔴 [{proj}] 재수정 에이전트 호출 중 에러 발생: {fix_err}")
                            log_messages.append(f"[{proj}] 재수정 에이전트 호출 중 API 에러: {str(fix_err)}")
                            break
                else:
                    log_messages.append(f"[{proj}] 최종 빌드 실패 상태로 종료되었습니다.")
            
            log_messages.append(f"[{proj}] 최종 개발 완료 요약:\n{result}")
            
        except Exception as e:
            log_messages.append(f"[{proj}] 개발 진행 중 오류 발생: {str(e)}")
            print(f"🔴 [{proj}] 개발 중 에러: {e}")
            
    return "\n\n".join(log_messages)


# --- [🎯 프로젝트 디렉토리 목록 조회 API] ---
@app.get("/api/v1/projects/directories")
async def list_project_directories():
    base_dir = r"C:\Users\LEEJAEJUN\IdeaProjects"
    try:
        if not os.path.exists(base_dir):
            return {"status": "error", "message": "Base directory not found"}
        
        dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and not d.startswith(".")]
        return {"status": "success", "directories": dirs}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- [🎯 메인 오케스트레이션 API 엔드포인트] ---
@app.post("/api/v1/orchestrate")
async def process_orchestration(request: Request):
    try:
        # 💡 토큰 사용량 측정 시작
        token_usage_dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        request_token_usage.set(token_usage_dict)
        # 리액트가 보낸 JSON 데이터를 있는 그대로 수집
        req_data = await request.json()

        # 변수명 구조 일관성 있게 매핑
        jira_key = req_data.get("jira_key") or req_data.get("jiraKey")
        log_text = req_data.get("log_text") or req_data.get("text") or req_data.get("prompt") or ""
        log_images = req_data.get("log_images", [])

        # 신규 파라미터 파싱
        run_development = req_data.get("run_development") or req_data.get("runDevelopment") or False
        create_branch = req_data.get("create_branch") or req_data.get("createBranch") or False
        use_verify_loop = req_data.get("use_verify_loop") or req_data.get("useVerifyLoop") or False
        require_leader_feedback = req_data.get("require_leader_feedback") or req_data.get("requireLeaderFeedback") or False
        run_testing = req_data.get("run_testing") or req_data.get("runTesting") or False

        working_agents_raw = req_data.get("working_agents") or req_data.get("selectedAgents") or []
        all_projects = []

        for agent in working_agents_raw:
            if isinstance(agent, dict):
                assigned = agent.get("assignedProjects") or agent.get("projects") or agent.get("target_projects")
                if assigned and isinstance(assigned, list):
                    all_projects.extend(assigned)
            elif isinstance(agent, str):
                all_projects.append(agent)

        direct_projects = req_data.get("projects") or req_data.get("selectedProjects")
        if direct_projects and isinstance(direct_projects, list):
            all_projects.extend(direct_projects)

        # 중복 제거 및 불필요한 찌꺼기 필터링
        all_projects = [p for p in set(all_projects) if not p.startswith("agent_") and p.strip() != ""]

        git_log = ""
        if create_branch:
            if jira_key:
                git_log = await git_checkout_new_branch(all_projects, jira_key)
            else:
                group_logs = []
                for agent in working_agents_raw:
                    agent_jira = agent.get("jira_key") or agent.get("jiraKey")
                    agent_projects = agent.get("assignedProjects") or agent.get("projects") or []
                    if agent_jira and agent_projects:
                        sub_log = await git_checkout_new_branch(agent_projects, agent_jira)
                        group_logs.append(sub_log)
                git_log = "\n".join(group_logs)

        print(f"🚀 [수정완료] 오케스트레이터 가동 - 분석 대상 프로젝트: {all_projects}")

        # 2. 지라(Jira) 연동 정보 가져오기 (.env 보안 적용)
        jira_info = "제공된 지라 티켓 정보 없음"
        if jira_key:
            JIRA_URL = os.getenv("JIRA_URL")
            JIRA_PAT = os.getenv("JIRA_PAT")
            url = f"{JIRA_URL}/rest/api/2/issue/{jira_key}"
            headers = {"Authorization": f"Bearer {JIRA_PAT}"}
            try:
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    jira_info = f"티켓명: {data['fields']['summary']}\n요청내용: {data['fields'].get('description', '')}"
            except Exception as e:
                print(f"Jira API Connect Pass: {e}")

        # --- [ 3. 🚀 멀티 에이전트 병렬 독립 분석 파이프라인 ] ---
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY가 .env 파일에 셋팅되지 않았습니다.")

        gemini_client = genai.Client(api_key=GEMINI_API_KEY)

        # ① 에이전트별 독립 분석 코루틴 (하이브리드 엔진 지원)
        async def analyze_single_agent(agent_data):
            agent_name = agent_data.get("name", "에이전트")
            agent_engine = agent_data.get("engine", "Gemini-Flash")
            agent_role = agent_data.get("role", "backend")
            agent_projects = agent_data.get("assignedProjects", [])
            model_name = ENGINE_MAP.get(agent_engine, "gemini-2.5-flash")

            # 💡 에이전트별 개별 요청 정보 추출 (없으면 글로벌 요청으로 폴백)
            agent_jira_key = agent_data.get("jira_key") or req_data.get("jira_key") or req_data.get("jiraKey")
            agent_log_text = agent_data.get("log_text") or req_data.get("log_text") or req_data.get("text") or req_data.get("prompt") or ""

            print(f"⚡ [{agent_name}] 독립 분석 시작 → 엔진: {agent_engine} ({model_name}), 프로젝트: {agent_projects}")

            # 에이전트별 Jira 티켓 정보 조회 (비동기로 실행)
            agent_jira_info = "제공된 지라 티켓 정보 없음"
            if agent_jira_key:
                JIRA_URL = os.getenv("JIRA_URL")
                JIRA_PAT = os.getenv("JIRA_PAT")
                url = f"{JIRA_URL}/rest/api/2/issue/{agent_jira_key}"
                headers = {"Authorization": f"Bearer {JIRA_PAT}"}
                try:
                    loop = asyncio.get_event_loop()
                    resp = await loop.run_in_executor(
                        None,
                        lambda: requests.get(url, headers=headers, timeout=5)
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        agent_jira_info = f"티켓명: {data['fields']['summary']}\n요청내용: {data['fields'].get('description', '')}"
                except Exception as e:
                    print(f"Jira API Connect Pass ({agent_name}): {e}")

            try:
                # 📸 만약 이미지가 첨부되어 있다면 Claude CLI 대신 Gemini 모델을 사용하여 이미지 분석을 지원합니다.
                is_claude_cli = (model_name == "claude-cli")
                if is_claude_cli and log_images:
                    print(f"📸 [{agent_name}] 이미지가 첨부되어 있어 Claude CLI 대신 Gemini-Flash를 사용하여 멀티모달 분석을 수행합니다.")
                    is_claude_cli = False
                    model_name = "gemini-2.5-flash"

                if is_claude_cli:
                    # 🆕 Claude CLI 하네스 호출 (MCP 서버 활용, 컨텍스트 자동 탐색)
                    prompt = build_claude_cli_prompt(agent_data, agent_jira_info, agent_log_text, engine_label="Claude-CLI")

                    # 첫 번째 프로젝트 폴더를 작업 디렉토리로 설정
                    primary_project = next((p for p in agent_projects if p != "db_meta"), None)
                    cwd = f"C:\\Users\\LEEJAEJUN\\IdeaProjects\\{primary_project}" if primary_project else None

                    try:
                        result = await call_claude_cli_async(prompt, cwd=cwd, role=agent_role)
                        print(f"✅ [{agent_name}] Claude CLI 독립 분석 완료! (결과 {len(result)}자)")
                    except Exception as cli_err:
                        print(f"⚠️ [{agent_name}] Claude CLI 독립 분석 실패 ({cli_err}). Gemini Flash로 자동 폴백합니다.")
                        md_ctx, db_ctx, navi_ctx = get_smart_context(agent_projects, agent_log_text)
                        fallback_prompt = build_agent_prompt(agent_data, md_ctx, db_ctx, navi_ctx, agent_jira_info, agent_log_text, engine_label="Gemini-Fallback")
                        result = await call_gemini_async(gemini_client, "gemini-2.5-flash", fallback_prompt, log_images)
                        print(f"✅ [{agent_name}] Gemini Flash 폴백 분석 완료! (결과 {len(result)}자)")
                else:
                    # 기존 Gemini API 호출 (컨텍스트 수동 삽입)
                    md_ctx, db_ctx, navi_ctx = get_smart_context(agent_projects, agent_log_text)
                    prompt = build_agent_prompt(agent_data, md_ctx, db_ctx, navi_ctx, agent_jira_info, agent_log_text, engine_label=model_name)
                    result = await call_gemini_async(gemini_client, model_name, prompt, log_images)
                    print(f"✅ [{agent_name}] Gemini 독립 분석 완료! (결과 {len(result)}자)")
            except Exception as agent_err:
                print(f"🔴 [{agent_name}] 에이전트 분석 중 치명적 오류 발생 (생략 진행): {agent_err}")
                result = f"⚠️ **[{agent_name} 에이전트 업무 불능]** API 호출 한도(Rate Limit), 할당량(Quota) 초과 또는 연동 오류가 발생하여 이 영역에 대한 심층 분석을 완료할 수 없습니다.\n* (상세 오류내용: {str(agent_err)})"

            return (agent_name, result, agent_jira_key)

        # ② asyncio.gather로 모든 에이전트 병렬 실행 (Claude CLI는 Semaphore로 최대 3개 동시)
        print(f"🚀 [{len(working_agents_raw)}개 에이전트] 하이브리드 병렬 독립 분석 가동!")
        agent_results = await asyncio.gather(
            *[analyze_single_agent(a) for a in working_agents_raw]
        )
        print(f"✅ 전체 {len(agent_results)}개 에이전트 독립 분석 완료!")

        # ⚠️ [분석 중단 예외 처리] 에이전트 결과물 중 분석 불가/정보 부족/업무 불능 상태가 감지되면 필터링합니다.
        cannot_analyze_agents = []
        valid_agent_results = []
        for name, res, j_key in agent_results:
            is_failure = "에이전트 업무 불능" in res or "API 호출 한도" in res
            is_unable_keywords = any(kw in res for kw in [
                "분석할 수 없", "분석이 불가능", "분석 불가",
                "확인할 수 없", "확인이 불가능", "확인 불가",
                "정보가 부족", "정보 부족", "이미지 내용을 파악할 수",
                "이미지를 직접 분석할 수"
            ])
            # 리포트 길이가 너무 짧은데 부정적 키워드가 있으면 정말 분석을 못한 것으로 판단 (오탐지 방지)
            is_unable = is_unable_keywords and len(res) < 350
            if is_failure or is_unable:
                cannot_analyze_agents.append((name, res, j_key))
            else:
                valid_agent_results.append((name, res, j_key))
                
        # 팀장 피드백 루프가 꺼져있고 실패한 에이전트가 있다면 기존처럼 즉시 중단(Abort)
        if cannot_analyze_agents and not require_leader_feedback:
            print(f"⚠️ [분석 중단] 일부 에이전트가 정보를 분석할 수 없는 상태입니다: {[n for n, _, _ in cannot_analyze_agents]}")
            error_summary = "### ⚠️ 분석 진행 중단 (정보 부족 및 분석 불가)\n\n"
            error_summary += "에이전트가 제공된 이미지 또는 텍스트 정보를 분석할 수 없거나 필수 지식(DB 스키마 등)이 부족하여 작업을 즉시 중단했습니다.\n"
            error_summary += "추가적인 텍스트 힌트 제공 또는 유효한 이미지를 첨부하여 다시 시도해 주십시오.\n\n"
            for name, res, _ in cannot_analyze_agents:
                error_summary += f"#### 🔴 {name} 분석 상태\n{res}\n\n"
                
            agent_reports = {}
            for a_name, a_res, _ in agent_results:
                agent_id = a_name
                for a in working_agents_raw:
                    if isinstance(a, dict) and a.get("name") == a_name:
                        agent_id = a.get("id") or a_name
                        break
                agent_reports[agent_id] = {
                    "result": a_res,
                    "result_html": convert_markdown_to_html(a_res, title=f"AI Analyst Report - {a_name}")
                }

            response_html = convert_markdown_to_html(error_summary, title="Orchestration Aborted")
            return {
                "status": "success",
                "message": "분석 불가 상황이 발생하여 프로세스를 중단했습니다.",
                "result": error_summary,
                "result_html": response_html,
                "agent_reports": agent_reports,
                "token_usage": request_token_usage.get() or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
        elif cannot_analyze_agents and require_leader_feedback:
            print(f"⚠️ 일부 에이전트 분석 불가 감지. 피드백 루프에서는 제외하고 강행합니다: {[n for n, _, _ in cannot_analyze_agents]}")

        # 🔄 [Round 2: 팀장 피드백 및 재분석] 
        final_agent_results = []
        if require_leader_feedback and valid_agent_results:
            print(f"👑 [팀장 피드백 파이프라인] {len(valid_agent_results)}개 에이전트에 대한 팀장 피드백 및 2차 분석 시작...")
            
            async def generate_feedback_and_refine(agent_res):
                agent_name, first_round_res, agent_jira_key = agent_res
                
                # 팀장 피드백 생성
                feedback_prompt = (
                    f"당신은 이 개발 프로젝트의 수석 아키텍트(팀장)입니다.\n"
                    f"다음은 '{agent_name}' 에이전트가 수행한 1차 분석 리포트입니다.\n\n"
                    f"### 1차 분석 리포트\n{first_round_res}\n\n"
                    f"이 리포트를 검토하고, 누락된 비즈니스 로직, 보안/성능 상의 허점, 또는 더 개선해야 할 방향을 1~3가지로 지적해주세요.\n"
                    f"매우 날카롭고 직관적으로 마크다운으로 작성하세요. (인사말 생략)"
                )
                
                print(f"👑 [{agent_name}] 팀장 피드백 생성 중...")
                try:
                    # 팀장은 항상 리더 롤로 동작
                    feedback = await call_claude_cli_async(feedback_prompt, cwd=r"C:\Users\LEEJAEJUN\IdeaProjects\aiOrchestrator", role="leader")
                    print(f"💬 [{agent_name}] 팀장 피드백 완료!")
                except Exception as e:
                    print(f"⚠️ [{agent_name}] 팀장 피드백 생성 실패. (Gemini 폴백): {e}")
                    feedback = await call_gemini_async(gemini_client, "gemini-2.5-flash", feedback_prompt)
                
                # 원본 에이전트 찾기
                agent_data = next((a for a in working_agents_raw if a.get("name") == agent_name), {})
                model_name = ENGINE_MAP.get(agent_data.get("engine", "Gemini-Flash"), "gemini-2.5-flash")
                is_claude_cli = (model_name == "claude-cli")
                
                # 2차 재분석 요청
                round2_prompt = (
                    f"당신은 '{agent_name}' 에이전트입니다.\n"
                    f"당신이 작성한 1차 분석에 대해 팀장이 다음과 같은 피드백을 주었습니다.\n\n"
                    f"> **[팀장 피드백]**\n{feedback}\n\n"
                    f"위 피드백을 적극적으로 수용하여 기존 분석 내용을 심층적으로 수정/보완한 '최종 2차 분석 리포트'를 작성하세요.\n"
                    f"기존 분석의 좋은 점은 유지하되, 지적된 문제를 완전히 해결한 완성본을 제공해야 합니다."
                )
                
                print(f"🔥 [{agent_name}] 2차 재분석(Refinement) 시작...")
                try:
                    if is_claude_cli and not log_images:
                        final_res = await call_claude_cli_async(round2_prompt, cwd=r"C:\Users\LEEJAEJUN\IdeaProjects\aiOrchestrator", role=agent_data.get("role", "backend"))
                    else:
                        final_res = await call_gemini_async(gemini_client, "gemini-2.5-flash", round2_prompt, log_images)
                    print(f"✅ [{agent_name}] 2차 재분석 완료!")
                except Exception as e:
                    print(f"⚠️ [{agent_name}] 2차 분석 실패. 1차 결과를 유지합니다: {e}")
                    final_res = first_round_res + f"\n\n> **[팀장 피드백 반영 실패]**\n{feedback}\n\n*(2차 재분석 중 오류가 발생하여 1차 결과가 유지되었습니다.)*"
                    
                return (agent_name, final_res, agent_jira_key)
                
            # 피드백 파이프라인 병렬 가동
            refined_results = await asyncio.gather(*[generate_feedback_and_refine(r) for r in valid_agent_results])
            
            # 실패해서 피드백을 받지 못한 에이전트들(에러 리포트) 다시 병합
            final_agent_results = refined_results + cannot_analyze_agents
        else:
            final_agent_results = agent_results

        # ③ 취합 단계 (Claude CLI 우선, 실패 시 Gemini Flash 폴백)
        if len(final_agent_results) == 1:
            # 에이전트가 1명이면 취합 불필요, 바로 결과 사용
            response_text = final_agent_results[0][1]
            print("📋 에이전트 1명 → 취합 단계 스킵, 단독 분석 결과 채택")
        else:
            synthesis_prompt = build_synthesis_prompt([(name, res) for name, res, _ in final_agent_results])
            try:
                # Claude CLI 우선으로 취합 시도
                print(f"🔗 [{len(final_agent_results)}개 결과] Claude CLI로 취합 시작...")
                response_text = await call_claude_cli_async(
                    synthesis_prompt,
                    cwd=r"C:\Users\LEEJAEJUN\IdeaProjects\aiOrchestrator",
                    role="backend"
                )
                print("✨ [최종 완수] Claude CLI 멀티 에이전트 취합 리포트 완성!")
            except Exception as claude_err:
                # Claude CLI 실패 시 Gemini Flash로 폴백
                print(f"⚠️ Claude CLI 취합 실패 ({claude_err}), Gemini Flash로 폴백...")
                response_text = await call_gemini_async(gemini_client, "gemini-2.5-flash", synthesis_prompt)
                print("✨ [최종 완수] Gemini Flash 폴백 취합 리포트 완성!")

        # Git branch log prepending
        if create_branch and git_log:
            response_text = f"### 🌿 Git 브랜치 생성 결과\n```\n{git_log}\n```\n\n" + response_text

        # Development sub-process running
        dev_log = ""
        if run_development:
            dev_log = await run_development_agents(all_projects, response_text, jira_info, log_text, use_verify_loop=use_verify_loop)
            
        if run_development and dev_log:
            response_text += f"\n\n---\n\n### 💻 자동 개발 진행 결과\n{dev_log}"

        # 6. 💡 [팀장 Claude용 브릿지] 분석 초안을 각 프로젝트 폴더로 분산 저장
        try:
            # ① 오늘 날짜 포맷 (예: 20260527)
            today_str = datetime.now().strftime("%Y%m%d")

            # ③ 선택된 프로젝트들을 돌면서 각각의 폴더에 복사본 저장
            for proj in all_projects:
                if "db_meta" in proj:
                    continue

                # 이 프로젝트를 담당한 에이전트 찾기
                assigned_agent_jira_key = None
                for agent_data in working_agents_raw:
                    assigned_projects = agent_data.get("assignedProjects") or agent_data.get("projects") or []
                    if proj in assigned_projects:
                        assigned_agent_jira_key = agent_data.get("jira_key") or req_data.get("jira_key") or req_data.get("jiraKey")
                        break

                # ② 지라 티켓 유무에 따른 파일명 동적 결정
                if assigned_agent_jira_key:
                    file_name = f"{assigned_agent_jira_key}_리포트.md"
                elif jira_key:
                    file_name = f"{jira_key}_리포트.md"
                else:
                    file_name = f"일반리포트_{datetime.now().strftime('%H%M%S')}.md"

                # 생성할 폴더 경로 (예: ../chooyu/report/20260527)
                target_dir = f"../{proj}/report/{today_str}"
                os.makedirs(target_dir, exist_ok=True)

                # 최종 파일 경로
                target_file = f"{target_dir}/{file_name}"

                # 파일 저장
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(response_text)

                # HTML 파일 저장
                file_name_html = file_name.replace(".md", ".html")
                target_file_html = f"{target_dir}/{file_name_html}"
                html_text = convert_markdown_to_html(response_text, title=f"AI Orchestrator Report - {assigned_agent_jira_key or jira_key or '일반리포트'}")
                with open(target_file_html, "w", encoding="utf-8") as f:
                    f.write(html_text)

                print(f"💾 [{proj}] 부서 서류철에 리포트 꽂힘 -> {target_file} & {target_file_html}")

            # ④ 윈도우 원드라이브 경로가 존재할 경우, 파워오토메이트 감지용 폴더에도 복사 저장
            onedrive_base = r"C:\Users\LEEJAEJUN\OneDrive - GS Retail Co., Ltd"
            if os.path.exists(onedrive_base):
                onedrive_report_dir = os.path.join(onedrive_base, "AI_Reports")
                os.makedirs(onedrive_report_dir, exist_ok=True)
                
                # 파일명 결정
                od_file_name = f"{jira_key}_결과.txt" if jira_key else f"일반리포트_{datetime.now().strftime('%H%M%S')}_결과.txt"
                onedrive_file_path = os.path.join(onedrive_report_dir, od_file_name)
                
                with open(onedrive_file_path, "w", encoding="utf-8") as f:
                    f.write(response_text)
                print(f"💾 [OneDrive Sync] 파워 오토메이트 감지용 원드라이브 폴더 복사 완료 -> {onedrive_file_path}")

        except Exception as file_err:
            print(f"🔴 보고서 파일 저장 실패: {file_err}")

        # 각 에이전트의 개별 분석 보고서 수집
        agent_reports = {}
        for name, res, a_jira_key in agent_results:
            agent_id = None
            for a in working_agents_raw:
                if a.get("name") == name:
                    agent_id = a.get("id")
                    break
            if not agent_id:
                agent_id = name
            res_html = convert_markdown_to_html(res, title=f"AI Analyst Report - {name}")
            agent_reports[agent_id] = {
                "result": res,
                "result_html": res_html
            }

        # 리액트 화면단으로 최종 리포트 반환
        usage = request_token_usage.get() or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        response_html = convert_markdown_to_html(response_text, title=f"AI Orchestrator Report - {jira_key or '일반리포트'}")
        return {
            "status": "success",
            "result": response_text,
            "result_html": response_html,
            "agent_reports": agent_reports,
            "token_usage": usage
        }

    except Exception as e:
        print(f"🔴 서버 내부 에러 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- [🤖 AUTO 오케스트레이션 글로벌 상태] ---
auto_status = {
    "step": "idle",         # "idle", "planning", "analyzing", "reviewing", "completed", "error"
    "message": "대기 중",
    "assignments": []       # [{"agent_name": "...", "role": "...", "projects": [...]}]
}

@app.get("/api/v1/orchestrate/auto/status")
async def get_auto_orchestrate_status():
    global auto_status
    return auto_status

@app.post("/api/v1/orchestrate/auto/status/reset")
async def reset_auto_orchestrate_status():
    global auto_status
    auto_status = {
        "step": "idle",
        "message": "대기 중",
        "assignments": [],
        "result": None,
        "result_html": None,
        "agent_reports": None,
        "token_usage": None
    }
    return {"status": "reset"}


# --- [🤖 AUTO 오케스트레이션 기본값 및 코어 로직] ---

DEFAULT_PROJECTS = [
    {"id": "echo-frontend", "name": "echo-frontend (화면단/MiPlatform)"},
    {"id": "annapurna", "name": "annapurna (메인 API/스프링)"},
    {"id": "chooyu", "name": "chooyu (고객관리 API/스프링)"},
    {"id": "member-batch", "name": "member-batch (배치 작업)"},
    {"id": "db_meta", "name": "db_meta (MDS 데이터베이스 스키마 엑셀)"},
    {"id": "manaslu", "name": "마나스루"},
    {"id": "smtc-batch-cst", "name": "고객배치"},
    {"id": "pis-epr-batch_git", "name": "유효기간제 배치"},
]

DEFAULT_AGENTS = [
    {
        "id": "agent_be1",
        "name": "백엔드/DB 에이전트1",
        "engine": "Claude-CLI",
        "role": "backend",
        "status": "idle",
        "spriteAsset": "👨‍💻",
        "assignedProjects": ["annapurna", "chooyu", "db_meta"],
        "isActive": True,
        "stress": 0,
        "totalTokens": 0
    },
    {
        "id": "agent_be2",
        "name": "백엔드/DB 에이전트2",
        "engine": "Claude-CLI",
        "role": "backend",
        "status": "idle",
        "spriteAsset": "🧙‍♂️",
        "assignedProjects": ["annapurna", "member-batch", "db_meta"],
        "isActive": True,
        "stress": 0,
        "totalTokens": 0
    },
    {
        "id": "agent_fe",
        "name": "프론트엔드 에이전트",
        "engine": "Gemini-Flash",
        "role": "frontend",
        "status": "idle",
        "spriteAsset": "👩‍💻",
        "assignedProjects": ["echo-frontend"],
        "isActive": True,
        "stress": 0,
        "totalTokens": 0
    },
    {
        "id": "agent_leader",
        "name": "팀장",
        "engine": "Gemini-Flash",
        "role": "leader",
        "status": "idle",
        "spriteAsset": "👔",
        "assignedProjects": [],
        "isActive": True,
        "stress": 0,
        "totalTokens": 0
    }
]

async def run_auto_orchestration_core(
    jira_key: str,
    log_text: str,
    log_images: list,
    available_agents: list,
    available_projects: list,
    leader_engine: str,
    create_branch: bool = False,
    run_development: bool = False,
    use_self_reflection: bool = False,
    use_verify_loop: bool = False,
    orchestration_mode: str = "parallel",
    generate_pt: bool = False
):
    global auto_status
    # 💡 토큰 사용량 측정 시작
    token_usage_dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    request_token_usage.set(token_usage_dict)
    
    # 1단계 시작: 기획 단계 초기화
    auto_status["step"] = "planning"
    auto_status["message"] = "👔 팀장이 업무 배정 계획을 수립하고 있습니다..."
    auto_status["assignments"] = []
    auto_status["result"] = None
    auto_status["result_html"] = None
    auto_status["agent_reports"] = None
    auto_status["token_usage"] = None

    print(f"🤖 [Auto Core] 가동! 팀장 엔진: {leader_engine}, 팀원: {len(available_agents)}명, 프로젝트: {len(available_projects)}개")

    # Jira 정보 획득
    jira_info = "제공된 지라 티켓 정보 없음"
    if jira_key:
        JIRA_URL = os.getenv("JIRA_URL")
        JIRA_PAT = os.getenv("JIRA_PAT")
        url = f"{JIRA_URL}/rest/api/2/issue/{jira_key}"
        headers = {"Authorization": f"Bearer {JIRA_PAT}"}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                jira_info = f"티켓명: {data['fields']['summary']}\n요청내용: {data['fields'].get('description', '')}"
        except Exception as e:
            print(f"Jira API Connect Pass: {e}")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY가 .env 파일에 셋팅되지 않았습니다.")
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

    # ==============================
    # [1단계] 👔 팀장: 업무 배정 계획 수립
    # ==============================
    print("👔 [팀장] 1단계: 업무 배정 계획 수립 중...")
    planning_prompt = build_leader_planning_prompt(available_agents, available_projects, jira_info, log_text)

    leader_model = ENGINE_MAP.get(leader_engine, "gemini-2.5-flash")
    # 📸 만약 이미지가 첨부되어 있다면 Claude CLI 대신 Gemini 모델을 사용하여 이미지 분석 및 기획을 수행합니다.
    is_leader_claude_cli = (leader_model == "claude-cli")
    if is_leader_claude_cli and log_images:
        print("📸 [팀장 1단계] 이미지가 첨부되어 있어 Claude CLI 대신 Gemini-Flash를 사용하여 멀티모달 기획을 수행합니다.")
        is_leader_claude_cli = False
        leader_model = "gemini-2.5-flash"

    if is_leader_claude_cli:
        try:
            planning_raw = await call_claude_cli_async(planning_prompt, role="backend")
        except Exception as cli_err:
            print(f"⚠️ [팀장 1단계] Claude CLI 기획 실패 ({cli_err}). Gemini Flash로 자동 폴백합니다.")
            planning_raw = await call_gemini_async(gemini_client, "gemini-2.5-flash", planning_prompt, log_images)
    else:
        planning_raw = await call_gemini_async(gemini_client, leader_model, planning_prompt, log_images)

    # JSON 파싱 (마크다운 코드 블록 제거 후 추출)
    json_str = re.sub(r'```(?:json)?', '', planning_raw).strip()
    json_str = re.sub(r'```', '', json_str).strip()
    json_match = re.search(r'\{[\s\S]*\}', json_str)
    if not json_match:
        raise Exception(f"팀장이 유효한 JSON을 반환하지 않았습니다. 원문: {planning_raw[:400]}")

    plan = json.loads(json_match.group())
    assignments = plan.get("assignments", [])

    if not assignments:
        raise Exception("팀장 배정 계획에 에이전트 배정이 없습니다.")

    print(f"👔 [팀장] 배정 완료: {len(assignments)}개 에이전트 배정")
    print(f"   분석 포인트: {plan.get('analysis_focus', '')}")
    for a in assignments:
        print(f"   └ {a['agent_name']} → {a.get('projects', [])}")

    # 1단계 완료: 에이전트 배정 목록을 전역 상태에 저장
    auto_status["assignments"] = assignments

    git_log = ""
    if create_branch:
        all_projects = list(set(p for a in assignments for p in a.get("projects", [])))
        auto_status["step"] = "planning"
        auto_status["message"] = "🌿 마스터 브랜치에서 신규 개발 브랜치 생성 중..."
        git_log = await git_checkout_new_branch(all_projects, jira_key)

    # 분석 단계로 돌입
    auto_status["step"] = "analyzing"
    assigned_names = ", ".join([a["agent_name"] for a in assignments])
    auto_status["message"] = f"🤝 배정된 {len(assignments)}명의 팀원({assigned_names})이 병렬 분석을 수행하고 있습니다..."

    # ==============================
    # [2단계] 🤝 에이전트 병렬 독립 분석
    # ==============================
    print(f"🤝 [2단계] {len(assignments)}개 에이전트 병렬 분석 가동!")
    agent_map = {a["name"]: a for a in available_agents}

    async def analyze_auto_agent(assignment, feedback=None):
        agent_name = assignment["agent_name"]
        agent_projects = assignment.get("projects", [])
        agent_role = assignment.get("role", "backend")
        db_filter = assignment.get("db_filter")  # 👔 팀장이 판단해 준 DB 필터 키워드
        base_agent = agent_map.get(agent_name, {})
        agent_engine = base_agent.get("engine", "Gemini-Flash")
        model_name = ENGINE_MAP.get(agent_engine, "gemini-2.5-flash")

        print(f"⚡ [{agent_name}] 자동 배정 분석 시작 → 엔진: {agent_engine} ({model_name}), 프로젝트: {agent_projects}, DB필터: {db_filter}")
        agent_data = {
            "name": agent_name,
            "engine": agent_engine,
            "role": agent_role,
            "assignedProjects": agent_projects
        }

        try:
            # 📸 만약 이미지가 첨부되어 있다면 Claude CLI 대신 Gemini 모델을 사용하여 이미지 분석을 지원합니다.
            is_claude_cli = (model_name == "claude-cli")
            if is_claude_cli and log_images:
                print(f"📸 [{agent_name}] 이미지가 첨부되어 있어 Claude CLI 대신 Gemini-Flash를 사용하여 멀티모달 분석을 수행합니다.")
                is_claude_cli = False
                model_name = "gemini-2.5-flash"

            if is_claude_cli:
                prompt = build_claude_cli_prompt(agent_data, jira_info, log_text)
                if db_filter:
                    prompt = f"ℹ️ [DB 스키마 타겟팅 안내] 이번 분석은 주로 {db_filter} 관련 데이터베이스(예: {db_filter}_ERD.xlsx 등)를 중점적으로 확인하십시오.\n\n" + prompt
                if feedback:
                    prompt += f"\n\n[👔 팀장의 1차 검토 피드백 및 보완 지시]\n{feedback}\n\n위 피드백 사항을 반드시 반영하여 기존 분석 보고서를 보완 및 최종 업데이트하십시오."
                primary_project = next((p for p in agent_projects if p != "db_meta"), None)
                cwd = f"C:\\Users\\LEEJAEJUN\\IdeaProjects\\{primary_project}" if primary_project else None
                try:
                    result = await call_claude_cli_async(prompt, cwd=cwd, role=agent_role)
                    print(f"✅ [{agent_name}] Claude CLI 분석 완료 ({len(result)}자)")
                except Exception as cli_err:
                    print(f"⚠️ [{agent_name}] Claude CLI 분석 실패 ({repr(cli_err)}). Gemini Flash로 자동 폴백합니다.")
                    md_ctx, db_ctx, navi_ctx = get_smart_context(agent_projects, log_text, db_filter=db_filter)
                    fallback_prompt = build_agent_prompt(agent_data, md_ctx, db_ctx, navi_ctx, jira_info, log_text)
                    if feedback:
                        fallback_prompt += f"\n\n[👔 팀장의 1차 검토 피드백 및 보완 지시]\n{feedback}\n\n위 피드백 사항을 반드시 반영하여 기존 분석 보고서를 보완 및 최종 업데이트하십시오."
                    result = await call_gemini_async(gemini_client, "gemini-2.5-flash", fallback_prompt, log_images)
                    print(f"✅ [{agent_name}] Gemini Flash 폴백 분석 완료 ({len(result)}자)")
            else:
                md_ctx, db_ctx, navi_ctx = get_smart_context(agent_projects, log_text, db_filter=db_filter)
                prompt = build_agent_prompt(agent_data, md_ctx, db_ctx, navi_ctx, jira_info, log_text)
                if feedback:
                    prompt += f"\n\n[👔 팀장의 1차 검토 피드백 및 보완 지시]\n{feedback}\n\n위 피드백 사항을 반드시 반영하여 기존 분석 보고서를 보완 및 최종 업데이트하십시오."
                result = await call_gemini_async(gemini_client, model_name, prompt, log_images)
                print(f"✅ [{agent_name}] Gemini 분석 완료 ({len(result)}자)")
        except Exception as agent_err:
            print(f"🔴 [{agent_name}] 에이전트 분석 중 치명적 오류 발생 (생략 진행): {agent_err}")
            result = f"⚠️ **[{agent_name} 에이전트 업무 불능]** API 호출 한도(Rate Limit), 할당량(Quota) 초과 또는 연동 오류가 발생하여 이 영역에 대한 심층 분석을 완료할 수 없습니다.\n* (상세 오류내용: {str(agent_err)})"

        return (agent_name, result)

    if orchestration_mode == "pipeline":
        # 💡 [순차적 파이프라인 모드] 우선순위에 따라 순차 실행하며 앞 사람의 산출물을 전달
        role_priority = {"기획": 1, "디자이너": 2, "frontend": 3, "backend": 3, "테스터": 4}
        assignments.sort(key=lambda x: role_priority.get(x["agent"].get("role", "").lower(), 5))
        
        agent_results = []
        pipeline_context = ""
        
        for a in assignments:
            agent_name = a["agent"]["name"]
            auto_status["message"] = f"🔄 {agent_name} 에이전트가 파이프라인 단계를 수행 중입니다..."
            
            # 이전 에이전트의 산출물이 있다면 feedback 파라미터를 활용해 전달
            current_feedback = f"[이전 파이프라인 단계 산출물]\n{pipeline_context}\n\n위 산출물을 바탕으로 당신의 역할을 수행하십시오." if pipeline_context else None
            
            res = await analyze_auto_agent(a, feedback=current_feedback)
            agent_results.append(res)
            
            pipeline_context += f"\n\n--- {agent_name} 결과 ---\n{res[1]}"
            
        print(f"✅ [2단계] 전체 {len(agent_results)}개 에이전트 파이프라인 릴레이 완료!")
    else:
        # 💡 [기본 병렬 스웜 모드] 모두 동시 실행
        agent_results = list(await asyncio.gather(
            *[analyze_auto_agent(a) for a in assignments]
        ))
        print(f"✅ [2단계] 전체 {len(agent_results)}개 에이전트 분석 완료!")

    # ⚠️ [분석 중단 예외 처리] 에이전트 결과물 중 분석 불가/정보 부족/업무 불능 상태가 감지되면 즉시 중단을 요청합니다.
    cannot_analyze_agents = []
    for name, res in agent_results:
        is_failure = "에이전트 업무 불능" in res or "API 호출 한도" in res
        is_unable = any(kw in res for kw in [
            "분석할 수 없", "분석이 불가능", "분석 불가",
            "확인할 수 없", "확인이 불가능", "확인 불가",
            "정보가 부족", "정보 부족", "이미지 내용을 파악할 수",
            "이미지를 직접 분석할 수"
        ])
        if is_failure or is_unable:
            cannot_analyze_agents.append((name, res))
            
    if cannot_analyze_agents:
        print(f"⚠️ [분석 중단] 일부 에이전트가 정보를 분석할 수 없는 상태입니다: {[n for n, _ in cannot_analyze_agents]}")
        error_summary = "### ⚠️ 분석 진행 중단 (정보 부족 및 분석 불가)\n\n"
        error_summary += "에이전트가 단서를 찾지 못했거나, 제공된 텍스트 정보만으로는 분석할 수 없어 작업을 중단했습니다.\n"
        error_summary += "오픈서치 검색 결과가 없거나, 추가적인 에러 로그/텍스트 힌트가 필요할 수 있습니다.\n\n"
        for name, res in cannot_analyze_agents:
            error_summary += f"#### 🔴 {name} 분석 상태\n{res}\n\n"
            
        agent_reports = {}
        for a_name, a_res in agent_results:
            agent_id = a_name
            for a in available_agents:
                if isinstance(a, dict) and a.get("name") == a_name:
                    agent_id = a.get("id") or a_name
                    break
            agent_reports[agent_id] = {
                "result": a_res,
                "result_html": convert_markdown_to_html(a_res, title=f"AI Analyst Report - {a_name}")
            }
            
        auto_status["step"] = "completed"
        auto_status["message"] = "⚠️ 정보 부족 또는 분석 불가로 작업을 즉시 중단했습니다."
        
        response_html = convert_markdown_to_html(error_summary, title="Orchestration Aborted")
        
        # 중단 시에도 결과 파일을 OneDrive 및 로컬에 저장
        try:
            target_dir = os.path.join(os.getcwd(), "artifacts", "reports")
            os.makedirs(target_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_file_name = f"aborted_report_{jira_key or timestamp}.md"
            target_file = os.path.join(target_dir, target_file_name)
            
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(error_summary)
            
            onedrive_base = r"C:\Users\LEEJAEJUN\OneDrive - GS Retail Co., Ltd"
            if os.path.exists(onedrive_base):
                onedrive_report_dir = os.path.join(onedrive_base, "AI_Reports")
                os.makedirs(onedrive_report_dir, exist_ok=True)
                
                # 파일명 결정 (Power Automate가 감지하는 방식: _결과.txt)
                od_file_name = f"{jira_key}_에러결과.txt" if jira_key else f"에러리포트_{datetime.now().strftime('%H%M%S')}_결과.txt"
                onedrive_file_path = os.path.join(onedrive_report_dir, od_file_name)
                
                with open(onedrive_file_path, "w", encoding="utf-8") as f:
                    f.write(error_summary)
                print(f"💾 [OneDrive Sync] 중단 리포트 파워 오토메이트 감지용 원드라이브 복사 완료 -> {onedrive_file_path}")
        except Exception as file_err:
            print(f"🔴 보고서 파일 저장 실패: {file_err}")

        return {
            "status": "success",
            "message": "분석 불가 상황이 발생하여 프로세스를 중단했습니다.",
            "result": error_summary,
            "result_html": response_html,
            "agent_reports": agent_reports,
            "token_usage": request_token_usage.get() or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }

    # 상호 피드백(Self-Reflection) 루프 진행
    if use_self_reflection and len(agent_results) > 0:
        # 오류 상태(할당량 초과, 업무 불능 등)인 에이전트는 피드백 대상에서 제외합니다.
        reflection_targets = []
        for name, res in agent_results:
            if "에이전트 업무 불능" in res or "API 호출 한도" in res or "할당량" in res or "Quota" in res:
                print(f"⚠️ [{name}] 에이전트는 오류 상태(업무 불능/할당량 초과 등)이므로 피드백 루프에서 제외합니다.")
                continue
            reflection_targets.append((name, res))
            
        if not reflection_targets:
            print("👔 [팀장] 분석에 성공한 에이전트가 없으므로 피드백 루프를 생략합니다.")
        else:
            print(f"👔 [팀장] 2.5단계: 팀원들의 1차 분석 결과 검토 및 피드백 루프 작동 시작... (대상 에이전트: {[n for n, _ in reflection_targets]})")
            auto_status["step"] = "reflecting"
            auto_status["message"] = "👔 팀장이 팀원들의 1차 분석 결과를 검토하여 보완 피드백을 전달하고 있습니다..."
            
            reflection_prompt = build_leader_reflection_prompt(plan, reflection_targets, jira_info, log_text)
            
            try:
                # 팀장 엔진을 사용하여 피드백 생성
                if leader_model == "claude-cli":
                    reflection_raw = await call_claude_cli_async(reflection_prompt, role="backend")
                else:
                    reflection_raw = await call_gemini_async(gemini_client, leader_model, reflection_prompt)
                    
                # JSON 파싱 시도 (백틱 등 불필요 문자 청소)
                clean_json_str = reflection_raw.strip()
                if clean_json_str.startswith("```json"):
                    clean_json_str = clean_json_str[7:]
                if clean_json_str.endswith("```"):
                    clean_json_str = clean_json_str[:-3]
                clean_json_str = clean_json_str.strip()
                
                feedback_data = json.loads(clean_json_str)
                print(f"📋 [팀장 피드백 파싱 완료] {feedback_data}")
                
                # 피드백이 있는 에이전트들에 대해 2차 분석 실행
                revision_tasks = []
                for a in assignments:
                    agent_name = a["agent_name"]
                    agent_res_entry = next((item for item in agent_results if item[0] == agent_name), None)
                    
                    # 오류 상태인 에이전트는 피드백 제외 (사용자 요구 반영)
                    if agent_res_entry and ("에이전트 업무 불능" in agent_res_entry[1] or "API 호출 한도" in agent_res_entry[1] or "할당량" in agent_res_entry[1] or "Quota" in agent_res_entry[1]):
                        print(f"⚠️ [{agent_name}] 에이전트는 오류 상태이므로 피드백 루프에서 제외합니다.")
                        continue
                        
                    agent_feedback = feedback_data.get(agent_name, {})
                    if agent_feedback.get("needs_revision") and agent_feedback.get("feedback"):
                        fb_text = agent_feedback["feedback"]
                        print(f"🔄 [{agent_name}] 피드백 감지됨 → 2차 보완 분석 요청: {fb_text}")
                        revision_tasks.append((agent_name, analyze_auto_agent(a, feedback=fb_text)))
                
                if revision_tasks:
                    auto_status["message"] = f"🔄 보완이 필요한 {len(revision_tasks)}명의 팀원이 2차 보완 분석을 진행 중입니다..."
                    results_2nd = await asyncio.gather(*[t[1] for t in revision_tasks])
                    
                    # 기존 1차 결과를 2차 보완 결과로 교체
                    for name, new_res in results_2nd:
                        for idx, (orig_name, _) in enumerate(agent_results):
                            if orig_name == name:
                                agent_results[idx] = (name, new_res)
                                print(f"✅ [{name}] 2차 보완 분석 리포트 반영 완료!")
                else:
                    print("👔 [팀장] 모든 결과가 만족스럽습니다. 보완이 필요한 에이전트가 없습니다.")
                    
            except Exception as ref_err:
                print(f"🔴 [팀장 피드백 루프] 처리 중 에러 발생 (루프 생략): {ref_err}")

    # 2단계 완료: 팀장 검토/통합 리포트 단계로 진입
    auto_status["step"] = "reviewing"
    auto_status["message"] = "📋 팀장이 팀원들의 결과를 검토하고 최종 통합 리포트를 작성하고 있습니다..."

    # ==============================
    # [3/4단계] 👔 팀장: 검토 + 최종 통합 리포트
    # ==============================
    print("👔 [팀장] 3/4단계: 팀원 결과 검토 및 최종 통합 리포트 작성 중...")
    review_prompt = build_leader_review_prompt(plan, agent_results, jira_info, log_text, generate_pt=generate_pt)

    if leader_model == "claude-cli":
        try:
            final_report = await call_claude_cli_async(review_prompt, role="backend")
        except Exception as cli_err:
            print(f"⚠️ [팀장 3/4단계] Claude CLI 검토/통합 실패 ({cli_err}). Gemini Flash로 자동 폴백합니다.")
            final_report = await call_gemini_async(gemini_client, "gemini-2.5-flash", review_prompt)
    else:
        final_report = await call_gemini_async(gemini_client, leader_model, review_prompt)

    print("✨ [팀장] 최종 통합 리포트 완성!")

    if create_branch and git_log:
        final_report = f"### 🌿 Git 브랜치 생성 결과\n```\n{git_log}\n```\n\n" + final_report

    # 개발 진행
    dev_log = ""
    if run_development:
        all_projects = list(set(p for a in assignments for p in a.get("projects", [])))
        auto_status["step"] = "developing"
        auto_status["message"] = "💻 분석 리포트를 기반으로 에이전트가 자동 코드 개발을 진행하고 있습니다..."
        dev_log = await run_development_agents(all_projects, final_report, jira_info, log_text, use_verify_loop=use_verify_loop)
        
    if run_development and dev_log:
        final_report += f"\n\n---\n\n### 💻 자동 개발 진행 결과\n{dev_log}"

    # 보고서 파일 저장
    try:
        today_str = datetime.now().strftime("%Y%m%d")
        file_name = f"{jira_key}_AUTO리포트.md" if jira_key else f"AUTO리포트_{datetime.now().strftime('%H%M%S')}.md"
        all_projects = list(set(p for a in assignments for p in a.get("projects", [])))
        for proj in all_projects:
            if "db_meta" in proj:
                continue
            target_dir = f"../{proj}/report/{today_str}"
            os.makedirs(target_dir, exist_ok=True)
            target_file = f"{target_dir}/{file_name}"
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(final_report)
            
            # HTML 파일 저장
            file_name_html = file_name.replace(".md", ".html")
            target_file_html = f"{target_dir}/{file_name_html}"
            html_text = convert_markdown_to_html(final_report, title=f"AI Orchestrator Report - {jira_key or 'AUTO리포트'}")
            with open(target_file_html, "w", encoding="utf-8") as f:
                f.write(html_text)

            print(f"💾 [{proj}] 자동 리포트 저장 → {target_file} & {target_file_html}")

        # ④ 윈도우 원드라이브 경로가 존재할 경우, 파워오토메이트 감지용 폴더에도 복사 저장
        onedrive_base = r"C:\Users\LEEJAEJUN\OneDrive - GS Retail Co., Ltd"
        if os.path.exists(onedrive_base):
            onedrive_report_dir = os.path.join(onedrive_base, "AI_Reports")
            os.makedirs(onedrive_report_dir, exist_ok=True)
            
            # 파일명 결정
            od_file_name = f"{jira_key}_결과.txt" if jira_key else f"일반리포트_{datetime.now().strftime('%H%M%S')}_결과.txt"
            onedrive_file_path = os.path.join(onedrive_report_dir, od_file_name)
            
            with open(onedrive_file_path, "w", encoding="utf-8") as f:
                f.write(final_report)
            print(f"💾 [OneDrive Sync] 파워 오토메이트 감지용 원드라이브 폴더 복사 완료 -> {onedrive_file_path}")

    except Exception as file_err:
        print(f"🔴 보고서 파일 저장 실패: {file_err}")

    # 각 에이전트의 개별 분석 보고서 수집
    agent_reports = {}
    for name, res in agent_results:
        agent_id = None
        for a in available_agents:
            if a.get("name") == name:
                agent_id = a.get("id")
                break
        if not agent_id:
            agent_id = name
        res_html = convert_markdown_to_html(res, title=f"AI Analyst Report - {name}")
        agent_reports[agent_id] = {
            "result": res,
            "result_html": res_html
        }

    # 4단계 완료: 성공적으로 완료되었음을 마킹
    auto_status["step"] = "completed"
    auto_status["message"] = "✨ 최종 통합 리포트 작성이 완료되었습니다!"

    usage = request_token_usage.get() or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    response_html = convert_markdown_to_html(final_report, title=f"AI Orchestrator Report - {jira_key or 'AUTO리포트'}")
    
    auto_status["result"] = final_report
    auto_status["result_html"] = response_html
    auto_status["agent_reports"] = agent_reports
    auto_status["token_usage"] = usage

    # PT 자동 생성
    pt_download_url = None
    if generate_pt:
        filename = f"pt_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        try:
            pt_download_url = create_pptx_from_text(final_report, filename)
        except Exception as e:
            print(f"⚠️ PPTX 생성 실패: {e}")
            
    if pt_download_url:
        auto_status["pt_download_url"] = pt_download_url

    usage = request_token_usage.get() or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    response_html = convert_markdown_to_html(final_report, title=f"AI Orchestrator Report - {jira_key or 'AUTO리포트'}")
    
    return_data = {
        "status": "success",
        "result": final_report,
        "result_html": response_html,
        "plan": plan,
        "agent_reports": agent_reports,
        "token_usage": usage
    }
    if pt_download_url:
        return_data["pt_download_url"] = pt_download_url
        
    return return_data

# --- [🤖 AUTO 오케스트레이션 API (팀장 자동 배정 모드)] ---
@app.post("/api/v1/orchestrate/auto")
async def process_auto_orchestration(request: Request):
    """팀장이 자동으로 에이전트를 배정하고 결과를 검토하는 4단계 파이프라인"""
    try:
        req_data = await request.json()

        jira_key = req_data.get("jira_key") or req_data.get("jiraKey")
        log_text = req_data.get("log_text") or req_data.get("text") or ""
        log_images = req_data.get("log_images", [])
        available_agents = req_data.get("available_agents", [])
        available_projects = req_data.get("available_projects", [])
        leader_engine = req_data.get("leader_engine", "Claude-CLI")

        run_development = req_data.get("run_development") or req_data.get("runDevelopment") or False
        create_branch = req_data.get("create_branch") or req_data.get("createBranch") or False
        use_self_reflection = req_data.get("use_self_reflection") or req_data.get("useSelfReflection") or False
        use_verify_loop = req_data.get("use_verify_loop") or req_data.get("useVerifyLoop") or False
        orchestration_mode = req_data.get("orchestration_mode", "parallel")
        generate_pt = req_data.get("generate_pt") or req_data.get("generatePt") or False

        result_data = await run_auto_orchestration_core(
            jira_key=jira_key,
            log_text=log_text,
            log_images=log_images,
            available_agents=available_agents,
            available_projects=available_projects,
            leader_engine=leader_engine,
            create_branch=create_branch,
            run_development=run_development,
            use_self_reflection=use_self_reflection,
            use_verify_loop=use_verify_loop,
            orchestration_mode=orchestration_mode,
            generate_pt=generate_pt
        )
        return result_data

    except Exception as e:
        print(f"🔴 [Auto 오케스트레이터] 에러 발생: {e}")
        global auto_status
        auto_status["step"] = "error"
        auto_status["message"] = f"❌ 오류 발생: {str(e)}"
        raise HTTPException(status_code=500, detail=str(e))


# --- [💬 Microsoft Teams Outgoing Webhook 연동 API] ---
@app.post("/api/v1/teams/webhook")
async def teams_webhook(request: Request):
    try:
        req_data = await request.json()
        print(f"🔍 [DEBUG Teams Webhook Raw Body]: {req_data}")
        raw_text = req_data.get("text") or ""
        
        # HTML 태그 제거 및 트림 (@mentions 등 제거)
        clean_text = re.sub(r'<[^>]*>', '', raw_text).strip()
        # '@AI ' 멘션 접두사 제거
        clean_text = re.sub(r'^@AI\s*', '', clean_text).strip()
        clean_text = re.sub(r'^@\w+\s*', '', clean_text).strip()
        
        # 지라 키 추출 (예: GRIT-2309522)
        jira_match = re.search(r'([A-Za-z0-9]+-\d+)', clean_text)
        jira_key = jira_match.group(1) if jira_match else None
        
        # 이미지 첨부파일 추출 및 base64 변환
        log_images = []
        attachments = req_data.get("attachments") or []
        for att in attachments:
            content_type = att.get("contentType", "")
            content_url = att.get("contentUrl", "")
            
            if content_url and content_url.startswith("data:image/"):
                log_images.append(content_url)
            elif content_type and "image/" in content_type and content_url:
                try:
                    # 외부 URL 이미지 다운로드 (User-Agent 헤더 추가 및 타임아웃 조정)
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                    loop = asyncio.get_event_loop()
                    resp = await loop.run_in_executor(
                        None,
                        lambda: requests.get(content_url, headers=headers, timeout=10)
                    )
                    if resp.status_code == 200:
                        b64_data = base64.b64encode(resp.content).decode("utf-8")
                        log_images.append(f"data:{content_type};base64,{b64_data}")
                except Exception as img_err:
                    print(f"⚠️ Teams Webhook 이미지 다운로드 실패: {img_err}")
        
        # 🌿 Teams 메시지 본문에서 신규 브랜치 및 개발 진행 옵션 파싱 (예: 브랜치생성 O, 개발진행 X, 혹은 브랜치생성:O, 개발진행/O)
        create_branch = False
        run_development = False

        # 공백(space), 콜론(:), 슬래시(/), 대시(-) 등 기호를 유연하게 매칭하도록 [\s:=/-]* 로 개선
        if re.search(r'(브랜치|branch)[\s:=/-]*(생성)?[\s:=/-]*(o|ㅇ|yes|y|켜기|true|1)', clean_text, re.IGNORECASE):
            create_branch = True
        if re.search(r'(개발|dev|development)[\s:=/-]*(진행)?[\s:=/-]*(o|ㅇ|yes|y|켜기|true|1)', clean_text, re.IGNORECASE):
            run_development = True

        print(f"💬 [Teams Webhook] 메시지 수신: {clean_text} (Jira: {jira_key}, 브랜치: {create_branch}, 개발: {run_development}, 이미지 첨부: {log_images}개)")
        
        # 코어 오케스트레이션 파이프라인 구동 (기본값 설정 사용)
        result_data = await run_auto_orchestration_core(
            jira_key=jira_key,
            log_text=clean_text,
            log_images=log_images,
            available_agents=DEFAULT_AGENTS,
            available_projects=DEFAULT_PROJECTS,
            leader_engine="Gemini-Flash",
            create_branch=create_branch,
            run_development=run_development
        )
        
        final_md = result_data.get("result", "")
        response_text = f"### 👔 팀장 자동 배정 분석 완료\n\n{final_md}"
        
        # UI 업데이트용 데이터도 실어줌 (시뮬레이터 연동 및 Teams 호환 응답)
        return {
            "type": "message",
            "text": response_text,
            # 시뮬레이터에서 처리하기 쉽도록 내부 결과 정보도 응답에 살짝 얹어둡니다.
            "result_data": result_data
        }
        
    except Exception as e:
        print(f"🔴 Teams Webhook 에러: {e}")
        return {
            "type": "message",
            "text": f"❌ Teams 자동 분석 중 에러가 발생했습니다:\n`{str(e)}`"
        }


# --- [🔥 Email Cloud Relay Polling 백그라운드 태스크] ---
def send_email_reply(to_email: str, subject: str, body_text: str):
    """SMTP를 사용해 결과 메일을 발송합니다 (동기 함수)."""
    relay_email = os.getenv("RELAY_EMAIL", "").strip()
    email_password = os.getenv("EMAIL_PASSWORD", "").strip()
    
    if not relay_email or "YOUR_16_DIGIT" in email_password or not email_password:
        print("⚠️ [Email SMTP] 메일 설정이 완료되지 않아 답장 메일을 보내지 않습니다.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = relay_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(relay_email, email_password)
        server.sendmail(relay_email, to_email, msg.as_string())
        server.quit()
        print(f"📧 [Email SMTP] 답장 발송 성공 -> {to_email} (제목: {subject})")
    except Exception as e:
        print(f"🔴 [Email SMTP] 답장 메일 발송 에러: {e}")


async def run_orchestration_from_email(teams_message_id: str, jira_key: str, create_branch: bool, run_development: bool, clean_text: str, reply_to_email: str):
    """이메일로 수신된 명령 기반 오케스트레이션을 실행하고 최종 결과를 이메일 답장 또는 웹훅으로 전송합니다."""
    loop = asyncio.get_event_loop()
    try:
        print(f"🚀 [Email Core] 오케스트레이터 구동 시작 (Jira: {jira_key}, 브랜치: {create_branch}, 개발: {run_development}, 회신처: {reply_to_email})")
        
        # 코어 오케스트레이션 실행
        result_data = await run_auto_orchestration_core(
            jira_key=jira_key,
            log_text=clean_text,
            log_images=[],  # 메일은 텍스트 명령 위주로 처리
            available_agents=DEFAULT_AGENTS,
            available_projects=DEFAULT_PROJECTS,
            leader_engine="Gemini-Flash",
            create_branch=create_branch,
            run_development=run_development
        )
        
        final_md = result_data.get("result", "")
        response_text = f"### 👔 팀장 자동 배정 분석 완료\n\n{final_md}"
        
        reply_subject = f"Re: [AI_CMD] <{teams_message_id}> 결과리포트"
        
        # 1. 윈도우 SMTP 방화벽 차단 우회를 위한 Webhook 우선 처리
        webhook_url = os.getenv("TEAMS_WEBHOOK_URL", "").strip()
        if webhook_url:
            try:
                print(f"🔗 [Teams Webhook] Webhook URL 감지됨. Teams로 결과 직접 전송 시도...")
                payload = {
                    "teams_message_id": teams_message_id,
                    "subject": reply_subject,
                    "body": response_text
                }
                resp = requests.post(webhook_url, json=payload, timeout=10)
                if resp.status_code in [200, 201, 202]:
                    print(f"✅ [Teams Webhook] Webhook 전송 성공! (HTTP {resp.status_code})")
                    return
                else:
                    print(f"⚠️ [Teams Webhook] Webhook 전송 실패 (HTTP {resp.status_code}): {resp.text}")
            except Exception as web_err:
                print(f"🔴 [Teams Webhook] Webhook 전송 중 에러 발생: {web_err}")
        
        # 2. Webhook 전송 안됨/실패 시 이메일(Power Automate Fallback) 전송
        print(f"📧 [Email Core] Webhook 전송을 생략했거나 실패했습니다. 이메일 답장(Fallback)을 시도합니다.")
        send_email_reply(reply_to_email, reply_subject, response_text)
        print(f"✅ [Email Core] 오케스트레이터 수행 완료! (Message ID: {teams_message_id})")
        
    except Exception as err:
        print(f"🔴 [Email Core] 처리 중 에러 발생: {err}")
        reply_subject = f"Re: [AI_CMD] <{teams_message_id}> 에러발생"
        err_msg = f"❌ 분석 중 에러가 발생했습니다:\n{str(err)}"
        
        webhook_url = os.getenv("TEAMS_WEBHOOK_URL", "").strip()
        if webhook_url:
            try:
                payload = {
                    "teams_message_id": teams_message_id,
                    "subject": reply_subject,
                    "body": err_msg
                }
                requests.post(webhook_url, json=payload, timeout=10)
                return
            except Exception as web_err:
                print(f"🔴 [Teams Webhook] 에러 Webhook 발송 실패: {web_err}")


async def email_polling_daemon():
    """Gmail 사서함을 주기적으로 폴링하여 [AI_CMD] 제목의 읽지 않은 메일을 수집하고 처리합니다."""
    relay_email = os.getenv("RELAY_EMAIL", "").strip()
    email_password = os.getenv("EMAIL_PASSWORD", "").strip()
    
    if not relay_email or "YOUR_16_DIGIT" in email_password or not email_password:
        print("⚠️ [Email Polling] RELAY_EMAIL 또는 EMAIL_PASSWORD가 설정되지 않았거나 기본값입니다. 폴링 데몬을 대기합니다.")
        return
        
    print(f"🔥 [Email Polling] 이메일 폴링 데몬 기동 시작 (계정: {relay_email})")
    loop = asyncio.get_event_loop()
    
    while True:
        try:
            await asyncio.sleep(5)
            
            # IMAP 연결 및 로그인 (동기 라이브러리이므로 executor 사용)
            def poll_emails():
                mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
                mail.login(relay_email, email_password)
                mail.select("inbox")
                
                # 읽지 않은 [AI_CMD] 제목 메일 검색
                status, data = mail.search(None, '(UNSEEN SUBJECT "[AI_CMD]")')
                if status != 'OK' or not data[0]:
                    mail.close()
                    mail.logout()
                    return []
                    
                messages = []
                for num in data[0].split():
                    # 메일 상세 조회
                    res_status, msg_data = mail.fetch(num, '(RFC822)')
                    if res_status != 'OK':
                        continue
                        
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # 제목 디코딩
                    subject = ""
                    raw_subject = msg['Subject']
                    if raw_subject:
                        decoded = decode_header(raw_subject)
                        for sub, encoding in decoded:
                            if isinstance(sub, bytes):
                                subject += sub.decode(encoding or 'utf-8', errors='replace')
                            else:
                                subject += sub
                                
                    # 즉시 읽음 마크 처리 (중복 실행 방지)
                    mail.store(num, '+FLAGS', '\\Seen')
                    
                    # 보낸 사람 이메일 주소 추출
                    from_header = msg.get('From', '')
                    _, from_email = email.utils.parseaddr(from_header)
                    if not from_email:
                        from_email = relay_email
                        
                    messages.append((subject, from_email))
                    
                mail.close()
                mail.logout()
                return messages

            new_emails = await loop.run_in_executor(None, poll_emails)
            for subject, from_email in new_emails:
                print(f"🔥 [Email Polling] 새 명령 메일 발견: {subject} (발신자: {from_email})")
                
                # 제목에서 매개변수 파싱: [AI_CMD] <teams_message_id> GRIT-XXXXXX 브랜치생성 O / 개발진행 O
                # teams_message_id 추출
                msg_id_match = re.search(r'<([^>]+)>', subject)
                teams_message_id = msg_id_match.group(1) if msg_id_match else "unknown"
                
                # 지라 키 추출 (예: GRIT-2309522)
                jira_match = re.search(r'([A-Za-z0-9]+-\d+)', subject)
                jira_key = jira_match.group(1) if jira_match else None
                
                # 옵션 파싱
                create_branch = False
                run_development = False
                
                if re.search(r'(브랜치|branch)[\s:=/-]*(생성)?[\s:=/-]*(o|ㅇ|yes|y|켜기|true|1)', subject, re.IGNORECASE):
                    create_branch = True
                if re.search(r'(개발|dev|development)[\s:=/-]*(진행)?[\s:=/-]*(o|ㅇ|yes|y|켜기|true|1)', subject, re.IGNORECASE):
                    run_development = True
                    
                # 비동기로 오케스트레이션 구동 (비차단)
                asyncio.create_task(run_orchestration_from_email(
                    teams_message_id=teams_message_id,
                    jira_key=jira_key,
                    create_branch=create_branch,
                    run_development=run_development,
                    clean_text=subject,
                    reply_to_email=from_email
                ))
                    
        except Exception as e:
            print(f"🔴 [Email Polling] 데몬 루프 중 에러 발생: {e}")


@app.on_event("startup")
async def startup_event():
    # 백그라운드 이메일 폴링 데몬 기동
    asyncio.create_task(email_polling_daemon())
