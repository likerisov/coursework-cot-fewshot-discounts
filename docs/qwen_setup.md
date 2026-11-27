# Настройка Qwen API для курсового проекта

Для запуска проекта используется **Alibaba Cloud Model Studio**, а не обычный веб-чат Qwen. Model Studio предоставляет OpenAI-compatible Chat Completions API; текущий Python-клиент проекта обращается к нему без отдельного SDK.

## 1. Создать workspace в Европе

1. Откройте [Alibaba Cloud Model Studio](https://modelstudio.console.alibabacloud.com/).
2. Перейдите в управление Workspaces и создайте workspace в регионе **Germany (Frankfurt)**.
3. Для этого учебного проекта выберите service deployment scope **EU**.
4. В карточке workspace найдите поле **API Host**. Оно имеет вид:
   `YOUR_WORKSPACE_ID.eu-central-1.maas.aliyuncs.com`.
5. Скопируйте именно API Host своего workspace. Не копируйте адрес API из другого региона.

## 2. Создать API-ключ

1. В Model Studio откройте управление API keys.
2. Создайте ключ в том же Frankfurt workspace/регионе.
3. Сохраните ключ у себя локально. Не отправляйте его в чат и не добавляйте в GitHub.

Важно: вход в Qwen Chat через пользовательский аккаунт не является API-ключом Model Studio. Для этого проекта нужен именно **Model Studio API Key**.

## 3. Заполнить локальный .env

В корне проекта скопируйте `.env.example` в файл `.env`. Вставьте свои значения:

```dotenv
LLM_API_KEY=ваш_ключ_model_studio
LLM_BASE_URL=https://YOUR_WORKSPACE_ID.eu-central-1.maas.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
```

Замените `YOUR_WORKSPACE_ID` на свой фактический workspace ID/API Host. В конце URL должно остаться `/compatible-mode/v1`.

Файл `.env` добавлен в `.gitignore`. Не снимайте его с игнорирования и не публикуйте секрет.

## 4. Выполнить один тестовый запрос

Установите Python 3.10 или новее. Из корневой папки проекта выполните:

```bash
python src/run_experiments.py --approach zero_shot --limit 1 --repeat 1
```

Команда отправит ровно один запрос: товар № 1 × Zero-shot × один повтор. Результат появится в локальном файле `results/llm_runs.jsonl`.

При успехе выполните:

```bash
python src/evaluate_results.py
```

Если вернулась ошибка 401/403, в первую очередь проверьте, что API-ключ и endpoint относятся к одному региону/workspace, а также что скопирован правильный API Host.

## 5. Запустить весь эксперимент

Один проход: 8 товаров × 4 метода = 32 API-вызова:

```bash
python src/run_experiments.py --repeat 1
python src/evaluate_results.py
```

Три повтора: 8 × 4 × 3 = 96 API-вызовов:

```bash
python src/run_experiments.py --repeat 3
python src/evaluate_results.py
```

Проверьте цены и тарифы в Model Studio до полного запуска. Тестовые и полные запросы могут тарифицироваться. Не запускайте 96 обращений, пока одиночная проверка не завершилась успешно.

## 6. Что сохраняется

- `results/llm_runs.jsonl` — фактические ответы модели, модель, хост API, временные отметки, задержка и результат извлечения скидки.
- `results/llm_evaluation.csv` — детальная экономическая проверка ответов.
- `results/llm_evaluation_summary.csv` — сводка по четырём подходам.
- `results/llm_evaluation.md` — Markdown-отчёт.

Журнал не должен содержать API-ключ. Исходные ручные ответы из `experiments/results.md` и новые ответы Qwen — разные источники данных; их нельзя смешивать в одну серию измерений.

## Официальные материалы

- [OpenAI-compatible Chat API](https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope)
- [Region and endpoints: Germany (Frankfurt)](https://www.alibabacloud.com/help/en/model-studio/germany-frankfurt-global)
- [Regions and service deployment scopes](https://www.alibabacloud.com/help/en/model-studio/regions/)
- [Obtain an API key](https://www.alibabacloud.com/help/en/model-studio/get-api-key)
- [Supported models](https://www.alibabacloud.com/help/en/model-studio/models)
