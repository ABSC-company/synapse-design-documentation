# 2.2. Редактор документов — Техническое задание для Front-end разработчика

## Назначение

Реализовать WYSIWYG-редактор документов на базе готовой библиотеки rich-text редактора. Редактор предназначен для создания HTML-шаблонов документов с поддержкой:
- стандартного форматирования текста;
- вставки изображений (через File Module S3);
- таблиц;
- маркированных и нумерованных списков;
- кастомных inline-узлов: **переменных** (`{{ var__name }}`), **полей ввода** (`{{ input__id }}`) и **переменных подписей** (`{{ signs__field__id }}`);
- двухколоночного макета документа.

Хранение контента — в HTML-формате.

---

## Стек и выбор библиотеки

Рекомендуемый выбор — **Tiptap** (на основе ProseMirror), либо **Quill.js**. Оба поддерживают кастомные узлы, расширения, хранение в HTML.

Ключевые требования к библиотеке:
- Поддержка кастомных inline-узлов (для переменных, полей ввода и переменных подписей).
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
│   └── SignatureDropdown           ← список подписей / добавить новую подпись
├── EditorCanvas                    ← рабочая область (экземпляр редактора)
│   ├── VariableNode                ← кастомный inline-узел (переменная)
│   ├── InputFieldNode              ← кастомный inline-узел (поле ввода)
│   └── SignVariableNode            ← кастомный inline-узел (переменная подписи)
├── InputFieldModal                 ← модальное окно создания поля ввода
└── SignatureModal                  ← модальное окно создания подписи
```

---

## Хранение контента

Контент редактора хранится и передаётся в виде HTML-строки. При инициализации редактора HTML подгружается в него. При сохранении — HTML извлекается из редактора.

### Переменные в HTML

```html
<span class="editor-variable" data-var-name="patient_name">{{ var__patient_name }}</span>
```

- Атрибут `data-var-name` — технический идентификатор переменной.
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
<span class="editor-sign-var" data-sign-id="1" data-sign-field="signer_fullname">{{ signs__signer_fullname__1 }}</span>
```

- `data-sign-id` — локальный id подписи в рамках шаблона.
- `data-sign-field` — одно из пяти полей: `signer_department`, `signer_position`, `signer_fullname`, `sign`, `sign_date`.
- Порядок подписей определяется массивом `signs` в `dependencies`, а не расположением в HTML.
- При загрузке в редактор — `<span class="editor-sign-var">` → `SignVariableNode`.

---

## Кастомный узел: VariableNode

### Описание

Inline-узел, представляющий вставленную переменную. Не редактируется пользователем напрямую — только вставляется и удаляется.

### Атрибуты узла

```typescript
interface VariableNodeAttrs {
  varName: string;      // технический идентификатор, например "patient_name"
  displayName: string;  // человекочитаемое название, например "Имя пациента"
}
```

### Список переменных (константа на фронте)

