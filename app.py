import streamlit as st
import ssl
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime

# 設定網頁頁面資訊
st.set_page_config(page_title="碩士論文文獻研究助手", page_icon="🎓", layout="wide")

ssl._create_default_https_context = ssl._create_unverified_context
CURRENT_YEAR = datetime.now().year

# 跨領域通用學術專有名詞字典（可持續擴充）
TRANSLATE_MAP = {
    # 資訊與 AI 領域 (避免與教育學深度學習混淆)
    "深度學習": "deep learning neural network",
    "機器學習": "machine learning algorithm",
    "生成式人工智慧": "generative artificial intelligence llm",
    "人工智慧": "artificial intelligence",
    "AI": "artificial intelligence",
    "強化學習": "reinforcement learning",
    "電腦視覺": "computer vision",
    "自然語言處理": "natural language processing nlp",
    "區塊鏈": "blockchain smart contract",
    "零知識證明": "zero knowledge proof",
    
    # 財金與經濟領域
    "股價崩盤風險": "stock price crash risk",
    "崩盤風險": "crash risk",
    "涉入程度": "adoption level involvement",
    "永續金融": "sustainable finance esg",
    "轉型融資": "transition finance decarbonization",
    "公司治理": "corporate governance",
    "資訊透明度": "information transparency",
    
    # 社會與管理領域
    "外送員": "food delivery riders courier",
    "勞動過程": "labor process control",
    "平台資本主義": "platform capitalism algorithm",
    "演算法控制": "algorithmic control management"
}

def translate_to_english(topic: str) -> str:
    # 1. 提取已有英文
    en_words = re.findall(r'[a-zA-Z0-9]+', topic)
    
    # 2. 精準匹配專業詞庫
    translated_keywords = []
    sorted_keys = sorted(TRANSLATE_MAP.keys(), key=len, reverse=True)
    
    temp_topic = topic
    for zh in sorted_keys:
        if zh in temp_topic:
            translated_keywords.append(TRANSLATE_MAP[zh])
            temp_topic = temp_topic.replace(zh, "")
            
    # 3. 清理剩餘中文無效字詞（去除連接詞、助詞）
    clean_remains = re.sub(r'[之與的關聯影響及在應用與之研究與分析基於對]', ' ', temp_topic).strip()
    
    all_keywords = translated_keywords + en_words
    if clean_remains:
        all_keywords.append(clean_remains)
        
    final_query = " ".join(all_keywords).strip()
    return final_query if final_query else topic

def generate_easy_outline(abstract_text):
    if not abstract_text or "文獻提供" in abstract_text or len(abstract_text) < 30:
        return ["摘要資訊較少，建議直接點擊 DOI 開啟全文觀看。"]
    sentences = [s.strip() for s in re.split(r'[.!?。；]', abstract_text) if len(s.strip()) > 10]
    outline = []
    if len(sentences) >= 1: outline.append(f"🎯 研究核心：{sentences[0]}")
    if len(sentences) >= 2: outline.append(f"🛠 方法/視角：{sentences[1]}")
    if len(sentences) >= 3: outline.append(f"💡 主要結論：{sentences[2]}")
    return outline

@st.cache_data(ttl=3600, show_spinner=False)
def search_crossref(query: str, lang_filter: str = "all", year_choice: str = "4", limit: int = 5):
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.crossref.org/works?query={encoded_query}&rows=25&sort=relevance"
    headers = {'User-Agent': 'AcademicPaperSearchWeb/6.0'}
    
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
    except Exception:
        return []

# --- 網頁 session 管理 ---
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'primary_results' not in st.session_state:
    st.session_state.primary_results = []
if 'search_title' not in st.session_state:
    st.session_state.search_title = ""
if 'primary_title' not in st.session_state:
    st.session_state.primary_title = ""
if 'is_extended' not in st.session_state:
    st.session_state.is_extended = False

# --- 網頁介面 ---
st.title("🎓 碩士論文文獻研究助手 (Web 版)")
st.caption("協助研究生打破資訊盲區、梳理理論脈絡，快速進行 Literature Review")

