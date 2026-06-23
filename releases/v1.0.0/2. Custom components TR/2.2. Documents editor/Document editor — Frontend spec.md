# 2.2. Редактор документов — Техническое задание для Front-end разработчика

## Назначение

Реализовать WYSIWYG-редактор документов на базе готовой библиотеки rich-text редактора. Редактор предназначен для создания HTML-шаблонов документов с поддержкой:
- стандартного форматирования текста;
- вставки изображений (через File Module S3);
- таблиц;
- маркированных и нумерованных списков;
- кастомных inline-узлов: **переменных** (`{{ var__id }}`), **полей ввода** (`{{ input__id }}`), **переменных подписей** (`{{ signs__field__queue }}`), **формул** (`{{ formula__id }}`), **результатов по условию** (`{{ condition__id }}`);
- двухколоночного макета документа.

Хранение контента — в HTML-формате.

---

## Стек и выбор библиотеки

Рекомендуемый выбор — **Tiptap** (на основе ProseMirror). Поддерживает кастомные узлы, расширения, хранение в HTML.

Ключевые требования к библиотеке:
- Поддержка кастомных inline-узлов (для переменных, полей ввода, переменных подписей, формул и результатов по условию).
- Экспорт/импорт контента в HTML.
- Расширяемый toolbar.
- Поддержка таблиц (через расширение).
- Поддержка двухколоночного layout (через расширение или CSS).

---

## Архитектура компонента

```
DocumentEditor
├── Toolbar
│   ├── DocumentLayoutControl       ← одна/две колонки
│   ├── TextFormattingControls      ← B, I, S, U, цвет, размер
│   ├── AlignmentControls           ← выравнивание текста
│   ├── ImageControls               ← добавить/удалить изображение
│   ├── TableControls               ← добавить/убрать строку, столбец и т.д.
│   ├── ListControls                ← маркированный/нумерованный список
│   ├── VariableDropdown            ← вставка переменной
│   ├── InputFieldDropdown          ← использовать/создать поле ввода
│   ├── SignatureDropdown           ← список подписей / добавить новую подпись
│   ├── FormulaDropdown             ← список формул / добавить новую формулу
│   └── ConditionDropdown           ← список условий / добавить новый результат по условию
├── EditorCanvas                    ← рабочая область (экземпляр редактора)
│   ├── VariableNode                ← кастомный inline-узел (переменная)
│   ├── InputFieldNode              ← кастомный inline-узел (поле ввода)
│   ├── SignVariableNode            ← кастомный inline-узел (переменная подписи)
│   ├── FormulaNode                 ← кастомный inline-узел (формула)
│   └── ConditionNode               ← кастомный inline-узел (результат по условию)
├── InputFieldModal                 ← модальное окно создания поля ввода
├── SignatureModal                  ← модальное окно создания подписи
├── FormulaModal                    ← модальное окно создания формулы
└── ConditionModal                  ← модальное окно создания результата по условию
```

---

## Хранение контента

Контент редактора хранится и передаётся в виде HTML-строки. При инициализации редактора HTML подгружается в него. При сохранении — HTML извлекается из редактора.

### Переменные в HTML

Вычисляемая переменная:
```html
<span class="editor-variable" data-var-id="1">{{ var__1 }}</span>
```

Статичная переменная:
```html
<span class="editor-variable" data-var-id="1" data-var-table="employees">{{ var__employees__1 }}</span>
```

- `data-var-id` — числовой id переменной (для вычисляемых) или id записи в таблице (для статичных).
- `data-var-table` — название таблицы БД; присутствует только у статичных переменных.
- При загрузке в редактор — парсится в `VariableNode`.

### Поля ввода в HTML

```html
<span class="editor-input-field" data-input-id="42">{{ input__42 }}</span>
```

- Атрибут `data-input-id` — id поля ввода.
- При загрузке в редактор — парсится в `InputFieldNode`.

### Переменные подписей в HTML

Переменные подписей — inline-элементы, работающие точно так же, как и обычные переменные. Каждая вставляется по отдельности в любое место документа:

```html
<span class="editor-sign-var" data-sign-queue="1" data-sign-field="signer_fullname">{{ signs__signer_fullname__1 }}</span>
```

- `data-sign-queue` — локальный порядковый номер подписи в рамках шаблона.
- `data-sign-field` — одно из пяти полей: `signer_department`, `signer_position`, `signer_fullname`, `sign`, `sign_date`.
- Порядок подписей определяется массивом `signs` в `dependencies`, а не расположением в HTML.
- При загрузке в редактор — `<span class="editor-sign-var">` → `SignVariableNode`.

### Формулы в HTML

