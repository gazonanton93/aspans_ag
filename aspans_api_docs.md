# Aspans API — Документация по CRUD

> Выведена из реального кода `inkay_gis_map.html`.  
> Базовый префикс всех API-запросов: `/ru/api/v1`

---

## Содержание

1. [Аутентификация](#1-аутентификация)
2. [CSRF-токен](#2-csrf-токен)
3. [Базовые хелперы fetch](#3-базовые-хелперы-fetch)
4. [READ — чтение списков](#4-read--чтение-списков)
5. [CREATE — создание записи](#5-create--создание-записи)
6. [UPDATE — обновление записи](#6-update--обновление-записи)
7. [DELETE — удаление записи](#7-delete--удаление-записи)
8. [Открытие карточки записи (view)](#8-открытие-карточки-записи-view)
9. [Именование таблиц и моделей](#9-именование-таблиц-и-моделей)
10. [Структура FormData-полей](#10-структура-formdata-полей)
11. [Разбор ответа](#11-разбор-ответа)
12. [Готовые JS-шаблоны](#12-готовые-js-шаблоны)

---

## 1. Аутентификация

Все запросы используют **HTTP Basic Auth** через заголовок `Authorization`.

### Алгоритм построения заголовка

```js
function getHeaders() {
  const personCode = localStorage.getItem('personCode') || 'anonymous';
  const raw = personCode + ':19451945';
  // URL-encode → декодировать символы обратно → btoa
  const decoded = encodeURIComponent(raw).replace(
    /%([0-9A-F]{2})/g,
    (_, hex) => String.fromCharCode('0x' + hex)
  );
  return {
    'X-Requested-With': 'XMLHttpRequest',
    'Authorization': 'Basic ' + btoa(decoded)
  };
}
```

**Ключевые детали:**
- `personCode` берётся из `localStorage.getItem('personCode')` — там хранится логин текущего пользователя Aspans
- Пароль фиксированный: `19451945`
- Формат credentials: `personCode:19451945`
- Перед `btoa` строка проходит через URL-encode → char-decode, чтобы корректно обработать кириллицу и спецсимволы
- Заголовок `X-Requested-With: XMLHttpRequest` обязателен — платформа проверяет его для AJAX-запросов

---

## 2. CSRF-токен

Все **POST**-запросы (create / update / delete) требуют CSRF-токен в теле `FormData` под ключом `_csrf-frontend`.

### Функция получения токена

```js
function getCsrf() {
  // 1. Мета-тег (стандартный Yii2)
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta?.content) return meta.content;

  // 2. Yii JS API
  if (window.yii?.getCsrfToken) {
    const t = window.yii.getCsrfToken();
    if (t) return t;
  }

  // 3. Скрытый input в форме
  const input = document.querySelector('input[name="_csrf-frontend"]');
  if (input?.value) return input.value;

  // 4. Из cookie _csrf-frontend
  try {
    const match = document.cookie.match(/_csrf-frontend=([^;]+)/);
    if (match) {
      const decoded = decodeURIComponent(match[1]);
      const tokenMatch = decoded.match(/"([a-zA-Z0-9_\-]{30,})"/);
      if (tokenMatch) return tokenMatch[1];
    }
  } catch {}

  // 5. Из родительского фрейма (если страница встроена через iframe)
  try {
    if (window.parent !== window) {
      const parentMeta = window.parent.document.querySelector('meta[name="csrf-token"]');
      if (parentMeta?.content) return parentMeta.content;
    }
  } catch {}

  return '';
}
```

> **Важно:** При работе внутри Aspans (iframe-встройка) токен часто живёт в родительском документе — вариант 5 критичен.

---

## 3. Базовые хелперы fetch

### GET

```js
async function apiGet(url) {
  const response = await fetch(url, { headers: getHeaders() });
  if (!response.ok) throw new Error('HTTP ' + response.status);
  const data = await response.json();
  // API возвращает либо массив, либо объект { items: [...] }
  return Array.isArray(data) ? data : (data.items || []);
}
```

### POST

```js
async function apiPost(url, formData) {
  const response = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: formData
  });
  // 302 редирект после успешного create/update — это нормально
  if (!response.ok && response.status !== 302) {
    const text = await response.text().catch(() => '');
    throw new Error('HTTP ' + response.status + ': ' + text.slice(0, 120));
  }
  return response;
}
```

> `Content-Type` **не указывается** — браузер выставляет его автоматически с boundary при передаче `FormData`.

---

## 4. READ — чтение списков

### Endpoint

```
GET /ru/api/v1/{tbl}?_format=json&query={encoded_json}
```

### Параметр `query`

JSON-объект, сериализованный и URL-encoded:

| Поле | Тип | Описание |
|------|-----|----------|
| `limit` | number | Максимальное количество строк. `100000` для полной выгрузки справочников |
| `columns` | string | Перечень полей через запятую. Если не указан — возвращаются все поля |
| `filter` | object | (опционально) Условия фильтрации |

### Примеры

**Загрузить все записи справочника (все поля):**
```js
const query = JSON.stringify({ limit: 100000 });
const data = await apiGet(`/ru/api/v1/list_skv?_format=json&query=${encodeURIComponent(query)}`);
```

**Загрузить только нужные поля:**
```js
const query = JSON.stringify({ limit: 100000, columns: 'id,code,sname' });
const data = await apiGet(`/ru/api/v1/list_skv?_format=json&query=${encodeURIComponent(query)}`);
```

**Загрузить слои с конкретными полями:**
```js
const query = JSON.stringify({
  limit: 500,
  columns: 'id,code,sname,i00_color,i00_sort_order,i00_is_visible,i00_is_active,i00_is_locked'
});
const layers = await apiGet(`/ru/api/v1/list_map_layers?_format=json&query=${encodeURIComponent(query)}`);
```

### Структура ответа

```json
// Вариант 1: прямой массив
[
  { "id": 1, "code": "well_001", "sname": "Скважина 001" },
  ...
]

// Вариант 2: объект с items
{
  "items": [
    { "id": 1, "code": "well_001", "sname": "Скважина 001" },
    ...
  ]
}
```

Хелпер `apiGet` нормализует оба варианта → всегда возвращает массив.

### Связанные данные (`_data`-суффикс)

Если запись содержит FK-поле (например `ilc_map_layers`), API может вернуть рядом объект с суффиксом `_data`:

```json
{
  "ilc_map_layers": "wells",
  "ilc_map_layers_data": {
    "id": 3,
    "code": "wells",
    "sname": "Скважины"
  }
}
```

Читать так:
```js
const layerCode = record.ilc_map_layers_data?.code || record.ilc_map_layers || '';
```

---

## 5. CREATE — создание записи

### Endpoint

```
POST /ru/t/create?tbl={tbl}&version=add&modal=true&ajax=true&is_ajax=true
```

### Обязательные query-параметры

| Параметр | Значение | Описание |
|----------|----------|----------|
| `tbl` | `doc_map_objects` | Имя таблицы (snake_case) |
| `version` | `add` | Режим операции |
| `modal` | `true` | Признак модального режима |
| `ajax` | `true` | Признак AJAX |
| `is_ajax` | `true` | Дублирующий признак AJAX |

### Тело запроса (FormData)

Поля передаются с префиксом **модели** (PascalCase имя таблицы):

```js
const fd = new FormData();
fd.append('_csrf-frontend', getCsrf());

// Поля модели: ModelName[field_name]
fd.append('DocMapObjects[ilc_map_layers]', 'wells');
fd.append('DocMapObjects[i00_label]', 'Скважина №142');
fd.append('DocMapObjects[i00_geom_type]', 'marker');
fd.append('DocMapObjects[i00_geom_json]', JSON.stringify({ type: 'Point', coordinates: [65.36, 44.07] }));
fd.append('DocMapObjects[i00_color]', '#ef4444');
fd.append('DocMapObjects[i00_fill_color]', '#ef4444');
fd.append('DocMapObjects[i00_opacity]', '0.35');
fd.append('DocMapObjects[i00_weight]', '2');
fd.append('DocMapObjects[i00_dash_pattern]', 'solid');
fd.append('DocMapObjects[i00_icon_type]', 'well');
fd.append('DocMapObjects[i00_is_active]', '1');

const response = await apiPost(
  '/ru/t/create?tbl=doc_map_objects&version=add&modal=true&ajax=true&is_ajax=true',
  fd
);
```

### Получение ID созданной записи

```js
try {
  const result = await response.clone().json();
  if (result?.success?.id) {
    record.id = Number(result.success.id);
  } else if (result?.id) {
    record.id = Number(result.id);
  }
} catch {
  // response может не содержать JSON при редиректе
}
```

---

## 6. UPDATE — обновление записи

### Endpoint

```
POST /ru/t/update?id={id}&tbl={tbl}&version=edit&modal=true&ajax=true&is_ajax=true
```

### Отличие от CREATE

- Параметр `version=edit` вместо `add`
- Параметр `id={id}` — числовой ID записи в БД
- Тело FormData идентично CREATE

```js
const fd = new FormData();
fd.append('_csrf-frontend', getCsrf());
fd.append('DocMapObjects[i00_label]', 'Обновлённое название');
fd.append('DocMapObjects[i00_color]', '#22c55e');
// ... остальные поля

const url = `/ru/t/update?id=${record.id}&tbl=doc_map_objects&version=edit&modal=true&ajax=true&is_ajax=true`;
await apiPost(url, fd);
```

### Паттерн create-or-update

```js
const url = record.id
  ? `/ru/t/update?id=${record.id}&tbl=doc_map_objects&version=edit&modal=true&ajax=true&is_ajax=true`
  : `/ru/t/create?tbl=doc_map_objects&version=add&modal=true&ajax=true&is_ajax=true`;

const response = await apiPost(url, fd);

// Если создание — сохраняем полученный id
if (!record.id) {
  try {
    const result = await response.clone().json();
    if (result?.success?.id) record.id = Number(result.success.id);
    else if (result?.id) record.id = Number(result.id);
  } catch {}
}
```

---

## 7. DELETE — удаление записи

### Endpoint

```
POST /ru/t/delete?id={id}&tbl={tbl}&ajax=true&is_ajax=true
```

### Тело запроса

```js
const fd = new FormData();
fd.append('id', record.id);
fd.append('tblName', 'doc_map_objects');
fd.append('_csrf-frontend', getCsrf());

await apiPost(
  `/ru/t/delete?id=${record.id}&tbl=doc_map_objects&ajax=true&is_ajax=true`,
  fd
);
```

> **Отличие от create/update:** параметры `modal` и `version` не передаются. Поле `tblName` дублируется в теле.

---

## 8. Открытие карточки записи (view)

Открывает страницу просмотра/редактирования конкретной записи в новой вкладке браузера. Используется для «Подробнее» → переход в карточку связанного справочника.

### URL

```
/ru/t/view?id={id}&tbl={tbl}&version=info_from_map
```

| Параметр | Описание |
|----------|----------|
| `id` | Числовой ID записи |
| `tbl` | Имя таблицы (snake_case) |
| `version` | Контекст открытия. `info_from_map` — специальный режим, сигнализирует платформе что переход из карты |

### Пример

```js
function openDetail(id, tbl) {
  if (!id) return;
  window.open(
    window.location.origin + `/ru/t/view?id=${id}&tbl=${tbl}&version=info_from_map`,
    '_blank'
  );
}

// Конкретные таблицы:
openDetail(skvId,  'list_skv');          // Скважина
openDetail(blkId,  'list_tblock');       // Технологический блок
openDetail(lapId,  'list_lap');          // ЛЭП
openDetail(pipeId, 'list_trunk_line');   // Трубопровод
openDetail(layId,  'list_map_layers');   // Слой карты
openDetail(objId,  'doc_map_objects');   // Объект карты
```

---

## 9. Именование таблиц и моделей

Aspans использует два варианта имён для одной сущности:

| Таблица (snake_case) | Модель (PascalCase) | Описание |
|----------------------|---------------------|----------|
| `list_map_layers` | `ListMapLayers` | Слои карты |
| `doc_map_objects` | `DocMapObjects` | Объекты карты |
| `list_skv` | `ListSkv` | Скважины |
| `list_tblock` | `ListTblock` | Технологические блоки |
| `list_lap` | `ListLap` | ЛЭП |
| `list_trunk_line` | `ListTrunkLine` | Трубопроводы |

**Правило преобразования:**  
`snake_case` → убрать подчёркивания → PascalCase каждое слово.  
Используется в:
- `tbl=` query-параметрах → **snake_case**
- Ключах FormData `ModelName[field]` → **PascalCase**

---

## 10. Структура FormData-полей

### Соглашения по именованию полей

| Префикс | Тип | Пример | Описание |
|---------|-----|--------|----------|
| `i00_` | строка/число | `i00_label` | Обычные атрибуты записи |
| `i0d_` | дата | `i0d_date_start` | Дата-поля |
| `ilc_` | FK | `ilc_map_layers` | Ссылка на другую таблицу (stores `code`) |
| `s00_` | системное | `s00_uuid` | UUID записи |

### Поля `doc_map_objects`

```js
fd.append('DocMapObjects[ilc_map_layers]',  layerCode);       // код слоя (FK)
fd.append('DocMapObjects[i00_geom_type]',   'marker');        // marker|polyline|polygon|circle|rectangle
fd.append('DocMapObjects[i00_label]',       'Название');
fd.append('DocMapObjects[i00_object_code]', 'WELL-142');
fd.append('DocMapObjects[i00_description]', 'Описание');
fd.append('DocMapObjects[i00_geom_json]',   JSON.stringify(geomObject)); // GeoJSON-объект
fd.append('DocMapObjects[i00_color]',       '#ef4444');       // hex цвет обводки
fd.append('DocMapObjects[i00_fill_color]',  '#ef4444');       // hex цвет заливки
fd.append('DocMapObjects[i00_opacity]',     '0.35');          // 0.0–1.0
fd.append('DocMapObjects[i00_weight]',      '2');             // толщина линии px
fd.append('DocMapObjects[i00_dash_pattern]','solid');         // solid|8,4|2,4|12,4,2,4
fd.append('DocMapObjects[i00_icon_type]',   'well');          // well|pump|valve|building|sensor|pin
fd.append('DocMapObjects[i00_is_active]',   '1');
// Опционально — FK-ссылка на связанный справочник:
fd.append('DocMapObjects[ilc_skv]',         skvCode);        // если слой = wells
fd.append('DocMapObjects[ilc_tblock]',      tblockCode);     // если слой = blocks
fd.append('DocMapObjects[ilc_lap]',         lapCode);        // если слой = lap
fd.append('DocMapObjects[ilc_trunk_line]',  trunkCode);      // если слой = pipe
```

### Поля `list_map_layers`

```js
fd.append('ListMapLayers[code]',            'wells_2a');
fd.append('ListMapLayers[sname]',           'Скважины блока 2А');
fd.append('ListMapLayers[i00_color]',       '#ef4444');
fd.append('ListMapLayers[i00_sort_order]',  '1');
fd.append('ListMapLayers[i00_description]', 'Описание слоя');
fd.append('ListMapLayers[i00_is_active]',   '1');
fd.append('ListMapLayers[i00_is_visible]',  '1');
```

### Формат `i00_geom_json`

Передаётся как **JSON-строка** (`JSON.stringify(...)`):

```js
// Точка (marker)
{ "type": "Point", "coordinates": [lng, lat] }

// Линия (polyline)
{ "type": "LineString", "coordinates": [[lng1, lat1], [lng2, lat2], ...] }

// Полигон / прямоугольник
{ "type": "Polygon", "coordinates": [[[lng1,lat1],[lng2,lat2],...,[lng1,lat1]]] }

// Круг (нестандартное расширение GeoJSON)
{ "type": "Circle", "coordinates": [lng, lat], "radius": 500 }
```

> **Порядок координат:** `[longitude, latitude]` — стандарт GeoJSON.

---

## 11. Разбор ответа

### После CREATE

```js
const response = await apiPost(createUrl, fd);
try {
  const result = await response.clone().json();
  // Оба варианта встречаются в зависимости от версии Aspans:
  if (result?.success?.id) return Number(result.success.id);
  if (result?.id)          return Number(result.id);
} catch {
  // Редирект 302 — запись создана, но id не возвращается
}
```

### После UPDATE / DELETE

Обычно возвращает `{}` или редирект `302`. Проверять ошибки достаточно по статусу HTTP:

```js
// В apiPost уже бросает Error при !ok && status !== 302
```

### Коды статусов

| Статус | Значение |
|--------|----------|
| `200` | Успех, тело содержит JSON |
| `302` | Редирект после create/update — операция успешна |
| `400` | Ошибка валидации |
| `401` | Неверная аутентификация |
| `403` | Доступ запрещён (CSRF или права) |
| `404` | Таблица или запись не найдена |
| `500` | Ошибка сервера |

---

## 12. Готовые JS-шаблоны

### Полный CRUD-класс

```js
const API_BASE = '/ru/api/v1';

// --- Утилиты ---

function getHeaders() {
  const u = localStorage.getItem('personCode') || 'anonymous';
  const s = u + ':19451945';
  const decoded = encodeURIComponent(s).replace(/%([0-9A-F]{2})/g, (_, h) => String.fromCharCode('0x' + h));
  return {
    'X-Requested-With': 'XMLHttpRequest',
    'Authorization': 'Basic ' + btoa(decoded)
  };
}

function getCsrf() {
  const m = document.querySelector('meta[name="csrf-token"]');
  if (m?.content) return m.content;
  if (window.yii?.getCsrfToken) { const t = window.yii.getCsrfToken(); if (t) return t; }
  const i = document.querySelector('input[name="_csrf-frontend"]');
  if (i?.value) return i.value;
  try {
    const cm = document.cookie.match(/_csrf-frontend=([^;]+)/);
    if (cm) { const tm = decodeURIComponent(cm[1]).match(/"([a-zA-Z0-9_\-]{30,})"/); if (tm) return tm[1]; }
  } catch {}
  try {
    if (window.parent !== window) {
      const pm = window.parent.document.querySelector('meta[name="csrf-token"]');
      if (pm?.content) return pm.content;
    }
  } catch {}
  return '';
}

async function apiGet(url) {
  const r = await fetch(url, { headers: getHeaders() });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  const d = await r.json();
  return Array.isArray(d) ? d : (d.items || []);
}

async function apiPost(url, fd) {
  const r = await fetch(url, { method: 'POST', headers: getHeaders(), body: fd });
  if (!r.ok && r.status !== 302) {
    const t = await r.text().catch(() => '');
    throw new Error('HTTP ' + r.status + ': ' + t.slice(0, 120));
  }
  return r;
}

// --- CRUD ---

// READ: загрузить все записи таблицы
async function readAll(tbl, columns = null, limit = 100000) {
  const query = JSON.stringify({ limit, ...(columns ? { columns } : {}) });
  return apiGet(`${API_BASE}/${tbl}?_format=json&query=${encodeURIComponent(query)}`);
}

// CREATE: создать запись
// model — PascalCase имя модели, fields — объект с полями
async function create(tbl, model, fields) {
  const fd = new FormData();
  fd.append('_csrf-frontend', getCsrf());
  for (const [k, v] of Object.entries(fields)) {
    fd.append(`${model}[${k}]`, v ?? '');
  }
  const res = await apiPost(
    `/ru/t/create?tbl=${tbl}&version=add&modal=true&ajax=true&is_ajax=true`,
    fd
  );
  try {
    const d = await res.clone().json();
    return d?.success?.id ? Number(d.success.id) : (d?.id ? Number(d.id) : null);
  } catch { return null; }
}

// UPDATE: обновить запись
async function update(tbl, model, id, fields) {
  const fd = new FormData();
  fd.append('_csrf-frontend', getCsrf());
  for (const [k, v] of Object.entries(fields)) {
    fd.append(`${model}[${k}]`, v ?? '');
  }
  await apiPost(
    `/ru/t/update?id=${id}&tbl=${tbl}&version=edit&modal=true&ajax=true&is_ajax=true`,
    fd
  );
}

// DELETE: удалить запись
async function remove(tbl, id) {
  const fd = new FormData();
  fd.append('id', id);
  fd.append('tblName', tbl);
  fd.append('_csrf-frontend', getCsrf());
  await apiPost(`/ru/t/delete?id=${id}&tbl=${tbl}&ajax=true&is_ajax=true`, fd);
}

// VIEW: открыть карточку в новой вкладке
function openView(tbl, id) {
  window.open(`${window.location.origin}/ru/t/view?id=${id}&tbl=${tbl}&version=info_from_map`, '_blank');
}
```

### Пример использования

```js
// Загрузить скважины
const wells = await readAll('list_skv', 'id,code,sname');

// Создать объект карты
const newId = await create('doc_map_objects', 'DocMapObjects', {
  ilc_map_layers: 'wells',
  i00_label: 'Скважина №142',
  i00_geom_type: 'marker',
  i00_geom_json: JSON.stringify({ type: 'Point', coordinates: [65.36, 44.07] }),
  i00_color: '#ef4444',
  i00_fill_color: '#ef4444',
  i00_opacity: 0.35,
  i00_weight: 2,
  i00_dash_pattern: 'solid',
  i00_icon_type: 'well',
  i00_is_active: 1,
  ilc_skv: 'well_142_code'
});

// Обновить
await update('doc_map_objects', 'DocMapObjects', newId, {
  i00_label: 'Скважина №142 (уточнено)',
  i00_color: '#22c55e'
});

// Удалить
await remove('doc_map_objects', newId);

// Открыть карточку скважины
openView('list_skv', skvId);
```
