"""
Plant Video Generator - Tạo video về thực vật với hình ảnh thực tế.

Features:
- Tìm ảnh/video thực từ Pexels API
- Đọc tên thực vật bằng Edge TTS
- Nhạc nền chung từ sounds/plants/plants.mp3
- Ghép thành video hoàn chỉnh
"""
USED_VIDEO_IDS = set()

import asyncio
import aiohttp
import os
import json
import random
import subprocess
from config import Config

import random
CONTEXTS = ["garden", "field", "forest", "park", "farm", "tropical", "nature"]
MOTIONS = ["wind blowing", "swaying", "slow motion", "breeze"]
LIGHTINGS = ["sunlight", "golden hour", "soft light", "morning light", "sunset"]
STYLES = ["cinematic", "macro", "close up", "wide shot"]
TRENDS = [
    "aesthetic",
    "relaxing",
    "cinematic",
    "4k ultra hd",
    "nature documentary",
    "viral style",
    "instagram reels",
    "tiktok style",
    "slow living",
    "ambient"
]

FLOWER_BOOST = ["macro", "bokeh", "close up"]
TREE_BOOST = ["wide shot", "aerial"]

USED_KEYWORDS = set()


# def _generate_smart_keyword(base_query: str) -> str:
#     words = base_query.split()
#     core = " ".join(words[:3])  # giữ object chính

#     # detect loại
#     if "flower" in base_query:
#         style = random.choice(FLOWER_BOOST)
#     elif "tree" in base_query:
#         style = random.choice(TREE_BOOST)
#     else:
#         style = random.choice(STYLES)

#     return " ".join([
#         core,
#         random.choice(CONTEXTS),
#         random.choice(MOTIONS),
#         random.choice(LIGHTINGS),
#         style,
#         random.choice(TRENDS),
#         "4k"
#     ])
def _generate_smart_keyword(base_query: str) -> str:
    words = base_query.split()
    core = " ".join(words[:2])  # giữ object chính gọn hơn

    if "flower" in base_query:
        style = random.choice(FLOWER_BOOST)
    elif "tree" in base_query:
        style = random.choice(TREE_BOOST)
    else:
        style = random.choice(STYLES)

    return " ".join(filter(None, [
        core,
        random.choice(CONTEXTS),
        random.choice(MOTIONS),
        random.choice(LIGHTINGS),
        style,
        random.choice(TRENDS),
        "4k"
    ]))


def _get_unique_keyword(base_query: str) -> str:
    for _ in range(10):
        kw = _generate_smart_keyword(base_query)
        if kw not in USED_KEYWORDS:
            USED_KEYWORDS.add(kw)
            return kw
    return kw

from generators.animal_video_generator import (
    PEXELS_API_KEY,
    search_pexels_images,
    download_file,
    get_video_duration,
    resize_video_for_short,
    create_image_video,
    concatenate_videos,
    add_silence_to_audio,
    _get_aspect_ratio_range,
    _pexels_video_search_single,
)

# ============================================================
# PLANT-SPECIFIC PEXELS SEARCH
# Không strip từ khóa "flower", "plant", "tree", v.v.
# ============================================================

def _extract_plant_core_name(query: str) -> str:
    """Trích xuất tên thực vật chính từ query (1-2 từ đầu, bỏ filler)."""
    filler_words = {
        "tree", "plant", "flower", "nature", "close", "up", "macro", "garden", "field",
        "forest", "tropical", "sunlight", "wind", "slow", "motion", "4k", "beautiful",
        "colorful", "large", "big", "small", "indoor", "outdoor", "aesthetic", "cinematic",
        "water", "pond", "farm", "plantation", "bush", "vine", "golden", "morning",
        "sunset", "soft", "light", "breeze", "blowing", "rays", "mist", "rain", "fruit",
        "red", "green", "white", "pink", "blue", "purple", "orange", "yellow",
    }
    words = query.lower().split()
    core = [w for w in words if w not in filler_words]
    return " ".join(core[:2]) if core else words[0] if words else ""


