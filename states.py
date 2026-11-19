
from aiogram.fsm.state import State, StatesGroup


class SenderCreateInvite(StatesGroup):
    choosing_city = State()
    choosing_style = State()


class RecipientSurvey(StatesGroup):
    step_food = State()
    step_activity = State()
    step_day = State()
    step_day_custom = State()
    step_time = State()
    step_time_custom = State()
    confirm = State()


class AdminPanelState(StatesGroup):
    waiting_broadcast_text = State()
    waiting_new_city = State()
    waiting_new_option_label = State()