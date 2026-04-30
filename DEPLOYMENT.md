# Деплой через Git

Ручная загрузка папок в Hugging Face или Cloudflare не используется. Нормальный
flow такой:

```text
локальный код -> GitHub monorepo -> Cloudflare Pages
                         |
                         -> Hugging Face Space git remote
```

GitHub остаётся основным источником правды. Hugging Face Space получает только
папку `MasteringBackend` через `git subtree push`.

## 1. Подготовить локальный Git

Сейчас проект должен быть обычным git-репозиторием.

```powershell
cd C:\Users\BAD\Desktop\OnlineMastering
git init
git add .gitignore MasteringBackend MasteringFrontend scripts DEPLOYMENT.md README.md requirements.txt
git commit -m "Initial online mastering MVP"
```

Важно: аудио, stems, `.venv`, research outputs и локальные исходники уже
исключены через `.gitignore`.

## 2. Создать GitHub репозиторий

На GitHub создайте репозиторий, например:

```text
tajmaker/hypermusiclife-mastering
```

Потом подключите его локально:

```powershell
git branch -M main
git remote add origin https://github.com/tajmaker/hypermusiclife-mastering.git
git push -u origin main
```

Дальше вся разработка идёт через обычный git:

```powershell
git status
git add .
git commit -m "..."
git push
```

## 3. Hugging Face Space как git remote

Space уже есть:

```text
tajmaker/hypermusiclife
```

Адрес git remote:

```text
https://huggingface.co/spaces/tajmaker/hypermusiclife
```

Добавьте remote:

```powershell
git remote add hf https://huggingface.co/spaces/tajmaker/hypermusiclife
```

Проверить:

```powershell
git remote -v
```

Должно быть примерно:

```text
origin  https://github.com/tajmaker/hypermusiclife-mastering.git
hf      https://huggingface.co/spaces/tajmaker/hypermusiclife
```

## 4. Деплой backend в Hugging Face

Hugging Face Space должен получать не весь monorepo, а только backend.

Используем `git subtree`:

```powershell
.\scripts\deploy-hf-backend.ps1
```

Внутри он выполняет:

```powershell
git subtree push --prefix MasteringBackend hf main
```

После push Hugging Face сам запустит Docker build.

Проверить backend:

```text
https://tajmaker-hypermusiclife.hf.space/docs
```

И endpoint:

```text
GET /api/v1/stem-rebalance/presets
```

Если возвращаются `safe` и `vocal`, backend живой.

## 5. Cloudflare Pages из GitHub

Cloudflare должен деплоить frontend из GitHub, не из локальной папки.

В Cloudflare:

```text
Workers & Pages -> Create application -> Pages -> Connect to Git
```

Выберите GitHub репозиторий:

```text
tajmaker/hypermusiclife-mastering
```

Build settings:

```text
Framework preset: Vite
Root directory: MasteringFrontend
Build command: npm run build
Build output directory: dist
```

Environment variable:

```text
VITE_API_URL=https://tajmaker-hypermusiclife.hf.space/api/v1
```

После каждого `git push origin main` Cloudflare будет сам пересобирать frontend.

## 6. Нормальный рабочий цикл

Разработка:

```powershell
git checkout -b feature/some-change
# правки
npm.cmd run build
git add .
git commit -m "Implement some change"
git push origin feature/some-change
```

После проверки merge в `main`.

Frontend деплоится автоматически через Cloudflare после push/merge.

Backend деплоится явно:

```powershell
git checkout main
git pull
.\scripts\deploy-hf-backend.ps1
```

Так backend не будет случайно пересобираться на каждый мелкий frontend commit.

## 7. Локальный запуск

Backend:

```powershell
cd MasteringBackend
..\.venv\Scripts\pip.exe install -e ".[api,stems]"
..\.venv\Scripts\python.exe -m uvicorn mastering.api.app:app --host 127.0.0.1 --port 8010
```

Frontend:

```powershell
cd MasteringFrontend
npm install
npm run dev
```

Открыть:

```text
http://127.0.0.1:5173
```

## 8. Что важно для продакшена

Текущий Hugging Face backend — MVP:

- состояние задач хранится в памяти;
- файлы лежат локально в `hosted_runs`;
- одновременно работает один worker;
- нет авторизации;
- нет автоочистки старых файлов;
- бесплатный CPU может быть медленным.

Следующий backend-уровень:

```text
API layer -> Application services -> Job repository -> File storage -> Worker
```

Минимальные улучшения:

1. JSON/SQLite job repository вместо памяти.
2. Cleanup service для старых задач.
3. Лимиты по размеру и длительности файла.
4. Отдельный worker/process для тяжёлой обработки.
5. Persistent storage или object storage.
6. Auth/token для публичного доступа.

## 9. Быстрый чеклист

Один раз:

```text
[ ] git init
[ ] создать GitHub repo
[ ] git remote add origin ...
[ ] git remote add hf https://huggingface.co/spaces/tajmaker/hypermusiclife
[ ] git push origin main
[ ] .\scripts\deploy-hf-backend.ps1
[ ] подключить Cloudflare Pages к GitHub
[ ] добавить VITE_API_URL
```

Каждый deploy:

```text
Frontend: git push origin main
Backend:  .\scripts\deploy-hf-backend.ps1
```