async def search_pexels_videos_plant(query: str, per_page: int = 10, orientation: str = "landscape") -> list[dict]:
    """Tìm video thực vật từ Pexels API.
    Khác với animal: KHÔNG strip các từ khóa plant/flower/tree.
    Có thêm validation để tránh lấy video không liên quan.
    """
    if not PEXELS_API_KEY:
        return []

    min_ratio, max_ratio, ratio_label = _get_aspect_ratio_range(orientation)

    # Với thực vật: dùng query gốc (đã có từ khóa tốt trong PLANT_DATABASE)
    # Thử thêm fallback ngắn hơn
    queries = _build_plant_search_queries(query)
    
    # Lấy tên thực vật chính để validate kết quả
    plant_core = _extract_plant_core_name(query)
    print(f"      [Pexels Video Plant] Core name for validation: '{plant_core}'")

    for qi, q in enumerate(queries):
        print(f"      [Pexels Video Plant] Try {qi+1}/{len(queries)}: '{q}'")
        videos = await _pexels_video_search_single(q, per_page, orientation,
                                                     min_ratio, max_ratio, ratio_label)
        videos = [v for v in videos if v.get("duration", 0) >= 3]
        
        if videos:
            # Validate: ưu tiên video có URL/page chứa tên thực vật
            validated = _validate_plant_videos(videos, plant_core)
            if validated:
                print(f"      [Pexels Video Plant] ✓ Found {len(validated)} VALIDATED videos with query '{q}'")
                return validated
            else:
                print(f"      [Pexels Video Plant] ⚠ Found {len(videos)} videos but NONE validated for '{plant_core}'")
                # Tiếp tục thử query khác
        else:
            print(f"      [Pexels Video Plant] ✗ No results for '{q}'")

    # Fallback: nếu không có video nào validated, trả về kết quả cuối cùng (nếu có)
    print(f"      [Pexels Video Plant] ⚠ No validated videos, returning empty (will fallback to image)")
    return []


def _validate_plant_videos(videos: list[dict], plant_core: str) -> list[dict]:
    """
    Lọc video có liên quan đến tên thực vật.
    - Bỏ video có người (people, person, woman, man, etc.)
    - Bỏ video có tên cây/quả khác trong URL
    
    Ví dụ: plant_core="starfruit" → skip video có URL chứa "banana", "orange", "lemon"
    """
    if not plant_core:
        return videos
    
    # Từ khóa liên quan đến người - SKIP những video này
    people_keywords = {
        "person", "people", "woman", "man", "girl", "boy", "child", "children",
        "kid", "kids", "human", "hand", "hands", "finger", "fingers",
        "farmer", "gardener", "worker", "tourist", "couple", "family",
        "holding", "picking", "harvesting", "eating", "cooking",
    }
    
    # Danh sách các loại cây/quả phổ biến - nếu URL chứa tên khác thì skip
    common_plants = {
        # Cây ăn quả nhiệt đới
        "banana", "papaya", "mango", "coconut", "pineapple", "durian", "jackfruit",
        "guava", "papaya", "avocado", "passion", "dragon", "rambutan", "lychee",
        "longan", "starfruit", "mangosteen", "soursop", "custard",
        # Cây ăn quả ôn đới  
        "orange", "lemon", "lime", "apple", "grape", "cherry", "peach", "pear",
        "plum", "fig", "olive", "apricot", "pomegranate", "persimmon", "kiwi",
        "strawberry", "blueberry", "raspberry", "watermelon", "melon",
        # Rau củ & cây nông nghiệp
        "tomato", "pepper", "chili", "corn", "wheat", "rice", "potato", "carrot",
        "cabbage", "lettuce", "onion", "garlic", "ginger", "cassava", "sugarcane",
        "soybean", "soya", "bean", "pea", "peanut", "cotton", "tea", "coffee",
        # Hoa
        "rose", "tulip", "daisy", "lily", "orchid", "lotus", "sunflower",
        "lavender", "jasmine", "hibiscus", "chrysanthemum", "magnolia",
        # Cây gỗ/rừng
        "pine", "oak", "maple", "willow", "birch", "cedar", "fir", "bamboo",
        "palm", "eucalyptus", "acacia", "teak", "mahogany", "redwood",
    }
    
    plant_words = set(plant_core.lower().split())
    
    validated = []
    for v in videos:
        url = v.get("page_url", v.get("url", "")).lower()
        
        # 1. Kiểm tra URL có chứa từ khóa về NGƯỜI không → SKIP
        found_people = False
        for people_word in people_keywords:
            if people_word in url:
                print(f"        [VALIDATE] SKIP id={v.get('id')} - URL contains PEOPLE keyword '{people_word}'")
                found_people = True
                break
        
        if found_people:
            continue
        
        # 2. Kiểm tra URL có chứa tên cây/quả KHÁC không → SKIP
        found_wrong_plant = False
        for other_plant in common_plants:
            if other_plant in url and other_plant not in plant_words:
                print(f"        [VALIDATE] SKIP id={v.get('id')} - URL contains '{other_plant}' (want '{plant_core}')")
                found_wrong_plant = True
                break
        
        if found_wrong_plant:
            continue
        
        # 3. Ưu tiên video có URL chứa đúng tên thực vật
        if any(pw in url for pw in plant_words):
            print(f"        [VALIDATE] ✓ EXACT MATCH id={v.get('id')} - URL contains '{plant_core}'")
            validated.insert(0, v)  # Ưu tiên lên đầu
        else:
            print(f"        [VALIDATE] ~ NEUTRAL id={v.get('id')} - URL neutral")
            validated.append(v)
    
    return validated


