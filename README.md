# Курсовой проект: сравнение подходов prompting для рекомендаций по скидкам

**Тема:** сравнение Zero-shot, Few-shot, Chain-of-Thought (CoT) и Few-shot + CoT при формировании рекомендаций по скидкам для учебного набора низкооборачиваемых товаров.

## Цель
Разработать воспроизводимый протокол сравнения четырёх вариантов промптинга и оценивать ответы модели по формату, арифметической согласованности и соблюдению ограничения по закупочной стоимости.

## Структура репозитория
- `data/slow_moving.csv` — учебный набор из восьми товаров.
- `prompts/` — четыре первоначальных промпта и унифицированные версии `v2_*.txt`.
- `experiments/results.md` — исходный ручной пилот для товара № 1.
- `results/manual_pilot_analysis.md` — проверяемый финансовый разбор пилота.
- `results/planned_experiment_matrix.csv` — план 8 товаров × 4 подхода × 3 повтора; строки имеют статус `planned_not_run`.
- `src/` — расчёты, рендеринг промптов, запуск модели через API и оценка ответов.
- `tests/` — модульные тесты.
- `docs/` — методика эксперимента и словарь данных.

## Анализ без API
Нужен Python 3.10+; для основных расчётов используются только стандартные библиотеки.

Windows: запустите `run_checks.bat`.

Командная строка:
    python -m unittest discover -s tests -v
    python src/analyze_portfolio.py

Будут созданы `results/portfolio_analysis.csv` и `results/portfolio_analysis.md`. Это детерминированные расчёты по CSV, не ответы языковой модели.

## Запуск Qwen через Alibaba Cloud Model Studio

Для проекта настроен Qwen через OpenAI-compatible Chat Completions API. Рекомендуемая конфигурация для пользователя в Европе:
- Region: **Germany (Frankfurt)**.
- Service deployment scope: **EU**.
- Model: **`qwen-plus`**.
- Base URL: workspace-specific URL вида `https://<WorkspaceId>.eu-central-1.maas.aliyuncs.com/compatible-mode/v1`.

Подробная инструкция: [`docs/qwen_setup.md`](docs/qwen_setup.md).

Создайте локальный `.env` на основе `.env.example`. В нём заполните:
- `LLM_API_KEY` — API-ключ Model Studio, созданный в том же Frankfurt workspace.
- `LLM_BASE_URL` — адрес API Host вашего workspace с окончанием `/compatible-mode/v1`.
- `LLM_MODEL=qwen-plus`.

**Не используйте пароль от Qwen Chat и не публикуйте API-ключ.** Qwen Chat и Model Studio API Key — разные способы авторизации. Не загружайте локальный `.env` в GitHub.

### Проверка перед полным запуском

Сначала выполните один реальный запрос к Qwen:
    python src/run_experiments.py --approach zero_shot --limit 1 --repeat 1

Затем проверьте журнал:
    python src/evaluate_results.py

Если тест прошёл, один полный проход по 8 товарам и 4 подходам:
    python src/run_experiments.py --repeat 1
    python src/evaluate_results.py

Для трёх повторов на каждую комбинацию (96 обращений):
    python src/run_experiments.py --repeat 3
    python src/evaluate_results.py

Проверьте тариф Model Studio перед запуском: API-вызовы могут быть платными. Первый тестовый запрос нужен, чтобы проверить ключ, endpoint и доступность модели до запуска всей матрицы. Сырые ответы сохраняются в локальный JSONL-журнал; ключ не записывается в журнал.

## Что уже подтверждено
В первоначальном пилоте для товара «Электроника» зафиксированы четыре ответа: Zero-shot — диапазон 25–30% (для табличного расчёта выбрано 25%), Few-shot — 15%, CoT — 20%, Few-shot + CoT — 30%. Имя модели/провайдера и параметры исходного запуска не зафиксированы. Пилот относится только к одному товару и не доказывает превосходство одного подхода.

## Методика и ограничения
См. `docs/methodology.md` и `docs/data_dictionary.md`. Учебные данные не содержат полных операционных расходов или продаж после изменения цены. Поэтому валовая разница с закупочной стоимостью не называется чистой прибылью, а влияние скидки на спрос не считается доказанным. Нельзя заявлять «точность оптимальной скидки» без экспертной эталонной разметки.

## Автоматические проверки
GitHub Actions запускает модульные тесты и анализ портфеля при push и pull request: `.github/workflows/tests.yml`.
