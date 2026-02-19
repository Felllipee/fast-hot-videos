
# Keyword-based Video Categorizer
# Supports multiple languages: EN, PT, ES, RU, etc.

CATEGORIES_KEYWORDS = {
    "Amador": ["amador", "amateur", "home made", "homemade", "handmade", "caseiro", "doméstico"],
    "Anal": ["anal", "ass", "butt", "sodomy", "anale", "arrombada", "cuzinho", "anus", "rectum", "анал", "жопа"],
    "Asiática": ["asian", "chinese", "korean", "japanese", "oriental", "japonesa", "chinesa", "coreana", "азиатка", "китаянка"],
    "ASMR": ["asmr", "whisper", "sussurro", "soft spoken", "licking", "ear licking"],
    "BBW": ["bbw", "chubby", "fat", "plump", "gorda", "gordinha", "fofinha", "rubenesque", "толстая", "пышка"],
    "Bi": ["bi", "bisexual", "bi-sexual", "bissexual", "mmf", "ffm", "threesome", "бисексуал"],
    "Boquete": ["blowjob", "bj", "sucking", "suck", "oral", "throat", "deepthroat", "gagging", "boquete", "mamada", "chupando", "garganta", "glub", "минет", "отсос"],
    "Brasileira": ["brazilian", "brazil", "brasileira", "brasil", "br", "brazzers", "бразильянка"],
    "Bunda Grande": ["big ass", "big butt", "booty", "pawg", "thick", "bunduda", "rabuda", "bunda", "popozuda", "raba", "большая жопа"],
    "Casada": ["wife", "housewife", "hotwife", "cheating", "esposa", "casada", "dona de casa", "corna", "traicao", "жена", "домохозяйка"],
    "Caseiro": ["homemade", "home video", "private", "real couple", "amador", "caseiro", "privado", "flagra", "caiu na net", "vazou", "домашнее"],
    "Coroa": ["milf", "mature", "mom", "mother", "momma", "mommy", "mama", "cougar", "coroa", "mae", "tudona", "мамочка", "зрелая"],
    "DP": ["dp", "double penetration", "double", "dupla penetracao", "dois paus", "двойное проникновение"],
    "Fisting": ["fisting", "fist", "hand", "punho", "enterrada", "fistfuck", "фистинг"],
    "Gangbang": ["gangbang", "gang bang", "orgy", "group", "groupsex", "suruba", "orgia", "bukkake", "bukke", "grupada", "групповуха"],
    "Gay": ["gay", "homosexual", "queer", "twink", "bear", "homo", "lgbt", "гей", "гомо"],
    "Gostosa": ["hot", "sexy", "babe", "stunning", "gostosa", "delicia", "maravilhosa", "linda", "красотка", "секси"],
    "Indiano": ["indian", "desi", "bhabhi", "hindu", "indiana", "indiano", "индианка"],
    "Interracial": ["interracial", "ir", "bbc", "bwc", "blacked", "black on blonde", "inter", "mixed", "negão", "preto e loira", "интер"],
    "Japonesa": ["japanese", "jav", "uncensored", "japonesa", "nippon", "японка"],
    "Lésbicas": ["lesbian", "dyke", "girl on girl", "tribadism", "scissoring", "lesbo", "sapphic", "less", "sapatão", "tesoura", "лейсбиянка"],
    "Lingerie": ["lingerie", "underwear", "panties", "stockings", "nylons", "calcinha", "sutiã", "meia calça", "renda", "белье", "чулки"],
    "Loira": ["blonde", "blond", "fair", "platinum", "loira", "loirinha", "galega", "блондинка"],
    "Madrasta": ["stepmom", "step-mom", "stepmother", "step mother", "family", "taboo", "madrasta", "enteada", "step", "мачеха"],
    "Massagem": ["massage", "oil", "rub", "nururu", "massagem", "oleo", "relax", "массаж"],
    "Milf": ["milf", "mature", "mom", "coroa", "mae", "tiabzinha", "милф"],
    "Morena": ["brunette", "dark hair", "brown hair", "morena", "mulata", "cacheada", "брюнетка"],
    "Novinhas": ["teen", "young", "18", "schoolgirl", "student", "fresh", "legal", "novinha", "estudante", "menina", "collegial", "подросток", "школьница"],
    "Pau Grande": ["big cock", "big dick", "huge cock", "monster cock", "hung", "pauzao", "pau grande", "dotado", "roludo", "jeba", "большой член"],
    "Peitão": ["big tits", "big boobs", "huge tits", "busty", "large tits", "peituada", "peitão", "tetuda", "melões", "comissão de frente", "большая грудь"],
    "Preto": ["black", "ebony", "african", "preto", "negra", "negro", "afro", "черная"],
    "Ruivas": ["redhead", "ginger", "red head", "fire crotch", "ruiva", "vermelha", "рыжая"],
    "Siririca": ["masturbation", "fingering", "solo", "touching", "dildo", "vibrator", "toy", "siririca", "dedo", "brinquedo", "solo", "мастурбация"],
    "Squirting": ["squirt", "gushing", "fountain", "wet", "soaking", "squirting", "esguicho", "mijo", "molhada", "сквирт"],
    "Transexual": ["trans", "shemale", "ladyboy", "tgirl", "tranny", "futanari", "dickgirl", "transexual", "travesti", "ts", "trap", "трансуха"],
    "Tudo": ["tudo", "all", "everything", "compilation", "best of", "melhores", "compilado"]
}

def detect_category(title):
    """
    Detects the best category for a video based on its title.
    Returns 'Outros' if no keyword matches.
    """
    if not title:
        return "Outros"
    
    title_lower = title.lower()
    
    # Priority check (optional: define order if some keywords are subset of others)
    # We iterate through the dictionary. The first match determines the category?
    # Or should we count matches? For simplicity and speed, first match is decent, 
    # but some categories overlap. 'Brazzers' -> 'Brasileira' but maybe 'Milf' too.
    # Let's try to match specifically.
    
    for category, keywords in CATEGORIES_KEYWORDS.items():
        for keyword in keywords:
            # Check for whole word matches or distinct enough substrings
            # Simple substring check is fast and works for most cases here
            if keyword in title_lower:
                return category
                
    return "Outros"

if __name__ == "__main__":
    # Test cases
    test_titles = [
        "Stepsister stuck in dryer",
        "Novinha no colegio dando o rabo",
        "Russian teen hard fuck",
        "Big tits blonde milf",
        "Japonesa safada no onibus",
        "Some random unknown title 123"
    ]
    
    print("Testing Keyword Categorizer:")
    for t in test_titles:
        print(f"'{t}' -> {detect_category(t)}")