# def _build_plant_search_queries(query: str) -> list[str]:
#     """
#     Tạo danh sách query cho thực vật.
#     KHÔNG strip "flower", "plant", "tree", "close up", etc.
#     """
#     clean = query.strip()
#     queries = []

#     # Query 1: query gốc đầy đủ (chính xác nhất)
#     queries.append(clean)

#     # Query 2: rút gọn bớt (bỏ filler nhẹ)
#     light_filler = {"close", "up", "large", "big", "small", "beautiful", "colorful"}
#     words = clean.lower().split()
#     short_words = [w for w in words if w not in light_filler]
#     if short_words and " ".join(short_words) != clean.lower():
#         queries.append(" ".join(short_words))

#     # Query 3: chỉ 2-3 từ đầu (fallback)
#     core_words = clean.split()[:3]
#     core_query = " ".join(core_words)
#     if core_query.lower() != clean.lower():
#         queries.append(core_query)

#     # Loại bỏ trùng lặp, giữ thứ tự
#     seen = set()
#     unique = []
#     for q in queries:
#         q_lower = q.lower().strip()
#         if q_lower not in seen:
#             seen.add(q_lower)
#             unique.append(q)

#     return unique
def _build_plant_search_queries(query: str) -> list[str]:
    """
    Tạo danh sách query cho thực vật, từ chính xác → tổng quát.

    Nguyên tắc:
    - Query gốc từ PLANT_DATABASE đứng TRƯỚC (đã được tối ưu sẵn)
    - Rút gọn dần để fallback, KHÔNG ghép random keyword
    - Giữ tên thực vật + bối cảnh tự nhiên để tránh lấy nhầm video
    """
    clean = query.strip()
    queries = []

    # Tách tên thực vật chính (bỏ filler words)
    filler_words = {
        "nature", "plant", "close", "up", "macro", "garden", "field",
        "forest", "tropical", "sunlight", "wind", "slow", "motion",
        "4k", "beautiful", "colorful", "large", "big", "small",
        "indoor", "outdoor", "aesthetic", "cinematic", "bokeh",
        "water", "pond", "farm", "plantation", "bush", "vine",
        "golden", "morning", "sunset", "soft", "light", "breeze",
        "blowing", "rays", "mist", "rain", "dew", "drops",
        "calm", "green", "white", "red", "pink", "blue", "purple",
        "orange", "yellow", "modern", "home", "office", "decor",
        "minimal", "hanging", "trailing", "swaying",
    }
    core_words = [w for w in clean.lower().split() if w not in filler_words]
    plant_name = " ".join(core_words[:3]) if core_words else clean.split()[0]

    # Query 1: query gốc đầy đủ từ database (chính xác nhất)
    queries.append(clean)

    # Query 2: tên thực vật + "plant nature" → tránh ảnh đồ ăn/nấu nướng
    queries.append(f"{plant_name} plant nature")

    # Query 3: chỉ tên thực vật (fallback cuối)
    queries.append(plant_name)

    # Loại bỏ trùng lặp, giữ thứ tự
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)

    return unique


# ============================================================
# PLANT DATABASE
# Key: tên tiếng Anh
# Value: (search_term, tên_đọc_tiếng_Việt)
# ============================================================

