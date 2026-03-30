"""
Animal Video Generator - Tạo video về động vật với hình ảnh/video thực tế.

Features:
- Tìm ảnh/video thực từ Pexels API (miễn phí)
- Tải tiếng kêu động vật từ Freesound (nếu có)
- Đọc tên động vật bằng Edge TTS
- Ghép thành video hoàn chỉnh
"""

import asyncio
import aiohttp
import os
import json
import random
import subprocess
from config import Config

# Pexels API (miễn phí, 200 requests/giờ)
PEXELS_API_KEY = Config.PEXELS_API_KEY or os.getenv("PEXELS_API_KEY", "")

# ============================================================
# ANIMAL DATABASE
# Key: tên nhập (tiếng Anh hoặc tiếng Việt)
# Value: (search_term_tiếng_Anh, tên_đọc_tiếng_Việt)
# ============================================================
# KHUYẾN KHÍCH NHẬP TIẾNG ANH để search chính xác!
# Ví dụ: "lion, tiger, elephant" thay vì "sư tử, hổ, voi"
# ============================================================

ANIMAL_DATABASE = {
    # ===== ĐỘNG VẬT HOANG DÃ CHÂU PHI =====
    "lion": ("lion wild safari", "sư tử"),
    "tiger": ("tiger wild jungle", "hổ"),
    "elephant": ("elephant wild safari", "voi"),
    "giraffe": ("giraffe wild safari", "hươu cao cổ"),
    "zebra": ("zebra wild safari", "ngựa vằn"),
    "rhinoceros": ("rhinoceros wild safari", "tê giác"),
    "hippo": ("hippopotamus wild river", "hà mã"),
    "leopard": ("leopard wild safari", "báo"),
    "cheetah": ("cheetah running wild", "báo săn"),
    "jaguar": ("jaguar wild jungle", "báo đốm"),
    "antelope": ("antelope wild safari", "linh dương"),
    "buffalo": ("buffalo wild safari", "trâu rừng"),
    "wildebeest": ("wildebeest migration safari", "linh dương đầu bò"),
    
    # ===== GẤU =====
    "bear": ("bear wild forest", "gấu"),
    "panda": ("panda bear eating bamboo", "gấu trúc"),
    "polar bear": ("polar bear arctic ice", "gấu bắc cực"),
    "brown bear": ("brown bear wild river", "gấu nâu"),
    "black bear": ("black bear wild forest", "gấu đen"),
    "grizzly": ("grizzly bear wild river", "gấu xám"),

    # ===== CHÓ SÓI, CÁO =====
    "wolf": ("wolf wild forest pack", "sói"),
    "fox": ("fox wild forest", "cáo"),
    "red fox": ("red fox wild", "cáo đỏ"),
    "arctic fox": ("arctic fox snow white", "cáo bắc cực"),
    "fennec fox": ("fennec fox desert ears", "cáo fennec"),
    "coyote": ("coyote wild prairie", "sói đồng cỏ"),

    # ===== KHỈ, VƯỢN =====
    "monkey": ("monkey wild tree jungle", "khỉ"),
    "chimpanzee": ("chimpanzee wild jungle", "tinh tinh"),
    "chimp": ("chimpanzee wild jungle", "tinh tinh"),
    "orangutan": ("orangutan wild borneo jungle", "đười ươi"),
    "gorilla": ("gorilla wild jungle", "khỉ đột"),
    "gibbon": ("gibbon swinging tree jungle", "vượn"),
    "baboon": ("baboon wild safari", "khỉ đầu chó"),
    "lemur": ("lemur madagascar wild", "vượn cáo"),
    "macaque": ("macaque monkey wild", "khỉ mặt đỏ"),
    
    # ===== ĐỘNG VẬT BIỂN =====
    "dolphin": ("dolphin jumping ocean", "cá heo"),
    "whale": ("whale underwater ocean", "cá voi"),
    "blue whale": ("blue whale underwater", "cá voi xanh"),
    "humpback whale": ("humpback whale jumping ocean", "cá voi lưng gù"),
    "orca": ("orca killer whale underwater", "cá voi sát thủ"),
    "shark": ("shark underwater ocean", "cá mập"),
    "great white shark": ("great white shark underwater", "cá mập trắng"),
    "hammerhead shark": ("hammerhead shark underwater", "cá mập đầu búa"),
    "sea turtle": ("sea turtle swimming underwater", "rùa biển"),
    "turtle": ("turtle walking grass", "rùa"),
    "seal": ("seal swimming underwater", "hải cẩu"),
    "sea lion": ("sea lion swimming ocean", "sư tử biển"),
    "walrus": ("walrus arctic ice", "hải mã"),
    "manatee": ("manatee swimming underwater", "lợn biển"),
    "dugong": ("dugong swimming underwater", "bò biển"),
    "seahorse": ("seahorse underwater close up", "cá ngựa"),
    "octopus": ("octopus underwater close up", "bạch tuộc"),
    "jellyfish": ("jellyfish underwater glowing", "sứa"),
    "starfish": ("starfish underwater ocean floor", "sao biển"),
    "clownfish": ("clownfish anemone underwater", "cá hề"),
    "manta ray": ("manta ray swimming underwater", "cá đuối"),
    "stingray": ("stingray swimming underwater", "cá đuối gai"),
    "crab": ("crab beach sand walking alive", "cua"),
    "lobster": ("lobster reef underwater marine", "tôm hùm"),
    "shrimp": ("shrimp marine life ocean reef", "tôm"),
    "coral": ("coral reef underwater colorful", "san hô"),
    "penguin": ("penguin colony antarctic", "chim cánh cụt"),
    
    # ===== CHIM =====
    "eagle": ("eagle bird raptor", "đại bàng"),
    "bald eagle": ("bald eagle bird america", "đại bàng đầu trắng"),
    "hawk": ("hawk bird raptor", "chim ưng"),
    "falcon": ("peregrine falcon bird raptor", "chim cắt"),
    "owl": ("owl bird nocturnal", "cú"),
    "flamingo": ("flamingo bird pink lake", "chim hồng hạc"),
    "peacock": ("peacock bird feathers display", "chim công"),
    "parrot": ("parrot bird colorful tropical", "vẹt"),
    "macaw": ("macaw parrot colorful bird", "vẹt đuôi dài"),
    "toucan": ("toucan bird colorful beak", "chim toucan"),
    "hummingbird": ("hummingbird bird flower nectar", "chim ruồi"),
    "swan": ("swan bird lake", "thiên nga"),
    "pelican": ("pelican bird", "bồ nông"),
    "crane": ("crane bird wetland", "hạc"),
    "heron": ("heron bird water", "diệc"),
    "stork": ("stork bird nest", "cò"),
    "vulture": ("vulture bird scavenger", "kền kền"),
    "crow": ("crow bird black", "quạ"),
    "raven": ("raven bird black", "quạ đen"),
    "sparrow": ("sparrow bird small branch", "chim sẻ"),
    "pigeon": ("pigeon bird", "bồ câu"),
    "dove": ("dove bird white", "chim bồ câu trắng"),
    "robin": ("robin bird red breast branch", "chim cổ đỏ"),
    "kingfisher": ("kingfisher bird colorful", "chim bói cá"),
    "woodpecker": ("woodpecker bird tree", "chim gõ kiến"),
    "chicken": ("chicken hen farm", "gà"),
    "rooster": ("rooster crowing farm", "gà trống"),
    "duck": ("duck bird pond swimming", "vịt"),
    "goose": ("goose bird", "ngỗng"),
    "turkey": ("turkey bird farm gobbler", "gà tây"),

    # ===== ĐỘNG VẬT ÚC =====
    "kangaroo": ("kangaroo australia hopping", "chuột túi"),
    "koala": ("koala tree eucalyptus", "gấu túi"),
    "platypus": ("platypus swimming australia", "thú mỏ vịt"),
    "wombat": ("wombat australia", "gấu túi mũi trần"),
    "tasmanian devil": ("tasmanian devil animal", "quỷ tasmania"),
    "emu": ("emu bird australia", "đà điểu Úc"),
    "kiwi bird": ("kiwi bird flightless nocturnal", "chim kiwi"),
    
    # ===== BÒ SÁT =====
    "snake": ("snake reptile close up", "rắn"),
    "cobra": ("cobra snake hood spread", "rắn hổ mang"),
    "python": ("python snake coiled", "trăn"),
    "anaconda": ("anaconda snake water", "trăn anaconda"),
    "viper": ("viper snake venomous close up", "rắn lục"),
    "crocodile": ("crocodile river close up", "cá sấu"),
    "alligator": ("alligator swamp close up", "cá sấu mỹ"),
    "lizard": ("lizard reptile close up", "thằn lằn"),
    "chameleon": ("chameleon reptile colorful close up", "tắc kè hoa"),
    "iguana": ("iguana green reptile close up", "kỳ nhông"),
    "komodo dragon": ("komodo dragon reptile close up", "rồng komodo"),
    "gecko": ("gecko lizard close up", "tắc kè"),
    "tortoise": ("tortoise land turtle close up", "rùa cạn"),
    "frog": ("frog green close up", "ếch"),
    "toad": ("toad amphibian close up", "cóc"),
    "salamander": ("salamander amphibian close up", "kỳ giông"),
    
    # ===== ĐỘNG VẬT NHÀ =====
    "cat": ("cat close up face", "mèo"),
    "kitten": ("kitten cute close up", "mèo con"),
    "dog": ("dog close up face", "chó"),
    "puppy": ("puppy cute close up", "chó con"),
    "rabbit": ("rabbit close up grass", "thỏ"),
    "bunny": ("bunny rabbit close up", "thỏ"),
    "hamster": ("hamster close up cute", "chuột hamster"),
    "guinea pig": ("guinea pig close up", "chuột lang"),
    "goldfish": ("goldfish aquarium underwater", "cá vàng"),
    "parrot pet": ("parrot bird close up colorful", "vẹt"),

    # ===== ĐỘNG VẬT TRANG TRẠI =====
    "cow": ("cow grass field farm", "bò"),
    "bull": ("bull close up farm", "bò đực"),
    "pig": ("pig farm close up", "lợn"),
    "horse": ("horse running field", "ngựa"),
    "pony": ("pony close up field", "ngựa con"),
    "donkey": ("donkey close up farm", "lừa"),
    "sheep": ("sheep flock grass field", "cừu"),
    "lamb": ("lamb close up grass", "cừu con"),
    "goat": ("goat close up farm", "dê"),
    "llama": ("llama close up field", "lạc đà không bướu"),
    "alpaca": ("alpaca close up face", "alpaca"),
    
    # ===== CÔN TRÙNG =====
    "butterfly": ("butterfly flower close up macro", "bướm"),
    "bee": ("bee flower close up macro", "ong"),
    "dragonfly": ("dragonfly close up macro", "chuồn chuồn"),
    "ladybug": ("ladybug close up macro leaf", "bọ rùa"),
    "beetle": ("beetle close up macro", "bọ cánh cứng"),
    "ant": ("ant close up macro", "kiến"),
    "spider": ("spider web close up macro", "nhện"),
    "tarantula": ("tarantula spider close up", "nhện tarantula"),
    "scorpion": ("scorpion close up desert", "bọ cạp"),
    "grasshopper": ("grasshopper close up macro green", "châu chấu"),
    "cricket": ("cricket insect close up macro", "dế"),
    "firefly": ("firefly glowing night close up", "đom đóm"),
    "moth": ("moth close up macro", "bướm đêm"),
    "caterpillar": ("caterpillar close up macro leaf", "sâu bướm"),
    "praying mantis": ("praying mantis close up macro", "bọ ngựa"),


    # ===== MÈO HOANG (giữ loài phổ biến) =====
    "lynx": ("lynx wild cat forest close up", "linh miêu"),
    "snow leopard": ("snow leopard mountain close up", "báo tuyết"),
    "cougar": ("cougar mountain lion close up", "báo sư tử"),

    # ĐỘNG VẬT HOANG DÃ
    "capybara": ("capybara close up", "chuột lang nước"),

    # CÁ - chỉ giữ loài phổ biến, dễ tìm đúng
    "salmon": ("salmon fish jumping river", "cá hồi"),
    "tuna": ("tuna fish swimming underwater ocean", "cá ngừ"),
    "eel": ("moray eel underwater reef", "cá chình"),
    "pufferfish": ("pufferfish underwater close up", "cá nóc"),
    "angelfish": ("angelfish tropical underwater aquarium", "cá thần tiên"),
    "betta fish": ("betta fish siamese fighting aquarium", "cá betta"),
    "koi": ("koi fish pond swimming colorful", "cá koi"),

    # CHIM (giữ loài phổ biến)
    "seagull": ("seagull bird beach flying", "chim hải âu"),
    "cockatoo": ("cockatoo parrot white bird", "vẹt mào"),

    # BÒ SÁT (giữ loài phổ biến)
    "monitor lizard": ("monitor lizard reptile close up", "kỳ đà"),
    "chameleon": ("chameleon reptile colorful close up", "tắc kè hoa"),

    #LƯỠNG CƯ (giữ loài phổ biến)
    "axolotl": ("axolotl pink aquarium", "kỳ giông mexico"),
    "tree frog": ("tree frog green close up", "ếch cây"),

    #CÔN TRÙNG (giữ loài phổ biến, bỏ loài khó tìm)
    "wasp": ("wasp insect close up macro", "ong bắp cày"),
    "cockroach": ("cockroach insect close up", "gián"),
    "centipede": ("centipede close up macro", "rết"),

    #ĐỘNG VẬT BIỂN - underwater (giữ loài phổ biến)
    "squid": ("squid swimming underwater ocean", "mực"),
    "sea urchin": ("sea urchin underwater close up", "nhím biển"),

    #Động vật Bắc Cực (giữ loài phổ biến)
    "arctic wolf": ("arctic wolf snow wild", "sói bắc cực"),
    "snowy owl": ("snowy owl bird white", "cú tuyết"),
    "beluga whale": ("beluga whale underwater white", "cá voi trắng"),

    #Động vật Nam Cực (giữ loài phổ biến)
    "emperor penguin": ("emperor penguin colony antarctica", "chim cánh cụt hoàng đế"),
    "leopard seal": ("leopard seal antarctica", "hải cẩu báo"),

    #Động vật Amazon (chỉ giữ loài phổ biến)
    "poison dart frog": ("poison dart frog colorful close up", "ếch phi tiêu"),
    "capuchin monkey": ("capuchin monkey jungle", "khỉ mũ"),
    "piranha": ("piranha fish underwater teeth", "cá ăn thịt"),

    #Động vật quý hiếm (chỉ giữ loài có ảnh tốt trên Pexels)
    "red panda": ("red panda tree bamboo", "gấu trúc đỏ"),
    "okapi": ("okapi close up wild", "hươu okapi"),
    "pangolin": ("pangolin close up scales wild", "tê tê"),

    # ===== ĐỘNG VẬT KHÁC =====
    "deer": ("deer wild forest close up", "nai"),
    "moose": ("moose wild close up", "nai sừng tấm"),
    "elk": ("elk wild close up", "nai sừng xám"),
    "reindeer": ("reindeer snow wild", "tuần lộc"),
    "camel": ("camel desert close up", "lạc đà"),
    "badger": ("badger animal nocturnal mammal", "lửng"),
    "honey badger": ("honey badger animal africa", "lửng mật"),
    "weasel": ("weasel wild close up", "chồn"),
    "ferret": ("ferret close up face", "chồn sương"),
    "mink": ("mink wild close up", "chồn vizon"),
    "otter": ("otter swimming river close up", "rái cá"),
    "sea otter": ("sea otter floating ocean close up", "rái cá biển"),
    "beaver": ("beaver river close up", "hải ly"),
    "hedgehog": ("hedgehog close up spines", "nhím"),
    "porcupine": ("porcupine close up spines", "nhím"),
    "pangolin": ("pangolin close up scales wild", "tê tê"),
    "sloth": ("sloth tree close up", "con lười"),
    "armadillo": ("armadillo close up wild", "tatu"),
    "raccoon": ("raccoon close up face wild", "gấu mèo"),
    "skunk": ("skunk close up wild", "chồn hôi"),
    "squirrel": ("squirrel tree close up", "sóc"),
    "chipmunk": ("chipmunk close up", "sóc chuột"),
    "bat": ("bat flying close up wild", "dơi"),
    "meerkat": ("meerkat standing close up wild", "cầy meerkat"),
    "mongoose": ("mongoose close up wild", "cầy mangut"),
    "hyena": ("hyena wild safari close up", "linh cẩu"),
    "jackal": ("jackal wild close up", "chó rừng"),
    "wild boar": ("wild boar forest close up", "lợn rừng"),
    "bison": ("bison wild close up", "bò rừng bison"),
    "yak": ("yak mountain close up", "bò tây tạng"),
    "musk ox": ("musk ox arctic close up", "bò xạ hương"),
    "tapir": ("tapir wild close up", "heo vòi"),
    "anteater": ("anteater wild close up", "thú ăn kiến"),
    "aardvark": ("aardvark wild close up", "lợn đất"),

    # ===== TIẾNG VIỆT (để tương thích ngược) =====
    "sư tử": ("lion wildlife africa", "sư tử"),
    "hổ": ("tiger wildlife", "hổ"),
    "voi": ("elephant wildlife africa", "voi"),
    "hươu cao cổ": ("giraffe wildlife africa", "hươu cao cổ"),
    "ngựa vằn": ("zebra wildlife africa", "ngựa vằn"),
    "gấu": ("bear wildlife forest", "gấu"),
    "gấu trúc": ("panda bear bamboo", "gấu trúc"),
    "sói": ("wolf wildlife forest", "sói"),
    "cáo": ("fox wildlife forest", "cáo"),
    "khỉ": ("monkey wildlife tree", "khỉ"),
    "cá heo": ("dolphin ocean swimming", "cá heo"),
    "cá voi": ("whale ocean underwater", "cá voi"),
    "cá mập": ("shark ocean underwater", "cá mập"),
    "rùa biển": ("sea turtle ocean underwater", "rùa biển"),
    "hải cẩu": ("seal ocean swimming", "hải cẩu"),
    "lợn biển": ("manatee sea cow underwater", "lợn biển"),
    "đại bàng": ("eagle bird flying majestic", "đại bàng"),
    "chim cánh cụt": ("penguin bird antarctic", "chim cánh cụt"),
    "vẹt": ("parrot bird colorful tropical", "vẹt"),
    "cú": ("owl bird wildlife night", "cú"),
    "mèo": ("cat cute pet domestic", "mèo"),
    "mèo nhà": ("cat cute pet domestic", "mèo"),
    "chó": ("dog pet cute domestic", "chó"),
    "thỏ": ("rabbit bunny cute pet", "thỏ"),
    "bò": ("cow farm animal grass", "bò"),
    "lợn": ("pig farm animal pink", "lợn"),
    "ngựa": ("horse farm animal running", "ngựa"),
    "cừu": ("sheep farm wool white", "cừu"),
    "nai": ("deer wildlife forest", "nai"),
    "hươu": ("deer wildlife forest", "hươu"),
    "lạc đà": ("camel desert sand", "lạc đà"),
    "lửng": ("badger wildlife", "lửng"),
    "rắn": ("snake reptile wildlife", "rắn"),
    "cá sấu": ("crocodile reptile water", "cá sấu"),
    "rùa": ("turtle wildlife", "rùa"),
    "bướm": ("butterfly insect colorful flower", "bướm"),
    "ong": ("bee insect flower honey", "ong"),
    "sóc": ("squirrel wildlife tree nut", "sóc"),
    "dơi": ("bat flying night wildlife", "dơi"),
}


