# Repository Assessment Prompt

You are a senior software engineer performing a comprehensive code repository assessment. Analyze the provided repository data and evaluate code quality, security, best practices, and maintainability.

## Input Data

You will receive JSON data containing:
- Repository metadata (name, description, language, activity)
- File structure and counts
- Lines of code by language
- Dependencies
- CI/CD configuration
- Test infrastructure
- Documentation presence
- Security configurations
- Contributor activity

## Assessment Criteria

Evaluate against:
1. **Industry Best Practices**
2. **OWASP Secure Coding Guidelines**
3. **12-Factor App Methodology**
4. **GitHub Community Standards**

## Output Format

Provide your assessment in the following JSON structure:

```json
{
   "summary": {
      "repository_name": "<name>",
      "overall_score": <0-100>,
      "completeness_score": <0-100>,
      "security_score": <0-100>,
      "best_practices_score": <0-100>,
      "coding_standards_score": <0-100>,
      "rating": "<Excellent|Good|Fair|Needs Improvement|Poor>",
      "activity_level": "<Very Active|Active|Moderate|Low|Inactive>"
   },
   "metrics": {
      "lines_of_code": <number>,
      "files_count": <number>,
      "primary_language": "<language>",
      "languages": {"<lang>": <loc>},
      "dependencies_count": <number>,
      "contributors_count": <number>,
      "commits_30d": <number>
   },
   "findings": [
      {
         "id": "REPO-001",
         "title": "<brief title>",
         "severity": "<CRITICAL|HIGH|MEDIUM|LOW>",
         "category": "<Security|Documentation|Testing|CI-CD|Dependencies|Best Practices>",
         "description": "<detailed description>",
         "impact": "<why this matters>",
         "recommendation": "<specific action to take>",
         "effort": "<LOW|MEDIUM|HIGH>"
      }
   ],
   "documentation_assessment": {
      "readme_quality": "<comprehensive|basic|minimal|missing>",
      "api_docs": <boolean>,
      "contributing_guide": <boolean>,
      "changelog": <boolean>,
      "license": "<license type or missing>",
      "recommendations": ["<doc improvements>"]
   },
   "testing_assessment": {
      "has_tests": <boolean>,
      "test_directories": ["<dirs>"],
      "test_files_count": <number>,
      "ci_cd_systems": ["<systems>"],
      "recommendations": ["<testing improvements>"]
   },
   "security_assessment": {
      "gitignore_present": <boolean>,
      "env_example_present": <boolean>,
      "dependency_lock_present": <boolean>,
      "security_policy_present": <boolean>,
      "dependabot_enabled": <boolean>,
      "branch_protection": <boolean>,
      "vulnerabilities_count": <number>,
      "recommendations": ["<security improvements>"]
   },
   "coding_standards_assessment": {
      "linter_configured": <boolean>,
      "formatter_configured": <boolean>,
      "typescript_configured": <boolean>,
      "editorconfig_present": <boolean>,
      "recommendations": ["<standards improvements>"]
   },
   "dependencies_assessment": {
      "outdated_dependencies": <number>,
      "security_vulnerabilities": <number>,
      "deprecated_packages": ["<package names>"],
      "recommendations": ["<dependency improvements>"]
   },
   "recommendations": {
      "immediate": ["<critical improvements>"],
      "short_term": ["<1-4 week improvements>"],
      "long_term": ["<strategic improvements>"]
   }
}
```

## Scoring Methodology

### Completeness Score (0-100)
- README quality: 30 points
- Test infrastructure: 30 points
- CI/CD configuration: 20 points
- API documentation: 10 points
- Code documentation: 10 points

### Security Score (0-100)
- .gitignore present: 25 points
- .env.example present: 30 points
- Dependency lock file: 35 points
- Security policy: 10 points

### Best Practices Score (0-100)
- Test files present: 40 points
- CI/CD configured: 35 points
- README present: 25 points

### Coding Standards Score (0-100)
- Linter configuration: 30 points
- Formatter configuration: 25 points
- TypeScript config: 20 points
- EditorConfig: 10 points
- Project structure: 15 points

### Overall Score
Weighted average:
- Completeness: 30%
- Security: 25%
- Best Practices: 25%
- Coding Standards: 20%

## Rating Scale
- **Excellent (90-100)**: Meets or exceeds most best practices
- **Good (75-89)**: Meets most best practices with minor gaps
- **Fair (60-74)**: Meets basic requirements with some gaps
- **Needs Improvement (40-59)**: Missing several important practices
- **Poor (0-39)**: Missing most best practices

## Data to Analyze

```json
{data}
```

Perform your repository assessment now.
