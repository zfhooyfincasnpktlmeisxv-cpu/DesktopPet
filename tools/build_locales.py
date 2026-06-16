#!/usr/bin/env python3
"""Build complete locale JSON files (18 languages) from en.json + translation packs."""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCALES = ROOT / "src" / "i18n" / "locales"
EN_PATH = LOCALES / "en.json"

# Shared text pool templates (pet speech bubbles)
def _pools(
    fallback: str,
    happy: list[str],
    hungry: list[str],
    sad: list[str],
    normal: list[str],
    feed: list[str],
    pet: list[str],
    no_food: list[str],
    game_win: list[str],
    game_daily_cap: list[str],
) -> dict:
    return {
        "fallback": fallback,
        "happy": happy,
        "hungry": hungry,
        "sad": sad,
        "normal": normal,
        "feed": feed,
        "pet": pet,
        "no_food": no_food,
        "game_win": game_win,
        "game_daily_cap": game_daily_cap,
    }


def _shop_burger(name: str, desc: str) -> dict:
    return {"shop_items": {"burger": {"name": name, "description": desc}}}


def _games(
    snake_n, snake_d, catch_n, catch_d, dodge_n, dodge_d, mem_n, mem_d, rich_n, rich_d, chess_n, chess_d
) -> dict:
    return {
        "games": {
            "snake": {"name": snake_n, "description": snake_d},
            "catch": {"name": catch_n, "description": catch_d},
            "dodge": {"name": dodge_n, "description": dodge_d},
            "memory": {"name": mem_n, "description": mem_d},
            "richman": {"name": rich_n, "description": rich_d},
            "chess": {"name": chess_n, "description": chess_d},
        }
    }


def _gf_snake(lang_lines: dict[str, list[str]]) -> dict:
    return {"game_feedback": {"snake": lang_lines}}


# Compact game feedback (start + a few events) per language — full keys fall back to en/constants
def _gf_compact(start: str, food: str, win: str, death: str) -> dict:
    return {
        "game_feedback": {
            "snake": {"start": [start], "food": [food], "milestone_3": [win], "death": [death]},
            "catch": {"start": [start], "catch": [food], "complete": [win], "death": [death]},
            "dodge": {"start": [start], "near_miss": [food], "milestone_30": [win], "death": [death]},
            "memory": {"start": [start], "match": [food], "complete": [win], "death": [death]},
        }
    }