def get_animal_info(animal_name: str) -> tuple[str, str]:
    """
    Lấy thông tin động vật: (search_term, display_name)
    
    Args:
        animal_name: Tên động vật (tiếng Anh hoặc tiếng Việt)
    
    Returns:
        (search_term_tiếng_Anh, tên_hiển_thị_tiếng_Việt)
    """
    name_lower = animal_name.lower().strip()
    
    # 1. Tìm CHÍNH XÁC trong database (ưu tiên cao nhất)
    if name_lower in ANIMAL_DATABASE:
        search_term, display_name = ANIMAL_DATABASE[name_lower]
        print(f"      [SEARCH] ✓ EXACT: '{animal_name}' -> search: '{search_term}', display: '{display_name}'")
        return search_term, display_name
    
    # 2. Tìm theo tên tiếng Việt (display_name)
    for key, (search_term, display_name) in ANIMAL_DATABASE.items():
        if display_name.lower() == name_lower:
            print(f"      [SEARCH] ✓ VN_NAME: '{animal_name}' -> search: '{search_term}', display: '{display_name}' (key: {key})")
            return search_term, display_name
    
    # 3. Tìm partial match - CHỈ khi key là một phần của tên HOẶC tên là một phần của key
    # KHÔNG match khi chỉ có 1 từ chung (như "fish")
    for key, (search_term, display_name) in ANIMAL_DATABASE.items():
        # Chỉ match nếu key hoàn toàn nằm trong tên (với word boundary)
        # hoặc tên hoàn toàn nằm trong key
        key_words = set(key.split())
        name_words = set(name_lower.split())
        
        # Match nếu tất cả các từ trong key đều có trong name
        if key_words and key_words.issubset(name_words):
            print(f"      [SEARCH] ~ PARTIAL (key in name): '{animal_name}' -> search: '{search_term}', display: '{display_name}' (key: {key})")
            return search_term, display_name
        
        # Match nếu tất cả các từ trong name đều có trong key
        if name_words and name_words.issubset(key_words):
            print(f"      [SEARCH] ~ PARTIAL (name in key): '{animal_name}' -> search: '{search_term}', display: '{display_name}' (key: {key})")
            return search_term, display_name
    
    # 4. Nếu tên đã là tiếng Anh (không có dấu), dùng trực tiếp để search
    import unicodedata
    normalized = unicodedata.normalize('NFD', animal_name)
    is_ascii = all(ord(c) < 128 for c in normalized if c.isalpha())
    
    if is_ascii:
        # Tên tiếng Anh - dùng trực tiếp
        search_term = f"{animal_name} wildlife animal"
        print(f"      [SEARCH] ? '{animal_name}' -> search: '{search_term}' (English, not in DB)")
        return search_term, animal_name
    
    # 5. Tên tiếng Việt không có trong DB - cảnh báo
    print(f"      [SEARCH] ⚠️ '{animal_name}' KHÔNG có trong database!")
    print(f"      [SEARCH] ⚠️ Hãy dùng tên tiếng Anh để search chính xác!")
    return "animal wildlife", animal_name


