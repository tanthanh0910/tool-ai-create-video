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

    #Động vật Nam Cực => Đang thực hiện
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


async def search_pexels_videos(query: str, per_page: int = 5, orientation: str = "landscape") -> list[dict]:
    """Tìm video từ Pexels API.
    
    Args:
        query: Từ khóa tìm kiếm
        per_page: Số kết quả mỗi trang
        orientation: "landscape" (ngang), "portrait" (dọc), hoặc "square" (vuông)
    """
    if not PEXELS_API_KEY:
        print("  [!] Cần PEXELS_API_KEY trong .env")
        return []
    
    # Giữ query đơn giản để search chính xác hơn
    # Chỉ thêm "animal" nếu query chưa có, không thêm quá nhiều từ khóa
    clean_query = query.strip()
    print(f"      [Pexels] Search query: '{clean_query}'")
    
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": clean_query, "per_page": per_page, "orientation": orientation}
    
    # Xác định tỷ lệ aspect ratio cần lọc
    if orientation == "portrait":
        min_ratio, max_ratio = 0.4, 0.7  # 9:16 = 0.56
        ratio_label = "PORTRAIT"
    elif orientation == "square":
        min_ratio, max_ratio = 0.9, 1.1  # 1:1 = 1.0
        ratio_label = "SQUARE"
    else:  # landscape
        min_ratio, max_ratio = 1.5, 2.0  # 16:9 = 1.78
        ratio_label = "LANDSCAPE"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    videos = []
                    for v in data.get("videos", []):
                        # Lấy video chất lượng phù hợp (HD hoặc SD)
                        for vf in v.get("video_files", []):
                            vf_width = vf.get("width", 0)
                            vf_height = vf.get("height", 0)
                            
                            if vf_height == 0:
                                continue
                            
                            # Tính tỷ lệ khung hình
                            aspect_ratio = vf_width / vf_height
                            is_correct_orientation = min_ratio <= aspect_ratio <= max_ratio
                            is_good_quality = vf.get("quality") in ["hd", "sd"] and max(vf_width, vf_height) >= 720
                            
                            if is_correct_orientation and is_good_quality:
                                print(f"        [Pexels] ✓ {ratio_label} video: {vf_width}x{vf_height} (ratio: {aspect_ratio:.2f})")
                                videos.append({
                                    "id": v["id"],
                                    "url": vf["link"],
                                    "width": vf_width,
                                    "height": vf_height,
                                    "duration": v.get("duration", 10),
                                })
                                break
                            else:
                                print(f"        [Pexels] ✗ Skip video: {vf_width}x{vf_height} (ratio: {aspect_ratio:.2f}, need {min_ratio}-{max_ratio})")
                    return videos
                else:
                    print(f"  [!] Pexels API error: {resp.status}")
                    return []
    except Exception as e:
        print(f"  [!] Pexels search error: {e}")
        return []