```html
<span class="editor-formula" data-formula-id="2">{{ formula__2 }}</span>
```

- Атрибут `data-formula-id` — id формулы.
- При загрузке в редактор — парсится в `FormulaNode`.

### Результаты по условию в HTML

```html
<span class="editor-condition" data-condition-id="5">{{ condition__5 }}</span>
```

- Атрибут `data-condition-id` — id результата по условию.
- При загрузке в редактор — парсится в `ConditionNode`.

---

## Кастомный узел: VariableNode

### Описание

Inline-узел, представляющий вставленную переменную. Не редактируется пользователем напрямую — только вставляется и удаляется.

### Атрибуты узла

```typescript
interface VariableNodeAttrs {
  varId: number;         // числовой id: для вычисляемых — id переменной, для статичных — id записи
  varTable?: string;     // только для статичных переменных: название таблицы БД (например "employees")
  displayName: string;   // человекочитаемое название, например "Имя пациента"
}
```

### Типы переменных

Переменные бывают двух типов:

- **Вычисляемые** — вычисляются бэкендом в момент формирования документа (текущая дата/время, данные заполняющего, пациента, клиники). Входят в группу «Основные». Синтаксис в HTML: `{{ var__<id> }}` (например `{{ var__1 }}`).
- **Статичные** — ссылаются на конкретную запись в таблице БД (например, конкретный сотрудник). Группируются по названию таблицы. Синтаксис в HTML: `{{ var__<table>__<record_id> }}` (например `{{ var__employees__1 }}`).

### Список переменных

Группы переменных загружаются с бэкенда при инициализации редактора. Вычисляемые переменные (группа «Основные») — полностью. Данные статичных групп — только список групп; конкретные записи подгружаются GET-запросом при раскрытии группы (accordion, lazy loading). Внутри каждой раскрытой статичной группы — инпут поиска по данным.

Структура на фронте:

```typescript
interface TemplateVariable {
  id: number;       // числовой id: для вычисляемых — id переменной, для статичных — id записи в таблице
  displayName: string;
  varTable?: string; // только для статичных: название таблицы БД
}

interface VariableGroup {
  group: string;
  isStatic: boolean; // true — данные загружаются lazy при раскрытии аккордиона
  items: TemplateVariable[]; // для статичных групп — пустой массив до раскрытия
}
```

Примерный состав вычисляемых переменных (id — присваиваются бэкендом):

| Группа | Переменные |
|--------|-----------|
| Дата и время | Текущая дата, Текущее время |
| Клиника | Название клиники, Логотип клиники |
| Филиал | Название филиала, Название главного филиала, Адрес филиала, Адрес главного филиала, Контакты филиала (соц. сети / эл. почта / телефоны), Контакты главного филиала (соц. сети / эл. почта / телефоны) |
| Заполняющий | Фамилия, Имя, Отчество, Специализация заполняющего врача, Категория заполняющего врача, Отдел заполняющего, Должность заполняющего |
| Пациент | Фамилия, Имя, Отчество, Дата рождения, Пол, Адрес, Группа крови (ABO), Резус-фактор (Rh), Рост, Вес, ИМТ, Аллергии, Хронические заболевания |

### Поведение в редакторе

- Атомарный узел: не разбивается на части, не редактируется по символам.
- Удаляется целиком через Delete/Backspace или клик + Delete.
- При сериализации вычисляемой переменной: `<span class="editor-variable" data-var-id="{varId}">{{ var__{varId} }}</span>`.
- При сериализации статичной переменной: `<span class="editor-variable" data-var-id="{varId}" data-var-table="{varTable}">{{ var__{varTable}__{varId} }}</span>`.
- При парсинге HTML обратно: `<span class="editor-variable">` → `VariableNode` (наличие `data-var-table` определяет тип).

---

## Кастомный узел: InputFieldNode

### Описание

Inline-узел, представляющий вставленное поле ввода. Ссылается на конкретный `InputField` по `id`.

### Атрибуты узла

```typescript
interface InputFieldNodeAttrs {
  inputId: number;      // FK на InputField.id
  displayName: string;  // InputField.name — для отображения в редакторе
  fieldType: string;    // InputField.type — для отображения иконки
}
```

### Поведение в редакторе

- Атомарный узел, аналогично VariableNode.
- Удаление чипа из документа не удаляет сам InputField из системы — только убирает ссылку из шаблона.
- При сериализации: `<span class="editor-input-field" data-input-id="{id}">{{ input__{id} }}</span>`.
- При парсинге HTML обратно: `<span class="editor-input-field">` → `InputFieldNode`.

---

## Кастомный узел: SignVariableNode

### Описание

