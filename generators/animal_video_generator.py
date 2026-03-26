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
    "lion": ("lion wildlife africa", "sư tử"),
    "tiger": ("tiger wildlife", "hổ"),
    "elephant": ("elephant wildlife africa", "voi"),
    "giraffe": ("giraffe wildlife africa", "hươu cao cổ"),
    "zebra": ("zebra wildlife africa", "ngựa vằn"),
    "rhinoceros": ("rhinoceros wildlife", "tê giác"),
    "rhino": ("rhinoceros wildlife", "tê giác"),
    "hippopotamus": ("hippopotamus wildlife", "hà mã"),
    "hippo": ("hippopotamus wildlife", "hà mã"),
    "leopard": ("leopard wildlife", "báo"),
    "cheetah": ("cheetah running wildlife", "báo săn"),
    "jaguar": ("jaguar wildlife jungle", "báo đốm"),
    "antelope": ("antelope wildlife", "linh dương"),
    "buffalo": ("buffalo wildlife africa", "trâu rừng"),
    "wildebeest": ("wildebeest migration africa", "linh dương đầu bò"),
    
    # ===== GẤU =====
    "bear": ("bear wildlife forest", "gấu"),
    "panda": ("panda bear bamboo", "gấu trúc"),
    "polar bear": ("polar bear arctic snow", "gấu bắc cực"),
    "brown bear": ("brown bear wildlife", "gấu nâu"),
    "black bear": ("black bear wildlife", "gấu đen"),
    "grizzly": ("grizzly bear wildlife", "gấu xám"),
    
    # ===== CHÓ SÓI, CÁO =====
    "wolf": ("wolf wildlife forest", "sói"),
    "fox": ("fox wildlife forest", "cáo"),
    "red fox": ("red fox wildlife", "cáo đỏ"),
    "arctic fox": ("arctic fox snow white", "cáo bắc cực"),
    "fennec fox": ("fennec fox desert", "cáo fennec"),
    "coyote": ("coyote wildlife", "sói đồng cỏ"),
    
    # ===== KHỈ, VƯỢN =====
    "monkey": ("monkey wildlife tree", "khỉ"),
    "chimpanzee": ("chimpanzee ape wildlife", "tinh tinh"),
    "chimp": ("chimpanzee ape wildlife", "tinh tinh"),
    "orangutan": ("orangutan ape borneo", "đười ươi"),
    "gorilla": ("gorilla ape wildlife", "khỉ đột"),
    "gibbon": ("gibbon ape swinging", "vượn"),
    "baboon": ("baboon monkey africa", "khỉ đầu chó"),
    "lemur": ("lemur madagascar", "vượn cáo"),
    "macaque": ("macaque monkey", "khỉ mặt đỏ"),
    
    # ===== ĐỘNG VẬT BIỂN =====
    "dolphin": ("dolphin ocean swimming jumping", "cá heo"),
    "whale": ("whale ocean underwater", "cá voi"),
    "blue whale": ("blue whale ocean", "cá voi xanh"),
    "humpback whale": ("humpback whale jumping", "cá voi lưng gù"),
    "orca": ("orca killer whale ocean", "cá voi sát thủ"),
    "shark": ("shark ocean underwater swimming", "cá mập"),
    "great white shark": ("great white shark ocean", "cá mập trắng"),
    "hammerhead shark": ("hammerhead shark ocean", "cá mập đầu búa"),
    "sea turtle": ("sea turtle ocean underwater", "rùa biển"),
    "turtle": ("turtle wildlife", "rùa"),
    "seal": ("seal ocean swimming", "hải cẩu"),
    "sea lion": ("sea lion ocean beach", "sư tử biển"),
    "walrus": ("walrus arctic", "hải mã"),
    "manatee": ("manatee sea cow underwater", "lợn biển"),
    "dugong": ("dugong sea cow ocean", "bò biển"),
    "seahorse": ("seahorse underwater colorful", "cá ngựa"),
    "octopus": ("octopus underwater ocean", "bạch tuộc"),
    "jellyfish": ("jellyfish underwater glowing", "sứa"),
    "starfish": ("starfish ocean beach", "sao biển"),
    "clownfish": ("clownfish nemo anemone", "cá hề"),
    "manta ray": ("manta ray ocean underwater", "cá đuối"),
    "stingray": ("stingray underwater", "cá đuối gai"),
    "crab": ("crab ocean beach", "cua"),
    "lobster": ("lobster ocean", "tôm hùm"),
    "shrimp": ("shrimp underwater", "tôm"),
    "coral": ("coral reef underwater colorful", "san hô"),
    "penguin": ("penguin bird antarctic", "chim cánh cụt"),
    
    # ===== CHIM =====
    "eagle": ("eagle bird flying majestic", "đại bàng"),
    "bald eagle": ("bald eagle america", "đại bàng đầu trắng"),
    "hawk": ("hawk bird flying hunting", "chim ưng"),
    "falcon": ("falcon bird flying fast", "chim cắt"),
    "owl": ("owl bird wildlife night", "cú"),
    "flamingo": ("flamingo bird pink lake", "chim hồng hạc"),
    "peacock": ("peacock bird colorful feathers", "chim công"),
    "parrot": ("parrot bird colorful tropical", "vẹt"),
    "macaw": ("macaw parrot colorful", "vẹt đuôi dài"),
    "toucan": ("toucan bird colorful beak", "chim toucan"),
    "hummingbird": ("hummingbird bird tiny flower", "chim ruồi"),
    "swan": ("swan bird lake elegant", "thiên nga"),
    "pelican": ("pelican bird fishing", "bồ nông"),
    "crane": ("crane bird flying", "hạc"),
    "heron": ("heron bird water", "diệc"),
    "stork": ("stork bird flying", "cò"),
    "vulture": ("vulture bird", "kền kền"),
    "crow": ("crow bird black intelligent", "quạ"),
    "raven": ("raven bird black", "quạ đen"),
    "sparrow": ("sparrow bird small", "chim sẻ"),
    "pigeon": ("pigeon bird city", "bồ câu"),
    "dove": ("dove bird white peace", "chim bồ câu trắng"),
    "robin": ("robin bird red breast", "chim cổ đỏ"),
    "kingfisher": ("kingfisher bird colorful fishing", "chim bói cá"),
    "woodpecker": ("woodpecker bird tree", "chim gõ kiến"),
    "chicken": ("chicken farm bird", "gà"),
    "rooster": ("rooster chicken farm", "gà trống"),
    "duck": ("duck bird water", "vịt"),
    "goose": ("goose bird farm", "ngỗng"),
    "turkey": ("turkey bird farm", "gà tây"),
    
    # ===== ĐỘNG VẬT ÚC =====
    "kangaroo": ("kangaroo australia jumping", "chuột túi"),
    "koala": ("koala australia eucalyptus cute", "gấu túi"),
    "platypus": ("platypus australia swimming", "thú mỏ vịt"),
    "wombat": ("wombat australia", "gấu túi mũi trần"),
    "tasmanian devil": ("tasmanian devil", "quỷ tasmania"),
    "emu": ("emu bird australia", "đà điểu Úc"),
    "kiwi bird": ("kiwi bird new zealand", "chim kiwi"),
    
    # ===== BÒ SÁT =====
    "snake": ("snake reptile wildlife", "rắn"),
    "cobra": ("cobra snake hood", "rắn hổ mang"),
    "python": ("python snake large", "trăn"),
    "anaconda": ("anaconda snake water", "trăn anaconda"),
    "viper": ("viper snake venomous", "rắn lục"),
    "crocodile": ("crocodile reptile water", "cá sấu"),
    "alligator": ("alligator reptile swamp", "cá sấu mỹ"),
    "lizard": ("lizard reptile", "thằn lằn"),
    "chameleon": ("chameleon colorful changing", "tắc kè hoa"),
    "iguana": ("iguana lizard green", "kỳ nhông"),
    "komodo dragon": ("komodo dragon lizard large", "rồng komodo"),
    "gecko": ("gecko lizard wall", "tắc kè"),
    "tortoise": ("tortoise turtle land", "rùa cạn"),
    "frog": ("frog amphibian green", "ếch"),
    "toad": ("toad amphibian", "cóc"),
    "salamander": ("salamander amphibian", "kỳ giông"),
    
    # ===== ĐỘNG VẬT NHÀ =====
    "cat": ("cat cute pet domestic", "mèo"),
    "kitten": ("kitten cat cute baby", "mèo con"),
    "dog": ("dog pet cute domestic", "chó"),
    "puppy": ("puppy dog cute baby", "chó con"),
    "rabbit": ("rabbit bunny cute pet", "thỏ"),
    "bunny": ("bunny rabbit cute", "thỏ"),
    "hamster": ("hamster pet cute small", "chuột hamster"),
    "guinea pig": ("guinea pig pet cute", "chuột lang"),
    "goldfish": ("goldfish aquarium orange", "cá vàng"),
    "parrot pet": ("parrot pet bird talking", "vẹt"),
    
    # ===== ĐỘNG VẬT TRANG TRẠI =====
    "cow": ("cow farm animal grass", "bò"),
    "bull": ("bull farm animal", "bò đực"),
    "pig": ("pig farm animal pink", "lợn"),
    "horse": ("horse farm animal running", "ngựa"),
    "pony": ("pony horse small cute", "ngựa con"),
    "donkey": ("donkey farm animal", "lừa"),
    "sheep": ("sheep farm wool white", "cừu"),
    "lamb": ("lamb sheep baby cute", "cừu con"),
    "goat": ("goat farm animal", "dê"),
    "llama": ("llama farm fluffy", "lạc đà không bướu"),
    "alpaca": ("alpaca fluffy cute", "alpaca"),
    
    # ===== CÔN TRÙNG =====
    "butterfly": ("butterfly insect colorful flower", "bướm"),
    "bee": ("bee insect flower honey", "ong"),
    "dragonfly": ("dragonfly insect flying", "chuồn chuồn"),
    "ladybug": ("ladybug insect red spots", "bọ rùa"),
    "beetle": ("beetle insect", "bọ cánh cứng"),
    "ant": ("ant insect small", "kiến"),
    "spider": ("spider web", "nhện"),
    "tarantula": ("tarantula spider large", "nhện tarantula"),
    "scorpion": ("scorpion desert", "bọ cạp"),
    "grasshopper": ("grasshopper insect green", "châu chấu"),
    "cricket": ("cricket insect", "dế"),
    "firefly": ("firefly insect glowing night", "đom đóm"),
    "moth": ("moth insect night", "bướm đêm"),
    "caterpillar": ("caterpillar insect", "sâu bướm"),
    "praying mantis": ("praying mantis insect", "bọ ngựa"),


    # ===== MÈO HOANG =====
    "lynx": ("lynx wild cat forest", "linh miêu"),
    "ocelot": ("ocelot wild cat jungle", "mèo rừng"),
    "serval": ("serval wild cat africa", "mèo"),
    "cougar": ("cougar mountain lion", "báo sư tử"),
    "mountain lion": ("mountain lion wildlife", "sư tử núi"),
    "snow leopard": ("snow leopard mountain", "báo tuyết"),

    # ĐỘNG VẬT HOANG DÃ
    "warthog": ("warthog africa wild pig", "lợn bướu"),
    "gazelle": ("gazelle wildlife africa", "linh dương"),
    "ibex": ("ibex mountain goat", "dê núi"),
    "chamois": ("chamois mountain goat", "sơn dương"),
    "capybara": ("capybara largest rodent", "chuột lang nước"),
    "chinchilla": ("chinchilla fluffy rodent", "chuột chinchilla"),
    "marmot": ("marmot mountain rodent", "chuột marmot"),
    "groundhog": ("groundhog burrowing rodent", "chuột chũi đất"),
    "jerboa": ("jerboa desert rodent jumping", "chuột nhảy sa mạc"),
    "vole": ("vole small rodent", "chuột vole"),
    "lemming": ("lemming arctic rodent", "chuột lemming"),

    # CÁ
    "salmon": ("salmon fish river", "cá hồi"),
    "tuna": ("tuna fish ocean", "cá ngừ"),
    "eel": ("eel fish long", "cá chình"),
    "pufferfish": ("pufferfish ocean blowfish", "cá nóc"),
    "catfish": ("catfish river whiskers", "cá da trơn"),
    "tilapia": ("tilapia freshwater fish", "cá rô phi"),
    "anchovy": ("anchovy small fish", "cá cơm"),
    "sardine": ("sardine small fish", "cá mòi"),
    "cod": ("cod fish ocean", "cá tuyết"),
    "haddock": ("haddock fish ocean", "cá haddock"),
    "halibut": ("halibut flatfish ocean", "cá bơn"),
    "flounder": ("flounder flatfish", "cá bơn"),
    "barracuda": ("barracuda predator fish", "cá nhồng"),
    "marlin": ("marlin big game fish", "cá cờ"),
    "swordfish": ("swordfish ocean", "cá kiếm"),
    "angelfish": ("angelfish aquarium colorful", "cá thần tiên"),
    "betta fish": ("betta fish siamese fighting fish", "cá betta"),
    "koi": ("koi fish pond colorful", "cá koi"),
    "carp": ("carp freshwater fish", "cá chép"),
    "perch": ("perch freshwater fish", "cá rô"),

    # CHIM
    "albatross": ("albatross seabird flying ocean", "chim hải âu lớn"),
    "seagull": ("seagull bird beach", "chim hải âu"),
    "magpie": ("magpie bird black white", "chim ác là"),
    "canary": ("canary yellow singing bird", "chim hoàng yến"),
    "finch": ("finch small bird", "chim sẻ finch"),
    "nightingale": ("nightingale singing bird", "chim sơn ca"),
    "lark": ("lark bird singing", "chim chiền chiện"),
    "cockatoo": ("cockatoo parrot white", "vẹt mào"),
    "budgerigar": ("budgerigar parakeet", "vẹt yến phụng"),
    "parakeet": ("parakeet small parrot", "vẹt nhỏ"),
    "quetzal": ("quetzal colorful bird", "chim quetzal"),

    # BÒ SÁT
    "monitor lizard": ("monitor lizard reptile", "kỳ đà"),
    "frilled lizard": ("frilled lizard australia", "thằn lằn cổ bạnh"),
    "gila monster": ("gila monster venomous lizard", "thằn lằn gila"),
    "skink": ("skink lizard", "thằn lằn bóng"),
    "slow worm": ("slow worm legless lizard", "thằn lằn không chân"),
    
    #LƯỠNG CƯ
    "axolotl": ("axolotl salamander cute", "kỳ giông mexico"),
    "newt": ("newt amphibian", "sa giông"),
    "tree frog": ("tree frog green", "ếch cây"),
    "bullfrog": ("bullfrog large frog", "ếch bò"),

    #CÔN TRÙNG
    "wasp": ("wasp insect flying", "ong bắp cày"),
    "termite": ("termite insect colony", "mối"),
    "cockroach": ("cockroach insect", "gián"),
    "mosquito": ("mosquito insect flying", "muỗi"),
    "centipede": ("centipede many legs", "rết"),
    "millipede": ("millipede many legs", "cuốn chiếu"),
    "stick insect": ("stick insect camouflage", "bọ que"),
    "leaf insect": ("leaf insect camouflage", "bọ lá"),

    #ĐỘNG VẬT BIỂN
    "squid": ("squid ocean underwater", "mực"),
    "cuttlefish": ("cuttlefish ocean camouflage", "mực nang"),
    "nautilus": ("nautilus shell ocean", "ốc anh vũ"),
    "sea urchin": ("sea urchin ocean spiny", "nhím biển"),
    "barnacle": ("barnacle shell ocean rock", "hà biển"),
    "krill": ("krill small ocean crustacean", "nhuyễn thể krill"),

    # Khủng long
    "dinosaur": ("dinosaur prehistoric", "khủng long"),
    "tyrannosaurus rex": ("tyrannosaurus rex dinosaur", "khủng long bạo chúa"),
    "velociraptor": ("velociraptor dinosaur", "khủng long săn mồi"),
    "triceratops": ("triceratops dinosaur horns", "khủng long ba sừng"),
    "stegosaurus": ("stegosaurus dinosaur plates", "khủng long gai lưng"),
    "brachiosaurus": ("brachiosaurus dinosaur long neck", "khủng long cổ dài"),
    "diplodocus": ("diplodocus dinosaur long tail", "khủng long đuôi roi"),
    "spinosaurus": ("spinosaurus dinosaur sail", "khủng long gai buồm"),
    "ankylosaurus": ("ankylosaurus dinosaur armored", "khủng long bọc giáp"),
    "allosaurus": ("allosaurus dinosaur predator", "khủng long săn mồi"),
    "pterodactyl": ("pterodactyl flying reptile", "thằn lằn bay"),
    "archaeopteryx": ("archaeopteryx feathered dinosaur", "khủng long có lông"),

    #Động vật tiền sử
    "mammoth": ("woolly mammoth ice age", "voi ma mút"),
    "saber tooth tiger": ("saber tooth tiger prehistoric", "hổ răng kiếm"),
    "giant sloth": ("giant sloth prehistoric", "lười khổng lồ"),
    "dire wolf": ("dire wolf prehistoric", "sói khổng lồ"),
    "megatherium": ("megatherium giant sloth", "lười khổng lồ"),
    "glyptodon": ("glyptodon armored mammal", "thú bọc giáp"),
    "deinotherium": ("deinotherium prehistoric elephant", "voi cổ đại"),
    "titanoboa": ("titanoboa giant snake", "rắn khổng lồ"),
    "megalodon": ("megalodon giant shark", "cá mập khổng lồ"),
    "argentavis": ("argentavis giant bird", "chim khổng lồ"),

    #Cá biển sâu
    "anglerfish": ("anglerfish deep sea glowing", "cá cần câu"),
    "gulper eel": ("gulper eel deep sea", "cá chình khổng lồ"),
    "vampire squid": ("vampire squid deep sea", "mực ma cà rồng"),
    "blobfish": ("blobfish deep sea", "cá giọt nước"),
    "lanternfish": ("lanternfish glowing ocean", "cá đèn lồng"),
    "dragonfish": ("dragonfish deep sea", "cá rồng biển sâu"),
    "fangtooth": ("fangtooth fish deep sea", "cá răng nanh"),
    "tripod fish": ("tripod fish deep sea", "cá ba chân"),
    "barreleye": ("barreleye fish transparent head", "cá đầu trong suốt"),
    "giant isopod": ("giant isopod deep sea crustacean", "bọ biển khổng lồ"),

    #Động vật Bắc Cực
    "arctic wolf": ("arctic wolf snow", "sói bắc cực"),
    "arctic hare": ("arctic hare snow", "thỏ bắc cực"),
    "arctic tern": ("arctic tern bird migration", "chim nhạn bắc cực"),
    "snowy owl": ("snowy owl arctic", "cú tuyết"),
    "narwhal": ("narwhal whale tusk", "cá voi kỳ lân"),
    "beluga whale": ("beluga whale white", "cá voi trắng"),
    "arctic ground squirrel": ("arctic ground squirrel", "sóc đất bắc cực"),

    #Động vật Nam Cực
    "emperor penguin": ("emperor penguin antarctica", "chim cánh cụt hoàng đế"),
    "adelie penguin": ("adelie penguin antarctica", "chim cánh cụt adelie"),
    "chinstrap penguin": ("chinstrap penguin antarctica", "chim cánh cụt quai mũ"),
    "weddell seal": ("weddell seal antarctica", "hải cẩu weddell"),
    "leopard seal": ("leopard seal antarctica", "hải cẩu báo"),
    "crabeater seal": ("crabeater seal antarctica", "hải cẩu ăn cua"),

    #Động vật Amazon
    "jaguarundi": ("jaguarundi wild cat", "mèo rừng"),
    "pink river dolphin": ("amazon river dolphin pink", "cá heo sông"),
    "poison dart frog": ("poison dart frog colorful", "ếch phi tiêu"),
    "green anaconda": ("green anaconda snake", "trăn xanh"),
    "capuchin monkey": ("capuchin monkey jungle", "khỉ mũ"),
    "howler monkey": ("howler monkey jungle", "khỉ hú"),
    "spider monkey": ("spider monkey jungle", "khỉ nhện"),
    "electric eel": ("electric eel amazon", "cá chình điện"),
    "piranha": ("piranha fish amazon", "cá ăn thịt"),
    "arapaima": ("arapaima giant fish", "cá khổng lồ"),

    #Động vật quý hiếm
    "saola": ("saola rare animal vietnam", "sao la"),
    "amur leopard": ("amur leopard rare", "báo amur"),
    "sumatran tiger": ("sumatran tiger rare", "hổ sumatra"),
    "vaquita": ("vaquita porpoise rare", "cá heo vaquita"),
    "okapi": ("okapi giraffe relative", "hươu okapi"),
    "aye aye": ("aye aye lemur madagascar", "vượn aye aye"),
    "pangolin giant": ("giant pangolin", "tê tê khổng lồ"),
    "red panda": ("red panda rare", "gấu trúc đỏ"),
    "ethiopian wolf": ("ethiopian wolf rare", "sói ethiopia"),
    "kakapo": ("kakapo flightless parrot", "vẹt kakapo"),

    # ===== ĐỘNG VẬT KHÁC =====
    "deer": ("deer wildlife forest", "nai"),
    "moose": ("moose wildlife antlers", "nai sừng tấm"),
    "elk": ("elk wildlife", "nai sừng xám"),
    "reindeer": ("reindeer snow christmas", "tuần lộc"),
    "camel": ("camel desert sand", "lạc đà"),
    "badger": ("badger wildlife", "lửng"),
    "honey badger": ("honey badger wildlife fierce", "lửng mật"),
    "weasel": ("weasel wildlife small", "chồn"),
    "ferret": ("ferret pet cute", "chồn sương"),
    "mink": ("mink wildlife", "chồn vizon"),
    "otter": ("otter river cute swimming", "rái cá"),
    "sea otter": ("sea otter ocean cute", "rái cá biển"),
    "beaver": ("beaver river dam", "hải ly"),
    "hedgehog": ("hedgehog cute small spines", "nhím"),
    "porcupine": ("porcupine wildlife spines", "nhím"),
    "pangolin": ("pangolin wildlife scales", "tê tê"),
    "sloth": ("sloth wildlife slow cute tree", "con lười"),
    "armadillo": ("armadillo wildlife", "tatu"),
    "raccoon": ("raccoon wildlife masked", "gấu mèo"),
    "skunk": ("skunk wildlife stripe", "chồn hôi"),
    "squirrel": ("squirrel wildlife tree nut", "sóc"),
    "chipmunk": ("chipmunk wildlife cute small", "sóc chuột"),
    "bat": ("bat flying night wildlife", "dơi"),
    "meerkat": ("meerkat wildlife standing", "cầy meerkat"),
    "mongoose": ("mongoose wildlife", "cầy mangut"),
    "hyena": ("hyena wildlife africa laughing", "linh cẩu"),
    "jackal": ("jackal wildlife", "chó rừng"),
    "wild boar": ("wild boar wildlife forest", "lợn rừng"),
    "bison": ("bison wildlife america", "bò rừng bison"),
    "yak": ("yak wildlife mountain", "bò tây tạng"),
    "musk ox": ("musk ox arctic", "bò xạ hương"),
    "tapir": ("tapir wildlife", "heo vòi"),
    "anteater": ("anteater wildlife tongue", "thú ăn kiến"),
    "aardvark": ("aardvark wildlife", "lợn đất"),

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
    
    # 1. Tìm chính xác trong database
    if name_lower in ANIMAL_DATABASE:
        search_term, display_name = ANIMAL_DATABASE[name_lower]
        print(f"      [SEARCH] ✓ '{animal_name}' -> search: '{search_term}', display: '{display_name}'")
        return search_term, display_name
    
    # 2. Tìm partial match
    for key, (search_term, display_name) in ANIMAL_DATABASE.items():
        if key in name_lower or name_lower in key:
            print(f"      [SEARCH] ~ '{animal_name}' -> search: '{search_term}', display: '{display_name}' (partial: {key})")
            return search_term, display_name
    
    # 3. Nếu tên đã là tiếng Anh (không có dấu), dùng trực tiếp để search
    import unicodedata
    normalized = unicodedata.normalize('NFD', animal_name)
    is_ascii = all(ord(c) < 128 for c in normalized if c.isalpha())
    
    if is_ascii:
        # Tên tiếng Anh - dùng trực tiếp
        search_term = f"{animal_name} wildlife animal"
        print(f"      [SEARCH] ? '{animal_name}' -> search: '{search_term}' (English, not in DB)")
        return search_term, animal_name
    
    # 4. Tên tiếng Việt không có trong DB - cảnh báo
    print(f"      [SEARCH] ⚠️ '{animal_name}' KHÔNG có trong database!")
    print(f"      [SEARCH] ⚠️ Hãy dùng tên tiếng Anh để search chính xác!")
    return "animal wildlife", animal_name


