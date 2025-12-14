# Repository Assessment Prompt

You are a senior software engineer performing a comprehensive code repository assessment. Analyze the provided repository data and evaluate code quality, security, best practices, maintainability, architecture, performance, compliance, and operational readiness.

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
- Code quality metrics (complexity, technical debt)
- Security deep dive (secret scanning, vulnerability patterns)
- Performance indicators
- Architecture and design patterns
- Maintainability metrics
- DevOps and operations readiness
- Compliance indicators
- Testing quality
- Developer experience
- Code review practices
- Error handling patterns
- Documentation quality

## Assessment Criteria

Evaluate against:
1. **Industry Best Practices**
2. **OWASP Secure Coding Guidelines**
3. **12-Factor App Methodology**
4. **GitHub Community Standards**
5. **SOLID Principles**
6. **Clean Code Principles**
7. **Security Best Practices**
8. **Performance Optimization Guidelines**
9. **Accessibility Standards (WCAG)**
10. **Compliance Frameworks (GDPR, HIPAA, PCI-DSS)**

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
      "code_quality_score": <0-100>,
      "architecture_score": <0-100>,
      "performance_score": <0-100>,
      "maintainability_score": <0-100>,
      "devops_score": <0-100>,
      "compliance_score": <0-100>,
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
         "category": "<Security|Documentation|Testing|CI-CD|Dependencies|Best Practices|Code Quality|Architecture|Performance|Maintainability|DevOps|Compliance|Error Handling>",
         "description": "<detailed description>",
         "impact": "<why this matters>",
         "recommendation": "<specific action to take>",
         "effort": "<LOW|MEDIUM|HIGH>"
      }
   ],
   "code_quality_assessment": {
      "complexity_indicators": {
         "large_files_count": <number>,
         "high_complexity": <boolean>,
         "complexity_rating": "<low|medium|high>"
      },
      "technical_debt": {
         "todo_count": <number>,
         "fixme_count": <number>,
         "hack_count": <number>,
         "deprecated_count": <number>,
         "debt_level": "<low|medium|high|critical>"
      },
      "code_smells": ["<list of identified code smells>"],
      "recommendations": ["<code quality improvements>"]
   },
   "security_assessment": {
      "gitignore_present": <boolean>,
      "env_example_present": <boolean>,
      "dependency_lock_present": <boolean>,
      "security_policy_present": <boolean>,
      "dependabot_enabled": <boolean>,
      "branch_protection": <boolean>,
      "vulnerabilities_count": <number>,
      "potential_secrets_count": <number>,
      "insecure_patterns": {
         "sql_injection_risk": <boolean>,
         "xss_risk": <boolean>,
         "eval_usage": <boolean>,
         "dangerous_functions": ["<list>"]
      },
      "encryption_usage": {
         "crypto_libraries": <boolean>,
         "tls_configured": <boolean>
      },
      "recommendations": ["<security improvements>"]
   },
   "performance_assessment": {
      "performance_tests": <boolean>,
      "monitoring_tools": ["<list>"],
      "caching_strategies": ["<list>"],
      "bundle_analysis": <boolean>,
      "recommendations": ["<performance improvements>"]
   },
   "architecture_assessment": {
      "project_structure_quality": "<excellent|good|fair|poor>",
      "design_patterns": ["<list of detected patterns>"],
      "api_design": {
         "has_openapi": <boolean>,
         "has_graphql": <boolean>,
         "versioning": <boolean>
      },
      "architecture_docs": <boolean>,
      "recommendations": ["<architecture improvements>"]
   },
   "maintainability_assessment": {
      "code_comments": {
         "comment_ratio": <percentage>,
         "docstring_ratio": <percentage>,
         "quality": "<good|fair|poor>"
      },
      "code_ownership": {
         "codeowners_present": <boolean>,
         "maintainers_file": <boolean>
      },
      "legacy_indicators": {
         "deprecated_libraries": ["<list>"],
         "old_patterns": <boolean>
      },
      "recommendations": ["<maintainability improvements>"]
   },
   "devops_assessment": {
      "infrastructure_as_code": {
         "terraform": <boolean>,
         "cloudformation": <boolean>,
         "cdk": <boolean>
      },
      "deployment_config": {
         "dockerfile": <boolean>,
         "kubernetes": <boolean>,
         "helm": <boolean>
      },
      "monitoring_logging": {
         "apm_tools": ["<list>"],
         "structured_logging": <boolean>
      },
      "health_checks": <boolean>,
      "environment_config": {
         "has_env_example": <boolean>,
         "config_files": <number>
      },
      "recommendations": ["<devops improvements>"]
   },
   "compliance_assessment": {
      "licenses": {
         "main_license": "<license type>",
         "license_file": <boolean>,
         "compliance_status": "<compliant|needs_review|non_compliant>"
      },
      "privacy_compliance": {
         "privacy_policy": <boolean>,
         "gdpr_indicators": <boolean>
      },
      "accessibility": {
         "a11y_testing": <boolean>,
         "a11y_libraries": ["<list>"]
      },
      "recommendations": ["<compliance improvements>"]
   },
   "testing_assessment": {
      "has_tests": <boolean>,
      "test_types": {
         "unit_tests": <boolean>,
         "integration_tests": <boolean>,
         "e2e_tests": <boolean>,
         "performance_tests": <boolean>
      },
      "test_frameworks": ["<list>"],
      "test_coverage_tools": <boolean>,
      "ci_cd_systems": ["<systems>"],
      "recommendations": ["<testing improvements>"]
   },
   "developer_experience_assessment": {
      "onboarding": {
         "getting_started": <boolean>,
         "setup_instructions": <boolean>
      },
      "dev_environment": {
         "docker_dev": <boolean>,
         "devcontainer": <boolean>
      },
      "ide_config": <boolean>,
      "pre_commit_hooks": <boolean>,
      "recommendations": ["<developer experience improvements>"]
   },
   "code_review_assessment": {
      "pr_template": <boolean>,
      "issue_templates": <boolean>,
      "review_requirements": <boolean>,
      "recommendations": ["<code review improvements>"]
   },
   "error_handling_assessment": {
      "try_catch_usage": <boolean>,
      "error_boundaries": <boolean>,
      "logging_present": <boolean>,
      "error_handling_quality": "<excellent|good|fair|poor>",
      "recommendations": ["<error handling improvements>"]
   },
   "documentation_assessment": {
      "readme_quality": "<comprehensive|basic|minimal|missing>",
      "api_docs": {
         "openapi": <boolean>,
         "swagger": <boolean>,
         "graphql_schema": <boolean>
      },
      "code_examples": <boolean>,
      "adr_present": <boolean>,
      "runbooks": <boolean>,
      "contributing_guide": <boolean>,
      "changelog": <boolean>,
      "license": "<license type or missing>",
      "recommendations": ["<doc improvements>"]
   },
   "dependencies_assessment": {
      "outdated_dependencies": <number>,
      "security_vulnerabilities": <number>,
      "deprecated_packages": ["<package names>"],
      "recommendations": ["<dependency improvements>"]
   },
   "coding_standards_assessment": {
      "linter_configured": <boolean>,
      "formatter_configured": <boolean>,
      "typescript_configured": <boolean>,
      "editorconfig_present": <boolean>,
      "recommendations": ["<standards improvements>"]
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
- README quality: 20 points
- Test infrastructure: 20 points
- CI/CD configuration: 15 points
- API documentation: 15 points
- Code documentation: 10 points
- Architecture documentation: 10 points
- Runbooks/operational docs: 10 points

### Security Score (0-100)
- .gitignore present: 10 points
- .env.example present: 15 points
- Dependency lock file: 15 points
- Security policy: 10 points
- No hardcoded secrets: 20 points
- Encryption libraries: 10 points
- No insecure patterns: 15 points
- Branch protection: 5 points

### Code Quality Score (0-100)
- Low technical debt: 30 points
- Reasonable complexity: 25 points
- Good code comments: 20 points
- No code smells: 15 points
- Clean code structure: 10 points

### Architecture Score (0-100)
- Clear project structure: 30 points
- Design patterns: 20 points
- API design quality: 25 points
- Architecture documentation: 15 points
- Modular design: 10 points

### Performance Score (0-100)
- Performance tests: 30 points
- Monitoring tools: 25 points
- Caching strategies: 25 points
- Bundle analysis: 20 points

### Maintainability Score (0-100)
- Code comments quality: 30 points
- Code ownership: 20 points
- Low legacy code: 25 points
- Good documentation: 25 points

### DevOps Score (0-100)
- Infrastructure as Code: 25 points
- Deployment configuration: 20 points
- Monitoring/logging: 20 points
- Health checks: 15 points
- Environment management: 20 points

### Compliance Score (0-100)
- License compliance: 30 points
- Privacy compliance: 25 points
- Accessibility: 20 points
- Industry compliance: 25 points

### Best Practices Score (0-100)
- Test files present: 25 points
- CI/CD configured: 25 points
- README present: 15 points
- Code review practices: 15 points
- Error handling: 20 points

### Coding Standards Score (0-100)
- Linter configuration: 30 points
- Formatter configuration: 25 points
- TypeScript config: 20 points
- EditorConfig: 10 points
- Project structure: 15 points

### Overall Score
Weighted average:
- Completeness: 15%
- Security: 20%
- Code Quality: 15%
- Architecture: 10%
- Performance: 5%
- Maintainability: 10%
- DevOps: 5%
- Compliance: 5%
- Best Practices: 10%
- Coding Standards: 5%

## Rating Scale
- **Excellent (90-100)**: Meets or exceeds most best practices across all categories
- **Good (75-89)**: Meets most best practices with minor gaps
- **Fair (60-74)**: Meets basic requirements with some gaps
- **Needs Improvement (40-59)**: Missing several important practices
- **Poor (0-39)**: Missing most best practices

## Assessment Priorities

### Critical Issues (Immediate Action)
- Hardcoded secrets or credentials
- SQL injection or XSS vulnerabilities
- Missing security policies
- No dependency lock files
- No error handling

### High Priority (Short-term)
- Missing tests
- No CI/CD
- Poor documentation
- High technical debt
- No monitoring

### Medium Priority (Medium-term)
- Architecture improvements
- Performance optimization
- Compliance gaps
- Developer experience

### Low Priority (Long-term)
- Code style improvements
- Documentation enhancements
- Accessibility improvements

## Data to Analyze

```json
{data}
```

Perform your comprehensive repository assessment now, evaluating all aspects of code quality, security, architecture, performance, maintainability, DevOps readiness, compliance, and operational excellence.