```typescript
export const TEMPLATE_VARIABLES: VariableGroup[] = [
  {
    group: 'Дата и время',
    items: [
      { varName: 'current_date', displayName: 'Текущая дата' },
      { varName: 'current_time', displayName: 'Текущее время' },
    ],
  },
  {
    group: 'Клиника',
    items: [
      { varName: 'clinic_name', displayName: 'Название клиники' },
      { varName: 'clinic_logo', displayName: 'Логотип клиники' },
    ],
  },
  {
    group: 'Филиал',
    items: [
      { varName: 'branch_name',          displayName: 'Название филиала' },
      { varName: 'main_branch_name',     displayName: 'Название главного филиала' },
      { varName: 'branch_address',       displayName: 'Адрес филиала' },
      { varName: 'main_branch_address',  displayName: 'Адрес главного филиала' },
      { varName: 'branch_socials',       displayName: 'Контакты филиала: соц. сети' },
      { varName: 'branch_email',         displayName: 'Контакты филиала: эл. почта' },
      { varName: 'branch_phones',        displayName: 'Контакты филиала: номера телефона' },
      { varName: 'main_branch_socials',  displayName: 'Контакты главного филиала: соц. сети' },
      { varName: 'main_branch_email',    displayName: 'Контакты главного филиала: эл. почта' },
      { varName: 'main_branch_phones',   displayName: 'Контакты главного филиала: номера телефона' },
    ],
  },
  {
    group: 'Врач',
    items: [
      { varName: 'doctor_last_name',   displayName: 'Фамилия врача' },
      { varName: 'doctor_first_name',  displayName: 'Имя врача' },
      { varName: 'doctor_middle_name', displayName: 'Отчество врача' },
      { varName: 'doctor_specialty',   displayName: 'Специализация врача' },
      { varName: 'doctor_category',    displayName: 'Категория врача' },
      { varName: 'doctor_department',  displayName: 'Отдел врача' },
      { varName: 'doctor_position',    displayName: 'Должность врача' },
    ],
  },
  {
    group: 'Пациент',
    items: [
      { varName: 'patient_last_name',   displayName: 'Фамилия пациента' },
      { varName: 'patient_first_name',  displayName: 'Имя пациента' },
      { varName: 'patient_middle_name', displayName: 'Отчество пациента' },
      { varName: 'patient_birth_date',  displayName: 'Дата рождения пациента' },
      { varName: 'patient_gender',      displayName: 'Пол пациента' },
      { varName: 'patient_address',     displayName: 'Адрес пациента' },
      { varName: 'patient_blood_abo',   displayName: 'Группа крови пациента (ABO)' },
      { varName: 'patient_blood_rh',    displayName: 'Резус-фактор пациента (Rh)' },
      { varName: 'patient_allergies',   displayName: 'Аллергии пациента' },
      { varName: 'patient_chronic',     displayName: 'Хронические заболевания пациента' },
      { varName: 'patient_relatives',   displayName: 'Родственники пациента' },
    ],
  },
];
```

> `current_datetime` удалён — заменён отдельными `current_date` и `current_time`.
> `doctor_signature` удалён — подписи управляются через `SignatureNode`.

### Поведение в редакторе

- Атомарный узел: не разбивается на части, не редактируется по символам.
- Удаляется целиком через Delete/Backspace или клик + Delete.
- При сериализации в HTML: `<span class="editor-variable" data-var-name="{varName}">{{ var__{varName} }}</span>`.
- При парсинге HTML обратно: `<span class="editor-variable">` → `VariableNode`.

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
  signId: number;       // локальный id подписи в рамках шаблона
  signField: 'signer_department' | 'signer_position' | 'signer_fullname' | 'sign' | 'sign_date';
  displayName: string;  // человекочитаемое название, например "ФИО подписанта #1"
}
```

### Отображаемые названия полей

| `signField` | `displayName` (шаблон) |
|-------------|------------------------|
| `signer_department` | `Отдел подписанта #<id>` |
| `signer_position` | `Должность подписанта #<id>` |
| `signer_fullname` | `ФИО подписанта #<id>` |
| `sign` | `Подпись #<id>` |
| `sign_date` | `Дата подписания #<id>` |

### Поведение в редакторе

- Атомарный inline-узел: аналогично `VariableNode`.
- Удаляется целиком через Delete/Backspace или клик + Delete.
- Одну и ту же переменную можно вставить в несколько мест документа.
- Удаление чипа из документа не удаляет саму подпись из массива `signs`.
- При сериализации: `<span class="editor-sign-var" data-sign-id="{id}" data-sign-field="{field}">{{ signs__{field}__{id} }}</span>`.
- При парсинге HTML: `<span class="editor-sign-var">` → `SignVariableNode`.

### Хранение подписей в состоянии редактора

Список подписей, добавленных в шаблон, хранится в локальном состоянии компонента (не в HTML редактора):

```typescript
interface Sign {
  id: number;            // локальный id (в рамках данного шаблона, начинается с 1)
  department_id: number; // FK (Structure Module)
  position_id: number;   // FK (Structure Module)
  employee_id: number | null; // FK (HR Module), nullable
}

const [signs, setSigns] = useState<Sign[]>([]);
```