def _build_search_queries(query: str) -> list[str]:
    """
    Tạo danh sách query từ chính xác → tổng quát để thử lần lượt.

    Nguyên tắc:
    - Query gốc (có môi trường sống) đứng TRƯỚC để tránh ảnh đồ ăn/nấu nướng
    - Ví dụ "shrimp underwater alive" trước "shrimp" để không lấy ảnh tôm luộc
    """
    clean = query.strip()

    # Tách tên động vật chính (bỏ filler words)
    filler_words = {
        "wildlife", "animal", "nature", "africa", "ocean", "sea", "underwater",
        "forest", "jungle", "tropical", "arctic", "snow", "desert", "mountain",
        "cute", "pet", "domestic", "farm", "colorful", "beautiful", "majestic",
        "flying", "running", "swimming", "jumping", "hunting", "eating",
        "prehistoric", "rare", "giant", "small", "large", "big", "baby",
        "close", "up", "only", "real", "museum", "fossil", "skeleton",
        "documentary", "water", "river", "lake", "beach", "grass",
        "bird", "fish", "insect", "reptile", "mammal",
        "wild", "safari", "alive", "face", "macro", "render",
        "colony", "field", "flock", "pack", "school",
        "glowing", "ice", "ears", "spines", "scales",
        "3d", "realistic", "floor",
    }
    core_words = [w for w in clean.lower().split() if w not in filler_words]
    animal_name = " ".join(core_words[:2]) if core_words else clean.split()[0]

    queries = []

    # Query 1: query gốc đầy đủ (tên + môi trường) → chính xác nhất
    queries.append(clean)

    # Query 2: tên động vật + "wildlife" → tránh ảnh đồ ăn
    queries.append(f"{animal_name} wildlife")

    # Query 3: chỉ tên động vật (fallback)
    queries.append(animal_name)

    # Loại bỏ trùng lặp, giữ thứ tự
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)

    return unique


def _get_aspect_ratio_range(orientation: str) -> tuple[float, float, str]:
    """Trả về (min_ratio, max_ratio, label) theo orientation."""
    if orientation == "portrait":
        return 0.4, 0.75, "PORTRAIT"
    elif orientation == "square":
        return 0.9, 1.1, "SQUARE"
    else:  # landscape
        return 1.3, 2.5, "LANDSCAPE"


