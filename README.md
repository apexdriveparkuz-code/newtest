# Taksapark nazorat boti

Telegram bot hodimlardan kunlik natijalarni qabul qiladi va admin uchun hisobot chiqaradi.

## Imkoniyatlar

- Hodim natija kiritadi: ulangan haydovchi, litsenziya, qo'ng'iroq.
- Admin bugungi hisobotni ko'radi.
- Admin umumiy xulosani ko'radi.
- Ma'lumotlar `taxi_bot.db` SQLite bazasida saqlanadi.

## Ishga tushirish

1. Kutubxonalarni o'rnating:

```powershell
pip install -r requirements.txt
```

Agar kompyuterda `python` yoki `pip` buyrug'i tanilmasa, Codex ichidagi Python bilan ishlatish mumkin:

```powershell
& 'C:\Users\MYPRO\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pip install -r requirements.txt
```

2. `.env.example` faylidan nusxa olib `.env` yarating:

```powershell
Copy-Item .env.example .env
```

3. `.env` ichiga bot token va admin Telegram ID yozing:

```env
BOT_TOKEN=BotFather bergan token
ADMIN_IDS=Sizning Telegram ID raqamingiz
```

Admin Telegram ID ni bilish uchun Telegramda `@userinfobot` yoki shunga o'xshash ID ko'rsatuvchi botlardan foydalanishingiz mumkin.

4. Botni ishga tushiring:

```powershell
python bot.py
```

Agar `python` buyrug'i tanilmasa:

```powershell
& 'C:\Users\MYPRO\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' bot.py
```

## Bot komandalar

- `/start` - menyuni ochadi
- `/hisobot` - admin uchun bugungi hisobot
- `/umumiy` - admin uchun umumiy hisobot

Hodimlar `/start` bosib, `Natija kiritish` tugmasi orqali ma'lumot yuboradi.