async def search_pexels_videos(query: str, per_page: int = 5) -> list[dict]:
    """Tìm video từ Pexels API."""
    if not PEXELS_API_KEY:
        print("  [!] Cần PEXELS_API_KEY trong .env")
        return []
    
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}  # 16:9 YouTube style
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    videos = []
                    for v in data.get("videos", []):
                        # Lấy video chất lượng phù hợp (HD hoặc SD)
                        for vf in v.get("video_files", []):
                            if vf.get("quality") in ["hd", "sd"] and vf.get("width", 0) >= 720:
                                videos.append({
                                    "id": v["id"],
                                    "url": vf["link"],
                                    "width": vf["width"],
                                    "height": vf["height"],
                                    "duration": v.get("duration", 10),
                                })
                                break
                    return videos
                else:
                    print(f"  [!] Pexels API error: {resp.status}")
                    return []
    except Exception as e:
        print(f"  [!] Pexels search error: {e}")
        return []


async def search_pexels_images(query: str, per_page: int = 5) -> list[dict]:
    """Tìm ảnh từ Pexels API."""
    if not PEXELS_API_KEY:
        print("  [!] Cần PEXELS_API_KEY trong .env")
        return []
    
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}  # 16:9 YouTube style
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    images = []
                    for p in data.get("photos", []):
                        images.append({
                            "id": p["id"],
                            "url": p["src"]["large2x"],  # Ảnh chất lượng cao
                            "url_landscape": p["src"].get("landscape", p["src"]["large2x"]),  # Ảnh ngang
                        })
                    return images
                else:
                    print(f"  [!] Pexels API error: {resp.status}")
                    return []
    except Exception as e:
        print(f"  [!] Pexels search error: {e}")
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


