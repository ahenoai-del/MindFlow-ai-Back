import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from core.config import settings


async def correct_text(text: str) -> str:
    if not settings.OPENAI_API_KEY:
        return _correct_local(text)
    
    try:
        from openai import AsyncOpenAI
        
        # Check if it's a fireworks key
        if settings.OPENAI_API_KEY.startswith("csk-"):
            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url="https://api.fireworks.ai/inference/v1"
            )
            model = "accounts/fireworks/models/gpt-4o-mini"
        else:
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            model = "gpt-4o-mini"
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": """Ты корректор текста. Твоя задача - исправить текст задачи:
1. Исправь опечатки и грамматические ошибки
2. Расшифруй сокращения (завт -> завтра, идт -> идти, ворк -> работа и т.д.)
3. Сделай текст читаемым и понятным
4. Сохрани смысл оригинала
5. Не добавляй ничего лишнего

Ответь ТОЛЬКО исправленным текстом без объяснений."""
                },
                {"role": "user", "content": text}
            ],
            temperature=0.2,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Correction error: {e}")
        return _correct_local(text)


def _correct_local(text: str) -> str:
    corrections = {
        "завт": "завтра",
        "завтр": "завтра",
        "идт": "идти",
        "ворк": "работа",
        "сег": "сегодня",
        "сегдн": "сегодня",
        "сегдня": "сегодня",
        "потм": "потом",
        "птм": "потом",
        "щас": "сейчас",
        "сйчас": "сейчас",
        "над": "надо",
        "нд": "надо",
        "делть": "делать",
        "сдлть": "сделать",
        "купит": "купить",
        "звн": "звонок",
        "звон": "звонок",
        "встр": "встреча",
        "встрч": "встреча",
        "отчт": "отчёт",
        "прочт": "прочитать",
        "док": "документ",
        "докум": "документ",
        "реп": "репетиция",
        "трен": "тренировка",
        "учб": "учёба",
        "учеб": "учёба",
        "домш": "домашнее",
        "домшк": "домашка",
        "рабт": "работа",
        "прв": "проверить",
        "провер": "проверить",
        "нпс": "написать",
        "напс": "написать",
        "звнк": "звонок",
        "позв": "позвонить",
        "отпр": "отправить",
        "получ": "получить",
        "законч": "закончить",
        "закон": "закончить",
        "начть": "начать",
        "начн": "начать",
        "продл": "продолжить",
        "подгот": "подготовить",
        "выполн": "выполнить",
        "сост": "составить",
        "заполн": "заполнить",
        "посм": "посмотреть",
        "посмотр": "посмотреть",
        "сход": "сходить",
        "пойт": "пойти",
        "прийт": "прийти",
        "уйт": "уйти",
        "верн": "вернуться",
        "поех": "поехать",
        "приех": "приехать",
        "встрт": "встретить",
        "позн": "познакомиться",
        "обзв": "обзвонить",
        "напомн": "напомнить",
        "попр": "поправить",
        "испр": "исправить",
        "обсуд": "обсудить",
        "решт": "решить",
        "принт": "принять",
        "отлож": "отложить",
        "перенс": "перенести",
        "отмн": "отменить",
        "подтв": "подтвердить",
        "согл": "согласовать",
        "утв": "утвердить",
        "подпс": "подписать",
        "отпрв": "отправить",
        "полч": "получить",
        "выд": "выдать",
        "разд": "раздать",
        "собр": "собрать",
        "разбр": "разобрать",
        "очст": "очистить",
        "убр": "убрать",
        "помыть": "помыть",
        "постр": "построить",
        "созд": "создать",
        "удл": "удалить",
        "измн": "изменить",
        "обнов": "обновить",
        "сохр": "сохранить",
        "найт": "найти",
        "потр": "потерять",
        "верн": "вернуть",
        "куп": "купить",
        "прод": "продать",
        "обмен": "обменять",
        "закз": "заказать",
        "дост": "доставить",
        "прин": "принять",
        "забр": "забрать",
        "привез": "привезти",
        "отвез": "отвезти",
        "посл": "послать",
        "перед": "передать",
    }
    
    import re
    
    corrected = text
    
    for wrong, right in corrections.items():
        pattern = r'\b' + re.escape(wrong) + r'\b'
        corrected = re.sub(pattern, right, corrected, flags=re.IGNORECASE)
    
    if corrected != text:
        corrected = corrected[0].upper() + corrected[1:]
    
    return corrected


async def parse_task_text(text: str) -> Dict[str, Any]:
    corrected_text = await correct_text(text)
    
    if not settings.OPENAI_API_KEY:
        result = _parse_local(corrected_text)
        result['original_text'] = text
        result['corrected_text'] = corrected_text
        return result
    
    try:
        from openai import AsyncOpenAI
        
        # Check if it's a fireworks key
        if settings.OPENAI_API_KEY.startswith("csk-"):
            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url="https://api.fireworks.ai/inference/v1"
            )
            model = "accounts/fireworks/models/gpt-4o-mini"
        else:
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            model = "gpt-4o-mini"
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": f"""Ты помощник для парсинга задач. Извлеки из текста:
- title: название задачи (кратко, исправленное)
- description: описание (если есть детали)
- deadline: дата дедлайна в формате YYYY-MM-DD (если указана, сегодня: {today})
- priority: 1-3 (1=высокий, 2=средний, 3=низкий)
- category: work/home/study/sport/other
- estimated_minutes: примерное время в минутах (если указано)

Ответь ТОЛЬКО JSON без markdown."""
                },
                {"role": "user", "content": corrected_text}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        result = json.loads(response.choices[0].message.content)
        result['original_text'] = text
        result['corrected_text'] = corrected_text
        return result
    
    except Exception as e:
        print(f"OpenAI error: {e}")
        result = _parse_local(corrected_text)
        result['original_text'] = text
        result['corrected_text'] = corrected_text
        return result


def _parse_local(text: str) -> Dict[str, Any]:
    result = {
        "title": text[:100],
        "priority": 2,
        "category": "general"
    }
    
    text_lower = text.lower()
    
    if any(w in text_lower for w in ["срочно", "важно", "немедленно", "urgent", "important"]):
        result["priority"] = 1
    elif any(w in text_lower for w in ["позже", "когда-нибудь", "later", "someday"]):
        result["priority"] = 3
    
    if any(w in text_lower for w in ["работ", "meet", "клиент", "проект", "work"]):
        result["category"] = "work"
    elif any(w in text_lower for w in ["дом", "квартир", "home", "уборк"]):
        result["category"] = "home"
    elif any(w in text_lower for w in ["учеб", "курс", "learn", "study", "экзамен"]):
        result["category"] = "study"
    elif any(w in text_lower for w in ["спорт", "тренаж", "gym", "fitness", "бег"]):
        result["category"] = "sport"
    
    if "завтра" in text_lower:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        result["deadline"] = tomorrow
    elif "сегодня" in text_lower or "вечер" in text_lower or "утро" in text_lower:
        result["deadline"] = datetime.now().strftime("%Y-%m-%d")
    
    import re
    time_match = re.search(r"(\d{1,2}):(\d{2})", text)
    if time_match:
        pass
    
    return result