PLANT_DATABASE = {
    # ===== HOA (40 loài) =====
    "rose": ("rose flower bloom petals", "hoa hồng"),
    "sunflower": ("sunflower field yellow", "hoa hướng dương"),
    "lotus": ("lotus flower pond water", "hoa sen"),
    "orchid": ("orchid flower phalaenopsis", "hoa lan"),
    "tulip": ("tulip flower field spring", "hoa tulip"),
    "cherry blossom": ("cherry blossom sakura petals", "hoa anh đào"),
    "lavender": ("lavender field purple", "hoa oải hương"),
    "daisy": ("daisy flower white yellow", "hoa cúc"),
    "lily": ("lily flower white bloom", "hoa lily"),
    "jasmine": ("jasmine flower white fragrant", "hoa nhài"),
    "hibiscus": ("hibiscus flower red tropical", "hoa dâm bụt"),
    "peony": ("peony flower pink bloom", "hoa mẫu đơn"),
    "chrysanthemum": ("chrysanthemum flower mum", "hoa cúc đại đóa"),
    "magnolia": ("magnolia flower tree bloom", "hoa mộc lan"),
    "plumeria": ("plumeria frangipani flower", "hoa sứ"),
    "bougainvillea": ("bougainvillea flower colorful", "hoa giấy"),
    "marigold": ("marigold flower orange yellow", "hoa vạn thọ"),
    "carnation": ("carnation flower pink red", "hoa cẩm chướng"),
    "iris": ("iris flower purple blue", "hoa diên vĩ"),
    "poppy": ("poppy flower red field", "hoa anh túc"),
    "dandelion": ("dandelion seeds blowing", "hoa bồ công anh"),
    "violet": ("violet flower purple small", "hoa violet"),
    "camellia": ("camellia flower pink white", "hoa trà"),
    "wisteria": ("wisteria flower purple hanging", "hoa tử đằng"),
    "hydrangea": ("hydrangea flower blue pink", "hoa cẩm tú cầu"),
    "gardenia": ("gardenia flower white fragrant", "hoa dành dành"),
    "azalea": ("azalea flower bush rhododendron", "hoa đỗ quyên"),
    "daffodil": ("daffodil narcissus flower yellow", "hoa thủy tiên"),
    "bluebell": ("bluebell flower forest blue", "hoa chuông xanh"),
    "crocus": ("crocus flower spring purple", "hoa nghệ tây"),
    "amaryllis": ("amaryllis flower red bloom", "hoa loa kèn đỏ"),
    "zinnia": ("zinnia flower colorful garden", "hoa cúc zinnia"),
    "dahlia": ("dahlia flower colorful petals", "hoa thược dược"),
    "aster": ("aster flower purple daisy", "hoa cúc tím"),
    "snapdragon": ("snapdragon antirrhinum flower", "hoa mõm chó"),
    "bird of paradise": ("bird of paradise strelitzia flower", "hoa thiên điểu"),
    "water lily": ("water lily nymphaea pond", "hoa súng"),
    "morning glory": ("morning glory ipomoea vine", "hoa bìm bìm"),
    "oleander": ("oleander nerium flower pink", "hoa trúc đào"),
    "frangipani": ("frangipani plumeria flower white", "hoa đại"),

    # ===== CÂY (20 loài) =====
    "bamboo": ("bamboo forest grove green", "tre"),
    "pine tree": ("pine tree conifer forest", "cây thông"),
    "oak tree": ("oak tree large branches", "cây sồi"),
    "maple tree": ("maple tree autumn leaves red", "cây phong"),
    "palm tree": ("palm tree coconut beach", "cây cọ"),
    "willow tree": ("weeping willow tree lake", "cây liễu"),
    "baobab": ("baobab tree africa savanna", "cây bao báp"),
    "redwood": ("redwood sequoia giant tree", "cây gỗ đỏ"),
    "banyan tree": ("banyan tree ficus aerial roots", "cây đa"),
    "coconut tree": ("coconut palm tree tropical", "cây dừa"),
    "cherrytree": ("cherry tree blossom spring", "cây anh đào"),
    "bonsai": ("bonsai tree miniature japanese", "cây bonsai"),
    "mangrove": ("mangrove tree swamp roots", "cây đước"),
    "birch tree": ("birch tree white bark forest", "cây bạch dương"),
    "eucalyptus": ("eucalyptus tree gum koala", "cây bạch đàn"),
    "cedar tree": ("cedar tree conifer tall", "cây tuyết tùng"),
    "cypress tree": ("cypress tree tall evergreen", "cây bách"),
    "fig tree": ("fig tree ficus fruit", "cây sung"),
    "acacia tree": ("acacia tree africa savanna", "cây keo"),
    "teak tree": ("teak tree timber hardwood", "cây tếch"),

    # ===== RAU CỦ & CÂY NÔNG NGHIỆP (25 loài) =====
    "rice": ("rice paddy field green asia", "lúa"),
    "corn": ("corn maize field crop", "ngô"),
    "wheat": ("wheat field golden grain", "lúa mì"),
    "tea": ("tea plantation camellia sinensis", "chè"),
    "coffee": ("coffee plant arabica beans", "cà phê"),
    "cactus": ("cactus succulent desert spines", "xương rồng"),
    "mushroom": ("mushroom fungi forest", "nấm"),
    "fern": ("fern frond forest green", "dương xỉ"),
    "moss": ("moss green texture forest", "rêu"),
    "seaweed": ("seaweed kelp ocean underwater", "rong biển"),
    "aloe vera": ("aloe vera succulent gel", "nha đam"),
    "ginseng": ("ginseng panax root herb", "nhân sâm"),
    "sugarcane": ("sugarcane plantation sugar crop", "mía"),
    "cassava": ("cassava tapioca manioc root", "sắn"),
    "sweet potato": ("sweet potato ipomoea batatas", "khoai lang"),
    "potato": ("potato solanum plant tuber", "khoai tây"),
    "tomato": ("tomato plant red fruit vine", "cà chua"),
    "chili pepper": ("chili pepper capsicum red hot", "ớt"),
    "garlic": ("garlic allium bulb plant", "tỏi"),
    "onion": ("onion allium plant field", "hành tây"),
    "ginger": ("ginger zingiber root rhizome", "gừng"),
    "turmeric": ("turmeric curcuma root yellow", "nghệ"),
    "pepper vine": ("black pepper piper nigrum vine", "tiêu"),
    "soybean": ("soybean soya glycine crop", "đậu nành"),
    "cotton": ("cotton plant boll fiber", "bông vải"),

    # ===== CÂY ĂN QUẢ (36 loài) =====
    "apple tree": ("apple tree orchard fruit", "cây táo"),
    "orange tree": ("orange citrus tree fruit", "cây cam"),
    "mango tree": ("mango tree mangifera fruit", "cây xoài"),
    "banana tree": ("banana plant musa leaves", "cây chuối"),
    "grape vine": ("grape vineyard vitis wine", "cây nho"),
    "strawberry": ("strawberry plant fragaria fruit", "dâu tây"),
    "watermelon": ("watermelon citrullus field", "dưa hấu"),
    "pineapple": ("pineapple ananas plant fruit", "dứa"),
    "durian": ("durian fruit tree spiky", "sầu riêng"),
    "jackfruit": ("jackfruit large fruit tree tropical", "mít"),
    "dragon fruit": ("dragon fruit pitaya pink cactus", "thanh long"),
    "lychee": ("lychee fruit red tree cluster", "vải"),
    "pomegranate": ("pomegranate fruit red seeds", "lựu"),
    "avocado": ("avocado fruit tree green", "bơ"),
    "papaya": ("papaya fruit tree tropical orange", "đu đủ"),
    "guava": ("guava fruit tree green tropical", "ổi"),
    "passion fruit": ("passion fruit vine purple yellow", "chanh dây"),
    "starfruit": ("starfruit carambola fruit yellow", "khế"),
    "rambutan": ("rambutan fruit red hairy tropical", "chôm chôm"),
    "longan": ("longan fruit tree cluster brown", "nhãn"),
    "persimmon": ("persimmon fruit orange tree autumn", "hồng"),
    "lemon tree": ("lemon fruit tree yellow citrus", "cây chanh"),
    "peach tree": ("peach fruit tree pink blossom", "cây đào"),
    "pear tree": ("pear fruit tree green orchard", "cây lê"),
    "plum tree": ("plum fruit tree purple", "cây mận"),
    "cherry fruit": ("cherry fruit tree red spring", "cây anh đào quả"),
    "coconut": ("coconut palm tree tropical beach", "dừa"),
    "kiwi fruit": ("kiwi fruit vine green fuzzy", "cây kiwi"),
    "blueberry": ("blueberry bush fruit blue berry", "việt quất"),
    "raspberry": ("raspberry bush fruit red berry", "mâm xôi"),
    "lime tree": ("lime fruit tree green citrus", "cây chanh xanh"),
    "apricot": ("apricot fruit tree orange blossom", "cây mơ"),
    "mulberry": ("mulberry fruit tree dark purple", "cây dâu tằm"),
    "custard apple": ("custard apple sugar apple fruit green", "na"),
    "tamarind": ("tamarind fruit tree pod brown", "me"),
    "soursop": ("soursop fruit green spiky tropical", "mãng cầu xiêm"),

    # ===== CÂY HOA KIỂNG (18 loài) =====
    "succulent": ("succulent plant echeveria sedum", "sen đá"),
    "venus flytrap": ("venus flytrap dionaea carnivorous", "cây bắt ruồi"),
    "pitcher plant": ("pitcher plant nepenthes carnivorous", "cây nắp ấm"),
    "monstera": ("monstera deliciosa swiss cheese plant", "cây trầu bà"),
    "fiddle leaf fig": ("fiddle leaf fig ficus lyrata", "cây bàng singapore"),
    "rubber tree": ("rubber tree ficus elastica hevea", "cây cao su"),
    "peace lily": ("peace lily spathiphyllum white", "cây lan ý"),
    "snake plant": ("snake plant sansevieria mother in law tongue", "cây lưỡi hổ"),
    "pothos": ("pothos epipremnum devils ivy", "cây trầu bà leo"),
    "spider plant": ("spider plant chlorophytum hanging", "cây dây nhện"),
    "jade plant": ("jade plant crassula money tree", "cây ngọc bích"),
    "anthurium": ("anthurium flamingo flower red heart", "hoa hồng môn"),
    "philodendron": ("philodendron tropical houseplant", "cây ráy"),
    "calathea": ("calathea prayer plant striped leaves", "cây đuôi công"),
    "areca palm": ("areca palm dypsis lutescens", "cây cau cảnh"),
    "dracaena": ("dracaena dragon tree houseplant", "cây phát tài"),
    "zz plant": ("zz plant zamioculcas zamiifolia", "cây kim tiền"),
    "croton": ("croton codiaeum colorful leaves", "cây cô tòng"),

    # ===== BỔ SUNG - HOA =====
    "cosmos": ("cosmos flower bipinnatus pink", "hoa sao nhái"),
    "geranium": ("geranium pelargonium flower red", "hoa phong lữ"),
    "begonia": ("begonia flower colorful tuberous", "hoa thu hải đường"),
    "tuberose": ("tuberose polianthes white fragrant", "hoa huệ"),

    # ===== BỔ SUNG - CÂY =====
    "mahogany": ("mahogany swietenia tree timber", "cây gỗ gụ"),
    "spruce": ("spruce picea tree conifer", "cây vân sam"),
    "fir tree": ("fir abies tree conifer", "cây linh sam"),
    "elm tree": ("elm ulmus tree park", "cây du"),

    # ===== BỔ SUNG - RAU CỦ =====
    "carrot": ("carrot daucus orange root", "cà rốt"),
    "cabbage": ("cabbage brassica vegetable green", "bắp cải"),
    "lettuce": ("lettuce lactuca salad green", "rau xà lách"),
    "eggplant": ("eggplant aubergine solanum purple", "cà tím"),

    # ===== TIẾNG VIỆT (tương thích ngược) =====
    "hoa hồng": ("rose flower bloom", "hoa hồng"),
    "hoa sen": ("lotus flower pond", "hoa sen"),
    "hoa lan": ("orchid phalaenopsis flower", "hoa lan"),
    "tre": ("bamboo forest grove", "tre"),
    "xương rồng": ("cactus succulent desert", "xương rồng"),
    "nấm": ("mushroom fungi forest", "nấm"),
    "lúa": ("rice paddy field asia", "lúa"),
}