def resize_video_for_short(input_path: str, output_path: str, target_duration: float = None) -> str | None:
    """
    Resize video về kích thước chuẩn (1920x1080 landscape - YouTube style).
    """
    try:
        target_w, target_h = Config.VIDEO_WIDTH, Config.VIDEO_HEIGHT
        
        # Filter: scale + pad để fit 16:9 landscape
        filter_complex = (
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black,"
            f"format=yuv420p"
        )
        
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", filter_complex,
            "-r", str(Config.FPS),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
        ]
        
        if target_duration:
            cmd.extend(["-t", str(target_duration)])
        
        cmd.append(output_path)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"      [!] FFmpeg resize error: {result.stderr[:300]}")
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            size_kb = os.path.getsize(output_path) / 1024
            print(f"      Resized: {size_kb:.1f} KB")
            return output_path
        return None
    except Exception as e:
        print(f"  [!] Resize error: {e}")
        return None


def create_image_video(image_path: str, output_path: str, duration: float = 5.0) -> str | None:
    """Tạo video từ ảnh tĩnh (1920x1080 landscape - YouTube style)."""
    try:
        # Scale ảnh về đúng kích thước 16:9, pad nếu cần
        filter_complex = (
            f"scale={Config.VIDEO_WIDTH}:{Config.VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={Config.VIDEO_WIDTH}:{Config.VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
            f"format=yuv420p"
        )
        
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", filter_complex,
            "-t", str(duration),
            "-r", str(Config.FPS),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"      [!] FFmpeg image error: {result.stderr[:300]}")
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
        return None
    except Exception as e:
        print(f"  [!] Image to video error: {e}")
        return None


