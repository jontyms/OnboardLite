import random

wordlist = ["Thoroughbred", "Arabian", "QuarterHorse", "PaintHorse", "Appaloosa",
             "Walking", "Standardbred", "Andalusian", "Percheron", "Morgan", "Friesian",
             "PasoFino", "Welsh", "Shetland", "Clydesdale", "Palomino", "Haflinger",
             "Mustang", "AkhalTeke", "GypsyVanner", "Pegasus", "Lusitano", "Connemara",
             "Trakehner", "Hanoverian", "Oldenburg", "SelleFrancais", "Holsteiner",
             "IrishSport", "Lipizzan", "Freiberger", "Knabstrupper", "RockyMountain",
             "TennesseeWalking", "AmericanSaddlebred", "Icelandic", "Peruvian", "Canadian",
             "DutchWarmblood", "Fjord", "NorwegianFjord", "BelgianWarmblood", "SwedishWarmblood",
             "DanishWarmblood", "GermanWarmblood", "AustralianStock", "Criollo",
             "SuffolkPunch", "NewForest", "WelshCob", "Hackney", "Highland",
             "ThuringianWarmblood", "Westphalian", "Fell", "Galician",
             "ArabianCross", "Trotter", "Gelderlander", "OrlovTrotter", "Pintabian",
             "Morab", "Warlander", "IrishCob", "Dartmoor", "Exmoor",
             "BashkirCurly", "BlackForest", "Brandenburger", "HaflingerCross",
             "IrishDraught", "Jutland", "Karabakh", "LipizzanCross", "Mecklenburger",
             "Miniature", "Mule", "MustangCross", "NormanCob", "Pleven", "Sanhe",
             "SchleswigerHeavyDraft", "Schwarzwald", "Senner", "SpanishJennet",
             "Taishuh", "Tawleed", "Tchernomor", "Waler", "Wielkopolski", "Knugget",
             "Mare", "Stallion", "Filly", "Foal", "Colt", "Pony", "Plinko", "Horse",
             "Helsinki", "Lexington", "BuenosAires", "Dubai", "Paris", "Tokyo", "Orlando",
             "Aachen", "Syndey", "Nitro", "Cyber", "Challenger"]

class HorsePass:
    """
    The Horse Plinko password generator
    """

    def __init__(self):
        super(HorsePas, self).__init__()

    def gen():
        word1, word2, word3, word4 = random.sample(wordlist, 4)
        password = f"{word1}-{word2}-{word3}-{word4}-{random.randint(0, 99):02}"
        return password