При добавлении новой подписи через модальное окно:
1. Присвоить `id = signs.length + 1`.
2. Добавить объект в массив `signs`.
3. Дропдаун автоматически обновляется и показывает новую подпись с её пятью переменными для вставки.

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
interface DocumentTemplate {
  name: string;
  description: string;
  content: string; // HTML из редактора
  dependencies: {
    variables: string[]; // полные идентификаторы переменных, например ["var__current_date", "var__patient_name"]
    inputs: number[];    // id полей ввода, использованных в шаблоне
    signs: Sign[];       // массив объектов подписей (очередь определяется порядком в массиве)
  };
}
```

Пример:

```json
{
  "name": "Справка об обследовании",
  "description": "Шаблон справки для амбулаторного приёма",
  "content": "<p>Пациент: <span class=\"editor-variable\" data-var-name=\"patient_last_name\">{{ var__patient_last_name }}</span></p><div class=\"editor-signature\" data-sign-id=\"1\">...</div>",
  "dependencies": {
    "variables": ["var__patient_last_name", "var__current_date"],
    "inputs": [1, 42],
    "signs": [
      { "id": 1, "department_id": 5, "position_id": 12, "employee_id": null },
      { "id": 2, "department_id": 3, "position_id": 7, "employee_id": 101 }
    ]
  }
}
```

### Извлечение dependencies из HTML и состояния

```typescript
function extractDependencies(
  html: string,
  signs: Sign[]
): DocumentTemplate['dependencies'] {
  const variables: string[] = [];
  const inputs: number[] = [];

  // Обычные переменные — из data-var-name, сохраняются с префиксом var__
  const varMatches = html.matchAll(/data-var-name="([^"]+)"/g);
  for (const match of varMatches) {
    const key = `var__${match[1]}`;
    if (!variables.includes(key)) variables.push(key);
  }

  // Поля ввода — из data-input-id
  const inputMatches = html.matchAll(/data-input-id="(\d+)"/g);
  for (const match of inputMatches) {
    const id = Number(match[1]);
    if (!inputs.includes(id)) inputs.push(id);
  }

  // Подписи — берутся из локального состояния (не из HTML).
  // HTML содержит отдельные чипы переменных подписей, но очередь подписания
  // определяется порядком объектов в массиве signs.
  return { variables, inputs, signs };
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
      varName: variable.varName,
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

function insertSignVariable(editor: Editor, signId: number, field: SignField) {
  editor.chain().focus().insertContent({
    type: 'signVariableNode',
    attrs: {
      signId,
      signField: field,
      displayName: `${SIGN_FIELD_LABELS[field]} #${signId}`,
    },
  }).run();
}
```

---

## Загрузка шаблона в редактор

При открытии существующего шаблона:

1. Получить объект шаблона с сервера (включая `dependencies.signs`).
2. Инициализировать локальное состояние подписей из `dependencies.signs`.
3. Подгрузить список полей ввода для разрешения `inputId` → `displayName`.
4. Передать `content` в редактор — парсеры кастомных узлов разрезолвят данные из HTML-атрибутов.

```typescript
async function loadTemplate(templateId: number): Promise<void> {
  const [template, inputFields] = await Promise.all([
    api.get(`/document-templates/${templateId}`),
    api.get('/document-templates/input-fields'),
  ]);

  setSigns(template.dependencies.signs);
  setInputFieldMap(new Map(inputFields.map((f: InputField) => [f.id, f])));
  editor.commands.setContent(template.content);
}
```

---

## Сохранение шаблона

```typescript
async function saveTemplate(
  templateId: number,
  editor: Editor,
  signs: Sign[],
  meta: { name: string; description: string }
): Promise<void> {
  const html = editor.getHTML();
  const dependencies = extractDependencies(html, signs);

  const body: DocumentTemplate = {
    name: meta.name,
    description: meta.description,
    content: html,
    dependencies,
  };

  await api.patch(`/document-templates/${templateId}`, body);
}

