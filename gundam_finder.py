import tkinter as tk
from tkinter import ttk, scrolledtext, font
import threading
import queue
import re
import traceback
import ctypes
import sys
import os
import webbrowser
from bs4 import BeautifulSoup

from webdriver_manager.chrome import ChromeDriverManager

from controller.WebSearch import WebSearch
from model.SearchItem import SearchItem
from model.Store import Store


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

STORE_DATA = {
    "서울": {
        "강변점": "301", "금천점": "335", "김포공항점": "441", "삼양점": "316", "서초점": "340",
        "송파점": "322", "양평점": "328", "월드타워점": "334", "중계점": "307", "청량리점": "312",
        "행당역점": "323", "맥스 금천점": "101", "맥스 영등포점": "103",
        "제타플렉스 서울역점": "200", "제타플렉스 잠실점": "302", "토이저러스 양평점": "344",
        "토이저러스 은평점": "343", "토이저러스 제타플렉스": "326", "토이저러스 중계점": "339"
    },
    "경기": {
        "경기양평점": "473", "고양점": "455", "광교점": "463", "토이저러스 광교점": "489",
        "권선점": "458", "김포한강점": "479", "덕소점": "457", "동두천점": "435",
        "롯데몰수지점": "446", "토이저러스 롯데몰수지점": "448", "마석점": "453",
        "상록점": "464", "선부점": "475", "수원점": "462", "시화점": "456",
        "시흥배곧점": "476", "시흥점": "459", "신갈점": "468", "안산점": "415",
        "안성점": "417", "오산점": "410", "의왕점": "409", "이천점": "422",
        "장암점": "430", "주엽점": "403", "천천점": "411", "토이저러스 기흥점": "496",
        "토이저러스 이천점": "492", "토이저러스 파주점": "497", "판교점": "471",
        "평택점": "436", "화정점": "408"
    },
    "인천": {
        "검단점": "433", "계양점": "469", "부평역점": "404", "부평점": "426",
        "삼산점": "418", "송도점": "465", "연수점": "406", "영종도점": "424",
        "청라점": "461", "토이저러스 청라점": "488"
    },
    "강원": {"석사점": "804", "원주점": "801", "춘천점": "802"},
    "충북": {"상당점": "519", "서청주점": "513", "제천점": "509", "청주점": "501", "충주점": "505"},
    "충남": {"당진점": "515", "서산점": "506", "성정점": "507", "아산터미널점": "512", "홍성점": "518"},
    "대전": {"노은점": "516", "대덕점": "508", "서대전점": "504"},
    "경북": {"구미점": "613", "김천점": "647", "포항점": "623"},
    "경남": {
        "거제점": "645", "김해점": "642", "맥스 창원중앙점": "112", "마산점": "607", 
        "삼계점": "639", "시티세븐점": "620", "양덕점": "643", "웅상점": "610", 
        "장유점": "609", "진주점": "648", "진해점": "611", "통영점": "608"
    },
    "대구": {"대구율하점": "629", "토이저러스 대구율하점": "649", "토이저러스 대구죽전점": "664"},
    "부산": {
        "광복점": "655", "동래점": "618", "동부산점": "658", "토이저러스 동부산점": "662",
        "부산점": "626", "사상점": "612", "사하점": "603", "화명점": "605"
    },
    "울산": {"울산점": "601", "진장점": "614"},
    "전북": {
        "군산점": "707", "남원점": "713", "맥스 송천점": "110", 
        "익산점": "702", "전주점": "708", "정읍점": "709"
    },
    "전남": {"나주점": "719", "남악점": "724", "맥스 목포점": "109", "여수점": "705", "여천점": "710"},
    "광주": {"맥스 상무점": "108", "수완점": "715", "토이저러스 수완점": "722", "월드컵점": "706", "첨단점": "704"},
    "제주": {"제주점": "852"}
}


