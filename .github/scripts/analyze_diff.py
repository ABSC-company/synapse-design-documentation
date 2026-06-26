import json
import os
from openai import OpenAI

DIFF_PATH = "diff.txt"
MAX_CHARS = 30000  # грубая защита от огромных диффов (≈ контроль токенов)

SYSTEM_PROMPT = """Ты — технический аналитик изменений в документации архитектуры.
На вход получаешь git diff документации (бекенд или дизайн).
Твоя задача — определить смысл изменения, а не пересказать diff построчно.

Правила:
- requires_attention = false, если изменение чисто косметическое
  (опечатки, форматирование, переносы строк, правка ссылок без смысла).
- requires_attention = true, если изменён контракт, поведение, схема данных,
  добавлен/удалён компонент, или изменение влияет на работу команды.
- change_type = "breaking", если меняется существующий контракт так,
  что старые клиенты/потребители сломаются.
- summary и impact пиши на русском, кратко и конкретно, по сути.
- task_title — короткий заголовок задачи в повелительном наклонении.
- task_description — что именно нужно сделать команде.
Отвечай строго по заданной схеме."""

SCHEMA = {
    "name": "doc_change_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "requires_attention": {"type": "boolean"},
            "audience": {"type": "string", "enum": ["backend", "design", "both"]},
            "affected_component": {"type": "string"},
            "change_type": {
                "type": "string",
                "enum": ["added", "modified", "removed", "breaking"],
            },
            "summary": {"type": "string"},
            "impact": {"type": "string"},
            "task_title": {"type": "string"},
            "task_description": {"type": "string"},
            "priority": {
                "type": "string",
                "enum": ["Highest", "High", "Medium", "Low"],
            },
        },
        "required": [
            "requires_attention", "audience", "affected_component",
            "change_type", "summary", "impact", "task_title",
            "task_description", "priority",
        ],
    },
}


def write_output(key, value):
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def load_diff():
    try:
        with open(DIFF_PATH, encoding="utf-8") as f:
            diff = f.read()
    except FileNotFoundError:
        return None
    if not diff.strip():
        return None
    if len(diff) > MAX_CHARS:
        diff = diff[:MAX_CHARS] + "\n\n[diff обрезан из-за размера]"
    return diff


def main():
    diff = load_diff()
    if diff is None:
        print("Пустой diff — нечего анализировать.")
        write_output("requires_attention", "false")
        return

    client = OpenAI()  # ключ берётся из OPENAI_API_KEY
    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Diff документации:\n\n{diff}"},
        ],
        response_format={"type": "json_schema", "json_schema": SCHEMA},
    )

    data = json.loads(resp.choices[0].message.content)
    with open("analysis.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(json.dumps(data, ensure_ascii=False, indent=2))
    write_output(
        "requires_attention",
        "true" if data["requires_attention"] else "false",
    )


if __name__ == "__main__":
    main()