Inline-узел, представляющий одну из пяти переменных конкретной подписи. По механике идентичен `VariableNode` — атомарный, вставляется и удаляется как чип. Отличается классом в HTML и набором атрибутов.

### Атрибуты узла

```typescript
interface SignVariableNodeAttrs {
  signQueue: number;    // локальный порядковый номер подписи в рамках шаблона
  signField: 'signer_department' | 'signer_position' | 'signer_fullname' | 'sign' | 'sign_date';
  displayName: string;  // человекочитаемое название, например "ФИО подписанта #1"
}
```

### Отображаемые названия полей

| `signField` | `displayName` (шаблон) |
|-------------|------------------------|
| `signer_department` | `Отдел подписанта #<queue>` |
| `signer_position` | `Должность подписанта #<queue>` |
| `signer_fullname` | `ФИО подписанта #<queue>` |
| `sign` | `Подпись #<queue>` |
| `sign_date` | `Дата подписания #<queue>` |

### Поведение в редакторе

- Атомарный inline-узел: аналогично `VariableNode`.
- Удаляется целиком через Delete/Backspace или клик + Delete.
- Одну и ту же переменную можно вставить в несколько мест документа.
- Удаление чипа из документа не удаляет саму подпись из массива `signs`.
- При сериализации: `<span class="editor-sign-var" data-sign-queue="{queue}" data-sign-field="{field}">{{ signs__{field}__{queue} }}</span>`.
- При парсинге HTML: `<span class="editor-sign-var">` → `SignVariableNode`.

### Хранение подписей в состоянии редактора

Список подписей, добавленных в шаблон, хранится в локальном состоянии компонента (не в HTML редактора):

```typescript
interface Sign {
  queue: number;         // локальный порядковый номер (в рамках данного шаблона, начинается с 1)
  department_id: number; // FK (Structure Module)
  position_id: number;   // FK (Structure Module)
  employee_id: number | null; // FK (HR Module), nullable
}

const [signs, setSigns] = useState<Sign[]>([]);
```

При добавлении новой подписи через модальное окно:
1. Присвоить `queue = signs.length + 1`.
2. Добавить объект в массив `signs`.
3. Дропдаун автоматически обновляется и показывает новую подпись с её пятью переменными для вставки.

---

## Кастомный узел: FormulaNode

### Описание

Inline-узел, представляющий вставленный результат формулы. Ссылается на конкретную формулу по `id`.

### Атрибуты узла

```typescript
interface FormulaNodeAttrs {
  formulaId: number;    // FK на Formula.id
  displayName: string;  // Formula.name — для отображения в редакторе
}
```

### Поведение в редакторе

- Атомарный узел, аналогично VariableNode.
- Удаление чипа из документа не удаляет саму формулу из системы.
- При сериализации: `<span class="editor-formula" data-formula-id="{id}">{{ formula__{id} }}</span>`.
- При парсинге HTML обратно: `<span class="editor-formula">` → `FormulaNode`.

### Схема формулы

```typescript
interface Formula {
  id: number;
  name: string;
  formula: string; // строка с арифметическим выражением
  dependencies: {
    variables: number[]; // id используемых переменных
    inputs: number[];    // id используемых полей ввода
    formulas: number[];  // id используемых формул
  };
}
```

Правила валидации формулы:
- В выражении можно использовать переменные (`{{ var__id }}`), поля ввода (`{{ input__id }}`), другие формулы (`{{ formula__id }}`).
- Запрещены взаимозависимые формулы (A зависит от B, B зависит от A).
- Формула не может ссылаться на ещё не вычисленную формулу (проверяется порядок зависимостей).

```typescript
const [formulas, setFormulas] = useState<Formula[]>([]);
```

---

## Кастомный узел: ConditionNode

### Описание

Inline-узел, представляющий вставленный результат по условию. Ссылается на конкретный результат по условию по `id`.

### Атрибуты узла

```typescript
interface ConditionNodeAttrs {
  conditionId: number;  // FK на Condition.id
  displayName: string;  // Condition.name — для отображения в редакторе
}
```

### Поведение в редакторе

- Атомарный узел, аналогично VariableNode.
- Удаление чипа из документа не удаляет сам результат по условию из системы.
- При сериализации: `<span class="editor-condition" data-condition-id="{id}">{{ condition__{id} }}</span>`.
- При парсинге HTML обратно: `<span class="editor-condition">` → `ConditionNode`.

### Схема результата по условию

