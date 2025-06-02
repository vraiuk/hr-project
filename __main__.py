import os
import math
import json
from conversion import convert_pdf_to_markdown
from cv_to_json_converter import convert_all_cvs
from ontology_check import check_all_resumes

def piecewise_education(edu_val):
    """
    edu_val: float в диапазоне [0..1]
    Кусочно-линейная функция
    """
    if edu_val <= 0.4:
        return 2.5 * edu_val           # растёт быстро на этом отрезке
    elif edu_val <= 0.7:
        return 1.0 + 1.6667 * (edu_val - 0.4)
    else:
        # от 0.7 до 1.0 идёт медленнее
        base = 1.5 + 0.5 * (edu_val - 0.7)
        return min(base, 1.0)         # чтобы не превысить 1.0

def experience_score(exp_dict):
    """
    exp_dict = { "totalYears": val, "relevance": val }
    """
    ty = exp_dict.get("totalYears", 0.0)
    rel = exp_dict.get("relevance", 0.0)
    base = (ty + rel) / 2

    # Синергия, если оба > 0.7
    synergy = 0.05 if (ty > 0.7 and rel > 0.7) else 0.0

    # Результат
    score = base + synergy
    return min(score, 1.0)

def calculate_mai_plus_score(resume, weights):

    # 1) Education c нелинейной функцией
    raw_edu = resume.get("education", 0.0)
    edu_u = piecewise_education(raw_edu)

    # 2) Experience (c учётом двух полей + синергия)
    exp_u = experience_score(resume.get("experience", {}))

    # 3) Skills
    sk = resume.get("skills", 0.0)
    # Допустим, если sk > 0.8 и exp_u > 0.6 -> +0.03
    synergy_skills = 0.03 if (sk > 0.8 and exp_u > 0.6) else 0.0
    sk_u = min(sk + synergy_skills, 1.0)

    # 4) Courses + образование (доп. 10% к edu_u)
    courses = resume.get("courses", 0.0)
    if edu_u > 0.8 and courses > 0.5:
        edu_u = min(edu_u * 1.1, 1.0)

    # 5) JobPrefs, Languages, Additional — линейно
    job_pref = resume.get("jobPreferences", 0.0)
    lang = resume.get("languages", 0.0)
    add_info = resume.get("additionalInfo", 0.0)

    # 6) Собираем итоговую сумму
    score = (
        weights["jobPreferences"] * job_pref +
        weights["experience"]     * exp_u +
        weights["education"]      * edu_u +
        weights["courses"]        * courses +
        weights["skills"]         * sk_u +
        weights["languages"]      * lang +
        weights["additional"]     * add_info
    )

    return round(score, 3)

def main():
    input_folder = "tests/raw_cvs"
    markdown_folder = "tests/cooked_cvs"
    scored_cvs_folder = "tests/scored_cvs"
    cvs_json_folder = "tests/cvs_json"
    
    # Step 1: Convert Markdown to JSON
    print("Converting PDF files to Markdown...")
    convert_pdf_to_markdown(input_folder, markdown_folder)
    print("Conversion completed!\n")

    # Step 1: Convert Markdown to JSON
    print("Converting Markdown files to JSON...")
    success, total = convert_all_cvs(markdown_folder, scored_cvs_folder)
    print(f"JSON conversion completed! Converted {success}/{total} files\n")

    # Step 2: Define weights
    weights = {
        "jobPreferences": 0.10,
        "experience":     0.25,
        "education":      0.15,
        "courses":        0.10,
        "skills":         0.20,
        "languages":      0.10,
        "additional":     0.10
    }

    # Step 3: Ontology Check
    if not check_all_resumes(cvs_json_folder):
        print("Warning: Proceeding with scoring despite ontology inconsistencies")

    # Step 4: Read JSON
    with open("tests/cv_scored_mocks_10.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # data - resumes list
    results = []
    for resume in data:
        score = calculate_mai_plus_score(resume, weights)
        results.append({
            "id": resume["id"],
            "score": score
        })

    # Step 5: Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)

    # Step 6: Log in console
    print("Результаты МАИ-оценки:")
    for item in results:
        print(f"ID = {item['id']}, Score = {item['score']}")

    # Step 7: Save to JSON
    with open("mai_results.json", "w", encoding="utf-8") as f_out:
        json.dump(results, f_out, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