async def generate_animal_narration(animal_name: str, output_path: str) -> tuple[str | None, float]:
    """
    Tạo audio đọc tên động vật.
    Trả về: (đường dẫn file, duration)
    """
    import edge_tts
    import hashlib
    
    # Text đọc rõ ràng, có ngắt nghỉ
    text = f"Đây là ... {animal_name}."
    
    # Tính hash của text để verify
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
    
    print(f"      ┌─────────────────────────────────────────")
    print(f"      │ [TTS] Animal: '{animal_name}'")
    print(f"      │ [TTS] Text: '{text}'")
    print(f"      │ [TTS] Text hash: {text_hash}")
    print(f"      │ [TTS] Output: {output_path}")
    print(f"      └─────────────────────────────────────────")
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Xóa file cũ nếu tồn tại để tránh dùng lại
        if os.path.exists(output_path):
            os.remove(output_path)
            print(f"      [TTS] Removed old file")
        
        # Tạo Edge TTS instance MỚI cho mỗi lần gọi
        communicate = edge_tts.Communicate(
            text=text,
            voice=Config.TTS_VOICE,
            rate="-20%",  # Chậm hơn 20% để rõ ràng
        )
        
        # AWAIT và đợi hoàn thành
        await communicate.save(output_path)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            duration = get_video_duration(output_path)
            size_kb = os.path.getsize(output_path) / 1024
            
            # Tính MD5 của file audio để verify
            with open(output_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()[:8]
            
            print(f"      [TTS] ✓ Created: {output_path}")
            print(f"      [TTS] ✓ Size: {size_kb:.1f} KB, Duration: {duration:.1f}s")
            print(f"      [TTS] ✓ File hash: {file_hash}")
            
            return output_path, duration
        else:
            print(f"      [TTS] ✗ Failed to create audio file")
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
    """Ghép audio vào video. XÓA audio gốc của video, chỉ dùng audio mới."""
    import hashlib
    
    try:
        video_duration = get_video_duration(video_path)
        audio_duration = get_video_duration(audio_path)
        
        # Tính hash để verify
        with open(audio_path, 'rb') as f:
            audio_hash = hashlib.md5(f.read()).hexdigest()[:8]
        
        print(f"      ┌─────────────────────────────────────────")
        print(f"      │ [MERGE] Animal: {animal_name}")
        print(f"      │ [MERGE] Video: {video_path}")
        print(f"      │ [MERGE] Audio: {audio_path}")
        print(f"      │ [MERGE] Audio hash: {audio_hash}")
        print(f"      │ [MERGE] Video dur: {video_duration:.1f}s, Audio dur: {audio_duration:.1f}s")
        print(f"      └─────────────────────────────────────────")
        
        # QUAN TRỌNG: 
        # -an: Xóa audio gốc của video
        # -map 0:v:0: Lấy video stream từ input 0
        # -map 1:a:0: Lấy audio stream từ input 1 (file audio mới)
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-preset", "fast", 
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-map", "0:v:0",      # Chỉ lấy VIDEO từ file video
            "-map", "1:a:0",      # Chỉ lấy AUDIO từ file audio mới
            "-t", str(video_duration),
            "-movflags", "+faststart",
            output_path,
        ]
        
        print(f"      [MERGE] Running ffmpeg...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"      [!] FFmpeg merge error: {result.stderr[:300]}")
            return None
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            size_kb = os.path.getsize(output_path) / 1024
            final_duration = get_video_duration(output_path)
            print(f"      [MERGE] ✓ Output: {output_path}")
            print(f"      [MERGE] ✓ Final: {size_kb:.1f} KB, {final_duration:.1f}s")
            return output_path
        return None
    except Exception as e:
        print(f"  [!] Merge audio error: {e}")
        import traceback
        traceback.print_exc()
        return None


def concatenate_videos(video_paths: list[str], output_path: str) -> str | None:
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
        
        # Dùng re-encode để đảm bảo tương thích
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]
        
        print(f"    Running ffmpeg concat...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Cleanup list file
        if os.path.exists(list_path):
            os.remove(list_path)
        
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


async def create_animal_clip(
    animal_name: str,
    work_dir: str,
    clip_index: int,
    use_video: bool = True,
    clip_duration: float = 8.0,
) -> str | None:
    """
    Tạo 1 clip về 1 con vật:
    1. Tạo audio đọc tên TRƯỚC (để biết duration)
    2. Tìm video/ảnh thực từ Pexels
    3. Tạo video với duration >= audio
    4. Ghép lại
    """
    # Lấy thông tin động vật: search term (tiếng Anh) và display name (tiếng Việt)
    search_term, display_name = get_animal_info(animal_name)
    
    # Tạo tên thư mục an toàn
    safe_name = "".join(c for c in animal_name if c.isalnum() or c in " _-").strip().replace(" ", "_")
    
    print(f"    [{clip_index}] Creating clip for: {animal_name}")
    print(f"      -> Search: '{search_term}'")
    print(f"      -> Display: '{display_name}'")
    
    # Thư mục riêng cho mỗi con vật - dùng cả index và tên để tránh nhầm
    clip_dir = os.path.join(work_dir, f"clip_{clip_index:03d}_{safe_name}")
    os.makedirs(clip_dir, exist_ok=True)
    
    print(f"      Working dir: {clip_dir}")
    
    # ========== BƯỚC 1: Tạo audio TRƯỚC (đọc tên tiếng Việt) ==========
    print(f"      [AUDIO] Generating narration for: {display_name}")
    audio_path = os.path.join(clip_dir, f"narration_{safe_name}.mp3")
    audio_result, audio_duration = await generate_animal_narration(display_name, audio_path)
    
    if audio_result:
        print(f"      [AUDIO] Created: {audio_path}")
    
    # Thêm im lặng trước và sau audio để có nhịp
    if audio_result:
        audio_with_silence = os.path.join(clip_dir, f"narration_{safe_name}_padded.mp3")
        padded = add_silence_to_audio(audio_path, audio_with_silence, silence_before=0.8, silence_after=1.5)
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
        # Thử tìm video trước
        print(f"      [VIDEO] Searching videos for: {search_term}")
        videos = await search_pexels_videos(search_term, per_page=3)
        
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
                print(f"      [VIDEO] Resizing video to 9:16...")
                media_path = resize_video_for_short(raw_video, video_clip_path, target_video_duration)
                if media_path:
                    print(f"      [VIDEO] Created: {media_path}")
    
    if not media_path:
        # Fallback: dùng ảnh
        print(f"      [IMAGE] Searching images for: {search_term}")
        images = await search_pexels_images(search_term, per_page=3)
        
        if images:
            image = random.choice(images)
            raw_image = os.path.join(clip_dir, f"raw_{safe_name}.jpg")
            
            print(f"      [IMAGE] Downloading image...")
            downloaded = await download_file(image["url_landscape"], raw_image)  # Ảnh ngang 16:9
            
            if downloaded:
                print(f"      [IMAGE] Creating video from image ({target_video_duration:.1f}s)...")
                media_path = create_image_video(raw_image, video_clip_path, target_video_duration)
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


# ============ DANH SÁCH ĐỘNG VẬT THEO CHỦ ĐỀ ============
# Chỉ lấy những động vật có trong ANIMAL_DATABASE (tiếng Anh)

ANIMAL_CATEGORIES = {
    "african": {
        "title": "Động vật hoang dã châu Phi",
        "animals": ["lion", "elephant", "giraffe", "zebra", "rhino", "hippo", "leopard", "cheetah", "hyena", "buffalo", "antelope"]
    },
    "ocean": {
        "title": "Khám phá đại dương",
        "animals": ["dolphin", "whale", "shark", "sea turtle", "octopus", "jellyfish", "seahorse", "clownfish", "manta ray", "seal", "orca"]
    },
    "birds": {
        "title": "Thế giới loài chim",
        "animals": ["eagle", "owl", "penguin", "flamingo", "peacock", "parrot", "toucan", "hummingbird", "swan", "pelican", "hawk"]
    },
    "pets": {
        "title": "Thú cưng đáng yêu",
        "animals": ["cat", "dog", "rabbit", "hamster", "goldfish", "parrot", "kitten", "puppy", "bunny", "guinea pig"]
    },
    "farm": {
        "title": "Động vật trang trại",
        "animals": ["cow", "pig", "horse", "sheep", "goat", "chicken", "duck", "donkey", "llama", "alpaca"]
    },
    "forest": {
        "title": "Động vật rừng",
        "animals": ["bear", "wolf", "fox", "deer", "owl", "squirrel", "raccoon", "badger", "hedgehog", "rabbit"]
    },
    "jungle": {
        "title": "Rừng nhiệt đới",
        "animals": ["tiger", "monkey", "gorilla", "orangutan", "parrot", "toucan", "snake", "chameleon", "sloth", "jaguar"]
    },
    "arctic": {
        "title": "Vùng Bắc Cực",
        "animals": ["polar bear", "penguin", "seal", "walrus", "arctic fox", "reindeer", "orca", "whale"]
    },
    "australia": {
        "title": "Động vật nước Úc",
        "animals": ["kangaroo", "koala", "platypus", "wombat", "emu", "crocodile", "tasmanian devil"]
    },
    "reptiles": {
        "title": "Thế giới bò sát",
        "animals": ["crocodile", "snake", "lizard", "chameleon", "turtle", "tortoise", "iguana", "gecko", "komodo dragon"]
    },
    "primates": {
        "title": "Họ hàng linh trưởng",
        "animals": ["monkey", "gorilla", "chimpanzee", "orangutan", "gibbon", "baboon", "lemur"]
    },
    "insects": {
        "title": "Thế giới côn trùng",
        "animals": ["butterfly", "bee", "dragonfly", "ladybug", "ant", "spider", "grasshopper", "firefly", "praying mantis"]
    },
    "underwater": {
        "title": "Dưới đáy đại dương",
        "animals": ["shark", "octopus", "jellyfish", "seahorse", "starfish", "crab", "lobster", "coral", "clownfish", "manta ray"]
    },
    "predators": {
        "title": "Những kẻ săn mồi",
        "animals": ["lion", "tiger", "wolf", "eagle", "shark", "crocodile", "cheetah", "leopard", "hawk", "orca"]
    },
    "cute": {
        "title": "Động vật dễ thương",
        "animals": ["panda", "koala", "otter", "hedgehog", "rabbit", "kitten", "puppy", "sloth", "penguin", "red fox"]
    },
}


def generate_animal_scripts(user_prompt: str, num_videos: int = 1, animals_per_video: int = 50) -> list[dict]:
    """
    Tạo danh sách động vật từ ANIMAL_DATABASE (không dùng Ollama).
    Random theo chủ đề hoặc random tổng hợp.
    
    Args:
        user_prompt: Chủ đề (có thể để trống)
        num_videos: Số video cần tạo
        animals_per_video: Số động vật mỗi video (mặc định 50)
    """
    import random
    
    prompt_lower = user_prompt.lower()
    
    # Tìm chủ đề phù hợp từ prompt
    matched_categories = []
    
    keyword_mapping = {
        "african": ["châu phi", "africa", "safari", "hoang dã"],
        "ocean": ["biển", "ocean", "sea", "đại dương", "marine"],
        "birds": ["chim", "bird", "bay", "flying"],
        "pets": ["thú cưng", "pet", "nuôi", "nhà"],
        "farm": ["trang trại", "farm", "nông trại"],
        "forest": ["rừng", "forest", "woodland"],
        "jungle": ["rừng nhiệt đới", "jungle", "tropical"],
        "arctic": ["bắc cực", "arctic", "polar", "tuyết", "snow"],
        "australia": ["úc", "australia", "kangaroo", "koala"],
        "reptiles": ["bò sát", "reptile", "rắn", "snake"],
        "primates": ["linh trưởng", "khỉ", "monkey", "ape"],
        "insects": ["côn trùng", "insect", "bọ", "bug"],
        "underwater": ["dưới nước", "underwater", "lặn", "diving"],
        "predators": ["săn mồi", "predator", "hunter", "ăn thịt"],
        "cute": ["dễ thương", "cute", "đáng yêu", "adorable"],
    }
    
    for cat_key, keywords in keyword_mapping.items():
        if any(kw in prompt_lower for kw in keywords):
            matched_categories.append(cat_key)
    
    # Nếu không match hoặc prompt là "all" / "tất cả", lấy từ tất cả categories
    if not matched_categories or "all" in prompt_lower or "tất cả" in prompt_lower:
        matched_categories = list(ANIMAL_CATEGORIES.keys())
    
    print(f"  [ANIMAL] Matched categories: {matched_categories}")
    print(f"  [ANIMAL] Target: {num_videos} video(s), {animals_per_video} animals each")
    
    # Thu thập TẤT CẢ động vật từ các categories phù hợp (không trùng lặp)
    all_available_animals = set()
    for cat_key in matched_categories:
        all_available_animals.update(ANIMAL_CATEGORIES[cat_key]["animals"])
    
    # Nếu vẫn không đủ, lấy thêm từ tất cả categories
    if len(all_available_animals) < animals_per_video:
        for cat_key in ANIMAL_CATEGORIES:
            all_available_animals.update(ANIMAL_CATEGORIES[cat_key]["animals"])
    
    all_available_animals = list(all_available_animals)
    random.shuffle(all_available_animals)
    
    print(f"  [ANIMAL] Total available: {len(all_available_animals)} unique animals")
    
    videos = []
    used_animals = set()
    
    for i in range(num_videos):
        # Lấy động vật chưa dùng
        available = [a for a in all_available_animals if a not in used_animals]
        
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
        print(f"           Last 5: {selected[-5:]}")
    
    return videos
