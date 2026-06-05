#python -m app.script.recordFamilyMartStore
import os,json,time,requests
from app.core.firebase import get_firestore_client
from dotenv import load_dotenv

load_dotenv()
cities = [
        "台北市","基隆市","新北市","桃園市",   "新竹市","新竹縣","苗栗縣","台中市",
        "彰化縣","南投縣","雲林縣","嘉義市","嘉義縣","台南市","高雄市","屏東縣",
        "宜蘭縣","花蓮縣","台東縣","澎湖縣","連江縣","金門縣"
    ]
FAMILYMART_URL="https://api.map.com.tw/net/familyShop.aspx"
FAMILYMART_API_KEY = os.getenv("FAMILYMART_API_KEY")

def get_town_list_familymart(city: str):
    url = (
        f"{FAMILYMART_URL}"
        f"?searchType=ShowTownList"
        f"&type="
        f"&city={city}"
        f"&fun=storeTownList"
        f"&key={FAMILYMART_API_KEY}"
    )

    res = requests.get(
        url,
        headers={
            "Referer": "https://www.family.com.tw/"
        }
    )

    text = res.text.strip()

    if not text.startswith("storeTownList("):
        print("取得行政區失敗")
        print(text[:500])
        return []

    json_text = text.replace("storeTownList(", "", 1).rsplit(")", 1)[0]

    towns = json.loads(json_text)

    return towns

def get_store_list_familymart(city: str, area: str):
    url = (
        f"{FAMILYMART_URL}"
        f"?searchType=ShopList"
        f"&type="
        f"&city={city}"
        f"&area={area}"
        f"&road="
        f"&fun=showStoreList"
        f"&key={FAMILYMART_API_KEY}"
    )

    res = requests.get(
        url,
        headers={
            "Referer": "https://www.family.com.tw/"
        }
    )

    text = res.text.strip()

    if not text.startswith("showStoreList("):
        print(f"取得門市失敗 {city} {area}")
        print(text[:500])
        return []

    json_text = text.replace("showStoreList(", "", 1).rsplit(")", 1)[0]

    return json.loads(json_text)

def fetch_city_familymart(city: str):
    print(f"fetching city: {city}")

    towns = get_town_list_familymart(city)

    all_stores = []

    for town in towns:
        area = town["town"]

        print(f"行政區: {area}")

        stores = get_store_list_familymart(city, area)

        print(f"  → {len(stores)} 間門市")
        # 將行政區與縣市資訊填入每一間門市資料中，方便後續建立分層的collection
        for store in stores:
            store["_temp_city"] = town["city"]
            store["_temp_area"] = town["town"]
        all_stores.extend(stores)

        time.sleep(0.3)

    print()
    print("====================")
    print("門市總數:", len(all_stores))
    print("====================")

    return all_stores
#用str.maketrans更優雅 O(N)
map=str.maketrans({
    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
    "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
})

def normalize_text(text: str) -> str:
    if not text:
        return ""
    #用maketrans建完表後要呼叫translate來替換 
    return text.translate(map).strip()

def refactor_familymart_store_data(data_list):
    stores = []
    # API 回傳的資料結構不太一致，有時候只有一筆資料會直接回傳物件而不是列表
    # ，所以這裡做個檢查確保統一處理列表
    if not isinstance(data_list, list):
        data_list = [data_list]

    for item in data_list:
        stores.append({
            "id": item["pkey"].strip(),
            "name": item["NAME"].strip() + "門市",
            "address": normalize_text(item["addr"].strip()),
            "telephone": item.get("TEL", "").strip(),
            "city": item.get("_temp_city", "").strip(),
            "area": item.get("_temp_area", "").strip(),
            "latitude": float(item["py"]),
            "longitude": float(item["px"]) ,
        })

    return stores

def upload_stores_to_firestore(stores):
    stores = refactor_familymart_store_data(stores)
    print("要儲存的格式:")
    print(stores[0])
    db = get_firestore_client()

    batch = db.batch()
    collection = db.collection("familyMartStore")

    total = 0
    count=0
    for store in stores:
        #結構化儲存，方便管理與維護
        doc_ref = db.collection("familyMartStore").document(store["city"]).collection(store["area"]).document(store["id"])
        #用batch保有atomicity、提升效率的好處
        batch.set(doc_ref, store)
        total += 1
        count+=1
        if count>=500:
            batch.commit()
            print(f"已上傳 {total} 間門市")
            batch = db.batch()
            count=0
    if count>0:
        batch.commit()
    print(f"已上傳 {total} 間門市")

def fetch_all_familymartstores():
    all_store=[]
    counter=0
    for city in cities:
        all_store=fetch_city_familymart(city)
        upload_stores_to_firestore(all_store)
        counter+=len(all_store)
        
    print("所有城市的familyMart門市資料已完成上傳,共", counter, "筆")
    
    return all_store 
if __name__ == "__main__":
    fetch_all_familymartstores()
    #familymart_stores=fetch_city_familymart("新竹市")
    #upload_stores_to_firestore(familymart_stores)