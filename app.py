import streamlit as st
import ssl
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime

# 設定網頁標題與寬螢幕佈局
st.set_page_config(page_title="碩士論文文獻研究助手", page_icon="🎓", layout="wide")

ssl._create_default_https_context = ssl._create_unverified_context
CURRENT_YEAR = datetime.now().year

TRANSLATE_MAP = {
    "零知識證明": "zero knowledge proof",
    "去中心化": "decentralized",
    "身分驗證": "identity authentication",
    "隱私保護": "privacy protection",
    "永續金融": "sustainable finance",
    "國際投資法": "international investment law",
    "適法性": "legality compliance",
    "分類標準": "taxonomy",
    "重工業": "heavy industry",
    "去碳化": "decarbonization",
    "轉型融資": "transition finance",
    "人工智慧": "artificial intelligence",
    "機器學習": "machine learning",
    "區塊鏈": "blockchain",
    "外送員": "food delivery riders courier",
    "勞動過程": "labor process"
}

def translate_to_english(topic: str) -> str:
    if len(re.findall(r'[a-zA-Z]', topic)) > len(topic) * 0.4:
        clean_text = re.sub(r'[^\w\s]', ' ', topic)
        return " ".join(clean_text.split()[:6])
    
    translated_keywords = [en for zh, en in TRANSLATE_MAP.items() if zh in topic]
    return " ".join(translated_keywords) if translated_keywords else re.sub(r'[^\w\s\u4e00-\u9fa5]', ' ', topic).strip()

def generate_easy_outline(abstract_text):
    if not abstract_text or "文獻提供" in abstract_text or len(abstract_text) < 30:
        return ["摘要資訊較少，建議直接點擊 DOI 開啟全文觀看。"]
    sentences = [s.strip() for s in re.split(r'[.!?。；]', abstract_text) if len(s.strip()) > 10]
    outline = []
    if len(sentences) >= 1: outline.append(f"🎯 研究核心：{sentences[0]}")
    if len(sentences) >= 2: outline.append(f"🛠️️ 方法/視角：{sentences[1]}")
    if len(sentences) >= 3: outline.append(f"💡 主要結論：{sentences[2]}")
    return outline

def search_crossref(query: str, lang_filter: str = "all", year_choice: str = "4", limit: int = 5):
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.crossref.org/works?query={encoded_query}&rows=20&sort=relevance"
    headers = {'User-Agent': 'AcademicPaperSearchWeb/1.0'}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            items = data.get('message', {}).get('items', [])
            
            papers = []
            for item in items:
                title = item.get('title', ['無標題'])[0] if item.get('title') else '無標題'
                has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', title))
                if lang_filter == "en" and has_chinese: continue
                elif lang_filter == "zh" and not has_chinese: continue

                year = item.get('published-print', {}).get('date-parts', [[ '未知' ]])[0][0]
                if year == '未知': year = item.get('published-online', {}).get('date-parts', [[ '未知' ]])[0][0]
                
                try:
                    y = int(year)
                    if year_choice == '1' and y < (CURRENT_YEAR - 5): continue
                    elif year_choice == '2' and y < (CURRENT_YEAR - 10): continue
                    elif year_choice == '3' and y >= (CURRENT_YEAR - 10): continue
                except: pass

                authors_list = item.get('author', [])
                author_names = [f"{a.get('family', '')}, {a.get('given', '')[0]}." if a.get('given') else a.get('family', '') for a in authors_list if a.get('family')]
                author_str = ", ".join(author_names[:3]) + (" et al." if len(author_names) > 3 else "") or "Unknown Author"

                container_title = item.get('container-title', [''])[0]
                doi = item.get('DOI', '')
                url_link = item.get('URL', f"https://doi.org/{doi}" if doi else "")
                
                abstract = re.sub(r'<[^>]+>', '', item.get('abstract', ''))
                outline = generate_easy_outline(abstract)
                cite_key = f"{author_names[0].split(',')[0] if author_names else 'paper'}{year}"
                bibtex = f"@article{{{cite_key},\n  title={{{title}}},\n  author={{{author_str}}},\n  journal={{{container_title}}},\n  year={{{year}}},\n  doi={{{doi}}}\n}}"

                papers.append({
                    "title": title, "author": author_str, "year": year, "doi": doi,
                    "url": url_link, "abstract": abstract[:250], "outline": outline,
                    "bibtex": bibtex, "apa": f"{author_str} ({year}). {title}. https://doi.org/{doi}" if doi else title
                })
                if len(papers) >= limit: break
            return papers
    except Exception as e:
        return []

# --- 網頁介面渲染 ---
st.title("🎓 碩士論文文獻研究助手 (Web 版)")
st.caption("協助研究生打破資訊盲區、梳理理論脈絡，快速進行 Literature Review")

# 側邊欄設定
st.sidebar.header("⚙️ 搜尋條件設定")
lang_option = st.sidebar.selectbox("🌐 論文語言類型", ["1. 不限 (中英文混合)", "2. 僅英文論文 (English Only)", "3. 仅中文論文 (Chinese Only)"])
year_option = st.sidebar.selectbox("📅 出版年份範圍", ["4. 不限年份", "1. 近 5 年文獻 (2021-2026)", "2. 近 10 年文獻 (2016-2026)", "3. 10 年以上經典文獻 (< 2016)"])

lang_map = {"1. 不限 (中英文混合)": "all", "2. 僅英文論文 (English Only)": "en", "3. 仅中文論文 (Chinese Only)": "zh"}
year_map = {"4. 不限年份": "4", "1. 近 5 年文獻 (2021-2026)": "1", "2. 近 10 年文獻 (2016-2026)": "2", "3. 10 年以上經典文獻 (< 2016)": "3"}

# 主搜尋輸入
topic = st.text_input("請輸入【研究題目 / 核心主題】：", placeholder="例如：生成式人工智慧在金融風險預測與法規合規之應用與挑戰")

if st.button("🚀 開始檢索並構建文獻組", type="primary") and topic:
    with st.spinner("🔍 正在檢索 Crossref 全球學術資料庫中..."):
        query = translate_to_english(topic)
        papers = search_crossref(query, lang_filter=lang_map[lang_option], year_choice=year_map[year_option], limit=5)
        
        if not papers:
            papers = search_crossref(topic, lang_filter="all", year_choice="4", limit=5)
            
        if papers:
            st.success(f"✅ 成功找到 5 篇核心文獻組！")
            st.markdown("---")
            
            for idx, p in enumerate(papers, 1):
                with st.expander(f"📌 [{idx}] {p['title']} ({p['year']})", expanded=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**👤 作者**：{p['author']} | **📅 年份**：{p['year']}")
                        st.markdown(f"**📖 APA 引用**：`{p['apa']}`")
                        st.markdown("---")
                        st.markdown("**💡 3秒淺顯易懂大綱 (Quick Summary)：**")
                        for line in p['outline']:
                            st.write(f"- {line}")
                    with col2:
                        if p['url']:
                            st.link_button("🌐 開啟全文網頁/DOI", p['url'])
                        st.code(p['bibtex'], language="latex")
        else:
            st.warning("⚠️ 未找到相關論文，請嘗試精簡關鍵字。")

st.markdown("---")
st.caption("💡 提示：連接校園網路 / VPN 後點擊「開啟全文網頁/DOI」，即可直接享受學校資料庫的全文下載權限！")