def get_stock_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    result_list = soup.find('body')
    if not result_list:
        return []
    all_products = result_list.find_all('li')
    in_stock_items = []
    for product in all_products:
        popup = product.find('div', class_='layer_popup')
        if not popup:
            continue
        name_tag = popup.find('div', class_='layer-head')
        price_th = popup.find('th', string=re.compile(r'ㆍ\s*가격\s*:'))
        stock_th = popup.find('th', string=re.compile(r'ㆍ\s*재고\s*:'))
        if name_tag and price_th and stock_th:
            name = name_tag.text.strip()
            price = price_th.find_next_sibling('td').text.strip()
            stock = stock_th.find_next_sibling('td').text.strip()
            if stock != '품절':
                in_stock_items.append(SearchItem(name, price, stock))
    return in_stock_items


class GundamStockCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("롯데마트 건담 재고 파인더")
        self.root.geometry("700x750")
        self.root.minsize(600, 500)

        self.web_search = WebSearch()
        
        try:
            icon_path = resource_path("gundam_icon.ico")
            self.root.iconbitmap(icon_path)
        except Exception:
            pass
        self.queue = queue.Queue()
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.X, pady=5, expand=False)
        self.notebook = notebook

        tab1 = ttk.Frame(notebook, padding="10")
        notebook.add(tab1, text="지점별 등급 검색")
        self.create_tab1_widgets(tab1)

        tab2 = ttk.Frame(notebook, padding="10")
        notebook.add(tab2, text="전체 지점 상품 검색")
        self.create_tab2_widgets(tab2)
        
        tab3 = ttk.Frame(notebook, padding="10")
        notebook.add(tab3, text="정보")
        self.create_tab3_widgets(tab3)

        self.start_button = ttk.Button(main_frame, text="재고 확인 시작", command=self.start_scraping_based_on_tab)
        self.start_button.pack(pady=10, fill=tk.X, expand=False)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, expand=False, pady=(0, 5))
        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack(side=tk.LEFT, padx=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(fill=tk.X, expand=True)

        self.log_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text.configure(state='disabled')

        default_font = font.nametofont("TkDefaultFont")
        bold_font = font.Font(family=default_font.cget("family"), size=default_font.cget("size"), weight="bold")
        self.log_text.tag_configure('bold', font=bold_font)
        self.log_text.tag_configure('success', foreground='blue', font=bold_font)
        self.log_text.tag_configure('error', foreground='red')

    def create_tab1_widgets(self, parent_frame):
        store_frame = ttk.LabelFrame(parent_frame, text="매장 선택", padding=10)
        store_frame.pack(fill=tk.X)
        store_frame.columnconfigure(1, weight=1)
        store_frame.columnconfigure(3, weight=1)

        ttk.Label(store_frame, text="지역:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.region_combo = ttk.Combobox(store_frame, values=list(STORE_DATA.keys()), state='readonly')
        self.region_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.region_combo.bind("<<ComboboxSelected>>", self.update_store_list)

        ttk.Label(store_frame, text="매장:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.store_combo = ttk.Combobox(store_frame, state='disabled')
        self.store_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.EW)

        self.region_combo.set("서울")
        self.update_store_list(None)
        self.store_combo.set("토이저러스 제타플렉스")

        grade_frame_outer = ttk.LabelFrame(parent_frame, text="등급 선택", padding=10)
        grade_frame_outer.pack(fill=tk.X, pady=5)
        
        self.grades = ["EG", "SD", "HG", "RG", "MG", "PG"]
        self.grade_vars = {grade: tk.BooleanVar() for grade in self.grades}
        
        grade_frame = ttk.Frame(grade_frame_outer)
        grade_frame.pack()

        self.select_all_var = tk.BooleanVar()
        ttk.Checkbutton(grade_frame, text="모두 선택", variable=self.select_all_var, command=self.toggle_select_all).pack(side=tk.LEFT, padx=5)
        # ttk.Button(grade_frame, text="모두 해제", command=self.deselect_all_grades).pack(side=tk.LEFT, padx=5)
        ttk.Separator(grade_frame, orient='vertical').pack(side=tk.LEFT, fill='y', padx=10, pady=5)

        for grade in self.grades:
            ttk.Checkbutton(grade_frame, text=grade, variable=self.grade_vars[grade],
                            command=self.update_select_all_status).pack(side=tk.LEFT, padx=5)

    def create_tab2_widgets(self, parent_frame):
        search_frame = ttk.LabelFrame(parent_frame, text="검색어 입력", padding="10")
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="상품명:").pack(side=tk.LEFT, padx=(0, 5))
        self.keyword_entry = ttk.Entry(search_frame)
        self.keyword_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.keyword_entry.bind("<Return>", self.on_enter_key)
        
        region_select_frame = ttk.LabelFrame(parent_frame, text="검색할 지역 선택", padding="10")
        region_select_frame.pack(fill=tk.X)

        self.region_vars = {region: tk.BooleanVar(value=True) for region in STORE_DATA.keys()}

        controls_frame = ttk.Frame(region_select_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 5))
        self.region_select_all_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls_frame, text="모두 선택", variable=self.region_select_all_var, command=self.toggle_region_select_all).pack(side=tk.LEFT, padx=5)
        # ttk.Button(controls_frame, text="모두 해제", command=self.deselect_all_regions).pack(side=tk.LEFT, padx=5)
        
        checkboxes_frame = ttk.Frame(region_select_frame)
        checkboxes_frame.pack(fill=tk.X)

        cols = 8
        for i, region in enumerate(STORE_DATA.keys()):
            ttk.Checkbutton(checkboxes_frame, text=region, variable=self.region_vars[region], command=self.update_region_select_all_status).grid(row=i//cols, column=i%cols, sticky=tk.W, padx=5)
    
    def create_tab3_widgets(self, parent_frame):
        about_frame = ttk.LabelFrame(parent_frame, text="프로그램 정보", padding=15)
        about_frame.pack(fill=tk.BOTH, expand=True)
        
        info_data = {
            "프로그램 이름": "롯데마트 건담 재고 파인더",
            "버전": "2.1.0",
            "제작자": "오해성",
            "기여자": "Github @Cass07",
            "연락처": "haesungoh0111@google.com",
            "설명": "롯데마트의 건담 재고를 쉽게 확인할 수 있도록 돕는 프로그램입니다.",
            "재고 홈페이지": "https://company.lottemart.com/mobiledowa/#",
            "아이콘": "Copyright - https://www.flaticon.com/kr/authors/medz"
        }
        
        for i, (key, value) in enumerate(info_data.items()):
            ttk.Label(about_frame, text=f"{key}:", font=('TkDefaultFont', 10, 'bold')).grid(row=i, column=0, sticky=tk.NW, padx=5, pady=2)
            default_font_family = font.nametofont("TkDefaultFont").cget("family")
            f = font.Font(family=default_font_family, size=10, underline=True)
            if key == "연락처":
                email_label = ttk.Label(about_frame, text=value, foreground="blue", cursor="hand2")
                email_label.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
                email_label.bind("<Button-1>", lambda e, v=value: self.open_email(v))
                email_label.configure(font=f)
            elif key == "아이콘":
                icon_label = ttk.Label(about_frame, text=value, foreground="blue", cursor="hand2")
                icon_label.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
                icon_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.flaticon.com/kr/authors/medz", new=1))
                icon_label.configure(font=f)
            elif key == "재고 홈페이지":
                link_label = ttk.Label(about_frame, text=value, foreground="blue", cursor="hand2")
                link_label.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
                link_label.bind("<Button-1>", lambda e: webbrowser.open("https://company.lottemart.com/mobiledowa/#", new=1))
                link_label.configure(font=f)
            else:
                ttk.Label(about_frame, text=value, wraplength=400).grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)

    def on_enter_key(self, event):
        self.start_scraping_based_on_tab()

    def open_email(self, email):
        webbrowser.open(f"mailto:{email}", new=1)
        
    def on_enter_key(self, event):
        self.start_scraping_based_on_tab()
    
    def start_scraping_based_on_tab(self):
        selected_tab_index = self.notebook.index('current')
        if selected_tab_index == 0:
            self.start_scraping_by_store_thread()
        else:
            self.start_scraping_all_stores_thread()
            
    def toggle_select_all(self):
        for var in self.grade_vars.values():
            var.set(self.select_all_var.get())
            
    def update_select_all_status(self):
        self.select_all_var.set(all(var.get() for var in self.grade_vars.values()))
        
    def deselect_all_grades(self):
        self.select_all_var.set(False)
        for var in self.grade_vars.values():
            var.set(False)
            
    def toggle_region_select_all(self):
        for var in self.region_vars.values():
            var.set(self.region_select_all_var.get())
            
    def update_region_select_all_status(self):
        self.region_select_all_var.set(all(var.get() for var in self.region_vars.values()))

    def deselect_all_regions(self):
        self.region_select_all_var.set(False)
        for var in self.region_vars.values():
            var.set(False)

    def update_store_list(self, event):
        selected_region = self.region_combo.get()
        if selected_region in STORE_DATA:
            stores = list(STORE_DATA[selected_region].keys())
            self.store_combo['values'] = stores
            self.store_combo.config(state='readonly')
            if event:
                self.store_combo.set('')
        else:
            self.store_combo.set('')
            self.store_combo.config(state='disabled')

    def log(self, message, tags=None):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message, tags)
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def common_start_logic(self):
        self.start_button.config(state='disabled')
        self.progress_bar['value'] = 0
        self.progress_label.config(text="")
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')

        try:
            driver_path = ChromeDriverManager().install()
            return driver_path
        except Exception as e:
            self.log(f"‼️ 드라이버 준비 중 오류 발생: {e}\n", 'error')
            self.start_button.config(state='normal')
            return None

    def start_scraping_by_store_thread(self):
        driver_path = self.common_start_logic()
        if not driver_path: return
        
        region_name = self.region_combo.get()
        store_name = self.store_combo.get()

        if not region_name or not store_name:
            self.log("‼️ 지역과 매장을 모두 선택해주세요.\n", 'error')
            self.start_button.config(state='normal')
            return

        selected_grades = [grade for grade, var in self.grade_vars.items() if var.get()]

        if not selected_grades:
            self.log("‼️ 검색할 건담 등급을 하나 이상 선택해주세요.\n", 'error')
            self.start_button.config(state='normal')
            return

        threading.Thread(target=self.worker_thread_scraping_by_store, 
                         args=(driver_path, region_name, store_name, selected_grades), 
                         daemon=True).start()
        
        self.process_queue()
        
    def start_scraping_all_stores_thread(self):
        driver_path = self.common_start_logic()
        if not driver_path: return

        keyword = self.keyword_entry.get().strip()
        if not keyword:
            self.log("‼️ 검색어를 입력해주세요.\n", 'error')
            self.start_button.config(state='normal')
            return

        selected_regions = [region for region, var in self.region_vars.items() if var.get()]
        if not selected_regions:
            self.log("‼️ 검색할 지역을 하나 이상 선택해주세요.\n", 'error')
            self.start_button.config(state='normal')
            return

        threading.Thread(target=self.worker_thread_scraping_all_stores, 
                         args=(driver_path, keyword, selected_regions), 
                         daemon=True).start()

        self.process_queue()

    def process_queue(self):
        try:
            message = self.queue.get_nowait()
            if message == "TASK_COMPLETE":
                self.start_button.config(state='normal')
                self.log("\n검색이 완료되었습니다.")
                self.progress_label.config(text="완료")
            elif isinstance(message, dict):
                 if 'result_by_store' in message:
                     self.display_by_store_results(message['result_by_store'])
                 elif 'result_all_stores' in message:
                     self.display_all_stores_results(message['result_all_stores'])
                 elif 'progress' in message:
                     progress, total = message['progress']
                     self.progress_bar['value'] = progress
                     self.progress_bar['maximum'] = total
                     self.progress_label.config(text=f"({progress}/{total})")
            else:
                self.log(str(message))
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def display_by_store_results(self, results):
        self.log("\n" + "="*50 + "\n")
        self.log(" 검색 결과 (지점별) ".center(44, "=") + "\n", 'bold')
        self.log("="*50 + "\n")

        if results:
            self.log(f"\n총 {len(results)}개의 건담을 찾았습니다!\n\n")
            for item in sorted(results, key=lambda x: x.name):
                self.log_text.configure(state='normal')
                self.log_text.insert(tk.END, "- 상품명: ")
                self.log_text.insert(tk.END, item.name, 'bold')
                self.log_text.insert(tk.END, "\n")
                self.log_text.insert(tk.END, f"  - 가격: {item.price}\n")
                self.log_text.insert(tk.END, f"  - 재고: {item.stock}\n")
                self.log_text.insert(tk.END, "-" * 25 + "\n")
                self.log_text.see(tk.END)
                self.log_text.configure(state='disabled')
        else:
            self.log("\n재고가 없습니다.")

    def display_all_stores_results(self, results):
        self.log("\n" + "="*50 + "\n")
        self.log(" 검색 결과 (전체 지점) ".center(44, "=") + "\n", 'bold')
        self.log("="*50 + "\n")
        
        if results:
            total_items = sum(len(store_result.search_items) for store_result in results)
            self.log(f"\n총 {len(results)}개 지점에서 {total_items}개의 재고를 발견했습니다!\n\n")
            for store_result in sorted(results, key=lambda x: x.store.name):
                self.log(f"{store_result.store.name}\n", 'success')
                for item in sorted(store_result.search_items, key=lambda x: x.name):
                    self.log_text.configure(state='normal')
                    self.log_text.insert(tk.END, "  - 상품명: ")
                    self.log_text.insert(tk.END, item.name, 'bold')
                    self.log_text.insert(tk.END, "\n")
                    self.log_text.insert(tk.END, f"    - 가격: {item.price}\n")
                    self.log_text.insert(tk.END, f"    - 재고: {item.stock}\n")
                    self.log_text.insert(tk.END, "-" * 25 + "\n")
                    self.log_text.see(tk.END)
                    self.log_text.configure(state='disabled')
        else:
            self.log("\n재고가 없습니다.")

    def worker_thread_scraping_by_store(self, driver_path, region_name, store_name, grades_to_search):
        self.queue.put("재고를 검색중입니다. 잠시만 기다려주세요...\n")

        store = Store(STORE_DATA[region_name][store_name], store_name, region_name)
        try :
            unique_items = self.web_search.worker_thread_scraping_by_store(
            driver_path, store, grades_to_search
            )
            self.queue.put({'result_by_store': unique_items})
        except Exception as e:
            self.queue.put("\n‼️ 스크립트 실행 중 심각한 오류가 발생했습니다.\n")
            self.queue.put(traceback.format_exc())
        finally:
            self.queue.put("TASK_COMPLETE")

            
    def worker_thread_scraping_all_stores(self, driver_path, keyword, selected_regions):
        self.queue.put("선택한 지역의 전체 지점 검색을 시작합니다. 잠시만 기다려주세요...\n")

        stores = []
        for region in selected_regions:
            if region in STORE_DATA:
                for store_name, store_code in STORE_DATA[region].items():
                    stores.append(Store(store_code, store_name, region))

        total_stores = len(stores)
        self.queue.put({'progress': (0, total_stores)})

        try :
            results = self.web_search.worker_thread_scraping_all_stores(
                driver_path, stores, keyword, self.queue
            )

            self.queue.put({'result_all_stores': results})
        except Exception:
            self.queue.put("\n‼️ 스크립트 실행 중 심각한 오류가 발생했습니다.\n")
            self.queue.put(traceback.format_exc())
        finally:
            self.queue.put("TASK_COMPLETE")


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        try:
            myappid = 'ohs.gundam.finder.2.1' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"알림: 작업 표시줄 아이콘 설정에 실패했습니다: {e}")

    root = tk.Tk()
    app = GundamStockCheckerApp(root)
    root.mainloop()
