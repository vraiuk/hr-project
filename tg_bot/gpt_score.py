import os
import json
import tempfile
import shutil
import logging
from docx import Document
from typing import List, Dict, Any
from openai import OpenAI, OpenAIError
from conversion import convert_pdf_to_markdown
from ontology_check import transform_and_check_resume

logger = logging.getLogger(__name__)

# JSON template for GPT output (path to your schema file)
TEMPLATE_JSON_PATH = "tests/cv_scored_example.json"
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")


def init_openai_client() -> OpenAI:
    """
    Initialize the OpenAI client using the API key.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=OPENAI_API_KEY)


def pdf_to_markdown_str(pdf_path: str) -> str:
    """
    Конвертирует ОДИН PDF в Markdown-строку,
    избегая конвертации всех файлов в downloads/.
    """
    # 1) Папка, куда скопируем только этот файл
    temp_input = tempfile.mkdtemp()
    basename = os.path.basename(pdf_path)
    single_pdf = os.path.join(temp_input, basename)
    shutil.copy(pdf_path, single_pdf)

    # 2) Папка для Markdown
    md_dir = tempfile.mkdtemp()

    try:
        # 3) Конвертация только этого PDF
        convert_pdf_to_markdown(temp_input, md_dir)

        # 4) Читаем единственный .md
        md_content = ""
        for fname in os.listdir(md_dir):
            if fname.lower().endswith(".md"):
                with open(os.path.join(md_dir, fname), encoding="utf-8") as f:
                    md_content = f.read()
                break

        return md_content

    finally:
        # Убираем за собой
        shutil.rmtree(temp_input)
        shutil.rmtree(md_dir)

# --- DOCX → Markdown ---
def docx_to_markdown(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        doc = Document(path)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    else:
        return "❌ Неподдерживаемый формат файла."

def gpt_match_score(
    resume_md: str,
    vacancy_md: str,
    template_path: str = TEMPLATE_JSON_PATH
) -> float:
    """
    Query GPT to evaluate how well resume_markdown matches vacancy_markdown.
    Uses a strict JSON schema loaded from `template_path`.
    Returns a float in [0.0, 1.0].
    """
    client = init_openai_client()

    with open(template_path, encoding="utf-8") as f:
        template = json.load(f)

    system_prompt = (
        "You are an expert HR specialist with deep recruiting experience. "
        "Your task is to analyze a job posting and a candidate’s resume—both provided in Markdown—and produce a structured JSON assessment. "
        "Evaluate each of the following dimensions:\n"
        "  • matchScore: overall fit between resume and vacancy (0.00–1.00)\n"
        "  • education: depth and relevance of academic background (0.00–1.00)\n"
        "  • experience: totalYears and relevance to the role (each 0.00–1.00)\n"
        "  • skills: technical and professional skills alignment (0.00–1.00)\n"
        "  • courses: completion of relevant courses (0.00–1.00)\n"
        "  • languages: proficiency levels (0.00–1.00)\n"
        "  • additionalInfo: certifications, projects, and extra achievements (0.00–1.00)\n"
        "  • jobPreferences: alignment of candidate’s preferences with the role (0.00–1.00)\n\n"
        "Return exactly one JSON object following this schema:\n"
        f"{json.dumps(template, ensure_ascii=False, indent=2)}\n\n"
        "Do NOT include any extra keys, explanations, or markdown fences—only the JSON."
    )

    user_prompt = (
        "Please evaluate the following documents and return only the JSON object defined above:\n\n"
        "=== Job Posting (Markdown) ===\n"
        f"{vacancy_md}\n\n"
        "=== Candidate Resume (Markdown) ===\n"
        f"{resume_md}\n\n"
        "Return only the JSON object with the fields and numeric values as specified—no commentary, no additional text."
    )


    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=0.0,
            top_p=1.0,
            max_completion_tokens=150
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        logger.info("GPT raw response:\n%s", raw)
    except OpenAIError as e:
        logger.error("OpenAI API error: %s", e)
        return 0.0

    # Strip code fences if present
    if raw.startswith("```"):
        raw = raw.split("```", 2)[-1]
    if raw.endswith("```"):
        raw = raw[:-3]

    try:
        data = json.loads(raw)
        return float(data.get("matchScore", 0.0))
    except Exception as e:
        logger.error("Failed to parse GPT response: %s\nRaw: %s", e, raw)
        return 0.0

def gpt_match_assessment(
    resume_md: str,
    vacancy_md: str,
    template_path: str = TEMPLATE_JSON_PATH
) -> Dict[str, Any]:
    """
    Query GPT to get full JSON assessment (matchScore + all metrics).
    Returns the parsed JSON dict, or defaults.
    """
    client = init_openai_client()
    # load expected schema with all keys
    with open(template_path, encoding="utf-8") as f:
        template = json.load(f)
    system_prompt = (
        "You are an expert HR specialist. Provide a structured JSON assessment of how well a resume matches a vacancy. "
        "Use this exact schema (no extra keys or commentary):\n" +
        json.dumps(template, ensure_ascii=False, indent=2)
    )
    user_prompt = (
        "Evaluate these documents and return only the JSON object: \n"
        "--- Vacancy Markdown ---\n" + vacancy_md + "\n\n"
        "--- Resume Markdown ---\n" + resume_md + "\n"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=0.0,
            top_p=1.0,
            max_completion_tokens=200
        )
        raw = resp.choices[0].message.content.strip()
        # clean code fences
        if raw.startswith("```json"):
            raw = raw.split("```", 2)[-1]
        raw = raw.strip("` \n")
        logger.info("GPT raw response:\n%s", raw)
        data = json.loads(raw)
    except (OpenAIError, json.JSONDecodeError) as e:
        logger.error("Error obtaining/parsing GPT assessment: %s", e)
        # return defaults based on schema
        data = {k: ({} if isinstance(v, dict) else 0.0) for k, v in template.items()}
        data['matchScore'] = 0.0
    return data

def piecewise_education(edu_val: float) -> float:
    """
    Non-linear transform for education score.
    """
    if edu_val <= 0.4:
        return 2.5 * edu_val
    if edu_val <= 0.7:
        return 1.0 + 1.6667 * (edu_val - 0.4)
    base = 1.5 + 0.5 * (edu_val - 0.7)
    return min(base, 1.0)


def experience_score(exp: Dict[str, float]) -> float:
    """
    Compute experience score from totalYears and relevance.
    """
    ty = exp.get("totalYears", 0.0)
    rel = exp.get("relevance", 0.0)
    base = (ty + rel) / 2
    synergy = 0.05 if (ty > 0.7 and rel > 0.7) else 0.0
    return min(base + synergy, 1.0)


def calculate_mai_plus_score(
    metrics: Dict[str, Any],
    weights: Dict[str, float]
) -> float:
    """
    Compute MAI+ score using provided metrics and weights.
    """
    edu_u = piecewise_education(metrics.get("education", 0.0))
    exp_u = experience_score(metrics.get("experience", {}))

    sk = metrics.get("skills", 0.0)
    synergy_sk = 0.03 if (sk > 0.8 and exp_u > 0.6) else 0.0
    sk_u = min(sk + synergy_sk, 1.0)

    courses = metrics.get("courses", 0.0)
    if edu_u > 0.8 and courses > 0.5:
        edu_u = min(edu_u * 1.1, 1.0)

    jp   = metrics.get("jobPreferences", 0.0)
    lang = metrics.get("languages", 0.0)
    add  = metrics.get("additionalInfo", 0.0)

    score = (
        weights["jobPreferences"] * jp +
        weights["experience"]     * exp_u +
        weights["education"]      * edu_u +
        weights["courses"]        * courses +
        weights["skills"]         * sk_u +
        weights["languages"]      * lang +
        weights["additional"]     * add
    )
    return round(score, 3)


def generate_report(
    *,
    vacancy_pdf: str = None,
    vacancy_md: str = None,
    resume_pdfs: List[str],
    mai_weights: Dict[str, float],
    alpha: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Для каждой резюме:
      1) Конвертируем vacancy (PDF → Markdown) или берём vacancy_md
      2) Конвертируем резюме в Markdown
      3) Запрашиваем у GPT полные метрики (matchScore + breakdown)
      4) Считаем локальный MAI+ по тем же метрикам
      5) Усредняем с весом alpha и возвращаем список:
         [{ name, score, details }, ...] отсортированный по score desc
    """
    # 1) Подготавливаем Markdown вакансии
    if vacancy_md is None:
        if not vacancy_pdf:
            raise ValueError("Ошибка в процессе конвертации описания вакансии.")
        vacancy_md = pdf_to_markdown_str(vacancy_pdf)

    report = []
    
    for path in resume_pdfs:
        # 2) Резюме → Markdown
        resume_md = pdf_to_markdown_str(path)

        # 3) Полный расклад от GPT (matchScore + поля)
        full: Dict[str, Any] = gpt_match_assessment(resume_md, vacancy_md)
        ontology_issues = transform_and_check_resume(resume_md)
        match_score = float(full.get("matchScore", 0.0))

        # 4) Локальный MAI+ по тем же метрикам
        local_score = calculate_mai_plus_score(full, mai_weights)

        # 5) Итоговый скор
        final = round(alpha * match_score + (1 - alpha) * local_score, 3)

        report.append({
            "name":    os.path.basename(path),
            "score":   final,
            "details": full,
            "ontologyIssues": ontology_issues
        })

    # Сортируем по убыванию score
    return sorted(report, key=lambda x: x["score"], reverse=True)