async def _pexels_video_search_single(query: str, per_page: int, orientation: str,
                                       min_ratio: float, max_ratio: float,
                                       ratio_label: str) -> list[dict]:
    """Thực hiện 1 lần search video Pexels với query cho trước."""
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": per_page, "orientation": orientation}

    print(f"        [API REQUEST] GET {url}")
    print(f"        [API REQUEST] params: {json.dumps(params)}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    print(f"        [API RESPONSE] HTTP {resp.status} ERROR")
                    return []

                data = await resp.json()
                total_results = data.get("total_results", 0)
                raw_videos = data.get("videos", [])
                print(f"        [API RESPONSE] HTTP 200 | total_results={total_results} | returned={len(raw_videos)} videos")

                videos = []
                for vi, v in enumerate(raw_videos):
                    v_id = v.get("id", "?")
                    v_url = v.get("url", "")
                    v_dur = v.get("duration", 0)
                    files_count = len(v.get("video_files", []))
                    print(f"        [RESULT {vi}] id={v_id} dur={v_dur}s files={files_count} page={v_url}")

                    best_file = None
                    best_res = 0
                    for vf in v.get("video_files", []):
                        vf_width = vf.get("width", 0)
                        vf_height = vf.get("height", 0)
                        if vf_height == 0:
                            continue

                        aspect_ratio = vf_width / vf_height
                        is_correct_orientation = min_ratio <= aspect_ratio <= max_ratio
                        is_good_quality = vf.get("quality") in ["hd", "sd"] and max(vf_width, vf_height) >= 720

                        if is_correct_orientation and is_good_quality:
                            res = vf_width * vf_height
                            if res > best_res:
                                best_res = res
                                best_file = vf

                    if best_file:
                        bw = best_file.get("width", 0)
                        bh = best_file.get("height", 0)
                        vid_url = best_file["link"]
                        print(f"          -> MATCHED: {bw}x{bh} quality={best_file.get('quality')} url={vid_url[:80]}...")
                        videos.append({
                            "id": v_id,
                            "url": vid_url,
                            "page_url": v_url,  # URL trang Pexels để validate
                            "width": bw,
                            "height": bh,
                            "duration": v_dur,
                        })
                    else:
                        print(f"          -> SKIP (no matching file)")

                print(f"        [SUMMARY] {len(videos)}/{len(raw_videos)} videos matched filters")
                return videos
    except Exception as e:
        print(f"        [API ERROR] {e}")
        return []


async def search_pexels_videos(query: str, per_page: int = 10, orientation: str = "landscape") -> list[dict]:
    """Tìm video từ Pexels API với nhiều lượt thử query từ chính xác → tổng quát.
    Có validation để lọc bỏ video không liên quan (người, động vật khác).

    Args:
        query: Từ khóa tìm kiếm
        per_page: Số kết quả mỗi trang
        orientation: "landscape" (ngang), "portrait" (dọc), hoặc "square" (vuông)
    """
    if not PEXELS_API_KEY:
        print("  [!] Cần PEXELS_API_KEY trong .env")
        return []

    min_ratio, max_ratio, ratio_label = _get_aspect_ratio_range(orientation)
    queries = _build_search_queries(query)
    
    # Lấy tên động vật chính để validate kết quả
    animal_core = _extract_animal_core_name(query)
    print(f"      [Pexels Video] Core name for validation: '{animal_core}'")

    for qi, q in enumerate(queries):
        print(f"      [Pexels Video] Try {qi+1}/{len(queries)}: '{q}'")
        videos = await _pexels_video_search_single(q, per_page, orientation,
                                                     min_ratio, max_ratio, ratio_label)
        if videos:
            # Validate: lọc bỏ video có người hoặc động vật khác
            validated = _validate_animal_videos(videos, animal_core)
            if validated:
                print(f"      [Pexels Video] ✓ Found {len(validated)} VALIDATED videos with query '{q}'")
                return validated
            else:
                print(f"      [Pexels Video] ⚠ Found {len(videos)} videos but NONE validated for '{animal_core}'")
                # Tiếp tục thử query khác
        else:
            print(f"      [Pexels Video] ✗ No results for '{q}'")

    print(f"      [Pexels Video] ⚠ No validated videos, returning empty (will fallback to image)")
    return []


def _extract_animal_core_name(query: str) -> str:
    """Trích xuất tên động vật chính từ query (1-2 từ đầu, bỏ filler)."""
    filler_words = {
        "wildlife", "animal", "nature", "africa", "ocean", "sea", "underwater",
        "forest", "jungle", "tropical", "arctic", "snow", "desert", "mountain",
        "cute", "pet", "domestic", "farm", "colorful", "beautiful", "majestic",
        "flying", "running", "swimming", "jumping", "hunting", "eating",
        "close", "up", "wild", "safari", "face", "macro",
    }
    words = query.lower().split()
    core = [w for w in words if w not in filler_words]
    return " ".join(core[:2]) if core else words[0] if words else ""


def _validate_animal_videos(videos: list[dict], animal_core: str) -> list[dict]:
    """
    Lọc video có liên quan đến tên động vật.
    - Bỏ video có người (people, person, woman, man, etc.)
    - Bỏ video có tên động vật khác trong URL
    
    Ví dụ: animal_core="lion" → skip video có URL chứa "tiger", "elephant", "person"
    """
    if not animal_core:
        return videos
    
    # Từ khóa liên quan đến người - SKIP những video này
    people_keywords = {
        "person", "people", "woman", "man", "girl", "boy", "child", "children",
        "kid", "kids", "human", "hand", "hands", "finger", "fingers",
        "farmer", "keeper", "trainer", "tourist", "couple", "family",
        "holding", "feeding", "petting", "riding",
    }
    
    # Danh sách các động vật phổ biến - nếu URL chứa tên khác thì skip
    common_animals = {
        "lion", "tiger", "elephant", "giraffe", "zebra", "rhino", "hippo",
        "bear", "panda", "wolf", "fox", "deer", "horse", "cow", "pig",
        "dog", "cat", "rabbit", "monkey", "gorilla", "chimpanzee",
        "dolphin", "whale", "shark", "fish", "turtle", "crocodile",
        "eagle", "owl", "parrot", "penguin", "flamingo", "duck", "chicken",
        "snake", "lizard", "frog", "butterfly", "bee", "spider",
        "kangaroo", "koala", "camel", "sheep", "goat",
    }
    
    animal_words = set(animal_core.lower().split())
    
    exact_matches = []
    neutral_matches = []
    
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
        
        # 2. Kiểm tra URL có chứa tên động vật KHÁC không → SKIP
        found_wrong_animal = False
        for other_animal in common_animals:
            if other_animal in url and other_animal not in animal_words:
                print(f"        [VALIDATE] SKIP id={v.get('id')} - URL contains '{other_animal}' (want '{animal_core}')")
                found_wrong_animal = True
                break
        
        if found_wrong_animal:
            continue
        
        # 3. Phân loại: EXACT MATCH vs NEUTRAL
        if any(aw in url for aw in animal_words):
            print(f"        [VALIDATE] ✓ EXACT MATCH id={v.get('id')} - URL contains '{animal_core}'")
            exact_matches.append(v)
        else:
            print(f"        [VALIDATE] ~ NEUTRAL id={v.get('id')} - URL neutral")
            neutral_matches.append(v)
    
    # Ưu tiên EXACT MATCH, chỉ dùng NEUTRAL nếu không có EXACT
    if exact_matches:
        print(f"        [VALIDATE] Returning {len(exact_matches)} EXACT matches (ignoring {len(neutral_matches)} neutral)")
        return exact_matches
    elif neutral_matches:
        # Chỉ trả về tối đa 2 video neutral để giảm rủi ro sai
        limited = neutral_matches[:2]
        print(f"        [VALIDATE] No exact matches, returning {len(limited)} NEUTRAL (risky)")
        return limited
    else:
        return []


async def _pexels_image_search_single(query: str, per_page: int, orientation: str,
                                       min_ratio: float, max_ratio: float,
                                       ratio_label: str) -> list[dict]:
    """Thực hiện 1 lần search ảnh Pexels với query cho trước."""
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": per_page, "orientation": orientation}

    print(f"        [API REQUEST] GET {url}")
    print(f"        [API REQUEST] params: {json.dumps(params)}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    print(f"        [API RESPONSE] HTTP {resp.status} ERROR")
                    return []

                data = await resp.json()
                total_results = data.get("total_results", 0)
                raw_photos = data.get("photos", [])
                print(f"        [API RESPONSE] HTTP 200 | total_results={total_results} | returned={len(raw_photos)} photos")

                images = []
                for pi, p in enumerate(raw_photos):
                    img_width = p.get("width", 0)
                    img_height = p.get("height", 0)
                    p_url = p.get("url", "")
                    alt = p.get("alt", "")

                    if img_height == 0:
                        continue

                    aspect_ratio = img_width / img_height
                    print(f"        [RESULT {pi}] id={p['id']} {img_width}x{img_height} ratio={aspect_ratio:.2f} alt=\"{alt[:60]}\"")

                    if min_ratio <= aspect_ratio <= max_ratio:
                        img_url = p["src"]["large2x"]
                        print(f"          -> MATCHED: {img_url[:80]}...")
                        images.append({
                            "id": p["id"],
                            "url": img_url,
                            "url_landscape": p["src"].get("landscape", img_url),
                            "url_portrait": p["src"].get("portrait", img_url),
                            "width": img_width,
                            "height": img_height,
                        })
                    else:
                        print(f"          -> SKIP (ratio {aspect_ratio:.2f} not in {min_ratio}-{max_ratio})")

                print(f"        [SUMMARY] {len(images)}/{len(raw_photos)} images matched filters")
                return images
    except Exception as e:
        print(f"        [API ERROR] {e}")
        return []


async def search_pexels_images(query: str, per_page: int = 10, orientation: str = "landscape") -> list[dict]:
    """Tìm ảnh từ Pexels API với nhiều lượt thử query từ chính xác → tổng quát.

    Args:
        query: Từ khóa tìm kiếm
        per_page: Số kết quả mỗi trang
        orientation: "landscape" (ngang), "portrait" (dọc), hoặc "square" (vuông)
    """
    if not PEXELS_API_KEY:
        print("  [!] Cần PEXELS_API_KEY trong .env")
        return []

    min_ratio, max_ratio, ratio_label = _get_aspect_ratio_range(orientation)
    queries = _build_search_queries(query)

    for qi, q in enumerate(queries):
        print(f"      [Pexels Image] Try {qi+1}/{len(queries)}: '{q}'")
        images = await _pexels_image_search_single(q, per_page, orientation,
                                                     min_ratio, max_ratio, ratio_label)
        if images:
            print(f"      [Pexels Image] ✓ Found {len(images)} images with query '{q}'")
            return images
        print(f"      [Pexels Image] ✗ No results for '{q}'")

    print(f"      [Pexels Image] ✗ No images found after {len(queries)} attempts")
    return []


async def download_file(url: str, output_path: str) -> str | None:
    """Tải file từ URL."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(output_path, "wb") as f:
                        f.write(await resp.read())
                    return output_path
        return None
    except Exception as e:
        print(f"  [!] Download error: {e}")
        return None


async def search_pixabay_videos(query: str, per_page: int = 5) -> list[dict]:
    """Tìm video từ Pixabay API (backup nếu không có Pexels key)."""
    pixabay_key = os.getenv("PIXABAY_API_KEY", "")
    if not pixabay_key:
        return []
    
    url = "https://pixabay.com/api/videos/"
    params = {
        "key": pixabay_key,
        "q": query,
        "per_page": per_page,
        "video_type": "film",
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    videos = []
                    for v in data.get("hits", []):
                        video_url = v.get("videos", {}).get("medium", {}).get("url")
                        if video_url:
                            videos.append({
                                "id": v["id"],
                                "url": video_url,
                                "duration": v.get("duration", 10),
                            })
                    return videos
        return []
    except Exception as e:
        print(f"  [!] Pixabay search error: {e}")
        return []


def get_video_duration(video_path: str) -> float:
    """Lấy duration của video bằng ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except:
        return 5.0


def resize_video_for_short(input_path: str, output_path: str, target_duration: float = None, 
                           target_width: int = 1920, target_height: int = 1080) -> str | None:
    """
    Resize video về kích thước chỉ định.
    
    Args:
        input_path: Đường dẫn video nguồn
        output_path: Đường dẫn video output
        target_duration: Thời lượng video (nếu cần cắt)
        target_width: Chiều rộng đích
        target_height: Chiều cao đích
    """
    try:
        target_w, target_h = target_width, target_height
        
        # Tính aspect ratio đích
        target_ratio = target_w / target_h
        if target_ratio > 1:
            orientation_label = "LANDSCAPE"
        elif target_ratio < 1:
            orientation_label = "PORTRAIT"
        else:
            orientation_label = "SQUARE"
        
        print(f"      [RESIZE] Target: {target_w}x{target_h} ({orientation_label})")
        
        # Kiểm tra video nguồn
        probe_cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            input_path,
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        src_w, src_h = 0, 0
        try:
            probe_data = json.loads(probe_result.stdout)
            for stream in probe_data.get("streams", []):
                if stream.get("codec_type") == "video":
                    src_w = stream.get("width", 0)
                    src_h = stream.get("height", 0)
                    print(f"      [INPUT] Source video: {src_w}x{src_h}")
                    break
        except:
            pass
        
        # Xử lý chuyển đổi orientation
        # Luôn scale + crop để đạt đúng kích thước đích
        if src_w > 0 and src_h > 0:
            src_ratio = src_w / src_h
            
            # Nếu nguồn và đích khác orientation hoàn toàn, cần crop mạnh
            if (src_ratio > 1 and target_ratio < 1) or (src_ratio < 1 and target_ratio > 1):
                print(f"      [CONVERT] Source {src_w}x{src_h} -> Target {target_w}x{target_h}")
        
        # Filter: scale để cover, sau đó crop chính giữa
        filter_complex = (
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},"
            f"setsar=1:1,"
            f"format=yuv420p"
        )
        
        # Tính aspect string cho metadata
        if target_w > target_h:
            aspect_str = "16:9"
        elif target_w < target_h:
            aspect_str = "9:16"
        else:
            aspect_str = "1:1"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", filter_complex,
            "-aspect", aspect_str,  # Dynamic aspect ratio
            "-r", str(Config.FPS),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
        ]
        
        if target_duration:
            cmd.extend(["-t", str(target_duration)])
        
        cmd.append(output_path)
        
        print(f"      [FFMPEG] Filter: {filter_complex}")
        print(f"      [FFMPEG] Aspect: {aspect_str}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"      [!] FFmpeg resize error: {result.stderr[:300]}")
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            # Verify output
            verify_cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", output_path]
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
            try:
                verify_data = json.loads(verify_result.stdout)
                for stream in verify_data.get("streams", []):
                    if stream.get("codec_type") == "video":
                        out_w = stream.get("width", 0)
                        out_h = stream.get("height", 0)
                        print(f"      [OUTPUT] Final video: {out_w}x{out_h}")
                        break
            except:
                pass
            
            size_kb = os.path.getsize(output_path) / 1024
            print(f"      Resized: {size_kb:.1f} KB")
            return output_path
        return None
    except Exception as e:
        print(f"  [!] Resize error: {e}")
        return None


def create_image_video(image_path: str, output_path: str, duration: float = 5.0,
                       target_width: int = 1920, target_height: int = 1080) -> str | None:
    """Tạo video từ ảnh tĩnh với kích thước chỉ định."""
    try:
        target_w, target_h = target_width, target_height
        
        # Tính aspect string
        if target_w > target_h:
            aspect_str = "16:9"
        elif target_w < target_h:
            aspect_str = "9:16"
        else:
            aspect_str = "1:1"
        
        # Scale ảnh để COVER toàn bộ, sau đó CROP chính giữa
        filter_complex = (
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},"
            f"setsar=1:1,"
            f"format=yuv420p"
        )
        
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", filter_complex,
            "-aspect", aspect_str,
            "-t", str(duration),
            "-r", str(Config.FPS),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ]
        
        print(f"      [IMAGE->VIDEO] Creating {target_w}x{target_h} video from image")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"      [!] FFmpeg image error: {result.stderr[:300]}")
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
        return None
    except Exception as e:
        print(f"  [!] Image to video error: {e}")
        return None