def get_plant_info(plant_name: str) -> tuple[str, str]:
    """Lấy thông tin thực vật: (search_term, display_name)"""
    name_lower = plant_name.lower().strip()

    # 1. Tìm chính xác
    if name_lower in PLANT_DATABASE:
        search_term, display_name = PLANT_DATABASE[name_lower]
        print(f"      [SEARCH] ✓ EXACT: '{plant_name}' -> search: '{search_term}', display: '{display_name}'")
        return search_term, display_name

    # 2. Tìm theo tên tiếng Việt
    for key, (search_term, display_name) in PLANT_DATABASE.items():
        if display_name.lower() == name_lower:
            print(f"      [SEARCH] ✓ VN_NAME: '{plant_name}' -> search: '{search_term}', display: '{display_name}'")
            return search_term, display_name

    # 3. Partial match
    for key, (search_term, display_name) in PLANT_DATABASE.items():
        key_words = set(key.split())
        name_words = set(name_lower.split())
        if key_words and key_words.issubset(name_words):
            return search_term, display_name
        if name_words and name_words.issubset(key_words):
            return search_term, display_name

    # 4. Fallback
    import unicodedata
    normalized = unicodedata.normalize('NFD', plant_name)
    is_ascii = all(ord(c) < 128 for c in normalized if c.isalpha())
    if is_ascii:
        return f"{plant_name} plant nature", plant_name

    return "plant nature flower", plant_name


