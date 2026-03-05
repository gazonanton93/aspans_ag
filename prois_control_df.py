"""
Производственный контроль 2025 г. — парсинг из Excel → DataFrame
Файл: 2 уровень_Производственный контроль_ПЛАН 2025г..xlsx

Структура листа (из скриншота):
  col 0  — № п/п
  col 1  — Подразделение (Отдел)
  col 2  — Количество ответственных
  col 3  — Должность
  col 4+ — Недели 1..52

Результирующий датафрейм:
  Отдел | Должность | Номер недели | Количество проверок
"""

import pandas as pd

EXCEL_FILE = r'2 уровень_Производственный контроль_ПЛАН 2025г..xlsx'

# ── 1. Читаем сырой лист ──────────────────────────────────────────────────────
raw = pd.read_excel(EXCEL_FILE, header=None)

# ── 2. Находим строку-заголовок с номерами недель (ищем «1» в колонках) ───────
# Заголовки недель — строка, где в col 4+ стоят числа 1,2,3...
header_row = None
for i, row in raw.iterrows():
    vals = row.iloc[4:].dropna().tolist()
    if len(vals) >= 10 and all(isinstance(v, (int, float)) for v in vals[:10]):
        nums = [int(v) for v in vals[:10]]
        if nums[:5] == list(range(1, 6)):   # 1,2,3,4,5 → это строка с неделями
            header_row = i
            break

if header_row is None:
    # Fallback: предполагаем, что недели начинаются с col 4 сразу как 1..52
    header_row = None
    print("⚠️  Строка-заголовок не найдена, используем col 4..55 как нед. 1–52")
    WEEK_COLS  = list(range(4, 56))
    WEEK_NAMES = list(range(1, 53))
else:
    print(f"✅ Строка заголовка недель: {header_row}")
    header = raw.iloc[header_row]
    WEEK_COLS  = [c for c in range(4, len(header)) if pd.notna(header[c])]
    WEEK_NAMES = [int(header[c]) for c in WEEK_COLS]

# ── 3. Строки с данными — непустой Отдел и числовые значения недель ──────────
data_rows = []
for i, row in raw.iterrows():
    dept = row.iloc[1]
    pos  = row.iloc[3]
    if pd.isna(dept) or pd.isna(pos):
        continue
    dept = str(dept).strip()
    pos  = str(pos).strip()
    if not dept or dept in ('Подразделения', 'nan'):
        continue
    # Проверяем, что есть хотя бы одно числовое значение в колонках недель
    week_vals = []
    for c in WEEK_COLS:
        v = row.iloc[c] if c < len(row) else None
        try:
            week_vals.append(float(v) if pd.notna(v) else 0.0)
        except (TypeError, ValueError):
            week_vals.append(0.0)
    if sum(week_vals) == 0:
        continue
    data_rows.append((dept, pos, week_vals))

print(f"✅ Найдено отделов: {len(data_rows)}")

# ── 4. Разворачиваем в длинный формат ────────────────────────────────────────
records = []
for dept, pos, week_vals in data_rows:
    for week_num, cnt in zip(WEEK_NAMES, week_vals):
        records.append({
            'Отдел':               dept,
            'Должность':           pos,
            'Номер недели':        int(week_num),
            'Количество проверок': cnt,
        })

df = pd.DataFrame(records)
df['Номер недели'] = df['Номер недели'].astype(int)

# ── 5. Контроль ───────────────────────────────────────────────────────────────
print(f"\nСтрок в df      : {len(df)}")
print(f"Итого проверок  : {df['Количество проверок'].sum():.0f}")
print(f"\nСумма по отделам:")
print(
    df.groupby('Отдел')['Количество проверок']
      .sum()
      .sort_values(ascending=False)
      .to_string()
)

df
