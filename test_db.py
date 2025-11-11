from database import Database

db = Database()

# Проверяем, что метод работает без параметров
try:
    reminders = db.get_due_reminders()
    print("✅ get_due_reminders() работает правильно")
    print(f"Найдено напоминаний: {len(reminders)}")
except Exception as e:
    print(f"❌ Ошибка: {e}")

# Проверяем другие методы
try:
    db.add_user(123, "test", "Test User")
    print("✅ add_user() работает")
except Exception as e:
    print(f"❌ Ошибка add_user: {e}")

try:
    db.add_task(123, "Test task")
    print("✅ add_task() работает")
except Exception as e:
    print(f"❌ Ошибка add_task: {e}")