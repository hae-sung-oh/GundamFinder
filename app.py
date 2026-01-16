from flask import Flask, render_template, request
from model.SearchItem import SearchItem
from controller.WebSearch import WebSearch
from model.Store import Store
import json

app = Flask(__name__)

# 기존 STORE_DATA 복사
STORE_DATA = {
    "서울": {"강변점": "301", "금천점": "335", "김포공항점": "441", "삼양점": "316", "서초점": "340", "송파점": "322", "양평점": "328", "월드타워점": "334", "중계점": "307", "청량리점": "312", "행당역점": "323", "맥스 금천점": "101", "맥스 영등포점": "103", "제타플렉스 서울역점": "200", "제타플렉스 잠실점": "302", "토이저러스 양평점": "344", "토이저러스 은평점": "343", "토이저러스 제타플렉스": "326", "토이저러스 중계점": "339"},
    "경기": {"경기양평점": "473", "고양점": "455", "광교점": "463", "토이저러스 광교점": "489", "권선점": "458", "김포한강점": "479", "덕소점": "457", "동두천점": "435", "롯데몰수지점": "446", "토이저러스 롯데몰수지점": "448", "마석점": "453", "상록점": "464", "선부점": "475", "수원점": "462", "시화점": "456", "시흥배곧점": "476", "시흥점": "459", "신갈점": "468", "안산점": "415", "안성점": "417", "오산점": "410", "의왕점": "409", "이천점": "422", "장암점": "430", "주엽점": "403", "천천점": "411", "토이저러스 기흥점": "496", "토이저러스 이천점": "492", "토이저러스 파주점": "497", "판교점": "471", "평택점": "436", "화정점": "408"},
    "인천": {"검단점": "433", "계양점": "469", "부평역점": "404", "부평점": "426", "삼산점": "418", "송도점": "465", "연수점": "406", "영종도점": "424", "청라점": "461", "토이저러스 청라점": "488"},
    "강원": {"석사점": "804", "원주점": "801", "춘천점": "802"},
    "충북": {"상당점": "519", "서청주점": "513", "제천점": "509", "청주점": "501", "충주점": "505"},
    "충남": {"당진점": "515", "서산점": "506", "성정점": "507", "아산터미널점": "512", "홍성점": "518"},
    "대전": {"노은점": "516", "대덕점": "508", "서대전점": "504"},
    "경북": {"구미점": "613", "김천점": "647", "포항점": "623"},
    "경남": {"거제점": "645", "김해점": "642", "맥스 창원중앙점": "112", "마산점": "607", "삼계점": "639", "시티세븐점": "620", "양덕점": "643", "웅상점": "610", "장유점": "609", "진주점": "648", "진해점": "611", "통영점": "608"},
    "대구": {"대구율하점": "629", "토이저러스 대구율하점": "649", "토이저러스 대구죽전점": "664"},
    "부산": {"광복점": "655", "동래점": "618", "동부산점": "658", "토이저러스 동부산점": "662", "부산점": "626", "사상점": "612", "사하점": "603", "화명점": "605"},
    "울산": {"울산점": "601", "진장점": "614"},
    "전북": {"군산점": "707", "남원점": "713", "맥스 송천점": "110", "익산점": "702", "전주점": "708", "정읍점": "709"},
    "전남": {"나주점": "719", "남악점": "724", "맥스 목포점": "109", "여수점": "705", "여천점": "710"},
    "광주": {"맥스 상무점": "108", "수완점": "715", "토이저러스 수완점": "722", "월드컵점": "706", "첨단점": "704"},
    "제주": {"제주점": "852"}
}
GRADES = ["EG", "SD", "HG", "RG", "MG", "PG"]

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html',
        regions=list(STORE_DATA.keys()),
        grades=GRADES,
        store_data=STORE_DATA,
        results=None
    )

@app.route('/search', methods=['POST'])
def search():
    region = request.form.get('region')
    store = request.form.get('store')
    grades = request.form.getlist('grades')
    keyword = request.form.get('keyword', '').strip()
    regions_multi = request.form.getlist('regions')

    results = []
    web_search = WebSearch()

    # 지점별 등급 검색 (상품명 입력 시 상품명으로 검색)
    if region and store:
        search_grades = grades if grades else GRADES
        store_code = STORE_DATA[region][store]
        store_obj = Store(int(store_code), store, region)
        if keyword:
            items = web_search.worker_thread_scraping_by_store(
                driver_path=None,
                store=store_obj,
                grades=[keyword]
            )
        else:
            items = web_search.worker_thread_scraping_by_store(
                driver_path=None,
                store=store_obj,
                grades=search_grades
            )
        results.append({'store': store, 'items': items})
    elif keyword and regions_multi:
        for reg in regions_multi:
            for store_name, store_code in STORE_DATA[reg].items():
                store_obj = Store(int(store_code), store_name, reg)
                items = web_search.worker_thread_scraping_by_store(
                    driver_path=None,
                    store=store_obj,
                    grades=[keyword]
                )
                results.append({'store': store_name, 'items': items})
    return render_template('index.html',
        regions=list(STORE_DATA.keys()),
        grades=GRADES,
        store_data=STORE_DATA,
        results=results,
        selected_region=region,
        selected_store=store,
        selected_grades=grades,
        selected_keyword=keyword,
        selected_regions=regions_multi
    )

@app.route('/search_by_store', methods=['POST'])
def search_by_store():
    region = request.form.get('region')
    store = request.form.get('store')
    grades = request.form.getlist('grades')
    results = []
    web_search = WebSearch()
    active_tab = 'by_store'
    if region and store:
        search_grades = grades if grades else GRADES
        store_code = STORE_DATA[region][store]
        store_obj = Store(int(store_code), store, region)
        items = web_search.worker_thread_scraping_by_store(
            driver_path=None,  # 실제 환경에서는 드라이버 경로 필요
            store=store_obj,
            grades=search_grades
        )
        results.append({'store': store, 'items': items})
    return render_template('index.html',
        regions=list(STORE_DATA.keys()),
        grades=GRADES,
        store_data=STORE_DATA,
        results=results,
        selected_region=region,
        selected_store=store,
        selected_grades=grades,
        active_tab=active_tab
    )

@app.route('/search_by_region', methods=['POST'])
def search_by_region():
    keyword = request.form.get('keyword', '').strip()
    regions_multi = request.form.getlist('regions')
    results = []
    web_search = WebSearch()
    active_tab = 'by_region'
    if keyword and regions_multi:
        for reg in regions_multi:
            for store_name, store_code in STORE_DATA[reg].items():
                store_obj = Store(int(store_code), store_name, reg)
                items = web_search.worker_thread_scraping_by_store(
                    driver_path=None,  # 실제 환경에서는 드라이버 경로 필요
                    store=store_obj,
                    grades=[keyword]
                )
                results.append({'store': store_name, 'items': items})
    return render_template('index.html',
        regions=list(STORE_DATA.keys()),
        grades=GRADES,
        store_data=STORE_DATA,
        results=results,
        selected_keyword=keyword,
        selected_regions=regions_multi,
        active_tab=active_tab
    )

if __name__ == '__main__':
    app.run(debug=True)
