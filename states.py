from aiogram.fsm.state import State, StatesGroup

class TaskStates(StatesGroup):
    waiting_for_reminder_name = State()
    waiting_for_reminder_time = State()
    waiting_for_task = State()
class ScheduleState(StatesGroup):
    time = State()
    day = State()
    text = State()
    