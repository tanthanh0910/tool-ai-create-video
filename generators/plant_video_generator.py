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

# Những loại cây/quả HIẾM trên Pexels (chủ yếu châu Á)
# Video thường sai → ưu tiên dùng ảnh hoặc search term thay thế
RARE_PLANTS_ON_PEXELS = {
    "longan": "longan fruit exotic",
    "lychee": "lychee fruit red", 
    "rambutan": "rambutan fruit red",
    "starfruit": "star fruit carambola",
    "soursop": "soursop fruit green",
    "custard apple": "sugar apple fruit",
    "tamarind": "tamarind fruit pod",
    "jackfruit": "jackfruit large fruit",
    "durian": "durian fruit spike",
    "mangosteen": "mangosteen fruit purple",
    "persimmon": "persimmon fruit orange",
    "mulberry": "mulberry berry fruit",
    "guava": "guava fruit tropical",
    "papaya": "papaya fruit orange",
    "passion fruit": "passion fruit purple",
    "dragon fruit": "dragon fruit pink",
}

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
    - Bỏ video có tên cây/quả khác trong URL (chỉ những tên rõ ràng)
    
    Ví dụ: plant_core="starfruit" → skip video có URL chứa "banana", "orange", "lemon"
    """
    if not plant_core:
        return videos
    
    # Từ khóa liên quan đến người - SKIP những video này
    people_keywords = {
        "person", "people", "woman", "man", "girl", "boy", "child", "children",
        "human", "farmer", "gardener", "worker", "tourist", "couple", "family",
        "holding", "picking", "harvesting", "eating", "cooking",
    }
    
    # Danh sách các loại cây/quả phổ biến - CHỈ những tên dài, rõ ràng để tránh match nhầm
    # Không dùng: "corn" (match "acorn"), "pea" (match "peach"), "fig" (match "figure")
    common_plants = {
        # Cây ăn quả (tên dài, ít nhầm)
        "banana", "papaya", "mango", "coconut", "pineapple", "durian", "jackfruit",
        "avocado", "rambutan", "lychee", "longan", "starfruit", "mangosteen",
        "orange", "lemon", "apple", "grape", "cherry", "peach", "pomegranate",
        "strawberry", "blueberry", "raspberry", "watermelon", "persimmon",
        # Rau củ (tên dài, ít nhầm)
        "tomato", "potato", "carrot", "cabbage", "lettuce", "onion", "garlic",
        "ginger", "cassava", "sugarcane", "soybean", "cotton", "coffee",
        "cucumber", "eggplant", "pumpkin",
        # Hoa (tên dài, ít nhầm)
        "tulip", "orchid", "lotus", "sunflower", "lavender", "jasmine",
        "hibiscus", "chrysanthemum", "magnolia", "dandelion",
        # Cây gỗ (tên dài, ít nhầm)
        "bamboo", "eucalyptus", "mahogany", "redwood",
    }
    
    plant_words = set(plant_core.lower().split())
    
    exact_matches = []
    neutral_matches = []
    
    for v in videos:
        url = v.get("page_url", v.get("url", "")).lower()
        
        # 1. Kiểm tra URL có chứa từ khóa về NGƯỜI không → SKIP
        found_people = False
        for people_word in people_keywords:
            # Chỉ match whole word để tránh nhầm (dùng dấu - hoặc / hoặc đầu/cuối)
            if f"-{people_word}-" in url or f"/{people_word}-" in url or f"-{people_word}/" in url:
                print(f"        [VALIDATE] SKIP id={v.get('id')} - URL contains PEOPLE keyword '{people_word}'")
                found_people = True
                break
        
        if found_people:
            continue
        
        # 2. Kiểm tra URL có chứa tên cây/quả KHÁC không → SKIP
        # Chỉ check những tên dài (>=5 ký tự) để tránh false positive
        found_wrong_plant = False
        for other_plant in common_plants:
            if len(other_plant) >= 5 and other_plant in url and other_plant not in plant_words:
                print(f"        [VALIDATE] SKIP id={v.get('id')} - URL contains '{other_plant}' (want '{plant_core}')")
                found_wrong_plant = True
                break
        
        if found_wrong_plant:
            continue
        
        # 3. Phân loại: EXACT MATCH vs NEUTRAL
        if any(pw in url for pw in plant_words if len(pw) >= 4):
            print(f"        [VALIDATE] ✓ EXACT MATCH id={v.get('id')} - URL contains '{plant_core}'")
            exact_matches.append(v)
        else:
            print(f"        [VALIDATE] ~ NEUTRAL id={v.get('id')} - URL neutral")
            neutral_matches.append(v)
    
    # Ưu tiên EXACT MATCH, nhưng chấp nhận NEUTRAL nếu không có EXACT
    if exact_matches:
        print(f"        [VALIDATE] Returning {len(exact_matches)} EXACT matches (ignoring {len(neutral_matches)} neutral)")
        return exact_matches
    elif neutral_matches:
        # Trả về tất cả NEUTRAL (không giới hạn) để có đủ video chọn
        print(f"        [VALIDATE] No exact matches, returning {len(neutral_matches)} NEUTRAL")
        return neutral_matches
    else:
        return []


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
    "palm tree": ("Majestic Palm Tree Against Clear Blue Sky", "cây cọ"),
    "willow tree": ("weeping willow tree lake", "cây liễu"),
    "redwood": ("redwood sequoia giant tree", "cây gỗ đỏ"),
    "banyan tree": ("banyan tree ficus aerial roots", "cây đa"),
    "cherrytree": ("cherry tree blossom spring", "cây anh đào"),
    "bonsai": ("bonsai tree miniature japanese", "cây bonsai"),
    "mangrove": ("mangrove tree swamp roots", "cây đước"),
    "birch tree": ("birch tree white bark forest", "cây bạch dương"),
    "eucalyptus": ("eucalyptus tree gum koala", "cây bạch đàn"),
    "cedar tree": ("cedar tree conifer tall", "cây tuyết tùng"),
    "fig tree": ("fig tree ficus fruit", "cây sung"),
    "acacia tree": ("Lush Green Tree in Sunny Outdoor Landscape", "cây keo"),
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
    "sugarcane": ("sugarcane plantation sugar crop", "mía"),
    "cassava": ("cassava tapioca manioc root", "sắn"),
    "sweet potato": ("sweet potato tuber root", "khoai lang"),
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
    "apple tree": ("apple tree orchard", "táo"),
    "orange tree": ("Close-Up of Lush Orange Tree in Orchard", "cam"),
    "mango tree": ("mango tree fruit", "xoài"),
    "banana tree": ("banana tree plant", "chuối"),
    "grape vine": ("grape vineyard", "nho"),
    "strawberry": ("strawberry fruit plant", "dâu tây"),
    "watermelon": ("watermelon field", "dưa hấu"),
    "jackfruit": ("jackfruit tree", "mít"),
    "dragon fruit": ("dragon fruit pitaya", "thanh long"),
    # "lychee": ("lychee fruit asian", "vải"),
    "pomegranate": ("pomegranate fruit", "lựu"),
    "avocado": ("avocado tree fruit", "bơ"),
    "papaya": ("papaya tree fruit", "đu đủ"),
    "guava": ("guava fruit", "ổi"),
    "passion fruit": ("passion fruit maracuja", "chanh dây"),
    "starfruit": ("starfruit carambola", "khế"),
    # "longan": ("longan fruit asian", "nhãn"),
    "persimmon": ("persimmon fruit", "hồng"),
    "lemon tree": ("lemon tree citrus", "chanh"),
    "peach tree": ("peach tree fruit", "đào"),
    # "pear tree": ("pear fruit tree", "lê"),
    "plum tree": ("plum tree fruit", "mận"),
    "cherry fruit": ("cherry tree fruit", "anh đào quả"),
    "coconut": ("coconut palm", "dừa"),
    "kiwi fruit": ("kiwi fruit", "kiwi"),
    "blueberry": ("blueberry bush", "việt quất"),
    "raspberry": ("raspberry bush", "mâm xôi"),
    "lime tree": ("lime tree citrus", "chanh xanh"),
    "mulberry": ("mulberry tree fruit", "dâu tằm"),
    "custard apple": ("custard apple sugar apple fruit green", "na"),
    "tamarind": ("tamarind fruit tree pod brown", "me"),

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
    "philodendron": ("philodendron tropical houseplant", "cây ráy"),
    "calathea": ("calathea prayer plant striped leaves", "cây đuôi công"),
    "areca palm": ("areca palm dypsis lutescens", "cây cau cảnh"),
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

    # ===== PHỔ BIẾN CHÂU ÂU & DỄ TÌM TRÊN PEXELS =====
    # --- Hoa phổ biến châu Âu ---
    "wildflower": ("wildflower meadow field colorful", "hoa dại"),
    "heather": ("heather calluna purple field", "hoa thạch nam"),
    "clover": ("clover flower field green", "cỏ ba lá"),
    "buttercup": ("buttercup ranunculus yellow flower", "hoa mao lương"),
    "foxglove": ("foxglove digitalis purple flower", "hoa mao địa hoàng"),
    "primrose": ("primrose primula yellow spring", "hoa anh thảo"),
    "cornflower": ("cornflower blue centaurea field", "hoa thanh cúc"),
    "edelweiss": ("edelweiss alpine white flower", "hoa nhung tuyết"),
    "forget me not": ("forget me not myosotis blue", "hoa lưu ly"),
    "snowdrop": ("snowdrop galanthus white spring", "hoa giọt tuyết"),
    "lily of the valley": ("lily of the valley convallaria white", "hoa linh lan"),
    "red clover": ("red clover trifolium pink flower", "cỏ ba lá đỏ"),
    "sweet pea": ("sweet pea lathyrus colorful flower", "hoa đậu thơm"),
    "freesia": ("freesia flower colorful fragrant", "hoa lan nam phi"),
    "anemone": ("anemone flower windflower colorful", "hoa cỏ chân ngỗng"),
    "ranunculus": ("ranunculus flower persian buttercup", "hoa mao lương ba tư"),
    "delphinium": ("delphinium larkspur blue purple", "hoa phi yến"),
    "hollyhock": ("hollyhock alcea tall flower garden", "hoa mãn đình hồng"),
    "sweet william": ("sweet william dianthus colorful flower", "hoa william ngọt"),
    "stock flower": ("stock flower matthiola fragrant", "hoa tử la lan"),
    
    # --- Cây & rừng châu Âu ---
    "olive tree": ("olive tree mediterranean olea", "cây ô liu"),
    "apple blossom": ("apple blossom spring white pink", "hoa táo"),
    "hawthorn": ("hawthorn crataegus white flower", "cây táo gai"),
    "holly": ("holly ilex red berries christmas", "cây nhựa ruồi"),
    "ivy": ("ivy hedera green vine climbing", "cây thường xuân"),
    "mistletoe": ("mistletoe viscum christmas plant", "cây tầm gửi"),
    "boxwood": ("boxwood buxus hedge garden", "cây hoàng dương"),
    "yew tree": ("yew tree taxus evergreen", "cây thủy tùng"),
    "chestnut tree": ("chestnut tree castanea leaves", "cây hạt dẻ"),
    "beech tree": ("beech tree fagus forest leaves", "cây sồi dẻ"),
    "ash tree": ("ash tree fraxinus forest", "cây tần bì"),
    "alder tree": ("alder tree alnus wetland", "cây tổng quán sủi"),
    "juniper": ("juniper juniperus berries evergreen", "cây bách xù"),
    "hazel tree": ("hazel corylus nuts tree", "cây phỉ"),
    
    # --- Hoa & cây địa trung hải ---
    "bougainvillea pink": ("bougainvillea pink mediterranean", "hoa giấy hồng"),
    "oleander white": ("oleander nerium white mediterranean", "hoa trúc đào trắng"),
    "agave": ("agave succulent mediterranean blue", "cây thùa"),
    "rosemary": ("rosemary rosmarinus herb purple flower", "cây hương thảo"),
    "thyme": ("thyme thymus herb purple flower", "cây cỏ xạ hương"),
    "sage": ("sage salvia purple herb flower", "cây xô thơm"),
    "oregano": ("oregano origanum herb flower", "cây kinh giới"),
    "basil": ("basil ocimum herb green", "cây húng quế"),
    "mint": ("mint mentha herb green fresh", "cây bạc hà"),
    "parsley": ("parsley petroselinum herb green", "cây mùi tây"),
    "fennel": ("fennel foeniculum yellow flower herb", "cây thì là"),
    "dill": ("dill anethum yellow flower herb", "cây thì là"),
    "chamomile": ("chamomile matricaria white flower field", "hoa cúc la mã"),
    
    # --- Hoa vườn phổ biến (nhiều trên Pexels) ---
    "petunia": ("petunia flower colorful garden hanging", "hoa dạ yến thảo"),
    "pansy": ("pansy viola flower colorful garden", "hoa bướm"),
    "impatiens": ("impatiens flower colorful shade garden", "hoa ngọc thạch"),
    "salvia": ("salvia sage red flower garden", "hoa xô đỏ"),
    "verbena": ("verbena flower purple cluster", "hoa cỏ roi ngựa"),
    "gazania": ("gazania flower orange yellow daisy", "hoa cúc gazania"),
    "gerbera": ("gerbera daisy flower colorful", "hoa đồng tiền"),
    "gladiolus": ("gladiolus flower spike colorful", "hoa lay ơn"),
    "hyacinth": ("hyacinth flower fragrant spring colorful", "hoa dạ lan hương"),
    "muscari": ("muscari grape hyacinth blue spring", "hoa tiên ông"),
    "allium": ("allium ornamental purple ball flower", "hoa hành tây tím"),
    "clematis": ("clematis flower vine climbing purple", "hoa ông lão"),
    "honeysuckle": ("honeysuckle lonicera flower fragrant", "hoa kim ngân"),
    "lilac": ("lilac syringa purple fragrant spring", "hoa tử đinh hương"),
    
    # --- Cây cảnh phổ biến (indoor plants - rất nhiều trên Pexels) --- 
    "dieffenbachia": ("dieffenbachia dumb cane tropical indoor", "cây vạn niên thanh"),
    "aglaonema": ("aglaonema chinese evergreen indoor", "cây bạc hà"),
    "palm indoor": ("indoor palm plant tropical", "cây cọ trong nhà"),
    "boston fern": ("boston fern nephrolepis hanging", "dương xỉ boston"),
    "bird nest fern": ("bird nest fern asplenium tropical", "dương xỉ tổ chim"),
    "string of pearls": ("string of pearls senecio succulent", "cây chuỗi ngọc"),
    "english ivy": ("english ivy hedera helix indoor", "cây thường xuân anh"),
    "golden pothos": ("golden pothos epipremnum aureum", "cây trầu bà vàng"),
    "money plant": ("money plant pilea peperomioides", "cây đồng tiền"),
    "swiss cheese plant": ("swiss cheese plant monstera adansonii", "cây trầu bà lỗ"),
    "chinese money plant": ("chinese money plant pilea peperomioides", "cây tiền xu"),
    
    # --- Cây hoa ngoài trời dễ tìm ---
    "rhododendron": ("rhododendron bush flower pink purple", "hoa đỗ quyên"),
    "camellia bush": ("camellia bush japonica flower pink", "hoa trà mi"),
    "forsythia": ("forsythia yellow spring bush", "cây mai vàng"),
    "spirea": ("spirea spiraea white flower bush", "cây tú cầu"),
    "viburnum": ("viburnum snowball bush white flower", "cây hoa cầu tuyết"),
    "weigela": ("weigela bush pink flower garden", "hoa nhài tây"),
    "butterfly bush": ("butterfly bush buddleia purple", "cây bướm"),
    
    # --- Cây nông nghiệp châu Âu ---
    "barley": ("barley field grain crop golden", "lúa mạch"),
    "oat": ("oat avena field grain crop", "yến mạch"),
    "rapeseed": ("rapeseed canola yellow field", "cây cải dầu"),
    "sunflower field": ("sunflower field yellow landscape", "cánh đồng hướng dương"),
    "vineyard": ("vineyard grape wine field", "vườn nho"),
    "flax": ("flax linum blue flower field", "cây lanh"),

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
    skip_narration: bool = False,
) -> str | None:
    """
    Tạo 1 clip về 1 loài thực vật:
    1. Tạo audio đọc tên (nếu skip_narration=False)
    2. Tìm video/ảnh từ Pexels (dùng plant-specific search)
    3. Ghép lại (KHÔNG có tiếng kêu, chỉ đọc tên nếu có)
    
    Args:
        is_first_clip: Nếu True, thêm 1s silence trước narration để tránh chồng lên intro
        skip_narration: Nếu True, không đọc tên (dùng cho shorts)
    """
    import edge_tts

    search_term, display_name = get_plant_info(plant_name)
    safe_name = "".join(c for c in plant_name if c.isalnum() or c in " _-").strip().replace(" ", "_")

    print(f"")
    print(f"    ╔══════════════════════════════════════════════════")
    print(f"    ║ PLANT CLIP #{clip_index}: {plant_name}")
    print(f"    ║ Search term: {search_term}")
    print(f"    ║ Display name: {display_name}")
    print(f"    ║ Skip narration: {skip_narration}")
    print(f"    ╚══════════════════════════════════════════════════")

    clip_dir = os.path.join(work_dir, f"clip_{clip_index:03d}_{safe_name}")
    os.makedirs(clip_dir, exist_ok=True)

    # ========== BƯỚC 1: Tạo audio đọc tên (nếu không skip) ==========
    narration_path = None
    audio_duration = clip_duration
    
    if skip_narration:
        print(f"      [STEP 1] SKIP narration (shorts mode)")
    else:
        narration_path = os.path.join(clip_dir, f"narration_{safe_name}.mp3")
        narration_text = display_name
        
        print(f"      [STEP 1] Generate TTS for: '{narration_text}'")
        try:
            communicate = edge_tts.Communicate(narration_text, "vi-VN-HoaiMyNeural")
            await communicate.save(narration_path)
            audio_duration = get_video_duration(narration_path)
            
            # Thêm silence trước và sau narration để người xem có thời gian xem ảnh/video
            silence_before = 1.0 if is_first_clip else 0.5
            silence_after = 4.0  # Tăng thời gian im lặng sau khi đọc tên
            padded_path = os.path.join(clip_dir, f"narration_{safe_name}_padded.mp3")
            padded = add_silence_to_audio(narration_path, padded_path, silence_before=silence_before, silence_after=silence_after)
            if padded:
                narration_path = padded_path
                audio_duration = get_video_duration(narration_path)
            print(f"      [TTS] OK: {audio_duration:.1f}s (silence_before={silence_before}s, silence_after={silence_after}s)")
        except Exception as e:
            print(f"      [TTS] ERROR: {e}")
            audio_duration = clip_duration
            narration_path = None

    # Nếu skip_narration (shorts mode), LUÔN dùng clip_duration từ người dùng
    if skip_narration:
        target_video_duration = clip_duration
        print(f"      [SHORTS] Force video duration: {target_video_duration:.1f}s (user setting)")
    else:
        target_video_duration = audio_duration if narration_path else clip_duration
    print(f"      Target duration: {target_video_duration:.1f}s")

    # ========== BƯỚC 2: Tìm video/ảnh (dùng plant-specific search) ==========
    print(f"      [STEP 2] Search Pexels for: '{search_term}'")
    media_path = None
    video_clip_path = os.path.join(clip_dir, f"video_{safe_name}.mp4")

    # Kiểm tra nếu là cây hiếm trên Pexels → dùng search term thay thế
    plant_key = plant_name.lower().strip()
    alt_search_term = RARE_PLANTS_ON_PEXELS.get(plant_key, None)
    if alt_search_term:
        print(f"      [STEP 2] ⚠ '{plant_name}' is RARE on Pexels, trying alternate: '{alt_search_term}'")

    if use_video:
        videos = await search_pexels_videos_plant(search_term, per_page=10, orientation=orientation)
        
        # Nếu không có video và là cây hiếm → thử search term thay thế
        if not videos and alt_search_term:
            print(f"      [STEP 2] Trying alternate search: '{alt_search_term}'")
            videos = await search_pexels_videos_plant(alt_search_term, per_page=10, orientation=orientation)
        
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
        
        # Nếu không có ảnh và là cây hiếm → thử search term thay thế
        if not images and alt_search_term:
            print(f"      [STEP 2] Trying alternate image search: '{alt_search_term}'")
            images = await search_pexels_images(alt_search_term, per_page=10, orientation=orientation)
        
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
    Hỗ trợ video có hoặc không có audio track.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    music_abs = os.path.join(base_dir, music_path) if not os.path.isabs(music_path) else music_path

    if not os.path.exists(music_abs):
        print(f"      [BGM] Music not found: {music_abs}")
        return None

    video_duration = get_video_duration(video_path)
    print(f"      [BGM] Video: {video_duration:.1f}s, Music: {music_abs}")

    # Kiểm tra video có audio track không
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "a", video_path,
    ]
    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
    has_audio = False
    try:
        probe_data = json.loads(probe_result.stdout)
        has_audio = len(probe_data.get("streams", [])) > 0
    except:
        pass
    
    print(f"      [BGM] Video has audio: {has_audio}")

    if has_audio:
        # Video có audio -> mix với nhạc nền
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
    else:
        # Video KHÔNG có audio (shorts mode) -> chỉ thêm nhạc nền
        print(f"      [BGM] Video has NO audio, adding music only")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-stream_loop", "-1", "-i", music_abs,
            "-filter_complex",
            f"[1:a]volume={music_volume * 3}[aout]",  # Tăng volume vì không có audio khác
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