# Thư mục chứa file tiếng kêu động vật local
SOUNDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds")


def get_local_animal_sound(animal_name: str) -> str | None:
    """
    Tìm file tiếng kêu động vật trong thư mục sounds/
    
    Quy tắc đặt tên file:
    - Tên file = tên động vật tiếng Anh (viết thường, thay space bằng _)
    - Định dạng: .mp3, .wav, .ogg, .m4a
    - Ví dụ: lion.mp3, polar_bear.mp3, sea_turtle.wav
    
    Returns: Đường dẫn file nếu tìm thấy, None nếu không có
    """
    if not os.path.exists(SOUNDS_DIR):
        return None
    
    # Chuẩn hóa tên: lowercase, thay space bằng _
    name_lower = animal_name.lower().strip().replace(" ", "_")
    
    # Các định dạng audio hỗ trợ
    extensions = [".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"]
    
    # 1. Tìm chính xác
    for ext in extensions:
        file_path = os.path.join(SOUNDS_DIR, f"{name_lower}{ext}")
        if os.path.exists(file_path):
            print(f"      [LOCAL_SOUND] ✓ Found: {file_path}")
            return file_path
    
    # 2. Tìm file bắt đầu bằng tên động vật (ví dụ: lion_roar.mp3)
    try:
        for filename in os.listdir(SOUNDS_DIR):
            if filename.lower().startswith(name_lower):
                file_path = os.path.join(SOUNDS_DIR, filename)
                if os.path.isfile(file_path):
                    print(f"      [LOCAL_SOUND] ✓ Found (partial): {file_path}")
                    return file_path
    except:
        pass
    
    # 3. Tìm qua ANIMAL_DATABASE để lấy tên tiếng Anh
    for key, (search_term, vn_name) in ANIMAL_DATABASE.items():
        if vn_name.lower() == animal_name.lower():
            key_normalized = key.replace(" ", "_")
            for ext in extensions:
                file_path = os.path.join(SOUNDS_DIR, f"{key_normalized}{ext}")
                if os.path.exists(file_path):
                    print(f"      [LOCAL_SOUND] ✓ Found (via DB): {file_path}")
                    return file_path
    
    return None


async def fetch_animal_sound(search_term: str, output_path: str, max_duration: float = 3.0, animal_key: str = "") -> str | None:
    """
    Lấy tiếng kêu động vật TỪ FILE LOCAL.
    
    Chỉ dùng file trong thư mục sounds/ - KHÔNG tải từ internet.
    Nếu không có file → trả về None (video chỉ có đọc tên).
    
    Args:
        search_term: Từ khóa search (VD: "lion wildlife")
        output_path: Đường dẫn output
        max_duration: Thời lượng tối đa (giây)
        animal_key: Tên động vật gốc (VD: "giant sloth") - ưu tiên dùng để tìm file
    """
    # Ưu tiên dùng animal_key nếu có, nếu không thì lấy từ search_term
    if animal_key:
        base_animal = animal_key.strip()
    else:
        # Fallback: lấy từ search_term, nhưng cố gắng lấy nhiều từ hơn
        # "giant sloth prehistoric" -> lấy "giant sloth" (bỏ các từ như wildlife, prehistoric, etc.)
        skip_words = {"wildlife", "animal", "nature", "africa", "ocean", "forest", "jungle", 
                      "underwater", "swimming", "flying", "running", "cute", "pet", "farm",
                      "prehistoric", "colorful", "tropical", "arctic", "rare", "deep", "sea"}
        words = [w for w in search_term.lower().split() if w not in skip_words]
        base_animal = " ".join(words[:2]) if len(words) >= 2 else (words[0] if words else search_term.split()[0])
    
    # Log rõ tên file đang tìm
    expected_filename = base_animal.lower().replace(" ", "_")
    print(f"      [SOUND] Looking for animal: '{base_animal}'")
    print(f"      [SOUND] Expected filename: '{expected_filename}.mp3' (or .wav, .ogg, .m4a)")
    
    # Tìm file local
    local_sound = get_local_animal_sound(base_animal)
    if not local_sound:
        print(f"      [SOUND] ⏭ Không có file local cho '{base_animal}' - bỏ qua tiếng kêu")
        return None
    
    print(f"      [SOUND] ✓ Dùng file LOCAL: {local_sound}")
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Kiểm tra duration của file gốc
        original_duration = get_video_duration(local_sound)
        print(f"      [SOUND] File gốc: {original_duration:.1f}s, Max: {max_duration:.1f}s")
        
        # Nếu file dài hơn max_duration, cắt và thêm fade out
        if original_duration > max_duration:
            fade_duration = min(0.3, max_duration * 0.1)
            fade_start = max_duration - fade_duration
            audio_filter = f"volume=1.2,afade=t=out:st={fade_start}:d={fade_duration}"
            print(f"      [SOUND] Cắt từ {original_duration:.1f}s -> {max_duration:.1f}s")
        else:
            audio_filter = "volume=1.2"
        
        # Dùng ffmpeg để xử lý
        cmd = [
            "ffmpeg", "-y",
            "-i", local_sound,
            "-t", str(max_duration),
            "-af", audio_filter,
            "-ar", "44100",
            "-ac", "1",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
            final_duration = get_video_duration(output_path)
            print(f"      [SOUND] ✓ OK: {final_duration:.1f}s")
            return output_path
        
        return None
    except Exception as e:
        print(f"      [SOUND] ! Error: {e}")
        return None


async def generate_animal_narration(animal_name: str, output_path: str, search_term: str = "", work_dir: str = "", animal_key: str = "") -> tuple[str | None, float]:
    """
    Tạo audio: đọc tên động vật + tiếng kêu (nếu có file local).
    Trả về: (đường dẫn file, duration)
    
    Args:
        animal_name: Tên hiển thị tiếng Việt (để đọc TTS)
        output_path: Đường dẫn output
        search_term: Từ khóa search Pexels
        work_dir: Thư mục làm việc
        animal_key: Tên động vật gốc tiếng Anh (để tìm file âm thanh)
    """
    import edge_tts
    import hashlib

    text = f"Đây là ... {animal_name}."

    print(f"      [TTS] Animal: '{animal_name}', Text: '{text}'")

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if os.path.exists(output_path):
            os.remove(output_path)

        # Buoc 1: Tao narration (doc ten)
        narration_path = output_path + ".narr.mp3"
        communicate = edge_tts.Communicate(
            text=text,
            voice=Config.TTS_VOICE,
            rate="-20%",
        )
        await communicate.save(narration_path)

        if not os.path.exists(narration_path) or os.path.getsize(narration_path) < 100:
            print(f"      [TTS] Failed to create narration")
            return None, 0

        # Buoc 2: Tim tieng keu thuc tu local/Pexels
        sound_path = None
        narration_duration = get_video_duration(narration_path)
        
        # Tính thời gian còn lại cho tiếng kêu
        # Video clip thường ~5-8 giây, narration ~2-3 giây
        # Dành ~0.5s silence + còn lại cho tiếng kêu
        silence_duration = 0.5
        max_sound_duration = max(1.0, 5.0 - narration_duration - silence_duration)  # Tối thiểu 1 giây
        
        print(f"      [SOUND] Narration: {narration_duration:.1f}s, Max sound: {max_sound_duration:.1f}s")
        
        if search_term and work_dir:
            safe = "".join(c for c in animal_name if c.isalnum() or c in " _-").strip().replace(" ", "_")
            sound_path = os.path.join(work_dir, f"sound_{safe}.mp3")
            print(f"      [SOUND] Tim tieng keu cho: {search_term} (animal_key: '{animal_key}')")
            sound_path = await fetch_animal_sound(search_term, sound_path, max_duration=max_sound_duration, animal_key=animal_key)
            if sound_path:
                print(f"      [SOUND] Da tai tieng keu: {sound_path}")

        # Buoc 3: Ghep narration + silence + tieng keu
        if sound_path and os.path.exists(sound_path):
            # Ghep: [narration] + [0.5s im lang] + [tieng keu]
            silence_path = output_path + ".silence.wav"
            cmd_silence = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-t", "0.5", "-i", "anullsrc=r=44100:cl=mono",
                silence_path,
            ]
            subprocess.run(cmd_silence, capture_output=True, text=True)

            concat_list = output_path + ".list.txt"
            with open(concat_list, "w") as f:
                f.write(f"file '{os.path.abspath(narration_path)}'\n")
                f.write(f"file '{os.path.abspath(silence_path)}'\n")
                f.write(f"file '{os.path.abspath(sound_path)}'\n")

            cmd_concat = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_list,
                "-c:a", "libmp3lame", "-b:a", "128k",
                output_path,
            ]
            subprocess.run(cmd_concat, capture_output=True, text=True)

            # Cleanup
            for tmp in [narration_path, silence_path, concat_list, sound_path]:
                if os.path.exists(tmp):
                    os.remove(tmp)

            print(f"      [TTS] Doc ten + tieng keu that!")
        else:
            # Khong co tieng keu -> chi doc ten
            os.rename(narration_path, output_path)
            print(f"      [TTS] Chi doc ten (khong tim duoc tieng keu)")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            duration = get_video_duration(output_path)
            size_kb = os.path.getsize(output_path) / 1024
            print(f"      [TTS] OK: {size_kb:.1f}KB, {duration:.1f}s")
            return output_path, duration
        else:
            print(f"      [TTS] Failed")
            return None, 0
    except Exception as e:
        print(f"  [!] TTS error: {e}")
        import traceback
        traceback.print_exc()
        return None, 0


