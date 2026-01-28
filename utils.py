import re
from datetime import datetime, timedelta

def parse_time(time_str):
    """Парсит время из строки в формате ЧЧ:ММ или ЧЧ.ММ"""
    try:
        time_str = time_str.replace('.', ':')
        time_pattern = r'^(\d{1,2})[:.](\d{2})$'
        match = re.match(time_pattern, time_str)
        
        if not match:
            return None
            
        hours = int(match.group(1))
        minutes = int(match.group(2))
        
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            return None
            
        return hours, minutes
        
    except (ValueError, AttributeError):
        return None

def get_time_until_reminder(reminder_time):
    """Рассчитывает оставшееся время до напоминания"""
    now = datetime.now()
    reminder_hour, reminder_minute = map(int, reminder_time.split(':'))
    
    reminder_today = now.replace(hour=reminder_hour, minute=reminder_minute, second=0, microsecond=0)
    
    if reminder_today < now:
        reminder_today += timedelta(days=1)
    
    time_left = reminder_today - now
    hours_left = time_left.seconds // 3600
    minutes_left = (time_left.seconds % 3600) // 60
    
    if hours_left > 0:
        return f"{hours_left}ч {minutes_left}м"
    else:
        return f"{minutes_left}м"

def format_tasks_list(tasks, reminders, schedule=None):
    text = "📋 **ВАШ СПИСОК ДЕЛ**\n\n"
    
    if tasks:
        text += "✅ **Задачи:**\n"
        for i, task in enumerate(tasks, 1):
            text += f"{i}. {task[1]}\n"
        text += "\n"

    active_reminders = [r for r in reminders if not r[3]]
    if active_reminders:
        text += "⏰ **Напоминания:**\n"
        for r in active_reminders:
            text += f"• {r[1]} в {r[2]}\n"
        text += "\n"

    if schedule:
        text += "🗓 **Постоянное расписание:**\n"
        current_day = ""
        for day, time, task_text in schedule:
            if day != current_day:
                text += f"┈┈ {day.capitalize()} ┈┈\n"
                current_day = day
            text += f"└ {time} — {task_text}\n"
            
    if not tasks and not active_reminders and not schedule:
        return "📭 Ваш список пока пуст!"
        
    return text