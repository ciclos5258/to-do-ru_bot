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

def format_tasks_list(tasks, reminders=None):
    """Форматирует список задач и напоминаний в текст"""
    if not tasks and not reminders:
        return "📭 У вас нет активных задач и напоминаний!"
    
    tasks_text = "📋 Ваши активные задачи и напоминания:\n\n"
    
    if tasks:
        tasks_text += "📝 Задачи:\n"
        for i, task in enumerate(tasks, 1):
            task_id, text, is_done = task
            status = "✅" if is_done else "⏳"
            tasks_text += f"{i}. {status} {text}\nID: {task_id}\n\n"
    
    if reminders:
        active_reminders = [r for r in reminders if not r[3]]
        if active_reminders:
            tasks_text += "⏰ Напоминания:\n"
            for i, reminder in enumerate(active_reminders, 1):
                reminder_id, name, time_str, is_sent = reminder
                time_left = get_time_until_reminder(time_str)
                tasks_text += f"{i + len(tasks) if tasks else i}. ⏰ {name} - {time_str} (через {time_left})\nID: R{reminder_id}\n\n"
    
    return tasks_text