async def create_plant_clip(
    plant_name: str,
    work_dir: str,
    clip_index: int,
    use_video: bool = True,
    clip_duration: float = 6.0,
    orientation: str = "landscape",
    target_width: int = 1920,
    target_height: int = 1080,
    is_first_clip: bool = False,
) -> str | None:
    """
    Tạo 1 clip về 1 loài thực vật:
    1. Tạo audio đọc tên
    2. Tìm video/ảnh từ Pexels (dùng plant-specific search)
    3. Ghép lại (KHÔNG có tiếng kêu, chỉ đọc tên)
    
    Args:
        is_first_clip: Nếu True, thêm 1s silence trước narration để tránh chồng lên intro
    """
    import edge_tts

    search_term, display_name = get_plant_info(plant_name)
    safe_name = "".join(c for c in plant_name if c.isalnum() or c in " _-").strip().replace(" ", "_")

    print(f"")
    print(f"    ╔══════════════════════════════════════════════════")
    print(f"    ║ [{clip_index}] PLANT: {plant_name}")
    print(f"    ║ Search term: '{search_term}'")
    print(f"    ║ Display (TTS): '{display_name}'")
    print(f"    ╚══════════════════════════════════════════════════")

    clip_dir = os.path.join(work_dir, f"clip_{clip_index:03d}_{safe_name}")
    os.makedirs(clip_dir, exist_ok=True)

    # ========== BƯỚC 1: Tạo audio đọc tên ==========
    text = f"Đây là ... {display_name}."
    print(f"      [STEP 1] TTS: text='{text}'")
    narration_path = os.path.join(clip_dir, f"narration_{safe_name}.mp3")

    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice=Config.TTS_VOICE,
            rate="-20%",
        )
        await communicate.save(narration_path)
    except Exception as e:
        print(f"      [TTS] Error: {e}")
        narration_path = None

    audio_duration = 0
    if narration_path and os.path.exists(narration_path) and os.path.getsize(narration_path) > 100:
        audio_duration = get_video_duration(narration_path)
        # Thêm silence padding
        # Clip đầu tiên: thêm nhiều silence trước để tránh chồng lên intro
        silence_before = 1.0 if is_first_clip else 0.3
        padded_path = os.path.join(clip_dir, f"narration_{safe_name}_padded.mp3")
        padded = add_silence_to_audio(narration_path, padded_path, silence_before=silence_before, silence_after=0.3)
        if padded:
            narration_path = padded_path
            audio_duration = get_video_duration(narration_path)
        print(f"      [TTS] OK: {audio_duration:.1f}s (silence_before={silence_before}s)")
    else:
        narration_path = None

    target_video_duration = audio_duration if narration_path else clip_duration
    print(f"      Target duration: {target_video_duration:.1f}s")

    # ========== BƯỚC 2: Tìm video/ảnh (dùng plant-specific search) ==========
    print(f"      [STEP 2] Search Pexels for: '{search_term}'")
    media_path = None
    video_clip_path = os.path.join(clip_dir, f"video_{safe_name}.mp4")

    if use_video:
        videos = await search_pexels_videos_plant(search_term, per_page=10, orientation=orientation)
        if videos:
            # video = random.choice(videos)
            unused_videos = [v for v in videos if v["id"] not in USED_VIDEO_IDS]

            if unused_videos:
                video = random.choice(unused_videos)
                USED_VIDEO_IDS.add(video["id"])
            else:
                print("      [STEP 2] ⚠ All videos used, fallback random")
                video = random.choice(videos) if videos else None
            print(f"      [STEP 2] ✓ VIDEO selected: id={video['id']}, {video.get('width','?')}x{video.get('height','?')}")
            print(f"      [STEP 2]   URL: {video['url'][:100]}...")
            raw_video = os.path.join(clip_dir, f"raw_{safe_name}.mp4")
            downloaded = await download_file(video["url"], raw_video)
            if downloaded:
                print(f"      [STEP 2]   Downloaded -> {raw_video}")
                media_path = resize_video_for_short(raw_video, video_clip_path, target_video_duration,
                                                     target_width, target_height)
        else:
            print(f"      [STEP 2] ✗ No videos found")

    if not media_path:
        print(f"      [STEP 2] Fallback to IMAGE search...")
        images = await search_pexels_images(search_term, per_page=10, orientation=orientation)
        if images:
            image = random.choice(images)
            print(f"      [STEP 2] ✓ IMAGE selected: id={image['id']}, {image.get('width','?')}x{image.get('height','?')}")
            print(f"      [STEP 2]   URL: {image['url'][:100]}...")
            raw_image = os.path.join(clip_dir, f"raw_{safe_name}.jpg")
            image_url = image.get("url_portrait" if orientation == "portrait" else "url_landscape", image["url"])
            downloaded = await download_file(image_url, raw_image)
            if downloaded:
                print(f"      [STEP 2]   Downloaded -> {raw_image}")
                media_path = create_image_video(raw_image, video_clip_path, target_video_duration,
                                                 target_width, target_height)
        else:
            print(f"      [STEP 2] ✗ No images found either")

    if not media_path:
        print(f"      [!] FAILED: Could not find any media for '{plant_name}'")
        return None

    print(f"      [STEP 2] Media ready: {media_path}")

    # ========== BƯỚC 3: Ghép audio vào video ==========
    if not narration_path:
        print(f"      [STEP 3] No narration, returning video only")
        return media_path

    print(f"      [STEP 3] Merge: video={os.path.basename(media_path)} + audio={os.path.basename(narration_path)}")
    final_clip = os.path.join(clip_dir, f"final_{safe_name}.mp4")
    video_duration = get_video_duration(media_path)

    cmd = [
        "ffmpeg", "-y",
        "-i", media_path, "-i", narration_path,
        "-filter_complex",
        f"[1:a]aresample=44100,apad=whole_dur={video_duration},volume=1.5[aout]",
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-video_track_timescale", "24000",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-t", str(video_duration),
        "-avoid_negative_ts", "make_zero",
        "-fflags", "+genpts",
        "-movflags", "+faststart",
        final_clip,
    ]
    merge_result = subprocess.run(cmd, capture_output=True, text=True)

    if os.path.exists(final_clip) and os.path.getsize(final_clip) > 1000:
        final_dur = get_video_duration(final_clip)
        size_kb = os.path.getsize(final_clip) / 1024
        print(f"      [STEP 3] ✓ Final clip: {final_clip}")
        print(f"      [STEP 3]   Duration: {final_dur:.1f}s, Size: {size_kb:.1f}KB")
        print(f"      ✅ DONE [{clip_index}] {plant_name} -> TTS:'{display_name}' -> {final_clip}")
        return final_clip

    print(f"      [STEP 3] ✗ Merge failed: {merge_result.stderr[:200] if merge_result.stderr else 'unknown'}")
    return media_path


