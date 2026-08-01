"""Handler router'lari. Tartib muhim: admin common'dan oldin turadi, chunki
«⚙️ Admin panel» tugmasi common'dagi umumiy matn filtrlariga tushib ketmasligi
kerak."""
from aiogram import Router

from bot.handlers import admin, booking, common


def build_router() -> Router:
    root = Router(name="root")
    root.include_router(admin.router)
    root.include_router(booking.router)
    root.include_router(common.router)
    return root