# 側邊欄設定
st.sidebar.header("⚙️️ 搜尋條件設定")
lang_option = st.sidebar.selectbox("🌐 論文語言類型", ["1. 不限 (中英文混合)", "2. 僅英文論文 (English Only)", "3. 僅中文論文 (Chinese Only)"])
year_option = st.sidebar.selectbox("📅 出版年份範圍", ["4. 不限年份", "1. 近 5 年文獻 (2021-2026)", "2. 近 10 年文獻 (2016-2026)", "3. 10 年以上經典文獻 (< 2016)"])

lang_map = {"1. 不限 (中英文混合)": "all", "2. 僅英文論文 (English Only)": "en", "3. 僅中文論文 (Chinese Only)": "zh"}
year_map = {"4. 不限年份": "4", "1. 近 5 年文獻 (2021-2026)": "1", "2. 近 10 年文獻 (2016-2026)": "2", "3. 10 年以上經典文獻 (< 2016)": "3"}

# 搜尋列
topic = st.text_input("請輸入【研究題目 / 核心主題】：", placeholder="例如：深度學習在影像辨識之應用")

if st.button("🚀 開始檢索並構建文獻組", type="primary") and topic:
    with st.spinner("🔍 正在檢索 Crossref 全球學術資料庫中..."):
        query = translate_to_english(topic)
        st.info(f"💡 系統自動轉化學術 Query：`{query}`")
        
        papers = search_crossref(query, lang_filter=lang_map[lang_option], year_choice=year_map[year_option], limit=5)
        if not papers:
            papers = search_crossref(topic, lang_filter="all", year_choice="4", limit=5)
            
        st.session_state.search_results = papers
        st.session_state.primary_results = papers
        st.session_state.search_title = f"核心主題：「{topic}」"
        st.session_state.primary_title = f"核心主題：「{topic}」"
        st.session_state.is_extended = False

# 顯示搜尋結果與返回按鈕
if st.session_state.search_results:
    st.markdown("---")
    
    if st.session_state.is_extended:
        col_title, col_back = st.columns([3, 1])
        with col_title:
            st.subheader(f"🔍 {st.session_state.search_title}")
        with col_back:
            if st.button("🔙 返回原始核心文獻組", type="secondary"):
                st.session_state.search_results = st.session_state.primary_results
                st.session_state.search_title = st.session_state.primary_title
                st.session_state.is_extended = False
                st.rerun()
    else:
        st.subheader(f"📚 {st.session_state.search_title}")
    
    for idx, p in enumerate(st.session_state.search_results, 1):
        with st.expander(f"📌 [{idx}] {p['title']} ({p['year']})", expanded=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**👤 作者**：{p['author']} | **📅 年份**：{p['year']}")
                st.markdown(f"**📖 APA 引用**：`{p['apa']}`")
                st.markdown("---")
                st.markdown("**💡 3秒淺顯易懂大綱 (Quick Summary)：**")
                for line in p['outline']:
                    st.write(f"- {line}")
                
                st.markdown("---")
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button(f"↔️ 橫向搜尋 (同類相似文獻)", key=f"sh_{idx}"):
                        with st.spinner("🔄 正在尋找同主題延伸論文..."):
                            sim_papers = search_crossref(p['title'], lang_filter="all", year_choice="4", limit=5)
                            if sim_papers:
                                st.session_state.search_results = sim_papers
                                st.session_state.search_title = f"橫向延伸搜尋: {p['title'][:25]}..."
                                st.session_state.is_extended = True
                                st.rerun()
                            else:
                                st.warning("未找到相關橫向文獻。")
                                
                with btn_col2:
                    if st.button(f"↕️️ 縱向脈絡 (溯源10年經典)", key=f"sv_{idx}"):
                        with st.spinner("📜 正在回溯理論起源與經典基石文獻..."):
                            origin_papers = search_crossref(p['title'], lang_filter="all", year_choice="3", limit=5)
                            if origin_papers:
                                st.session_state.search_results = origin_papers
                                st.session_state.search_title = f"縱向源頭脈絡: {p['title'][:25]}..."
                                st.session_state.is_extended = True
                                st.rerun()
                            else:
                                st.warning("未找到 10 年以上相關經典文獻。")

            with col2:
                if p['url']:
                    st.link_button("🌐 開啟全文網頁/DOI", p['url'])
                st.code(p['bibtex'], language="latex")

st.markdown("---")
st.caption("💡 提示：連接校園網路 / VPN 後點擊「開啟全文網頁/DOI」，即可直接享受學校資料庫的全文下載權限！")