PACKS: dict[str, dict] = {
    "zh_CN": {
        "menu": {
            "feed": "喂食", "feed_count": "喂食 🍖×{count}", "pet": "抚摸", "wake": "唤醒",
            "add_pet": "添加新宠物", "switch_skin": "切换皮肤", "show_stat_hud": "显示状态栏",
            "shop": "小商店", "backpack": "背包", "game_hub": "陪玩打工", "settings": "设置",
            "hide": "隐藏", "quit": "退出程序",
        },
        "store": {
            "header_title": "小商店", "shop_hint": "购买食物后，在右键菜单选择「喂食」即可使用。",
            "price_each": "💰 {price} 金币 / 个", "quantity": "数量",
            "bag_item_kinds": "物品种类 {count}", "bag_feedable": "可喂食 {count}",
            "empty_bag_hint": "背包是空的\n去「商店」买点食物吧～",
            "tag_food": "可喂食", "tag_item": "道具", "buy": "购买",
            "buy_success": "购买成功！{emoji} {name} ×{qty}",
            "buy_fail": "购买失败，请稍后再试",
            "not_enough_gold": "金币不足，还差 {need} 金币", "close": "关闭",
        },
        **_shop_burger("汉堡", "喂食时消耗，恢复饱食与少量心情"),
        **_games("贪吃蛇", "方向键或 WASD 控制", "接汉堡", "← → 接盘 60 秒", "流星躲避", "躲避流星",
                 "美食记忆", "90 秒内翻牌配对", "大富翁", "24 格城市棋盘", "国际象棋", "人机或双人"),
        "text_pools": _pools("喵～",
            ["你好呀！", "今天真开心~", "主人来陪我玩吧！"],
            ["我饿了...", "想吃好吃的！", "🍖"],
            ["心情不好...", "摸摸我好不好？", "😢"],
            ["喵～", "我在哦～", "有什么事吗？"],
            ["好吃！", "谢谢主人！", "饱饱的～"],
            ["舒服～", "再摸摸～", "❤️"],
            ["没有食物了…去商店买点吧！", "背包里没有吃的～"],
            ["打工辛苦啦！赚了不少金币～", "一起玩真开心！💰"],
            ["今天打工够啦～", "明日再来陪我玩！"]),
    },
    "nl": {
        "menu": {
            "feed": "Voeren", "feed_count": "Voeren 🍖×{count}", "pet": "Aaien", "wake": "Wekken",
            "add_pet": "Huisdier toevoegen", "switch_skin": "Skin wisselen",
            "show_stat_hud": "Statusbalk tonen", "shop": "Winkel", "backpack": "Rugzak",
            "game_hub": "Minispellen", "settings": "Instellingen", "hide": "Verbergen", "quit": "Afsluiten",
        },
        "tray": {
            "toggle_pets": "Huisdieren tonen / verbergen", "add_pet": "Huisdier toevoegen",
            "settings": "Instellingen", "quit": "Afsluiten",
            "startup_visible": "Je huisdier is terug op het bureaublad. Rechtsklik op het tray-pictogram om te sluiten.",
            "startup_hidden": "Je huisdier is verborgen. Linksklik op het tray-pictogram om het te tonen.",
        },
        "settings": {
            "language_hint": "Wordt direct toegepast op menu's en dialogen.",
            "auto_walk": "Automatisch wandelen", "show_stat_hud": "Honger / humeur tonen",
            "opacity": "Venstertransparantie",
        },
        "store": {
            "title": "Winkel & rugzak", "header_title": "Winkel", "shop_tab": "Winkel", "bag_tab": "Rugzak",
            "gold": "Goud: {amount}", "shop_hint": "Koop eten en gebruik Voeren via het rechtsklikmenu.",
            "price_each": "💰 {price} goud per stuk", "quantity": "Aantal",
            "bag_item_kinds": "Soorten items: {count}", "bag_feedable": "Te voeren: {count}",
            "empty_bag_hint": "Rugzak is leeg.\nKoop eten in de winkel~",
            "tag_food": "Voedsel", "tag_item": "Voorwerp", "buy": "Kopen",
            "buy_success": "Gekocht! {emoji} {name} ×{qty}",
            "buy_fail": "Aankoop mislukt. Probeer later opnieuw.",
            "not_enough_gold": "Niet genoeg goud — nog {need} nodig", "close": "Sluiten",
        },
        **_shop_burger("Hamburger", "Wordt gebruikt bij voeren; herstelt honger en een beetje humeur"),
        "game_hub": {
            "title": "Minispellen", "subtitle": "Speel met je huisdier en verdien goud",
            "gold_today": "Goud vandaag over: {left} / {cap}", "pet_live": "💬 Huisdier live",
            "waiting": "Wachten op start…", "fps": "Framerate", "vsync": "VSync",
            "featured": "Uitgelicht", "mini_games": "Arcade", "enter_3d_board": "3D-bord openen",
            "start_match": "Wedstrijd starten", "start": "Spelen", "close": "Sluiten",
            "wins_badge": "{count} overwinningen", "best_score": "Beste {score}",
            "session_title": "Minispellen · {name}",
        },
        **_games("Slang", "Pijltjes of WASD", "Burgers vangen", "← → 60 seconden",
                 "Meteor ontwijken", "Overleef langer", "Geheugenspel", "90 sec paren",
                 "Monopoly", "24-tegel bord", "Schaken", "AI of lokaal 2 spelers"),
        "text_pools": _pools("Miauw~",
            ["Hoi!", "Wat een fijne dag~", "Kom met me spelen!"],
            ["Ik heb honger...", "Iets lekkers alsjeblieft!", "🍖"],
            ["Ik voel me down...", "Aai me even?", "😢"],
            ["Miauw~", "Ik ben er~", "Iets nodig?"],
            ["Lekker!", "Bedankt!", "Ik zit vol~"],
            ["Heerlijk~", "Nog meer~", "❤️"],
            ["Geen eten meer… naar de winkel!", "Rugzak leeg~"],
            ["Goed gedaan! Goud verdiend~", "Dat was leuk! 💰"],
            ["Genoeg gewerkt vandaag~", "Tot morgen!"]),
        **_gf_compact("Laten we gaan!", "Lekker!", "Geweldig!", "Opnieuw proberen!"),
        "stat_hud": {"hunger": "Honger", "mood": "Humeur", "intimacy": "Lv.{level}"},
    },
    "de": {
        "menu": {
            "feed": "Füttern", "feed_count": "Füttern 🍖×{count}", "pet": "Streicheln", "wake": "Wecken",
            "add_pet": "Haustier hinzufügen", "switch_skin": "Skin wechseln",
            "show_stat_hud": "Statusleiste", "shop": "Shop", "backpack": "Rucksack",
            "game_hub": "Minispiele", "settings": "Einstellungen", "hide": "Verstecken", "quit": "Beenden",
        },
        "store": {
            "header_title": "Shop", "shop_hint": "Nach dem Kauf über das Rechtsklick-Menü „Füttern“ verwenden.",
            "price_each": "💰 {price} Gold pro Stück", "quantity": "Menge", "buy": "Kaufen", "close": "Schließen",
            "bag_item_kinds": "Artikelarten: {count}", "bag_feedable": "Fütterbar: {count}",
            "empty_bag_hint": "Rucksack ist leer.\nKauf Essen im Shop~",
            "tag_food": "Futter", "tag_item": "Gegenstand",
            "buy_success": "Gekauft! {emoji} {name} ×{qty}",
            "not_enough_gold": "Nicht genug Gold — noch {need} nötig",
        },
        **_shop_burger("Burger", "Beim Füttern verbraucht; stellt Hunger und etwas Stimmung wieder her"),
        "text_pools": _pools("Miau~",
            ["Hallo!", "Schöner Tag~", "Spiel mit mir!"],
            ["Ich habe Hunger...", "Etwas Leckeres bitte!"],
            ["Schlechte Laune...", "Streichel mich?", "😢"],
            ["Miau~", "Ich bin da~"],
            ["Lecker!", "Danke!", "Satt~"],
            ["Schön~", "Mehr bitte~", "❤️"],
            ["Kein Futter… zum Shop!", "Rucksack leer~"],
            ["Gut gemacht! Gold verdient~", "Das macht Spaß! 💰"],
            ["Genug für heute~", "Bis morgen!"]),
        **_gf_compact("Los geht's!", "Lecker!", "Super!", "Nochmal!"),
    },
    "fr": {
        "menu": {
            "feed": "Nourrir", "feed_count": "Nourrir 🍖×{count}", "pet": "Caresser", "wake": "Réveiller",
            "shop": "Boutique", "backpack": "Sac", "game_hub": "Mini-jeux", "settings": "Paramètres",
            "hide": "Masquer", "quit": "Quitter",
        },
        "store": {
            "header_title": "Boutique", "shop_hint": "Après l'achat, utilisez Nourrir dans le menu clic droit.",
            "price_each": "💰 {price} or pièce", "quantity": "Qté", "buy": "Acheter", "close": "Fermer",
            "tag_food": "Nourriture", "buy_success": "Acheté ! {emoji} {name} ×{qty}",
            "not_enough_gold": "Pas assez d'or — il manque {need}",
        },
        **_shop_burger("Burger", "Consommé en nourrissant ; restaure faim et un peu d'humeur"),
        "text_pools": _pools("Miaou~",
            ["Coucou !", "Belle journée~", "Viens jouer !"],
            ["J'ai faim...", "Something tasty please!"],
            ["Je suis triste...", "Caresses ?"],
            ["Miaou~", "Je suis là~"],
            ["Délicieux !", "Merci !"],
            ["Ça fait du bien~", "Encore~"],
            ["Plus de nourriture…", "Sac vide~"],
            ["Bravo ! Or gagné~", "C'était fun ! 💰"],
            ["Assez pour aujourd'hui~", "À demain !"]),
        **_gf_compact("C'est parti !", "Miam !", "Super !", "Encore !"),
    },
    "es": {
        "menu": {
            "feed": "Alimentar", "feed_count": "Alimentar 🍖×{count}", "pet": "Acariciar",
            "shop": "Tienda", "backpack": "Mochila", "game_hub": "Minijuegos", "settings": "Ajustes",
            "quit": "Salir", "hide": "Ocultar",
        },
        "store": {
            "header_title": "Tienda", "shop_hint": "Tras comprar, usa Alimentar en el menú contextual.",
            "price_each": "💰 {price} oro c/u", "quantity": "Cant.", "buy": "Comprar", "close": "Cerrar",
            "buy_success": "¡Comprado! {emoji} {name} ×{qty}",
            "not_enough_gold": "Oro insuficiente — faltan {need}",
        },
        **_shop_burger("Hamburguesa", "Se consume al alimentar; restaura hambre y algo de ánimo"),
        "text_pools": _pools("Miau~",
            ["¡Hola!", "Qué buen día~", "¡Juguemos!"],
            ["Tengo hambre...", "¡Comida por favor!"],
            ["Estoy triste...", "¿Me acaricias?"],
            ["Miau~", "Aquí estoy~"],
            ["¡Rico!", "¡Gracias!"],
            ["Qué bien~", "Más~"],
            ["Sin comida…", "Mochila vacía~"],
            ["¡Bien hecho! Oro~", "¡Qué divertido! 💰"],
            ["Suficiente por hoy~", "¡Hasta mañana!"]),
        **_gf_compact("¡Vamos!", "¡Rico!", "¡Genial!", "¡Otra vez!"),
    },
    "it": {
        "menu": {"feed": "Nutri", "feed_count": "Nutri 🍖×{count}", "pet": "Accarezza", "shop": "Negozio",
                 "settings": "Impostazioni", "quit": "Esci"},
        "store": {"header_title": "Negozio", "buy": "Compra", "close": "Chiudi",
                  "price_each": "💰 {price} oro cad.", "quantity": "Qtà"},
        **_shop_burger("Hamburger", "Consumato quando nutri; ripristina fame e umore"),
        "text_pools": _pools("Miao~",
            ["Ciao!", "Che bella giornata~"], ["Ho fame..."], ["Sono triste..."],
            ["Miao~"], ["Buono!", "Grazie!"], ["Che bello~"],
            ["Niente cibo…"], ["Bravo! Oro~"], ["Basta per oggi~"]),
        **_gf_compact("Via!", "Buono!", "Grande!", "Ancora!"),
    },
    "pt": {
        "menu": {"feed": "Alimentar", "pet": "Acariciar", "shop": "Loja", "settings": "Configurações", "quit": "Sair"},
        "store": {"header_title": "Loja", "buy": "Comprar", "close": "Fechar",
                  "price_each": "💰 {price} ouro cada", "quantity": "Qtd"},
        **_shop_burger("Hambúrguer", "Consumido ao alimentar; restaura fome e humor"),
        "text_pools": _pools("Miau~",
            ["Olá!", "Que dia lindo~"], ["Estou com fome..."], ["Estou triste..."],
            ["Miau~"], ["Gostoso!", "Obrigado!"], ["Que bom~"],
            ["Sem comida…"], ["Mandou bem! Ouro~"], ["Chega por hoje~"]),
        **_gf_compact("Vamos!", "Gostoso!", "Ótimo!", "De novo!"),
    },
    "ru": {
        "menu": {"feed": "Кормить", "feed_count": "Кормить 🍖×{count}", "pet": "Гладить",
                 "shop": "Магазин", "settings": "Настройки", "quit": "Выход"},
        "store": {"header_title": "Магазин", "buy": "Купить", "close": "Закрыть",
                  "price_each": "💰 {price} золота / шт.", "quantity": "Кол-во"},
        **_shop_burger("Бургер", "Тратится при кормлении; восстанавливает сытость и настроение"),
        "text_pools": _pools("Мяу~",
            ["Привет!", "Какой хороший день~"], ["Я голоден..."], ["Мне грустно..."],
            ["Мяу~"], ["Вкусно!", "Спасибо!"], ["Приятно~"],
            ["Еды нет…"], ["Молодец! Золото~"], ["Хватит на сегодня~"]),
        **_gf_compact("Поехали!", "Вкусно!", "Отлично!", "Ещё раз!"),
    },
    "ja": {
        "menu": {
            "feed": "エサ", "feed_count": "エサ 🍖×{count}", "pet": "なでる", "wake": "起こす",
            "shop": "ショップ", "backpack": "バッグ", "game_hub": "ミニゲーム", "settings": "設定",
            "hide": "非表示", "quit": "終了",
        },
        "store": {
            "header_title": "ショップ", "shop_hint": "購入後、右クリックメニューの「エサ」で使えます。",
            "price_each": "💰 {price} ゴールド / 個", "quantity": "数量", "buy": "購入", "close": "閉じる",
            "bag_item_kinds": "アイテム種類 {count}", "bag_feedable": "エサ可能 {count}",
            "empty_bag_hint": "バッグは空です\nショップで買いましょう~",
            "tag_food": "エサ", "buy_success": "購入成功！{emoji} {name} ×{qty}",
            "not_enough_gold": "ゴールド不足 — あと {need}",
        },
        **_shop_burger("バーガー", "エサやりで消費。満腹度と気分を回復"),
        "text_pools": _pools("ニャ～",
            ["こんにちは！", "いい天気~", "遊ぼう！"],
            ["お腹すいた…", "おいしいものちょうだい！"],
            ["元気ない…", "なでて？"],
            ["ニャ～", "ここにいるよ~"],
            ["おいしい！", "ありがとう！"],
            ["気持ちいい~", "もっと~"],
            ["エサがない…", "バッグ空っぽ~"],
            ["お疲れ様！ゴールドGET~", "楽しかった！💰"],
            ["今日はここまで~", "また明日！"]),
        **_gf_compact("行こう！", "おいしい！", "すごい！", "もう一回！"),
    },
    "ko": {
        "menu": {
            "feed": "먹이", "feed_count": "먹이 🍖×{count}", "pet": "쓰다듬기",
            "shop": "상점", "backpack": "가방", "game_hub": "미니게임", "settings": "설정", "quit": "종료",
        },
        "store": {
            "header_title": "상점", "shop_hint": "구매 후 우클릭 메뉴에서 먹이를 선택하세요.",
            "price_each": "💰 {price} 골드 / 개", "quantity": "수량", "buy": "구매", "close": "닫기",
            "buy_success": "구매 성공! {emoji} {name} ×{qty}",
            "not_enough_gold": "골드 부족 — {need} 더 필요",
        },
        **_shop_burger("버거", "먹일 때 소비; 배고픔과 기분 회복"),
        "text_pools": _pools("야옹~",
            ["안녕!", "좋은 하루~"], ["배고파..."], ["우울해..."],
            ["야옹~"], ["맛있어!", "고마워!"], ["좋아~"],
            ["먹이 없어…"], ["수고했어! 골드~"], ["오늘은 여기까지~"]),
        **_gf_compact("시작!", "맛있어!", "대단해!", "다시!"),
    },
    "zh_TW": {
        "menu": {"feed": "餵食", "feed_count": "餵食 🍖×{count}", "pet": "撫摸", "shop": "小商店",
                 "settings": "設定", "quit": "結束程式"},
        "store": {
            "header_title": "小商店", "shop_hint": "購買食物後，在右鍵選單選擇「餵食」即可使用。",
            "price_each": "💰 {price} 金幣 / 個", "quantity": "數量", "buy": "購買", "close": "關閉",
            "buy_success": "購買成功！{emoji} {name} ×{qty}",
            "not_enough_gold": "金幣不足，還差 {need}",
        },
        **_shop_burger("漢堡", "餵食時消耗，恢復飽食與少量心情"),
        "text_pools": _pools("喵～",
            ["你好呀！", "今天真開心~"], ["我餓了..."], ["心情不好..."],
            ["喵～"], ["好吃！", "謝謝主人！"], ["舒服～"],
            ["沒有食物了…"], ["打工辛苦啦！"], ["今天夠啦~"]),
    },
    "ar": {
        "menu": {"feed": "إطعام", "pet": "دلّك", "shop": "متجر", "settings": "الإعدادات", "quit": "خروج"},
        "store": {"header_title": "متجر", "buy": "شراء", "close": "إغلاق", "price_each": "💰 {price} ذهب"},
        **_shop_burger("برجر", "يُستهلك عند الإطعام؛ يستعيد الجوع والمزاج"),
        "text_pools": _pools("مواء~",
            ["مرحباً!", "يوم جميل~"], ["أنا جائع..."], ["حزين..."],
            ["مواء~"], ["لذيذ!", "شكراً!"], ["جميل~"],
            ["لا طعام…"], ["أحسنت! ذهب~"], ["يكفي لليوم~"]),
    },
    "hi": {
        "menu": {"feed": "खिलाएँ", "pet": "प्यार करें", "shop": "दुकान", "settings": "सेटिंग", "quit": "बाहर"},
        "store": {"header_title": "दुकान", "buy": "खरीदें", "close": "बंद", "price_each": "💰 {price} सोना"},
        **_shop_burger("बर्गर", "खिलाने पर खर्च; भूख और मूड बढ़ाता है"),
        "text_pools": _pools("म्याऊ~",
            ["नमस्ते!", "क्या दिन है~"], ["भूख लगी..."], ["उदास हूँ..."],
            ["म्याऊ~"], ["स्वादिष्ट!", "धन्यवाद!"], ["अच्छा लगा~"],
            ["खाना नहीं…"], ["शाबाश! सोना~"], ["आज बस~"]),
    },
    "th": {
        "menu": {"feed": "ให้อาหาร", "pet": "ลูบ", "shop": "ร้านค้า", "settings": "ตั้งค่า", "quit": "ออก"},
        "store": {"header_title": "ร้านค้า", "buy": "ซื้อ", "close": "ปิด", "price_each": "💰 {price} ทอง"},
        **_shop_burger("เบอร์เกอร์", "ใช้เมื่อให้อาหาร ฟื้นความหิวและอารมณ์"),
        "text_pools": _pools("เหมียว~",
            ["สวัสดี!", "วันดี~"], ["หิว..."], ["เศร้า..."],
            ["เหมียว~"], ["อร่อย!", "ขอบคุณ!"], ["ดี~"],
            ["ไม่มีอาหาร…"], ["เก่ง! ได้ทอง~"], ["พอแล้ววันนี้~"]),
    },
    "vi": {
        "menu": {"feed": "Cho ăn", "pet": "Vuốt ve", "shop": "Cửa hàng", "settings": "Cài đặt", "quit": "Thoát"},
        "store": {"header_title": "Cửa hàng", "buy": "Mua", "close": "Đóng", "price_each": "💰 {price} vàng"},
        **_shop_burger("Burger", "Dùng khi cho ăn; hồi đói và tâm trạng"),
        "text_pools": _pools("Meo~",
            ["Chào!", "Ngày đẹp~"], ["Đói quá..."], ["Buồn..."],
            ["Meo~"], ["Ngon!", "Cảm ơn!"], ["Thích~"],
            ["Hết đồ ăn…"], ["Giỏi! Vàng~"], ["Đủ rồi hôm nay~"]),
    },
    "tr": {
        "menu": {"feed": "Besle", "pet": "Okşa", "shop": "Dükkan", "settings": "Ayarlar", "quit": "Çık"},
        "store": {"header_title": "Dükkan", "buy": "Satın al", "close": "Kapat", "price_each": "💰 {price} altın"},
        **_shop_burger("Burger", "Beslerken tüketilir; açlık ve ruh hali verir"),
        "text_pools": _pools("Miyav~",
            ["Merhaba!", "Güzel gün~"], ["Acıktım..."], ["Üzgünüm..."],
            ["Miyav~"], ["Lezzetli!", "Teşekkürler!"], ["Güzel~"],
            ["Yemek yok…"], ["Aferin! Altın~"], ["Bugünlük yeter~"]),
    },
    "pl": {
        "menu": {"feed": "Nakarm", "pet": "Pogłaskaj", "shop": "Sklep", "settings": "Ustawienia", "quit": "Wyjdź"},
        "store": {"header_title": "Sklep", "buy": "Kup", "close": "Zamknij", "price_each": "💰 {price} złota"},
        **_shop_burger("Burger", "Zużywany przy karmieniu; przywraca głód i nastrój"),
        "text_pools": _pools("Miau~",
            ["Cześć!", "Piękny dzień~"], ["Głodny..."], ["Smutno..."],
            ["Miau~"], ["Pyszne!", "Dzięki!"], ["Miło~"],
            ["Brak jedzenia…"], ["Brawo! Złoto~"], ["Na dziś wystarczy~"]),
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def main() -> None:
    en = json.loads(EN_PATH.read_text(encoding="utf-8"))
    # Add English game feedback (short)
    en.setdefault("game_feedback", {})
    en["game_feedback"].update(_gf_compact("Let's go!", "Nice!", "Great!", "Try again!")["game_feedback"])
    EN_PATH.write_text(json.dumps(en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for code, pack in PACKS.items():
        merged = _deep_merge(en, pack)
        path = LOCALES / f"{code}.json"
        path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("wrote", path.name)

    print("done", len(PACKS), "locales")


if __name__ == "__main__":
    main()
