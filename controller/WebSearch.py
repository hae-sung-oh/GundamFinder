import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from model.SearchItem import SearchItem
from model.StoreResult import StoreResult


class WebSearch:
    def __init__(self):
        self.gradeObjects = [{
                "HG": ["건담 HG", "건담 HGUC", "건담 HGCE", "건담 HGFC", "건담 HGAW", "건담 HGAC", "건담 HGBD"]
            },
            {
                "MG": ["건담 MG", "건담 MGEX", "건담 MGSD"]
            },
            {
                "SD": ["건담 SD", "건담 SDCS", "건담 SDEX", "건담 SDWH"]
            }
        ]

    def worker_thread_scraping_by_store(self, driver_path, store, grades):
        keywords = []

        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("headless")
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=options)

        for grade in grades:
            if grade in self.gradeObjects:
                for keyword in self.gradeObjects[grade]:
                    keywords.append(keyword)
            else:
                keywords.append(f'건담 {grade}')

        unique_items = []
        try:
            for keyword in keywords:
                items = self.__scrap(driver, store, keyword)
                if items:
                    unique_items += items
        finally:
            if driver:
                driver.quit()

        return unique_items

    def worker_thread_scraping_all_stores(self, driver_path, stores, keyword, queue):

        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("headless")
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=options)

        store_results = []
        i = 1
        total_stores = len(stores)
        try:
            for store in stores:
                queue.put({'progress': (i, total_stores)})
                queue.put(f"({i}/{total_stores}) '{store.region} {store.name}' 검색 중...\n")
                i += 1

                items = self.__scrap(driver, store, keyword)
                if items:
                    store_results.append(StoreResult(store, items))
        finally:
            if driver:
                driver.quit()

        return store_results

    def __scrap(self, driver, store, keyword):
        all_found_items = []

        search_url = "https://company.lottemart.com/mobiledowa/inc/asp/search_product_list.asp"

        payload = {
            "p_market": store.id,
            "p_schWord": keyword,
            "page": 1
        }

        items = []
        while True:
            driver.get(search_url + '?' + '&'.join(f"{k}={v}" for k, v in payload.items()))
            print(driver.page_source)
            if "해당 페이지를 찾을 수 없습니다" in driver.page_source:
                break
            result_list = self.__get_stock_from_html(driver.page_source)
            if result_list is False:
                break
            items += result_list
            payload["page"] += 1
        unique_items = self.__remove_duplicates(items)
        return unique_items

    def __get_stock_from_html(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        result_list = soup.find('body')
        if not result_list or not result_list.contents or str(result_list) == '<body></body>':
            return False
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

    def __remove_duplicates(self, items):
        seen = {}
        return [seen.setdefault(item.name, item) for item in items if item.name not in seen]
