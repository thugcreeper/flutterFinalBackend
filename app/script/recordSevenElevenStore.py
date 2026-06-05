#python -m app.script.recordSevenElevenStore
#這個code是儲存超商(7-11)到firestore
import requests
import xmltodict
import time
from app.core.firebase import get_firestore_client

SEVEN_ELEVEN_URL = "https://emap.pcsc.com.tw/EMapSDK.aspx"

db = get_firestore_client()
#對，他id就是會亂跳
city_ids = {
        "台北市": "01","基隆市": "02","新北市": "03","桃園市": "04","新竹市": "05",
        "新竹縣": "06","苗栗縣": "07","台中市": "08","彰化縣": "10","南投縣": "11",
        "雲林縣": "12","嘉義市": "13","嘉義縣": "14","台南市": "15","高雄市": "17",
        "屏東縣": "19","宜蘭縣": "20","花蓮縣": "21","台東縣": "22","澎湖縣": "23",
        "連江縣": "24","金門縣": "25", 
    }
def safe_parse_xml(text: str):
    if not text or not text.strip():
        return None
    if "<html" in text.lower():
        return None
    try:
        return xmltodict.parse(text)
    except Exception as e:
        print("XML解析錯誤:", e)
        return None

# 取得指定城市的鄉鎮列表
def get_711town_list(city: str, city_id: str):
    params = {
        "commandid": "GetTown",
        "cityid": city_id
    }

    res = requests.get(SEVEN_ELEVEN_URL, params=params, headers={
    "Referer": "https://emap.pcsc.com.tw/"
}
)
    data = safe_parse_xml(res.text)

    if not data:
        print("沒有取得鄉鎮資料")
        return []

    geo = data.get("iMapSDKOutput", {}).get("GeoPosition")

    if not geo:
        return []

    if not isinstance(geo, list):
        geo = [geo]

    result = []

    for item in geo:
        result.append({
            "city": city,
            "cityId": city_id,
            "town": item.get("TownName"),
            "townId": item.get("TownID")
        })

    return result


#根據城市和鄉鎮取得門市列表
def get_711store_list(city: str, town: str):
    params = {
        "commandid": "SearchStore",
        "city": city,
        "town": town
    }

    res = requests.get(SEVEN_ELEVEN_URL, params=params, headers={
        "Referer": "https://emap.pcsc.com.tw/"
    })
    #print("DEBUG URL:", res.url)

    data = safe_parse_xml(res.text)

    if not data:
        return []

    geo = data.get("iMapSDKOutput", {}).get("GeoPosition")

    if not geo:
        return []

    if not isinstance(geo, list):
        geo = [geo]

    return geo



# 跟據城市和鄉鎮取得門市列表
def fetch_city_711(city: str, city_id: str):
    print(f" fetching city: {city}")

    towns = get_711town_list(city, city_id)

    all_stores = []

    for town in towns:
        print(f" 行政區: {town['town']}")

        if not town["townId"]:
            continue

        stores = get_711store_list(
            
            
            town["city"],
            town["town"]
        )

        print(f"   → {len(stores)} 間門市")
        # 將行政區與縣市資訊填入每一間門市資料中，方便後續建立分層的collection
        for store in stores:
            store["_temp_city"] = town["city"]
            store["_temp_area"] = town["town"]
        all_stores.extend(stores)

        time.sleep(0.3)  # avoid API spam

    print("\n====================")
    print("門市總數:", len(all_stores))
    print("====================\n")

    #for s in all_stores[:10]:
        #print(s)

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

def refactor_711store_data(data_list):
    stores = []
    # API 回傳的資料結構不太一致，有時候只有一筆資料會直接回傳物件而不是列表
    # ，所以這裡做個檢查確保統一處理列表
    
    if not isinstance(data_list, list):
        data_list = [data_list]

    for item in data_list:
        stores.append({
            "id": item["POIID"].strip(),
            "name": item["POIName"].strip() + "門市",
            "address": normalize_text(item["Address"].strip()),
            "telephone": item.get("Telno", "").strip(),
            "open_time": item.get("OP_TIME", ""),       
            "city": item.get("_temp_city", "").strip(),
            "area": item.get("_temp_area", "").strip(),
            #取得的原始資料經緯度是叫做"X" "Y"，要記得除100萬
            "latitude": float(item["Y"]) / 1000000,
            "longitude": float(item["X"]) / 1000000,
        })

    return stores


def upload_711stores_to_firestore(stores):
    stores = refactor_711store_data(stores)
    print("要儲存的格式:")
    print(stores[0])
    db = get_firestore_client()

    batch = db.batch()
    
    
    total = 0
    count=0
    for store in stores:
        #結構化儲存，方便管理與維護
        doc_ref = db.collection("7-11Store").document(store["city"]).collection(store["area"]).document(store["id"])
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
    
def fetch_all_711stores():
    all_store=[]
    counter=0
    for city, city_id in city_ids.items():
        all_store=fetch_city_711(city, city_id)
        upload_711stores_to_firestore(all_store)
        counter+=len(all_store)
    print("所有城市的7-11門市資料已完成上傳,共", counter, "筆")
    
    return all_store

if __name__ == "__main__":
    #all_store=fetch_city_711("南投縣", city_ids.get("南投縣"))
    #upload_711stores_to_firestore(all_store)
    all_store=fetch_all_711stores()
    

