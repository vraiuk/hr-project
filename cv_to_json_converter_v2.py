import os
import json
from openai import OpenAI

def init_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)

def get_json_template(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def convert_all_cvs(input_folder: str,
                    output_folder: str,
                    position_md_path: str,
                    template_json_path: str):
    """
    Пробегаем по всем .md в input_folder и генерируем для каждого JSON
    с учётом вакансии из position_md_path.
    """
    client = init_openai_client()
    os.makedirs(output_folder, exist_ok=True)

    # Шаблон JSON-структуры
    json_structure_str = json.dumps(
        get_json_template(template_json_path),
        ensure_ascii=False,
        indent=2
    )

    # Считываем вакансию целиком как текст
    with open(position_md_path, "r", encoding="utf-8") as f:
        vacancy_md = f.read()

    md_files = [f for f in os.listdir(input_folder) if f.endswith(".md")]
    success, total = 0, len(md_files)

    for idx, fname in enumerate(md_files, start=1):
        in_path  = os.path.join(input_folder, fname)
        out_path = os.path.join(output_folder, f"{idx}.json")
        try:
            result = convert_cv_to_json(
                markdown_path=in_path,
                vacancy_md=vacancy_md,
                json_template=json_structure_str,
                client=client
            )
            with open(out_path, "w", encoding="utf-8") as fo:
                json.dump(result, fo, ensure_ascii=False, indent=2)
            success += 1
            print(f"[{idx}/{total}] {fname} → OK")
        except Exception as e:
            print(f"[{idx}/{total}] {fname} → ERROR: {e}")

    return success, total

def convert_cv_to_json(markdown_path: str,
                       vacancy_md: str,
                       json_template: str,
                       client: OpenAI) -> dict:
    """
    Выполняет единичный запрос к GPT, передавая:
      1) system: шаблон JSON-структуры
      2) user: текст вакансии + текст резюме
    Ожидает в ответ один валидный JSON в нужном формате.
    """
    # Читаем резюме
    with open(markdown_path, "r", encoding="utf-8") as f:
        resume_md = f.read()

    # Формируем сообщения для chat API
    messages = [
        {
            "role": "system",
            "content": (
                "Ты — опытный HR-специалист. "
                "Твоя задача — оценить, насколько резюме соответствует вакансии, "
                "и вернуть один объект в строгом JSON-формате:\n"
                f"{json_template}"
            )
        },
        {
            "role": "user",
            "content": (
                "Вакансия (маркап):\n"
                f"{vacancy_md}\n\n"
                "Резюме (маркап):\n"
                f"{resume_md}\n\n"
                "Верни готовый JSON без лишнего текста."
            )
        }
    ]

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_completion_tokens=400
    )
    generated = resp.choices[0].message.content.strip()

    # Убираем блоки ```json … ```
    if generated.startswith("```json"):
        generated = generated[len("```json"):].strip()
    if generated.endswith("```"):
        generated = generated[:-3].strip()

    try:
        return json.loads(generated)
    except json.JSONDecodeError as e:
        raise ValueError(f"Не удалось распарсить JSON: {e}")

# Пример вызова:
# convert_all_cvs(
#     input_folder="tests/cooked_cvs",
#     output_folder="tests/cvs_json",
#     position_md_path="tests/position_info.md",
#     template_json_path="tests/cv_scored_example.json"
# )