```typescript
interface ConditionRule {
  field: string;            // операнда для проверки (переменная, поле ввода или формула)
  operator: string;         // оператор сравнения (==, !=, >, <, >=, <=)
  value: string | number;   // операнда для сравнения
}

interface ConditionRuleGroup {
  logical?: 'AND' | 'OR';
  rules: Array<ConditionRule | ConditionRuleGroup>; // вложенность для OR-групп
}

interface ConditionBranch {
  type: 'if' | 'else_if' | 'else';
  condition?: ConditionRuleGroup; // отсутствует только для type === 'else'
  then: string; // результат (переменная, поле ввода или формула)
}

interface Condition {
  id: number;
  name: string;
  conditions: ConditionBranch[];
  dependencies: {
    variables: number[];
    inputs: number[];
    formulas: number[];
  };
}
```

Пример структуры, которую подготавливает фронтенд перед отправкой:

```json
{
  "name": "Проверка возраста",
  "conditions": [
    {
      "type": "if",
      "condition": {
        "logical": "OR",
        "rules": [
          {
            "logical": "AND",
            "rules": [
              { "field": "{{ var__2 }}", "operator": ">=", "value": "{{ var__6 }}" },
              { "field": "{{ input__1 }}", "operator": "!=", "value": "some value" }
            ]
          },
          {
            "logical": "AND",
            "rules": [
              { "field": "{{ formula__2 }}", "operator": ">=", "value": 20 },
              { "field": "{{ var__1 }}", "operator": "==", "value": "{{ var__24 }}" }
            ]
          }
        ]
      },
      "then": "{{ var__4 }}"
    },
    {
      "type": "else_if",
      "condition": {
        "logical": "AND",
        "rules": [
          { "field": "{{ input__12 }}", "operator": "<=", "value": 2 },
          { "field": "{{ formula__10 }}", "operator": "!=", "value": "some value" }
        ]
      },
      "then": "{{ formula__5 }}"
    },
    {
      "type": "else",
      "then": "{{ var__40 }}"
    }
  ]
}
```

Свойства `condition.rules` могут быть вложены сами в себя, если используется логический оператор `"OR"`.

```typescript
const [conditions, setConditions] = useState<Condition[]>([]);
```

---

## Схема поля ввода (InputField)

```typescript
interface InputField {
  id: number;
  name: string;
  value: string | number | string[] | null;
  type: 'input' | 'number_input' | 'file_input' | 'select' | 'multi_select';
  required: boolean;        // default: false
  default_value: string | number | null;
  data: InputFieldData | null;
}
```

### Типизация `data` по типу поля

```typescript
// type === 'number_input'
type NumberInputData = [number, number]; // [min, max]

// type === 'file_input'
type FileInputData = string; // MIME-тип, например "image/png,image/jpeg"

// type === 'select' | 'multi_select' — статический список (без гидратации)
type SelectStaticData = Array<{
  key: string;    // отображаемое название
  value: unknown; // значение
}>;

// type === 'select' | 'multi_select' — с гидратацией из бекенда
type SelectHydratedData = {
  src: 'sql' | 'json';
  path: string;           // название таблицы или json-файла
  query_keys: string[];   // колонки для фильтрации (sql)
  query_values: string[]; // значения для фильтрации (sql)
  key: string;            // поле/колонка для display label
  value: string;          // поле/колонка для value
};

type InputFieldData = NumberInputData | FileInputData | SelectStaticData | SelectHydratedData | null;
```

---

## Схема итогового шаблона (DocumentTemplate)

Объект, который фронт отправляет на бекенд при создании или обновлении шаблона:

```typescript
interface DocumentPage {
  page: number;   // порядковый номер страницы, начиная с 1
  content: string; // HTML-содержимое страницы
}

interface DocumentTemplate {
  name: string;
  description: string;
  pages: DocumentPage[]; // массив страниц с HTML-содержимым
  dependencies: {
    variables: number[];   // id переменных, использованных в шаблоне
    inputs: number[];      // id полей ввода, использованных в шаблоне
    signs: number[];       // порядковые номера (queue) подписей в очерёдности подписания
    formulas: number[];    // id формул, использованных в шаблоне
    conditions: number[];  // id результатов по условию, использованных в шаблоне
  };
}
```

Пример:

```json
{
  "name": "Справка об обследовании",
  "description": "Шаблон справки для амбулаторного приёма",
  "pages": [
    {
      "page": 1,
      "content": "<p>Пациент: <span class=\"editor-variable\" data-var-id=\"22\">{{ var__22 }}</span></p>"
    }
  ],
  "dependencies": {
    "variables": [22, 1],
    "inputs": [1, 42],
    "signs": [1, 2],
    "formulas": [3],
    "conditions": [1]
  }
}
```

### Извлечение dependencies из HTML и состояния

Функция принимает массив страниц и объединяет HTML всех страниц для поиска зависимостей:

```typescript
function extractDependencies(
  pages: DocumentPage[],
  signs: Sign[],
): DocumentTemplate['dependencies'] {
  const variables: number[] = [];
  const inputs: number[] = [];
  const formulas: number[] = [];
  const conditions: number[] = [];

  // Объединяем HTML всех страниц для поиска зависимостей
  const combinedHtml = pages.map(p => p.content).join('');

  // Переменные — из data-var-id
  const varMatches = combinedHtml.matchAll(/data-var-id="(\d+)"/g);
  for (const match of varMatches) {
    const id = Number(match[1]);
    if (!variables.includes(id)) variables.push(id);
  }

  // Поля ввода — из data-input-id
  const inputMatches = combinedHtml.matchAll(/data-input-id="(\d+)"/g);
  for (const match of inputMatches) {
    const id = Number(match[1]);
    if (!inputs.includes(id)) inputs.push(id);
  }

  // Формулы — из data-formula-id
  const formulaMatches = combinedHtml.matchAll(/data-formula-id="(\d+)"/g);
  for (const match of formulaMatches) {
    const id = Number(match[1]);
    if (!formulas.includes(id)) formulas.push(id);
  }

  // Результаты по условию — из data-condition-id
  const conditionMatches = combinedHtml.matchAll(/data-condition-id="(\d+)"/g);
  for (const match of conditionMatches) {
    const id = Number(match[1]);
    if (!conditions.includes(id)) conditions.push(id);
  }

  // Подписи — из локального состояния (не из HTML).
  // Порядок в массиве определяет очерёдность подписания.
  const signQueues = signs.map(s => s.queue);

  return { variables, inputs, signs: signQueues, formulas, conditions };
}
```

---

## API — поля ввода

### Получение списка полей ввода

```
GET /document-templates/input-fields
```

Возвращает `InputField[]`. Используется для дропдауна "Вставить существующее поле" и при загрузке шаблона.

### Создание нового поля ввода

```
POST /document-templates/input-fields
Body: Omit<InputField, 'id'>
Response: InputField (с присвоенным id)
```

После создания — чип сразу вставляется в документ.

### Обновление поля ввода

```
PATCH /document-templates/input-fields/:id
Body: Partial<Omit<InputField, 'id'>>
```

### Удаление поля ввода

```
DELETE /document-templates/input-fields/:id
```

Удаление недоступно, если поле используется хотя бы в одном шаблоне. Показать ошибку: "Поле используется в шаблонах: [список]".

---

## API — формулы

### Получение списка формул

```
GET /document-templates/formulas
```

Возвращает `Formula[]`. Используется для дропдауна "Формула ▾" и при загрузке шаблона.

### Создание новой формулы

```
POST /document-templates/formulas
Body: Omit<Formula, 'id'>
Response: Formula (с присвоенным id)
```

После создания — чип сразу вставляется в документ.

### Обновление формулы

```
PATCH /document-templates/formulas/:id
Body: Partial<Omit<Formula, 'id'>>
```

### Удаление формулы

```
DELETE /document-templates/formulas/:id
```

---

## API — результаты по условию

### Получение списка результатов по условию

```
GET /document-templates/conditions
```

Возвращает `Condition[]`. Используется для дропдауна "Условие ▾" и при загрузке шаблона.

### Создание нового результата по условию

```
POST /document-templates/conditions
Body: Omit<Condition, 'id'>
Response: Condition (с присвоенным id)
```

После создания — чип сразу вставляется в документ.

### Обновление результата по условию

```
PATCH /document-templates/conditions/:id
Body: Partial<Omit<Condition, 'id'>>
```

### Удаление результата по условию

```
DELETE /document-templates/conditions/:id
```

---

## API — загрузка изображений (File Module)

Вставка изображения через drag & drop или file input:

1. Файл загружается на `POST /files/upload` (multipart/form-data).
2. Ответ: `{ id: string, url: string }` — статический URL файла из S3.
3. В HTML редактора вставляется `<img src="{url}" data-file-id="{id}" />`.

Вставка по URL — URL вставляется напрямую в `src` без загрузки.

```typescript
async function uploadImageToEditor(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<{ id: string; url: string }>('/files/upload', formData);
  return response.url;
}
```

---

## Toolbar — детализация реализации

### Форматирование текста

```typescript
editor.chain().focus().toggleBold().run()
editor.chain().focus().toggleItalic().run()
editor.chain().focus().toggleStrike().run()
editor.chain().focus().toggleUnderline().run()
editor.chain().focus().setColor('#FF0000').run()
editor.chain().focus().setFontSize('16px').run()
editor.chain().focus().setTextAlign('left' | 'center' | 'right' | 'justify').run()
```