def add_silence_to_audio(audio_path: str, output_path: str, silence_before: float = 0.5, silence_after: float = 1.0) -> str | None:
    """Thêm khoảng im lặng trước và sau audio."""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-t", str(silence_before), "-i", "anullsrc=r=44100:cl=mono",
            "-i", audio_path,
            "-f", "lavfi", "-t", str(silence_after), "-i", "anullsrc=r=44100:cl=mono",
            "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1[out]",
            "-map", "[out]",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            return output_path
        return None
    except Exception as e:
        print(f"  [!] Add silence error: {e}")
        return None


def get_audio_duration(audio_path: str) -> float:
    """Lấy duration của file audio."""
    return get_video_duration(audio_path)


def merge_audio_to_video(video_path: str, audio_path: str, output_path: str, animal_name: str = "") -> str | None:
    """Ghep narration (doc ten) vao video. Neu video goc co tieng keu that thi mix them."""
    import hashlib

    try:
        video_duration = get_video_duration(video_path)
        audio_duration = get_video_duration(audio_path)

        with open(audio_path, 'rb') as f:
            audio_hash = hashlib.md5(f.read()).hexdigest()[:8]

        print(f"      [MERGE] Animal: {animal_name}")
        print(f"      [MERGE] Video dur: {video_duration:.1f}s, Audio dur: {audio_duration:.1f}s, hash: {audio_hash}")

        # Kiem tra video goc co tieng keu dong vat khong
        mix_animal_sound = False
        probe_cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-select_streams", "a", video_path,
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        try:
            probe_data = json.loads(probe_result.stdout)
            if len(probe_data.get("streams", [])) > 0:
                vol_cmd = ["ffmpeg", "-i", video_path, "-af", "volumedetect", "-f", "null", "-"]
                vol_result = subprocess.run(vol_cmd, capture_output=True, text=True)
                for line in vol_result.stderr.split("\n"):
                    if "mean_volume" in line:
                        try:
                            mean_vol = float(line.split("mean_volume:")[1].split("dB")[0].strip())
                            mix_animal_sound = mean_vol > -35.0
                            print(f"      [MERGE] Audio goc: {mean_vol:.1f}dB -> {'MIX tieng keu' if mix_animal_sound else 'bo qua'}")
                        except:
                            pass
        except:
            pass

        if mix_animal_sound:
            # Nang cao: MIX narration + tieng keu goc
            print(f"      [MERGE] MIX: narration + tieng keu dong vat")
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path, "-i", audio_path,
                "-filter_complex",
                "[0:a]volume=0.3[original];[1:a]volume=1.5[narration];"
                "[narration][original]amix=inputs=2:duration=longest:dropout_transition=1,volume=2.0[aout]",
                "-map", "0:v:0", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-video_track_timescale", "24000",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                "-t", str(video_duration),
                "-avoid_negative_ts", "make_zero",
                "-fflags", "+genpts",
                "-movflags", "+faststart",
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"      [MERGE] Mix loi, fallback narration only")
                mix_animal_sound = False

        if not mix_animal_sound:
            # Mac dinh: chi doc ten
            # Dùng apad để pad silence, giữ nguyên volume narration
            print(f"      [MERGE] Narration only (doc ten)")
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path, "-i", audio_path,
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
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, text=True)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            size_kb = os.path.getsize(output_path) / 1024
            final_duration = get_video_duration(output_path)
            print(f"      [MERGE] OK: {size_kb:.1f}KB, {final_duration:.1f}s")
            return output_path
        return None
    except Exception as e:
        print(f"  [!] Merge audio error: {e}")
        import traceback
        traceback.print_exc()
        return None


