# Smart Selector: Документация (RU)

Основная документация на английском находится в `README.md`.

## Обзор
Smart Selector — библиотека на Python для построения устойчивых XPath/CSS селекторов по:
- HTML-странице,
- абсолютному XPath целевого элемента.

Поддерживает два режима:
1. **Single element mode**: подбор селекторов для одного поля.
2. **Collection mode**: построение селектора списка/каталога по двум соседним XPath.

## Быстрый старт

### Установка
```bash
pip install lxml cssselect pytest
```
или
```bash
pipenv install --dev
```

### Одиночный элемент
```python
from pathlib import Path
from smart_selector import build_selectors

html = Path("html_examples/ozon.html").read_text(encoding="utf-8")
abs_xpath = "/html/body/.../span"

result = build_selectors(html, abs_xpath)

print(result.best_xpath)
print(result.best_css)
print(result.variants[:5])
print(result.xpath_variants[:3])
print(result.css_variants[:3])
print(result.variants_with_text[:3])
```

### Каталог/список по двум соседям
```python
from smart_selector import build_collection_selector

collection = build_collection_selector(
    html,
    first_absolute_xpath="/html/body/.../article[1]",
    second_absolute_xpath="/html/body/.../article[2]",
)

print(collection.collection_xpath)
print(collection.collection_css)
print(collection.item_xpath_template)  # ...[{i}]...
print(collection.item_css_template)    # ...:nth-of-type({i})...
print(collection.estimated_count)
```

## API

### Для одиночного элемента
- `build_selectors(html, absolute_xpath, config=None) -> BuildResult`
- `build_best_selector(html, absolute_xpath, config=None) -> SelectorVariant | None`
- `build_xpath_variants(html, absolute_xpath, config=None) -> list[SelectorVariant]`
- `build_css_variants(html, absolute_xpath, config=None) -> list[SelectorVariant]`
- `build_text_variants(html, absolute_xpath, config=None) -> list[SelectorVariant]`
- `analyze_selector(html, absolute_xpath, config=None) -> dict`

### Для коллекций
- `build_collection_selector(html, first_absolute_xpath, second_absolute_xpath, config=None) -> CollectionSelectorResult`
- `analyze_collection_selector(...) -> dict`

## Что возвращается

### BuildResult
- `target_found`
- `best_xpath`, `best_css`
- `variants` (общий рейтинг)
- `xpath_variants` (только XPath)
- `css_variants` (только CSS)
- `variants_with_text` (текстовые XPath)
- `debug_report`

### CollectionSelectorResult
- `ok`, `reason`
- `collection_xpath`, `collection_css`
- `item_xpath_template`, `item_css_template`
- `sample_item_xpath`, `sample_item_css`
- `estimated_count`

## Логика работы

### Одиночный элемент
1. Парсинг HTML (`lxml`).
2. Резолв target по absolute XPath (с tolerant fallback).
3. Генерация кандидатов XPath/CSS разными стратегиями.
4. Валидация каждого кандидата (match count + попадание в target).
5. Скоринг и сортировка.
6. Формирование отдельных срезов выдачи.

### Коллекция
1. Резолв двух соседних элементов.
2. Нахождение общей части путей и точки расхождения.
3. Построение общего селектора списка.
4. Построение шаблона элемента с индексом `{i}`.
5. Попытка сократить путь через якоря предков (`id`, `data-*`, class).

## Структура проекта

```text
smart_selector/
  api.py
  config.py
  models.py
  dom/
  generation/
  validation/
  scoring/
  engine/

tests/
  integration/
  unit/
```

## Практические советы
- Предпочитай `id`, `data-*`, `aria-*` вместо длинных абсолютных путей.
- Для каталога используй `build_collection_selector(...)`.
- Текстовые селекторы удобны для UI-лейблов, но чувствительны к изменениям текста.

## Ограничения
- Локальный HTML-снимок может отличаться от DOM в браузере после JS-гидрации.
- Сильно динамические обфусцированные классы ухудшают качество CSS.