async function createTemplate(
  editor: Editor,
  signs: Sign[],
  meta: { name: string; description: string }
): Promise<void> {
  const html = editor.getHTML();
  const dependencies = extractDependencies(html, signs);

  const body: DocumentTemplate = {
    name: meta.name,
    description: meta.description,
    content: html,
    dependencies,
  };

  await api.post('/document-templates', body);
}
```

---

## Режим read-only

```typescript
editor.setEditable(false); // или через опцию при инициализации: editable: false
```

В режиме read-only:
- Toolbar скрыт или весь disabled.
- Кастомные узлы не принимают события клика/фокуса.

---

## Подстановка переменных при рендеринге итогового документа

При формировании готового документа по шаблону фронт (или бек) заменяет плейсхолдеры значениями:

```
{{ var__patient_name }}           → "Иванов"
{{ var__current_date }}           → "12.06.2026"
{{ var__current_time }}           → "09:41"
{{ input__42 }}                   → значение, введённое пользователем
{{ signs__signer_fullname__1 }}   → "Петров П.П."
{{ signs__sign__1 }}              → [изображение подписи]
{{ signs__sign_date__1 }}         → "12.06.2026"
```

Регулярные выражения для поиска при рендеринге:

```typescript
const VAR_REGEX   = /\{\{\s*var__(\w+)\s*\}\}/g;
const INPUT_REGEX = /\{\{\s*input__(\d+)\s*\}\}/g;
const SIGN_REGEX  = /\{\{\s*signs__(\w+)__(\d+)\s*\}\}/g;
// SIGN_REGEX: match[1] — signField, match[2] — signId
```

---

## Edge cases и обработка ошибок

| Ситуация | Поведение |
|----------|-----------|
| Ошибка загрузки изображения | Toast с ошибкой, изображение не вставляется |
| Создание поля ввода — пустое название | Валидация в модальном окне, сабмит заблокирован |
| Вставка `select`/`multi_select` без значений в `data` | Предупреждение в модальном окне |
| Шаблон содержит `input__id`, которого нет в базе | Чип `[Удалённое поле #id]` красным цветом |
| Шаблон содержит `var__name`, которой нет в списке | Чип `[Неизвестная переменная: name]` красным цветом |
| Попытка удалить поле ввода, используемое в шаблонах | Ошибка от API, уведомление пользователю |
| Загрузка файла > допустимого размера | Валидация на фронте до запроса, сообщение об ошибке |
| Создание подписи — не выбран отдел или должность | Валидация в модальном окне, сабмит заблокирован |
| Шаблон содержит `data-sign-id`, которого нет в `signs` | Чип с пометкой `[Удалённая подпись #id]` красным цветом |
| Редактор не инициализирован при попытке вставки | Guard-условие перед командой, silent fail |

---

## Acceptance criteria для разработчика

- Контент редактора сохраняется и загружается в корректном HTML-формате.
- Переменные парсятся из HTML в `VariableNode` и сериализуются обратно без потерь.
- Поля ввода парсятся из HTML в `InputFieldNode` и сериализуются обратно без потерь.
- Переменные подписей парсятся из HTML в `SignVariableNode` и сериализуются обратно без потерь.
- Константа `TEMPLATE_VARIABLES` содержит `current_time` вместо `current_datetime`; `doctor_signature` отсутствует.
- Чипы переменных, полей ввода и переменных подписей — атомарные inline-узлы: не редактируются по символам, удаляются целиком.
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
- `extractDependencies` корректно собирает `variables` (с префиксом `var__`), `inputs` и `signs`.
- Функции `saveTemplate` / `createTemplate` передают полный объект `DocumentTemplate` с `dependencies.signs`.
- При загрузке шаблона массив `signs` инициализируется из `dependencies.signs`.
- Режим read-only скрывает toolbar и блокирует редактирование всех узлов.
- При загрузке шаблона с неизвестным `input__id`, `var__name` или `sign-id` — элемент показывает ошибочное состояние.
