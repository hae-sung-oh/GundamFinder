import tkinter as tk
from tkinter import ttk, scrolledtext, font
import threading
import queue
import re
import traceback
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# 롯데마트/토이저러스 매장 정보 (가나다 순)
STORE_DATA = {
    "서울": {
        "강변점": "301", "금천점": "335", "김포공항점": "441", "삼양점": "316", "서초점": "340",
        "송파점": "322", "양평점": "328", "월드타워점": "334", "중계점": "307", "청량리점": "312",
        "행당역점": "323", "맥스 금천점": "101", "맥스 영등포점": "103",
        "제타플렉스 서울역점": "200", "제타플렉스 잠실점": "302", "토이저러스 양평점": "344",
        "토이저러스 은평점": "343", "토이저러스 제타플렉스": "326", "토이저러스 중계점": "339"
    },
    "경기": {
        "그랑그로서리 구리점": "405", "경기양평점": "473", "고양점": "455", "광교점": "463",
        "토이저러스 광교점": "489", "권선점": "458", "김포한강점": "479", "덕소점": "457",
        "동두천점": "435", "롯데몰수지점": "446", "토이저러스 롯데몰수지점": "448",
        "마석점": "453", "비바건강마켓 남양주진접점": "449", "상록점": "464", "선부점": "475",
        "수원점": "462", "시화점": "456", "시흥배곧점": "476", "시흥점": "459", "신갈점": "468",
        "안산점": "415", "안성점": "417", "오산점": "410", "의왕점": "409", "이천점": "422",
        "장암점": "430", "주엽점": "403", "천천점": "411", "토이저러스 기흥점": "496",
        "토이저러스 이천점": "492", "토이저러스 파주점": "497", "판교점": "471", "평택점": "436",
        "화정점": "408"
    },
    "인천": {
        "검단점": "433", "계양점": "469", "부평역점": "404", "부평점": "426",
        "삼산점": "418", "송도점": "465", "연수점": "406", "영종도점": "424",
        "청라점": "461"
    },
    "강원": {"석사점": "804", "원주점": "801", "춘천점": "802"},
    "충북": {"상당점": "519", "서청주점": "513", "제천점": "509", "청주점": "501", "충주점": "505"},
    #TODO: Write for the rest of the regions
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
                in_stock_items.append({"name": name, "price": price, "stock": stock})
    return in_stock_items

class GundamStockCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("롯데마트 건담 재고 파인더")
        self.root.geometry("650x700")
        self.root.minsize(550, 400)

        self.queue = queue.Queue()
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        store_frame = ttk.LabelFrame(main_frame, text="매장 및 등급 선택", padding="10")
        store_frame.pack(fill=tk.X, pady=5, expand=False)
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

        self.grades = ["EG", "SD", "HG", "RG", "MG", "PG"]
        self.grade_vars = {grade: tk.BooleanVar() for grade in self.grades}
        
        grade_frame = ttk.Frame(store_frame)
        grade_frame.grid(row=1, column=0, columnspan=4, pady=(10, 5))

        self.select_all_var = tk.BooleanVar()
        ttk.Checkbutton(grade_frame, text="모두 선택", variable=self.select_all_var, command=self.toggle_select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(grade_frame, text="모두 해제", command=self.deselect_all_grades).pack(side=tk.LEFT, padx=5)
        ttk.Separator(grade_frame, orient='vertical').pack(side=tk.LEFT, fill='y', padx=10, pady=5)
        
        for grade in self.grades:
            ttk.Checkbutton(grade_frame, text=grade, variable=self.grade_vars[grade], command=self.update_select_all_status).pack(side=tk.LEFT, padx=5)

        self.start_button = ttk.Button(main_frame, text="재고 확인 시작", command=self.start_scraping_thread)
        self.start_button.pack(pady=10, fill=tk.X, expand=False)

        self.log_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text.configure(state='disabled')

        default_font = font.nametofont("TkDefaultFont")
        bold_font = font.Font(family=default_font.cget("family"), size=default_font.cget("size"), weight="bold")
        self.log_text.tag_configure('bold', font=bold_font)
        
    def toggle_select_all(self):
        is_checked = self.select_all_var.get()
        for var in self.grade_vars.values():
            var.set(is_checked)
            
    def update_select_all_status(self):
        all_checked = all(var.get() for var in self.grade_vars.values())
        self.select_all_var.set(all_checked)
        
    def deselect_all_grades(self):
        self.select_all_var.set(False)
        for var in self.grade_vars.values():
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

    def start_scraping_thread(self):
        self.start_button.config(state='disabled')
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        
        region_name = self.region_combo.get()
        store_name = self.store_combo.get()

        if not region_name or not store_name:
            self.log("‼️ 지역과 매장을 모두 선택해주세요.\n")
            self.start_button.config(state='normal')
            return
            
        selected_grades = [grade for grade, var in self.grade_vars.items() if var.get()]

        if not selected_grades:
            self.log("‼️ 검색할 건담 등급을 하나 이상 선택해주세요.\n")
            self.start_button.config(state='normal')
            return

        try:
            driver_path = ChromeDriverManager().install()
        except Exception as e:
            self.log(f"‼️ 드라이버 준비 중 오류 발생: {e}\n")
            self.start_button.config(state='normal')
            return

        threading.Thread(target=self.worker_thread_scraping, 
                         args=(driver_path, region_name, store_name, selected_grades), 
                         daemon=True).start()
        
        self.process_queue()

    def process_queue(self):
        try:
            message = self.queue.get_nowait()
            if message == "TASK_COMPLETE":
                self.start_button.config(state='normal')
            elif isinstance(message, dict) and 'result' in message:
                 self.display_results(message['result'])
            else:
                self.log(str(message))
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def display_results(self, results):
        self.log("\n" + "="*50 + "\n")
        self.log(" 검색 결과 ".center(47, "=") + "\n")
        self.log("="*50 + "\n")

        if results:
            self.log(f"\n총 {len(results)}개의 재고 보유 건담을 찾았습니다!\n\n")
            for item in sorted(results, key=lambda x: x['name']):
                self.log_text.configure(state='normal')
                
                self.log_text.insert(tk.END, "- 상품명: ")
                self.log_text.insert(tk.END, item['name'], 'bold')
                self.log_text.insert(tk.END, "\n")
                
                self.log_text.insert(tk.END, f"  - 가격: {item['price']}\n")
                self.log_text.insert(tk.END, f"  - 재고: {item['stock']}\n")
                self.log_text.insert(tk.END, "-" * 25 + "\n")

                self.log_text.see(tk.END)
                self.log_text.configure(state='disabled')
        else:
            self.log("\n재고가 없습니다.")

    def worker_thread_scraping(self, driver_path, region_name, store_name, grades_to_search):
        driver = None
        all_found_items = []
        try:
            search_terms = []
            for grade in grades_to_search:
                if grade == 'HG':
                    search_terms.append('건담 HG'); search_terms.append('건담 HGUC')
                else:
                    search_terms.append(f'건담 {grade}')

            self.queue.put("재고를 검색중입니다. 잠시만 기다려주세요...\n")
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("headless")
            options.add_argument('--log-level=3')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            wait = WebDriverWait(driver, 10)

            search_url = "https://company.lottemart.com/mobiledowa/inc/asp/search_product_list.asp"

            payload = {
                "p_market": STORE_DATA[region_name][store_name],
                "p_schWord": "",
                "page" : 1
            }
            
            for term in search_terms:
                payload["p_schWord"] = term
                payload["page"] = 1

                items = []
                while True:
                    driver.get(search_url + '?' + '&'.join(f"{k}={v}" for k, v in payload.items()))
                    if "해당 페이지를 찾을 수 없습니다" in driver.page_source:
                        break
                    items += get_stock_from_html(driver.page_source)
                    if items:
                        all_found_items.extend(items)
                    payload["page"] += 1

            unique_items = list({frozenset(item.items()): item for item in all_found_items}.values())
            self.queue.put({'result': unique_items})

        except Exception:
            self.queue.put("\n‼️ 스크립트 실행 중 심각한 오류가 발생했습니다.\n")
            self.queue.put(traceback.format_exc())
        finally:
            if driver:
                driver.quit()
            self.queue.put("TASK_COMPLETE")

if __name__ == "__main__":
    root = tk.Tk()
    app = GundamStockCheckerApp(root)
    root.mainloop()