Кнопки форматирования отражают активное состояние:
```typescript
editor.isActive('bold')
editor.isActive('italic')
editor.isActive({ textAlign: 'center' })
```

### Таблицы

```typescript
editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
editor.chain().focus().addRowAfter().run()
editor.chain().focus().deleteRow().run()
editor.chain().focus().addColumnAfter().run()
editor.chain().focus().deleteColumn().run()
editor.chain().focus().mergeCells().run()
editor.chain().focus().setCellAttribute('backgroundColor', '#FFFF00').run()
```

Кнопки активны только при курсоре внутри таблицы:
```typescript
editor.can().addRowAfter()
editor.can().mergeCells()
```

### Изображения

Расширение Image поддерживает атрибуты `width` и `height`. Resize handles — через кастомное расширение или npm-пакет (например, `tiptap-extension-resize-image`).

### Список

```typescript
editor.chain().focus().toggleBulletList().run()
editor.chain().focus().toggleOrderedList().run()
```

### Две колонки

Кастомный узел `TwoColumnLayout` (block-node) с двумя дочерними контейнерами-колонками.

```html
<div class="editor-two-columns">
  <div class="editor-column">...контент колонки 1...</div>
  <div class="editor-column">...контент колонки 2...</div>
</div>
```

### Вставка переменной

```typescript
function insertVariable(editor: Editor, variable: TemplateVariable) {
  editor.chain().focus().insertContent({
    type: 'variableNode',
    attrs: {
      varId: variable.id,
      displayName: variable.displayName,
    },
  }).run();
}
```

### Вставка переменной подписи

```typescript
type SignField = 'signer_department' | 'signer_position' | 'signer_fullname' | 'sign' | 'sign_date';

const SIGN_FIELD_LABELS: Record<SignField, string> = {
  signer_department: 'Отдел подписанта',
  signer_position:   'Должность подписанта',
  signer_fullname:   'ФИО подписанта',
  sign:              'Подпись',
  sign_date:         'Дата подписания',
};

function insertSignVariable(editor: Editor, signQueue: number, field: SignField) {
  editor.chain().focus().insertContent({
    type: 'signVariableNode',
    attrs: {
      signQueue,
      signField: field,
      displayName: `${SIGN_FIELD_LABELS[field]} #${signQueue}`,
    },
  }).run();
}
```

### Вставка формулы

```typescript
function insertFormula(editor: Editor, formula: Formula) {
  editor.chain().focus().insertContent({
    type: 'formulaNode',
    attrs: {
      formulaId: formula.id,
      displayName: formula.name,
    },
  }).run();
}
```

### Вставка результата по условию

```typescript
function insertCondition(editor: Editor, condition: Condition) {
  editor.chain().focus().insertContent({
    type: 'conditionNode',
    attrs: {
      conditionId: condition.id,
      displayName: condition.name,
    },
  }).run();
}
```

---

## Загрузка шаблона в редактор

При открытии существующего шаблона:

1. Получить объект шаблона с сервера (включая `dependencies` и `pages`).
2. Инициализировать локальное состояние подписей из `dependencies.signs`.
3. Подгрузить списки полей ввода, формул и результатов по условию.
4. Передать HTML первой (или единственной) страницы в редактор — парсеры кастомных узлов разрезолвят данные из HTML-атрибутов. При необходимости поддержки навигации между страницами — хранить `pages` в локальном состоянии.

```typescript
async function loadTemplate(templateId: number): Promise<void> {
  const [template, inputFields, formulas, conditions] = await Promise.all([
    api.get(`/document-templates/${templateId}`),
    api.get('/document-templates/input-fields'),
    api.get('/document-templates/formulas'),
    api.get('/document-templates/conditions'),
  ]);

  setPages(template.pages);
  setSigns(template.dependencies.signs);
  setInputFieldMap(new Map(inputFields.map((f: InputField) => [f.id, f])));
  setFormulaMap(new Map(formulas.map((f: Formula) => [f.id, f])));
  setConditionMap(new Map(conditions.map((c: Condition) => [c.id, c])));
  // Загружаем контент текущей (активной) страницы
  editor.commands.setContent(template.pages[0]?.content ?? '');
}
```

---

## Сохранение шаблона

Перед сохранением фиксируем HTML текущей активной страницы в массиве `pages`, после чего собираем зависимости по всем страницам:

```typescript
async function saveTemplate(
  templateId: number,
  editor: Editor,
  pages: DocumentPage[],
  currentPageIndex: number,
  signs: Sign[],
  meta: { name: string; description: string }
): Promise<void> {
  const updatedPages = pages.map((p, i) =>
    i === currentPageIndex ? { ...p, content: editor.getHTML() } : p
  );
  const dependencies = extractDependencies(updatedPages, signs);

  const body: DocumentTemplate = {
    name: meta.name,
    description: meta.description,
    pages: updatedPages,
    dependencies,
  };

  await api.patch(`/document-templates/${templateId}`, body);
}

