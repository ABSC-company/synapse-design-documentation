import json
import os
import requests
from requests.auth import HTTPBasicAuth

with open("analysis.json", encoding="utf-8") as f:
    a = json.load(f)

base = os.environ["JIRA_BASE_URL"].rstrip("/")
auth = HTTPBasicAuth(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])
project = os.environ.get("JIRA_PROJECT_KEY", "").strip()
if not project:
    print("Не передан ключ проекта Jira — задача не создаётся.")
    raise SystemExit(1)


# --- предварительные проверки доступа к Jira (понятные сообщения в логах) ---
def preflight():
    # 1) Аутентификация: кто мы для Jira?
    who = requests.get(
        f"{base}/rest/api/3/myself", auth=auth,
        headers={"Accept": "application/json"},
    )
    if who.status_code == 401:
        print("Jira preflight: 401 — неверные JIRA_EMAIL / JIRA_API_TOKEN "
              "или токен от другого сайта Atlassian.")
        raise SystemExit(1)
    if who.status_code >= 300:
        print("Jira preflight: не удалось проверить учётные данные:",
              who.status_code, who.text)
        raise SystemExit(1)
    print(f"Jira preflight: аутентифицированы как "
          f"{who.json().get('emailAddress') or who.json().get('displayName')}")

    # 2) Проект: существует и виден ли этой учётке?
    proj = requests.get(
        f"{base}/rest/api/3/project/{project}", auth=auth,
        headers={"Accept": "application/json"},
    )
    if proj.status_code == 404:
        print(f"Jira preflight: проект с ключом '{project}' не найден или недоступен. "
              f"Проверьте, что это именно КЛЮЧ проекта (префикс задач, напр. {project}-123), "
              f"а не название, и что JIRA_BASE_URL указывает на нужный сайт.")
        raise SystemExit(1)
    if proj.status_code >= 300:
        print(f"Jira preflight: ошибка доступа к проекту '{project}':",
              proj.status_code, proj.text)
        raise SystemExit(1)

    # 3) Есть ли в проекте право создавать задачи и тип "Task"?
    meta = requests.get(
        f"{base}/rest/api/3/issue/createmeta",
        params={"projectKeys": project, "expand": "projects.issuetypes"},
        auth=auth, headers={"Accept": "application/json"},
    )
    if meta.status_code < 300:
        projects = meta.json().get("projects", [])
        if not projects:
            print(f"Jira preflight: у учётки нет права создавать задачи в проекте "
                  f"'{project}' (Create issues). Добавьте пользователя в проект "
                  f"с подходящей ролью.")
            raise SystemExit(1)
        types = [t["name"] for t in projects[0].get("issuetypes", [])]
        if types and "Task" not in types:
            print(f"Jira preflight: в проекте '{project}' нет типа задачи 'Task'. "
                  f"Доступные типы: {', '.join(types)}.")
            raise SystemExit(1)
    print(f"Jira preflight: проект '{project}' доступен для создания задач.")


preflight()

commit_url = os.environ.get("COMMIT_URL", "")
compare_url = os.environ.get("COMPARE_URL", "")
author = os.environ.get("COMMIT_AUTHOR", "")
repo = os.environ.get("REPO", "")
assignee = os.environ.get("JIRA_ASSIGNEE", "").strip()


# --- определение исполнителя: принимаем accountId или email ---
def resolve_assignee(value):
    if not value:
        return None
    # если это не email — считаем, что передан готовый accountId
    if "@" not in value:
        return value
    # email → accountId через поиск пользователей (нужно право Browse users)
    res = requests.get(
        f"{base}/rest/api/3/user/search",
        params={"query": value}, auth=auth,
        headers={"Accept": "application/json"},
    )
    if res.status_code >= 300:
        print(f"Не удалось найти исполнителя по '{value}': "
              f"{res.status_code} {res.text}. Задача создаётся без исполнителя.")
        return None
    users = res.json()
    if not users:
        print(f"Исполнитель '{value}' не найден в Jira. "
              f"Задача создаётся без исполнителя.")
        return None
    return users[0]["accountId"]


# --- сборка описания в формате ADF (Atlassian Document Format), нужен для API v3 ---
def heading(text):
    return {"type": "heading", "attrs": {"level": 3},
            "content": [{"type": "text", "text": text}]}

def para(text):
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}

def link_para(label, url):
    return {"type": "paragraph", "content": [
        {"type": "text", "text": f"{label}: "},
        {"type": "text", "text": url,
         "marks": [{"type": "link", "attrs": {"href": url}}]},
    ]}


description = {
    "type": "doc", "version": 1,
    "content": [
        heading("Что изменилось"),
        para(a["summary"]),
        heading("Влияние"),
        para(a["impact"]),
        heading("Что нужно сделать"),
        para(a["task_description"]),
        heading("Детали"),
        para(f'Компонент: {a["affected_component"]}'),
        para(f'Тип изменения: {a["change_type"]}'),
        para(f'Аудитория: {a["audience"]}'),
        heading("Источник"),
        para(f"Репозиторий: {repo}"),
        para(f"Автор коммита: {author}"),
        link_para("Коммит", commit_url),
        link_para("Сравнение изменений", compare_url),
    ],
}

# labels в Jira не могут содержать пробелы — наши значения однословные
payload = {
    "fields": {
        "project": {"key": project},
        "summary": a["task_title"][:240],
        "description": description,
        "issuetype": {"name": "Task"},
        "labels": ["ai-generated", "needs-triage",
                   a["audience"], a["change_type"]],
        "priority": {"name": a["priority"]},  # см. примечание ниже
    }
}

# назначаем исполнителя, если задан и успешно отрезолвлен
assignee_id = resolve_assignee(assignee)
if assignee_id:
    payload["fields"]["assignee"] = {"accountId": assignee_id}
    print(f"Исполнитель задачи: {assignee_id}")

r = requests.post(
    f"{base}/rest/api/3/issue",
    json=payload, auth=auth,
    headers={"Accept": "application/json", "Content-Type": "application/json"},
)

if r.status_code >= 300:
    print("Jira error:", r.status_code, r.text)
    if r.status_code == 400:
        print("Подсказка: поле в payload не подходит схеме проекта — чаще всего "
              "'priority' отсутствует на экране (особенно в team-managed проектах), "
              f"значение priority '{a.get('priority')}' недопустимо, "
              "либо у исполнителя нет права 'Assignable User' в этом проекте.")
    raise SystemExit(1)

key = r.json()["key"]
print(f"Создана задача: {base}/browse/{key}")