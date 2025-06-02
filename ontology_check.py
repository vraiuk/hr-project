from owlready2 import *
import logging
import json
import os
import json
from typing import List, Dict, Any, Tuple, Union

from openai import OpenAI, OpenAIError
from owlready2 import sync_reasoner
from github import Github
from datetime import datetime, timezone


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

gh_client = Github(GITHUB_TOKEN)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TEMPLATE_JSON_PATH = "tests/cvs_json/cv_example.json"
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")

def init_openai_client() -> OpenAI:
    """
    Initialize the OpenAI client using the API key.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=OPENAI_API_KEY)

def extract_github_username(resume_md: str) -> Union[str, None]:
    match = re.search(r'https?://github\.com/([A-Za-z0-9_-]+)', resume_md)
    return match.group(1) if match else None


def check_github_profile(username: str) -> dict:
    """
    Возвращает словарь с метриками профиля или пустой dict, если не найден.
    """
    try:
        user = gh_client.get_user(username)
    except Exception as e:
        # не удалось найти или нет доступа
        return {
        "githubExists":      False,
        "publicRepos":       0,
        "followers":         0,
        "lastActiveDays":    None
    }

    # Кол-во публичных репозиториев и подписчиков
    repos = user.public_repos
    followers = user.followers

    # Дата последнего публичного события (push, pr, issue и т.д.)
    events = user.get_events()  # список публичных событий
    last_active = None
    for ev in events:
        last_active = ev.created_at
        break

    days_ago = None
    if last_active:
        now = datetime.now(timezone.utc)
        days_ago = (now - last_active).days

    return {
        "githubExists":      True,
        "publicRepos":       repos,
        "followers":         followers,
        "lastActiveDays":    days_ago
    }

def create_ontology():
    """
    Creates and returns the resume ontology with all necessary classes and properties
    """
    onto = get_ontology("http://example.org/resume.owl")

    with onto:
        # Define main classes
        class Resume(Thing):
            pass

        class Person(Thing):
            pass

        class Education(Thing):
            pass

        class Course(Thing):
            pass

        class Experience(Thing):
            pass

        class Language(Thing):
            pass

        class Location(Thing):
            pass

        # Define properties for Resume
        class hasID(Resume >> str): pass
        class hasTotalExperience(Resume >> str): pass
        class hasAdditionalInfo(Resume >> str): pass
        class hasSkills(Resume >> str): pass
        class hasPerson(Resume >> Person): pass
        class hasEducation(Resume >> Education): pass
        class hasCourse(Resume >> Course): pass
        class hasExperience(Resume >> Experience): pass
        class hasLanguage(Resume >> Language): pass
        class hasLocation(Resume >> Location): pass

        # Properties for Person
        class hasFullName(Person >> str): pass

        # Properties for Education
        class eduYear(Education >> str): pass
        class eduDegree(Education >> str): pass
        class eduInstitution(Education >> str): pass
        class eduLocation(Education >> str): pass
        class eduFaculty(Education >> str): pass
        class eduSpecialization(Education >> str): pass

        # Properties for Course
        class courseYear(Course >> str): pass
        class courseTitle(Course >> str): pass
        class courseCategory(Course >> str): pass

        # Properties for Experience
        class expCompanyName(Experience >> str): pass
        class expRole(Experience >> str): pass
        class expStartDate(Experience >> str): pass
        class expEndDate(Experience >> str): pass
        class expMonthsInPosition(Experience >> str): pass
        class expStack(Experience >> str): pass
        class expAchievements(Experience >> str): pass

        # Properties for Language
        class langName(Language >> str): pass
        class langLevel(Language >> str): pass

        # Properties for Location
        class locCity(Location >> str): pass
        class locWillingToRelocate(Location >> str): pass

    return onto

def check_resume_ontology(resume_data, onto):
    """
    Creates ontology instances for a single resume and adds them to the ontology
    """
    # Create Resume instance
    resume_ind = onto.Resume(f"Resume_{resume_data.get('id', 'unknown')}")
    resume_ind.hasID.append(str(resume_data.get("id", "")))
    resume_ind.hasTotalExperience.append(str(resume_data.get("totalExperience", 0.0)))
    resume_ind.hasAdditionalInfo.append(str(resume_data.get("additionalInfo", "")))

    # Create Person instance
    person_ind = onto.Person(f"Person_{resume_data.get('id', 'unknown')}")
    person_ind.hasFullName.append(str(resume_data.get("fullName", "")))
    person_ind.hasPerson = [person_ind]

    # Process Education
    education_list = resume_data.get("education", []) or []
    for idx, edu in enumerate(education_list):
        edu_ind = onto.Education(f"Education_{resume_data.get('id', 'unknown')}_{idx}")
        edu_ind.eduYear.append(str(edu.get("year", "")))
        edu_ind.eduDegree.append(str(edu.get("degree", "")))
        edu_ind.eduInstitution.append(str(edu.get("institution", "")))
        edu_ind.eduLocation.append(str(edu.get("location", "")))
        edu_ind.eduFaculty.append(str(edu.get("faculty", "")))
        edu_ind.eduSpecialization.append(str(edu.get("specialization", "")))
        resume_ind.hasEducation.append(edu_ind)

    # Process Courses
    courses_list = resume_data.get("courses", []) or []
    for idx, course in enumerate(courses_list):
        course_ind = onto.Course(f"Course_{resume_data.get('id', 'unknown')}_{idx}")
        course_ind.courseYear.append(str(course.get("year", "")))
        course_ind.courseTitle.append(str(course.get("title", "")))
        course_ind.courseCategory.append(str(course.get("category", "")))
        resume_ind.hasCourse.append(course_ind)

    # Process Experience
    experience_list = resume_data.get("experience", []) or []
    for idx, exp in enumerate(experience_list):
        exp_ind = onto.Experience(f"Experience_{resume_data.get('id', 'unknown')}_{idx}")
        exp_ind.expCompanyName.append(str(exp.get("companyName", "")))
        exp_ind.expRole.append(str(exp.get("role", "")))
        exp_ind.expStartDate.append(str(exp.get("startDate", "")))
        exp_ind.expEndDate.append(str(exp.get("endDate", "")))
        exp_ind.expMonthsInPosition.append(str(exp.get("monthsInPosition", 0)))
        
        # Process stack items
        stack_list = exp.get("stack", []) or []
        for stack_item in stack_list:
            exp_ind.expStack.append(str(stack_item))
        
        # Process achievements
        achievements_list = exp.get("achievements", []) or []
        for achievement in achievements_list:
            exp_ind.expAchievements.append(str(achievement))
            
        resume_ind.hasExperience.append(exp_ind)

    # Process Skills
    skills_list = resume_data.get("skills", []) or []
    for skill in skills_list:
        resume_ind.hasSkills.append(str(skill))

    # Process Languages
    languages_list = resume_data.get("languages", []) or []
    for idx, lang in enumerate(languages_list):
        lang_ind = onto.Language(f"Language_{resume_data.get('id', 'unknown')}_{idx}")
        lang_ind.langName.append(str(lang.get("name", "")))
        lang_ind.langLevel.append(str(lang.get("level", "")))
        resume_ind.hasLanguage.append(lang_ind)

    # Process Location
    loc = resume_data.get("location", {}) or {}
    if loc:
        loc_ind = onto.Location(f"Location_{resume_data.get('id', 'unknown')}")
        loc_ind.locCity.append(str(loc.get("city", "")))
        loc_ind.locWillingToRelocate.append(str(loc.get("willingToRelocate", False)))
        resume_ind.hasLocation = [loc_ind]

def check_all_resumes(scored_cvs_folder):
    """
    Performs ontology check on all resumes in the specified folder
    Returns True if all checks pass, False otherwise
    """
    print("Performing ontology check...")
    
    # Create the ontology
    onto = create_ontology()
    
    try:
        # Load and check each resume
        for resume_file in os.listdir(scored_cvs_folder):
            if resume_file.endswith('.json'):
                with open(os.path.join(scored_cvs_folder, resume_file), "r", encoding="utf-8") as f:
                    resume_data = json.load(f)
                    check_resume_ontology(resume_data, onto)

        # Run the reasoner to check ontology consistency
        sync_reasoner()

        # Save the ontology (optional)
        onto.save(file=os.path.join(scored_cvs_folder, "resume.owl"), format="rdfxml")

        # Check and report consistency
        # In owlready2, we can check if there are any unsatisfiable classes
        unsatisfiable_classes = [cls for cls in onto.classes() if cls in (onto.unsatisfiable or [])]
        if unsatisfiable_classes:
            print("Warning: Ontology inconsistency found! The following classes are unsatisfiable:")
            for cls in unsatisfiable_classes:
                print(f"  - {cls.name}")
            return False
        else:
            print("Ontology check passed. All resumes conform to the expected structure.")
            return True
            
    except Exception as e:
        print(f"Error during ontology check: {str(e)}")
        return False 
    
def gpt_convert_resume_to_json(
    resume_md: str,
    template_path: str = TEMPLATE_JSON_PATH
) -> Dict[str, Any]:
    """
    Запрашивает у GPT JSON-структуру резюме по заданному шаблону.
    """
    client = init_openai_client()
    with open(template_path, encoding="utf-8") as f:
        schema = json.load(f)

    system_prompt = (
        "You are an expert HR specialist. Provide a structured JSON object "
        "of the following schema (no extra keys):\n" +
        json.dumps(schema, ensure_ascii=False, indent=2)
    )
    user_prompt = (
        "=== Candidate Resume (Markdown) ===\n"
        f"{resume_md}\n\n"
        "Respond with only the JSON object."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.0,
            max_completion_tokens=500
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```json"):
            raw = raw.split("```", 2)[-1]
        raw = raw.strip("` \n")
        return json.loads(raw)
    except (OpenAIError, json.JSONDecodeError) as e:
        logger.error("GPT conversion failed: %s", e)
        # возвращаем «пустой» объект по шаблону
        return {
            k: ([] if isinstance(v, list) else ({} if isinstance(v, dict) else ""))
            for k, v in schema.items()
        }

def transform_and_check_resume(
    resume_md: str
) -> Tuple[Dict[str, Any], List[str]]:
    """
    1) Преобразует resume_md → JSON через GPT (по вашему шаблону)
    2) Прогоняет полученный JSON через онтологическую проверку
    3) Возвращает кортеж (resume_json, ontology_issues)
    """
    # 1) Конвертация резюме
    resume_json = gpt_convert_resume_to_json(resume_md)

    # 2) Инициализация и проверка онтологии
    onto = create_ontology()
    issues: List[str] = []

    username = extract_github_username(resume_md)
    if username:
        gh_metrics = check_github_profile(username)
        # кейс: профиль найден, но нет публичных репозиториев
        if gh_metrics.get("publicRepos", 0) == 0:
            issues.append("GitHub: нет публичных репозиториев")
        # кейс: профиль найден, но нет активности (нет последних событий)
        if gh_metrics.get("lastActiveDays") is None:
            issues.append("GitHub: нет коммитов/событий")

    try:
        check_resume_ontology(resume_json, onto)
        sync_reasoner(infer_property_values=True)
    except Exception as e:
        logger.error("Unexpected ontology error: %s", e)
        issues = [str(e)]

    return issues