def add_background_music(video_path: str, output_path: str,
                          music_path: str = "sounds/plants/plants.mp3",
                          music_volume: float = 0.15) -> str | None:
    """
    Thêm nhạc nền vào video.
    Nếu video dài hơn nhạc -> lặp lại nhạc.
    Nếu video ngắn hơn -> cắt nhạc.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    music_abs = os.path.join(base_dir, music_path) if not os.path.isabs(music_path) else music_path

    if not os.path.exists(music_abs):
        print(f"      [BGM] Music not found: {music_abs}")
        return None

    video_duration = get_video_duration(video_path)
    print(f"      [BGM] Video: {video_duration:.1f}s, Music: {music_abs}")

    # -stream_loop -1: lặp vô hạn nhạc nền
    # amix: trộn narration gốc (volume giữ nguyên) + nhạc nền (volume nhỏ)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-i", music_abs,
        "-filter_complex",
        f"[1:a]volume={music_volume}[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2,volume=1.5[aout]",
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-t", str(video_duration),
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"      [BGM] Error: {result.stderr[:300]}")
        return None

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        print(f"      [BGM] OK: {output_path}")
        return output_path

    return None


def generate_plant_scripts(user_prompt: str, num_videos: int = 1, plants_per_video: int = 10) -> list[dict]:
    """Tạo danh sách thực vật random từ database."""
    all_plants = [k for k in PLANT_DATABASE.keys() if not any(ord(c) > 127 for c in k)]
    print(f"  [PLANT] Total plants in DATABASE: {len(all_plants)}")

    random.shuffle(all_plants)

    videos = []
    used = set()

    for i in range(num_videos):
        available = [p for p in all_plants if p not in used]
        if len(available) < plants_per_video:
            used.clear()
            available = all_plants.copy()
            random.shuffle(available)

        selected = available[:plants_per_video]
        used.update(selected)

        if plants_per_video >= 10:
            title = f"Thế giới thực vật - {plants_per_video} loài"
        else:
            title = "Khám phá thực vật"

        videos.append({
            "title": title,
            "theme": "plants",
            "plants": selected,
        })
        print(f"  [PLANT] Video {i+1}: {title} -> {len(selected)} plants")

    return videos