def concatenate_videos(video_paths: list[str], output_path: str, 
                       target_width: int = 1920, target_height: int = 1080) -> str | None:
    """Ghép nhiều video thành 1 video dài. GIỮ NGUYÊN THỨ TỰ."""
    if not video_paths:
        return None
    
    # Lọc chỉ lấy file tồn tại - GIỮ NGUYÊN THỨ TỰ
    valid_paths = []
    for vp in video_paths:
        if os.path.exists(vp) and os.path.getsize(vp) > 1000:
            valid_paths.append(vp)
        else:
            print(f"    [!] Skip invalid: {vp}")
    
    if not valid_paths:
        print(f"  [!] No valid video files to concatenate")
        return None
    
    print(f"    ====== CONCATENATE ORDER ======")
    print(f"    Concatenating {len(valid_paths)} clips IN ORDER:")
    for idx, vp in enumerate(valid_paths):
        size_kb = os.path.getsize(vp) / 1024
        print(f"      {idx+1}. {vp}")
        print(f"         Size: {size_kb:.1f} KB")
    print(f"    ================================")
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Tạo file list - GIỮ NGUYÊN THỨ TỰ
        list_path = output_path + ".txt"
        with open(list_path, "w") as f:
            for vp in valid_paths:
                abs_path = os.path.abspath(vp)
                f.write(f"file '{abs_path}'\n")
        
        # In nội dung file list để debug
        print(f"    File list content:")
        with open(list_path, "r") as f:
            print(f.read())
        
        # Tính aspect string
        if target_width > target_height:
            aspect_str = "16:9"
        elif target_width < target_height:
            aspect_str = "9:16"
        else:
            aspect_str = "1:1"
        
        # Concat bằng TS intermediate: chuẩn hóa tất cả clip về cùng format
        # rồi nối bằng concat protocol (không có encoder delay tích lũy)
        ts_files = []
        print(f"    Step 1: Convert {len(valid_paths)} clips to TS...")

        for idx, vp in enumerate(valid_paths):
            print(f"      TS [{idx}] {vp}")
            ts_path = output_path + f".part{idx:03d}.ts"
            ts_cmd = [
                "ffmpeg", "-y", "-i", vp,
                "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height},setsar=1:1,format=yuv420p",
                "-r", str(Config.FPS),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                "-bsf:v", "h264_mp4toannexb",
                "-f", "mpegts",
                ts_path,
            ]
            subprocess.run(ts_cmd, capture_output=True, text=True)
            if os.path.exists(ts_path) and os.path.getsize(ts_path) > 1000:
                ts_files.append(ts_path)

        if not ts_files:
            print(f"    [!] No TS files created")
            if os.path.exists(list_path):
                os.remove(list_path)
            return None

        # Concat bằng concat protocol: file:part000.ts|file:part001.ts|...
        concat_input = "concat:" + "|".join(os.path.abspath(t) for t in ts_files)

        cmd = [
            "ffmpeg", "-y",
            "-i", concat_input,
            "-af", "dynaudnorm=f=250:g=15:p=0.95:m=10",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-aspect", aspect_str,
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-movflags", "+faststart",
            output_path,
        ]

        print(f"    Step 2: Concat {len(ts_files)} TS -> MP4 ({target_width}x{target_height})...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Cleanup temp files
        if os.path.exists(list_path):
            os.remove(list_path)
        for ts in ts_files:
            if os.path.exists(ts):
                os.remove(ts)
        
        if result.returncode != 0:
            print(f"    [!] FFmpeg error: {result.stderr[:500]}")
            return None
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            print(f"    Output: {output_path} ({size_mb:.1f} MB)")
            return output_path
        
        print(f"    [!] Output file not created or too small")
        return None
    except Exception as e:
        print(f"  [!] Concatenate error: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_intro_clip(
    work_dir: str,
    image_path: str = "images/gioi_thieu.jpeg",
    bg_music_path: str = "sounds/nhac_nen_mo_dau_dong_vat.mp3",
    voice_path: str = "sounds/voice_first.mp3",
    duration: float = 7.0,
    target_width: int = 1920,
    target_height: int = 1080,
) -> str | None:
    """
    Tạo clip mở đầu (intro) với:
    - Hình ảnh slide có hiệu ứng zoom-in chậm
    - Nhạc nền (cắt theo duration)
    - Voice overlay

    Returns: đường dẫn file video intro hoặc None
    """
    try:
        # Resolve đường dẫn tuyệt đối
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        image_abs = os.path.join(base_dir, image_path) if not os.path.isabs(image_path) else image_path
        bg_music_abs = os.path.join(base_dir, bg_music_path) if not os.path.isabs(bg_music_path) else bg_music_path
        voice_abs = os.path.join(base_dir, voice_path) if not os.path.isabs(voice_path) else voice_path

        for label, p in [("Image", image_abs), ("BG Music", bg_music_abs), ("Voice", voice_abs)]:
            if not os.path.exists(p):
                print(f"      [INTRO] ✗ {label} not found: {p}")
                return None

        os.makedirs(work_dir, exist_ok=True)
        intro_output = os.path.join(work_dir, "intro_clip.mp4")

        target_w, target_h = target_width, target_height

        # Tính aspect string
        if target_w > target_h:
            aspect_str = "16:9"
        elif target_w < target_h:
            aspect_str = "9:16"
        else:
            aspect_str = "1:1"

        # Hiệu ứng zoom-in chậm (ken burns) trên ảnh
        # Scale ảnh lớn hơn 20% rồi zoom từ 100% -> 120% trong suốt duration
        zoom_filter = (
            f"scale={int(target_w * 1.3)}:{int(target_h * 1.3)}:force_original_aspect_ratio=increase,"
            f"crop={int(target_w * 1.3)}:{int(target_h * 1.3)},"
            f"zoompan=z='min(zoom+0.0015,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={int(duration * Config.FPS)}:s={target_w}x{target_h}:fps={Config.FPS},"
            f"format=yuv420p"
        )

        # Mix audio: nhạc nền (volume thấp) + voice (volume cao)
        # Voice bắt đầu sau 0.5s, nhạc nền fade in/out
        fade_out_start = duration - 1.0
        audio_filter = (
            f"[1:a]atrim=0:{duration},volume=0.25,afade=t=in:st=0:d=1.0,afade=t=out:st={fade_out_start}:d=1.0[bg];"
            f"[2:a]volume=1.0,adelay=500|500[voice];"
            f"[bg][voice]amix=inputs=2:duration=first:dropout_transition=1[aout]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_abs,       # input 0: image
            "-i", bg_music_abs,                    # input 1: background music
            "-i", voice_abs,                       # input 2: voice
            "-filter_complex",
            f"{zoom_filter}[v];{audio_filter}",
            "-map", "[v]", "-map", "[aout]",
            "-t", str(duration),
            "-aspect", aspect_str,
            "-r", str(Config.FPS),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-movflags", "+faststart",
            intro_output,
        ]

        print(f"      [INTRO] Creating intro clip: {duration}s, {target_w}x{target_h}")
        print(f"      [INTRO] Image: {image_abs}")
        print(f"      [INTRO] BG Music: {bg_music_abs}")
        print(f"      [INTRO] Voice: {voice_abs}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"      [INTRO] ✗ FFmpeg error: {result.stderr[:500]}")
            return None

        if os.path.exists(intro_output) and os.path.getsize(intro_output) > 1000:
            size_kb = os.path.getsize(intro_output) / 1024
            final_dur = get_video_duration(intro_output)
            print(f"      [INTRO] ✓ Created: {size_kb:.1f} KB, {final_dur:.1f}s")
            return intro_output

        print(f"      [INTRO] ✗ Output file not created or too small")
        return None
    except Exception as e:
        print(f"      [INTRO] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def create_animal_clip(
    animal_name: str,
    work_dir: str,
    clip_index: int,
    use_video: bool = True,
    clip_duration: float = 8.0,
    orientation: str = "landscape",
    target_width: int = 1920,
    target_height: int = 1080,
) -> str | None:
    """
    Tạo 1 clip về 1 con vật:
    1. Tạo audio đọc tên TRƯỚC (để biết duration)
    2. Tìm video/ảnh thực từ Pexels
    3. Tạo video với duration >= audio
    4. Ghép lại
    
    Args:
        orientation: "landscape", "portrait", hoặc "square"
        target_width: Chiều rộng đích
        target_height: Chiều cao đích
    """
    # Lấy thông tin động vật: search term (tiếng Anh) và display name (tiếng Việt)
    search_term, display_name = get_animal_info(animal_name)
    
    # Tạo tên thư mục an toàn
    safe_name = "".join(c for c in animal_name if c.isalnum() or c in " _-").strip().replace(" ", "_")
    
    print(f"    [{clip_index}] Creating clip for: {animal_name}")
    print(f"      -> Search: '{search_term}'")
    print(f"      -> Display: '{display_name}'")
    print(f"      -> Orientation: {orientation} ({target_width}x{target_height})")
    
    # Thư mục riêng cho mỗi con vật - dùng cả index và tên để tránh nhầm
    clip_dir = os.path.join(work_dir, f"clip_{clip_index:03d}_{safe_name}")
    os.makedirs(clip_dir, exist_ok=True)
    
    print(f"      Working dir: {clip_dir}")
    
    # ========== BƯỚC 1: Tạo audio TRƯỚC (đọc tên tiếng Việt) ==========
    print(f"      [AUDIO] Generating narration for: {display_name}")
    audio_path = os.path.join(clip_dir, f"narration_{safe_name}.mp3")
    audio_result, audio_duration = await generate_animal_narration(
        display_name, audio_path, search_term=search_term, work_dir=clip_dir, animal_key=animal_name
    )
    
    if audio_result:
        print(f"      [AUDIO] Created: {audio_path}")
    
    # Thêm im lặng trước và sau audio để người xem có thời gian xem hình ảnh/video
    if audio_result:
        audio_with_silence = os.path.join(clip_dir, f"narration_{safe_name}_padded.mp3")
        padded = add_silence_to_audio(audio_path, audio_with_silence, silence_before=0.5, silence_after=4.0)
        if padded:
            audio_path = audio_with_silence
            audio_duration = get_video_duration(audio_path)
            print(f"      [AUDIO] With silence: {audio_duration:.1f}s")
    
    # Video duration = audio duration (đã có padding trong audio)
    if audio_result:
        target_video_duration = audio_duration
    else:
        target_video_duration = clip_duration
    
    print(f"      Target video duration: {target_video_duration:.1f}s")
    
    # ========== BƯỚC 2: Tìm và tạo video ==========
    media_path = None
    video_clip_path = os.path.join(clip_dir, f"video_{safe_name}.mp4")
    
    if use_video:
        # Thử tìm video trước với đúng orientation
        print(f"      [VIDEO] Searching {orientation} videos for: {search_term}")
        videos = await search_pexels_videos(search_term, per_page=10, orientation=orientation)
        
        if not videos:
            # Thử Pixabay
            videos = await search_pixabay_videos(search_term, per_page=3)
        
        if videos:
            # Chọn random 1 video
            video = random.choice(videos)
            raw_video = os.path.join(clip_dir, f"raw_{safe_name}.mp4")
            
            print(f"      [VIDEO] Downloading video...")
            downloaded = await download_file(video["url"], raw_video)
            
            if downloaded:
                print(f"      [VIDEO] Resizing video to {target_width}x{target_height}...")
                media_path = resize_video_for_short(raw_video, video_clip_path, target_video_duration,
                                                    target_width, target_height)
                if media_path:
                    print(f"      [VIDEO] Created: {media_path}")
    
    if not media_path:
        # Fallback: dùng ảnh
        print(f"      [IMAGE] Searching {orientation} images for: {search_term}")
        images = await search_pexels_images(search_term, per_page=10, orientation=orientation)
        
        if images:
            image = random.choice(images)
            raw_image = os.path.join(clip_dir, f"raw_{safe_name}.jpg")
            
            # Chọn URL phù hợp với orientation
            if orientation == "portrait":
                image_url = image.get("url_portrait", image["url"])
            else:
                image_url = image.get("url_landscape", image["url"])
            
            print(f"      [IMAGE] Downloading image...")
            downloaded = await download_file(image_url, raw_image)
            
            if downloaded:
                print(f"      [IMAGE] Creating {target_width}x{target_height} video from image...")
                media_path = create_image_video(raw_image, video_clip_path, target_video_duration,
                                                target_width, target_height)
                if media_path:
                    print(f"      [IMAGE] Created: {media_path}")
    
    if not media_path:
        print(f"      [!] Could not find media for {animal_name}")
        return None
    
    # ========== BƯỚC 3: Ghép audio vào video ==========
    if not audio_result:
        print(f"      [!] No audio, returning video only")
        return media_path
    
    # Final clip với tên rõ ràng
    final_clip = os.path.join(clip_dir, f"final_{safe_name}.mp4")
    
    print(f"      ======= MERGE FOR: {animal_name} =======")
    print(f"        Video file: {media_path}")
    print(f"        Audio file: {audio_path}")
    print(f"        Output file: {final_clip}")
    
    # Kiểm tra file tồn tại trước khi merge
    if not os.path.exists(media_path):
        print(f"      [!] Video file not found: {media_path}")
        return None
    if not os.path.exists(audio_path):
        print(f"      [!] Audio file not found: {audio_path}")
        return None
    
    result = merge_audio_to_video(media_path, audio_path, final_clip, animal_name)
    
    if result:
        print(f"      [DONE] Clip created for {animal_name}: {result}")
    else:
        print(f"      [!] Merge failed, returning video without audio")
    
    if result:
        print(f"      [DONE] Clip created: {result}")
    else:
        print(f"      [!] Merge failed, returning video without audio")
        result = media_path
    
    return result


def generate_animal_scripts(user_prompt: str, num_videos: int = 1, animals_per_video: int = 10) -> list[dict]:
    """
    Tạo danh sách động vật từ ANIMAL_DATABASE.
    Random theo chủ đề hoặc random từ toàn bộ database.
    
    Args:
        user_prompt: Chủ đề (có thể để trống)
        num_videos: Số video cần tạo
        animals_per_video: Số động vật mỗi video
    """
    import random
    
    prompt_lower = user_prompt.lower()
    
    # Lấy TẤT CẢ động vật từ ANIMAL_DATABASE (chỉ lấy key tiếng Anh, bỏ key tiếng Việt)
    all_animals_from_db = []
    for key in ANIMAL_DATABASE.keys():
        # Bỏ qua key tiếng Việt (có dấu hoặc là bản dịch)
        # Kiểm tra nếu key có ký tự tiếng Việt
        is_vietnamese = any(ord(c) > 127 for c in key)
        if not is_vietnamese:
            all_animals_from_db.append(key)
    
    print(f"  [ANIMAL] Total animals in DATABASE: {len(all_animals_from_db)}")
    
    # Tìm chủ đề phù hợp từ prompt
    matched_categories = []
    
    keyword_mapping = {
        "african": ["châu phi", "africa", "safari", "hoang dã"],
        "ocean": ["biển", "ocean", "sea", "đại dương", "marine", "underwater"],
        "birds": ["chim", "bird", "bay", "flying"],
        "pets": ["thú cưng", "pet", "nuôi", "nhà"],
        "farm": ["trang trại", "farm", "nông trại"],
        "forest": ["rừng", "forest", "woodland"],
        "jungle": ["rừng nhiệt đới", "jungle", "tropical", "amazon"],
        "arctic": ["bắc cực", "arctic", "polar", "tuyết", "snow", "antarctic", "nam cực"],
        "australia": ["úc", "australia", "kangaroo", "koala"],
        "reptiles": ["bò sát", "reptile", "rắn", "snake", "lizard"],
        "primates": ["linh trưởng", "khỉ", "monkey", "ape", "gorilla"],
        "insects": ["côn trùng", "insect", "bọ", "bug"],
        "predators": ["săn mồi", "predator", "hunter", "ăn thịt"],
        "cute": ["dễ thương", "cute", "đáng yêu", "adorable"],
        "fish": ["cá", "fish", "aquarium"],
    }
    
    for cat_key, keywords in keyword_mapping.items():
        if any(kw in prompt_lower for kw in keywords):
            matched_categories.append(cat_key)
    
    # Lọc động vật theo chủ đề (nếu có)
    filtered_animals = []
    
    if matched_categories and "all" not in prompt_lower and "tất cả" not in prompt_lower:
        print(f"  [ANIMAL] Matched categories: {matched_categories}")
        
        # Mapping từ category -> keywords để lọc từ ANIMAL_DATABASE
        category_keywords = {
            "african": ["africa", "safari", "lion", "elephant", "giraffe", "zebra", "rhino", "hippo", "leopard", "cheetah", "hyena", "buffalo", "antelope", "wildebeest", "gazelle", "warthog"],
            "ocean": ["ocean", "sea", "underwater", "marine", "dolphin", "whale", "shark", "turtle", "seal", "octopus", "jellyfish", "coral", "fish", "crab", "lobster", "shrimp", "squid", "orca", "manatee", "seahorse", "starfish", "clownfish", "manta", "stingray", "beluga"],
            "birds": ["bird", "eagle", "owl", "hawk", "falcon", "parrot", "swan", "pelican", "crane", "heron", "stork", "vulture", "crow", "raven", "sparrow", "pigeon", "dove", "robin", "kingfisher", "woodpecker", "chicken", "rooster", "duck", "goose", "turkey", "flamingo", "peacock", "toucan", "hummingbird", "penguin", "emu", "seagull", "cockatoo", "macaw"],
            "pets": ["pet", "cat", "dog", "kitten", "puppy", "rabbit", "bunny", "hamster", "guinea pig", "goldfish", "parrot", "ferret"],
            "farm": ["farm", "cow", "bull", "pig", "horse", "pony", "donkey", "sheep", "lamb", "goat", "llama", "alpaca", "chicken", "duck", "goose", "turkey"],
            "forest": ["forest", "bear", "wolf", "fox", "deer", "moose", "elk", "squirrel", "raccoon", "badger", "hedgehog", "owl", "rabbit"],
            "jungle": ["jungle", "tropical", "tiger", "jaguar", "monkey", "gorilla", "orangutan", "chimpanzee", "gibbon", "toucan", "parrot", "snake", "chameleon", "sloth", "anaconda", "piranha", "capuchin"],
            "arctic": ["arctic", "polar", "snow", "antarctic", "polar bear", "penguin", "seal", "arctic fox", "reindeer", "beluga", "snowy owl", "arctic wolf"],
            "australia": ["australia", "kangaroo", "koala", "platypus", "wombat", "emu", "kiwi"],
            "reptiles": ["reptile", "snake", "cobra", "python", "anaconda", "viper", "crocodile", "alligator", "lizard", "chameleon", "iguana", "komodo", "gecko", "tortoise", "turtle", "monitor"],
            "primates": ["monkey", "ape", "gorilla", "chimpanzee", "orangutan", "gibbon", "baboon", "lemur", "macaque", "capuchin"],
            "insects": ["insect", "butterfly", "bee", "dragonfly", "ladybug", "beetle", "ant", "spider", "tarantula", "scorpion", "grasshopper", "cricket", "firefly", "moth", "caterpillar", "praying mantis", "wasp", "cockroach", "centipede"],
            "predators": ["predator", "lion", "tiger", "wolf", "eagle", "shark", "crocodile", "cheetah", "leopard", "hawk", "orca", "jaguar", "bear", "hyena"],
            "cute": ["cute", "panda", "koala", "otter", "hedgehog", "rabbit", "kitten", "puppy", "sloth", "penguin", "red panda", "bunny", "hamster"],
            "fish": ["fish", "salmon", "tuna", "eel", "pufferfish", "angelfish", "betta", "koi", "goldfish", "clownfish", "piranha"],
        }
        
        # Lọc động vật phù hợp với chủ đề
        for animal in all_animals_from_db:
            animal_lower = animal.lower()
            search_term = ANIMAL_DATABASE[animal][0].lower()
            
            for cat in matched_categories:
                if cat in category_keywords:
                    for keyword in category_keywords[cat]:
                        if keyword in animal_lower or keyword in search_term:
                            if animal not in filtered_animals:
                                filtered_animals.append(animal)
                            break
        
        print(f"  [ANIMAL] Filtered by theme: {len(filtered_animals)} animals")
    
    # Nếu không đủ hoặc không có filter, dùng tất cả
    if len(filtered_animals) < animals_per_video:
        print(f"  [ANIMAL] Using ALL animals from database")
        filtered_animals = all_animals_from_db.copy()
    
    # Shuffle để random
    random.shuffle(filtered_animals)
    
    print(f"  [ANIMAL] Total available: {len(filtered_animals)} unique animals")
    print(f"  [ANIMAL] Target: {num_videos} video(s), {animals_per_video} animals each")
    
    videos = []
    used_animals = set()
    
    for i in range(num_videos):
        # Lấy động vật chưa dùng
        available = [a for a in filtered_animals if a not in used_animals]
        
        # Nếu hết động vật, reset
        if len(available) < animals_per_video:
            print(f"  [ANIMAL] Resetting used animals pool")
            used_animals.clear()
            available = filtered_animals.copy()
            random.shuffle(available)
        
        # Số động vật cho video này
        num_animals = min(animals_per_video, len(available))
        
        if num_animals == 0:
            print(f"  [ANIMAL] Warning: No more animals available for video {i+1}")
            break
        
        selected = available[:num_animals]
        
        # Đánh dấu đã dùng
        used_animals.update(selected)
        
        # Xác định title dựa trên số lượng
        if num_animals >= 30:
            title = f"Khám phá {num_animals} loài động vật"
        elif num_animals >= 10:
            title = f"Thế giới động vật - {num_animals} loài"
        else:
            title = "Động vật hoang dã"
        
        videos.append({
            "title": title,
            "theme": "mixed",
            "animals": selected
        })
        
        print(f"  [ANIMAL] Video {i+1}: {title} -> {num_animals} animals")
        print(f"           First 5: {selected[:5]}")
        if len(selected) > 5:
            print(f"           Last 5: {selected[-5:]}")
    
    return videos
