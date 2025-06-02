# HR Resume Analysis System

A comprehensive system for analyzing and evaluating resumes using multiple criteria, data verification, and external service integration.

## Features

- **Multicriteria Evaluation**: Evaluate resumes based on multiple criteria including experience, skills, education, and languages
- **Data Verification**: Verify resume data against external sources
- **External Service Integration**: Enrich resume data with information from professional networks and job market data
- **Job Recommendations**: Get personalized job recommendations based on resume analysis

## Project Structure

```
project_root/
├── requirements.txt         # Project dependencies
├── main.py                  # FastAPI application entry point
├── config.py               # Configuration settings
├── data/                   # Data storage directory
├── modules/
│   ├── multicriteria/      # Resume evaluation module
│   ├── verification/       # Data verification module
│   └── external_services/  # External service integration
└── tests/                  # Test files
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd hr-project
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root with the following variables:
```
EXTERNAL_API_KEY=your_api_key
DATABASE_URL=your_database_url
```

## Usage

1. Start the FastAPI server:
```bash
python main.py
```

2. Access the API documentation:
- Open your browser and navigate to `http://localhost:8000/docs`
- Or use the alternative documentation at `http://localhost:8000/redoc`

3. API Endpoints:
- `POST /analyze-resume`: Analyze a resume
- `GET /health`: Check system health

## Example Request

```python
import requests

resume_data = {
    "candidate_id": "123",
    "full_name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "education": [
        {
            "institution": "University of Example",
            "degree": "Bachelor",
            "field_of_study": "Computer Science",
            "start_date": "2018-09-01",
            "end_date": "2022-06-30"
        }
    ],
    "experience": [
        {
            "company": "Tech Corp",
            "position": "Software Engineer",
            "start_date": "2022-07-01",
            "end_date": "2023-12-31",
            "description": "Full-stack development",
            "skills_used": ["Python", "FastAPI", "React"]
        }
    ],
    "skills": [
        {
            "name": "Python",
            "level": 0.9,
            "years_of_experience": 3
        }
    ],
    "languages": [
        {
            "name": "English",
            "level": "C1",
            "certificate": "IELTS 7.5"
        }
    ]
}

response = requests.post(
    "http://localhost:8000/analyze-resume",
    json=resume_data
)
print(response.json())
```

## Testing

Run the test suite:
```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 