async def search_pexels_images(query: str, per_page: int = 5, orientation: str = "landscape") -> list[dict]:
    """Tìm ảnh từ Pexels API.
    
    Args:
        query: Từ khóa tìm kiếm
        per_page: Số kết quả mỗi trang
        orientation: "landscape" (ngang), "portrait" (dọc), hoặc "square" (vuông)
    """
    if not PEXELS_API_KEY:
        print("  [!] Cần PEXELS_API_KEY trong .env")
        return []
    
    # Giữ query đơn giản để search chính xác hơn
    clean_query = query.strip()
    print(f"      [Pexels] Search query: '{clean_query}'")
    
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": clean_query, "per_page": per_page, "orientation": orientation}
    
    # Xác định tỷ lệ aspect ratio cần lọc
    if orientation == "portrait":
        min_ratio, max_ratio = 0.4, 0.8  # 9:16 = 0.56
        ratio_label = "PORTRAIT"
    elif orientation == "square":
        min_ratio, max_ratio = 0.9, 1.1  # 1:1 = 1.0
        ratio_label = "SQUARE"
    else:  # landscape
        min_ratio, max_ratio = 1.3, 2.5  # 16:9 = 1.78
        ratio_label = "LANDSCAPE"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    images = []
                    for p in data.get("photos", []):
                        img_width = p.get("width", 0)
                        img_height = p.get("height", 0)
                        
                        if img_height == 0:
                            continue
                        
                        aspect_ratio = img_width / img_height
                        if min_ratio <= aspect_ratio <= max_ratio:
                            print(f"        [Pexels] ✓ {ratio_label} image: {img_width}x{img_height} (ratio: {aspect_ratio:.2f})")
                            images.append({
                                "id": p["id"],
                                "url": p["src"]["large2x"],
                                "url_landscape": p["src"].get("landscape", p["src"]["large2x"]),
                                "url_portrait": p["src"].get("portrait", p["src"]["large2x"]),
                                "width": img_width,
                                "height": img_height,
                            })
                        else:
                            print(f"        [Pexels] ✗ Skip image: {img_width}x{img_height} (ratio: {aspect_ratio:.2f}, need {min_ratio}-{max_ratio})")
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
                "[0:a]volume=0.4[original];[1:a]volume=1.2[narration];"
                "[narration][original]amix=inputs=2:duration=longest:dropout_transition=1[aout]",
                "-map", "0:v:0", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(video_duration), "-movflags", "+faststart",
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"      [MERGE] Mix loi, fallback narration only")
                mix_animal_sound = False

        if not mix_animal_sound:
            # Mac dinh: chi doc ten (GIONG NHU TRUOC)
            print(f"      [MERGE] Narration only (doc ten)")
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path, "-i", audio_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(video_duration), "-movflags", "+faststart",
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
        
        # Dùng re-encode để đảm bảo tương thích
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height},setsar=1:1,format=yuv420p",
            "-aspect", aspect_str,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]
        
        print(f"    Running ffmpeg concat -> {target_width}x{target_height} ({aspect_str})...")
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
        # Thử tìm video trước với đúng orientation
        print(f"      [VIDEO] Searching {orientation} videos for: {search_term}")
        videos = await search_pexels_videos(search_term, per_page=5, orientation=orientation)
        
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
        images = await search_pexels_images(search_term, per_page=5, orientation=orientation)
        
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
        "dinosaur": ["khủng long", "dinosaur", "prehistoric", "tiền sử"],
        "rare": ["quý hiếm", "rare", "endangered"],
        "deep sea": ["biển sâu", "deep sea", "abyss"],
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
            "ocean": ["ocean", "sea", "underwater", "marine", "dolphin", "whale", "shark", "turtle", "seal", "octopus", "jellyfish", "coral", "fish", "crab", "lobster", "shrimp", "squid", "orca", "manatee", "dugong", "seahorse", "starfish", "clownfish", "manta", "stingray", "walrus", "narwhal", "beluga"],
            "birds": ["bird", "eagle", "owl", "hawk", "falcon", "parrot", "swan", "pelican", "crane", "heron", "stork", "vulture", "crow", "raven", "sparrow", "pigeon", "dove", "robin", "kingfisher", "woodpecker", "chicken", "rooster", "duck", "goose", "turkey", "flamingo", "peacock", "toucan", "hummingbird", "penguin", "emu", "albatross", "seagull", "magpie", "canary", "finch", "nightingale", "lark", "cockatoo", "budgerigar", "parakeet", "quetzal", "macaw"],
            "pets": ["pet", "cat", "dog", "kitten", "puppy", "rabbit", "bunny", "hamster", "guinea pig", "goldfish", "parrot", "ferret"],
            "farm": ["farm", "cow", "bull", "pig", "horse", "pony", "donkey", "sheep", "lamb", "goat", "llama", "alpaca", "chicken", "duck", "goose", "turkey"],
            "forest": ["forest", "bear", "wolf", "fox", "deer", "moose", "elk", "squirrel", "raccoon", "badger", "hedgehog", "owl", "rabbit"],
            "jungle": ["jungle", "tropical", "tiger", "jaguar", "monkey", "gorilla", "orangutan", "chimpanzee", "gibbon", "toucan", "parrot", "snake", "chameleon", "sloth", "anaconda", "piranha", "capuchin", "howler", "spider monkey"],
            "arctic": ["arctic", "polar", "snow", "antarctic", "polar bear", "penguin", "seal", "walrus", "arctic fox", "reindeer", "narwhal", "beluga", "snowy owl", "arctic wolf", "arctic hare", "lemming"],
            "australia": ["australia", "kangaroo", "koala", "platypus", "wombat", "emu", "tasmanian", "kiwi"],
            "reptiles": ["reptile", "snake", "cobra", "python", "anaconda", "viper", "crocodile", "alligator", "lizard", "chameleon", "iguana", "komodo", "gecko", "tortoise", "turtle", "monitor", "skink"],
            "primates": ["monkey", "ape", "gorilla", "chimpanzee", "orangutan", "gibbon", "baboon", "lemur", "macaque", "capuchin", "howler", "spider monkey"],
            "insects": ["insect", "butterfly", "bee", "dragonfly", "ladybug", "beetle", "ant", "spider", "tarantula", "scorpion", "grasshopper", "cricket", "firefly", "moth", "caterpillar", "praying mantis", "wasp", "termite", "cockroach", "mosquito", "centipede", "millipede"],
            "predators": ["predator", "lion", "tiger", "wolf", "eagle", "shark", "crocodile", "cheetah", "leopard", "hawk", "orca", "jaguar", "bear", "hyena"],
            "cute": ["cute", "panda", "koala", "otter", "hedgehog", "rabbit", "kitten", "puppy", "sloth", "penguin", "red panda", "bunny", "hamster"],
            "fish": ["fish", "salmon", "tuna", "eel", "pufferfish", "catfish", "tilapia", "anchovy", "sardine", "cod", "haddock", "halibut", "flounder", "barracuda", "marlin", "swordfish", "angelfish", "betta", "koi", "carp", "perch", "piranha", "arapaima", "goldfish", "clownfish"],
            "dinosaur": ["dinosaur", "tyrannosaurus", "velociraptor", "triceratops", "stegosaurus", "brachiosaurus", "diplodocus", "spinosaurus", "ankylosaurus", "allosaurus", "pterodactyl", "archaeopteryx", "mammoth", "saber tooth", "megalodon"],
            "rare": ["rare", "saola", "amur", "sumatran", "vaquita", "okapi", "aye aye", "pangolin", "red panda", "ethiopian", "kakapo"],
            "deep sea": ["deep sea", "anglerfish", "gulper", "vampire squid", "blobfish", "lanternfish", "dragonfish", "fangtooth", "tripod fish", "barreleye", "giant isopod"],
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