async function createTemplate(
  editor: Editor,
  pages: DocumentPage[],
  currentPageIndex: number,
  signs: Sign[],
  meta: { name: string; description: string }
): Promise<void> {
  const updatedPages = pages.map((p, i) =>
    i === currentPageIndex ? { ...p, content: editor.getHTML() } : p
  );
  const dependencies = extractDependencies(updatedPages, signs);

  const body: DocumentTemplate = {
    name: meta.name,
    description: meta.description,
    pages: updatedPages,
    dependencies,
  };

  await api.post('/document-templates', body);
}
```

---

## Кнопки действий и отправка в ЭДО

После того как в редакторе появляется любой контент, становятся доступны две кнопки:
- **"Сохранить как шаблон"** — сохраняет шаблон через `createTemplate` / `saveTemplate`.
- **"Отправить"** — открывает модальное окно отправки документа в ЭДО (без обязательного сохранения как шаблона).

### Схема запроса на отправку документа

```typescript
type AccessType = 'public' | 'restricted';

interface AccessRight {
  subject_id: number;         // id сотрудника или группы
  subject_type: 'employee' | 'group';
  can_view: true;             // всегда true для явно добавленных
  can_edit: boolean;
  can_delete: boolean;
}

interface SendDocumentPayload {
  recipients: number[];       // id сотрудников-получателей (право на просмотр)
  access_type: AccessType;
  access_rights?: AccessRight[]; // только при access_type === 'restricted'
  // HTML шаблона передаётся как массив страниц (аналогично DocumentTemplate)
  pages: DocumentPage[];
  dependencies: DocumentTemplate['dependencies'];
}
```

```
POST /documents/send
Body: SendDocumentPayload
```

- Сотрудники из `recipients` всегда получают право на просмотр независимо от `access_rights`.
- Подписывающие (из `dependencies.signs`) также автоматически получают право на просмотр — бэкенд добавляет их самостоятельно.
- При `access_type === 'public'` поле `access_rights` не передаётся.

---

## Режим read-only

```typescript
editor.setEditable(false); // или через опцию при инициализации: editable: false
```

В режиме read-only:
- Toolbar скрыт или весь disabled.
- Кастомные узлы не принимают события клика/фокуса.

---

## Подстановка значений при рендеринге итогового документа

При формировании готового документа по шаблону фронт (или бек) заменяет плейсхолдеры значениями:

```
{{ var__1 }}                      → "12.06.2026"
{{ var__22 }}                     → "Иванов"
{{ input__42 }}                   → значение, введённое пользователем
{{ signs__signer_fullname__1 }}   → "Петров П.П."
{{ signs__sign__1 }}              → [изображение подписи]
{{ signs__sign_date__1 }}         → "12.06.2026"
{{ formula__3 }}                  → вычисленное числовое значение
{{ condition__1 }}                → результат вычисления условия
```

Регулярные выражения для поиска при рендеринге:

```typescript
const VAR_COMPUTED_REGEX  = /\{\{\s*var__(\d+)\s*\}\}/g;                    // вычисляемые: match[1] — id
const VAR_STATIC_REGEX    = /\{\{\s*var__(\w+)__(\d+)\s*\}\}/g;             // статичные: match[1] — table, match[2] — record_id
const INPUT_REGEX         = /\{\{\s*input__(\d+)\s*\}\}/g;
const SIGN_REGEX          = /\{\{\s*signs__(\w+)__(\d+)\s*\}\}/g;           // match[1] — signField, match[2] — signQueue
const FORMULA_REGEX       = /\{\{\s*formula__(\d+)\s*\}\}/g;
const CONDITION_REGEX     = /\{\{\s*condition__(\d+)\s*\}\}/g;
```

---

## Edge cases и обработка ошибок

| Ситуация | Поведение |
|----------|-----------|
| Ошибка загрузки изображения | Toast с ошибкой, изображение не вставляется |
| Создание поля ввода — пустое название | Валидация в модальном окне, сабмит заблокирован |
| Вставка `select`/`multi_select` без значений в `data` | Предупреждение в модальном окне |
| Шаблон содержит `data-input-id`, которого нет в базе | Чип `[Удалённое поле #id]` красным цветом |
| Шаблон содержит `data-var-id`, которого нет в списке | Чип `[Неизвестная переменная #id]` красным цветом |
| Попытка удалить поле ввода, используемое в шаблонах | Ошибка от API, уведомление пользователю |
| Загрузка файла > допустимого размера | Валидация на фронте до запроса, сообщение об ошибке |
| Создание подписи — не выбран отдел или должность | Валидация в модальном окне, сабмит заблокирован |
| Шаблон содержит `data-sign-queue`, которого нет в `signs` | Чип `[Удалённая подпись #queue]` красным цветом |
| Формула ссылается на ещё не вычисленную формулу | Ошибка валидации при создании, сабмит заблокирован |
| Взаимная зависимость формул (A→B→A) | Ошибка валидации при создании, сабмит заблокирован |
| Шаблон содержит `data-formula-id`, которого нет в базе | Чип `[Удалённая формула #id]` красным цветом |
| Шаблон содержит `data-condition-id`, которого нет в базе | Чип `[Удалённый результат по условию #id]` красным цветом |
| Редактор не инициализирован при попытке вставки | Guard-условие перед командой, silent fail |
| Удаление записи из БД, используемой как статичная переменная в шаблонах | Модальное окно-предупреждение со списком затронутых шаблонов (инициируется модулем, выполняющим удаление, а не редактором) |

---

## Acceptance criteria для разработчика

- Контент редактора сохраняется и загружается в корректном HTML-формате.
- Вычисляемые переменные сериализуются в HTML с `data-var-id`; статичные — дополнительно с `data-var-table`; оба типа парсятся обратно в `VariableNode` без потерь.
- Группа переменных «Заполняющий» содержит переменные заполняющего (не "врача"); группа «Пациент» содержит ИМТ и не содержит «Родственники».
- Статичные группы переменных загружают данные lazy при раскрытии аккордиона; внутри каждой — поиск по данным.
- Поля ввода парсятся из HTML в `InputFieldNode` и сериализуются обратно без потерь.
- Переменные подписей парсятся из HTML в `SignVariableNode` и сериализуются обратно без потерь.
- Формулы парсятся из HTML в `FormulaNode` и сериализуются обратно без потерь.
- Результаты по условию парсятся из HTML в `ConditionNode` и сериализуются обратно без потерь.
- Переменные идентифицируются числовым `data-var-id` в HTML (не строковым именем).
- Подписи используют поле `queue` (не `id`) для локального порядкового номера.
- Чипы всех типов — атомарные inline-узлы: не редактируются по символам, удаляются целиком.
- Загрузка изображения через drag & drop / file input выполняет upload в File Module и вставляет URL в HTML.
- Resize handles изображения меняют атрибуты ширины/высоты в HTML.
- Таблицы поддерживают: добавление/удаление строк и столбцов, объединение ячеек, цвет ячеек.
- Кнопки таблицы активны только при курсоре внутри таблицы.
- Кнопки форматирования отражают активное состояние форматирования в позиции курсора.
- Создание поля ввода через модальное окно создаёт запись через API и вставляет чип.
- Из дропдауна "Поле ввода ▾" можно вставить уже созданное поле ввода.
- Добавление подписи через модальное окно добавляет объект в массив `signs` и обновляет дропдаун подписей.
- Порядок элементов в массиве `signs` соответствует порядку создания подписей (определяет очередь подписания).
- Из дропдауна "Подписи ▾" можно вставить любую из 5 переменных каждой подписи как inline-чип.
- Создание формулы через модальное окно создаёт запись через API и вставляет чип.
- Из дропдауна "Формула ▾" можно вставить уже созданную формулу.
- Создание результата по условию через модальное окно создаёт запись через API и вставляет чип.
- Из дропдауна "Условие ▾" можно вставить уже созданный результат по условию.
- `extractDependencies` корректно собирает числовые id для `variables`, `inputs`, `signs` (queue), `formulas`, `conditions`.
- При загрузке шаблона массив `signs` инициализируется из `dependencies.signs`.
- Режим read-only скрывает toolbar и блокирует редактирование всех узлов.
- При загрузке шаблона с неизвестным `data-var-id`, `data-input-id`, `data-sign-queue`, `data-formula-id` или `data-condition-id` — элемент показывает ошибочное состояние (красный чип).
- Шаблон сохраняется и загружается в формате `pages[]`, а не единого `content`; `extractDependencies` обходит HTML всех страниц.
- Кнопки "Сохранить как шаблон" и "Отправить" отображаются только при наличии контента в редакторе.
- Запрос на отправку (`POST /documents/send`) передаёт `pages[]` и `dependencies`; при `access_type === 'public'` поле `access_rights` не включается в тело запроса.
